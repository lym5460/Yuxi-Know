"""豆包端到端实时语音大模型 API 客户端

实现豆包 Realtime API 的二进制协议封装。
文档: https://www.volcengine.com/docs/6561/1329505
"""

import asyncio
import json
import struct
import uuid
from dataclasses import dataclass
from enum import IntEnum

import websockets

from src.utils import logger


class EventID(IntEnum):
    """事件 ID 定义"""

    # 客户端事件
    START_CONNECTION = 1
    FINISH_CONNECTION = 2
    START_SESSION = 100
    FINISH_SESSION = 102
    TASK_REQUEST = 200  # 上传音频
    SAY_HELLO = 300
    CHAT_TTS_TEXT = 500
    CHAT_TEXT_QUERY = 501
    CHAT_RAG_TEXT = 502

    # 服务端事件
    CONNECTION_STARTED = 50
    CONNECTION_FAILED = 51
    CONNECTION_FINISHED = 52
    SESSION_STARTED = 150
    SESSION_FINISHED = 152
    SESSION_FAILED = 153
    USAGE_RESPONSE = 154
    TTS_SENTENCE_START = 350
    TTS_SENTENCE_END = 351
    TTS_RESPONSE = 352
    TTS_ENDED = 359
    ASR_INFO = 450
    ASR_RESPONSE = 451
    ASR_ENDED = 459
    CHAT_RESPONSE = 550
    CHAT_TEXT_QUERY_CONFIRMED = 553
    CHAT_ENDED = 559
    DIALOG_COMMON_ERROR = 599


class MessageType(IntEnum):
    """消息类型"""

    FULL_CLIENT_REQUEST = 0b0001
    FULL_SERVER_RESPONSE = 0b1001
    AUDIO_ONLY_REQUEST = 0b0010
    AUDIO_ONLY_RESPONSE = 0b1011
    ERROR_INFORMATION = 0b1111


@dataclass
class DoubaoConfig:
    """豆包 Realtime API 配置"""

    app_id: str
    access_key: str
    model: str = "O"
    voice: str = "zh_female_vv_jupiter_bigtts"
    bot_name: str = "语析助手"
    system_role: str = ""
    speaking_style: str = ""
    end_smooth_window_ms: int = 1500


