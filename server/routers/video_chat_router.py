"""视频对话路由 - 代理 Memeries Video Chat API"""

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from server.routers.auth_router import get_admin_user
from src.services.memeries_service import get_memeries_service
from src.storage.postgres.models_business import User
from src.utils.logging_config import logger

video_chat = APIRouter(prefix="/video-chat", tags=["Video Chat"])


def _next_session_id() -> str:
    """生成数字格式的 session_id（Memeries 要求 Long 类型）"""
    import time

    return str(int(time.time() * 1000))


class VideoChatRequest(BaseModel):
    db_id: str
    video_nos: list[str | None]
    prompt: str
    session_id: str | None = None


@video_chat.post("/stream")
async def video_chat_stream(
    request: VideoChatRequest,
    current_user: User = Depends(get_admin_user),
):
    """流式视频对话，代理 Memeries chat_stream API"""
    service = get_memeries_service()
    if not service.is_configured():
        raise HTTPException(status_code=503, detail="Memeries 服务未配置")

    # 过滤掉 None 和空字符串
    video_nos = [v for v in request.video_nos if v]
    logger.info(f"Video chat request: raw_video_nos={request.video_nos}, filtered={video_nos}, db_id={request.db_id}")
    if not video_nos:
        raise HTTPException(status_code=400, detail="请至少选择一个视频")

    # session_id 必须是数字格式（Memeries 要求 Long 类型）
    raw_sid = request.session_id or ""
    try:
        session_id = str(int(raw_sid))
    except (ValueError, TypeError):
        session_id = _next_session_id()

    # 注入中文指令
    prompt = f"请用中文回答。\n\n{request.prompt}"

    async def event_generator():
        try:
            async for line in service.chat_stream(
                video_nos=video_nos,
                prompt=prompt,
                session_id=session_id,
                unique_id=request.db_id,
            ):
                yield f"{line}\n"
        except Exception as e:
            logger.error(f"Video chat stream error: {e}")
            err_str = str(e)
            if "SSL" in err_str or "ssl" in err_str:
                msg = "与视频分析服务的连接中断，请点击重试"
            else:
                msg = err_str.replace('"', '\\"')
            yield f'data:{{"type":"error","content":"{msg}"}}\n'

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@video_chat.get("/videos")
async def list_videos(
    db_id: str = Query(..., description="Memeries 知识库 ID"),
    current_user: User = Depends(get_admin_user),
):
    """获取指定知识库的视频列表"""
    service = get_memeries_service()
    if not service.is_configured():
        raise HTTPException(status_code=503, detail="Memeries 服务未配置")

    try:
        result = await service.list_videos(unique_id=db_id, status="PARSE")

        # 用本地 files_meta 中的文件名覆盖 Memeries 返回的原始名称
        from src import knowledge_base

        try:
            kb_instance = knowledge_base._get_or_create_kb_instance("memeries")
            name_map = {
                meta.get("memeries_video_no"): meta.get("filename")
                for meta in kb_instance.files_meta.values()
                if meta.get("memeries_video_no") and meta.get("filename")
            }
            data = result.get("data", result)
            for video in data.get("videos", []):
                local_name = name_map.get(video.get("video_no"))
                if local_name:
                    video["video_name"] = local_name
        except Exception:
            pass  # 查找失败不影响主流程

        return result
    except Exception as e:
        logger.error(f"List videos error: {e}")
        raise HTTPException(status_code=500, detail=f"获取视频列表失败: {e}")
