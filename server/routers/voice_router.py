"""
语音交互 WebSocket 路由器

实现语音智能体的 WebSocket 通信端点，支持双向音频流传输。
支持流式输出、打断和取消功能。
"""

import asyncio
import base64
import os
import re
import uuid
from enum import Enum

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect, status
from langchain.messages import AIMessageChunk, HumanMessage
from pydantic import BaseModel, ValidationError

from server.utils.auth_utils import AuthUtils
from src.agents import agent_manager
from src.services.voice.asr_service import ASRError, create_asr_service
from src.services.voice.tts_service import TTSError, create_tts_service
from src.utils.logging_config import logger


# =============================================================================
# 消息协议模型
# =============================================================================


class ClientMessageType(str, Enum):
    """客户端消息类型"""
    AUDIO = "audio"
    CONTROL = "control"
    CONFIG = "config"


class ControlAction(str, Enum):
    """控制动作类型"""
    START = "start"
    STOP = "stop"
    INTERRUPT = "interrupt"


class VoiceConfigMessage(BaseModel):
    """语音配置消息"""
    asr_provider: str | None = None
    tts_provider: str | None = None
    tts_voice: str | None = None
    tts_speed: float | None = None
    vad_threshold: float | None = None
    interrupt_enabled: bool | None = None


class ClientMessage(BaseModel):
    """客户端发送的消息"""
    type: ClientMessageType
    audio_data: str | None = None
    action: ControlAction | None = None
    config: VoiceConfigMessage | None = None


class ServerMessageType(str, Enum):
    """服务端消息类型"""
    TRANSCRIPTION = "transcription"
    RESPONSE = "response"
    RESPONSE_END = "response_end"
    AUDIO = "audio"
    AUDIO_END = "audio_end"
    STATUS = "status"
    ERROR = "error"
    TOOL_CALL = "tool_call"


class VoiceStatus(str, Enum):
    """语音会话状态"""
    LISTENING = "listening"
    PROCESSING = "processing"
    SPEAKING = "speaking"
    IDLE = "idle"


class ServerMessage(BaseModel):
    """服务端发送的消息"""
    type: ServerMessageType
    text: str | None = None
    is_final: bool | None = None
    audio_data: str | None = None
    status: VoiceStatus | None = None
    error: str | None = None


# =============================================================================
# 辅助函数
# =============================================================================


def validate_token(token: str | None) -> dict | None:
    """验证 WebSocket 连接的 token"""
    if not token:
        return None
    try:
        return AuthUtils.verify_access_token(token)
    except ValueError:
        return None


def parse_client_message(data: dict) -> ClientMessage:
    """解析并验证客户端消息"""
    return ClientMessage.model_validate(data)


async def send_message(websocket: WebSocket, msg: ServerMessage) -> None:
    """发送消息到客户端"""
    await websocket.send_json(msg.model_dump(exclude_none=True))


async def send_error(websocket: WebSocket, error_message: str) -> None:
    """发送错误消息"""
    await send_message(websocket, ServerMessage(type=ServerMessageType.ERROR, error=error_message))


async def send_status(websocket: WebSocket, voice_status: VoiceStatus) -> None:
    """发送状态消息"""
    await send_message(websocket, ServerMessage(type=ServerMessageType.STATUS, status=voice_status))


async def send_transcription(websocket: WebSocket, text: str, is_final: bool = False) -> None:
    """发送转录结果"""
    await send_message(websocket, ServerMessage(type=ServerMessageType.TRANSCRIPTION, text=text, is_final=is_final))


async def send_response_chunk(websocket: WebSocket, text: str) -> None:
    """发送流式响应文本块"""
    await send_message(websocket, ServerMessage(type=ServerMessageType.RESPONSE, text=text))


async def send_response_end(websocket: WebSocket) -> None:
    """发送响应结束标记"""
    await send_message(websocket, ServerMessage(type=ServerMessageType.RESPONSE_END))


async def send_audio(websocket: WebSocket, audio_data: bytes) -> None:
    """发送音频数据"""
    await send_message(websocket, ServerMessage(
        type=ServerMessageType.AUDIO,
        audio_data=base64.b64encode(audio_data).decode("utf-8"),
    ))


async def send_audio_end(websocket: WebSocket) -> None:
    """发送音频结束标记"""
    await send_message(websocket, ServerMessage(type=ServerMessageType.AUDIO_END))


