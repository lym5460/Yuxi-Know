"""Voice Session Manager.

管理 WebSocket 连接和语音会话状态。

Validates: Requirements 6.1, 6.2, 6.3, 6.4, 6.6
"""

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum

from src.utils.logging_config import logger


class SessionState(str, Enum):
    """会话状态"""
    IDLE = "idle"
    LISTENING = "listening"
    PROCESSING = "processing"
    SPEAKING = "speaking"


@dataclass
class VoiceSession:
    """语音会话"""
    session_id: str
    user_id: str
    agent_id: str
    thread_id: str | None = None
    state: SessionState = SessionState.IDLE
    created_at: float = field(default_factory=time.time)
    last_activity: float = field(default_factory=time.time)
    # 运行时配置
    asr_provider: str = "openai"
    tts_provider: str = "edge-tts"
    tts_voice: str = "zh-CN-XiaoxiaoNeural"
    tts_speed: float = 1.0
    vad_threshold: float = 0.5
    interrupt_enabled: bool = True

    def touch(self):
        """更新最后活动时间"""
        self.last_activity = time.time()

    def is_expired(self, timeout: float) -> bool:
        """检查会话是否超时"""
        return (time.time() - self.last_activity) > timeout


class VoiceSessionManager:
    """语音会话管理器
    
    管理多个并发语音会话，处理会话超时。
    """

    def __init__(self, session_timeout: float = 300.0):
        self.sessions: dict[str, VoiceSession] = {}
        self.session_timeout = session_timeout
        self._cleanup_task: asyncio.Task | None = None
        self._lock = asyncio.Lock()

    async def start(self):
        """启动会话管理器"""
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info("VoiceSessionManager started")

    async def stop(self):
        """停止会话管理器"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        logger.info("VoiceSessionManager stopped")

    async def create_session(
        self,
        session_id: str,
        user_id: str,
        agent_id: str,
        thread_id: str | None = None,
    ) -> VoiceSession:
        """创建新会话"""
        async with self._lock:
            session = VoiceSession(
                session_id=session_id,
                user_id=user_id,
                agent_id=agent_id,
                thread_id=thread_id,
            )
            self.sessions[session_id] = session
            logger.info(f"Created voice session: {session_id}")
            return session

    async def get_session(self, session_id: str) -> VoiceSession | None:
        """获取会话"""
        return self.sessions.get(session_id)

    async def remove_session(self, session_id: str) -> None:
        """移除会话"""
        async with self._lock:
            if session_id in self.sessions:
                del self.sessions[session_id]
                logger.info(f"Removed voice session: {session_id}")

    async def update_state(self, session_id: str, state: SessionState) -> None:
        """更新会话状态"""
        session = self.sessions.get(session_id)
        if session:
            session.state = state
            session.touch()

    async def _cleanup_loop(self):
        """定期清理超时会话"""
        while True:
            try:
                await asyncio.sleep(60)  # 每分钟检查一次
                await self._cleanup_expired()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Session cleanup error: {e}")

    async def _cleanup_expired(self):
        """清理超时会话"""
        async with self._lock:
            expired = [
                sid for sid, s in self.sessions.items()
                if s.is_expired(self.session_timeout)
            ]
            for sid in expired:
                del self.sessions[sid]
                logger.info(f"Expired voice session removed: {sid}")


# 全局实例
voice_session_manager = VoiceSessionManager()
