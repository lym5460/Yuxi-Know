"""
Open API Router 集成测试

测试开放 API 接口的认证和权限验证。

测试内容:
- 知识库列表接口
- 知识库查询接口
- 权限验证

Property 9: 权限范围验证
Validates: Requirements 6.2.1, 6.2.3, 6.1.3
"""

from __future__ import annotations

import pytest
import httpx

pytestmark = [pytest.mark.asyncio, pytest.mark.integration]


# =============================================================================
# === Fixtures ===
# =============================================================================


@pytest.fixture
async def api_key_with_all_scopes(test_client: httpx.AsyncClient, admin_headers: dict[str, str]):
    """创建具有所有权限的 API Key"""
    response = await test_client.post(
        "/api/apikeys",
        json={
            "name": "pytest_open_api_test_all",
            "description": "Test API Key with all scopes",
            "scopes": ["knowledge:list", "knowledge:read"],
            "expires_days": 1,
        },
        headers=admin_headers,
    )
    assert response.status_code == 201, f"Failed to create API Key: {response.text}"
    data = response.json()
    key_id = data["id"]
    raw_key = data["key"]

    yield {"id": key_id, "key": raw_key, "scopes": data["scopes"]}

    # 清理
    await test_client.delete(f"/api/apikeys/{key_id}", headers=admin_headers)


@pytest.fixture
async def api_key_list_only(test_client: httpx.AsyncClient, admin_headers: dict[str, str]):
    """创建仅有 knowledge:list 权限的 API Key"""
    response = await test_client.post(
        "/api/apikeys",
        json={
            "name": "pytest_open_api_test_list",
            "description": "Test API Key with list scope only",
            "scopes": ["knowledge:list"],
            "expires_days": 1,
        },
        headers=admin_headers,
    )
    assert response.status_code == 201, f"Failed to create API Key: {response.text}"
    data = response.json()
    key_id = data["id"]
    raw_key = data["key"]

    yield {"id": key_id, "key": raw_key, "scopes": data["scopes"]}

    # 清理
    await test_client.delete(f"/api/apikeys/{key_id}", headers=admin_headers)


@pytest.fixture
async def api_key_read_only(test_client: httpx.AsyncClient, admin_headers: dict[str, str]):
    """创建仅有 knowledge:read 权限的 API Key"""
    response = await test_client.post(
        "/api/apikeys",
        json={
            "name": "pytest_open_api_test_read",
            "description": "Test API Key with read scope only",
            "scopes": ["knowledge:read"],
            "expires_days": 1,
        },
        headers=admin_headers,
    )
    assert response.status_code == 201, f"Failed to create API Key: {response.text}"
    data = response.json()
    key_id = data["id"]
    raw_key = data["key"]

    yield {"id": key_id, "key": raw_key, "scopes": data["scopes"]}

    # 清理
    await test_client.delete(f"/api/apikeys/{key_id}", headers=admin_headers)


@pytest.fixture
async def disabled_api_key(test_client: httpx.AsyncClient, admin_headers: dict[str, str]):
    """创建已禁用的 API Key"""
    # 创建 API Key
    response = await test_client.post(
        "/api/apikeys",
        json={
            "name": "pytest_open_api_test_disabled",
            "description": "Test disabled API Key",
            "scopes": ["knowledge:list", "knowledge:read"],
            "expires_days": 1,
        },
        headers=admin_headers,
    )
    assert response.status_code == 201, f"Failed to create API Key: {response.text}"
    data = response.json()
    key_id = data["id"]
    raw_key = data["key"]

    # 禁用 API Key
    toggle_response = await test_client.put(f"/api/apikeys/{key_id}/toggle", headers=admin_headers)
    assert toggle_response.status_code == 200, f"Failed to disable API Key: {toggle_response.text}"
    assert toggle_response.json()["is_active"] is False

    yield {"id": key_id, "key": raw_key, "scopes": data["scopes"]}

    # 清理
    await test_client.delete(f"/api/apikeys/{key_id}", headers=admin_headers)


# =============================================================================
# === 知识库列表接口测试 ===
# =============================================================================


async def test_list_knowledge_bases_with_valid_key(
    test_client: httpx.AsyncClient,
    api_key_with_all_scopes: dict,
    knowledge_database: dict,
):
    """测试使用有效 API Key 获取知识库列表

    Validates: Requirements 6.2.3
    """
    headers = {"Authorization": f"Bearer {api_key_with_all_scopes['key']}"}
    response = await test_client.get("/api/v1/open/knowledge/databases", headers=headers)

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    data = response.json()
    assert "databases" in data
    assert "total" in data
    assert isinstance(data["databases"], list)
    assert data["total"] >= 0


async def test_list_knowledge_bases_without_auth(test_client: httpx.AsyncClient):
    """测试无认证访问知识库列表接口返回 401"""
    response = await test_client.get("/api/v1/open/knowledge/databases")

    assert response.status_code == 401
    assert "Missing API key" in response.json()["detail"]


async def test_list_knowledge_bases_with_invalid_key(test_client: httpx.AsyncClient):
    """测试使用无效 API Key 返回 401"""
    headers = {"Authorization": "Bearer yk_invalid_key_12345678901234567890"}
    response = await test_client.get("/api/v1/open/knowledge/databases", headers=headers)

    assert response.status_code == 401
    assert "Invalid API key" in response.json()["detail"]