def clean_text_for_tts(text: str) -> str:
    """清理文本，移除不适合 TTS 朗读的格式

    移除 Markdown 格式、HTML 标签、emoji 等，
    使文本更适合语音合成。
    """
    if not text:
        return text

    # 移除代码块 ```...```
    text = re.sub(r"```[\s\S]*?```", "", text)

    # 移除行内代码 `...`
    text = re.sub(r"`([^`]+)`", r"\1", text)

    # 移除 Markdown 链接 [text](url) -> text
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)

    # 移除 Markdown 图片 ![alt](url)
    text = re.sub(r"!\[[^\]]*\]\([^)]+\)", "", text)

    # 移除 HTML 标签
    text = re.sub(r"<[^>]+>", "", text)

    # 移除 Markdown 加粗 **text** 或 __text__
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"__([^_]+)__", r"\1", text)

    # 移除 Markdown 斜体 *text* 或 _text_
    text = re.sub(r"\*([^*]+)\*", r"\1", text)
    text = re.sub(r"(?<!\w)_([^_]+)_(?!\w)", r"\1", text)

    # 移除 Markdown 标题 # ## ### 等
    text = re.sub(r"^#{1,6}\s*", "", text, flags=re.MULTILINE)

    # 移除 Markdown 列表符号 - * + 和数字列表
    text = re.sub(r"^\s*[-*+]\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*\d+\.\s+", "", text, flags=re.MULTILINE)

    # 移除 Markdown 引用 >
    text = re.sub(r"^\s*>\s*", "", text, flags=re.MULTILINE)

    # 移除 Markdown 分隔线 --- *** ___
    text = re.sub(r"^[-*_]{3,}\s*$", "", text, flags=re.MULTILINE)

    # 移除多余的空行
    text = re.sub(r"\n{3,}", "\n\n", text)

    # 移除首尾空白
    text = text.strip()

    return text


# =============================================================================
# 路由器定义
# =============================================================================

voice = APIRouter(prefix="/voice", tags=["voice"])


