"""API Key Service - API Key 管理服务

提供 API Key 的创建、验证、管理等业务逻辑。

职责:
- API Key 生成和哈希
- API Key CRUD 操作
- API Key 验证和权限检查
"""

import hashlib
import secrets
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.storage.postgres.models_business import APIKey
from src.utils import logger
from src.utils.datetime_utils import utc_now_naive

# =============================================================================
# === 常量定义 ===
# =============================================================================

# API Key 前缀
API_KEY_PREFIX = "yk_"

# API Key 随机部分长度
API_KEY_RANDOM_LENGTH = 32

# 存储的前缀长度（用于识别）
KEY_PREFIX_DISPLAY_LENGTH = 8

# 预定义权限范围
AVAILABLE_SCOPES = {
    "knowledge:list": "获取知识库列表",
    "knowledge:read": "查询知识库内容",
}


# =============================================================================
# === 密钥生成和哈希 ===
# =============================================================================


def generate_api_key() -> str:
    """生成 API Key

    格式: yk_ + 32位随机字符

    Returns:
        完整的 API Key 明文
    """
    random_part = secrets.token_urlsafe(API_KEY_RANDOM_LENGTH)[:API_KEY_RANDOM_LENGTH]
    return f"{API_KEY_PREFIX}{random_part}"


def hash_api_key(raw_key: str) -> str:
    """计算 API Key 的 SHA256 哈希值

    Args:
        raw_key: API Key 明文

    Returns:
        64位十六进制哈希字符串
    """
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def get_key_prefix(raw_key: str) -> str:
    """获取 API Key 的前缀部分（用于识别）

    Args:
        raw_key: API Key 明文

    Returns:
        前缀字符串，如 "yk_a1b2"
    """
    return raw_key[:KEY_PREFIX_DISPLAY_LENGTH]


# =============================================================================
# === API Key CRUD 操作 ===
# =============================================================================


async def create_api_key(
    db: AsyncSession,
    name: str,
    scopes: list[str],
    created_by: int,
    description: str | None = None,
    expires_days: int | None = None,
) -> tuple[APIKey, str]:
    """创建 API Key

    Args:
        db: 数据库会话
        name: API Key 名称
        scopes: 权限范围列表
        created_by: 创建者用户 ID
        description: 描述（可选）
        expires_days: 过期天数（可选，None 表示永不过期）

    Returns:
        (APIKey 对象, 明文密钥) - 明文密钥仅此一次返回
    """
    # 生成密钥
    raw_key = generate_api_key()
    key_hash = hash_api_key(raw_key)
    key_prefix = get_key_prefix(raw_key)

    # 计算过期时间
    expires_at = None
    if expires_days is not None and expires_days > 0:
        expires_at = utc_now_naive() + timedelta(days=expires_days)

    # 创建记录
    api_key = APIKey(
        name=name,
        description=description,
        key_prefix=key_prefix,
        key_hash=key_hash,
        scopes=scopes,
        is_active=1,
        expires_at=expires_at,
        created_by=created_by,
    )

    db.add(api_key)
    await db.commit()
    await db.refresh(api_key)

    logger.info(f"Created API Key '{name}' (id={api_key.id}) by user {created_by}")
    return api_key, raw_key


async def list_api_keys(db: AsyncSession) -> list[APIKey]:
    """获取所有 API Key 列表

    Args:
        db: 数据库会话

    Returns:
        API Key 列表（不含明文密钥）
    """
    result = await db.execute(select(APIKey).order_by(APIKey.created_at.desc()))
    return list(result.scalars().all())


async def get_api_key(db: AsyncSession, key_id: int) -> APIKey | None:
    """获取单个 API Key

    Args:
        db: 数据库会话
        key_id: API Key ID

    Returns:
        API Key 对象或 None
    """
    result = await db.execute(select(APIKey).filter(APIKey.id == key_id))
    return result.scalar_one_or_none()