async def test_list_knowledge_bases_with_disabled_key(
    test_client: httpx.AsyncClient,
    disabled_api_key: dict,
):
    """测试使用已禁用的 API Key 返回 403

    Property 7: 禁用密钥返回 403
    """
    headers = {"Authorization": f"Bearer {disabled_api_key['key']}"}
    response = await test_client.get("/api/v1/open/knowledge/databases", headers=headers)

    assert response.status_code == 403
    assert "disabled" in response.json()["detail"].lower()


# =============================================================================
# === 知识库查询接口测试 ===
# =============================================================================


async def test_query_knowledge_base_with_valid_key(
    test_client: httpx.AsyncClient,
    api_key_with_all_scopes: dict,
    knowledge_database: dict,
):
    """测试使用有效 API Key 查询知识库

    Validates: Requirements 6.2.1
    """
    db_id = knowledge_database["db_id"]
    headers = {"Authorization": f"Bearer {api_key_with_all_scopes['key']}"}
    response = await test_client.post(
        f"/api/v1/open/knowledge/databases/{db_id}/query",
        json={"query": "test query", "top_k": 5},
        headers=headers,
    )

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    data = response.json()
    assert "result" in data
    assert "status" in data
    assert data["status"] == "success"


async def test_query_nonexistent_knowledge_base(
    test_client: httpx.AsyncClient,
    api_key_with_all_scopes: dict,
):
    """测试查询不存在的知识库返回 404"""
    headers = {"Authorization": f"Bearer {api_key_with_all_scopes['key']}"}
    response = await test_client.post(
        "/api/v1/open/knowledge/databases/nonexistent_db_id/query",
        json={"query": "test query", "top_k": 5},
        headers=headers,
    )

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


async def test_query_knowledge_base_without_auth(
    test_client: httpx.AsyncClient,
    knowledge_database: dict,
):
    """测试无认证查询知识库返回 401"""
    db_id = knowledge_database["db_id"]
    response = await test_client.post(
        f"/api/v1/open/knowledge/databases/{db_id}/query",
        json={"query": "test query", "top_k": 5},
    )

    assert response.status_code == 401


# =============================================================================
# === 权限范围验证测试 (Property 9) ===
# =============================================================================


async def test_list_without_list_scope_returns_403(
    test_client: httpx.AsyncClient,
    api_key_read_only: dict,
):
    """测试无 knowledge:list 权限访问列表接口返回 403

    Property 9: 权限范围验证
    Validates: Requirements 6.1.3
    """
    headers = {"Authorization": f"Bearer {api_key_read_only['key']}"}
    response = await test_client.get("/api/v1/open/knowledge/databases", headers=headers)

    assert response.status_code == 403
    assert "permissions" in response.json()["detail"].lower()


async def test_query_without_read_scope_returns_403(
    test_client: httpx.AsyncClient,
    api_key_list_only: dict,
    knowledge_database: dict,
):
    """测试无 knowledge:read 权限查询知识库返回 403

    Property 9: 权限范围验证
    Validates: Requirements 6.1.3
    """
    db_id = knowledge_database["db_id"]
    headers = {"Authorization": f"Bearer {api_key_list_only['key']}"}
    response = await test_client.post(
        f"/api/v1/open/knowledge/databases/{db_id}/query",
        json={"query": "test query", "top_k": 5},
        headers=headers,
    )

    assert response.status_code == 403
    assert "permissions" in response.json()["detail"].lower()


async def test_list_with_list_scope_succeeds(
    test_client: httpx.AsyncClient,
    api_key_list_only: dict,
):
    """测试有 knowledge:list 权限可以访问列表接口

    Property 9: 权限范围验证
    """
    headers = {"Authorization": f"Bearer {api_key_list_only['key']}"}
    response = await test_client.get("/api/v1/open/knowledge/databases", headers=headers)

    assert response.status_code == 200


async def test_query_with_read_scope_succeeds(
    test_client: httpx.AsyncClient,
    api_key_read_only: dict,
    knowledge_database: dict,
):
    """测试有 knowledge:read 权限可以查询知识库

    Property 9: 权限范围验证
    """
    db_id = knowledge_database["db_id"]
    headers = {"Authorization": f"Bearer {api_key_read_only['key']}"}
    response = await test_client.post(
        f"/api/v1/open/knowledge/databases/{db_id}/query",
        json={"query": "test query", "top_k": 5},
        headers=headers,
    )

    assert response.status_code == 200


# =============================================================================
# === Authorization 格式验证测试 ===
# =============================================================================


async def test_invalid_auth_format_returns_401(test_client: httpx.AsyncClient):
    """测试无效的 Authorization 格式返回 401"""
    # 缺少 Bearer 前缀
    headers = {"Authorization": "yk_some_key_12345678901234567890123"}
    response = await test_client.get("/api/v1/open/knowledge/databases", headers=headers)

    assert response.status_code == 401
    assert "Invalid authorization format" in response.json()["detail"]


async def test_malformed_bearer_token_returns_401(test_client: httpx.AsyncClient):
    """测试格式错误的 Bearer token 返回 401"""
    # 使用 Basic 而非 Bearer
    headers = {"Authorization": "Basic yk_some_key_12345678901234567890123"}
    response = await test_client.get("/api/v1/open/knowledge/databases", headers=headers)

    assert response.status_code == 401
    assert "Invalid authorization format" in response.json()["detail"]
