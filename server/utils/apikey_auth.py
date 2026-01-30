"""API Key Authentication - API Key 认证依赖模块

提供 FastAPI 依赖注入函数，用于验证 API Key 并检查权限范围。

职责:
- 从 Authorization 头提取 API Key
- 验证 API Key 有效性
- 检查权限范围
- 处理各种错误情况（401/403）
- 频率限制（429）
"""

import time
from collections.abc import Callable
from dataclasses import dataclass, field

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from server.utils.auth_middleware import get_db
from src.services.apikey_service import check_scopes, update_last_used, validate_api_key
from src.storage.postgres.models_business import APIKey


# =============================================================================
# === 错误消息常量 ===
# =============================================================================

ERROR_MISSING_API_KEY = "Missing API key"
ERROR_INVALID_AUTH_FORMAT = "Invalid authorization format. Expected: Bearer {api_key}"
ERROR_INVALID_API_KEY = "Invalid API key"
ERROR_API_KEY_EXPIRED = "API key has expired"
ERROR_API_KEY_DISABLED = "API key is disabled"
ERROR_INSUFFICIENT_PERMISSIONS = "Insufficient permissions"
ERROR_RATE_LIMIT_EXCEEDED = "Rate limit exceeded"


# =============================================================================
# === 频率限制配置 ===
# =============================================================================

# 每分钟最大请求数（默认值）
DEFAULT_RATE_LIMIT = 60
# 时间窗口（秒）
RATE_LIMIT_WINDOW = 60


# =============================================================================
# === 频率限制器 ===
# =============================================================================


@dataclass
class RateLimitEntry:
    """频率限制条目"""

    count: int = 0
    window_start: float = field(default_factory=time.time)


class RateLimiter:
    """基于内存的频率限制器

    使用滑动窗口算法，对每个 API Key 实施每分钟最大请求数限制。
    """

    def __init__(self, max_requests: int = DEFAULT_RATE_LIMIT, window_seconds: int = RATE_LIMIT_WINDOW):
        """初始化频率限制器

        Args:
            max_requests: 时间窗口内最大请求数
            window_seconds: 时间窗口大小（秒）
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._cache: dict[int, RateLimitEntry] = {}

    def check_rate_limit(self, api_key_id: int) -> tuple[bool, int]:
        """检查是否超过频率限制

        Args:
            api_key_id: API Key ID

        Returns:
            (是否允许请求, 剩余等待秒数)
            - 如果允许请求，返回 (True, 0)
            - 如果超过限制，返回 (False, retry_after_seconds)
        """
        current_time = time.time()

        # 获取或创建条目
        if api_key_id not in self._cache:
            self._cache[api_key_id] = RateLimitEntry(count=1, window_start=current_time)
            return True, 0

        entry = self._cache[api_key_id]
        elapsed = current_time - entry.window_start

        # 如果时间窗口已过，重置计数
        if elapsed >= self.window_seconds:
            entry.count = 1
            entry.window_start = current_time
            return True, 0

        # 检查是否超过限制
        if entry.count >= self.max_requests:
            retry_after = int(self.window_seconds - elapsed) + 1
            return False, retry_after

        # 增加计数
        entry.count += 1
        return True, 0

    def get_remaining(self, api_key_id: int) -> int:
        """获取剩余请求次数

        Args:
            api_key_id: API Key ID

        Returns:
            剩余请求次数
        """
        if api_key_id not in self._cache:
            return self.max_requests

        entry = self._cache[api_key_id]
        current_time = time.time()
        elapsed = current_time - entry.window_start

        # 如果时间窗口已过，返回最大值
        if elapsed >= self.window_seconds:
            return self.max_requests

        return max(0, self.max_requests - entry.count)

    def clear(self) -> None:
        """清除所有缓存"""
        self._cache.clear()


# 全局频率限制器实例
_rate_limiter = RateLimiter()


# =============================================================================
# === 辅助函数 ===
# =============================================================================


def get_api_key_from_header(authorization: str | None) -> str:
    """从 Authorization 头提取 API Key

    Args:
        authorization: Authorization 头的值，格式应为 "Bearer {api_key}"

    Returns:
        提取的 API Key 明文

    Raises:
        HTTPException 401: 缺少 Authorization 头或格式错误
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MISSING_API_KEY,
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 检查格式
    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_INVALID_AUTH_FORMAT,
            headers={"WWW-Authenticate": "Bearer"},
        )

    return parts[1]