class DoubaoRealtimeClient:
    """豆包端到端实时语音客户端"""

    WS_URL = "wss://openspeech.bytedance.com/api/v3/realtime/dialogue"

    def __init__(self, config: DoubaoConfig):
        self.config = config
        self.ws = None
        self.session_id = None
        self.connect_id = None
        self._connected = False

    def _build_header(
        self,
        msg_type: MessageType,
        msg_flags: int = 0b0100,
        serialization: int = 0b0001,
        compression: int = 0b0000,
    ) -> bytes:
        """构建 4 字节 header"""
        byte0 = 0b0001_0001  # protocol version 1, header size 1 (4 bytes)
        byte1 = (msg_type << 4) | msg_flags
        byte2 = (serialization << 4) | compression
        byte3 = 0x00
        return bytes([byte0, byte1, byte2, byte3])

    def _build_event_frame(self, event_id: int, payload: dict | None = None, session_id: str | None = None) -> bytes:
        """构建事件帧

        根据豆包文档，帧结构为:
        - header (4 bytes)
        - event ID (4 bytes)
        - session ID size + session ID (仅 Session 类事件需要)
        - payload size + payload
        """
        # Header: msg_type=FULL_CLIENT_REQUEST, flags=0b0100 (携带 event)
        header = self._build_header(MessageType.FULL_CLIENT_REQUEST, msg_flags=0b0100)

        # Event ID (4 bytes)
        event_bytes = struct.pack(">I", event_id)

        # Payload
        if payload:
            payload_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        else:
            payload_bytes = b"{}"
        payload_size = struct.pack(">I", len(payload_bytes))

        # Connect 类事件 (1, 2) 不需要 session ID
        if event_id in (EventID.START_CONNECTION, EventID.FINISH_CONNECTION):
            return header + event_bytes + payload_size + payload_bytes

        # Session 类事件需要 session ID
        if session_id:
            session_bytes = session_id.encode("utf-8")
            session_size = struct.pack(">I", len(session_bytes))
            session_part = session_size + session_bytes
        else:
            session_part = struct.pack(">I", 0)

        return header + event_bytes + session_part + payload_size + payload_bytes

    def _build_audio_frame(self, audio_data: bytes, session_id: str) -> bytes:
        """构建音频帧"""
        # Header: msg_type=AUDIO_ONLY_REQUEST, flags=0b0100, serialization=RAW
        header = self._build_header(MessageType.AUDIO_ONLY_REQUEST, msg_flags=0b0100, serialization=0b0000)

        # Event ID
        event_bytes = struct.pack(">I", EventID.TASK_REQUEST)

        # Session ID
        session_bytes = session_id.encode("utf-8")
        session_size = struct.pack(">I", len(session_bytes))

        # Audio payload
        payload_size = struct.pack(">I", len(audio_data))

        return header + event_bytes + session_size + session_bytes + payload_size + audio_data

    def _parse_response(self, data: bytes) -> dict:
        """解析服务端响应"""
        if len(data) < 4:
            return {"error": "数据太短"}

        try:
            # 解析 header
            byte1 = data[1]
            msg_type = (byte1 >> 4) & 0x0F
            msg_flags = byte1 & 0x0F

            byte2 = data[2]
            serialization = (byte2 >> 4) & 0x0F

            offset = 4
            result = {"msg_type": msg_type, "msg_flags": msg_flags}

            # 解析 event ID (如果 flags 包含 0b0100)
            if msg_flags & 0b0100:
                if offset + 4 > len(data):
                    return {"error": "无法解析 event ID"}
                event_id = struct.unpack(">I", data[offset : offset + 4])[0]
                result["event_id"] = event_id
                offset += 4

            # 解析 session ID
            if offset + 4 > len(data):
                return result
            session_id_size = struct.unpack(">I", data[offset : offset + 4])[0]
            offset += 4
            if session_id_size > 0 and offset + session_id_size <= len(data):
                try:
                    result["session_id"] = data[offset : offset + session_id_size].decode("utf-8")
                except UnicodeDecodeError:
                    result["session_id"] = data[offset : offset + session_id_size].hex()
                offset += session_id_size

            # 解析 payload
            if offset + 4 > len(data):
                return result
            payload_size = struct.unpack(">I", data[offset : offset + 4])[0]
            offset += 4

            if payload_size > 0 and offset + payload_size <= len(data):
                payload_data = data[offset : offset + payload_size]
                # 音频数据直接返回
                if msg_type == MessageType.AUDIO_ONLY_RESPONSE:
                    result["audio_data"] = payload_data
                elif serialization == 0b0001:  # JSON
                    try:
                        result["payload"] = json.loads(payload_data.decode("utf-8"))
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        result["payload_raw"] = payload_data
                else:
                    result["payload_raw"] = payload_data

            return result
        except Exception as e:
            logger.error(f"解析响应失败: {e}, 原始数据: {data[:50].hex()}")
            return {"error": str(e)}

    async def connect(self) -> bool:
        """建立 WebSocket 连接"""
        headers = {
            "X-Api-App-ID": self.config.app_id,
            "X-Api-Access-Key": self.config.access_key,
            "X-Api-Resource-Id": "volc.speech.dialog",
            "X-Api-App-Key": "PlgvMymc7f3tQnJ6",
            "X-Api-Connect-Id": str(uuid.uuid4()),
        }

        try:
            logger.debug(f"正在连接豆包 Realtime: {self.WS_URL}")
            self.ws = await websockets.connect(self.WS_URL, additional_headers=headers, ping_interval=30)
            self.connect_id = headers["X-Api-Connect-Id"]
            logger.debug(f"WebSocket 连接已建立，发送 StartConnection")

            # 发送 StartConnection
            frame = self._build_event_frame(EventID.START_CONNECTION)
            await self.ws.send(frame)
            logger.debug(f"已发送 StartConnection 帧: {len(frame)} bytes")

            # 等待 ConnectionStarted (二进制响应)
            response = await self.ws.recv()
            logger.debug(f"收到响应类型: {type(response)}, 长度: {len(response) if response else 0}")
            if isinstance(response, str):
                response = response.encode("latin-1")  # 使用 latin-1 保留原始字节
            result = self._parse_response(response)
            logger.debug(f"解析结果: {result}")
            if result.get("event_id") == EventID.CONNECTION_STARTED:
                self._connected = True
                logger.info(f"豆包 Realtime 连接成功: connect_id={self.connect_id}")
                return True
            else:
                logger.error(f"连接失败: {result}")
                return False
        except Exception as e:
            logger.error(f"WebSocket 连接失败: {e}", exc_info=True)
            return False

    async def start_session(self, dialog_id: str | None = None) -> str | None:
        """启动会话"""
        if not self._connected:
            return None

        self.session_id = str(uuid.uuid4())

        payload = {
            "dialog": {
                "bot_name": self.config.bot_name,
                "system_role": self.config.system_role,
                "speaking_style": self.config.speaking_style,
                "dialog_id": dialog_id or "",
                "extra": {
                    "model": self.config.model,
                    "end_smooth_window_ms": self.config.end_smooth_window_ms,
                },
            },
            "tts": {
                "speaker": self.config.voice,
                "audio_config": {
                    "channel": 1,
                    "format": "pcm_s16le",
                    "sample_rate": 24000,
                },
            },
        }

        frame = self._build_event_frame(EventID.START_SESSION, payload, self.session_id)
        await self.ws.send(frame)

        # 等待 SessionStarted (二进制响应)
        response = await self.ws.recv()
        if isinstance(response, str):
            response = response.encode("utf-8")
        result = self._parse_response(response)
        if result.get("event_id") == EventID.SESSION_STARTED:
            dialog_id = result.get("payload", {}).get("dialog_id", "")
            logger.info(f"豆包会话启动成功: session_id={self.session_id}, dialog_id={dialog_id}")
            return self.session_id
        else:
            logger.error(f"会话启动失败: {result}")
            return None

    async def send_audio(self, audio_data: bytes):
        """发送音频数据"""
        if not self.session_id:
            return
        frame = self._build_audio_frame(audio_data, self.session_id)
        await self.ws.send(frame)

    async def send_rag_text(self, rag_results: list[dict]):
        """发送外部 RAG 结果

        Args:
            rag_results: [{"title": "xxx", "content": "xxx"}, ...]
        """
        if not self.session_id:
            return

        payload = {"external_rag": json.dumps(rag_results, ensure_ascii=False)}
        frame = self._build_event_frame(EventID.CHAT_RAG_TEXT, payload, self.session_id)
        await self.ws.send(frame)
        logger.debug(f"发送 RAG 结果: {len(rag_results)} 条")

    async def finish_session(self, wait_for_confirmation: bool = True):
        """结束会话

        Args:
            wait_for_confirmation: 是否等待服务端确认会话已结束
        """
        if not self.session_id:
            return

        session_id = self.session_id
        self.session_id = None  # 先清除，防止重复调用

        frame = self._build_event_frame(EventID.FINISH_SESSION, {}, session_id)
        await self.ws.send(frame)
        logger.debug(f"已发送 FinishSession: session_id={session_id}")

        if wait_for_confirmation:
            # 持续等待直到收到 SessionFinished 事件
            try:
                while True:
                    data = await asyncio.wait_for(self.ws.recv(), timeout=10)
                    if isinstance(data, str):
                        data = data.encode("utf-8")
                    result = self._parse_response(data)
                    event_id = result.get("event_id")

                    if event_id == EventID.SESSION_FINISHED:
                        logger.info(f"会话已结束确认: session_id={session_id}")
                        break
                    elif event_id == EventID.SESSION_FAILED:
                        logger.warning(f"会话结束失败: {result.get('payload', {})}")
                        break
                    # 其他事件（TTS_RESPONSE、CHAT_RESPONSE 等）继续等待
                    logger.debug(f"等待会话结束，收到事件: {event_id}")
            except TimeoutError:
                logger.warning(f"等待会话结束超时: session_id={session_id}")
            except Exception as e:
                logger.warning(f"等待会话结束异常: {e}")

    async def close(self):
        """关闭连接"""
        if self.ws:
            try:
                frame = self._build_event_frame(EventID.FINISH_CONNECTION)
                await self.ws.send(frame)
                await self.ws.close()
            except Exception:
                pass
            self.ws = None
            self._connected = False

    async def receive(self) -> dict | None:
        """接收服务端消息"""
        if not self.ws:
            return None
        try:
            data = await asyncio.wait_for(self.ws.recv(), timeout=60)
            if isinstance(data, str):
                data = data.encode("utf-8")
            return self._parse_response(data)
        except TimeoutError:
            return None
        except websockets.exceptions.ConnectionClosed:
            self._connected = False
            return None

    @property
    def is_connected(self) -> bool:
        return self._connected and self.ws is not None
