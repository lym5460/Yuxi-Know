"""API Key Management Router - API Key 管理路由

提供 API Key 的 CRUD 管理接口，所有接口需要管理员权限。

路由:
- POST /api/apikeys - 创建 API Key
- GET /api/apikeys - 获取 API Key 列表
- GET /api/apikeys/scopes - 获取可用权限范围列表
- GET /api/apikeys/{key_id} - 获取单个 API Key
- PUT /api/apikeys/{key_id} - 更新 API Key
- DELETE /api/apikeys/{key_id} - 删除 API Key
- PUT /api/apikeys/{key_id}/toggle - 启用/禁用 API Key
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from server.utils.auth_middleware import get_admin_user, get_db
from src.services import apikey_service
from src.storage.postgres.models_business import User

apikey = APIRouter(prefix="/apikeys", tags=["api-keys"])


# =============================================================================
# === 请求/响应模型 ===
# =============================================================================


class APIKeyCreate(BaseModel):
    """创建 API Key 请求"""

    name: str = Field(..., min_length=1, max_length=100, description="API Key 名称")
    description: str | None = Field(None, max_length=500, description="描述")
    scopes: list[str] = Field(..., description="权限范围列表")
    expires_days: int | None = Field(None, ge=1, description="过期天数，None 表示永不过期")


class APIKeyUpdate(BaseModel):
    """更新 API Key 请求"""

    name: str | None = Field(None, min_length=1, max_length=100, description="API Key 名称")
    description: str | None = Field(None, max_length=500, description="描述")
    scopes: list[str] | None = Field(None, description="权限范围列表")


class APIKeyResponse(BaseModel):
    """API Key 响应（不含明文密钥）"""

    id: int
    name: str
    description: str | None
    key_prefix: str
    scopes: list[str]
    is_active: bool
    expires_at: str | None
    last_used_at: str | None
    created_at: str


class APIKeyCreateResponse(APIKeyResponse):
    """创建 API Key 响应（包含明文密钥，仅此一次）"""

    key: str = Field(..., description="完整密钥，仅此一次返回")


class ScopeInfo(BaseModel):
    """权限范围信息"""

    scope: str
    description: str


# =============================================================================
# === 辅助函数 ===
# =============================================================================


def _format_datetime(dt) -> str | None:
    """格式化日期时间为 ISO 字符串"""
    return dt.isoformat() if dt else None


def _api_key_to_response(api_key) -> APIKeyResponse:
    """将 APIKey 模型转换为响应对象"""
    return APIKeyResponse(
        id=api_key.id,
        name=api_key.name,
        description=api_key.description,
        key_prefix=api_key.key_prefix,
        scopes=api_key.scopes or [],
        is_active=bool(api_key.is_active),
        expires_at=_format_datetime(api_key.expires_at),
        last_used_at=_format_datetime(api_key.last_used_at),
        created_at=_format_datetime(api_key.created_at),
    )


# =============================================================================
# === 路由处理 ===
# =============================================================================


@apikey.post("", response_model=APIKeyCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    data: APIKeyCreate,
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """创建 API Key

    创建成功后返回完整的 API Key 明文，此密钥仅在创建时返回一次，请妥善保存。
    """
    # 验证权限范围
    available_scopes = apikey_service.get_available_scopes()
    invalid_scopes = [s for s in data.scopes if s not in available_scopes]
    if invalid_scopes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid scopes: {', '.join(invalid_scopes)}",
        )

    api_key, raw_key = await apikey_service.create_api_key(
        db=db,
        name=data.name,
        scopes=data.scopes,
        created_by=current_user.id,
        description=data.description,
        expires_days=data.expires_days,
    )

    return APIKeyCreateResponse(
        id=api_key.id,
        name=api_key.name,
        description=api_key.description,
        key_prefix=api_key.key_prefix,
        key=raw_key,
        scopes=api_key.scopes or [],
        is_active=bool(api_key.is_active),
        expires_at=_format_datetime(api_key.expires_at),
        last_used_at=_format_datetime(api_key.last_used_at),
        created_at=_format_datetime(api_key.created_at),
    )


@apikey.get("", response_model=list[APIKeyResponse])
async def list_api_keys(
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """获取 API Key 列表

    返回所有 API Key 的元数据，不包含明文密钥。
    """
    api_keys = await apikey_service.list_api_keys(db)
    return [_api_key_to_response(k) for k in api_keys]


@apikey.get("/scopes", response_model=list[ScopeInfo])
async def get_available_scopes(
    current_user: User = Depends(get_admin_user),
):
    """获取可用权限范围列表

    返回系统支持的所有权限范围及其描述。
    """
    scopes = apikey_service.get_available_scopes()
    return [ScopeInfo(scope=k, description=v) for k, v in scopes.items()]


@apikey.get("/{key_id}", response_model=APIKeyResponse)
async def get_api_key(
    key_id: int,
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """获取单个 API Key

    返回指定 API Key 的详细信息，不包含明文密钥。
    """
    api_key = await apikey_service.get_api_key(db, key_id)
    if api_key is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API Key not found",
        )
    return _api_key_to_response(api_key)


@apikey.put("/{key_id}", response_model=APIKeyResponse)
async def update_api_key(
    key_id: int,
    data: APIKeyUpdate,
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """更新 API Key

    更新 API Key 的名称、描述或权限范围。
    """
    # 验证权限范围（如果提供）
    if data.scopes is not None:
        available_scopes = apikey_service.get_available_scopes()
        invalid_scopes = [s for s in data.scopes if s not in available_scopes]
        if invalid_scopes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid scopes: {', '.join(invalid_scopes)}",
            )

    api_key = await apikey_service.update_api_key(
        db=db,
        key_id=key_id,
        name=data.name,
        description=data.description,
        scopes=data.scopes,
    )

    if api_key is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API Key not found",
        )

    return _api_key_to_response(api_key)


@apikey.delete("/{key_id}")
async def delete_api_key(
    key_id: int,
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """删除 API Key

    永久删除指定的 API Key，删除后使用该密钥的所有请求将被拒绝。
    """
    success = await apikey_service.delete_api_key(db, key_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API Key not found",
        )
    return {"message": "API Key deleted successfully", "key_id": key_id}


@apikey.put("/{key_id}/toggle", response_model=APIKeyResponse)
async def toggle_api_key(
    key_id: int,
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """启用/禁用 API Key

    切换 API Key 的启用状态。禁用后，使用该密钥的请求将返回 403 错误。
    """
    api_key = await apikey_service.toggle_api_key(db, key_id)
    if api_key is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API Key not found",
        )
    return _api_key_to_response(api_key)