# =============================================================================
# === 认证依赖 ===
# =============================================================================


async def validate_api_key_auth(
    authorization: str | None = Header(None, alias="Authorization"),
    db: AsyncSession = Depends(get_db),
) -> APIKey:
    """验证 API Key 有效性的 FastAPI 依赖

    验证流程:
    1. 从 Authorization 头提取 API Key
    2. 验证 API Key 是否存在且未过期
    3. 检查 API Key 是否启用
    4. 检查频率限制
    5. 更新最后使用时间

    Args:
        authorization: Authorization 头，格式为 "Bearer {api_key}"
        db: 数据库会话

    Returns:
        验证通过的 APIKey 对象

    Raises:
        HTTPException 401: API Key 无效或过期
        HTTPException 403: API Key 已禁用
        HTTPException 429: 超过频率限制
    """
    # 提取 API Key
    raw_key = get_api_key_from_header(authorization)

    # 验证 API Key（检查存在性和过期）
    api_key = await validate_api_key(db, raw_key)

    if api_key is None:
        # 需要区分是不存在还是已过期
        # validate_api_key 返回 None 可能是因为：
        # 1. 格式错误
        # 2. 不存在
        # 3. 已过期
        # 为了安全，统一返回 Invalid API key，但如果需要区分过期，需要额外检查
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_INVALID_API_KEY,
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 检查是否启用
    if not api_key.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERROR_API_KEY_DISABLED,
        )

    # 检查频率限制
    allowed, retry_after = _rate_limiter.check_rate_limit(api_key.id)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=ERROR_RATE_LIMIT_EXCEEDED,
            headers={"Retry-After": str(retry_after)},
        )

    # 更新最后使用时间
    await update_last_used(db, api_key.id)

    return api_key


def require_scopes(*scopes: str) -> Callable[..., APIKey]:
    """创建检查权限范围的依赖工厂

    用于指定接口所需的权限范围，返回一个 FastAPI 依赖函数。

    Usage:
        @router.get("/knowledge/list")
        async def list_kb(api_key: APIKey = Depends(require_scopes("knowledge:list"))):
            ...

        @router.post("/knowledge/query")
        async def query_kb(api_key: APIKey = Depends(require_scopes("knowledge:read", "knowledge:list"))):
            ...

    Args:
        *scopes: 该接口所需的权限范围

    Returns:
        FastAPI 依赖函数
    """
    required_scopes = list(scopes)

    async def _check_scopes(
        api_key: APIKey = Depends(validate_api_key_auth),
    ) -> APIKey:
        """检查 API Key 是否具有所需权限范围

        Args:
            api_key: 已验证的 API Key 对象

        Returns:
            验证通过的 APIKey 对象

        Raises:
            HTTPException 403: 权限不足
        """
        if not check_scopes(api_key, required_scopes):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=ERROR_INSUFFICIENT_PERMISSIONS,
            )
        return api_key

    return _check_scopes


# =============================================================================
# === 频率限制器管理函数 ===
# =============================================================================


def get_rate_limiter() -> RateLimiter:
    """获取全局频率限制器实例

    Returns:
        全局频率限制器实例
    """
    return _rate_limiter


def configure_rate_limiter(max_requests: int = DEFAULT_RATE_LIMIT, window_seconds: int = RATE_LIMIT_WINDOW) -> None:
    """配置全局频率限制器

    Args:
        max_requests: 时间窗口内最大请求数
        window_seconds: 时间窗口大小（秒）
    """
    global _rate_limiter
    _rate_limiter = RateLimiter(max_requests=max_requests, window_seconds=window_seconds)


def reset_rate_limiter() -> None:
    """重置频率限制器缓存

    清除所有 API Key 的请求计数，用于测试或管理目的。
    """
    _rate_limiter.clear()
