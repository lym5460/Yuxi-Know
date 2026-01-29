"""
语音交互 WebSocket 路由器 - 豆包端到端模式

使用豆包 Realtime API 实现语音到语音的实时对话。
支持知识库 RAG 检索增强。
"""

import asyncio
import base64
import os
import uuid

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect, status
from pydantic import BaseModel, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from server.utils.auth_middleware import get_required_user
from server.utils.auth_utils import AuthUtils
from src.agents import agent_manager
from src.repositories.agent_config_repository import AgentConfigRepository
from src.repositories.conversation_repository import ConversationRepository
from src.services.voice.doubao_realtime import DoubaoConfig, DoubaoRealtimeClient, EventID
from src.storage.postgres.manager import pg_manager
from src.storage.postgres.models_business import User
from src.utils.logging_config import logger


# =============================================================================
# 消息协议模型
# =============================================================================


class ClientMessageType(str):
    AUDIO = "audio"
    CONTROL = "control"


class ControlAction(str):
    START = "start"
    STOP = "stop"
    INTERRUPT = "interrupt"


class ClientMessage(BaseModel):
    type: str
    audio_data: str | None = None
    action: str | None = None


class ServerMessageType(str):
    TRANSCRIPTION = "transcription"
    RESPONSE = "response"
    RESPONSE_END = "response_end"
    AUDIO = "audio"
    AUDIO_END = "audio_end"
    STATUS = "status"
    ERROR = "error"


class VoiceStatus(str):
    LISTENING = "listening"
    PROCESSING = "processing"
    SPEAKING = "speaking"
    IDLE = "idle"


class ServerMessage(BaseModel):
    type: str
    text: str | None = None
    is_final: bool | None = None
    audio_data: str | None = None
    status: str | None = None
    error: str | None = None


class VoiceMessageRequest(BaseModel):
    """语音消息请求模型"""

    role: str  # 'user' or 'assistant'
    content: str


# =============================================================================
# 辅助函数
# =============================================================================


def validate_token(token: str | None) -> dict | None:
    if not token:
        return None
    try:
        return AuthUtils.verify_access_token(token)
    except ValueError:
        return None


async def send_message(websocket: WebSocket, msg: ServerMessage) -> None:
    await websocket.send_json(msg.model_dump(exclude_none=True))


async def send_error(websocket: WebSocket, error_message: str) -> None:
    await send_message(websocket, ServerMessage(type=ServerMessageType.ERROR, error=error_message))


async def send_status(websocket: WebSocket, voice_status: str) -> None:
    await send_message(websocket, ServerMessage(type=ServerMessageType.STATUS, status=voice_status))


async def send_transcription(websocket: WebSocket, text: str, is_final: bool = False) -> None:
    await send_message(websocket, ServerMessage(type=ServerMessageType.TRANSCRIPTION, text=text, is_final=is_final))


async def send_response_chunk(websocket: WebSocket, text: str) -> None:
    await send_message(websocket, ServerMessage(type=ServerMessageType.RESPONSE, text=text))


async def send_audio(websocket: WebSocket, audio_data: bytes) -> None:
    await send_message(
        websocket,
        ServerMessage(type=ServerMessageType.AUDIO, audio_data=base64.b64encode(audio_data).decode("utf-8")),
    )


# =============================================================================
# 路由器定义
# =============================================================================

voice = APIRouter(prefix="/voice", tags=["voice"])


# =============================================================================
# 语音消息持久化 API
# =============================================================================


@voice.get("/messages/{thread_id}")
async def get_voice_messages(
    thread_id: str,
    current_user: User = Depends(get_required_user),
):
    """获取语音消息历史"""
    async with pg_manager.get_async_session_context() as db:
        conv_repo = ConversationRepository(db)
        messages = await conv_repo.get_messages_by_thread_id(thread_id)

        # 过滤出语音消息
        voice_messages = []
        for msg in messages:
            if msg.message_type == "voice":
                voice_messages.append({"role": msg.role, "content": msg.content})

        return voice_messages