async def update_api_key(
    db: AsyncSession,
    key_id: int,
    name: str | None = None,
    description: str | None = None,
    scopes: list[str] | None = None,
    is_active: bool | None = None,
) -> APIKey | None:
    """更新 API Key

    Args:
        db: 数据库会话
        key_id: API Key ID
        name: 新名称（可选）
        description: 新描述（可选）
        scopes: 新权限范围（可选）
        is_active: 新启用状态（可选）

    Returns:
        更新后的 API Key 对象，如果不存在则返回 None
    """
    api_key = await get_api_key(db, key_id)
    if api_key is None:
        return None

    if name is not None:
        api_key.name = name
    if description is not None:
        api_key.description = description
    if scopes is not None:
        api_key.scopes = scopes
    if is_active is not None:
        api_key.is_active = 1 if is_active else 0

    await db.commit()
    await db.refresh(api_key)

    logger.info(f"Updated API Key '{api_key.name}' (id={key_id})")
    return api_key


async def delete_api_key(db: AsyncSession, key_id: int) -> bool:
    """删除 API Key

    Args:
        db: 数据库会话
        key_id: API Key ID

    Returns:
        是否删除成功
    """
    api_key = await get_api_key(db, key_id)
    if api_key is None:
        return False

    name = api_key.name
    await db.delete(api_key)
    await db.commit()

    logger.info(f"Deleted API Key '{name}' (id={key_id})")
    return True


async def toggle_api_key(db: AsyncSession, key_id: int) -> APIKey | None:
    """切换 API Key 启用/禁用状态

    Args:
        db: 数据库会话
        key_id: API Key ID

    Returns:
        更新后的 API Key 对象，如果不存在则返回 None
    """
    api_key = await get_api_key(db, key_id)
    if api_key is None:
        return None

    api_key.is_active = 0 if api_key.is_active else 1
    await db.commit()
    await db.refresh(api_key)

    status = "enabled" if api_key.is_active else "disabled"
    logger.info(f"Toggled API Key '{api_key.name}' (id={key_id}) to {status}")
    return api_key


# =============================================================================
# === API Key 验证 ===
# =============================================================================


async def validate_api_key(db: AsyncSession, raw_key: str) -> APIKey | None:
    """验证 API Key

    验证流程:
    1. 计算密钥哈希
    2. 查找匹配的记录
    3. 检查是否过期

    注意: 此函数不检查 is_active 状态，调用方需要单独处理

    Args:
        db: 数据库会话
        raw_key: API Key 明文

    Returns:
        有效的 APIKey 对象，如果无效或过期则返回 None
    """
    # 检查格式
    if not raw_key or not raw_key.startswith(API_KEY_PREFIX):
        return None

    # 计算哈希并查找
    key_hash = hash_api_key(raw_key)
    result = await db.execute(select(APIKey).filter(APIKey.key_hash == key_hash))
    api_key = result.scalar_one_or_none()

    if api_key is None:
        return None

    # 检查是否过期
    if api_key.expires_at is not None and api_key.expires_at < utc_now_naive():
        logger.debug(f"API Key '{api_key.name}' (id={api_key.id}) has expired")
        return None

    return api_key


async def update_last_used(db: AsyncSession, key_id: int) -> None:
    """更新 API Key 最后使用时间

    Args:
        db: 数据库会话
        key_id: API Key ID
    """
    api_key = await get_api_key(db, key_id)
    if api_key is not None:
        api_key.last_used_at = utc_now_naive()
        await db.commit()


def check_scopes(api_key: APIKey, required_scopes: list[str]) -> bool:
    """检查 API Key 是否具有所需的权限范围

    Args:
        api_key: API Key 对象
        required_scopes: 所需的权限范围列表

    Returns:
        是否具有所有所需权限
    """
    if not required_scopes:
        return True

    key_scopes = set(api_key.scopes or [])
    return all(scope in key_scopes for scope in required_scopes)


def get_available_scopes() -> dict[str, str]:
    """获取所有可用的权限范围

    Returns:
        权限范围字典 {scope: description}
    """
    return AVAILABLE_SCOPES.copy()