@voice.websocket("/ws/voice/{agent_id}")
async def voice_websocket(
    websocket: WebSocket,
    agent_id: str,
    token: str | None = Query(default=None),
):
    """语音交互 WebSocket 端点"""
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

    # 4. 初始化服务
    asr_provider = os.getenv("VOICE_ASR_PROVIDER", "local-whisper")
    tts_provider = os.getenv("VOICE_TTS_PROVIDER", "edge-tts")
    tts_voice = os.getenv("VOICE_TTS_VOICE", "zh-CN-XiaoxiaoNeural")
    tts_speed = float(os.getenv("VOICE_TTS_SPEED", "1.0"))

    try:
        asr_service = create_asr_service(asr_provider)
        tts_service = create_tts_service(tts_provider)
        logger.info(f"服务已初始化: ASR={asr_provider}, TTS={tts_provider}")
    except Exception as e:
        logger.error(f"服务初始化失败: {e}")
        await send_error(websocket, f"服务初始化失败: {e}")
        await websocket.close()
        return

    # 5. 会话状态
    audio_buffer = bytearray()
    is_listening = False
    thread_id = str(uuid.uuid4())
    current_task: asyncio.Task | None = None  # 当前正在执行的任务
    is_cancelled = False  # 取消标志

    await send_status(websocket, VoiceStatus.IDLE)

    async def process_and_respond(query: str):
        """处理用户输入并流式响应"""
        nonlocal is_cancelled
        
        try:
            await send_status(websocket, VoiceStatus.PROCESSING)
            
            # 构建输入
            messages = [HumanMessage(content=query)]
            input_context = {"thread_id": thread_id, "user_id": user_id}
            
            logger.info(f"调用智能体: query={query}")
            
            # 流式获取响应
            full_response = ""
            sentence_buffer = ""
            sentence_endings = {"。", "！", "？", ".", "!", "?", "\n"}
            
            async for msg, metadata in agent.stream_messages(messages, input_context=input_context):
                # 在每次迭代开始时检查取消状态
                if is_cancelled:
                    logger.info("任务被取消，停止处理")
                    return
                
                # 只处理 AIMessageChunk 类型的消息
                if isinstance(msg, AIMessageChunk) and msg.content:
                    chunk = msg.content
                    full_response += chunk
                    sentence_buffer += chunk
                    
                    # 再次检查取消状态
                    if is_cancelled:
                        return
                    
                    # 发送文本块
                    await send_response_chunk(websocket, chunk)
                    
                    # 检查是否有完整句子可以合成语音
                    while True:
                        # 在循环中检查取消状态
                        if is_cancelled:
                            return
                        
                        end_pos = -1
                        for i, char in enumerate(sentence_buffer):
                            if char in sentence_endings:
                                end_pos = i
                                break
                        
                        if end_pos == -1:
                            break
                        
                        sentence = sentence_buffer[:end_pos + 1].strip()
                        sentence_buffer = sentence_buffer[end_pos + 1:]
                        
                        if sentence and not is_cancelled:
                            # 清理文本，移除 Markdown 等格式
                            clean_sentence = clean_text_for_tts(sentence)
                            if not clean_sentence:
                                continue
                            
                            # 再次检查取消状态
                            if is_cancelled:
                                return
                            
                            # 合成并发送语音
                            await send_status(websocket, VoiceStatus.SPEAKING)
                            try:
                                audio_data = await tts_service.synthesize(
                                    text=clean_sentence,
                                    voice=tts_voice,
                                    speed=tts_speed,
                                )
                                # 合成后再次检查取消状态
                                if audio_data and not is_cancelled:
                                    await send_audio(websocket, audio_data)
                            except TTSError as e:
                                logger.error(f"TTS 合成失败: {e}")
            
            # 处理剩余的文本
            if sentence_buffer.strip() and not is_cancelled:
                clean_remaining = clean_text_for_tts(sentence_buffer.strip())
                if clean_remaining:
                    await send_status(websocket, VoiceStatus.SPEAKING)
                    try:
                        audio_data = await tts_service.synthesize(
                            text=clean_remaining,
                            voice=tts_voice,
                            speed=tts_speed,
                        )
                        if audio_data and not is_cancelled:
                            await send_audio(websocket, audio_data)
                    except TTSError as e:
                        logger.error(f"TTS 合成失败: {e}")
            
            if not is_cancelled:
                await send_response_end(websocket)
                await send_audio_end(websocket)
                logger.info(f"响应完成: {len(full_response)} 字符")
            
        except asyncio.CancelledError:
            logger.info("任务被取消")
        except Exception as e:
            logger.error(f"处理失败: {e}")
            if not is_cancelled:
                await send_error(websocket, f"处理失败: {e}")
        finally:
            if not is_cancelled:
                await send_status(websocket, VoiceStatus.IDLE)

    def cancel_current_task():
        """取消当前任务"""
        nonlocal current_task, is_cancelled
        if current_task and not current_task.done():
            is_cancelled = True
            current_task.cancel()
            logger.info("已取消当前任务")

    try:
        while True:
            raw_data = await websocket.receive_json()

            try:
                message = parse_client_message(raw_data)
            except ValidationError as e:
                logger.warning(f"无效的消息格式: {e}")
                await send_error(websocket, f"无效的消息格式: {e}")
                continue

            match message.type:
                case ClientMessageType.AUDIO:
                    if message.audio_data and is_listening:
                        try:
                            pcm_data = base64.b64decode(message.audio_data)
                            audio_buffer.extend(pcm_data)
                        except Exception as e:
                            logger.warning(f"音频数据解码失败: {e}")

                case ClientMessageType.CONTROL:
                    if not message.action:
                        continue

                    match message.action:
                        case ControlAction.START:
                            # 取消之前的任务
                            cancel_current_task()
                            is_cancelled = False
                            
                            logger.info(f"开始语音会话: agent_id={agent_id}")
                            is_listening = True
                            audio_buffer.clear()
                            await send_status(websocket, VoiceStatus.LISTENING)

                        case ControlAction.STOP:
                            logger.info(f"停止语音会话: agent_id={agent_id}")
                            is_listening = False
                            
                            # 取消之前的任务
                            cancel_current_task()
                            is_cancelled = False

                            if len(audio_buffer) > 0:
                                try:
                                    # ASR 转录
                                    result = await asr_service.transcribe(bytes(audio_buffer), language="auto")
                                    audio_buffer.clear()

                                    if result.text:
                                        await send_transcription(websocket, result.text, is_final=True)
                                        logger.info(f"转录结果: {result.text}")
                                        
                                        # 启动新任务处理响应
                                        current_task = asyncio.create_task(process_and_respond(result.text))
                                    else:
                                        await send_transcription(websocket, "", is_final=True)
                                        await send_status(websocket, VoiceStatus.IDLE)
                                except ASRError as e:
                                    logger.error(f"ASR 转录失败: {e}")
                                    await send_error(websocket, f"语音识别失败: {e}")
                                    await send_status(websocket, VoiceStatus.IDLE)
                            else:
                                await send_status(websocket, VoiceStatus.IDLE)

                        case ControlAction.INTERRUPT:
                            logger.info(f"打断语音会话: agent_id={agent_id}")
                            # 取消当前任务
                            cancel_current_task()
                            
                            # 清空音频缓冲
                            audio_buffer.clear()
                            
                            # 立即发送监听状态，让前端知道可以开始新的对话
                            await send_status(websocket, VoiceStatus.LISTENING)
                            
                            # 重置取消标志，准备接收新的请求
                            is_cancelled = False
                            is_listening = True

                case ClientMessageType.CONFIG:
                    if message.config:
                        logger.info(f"更新语音配置: {message.config.model_dump(exclude_none=True)}")

    except WebSocketDisconnect:
        logger.info(f"语音 WebSocket 连接已断开: agent_id={agent_id}")
    except Exception as e:
        logger.error(f"语音 WebSocket 处理错误: {e}", exc_info=True)
        try:
            await send_error(websocket, f"服务器内部错误: {str(e)}")
        except Exception:
            pass
    finally:
        # 取消正在执行的任务
        cancel_current_task()
        
        # 清理资源
        if hasattr(asr_service, "close"):
            await asr_service.close()
        logger.info(f"语音 WebSocket 连接清理完成: agent_id={agent_id}")
