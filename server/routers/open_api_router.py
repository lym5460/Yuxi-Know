"""Open API Router - 开放接口路由

提供第三方应用通过 API Key 访问的开放接口。

路由前缀: /api/v1/open
认证方式: Bearer Token (API Key)

路由:
- GET /api/v1/open/knowledge/databases - 获取知识库列表（需要 knowledge:list 权限）
- POST /api/v1/open/knowledge/databases/{db_id}/query - 查询知识库（需要 knowledge:read 权限）
"""

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

        # 处理不同类型的返回结果
        if isinstance(result, str):
            # 纯字符串结果
            return QueryResult(
                results=[QueryResultItem(content=result, source="lightrag", score=1.0)] if result else [],
                total=1 if result else 0,
                status="success",
            )
        elif isinstance(result, dict):
            # LightRAG 返回字典格式 {"status": "success", "data": {...}}
            data = result.get("data", {}) or {}
            items = []

            # 提取 chunks 内容
            chunks = data.get("chunks", [])
            for chunk in chunks:
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

            # 如果没有 chunks，尝试从 entities 构建摘要
            if not items:
                entities = data.get("entities", [])

                # 构建实体摘要
                for entity in entities[:5]:  # 限制数量
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

            return QueryResult(results=items, total=len(items), status="success")
        elif isinstance(result, list):
            # Milvus 返回列表
            items = [
                QueryResultItem(
                    content=item.get("content", ""),
                    source=item.get("source", ""),
                    score=item.get("distance", item.get("score", 0.0)),
                )
                for item in result
            ]
            return QueryResult(results=items, total=len(items), status="success")
        else:
            return QueryResult(results=[], total=0, status="success")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[OpenAPI] 知识库查询失败 (db_id={db_id}): {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"知识库查询失败: {str(e)}",
        )
