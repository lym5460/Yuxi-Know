"""Interrupt Handler.

处理用户打断，当用户在 TTS 播放时说话时停止播放。

Validates: Requirements 5.1, 5.2, 5.3, 5.4, 5.5
"""

import asyncio
from dataclasses import dataclass

from src.utils.logging_config import logger


@dataclass
class InterruptConfig:
    """打断配置"""
    enabled: bool = True
    sensitivity: float = 0.5  # 0.0-1.0


class InterruptHandler:
    """打断处理器
    
    检测用户打断并停止 TTS 播放。
    """

    def __init__(self, config: InterruptConfig | None = None):
        self.config = config or InterruptConfig()
        self._is_tts_playing = False
        self._pending_tasks: list[asyncio.Task] = []
        self._interrupt_event = asyncio.Event()

    @property
    def is_tts_playing(self) -> bool:
        return self._is_tts_playing

    def set_tts_playing(self, playing: bool):
        """设置 TTS 播放状态"""
        self._is_tts_playing = playing
        if not playing:
            self._interrupt_event.clear()

    def check_interrupt(self, speech_detected: bool) -> bool:
        """检查是否应该打断
        
        Args:
            speech_detected: VAD 是否检测到语音
            
        Returns:
            是否应该打断
        """
        if not self.config.enabled:
            return False
        if not self._is_tts_playing:
            return False
        return speech_detected

    async def handle_interrupt(self) -> bool:
        """处理打断
        
        Returns:
            是否成功处理打断
        """
        if not self._is_tts_playing:
            return False

        logger.info("Interrupt detected, stopping TTS")
        
        # 设置打断事件
        self._interrupt_event.set()
        
        # 取消待处理的 TTS 任务
        for task in self._pending_tasks:
            if not task.done():
                task.cancel()
        self._pending_tasks.clear()
        
        self._is_tts_playing = False
        return True

    def add_pending_task(self, task: asyncio.Task):
        """添加待处理任务"""
        self._pending_tasks.append(task)

    def clear_pending_tasks(self):
        """清空待处理任务"""
        self._pending_tasks.clear()

    async def wait_for_interrupt(self) -> bool:
        """等待打断事件"""
        try:
            await self._interrupt_event.wait()
            return True
        except asyncio.CancelledError:
            return False

    def is_interrupted(self) -> bool:
        """检查是否已被打断"""
        return self._interrupt_event.is_set()