@voice.post("/messages/{thread_id}")
async def save_voice_message(
    thread_id: str,
    message: VoiceMessageRequest,
    current_user: User = Depends(get_required_user),
):
    """保存语音消息"""
    async with pg_manager.get_async_session_context() as db:
        conv_repo = ConversationRepository(db)

        # 检查会话是否存在
        conversation = await conv_repo.get_conversation_by_thread_id(thread_id)
        if not conversation:
            return {"success": False, "error": "会话不存在"}

        # 保存消息
        await conv_repo.add_message(
            conversation_id=conversation.id,
            role=message.role,
            content=message.content,
            message_type="voice",
        )

        return {"success": True}


@voice.websocket("/ws/voice/{agent_id}")
async def voice_websocket(
    websocket: WebSocket,
    agent_id: str,
    token: str | None = Query(default=None),
):
    """语音交互 WebSocket 端点 - 豆包端到端模式"""
    # 1. 验证 token
    payload = validate_token(token)
    if payload is None:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="认证失败")
        return

    user_id = payload.get("sub")
    if not user_id:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="token 中缺少用户信息")
        return

    # 2. 验证智能体
    agent = agent_manager.get_agent(agent_id)
    if agent is None:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason=f"智能体 {agent_id} 不存在")
        return

    # 3. 接受连接
    await websocket.accept()
    logger.info(f"语音 WebSocket 连接已建立: agent_id={agent_id}, user_id={user_id}")

    # 4. 加载配置
    # 从环境变量获取豆包 API 凭证
    doubao_app_id = os.getenv("DOUBAO_APP_ID", "")
    doubao_access_key = os.getenv("DOUBAO_ACCESS_KEY", "")

    if not doubao_app_id or not doubao_access_key:
        await send_error(websocket, "豆包 API 凭证未配置，请设置 DOUBAO_APP_ID 和 DOUBAO_ACCESS_KEY 环境变量")
        await websocket.close()
        return

    # 默认配置
    doubao_model = "O"
    doubao_voice = "zh_female_vv_jupiter_bigtts"
    bot_name = "语析助手"
    system_role = "你是一个友好的智能助手，擅长回答各种问题。回答要简洁明了，适合语音播报。"
    speaking_style = ""
    silence_duration_ms = 1500
    interrupt_enabled = True
    session_timeout = 300
    knowledges = []

    # 从数据库加载用户配置
    try:
        async with pg_manager.get_async_session_context() as db:
            from sqlalchemy import select

            from src.storage.postgres.models_business import User

            result = await db.execute(select(User.department_id).where(User.id == int(user_id)))
            department_id = result.scalar_one_or_none()

            if department_id:
                config_repo = AgentConfigRepository(db)
                config_item = await config_repo.get_default(department_id=department_id, agent_id=agent_id)
                if config_item and config_item.config_json:
                    ctx = config_item.config_json.get("context", {})
                    doubao_model = ctx.get("doubao_model", doubao_model)
                    doubao_voice = ctx.get("doubao_voice", doubao_voice)
                    bot_name = ctx.get("bot_name", bot_name)
                    system_role = ctx.get("system_role", system_role)
                    speaking_style = ctx.get("speaking_style", speaking_style)
                    silence_duration_ms = ctx.get("silence_duration_ms", silence_duration_ms)
                    interrupt_enabled = ctx.get("interrupt_enabled", interrupt_enabled)
                    session_timeout = ctx.get("session_timeout", session_timeout)
                    knowledges = ctx.get("knowledges", [])
                    logger.info(f"已加载智能体配置: model={doubao_model}, voice={doubao_voice}")
    except Exception as e:
        logger.warning(f"加载智能体配置失败，使用默认配置: {e}")

    # 5. 创建豆包客户端
    config = DoubaoConfig(
        app_id=doubao_app_id,
        access_key=doubao_access_key,
        model=doubao_model,
        voice=doubao_voice,
        bot_name=bot_name,
        system_role=system_role,
        speaking_style=speaking_style,
        end_smooth_window_ms=silence_duration_ms,
    )
    doubao_client = DoubaoRealtimeClient(config)

    # 6. 会话状态
    is_listening = False
    dialog_id = str(uuid.uuid4())
    last_activity_time = asyncio.get_event_loop().time()
    receive_task: asyncio.Task | None = None
    timeout_task: asyncio.Task | None = None
    current_question_id: str | None = None
    current_asr_text: str = ""  # 累积 ASR 识别文本用于 RAG 检索

    await send_status(websocket, VoiceStatus.IDLE)

    async def check_session_timeout():
        """检测会话超时"""
        nonlocal last_activity_time
        while True:
            await asyncio.sleep(30)
            if asyncio.get_event_loop().time() - last_activity_time > session_timeout:
                logger.info(f"语音会话超时: agent_id={agent_id}")
                await send_error(websocket, "会话超时，请重新连接")
                await websocket.close()
                break

    async def handle_doubao_events():
        """处理豆包服务端事件"""
        nonlocal current_question_id, is_listening, current_asr_text

        while doubao_client.is_connected:
            result = await doubao_client.receive()
            if result is None:
                continue

            event_id = result.get("event_id")
            payload = result.get("payload", {})

            match event_id:
                case EventID.ASR_INFO:
                    # 检测到用户开始说话，可用于打断
                    current_question_id = payload.get("question_id")
                    current_asr_text = ""  # 重置 ASR 文本
                    if interrupt_enabled:
                        await send_status(websocket, VoiceStatus.LISTENING)

                case EventID.ASR_RESPONSE:
                    # ASR 识别结果
                    results = payload.get("results", [])
                    for r in results:
                        text = r.get("text", "")
                        is_interim = r.get("is_interim", True)
                        if text:
                            await send_transcription(websocket, text, is_final=not is_interim)
                            # 累积最终的 ASR 文本用于 RAG 检索
                            if not is_interim:
                                current_asr_text = text

                case EventID.ASR_ENDED:
                    # 用户说话结束
                    logger.info(f"用户说话结束，ASR 文本: {current_asr_text}")
                    await send_status(websocket, VoiceStatus.PROCESSING)

                    # 如果配置了知识库且有 ASR 文本，执行 RAG 检索
                    if knowledges and current_asr_text:
                        await do_rag_retrieval(doubao_client, knowledges, current_asr_text)

                case EventID.TTS_SENTENCE_START:
                    # TTS 开始合成
                    text = payload.get("text", "")
                    if text:
                        await send_response_chunk(websocket, text)
                    await send_status(websocket, VoiceStatus.SPEAKING)

                case EventID.TTS_RESPONSE:
                    # TTS 音频数据
                    audio_data = result.get("audio_data")
                    if audio_data:
                        logger.debug(f"收到 TTS 音频: {len(audio_data)} bytes, 前16字节: {audio_data[:16].hex()}")
                        await send_audio(websocket, audio_data)

                case EventID.TTS_ENDED:
                    # TTS 结束
                    await send_message(websocket, ServerMessage(type=ServerMessageType.AUDIO_END))
                    await send_message(websocket, ServerMessage(type=ServerMessageType.RESPONSE_END))
                    await send_status(websocket, VoiceStatus.IDLE if not is_listening else VoiceStatus.LISTENING)

                case EventID.CHAT_RESPONSE:
                    # 模型回复文本
                    content = payload.get("content", "")
                    if content:
                        await send_response_chunk(websocket, content)

                case EventID.SESSION_FAILED | EventID.DIALOG_COMMON_ERROR:
                    # 错误
                    error_msg = payload.get("error") or payload.get("message", "未知错误")
                    logger.error(f"豆包会话错误: {error_msg}")
                    await send_error(websocket, f"语音服务错误: {error_msg}")

    async def do_rag_retrieval(client: DoubaoRealtimeClient, kb_ids: list[str], query: str):
        """执行知识库检索并发送结果给豆包

        Args:
            client: 豆包客户端
            kb_ids: 知识库 ID 列表
            query: 用户查询文本
        """
        if not query or not kb_ids:
            return

        try:
            from src.knowledge import knowledge_base

            rag_results = []

            for kb_id in kb_ids:
                try:
                    # 执行知识库检索
                    results = await knowledge_base.aquery(query, kb_id, top_k=3)

                    # 转换为豆包 RAG 格式
                    for i, result in enumerate(results):
                        if isinstance(result, dict):
                            content = result.get("content") or result.get("text", "")
                            title = result.get("title") or result.get("filename") or f"文档片段 {i + 1}"
                        else:
                            content = str(result)
                            title = f"文档片段 {i + 1}"

                        if content:
                            rag_results.append({"title": title, "content": content})

                except Exception as e:
                    logger.warning(f"知识库 {kb_id} 检索失败: {e}")
                    continue

            # 发送 RAG 结果给豆包
            if rag_results:
                logger.info(f"发送 RAG 结果: {len(rag_results)} 条")
                await client.send_rag_text(rag_results)
            else:
                logger.debug("RAG 检索无结果")

        except Exception as e:
            logger.warning(f"RAG 检索失败: {e}")

    # 启动超时检测
    timeout_task = asyncio.create_task(check_session_timeout())

    try:
        while True:
            raw_data = await websocket.receive_json()

            try:
                message = ClientMessage.model_validate(raw_data)
            except ValidationError as e:
                logger.warning(f"无效的消息格式: {e}")
                await send_error(websocket, f"无效的消息格式: {e}")
                continue

            last_activity_time = asyncio.get_event_loop().time()

            if message.type == ClientMessageType.AUDIO:
                # 转发音频到豆包（持续发送，让豆包自己处理 VAD）
                if message.audio_data and doubao_client.is_connected and doubao_client.session_id:
                    try:
                        pcm_data = base64.b64decode(message.audio_data)
                        await doubao_client.send_audio(pcm_data)
                    except Exception as e:
                        logger.warning(f"音频数据处理失败: {e}")

            elif message.type == ClientMessageType.CONTROL:
                if message.action == ControlAction.START:
                    logger.info(f"开始语音会话: agent_id={agent_id}")

                    # 如果已有会话在运行，直接复用，不重新创建
                    if doubao_client.is_connected and doubao_client.session_id:
                        is_listening = True
                        await send_status(websocket, VoiceStatus.LISTENING)
                        # 确保接收任务在运行
                        if receive_task is None or receive_task.done():
                            receive_task = asyncio.create_task(handle_doubao_events())
                        continue

                    # 先取消已有的接收任务，避免 recv 冲突
                    if receive_task and not receive_task.done():
                        receive_task.cancel()
                        try:
                            await receive_task
                        except asyncio.CancelledError:
                            pass

                    # 连接豆包
                    if not doubao_client.is_connected:
                        if not await doubao_client.connect():
                            await send_error(websocket, "连接豆包服务失败")
                            continue

                    # 如果已有会话，先结束
                    if doubao_client.session_id:
                        await doubao_client.finish_session(wait_for_confirmation=True)

                    # 启动会话
                    session_id = await doubao_client.start_session(dialog_id)
                    if not session_id:
                        await send_error(websocket, "启动豆包会话失败")
                        continue

                    is_listening = True
                    await send_status(websocket, VoiceStatus.LISTENING)

                    # 启动事件处理任务
                    receive_task = asyncio.create_task(handle_doubao_events())

                elif message.action == ControlAction.STOP:
                    logger.info(f"停止语音会话: agent_id={agent_id}")
                    is_listening = False
                    # 不结束豆包会话，让它继续处理并返回结果

                elif message.action == ControlAction.INTERRUPT:
                    if interrupt_enabled:
                        logger.info(f"打断语音会话: agent_id={agent_id}")
                        # 先取消接收任务
                        if receive_task and not receive_task.done():
                            receive_task.cancel()
                            try:
                                await receive_task
                            except asyncio.CancelledError:
                                pass

                        # 结束当前会话（等待服务端确认）
                        if doubao_client.session_id:
                            await doubao_client.finish_session(wait_for_confirmation=True)

                        # 重新启动会话
                        session_id = await doubao_client.start_session(dialog_id)
                        if session_id:
                            is_listening = True
                            await send_status(websocket, VoiceStatus.LISTENING)
                            # 重新启动接收任务
                            receive_task = asyncio.create_task(handle_doubao_events())
                        else:
                            await send_error(websocket, "重新启动会话失败")
                            is_listening = False

    except WebSocketDisconnect:
        logger.info(f"语音 WebSocket 连接已断开: agent_id={agent_id}")
    except Exception as e:
        logger.error(f"语音 WebSocket 处理错误: {e}", exc_info=True)
        try:
            await send_error(websocket, f"服务器内部错误: {str(e)}")
        except Exception:
            pass
    finally:
        # 清理资源
        if timeout_task and not timeout_task.done():
            timeout_task.cancel()
        if receive_task and not receive_task.done():
            receive_task.cancel()
        await doubao_client.close()
        logger.info(f"语音 WebSocket 连接清理完成: agent_id={agent_id}")
