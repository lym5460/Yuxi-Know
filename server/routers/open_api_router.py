"""Open API Router - 开放接口路由

提供第三方应用通过 API Key 访问的开放接口。

路由前缀: /api/v1/open
认证方式: Bearer Token (API Key)

路由:
- GET /api/v1/open/knowledge/databases - 获取知识库列表（需要 knowledge:list 权限）
- POST /api/v1/open/knowledge/databases/{db_id}/query - 查询知识库（需要 knowledge:read 权限）
- POST /api/v1/open/retrieval - Dify 外部知识库兼容接口（需要 knowledge:read 权限）
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from server.utils.apikey_auth import require_scopes
from src import knowledge_base
from src.storage.postgres.models_business import APIKey
from src.utils import logger

open_api = APIRouter(prefix="/v1/open", tags=["open-api"])


# =============================================================================
# === 响应模型 ===
# =============================================================================


class KnowledgeBaseInfo(BaseModel):
    """知识库信息"""

    db_id: str = Field(..., description="知识库ID")
    name: str = Field(..., description="知识库名称")
    description: str = Field("", description="知识库描述")
    kb_type: str = Field("lightrag", description="知识库类型")
    row_count: int = Field(0, description="文档数量")


class KnowledgeBaseListResponse(BaseModel):
    """知识库列表响应"""

    databases: list[KnowledgeBaseInfo] = Field(..., description="知识库列表")
    total: int = Field(..., description="总数")


class QueryRequest(BaseModel):
    """知识库查询请求"""

    query: str = Field(..., min_length=1, description="查询文本")
    top_k: int = Field(5, ge=1, le=50, description="返回结果数量")


class QueryResultItem(BaseModel):
    """单个查询结果项"""

    content: str = Field(..., description="内容")
    source: str = Field("", description="来源")
    score: float = Field(0.0, description="相关度分数")


class QueryResult(BaseModel):
    """知识库查询结果"""

    results: list[QueryResultItem] = Field(default_factory=list, description="查询结果列表")
    total: int = Field(0, description="结果数量")
    status: str = Field("success", description="状态")


# --- Dify 外部知识库兼容模型 ---


class DifyRetrievalSetting(BaseModel):
    """Dify 检索设置"""

    top_k: int = Field(3, ge=1, le=50, description="返回结果数量")
    score_threshold: float = Field(0.5, ge=0.0, le=1.0, description="分数阈值")


class DifyRetrievalRequest(BaseModel):
    """Dify 外部知识库检索请求"""

    knowledge_id: str = Field(..., min_length=1, description="知识库ID")
    query: str = Field(..., min_length=1, description="查询文本")
    retrieval_setting: DifyRetrievalSetting = Field(default_factory=DifyRetrievalSetting)


class DifyRecord(BaseModel):
    """Dify 检索结果记录"""

    content: str = Field(..., description="文本内容")
    score: float = Field(0.0, description="相关度分数")
    title: str = Field("", description="来源标题")
    metadata: dict[str, Any] = Field(default_factory=dict, description="元数据")


class DifyRetrievalResponse(BaseModel):
    """Dify 外部知识库检索响应"""

    records: list[DifyRecord] = Field(default_factory=list, description="检索结果列表")


# =============================================================================
# === 知识库接口 ===
# =============================================================================


@open_api.get("/knowledge/databases", response_model=KnowledgeBaseListResponse)
async def list_knowledge_bases(
    api_key: APIKey = Depends(require_scopes("knowledge:list")),
):
    """获取知识库列表

    返回当前可用的知识库列表，包含基本信息。
    需要 `knowledge:list` 权限。
    """
    try:
        # 获取所有知识库（开放接口不做用户权限过滤，由 API Key 权限控制）
        result = await knowledge_base.get_databases()
        databases = result.get("databases", [])

        # 转换为响应格式
        db_list = [
            KnowledgeBaseInfo(
                db_id=db.get("db_id", ""),
                name=db.get("name", ""),
                description=db.get("description", ""),
                kb_type=db.get("kb_type", "lightrag"),
                row_count=db.get("row_count", 0),
            )
            for db in databases
        ]

        return KnowledgeBaseListResponse(databases=db_list, total=len(db_list))

    except Exception as e:
        logger.error(f"[OpenAPI] 获取知识库列表失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取知识库列表失败: {str(e)}",
        )


@open_api.post("/knowledge/databases/{db_id}/query", response_model=QueryResult)
async def query_knowledge_base(
    db_id: str,
    request: QueryRequest,
    api_key: APIKey = Depends(require_scopes("knowledge:read")),
):
    """查询知识库

    对指定知识库执行查询，返回相关结果。
    需要 `knowledge:read` 权限。

    Args:
        db_id: 知识库ID
        request: 查询请求，包含查询文本和返回数量
    """
    try:
        # 检查知识库是否存在
        db_info = await knowledge_base.get_database_info(db_id)
        if db_info is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Knowledge base not found",
            )

        # 执行查询
        result = await knowledge_base.aquery(
            request.query,
            db_id=db_id,
            top_k=request.top_k,
        )

        items = _parse_query_result(result)
        return QueryResult(results=items, total=len(items), status="success")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[OpenAPI] 知识库查询失败 (db_id={db_id}): {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"知识库查询失败: {str(e)}",
        )


# =============================================================================
# === Dify 外部知识库兼容接口 ===
# =============================================================================


def _parse_query_result(result: Any) -> list[QueryResultItem]:
    """将 knowledge_base.aquery 的返回值解析为统一的 QueryResultItem 列表"""
    if isinstance(result, str):
        return [QueryResultItem(content=result, source="lightrag", score=1.0)] if result else []
    elif isinstance(result, dict):
        data = result.get("data", {}) or {}
        items = []

        for chunk in data.get("chunks", []):
            if isinstance(chunk, dict):
                items.append(
                    QueryResultItem(
                        content=chunk.get("content", ""),
                        source=chunk.get("file_path", chunk.get("source", "")),
                        score=chunk.get("score", 0.0),
                    )
                )
            elif isinstance(chunk, str):
                items.append(QueryResultItem(content=chunk, source="lightrag", score=1.0))

        if not items:
            for entity in data.get("entities", [])[:5]:
                if isinstance(entity, dict):
                    name = entity.get("entity_name", "")
                    desc = entity.get("description", "")
                    if name and desc:
                        items.append(
                            QueryResultItem(
                                content=f"[{name}] {desc}",
                                source=entity.get("file_path", "graph"),
                                score=1.0,
                            )
                        )
        return items
    elif isinstance(result, list):
        return [
            QueryResultItem(
                content=item.get("content", ""),
                source=item.get("source", ""),
                score=item.get("distance", item.get("score", 0.0)),
            )
            for item in result
        ]
    return []


@open_api.post("/retrieval", response_model=DifyRetrievalResponse)
async def dify_retrieval(
    request: DifyRetrievalRequest,
    api_key: APIKey = Depends(require_scopes("knowledge:read")),
):
    """Dify 外部知识库兼容接口

    遵循 Dify External Knowledge API 规范，使第三方平台可以通过标准接口检索本系统的知识库。

    请求体:
        knowledge_id: 知识库ID
        query: 查询文本
        retrieval_setting: 检索设置（top_k, score_threshold）
    """
    db_id = request.knowledge_id
    try:
        db_info = await knowledge_base.get_database_info(db_id)
        if db_info is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Knowledge base not found",
            )

        result = await knowledge_base.aquery(
            request.query,
            db_id=db_id,
            top_k=request.retrieval_setting.top_k,
        )

        items = _parse_query_result(result)

        # 按 score_threshold 过滤并转换为 Dify 格式
        score_threshold = request.retrieval_setting.score_threshold
        records = [
            DifyRecord(
                content=item.content,
                score=item.score,
                title=item.source,
                metadata={"source": item.source},
            )
            for item in items
            if item.score >= score_threshold
        ]

        return DifyRetrievalResponse(records=records)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[OpenAPI] Dify 知识库检索失败 (knowledge_id={db_id}): {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"知识库检索失败: {str(e)}",
        )
