"""Audio Stream Handler.

处理音频流的接收和发送，支持全双工通信。

Validates: Requirements 2.1, 2.4, 2.5, 2.7
"""

import asyncio
import base64
from collections.abc import AsyncIterator
from dataclasses import dataclass

from src.utils.logging_config import logger


@dataclass
class AudioChunk:
    """音频块"""
    data: bytes
    timestamp: float


class AudioStreamHandler:
    """音频流处理器
    
    处理双向音频流，支持：
    - 接收客户端音频块
    - 发送 TTS 音频块
    - 全双工通信
    """

    def __init__(self, sample_rate: int = 16000):
        self.sample_rate = sample_rate
        self._input_queue: asyncio.Queue[bytes] = asyncio.Queue()
        self._output_queue: asyncio.Queue[bytes] = asyncio.Queue()
        self._is_speaking = False

    async def receive_audio(self, audio_data_b64: str) -> bytes:
        """接收 base64 编码的音频数据"""
        try:
            audio_bytes = base64.b64decode(audio_data_b64)
            await self._input_queue.put(audio_bytes)
            return audio_bytes
        except Exception as e:
            logger.error(f"Failed to decode audio: {e}")
            raise

    async def get_input_stream(self) -> AsyncIterator[bytes]:
        """获取输入音频流"""
        while True:
            chunk = await self._input_queue.get()
            if chunk is None:  # 结束信号
                break
            yield chunk

    async def send_audio(self, audio_bytes: bytes) -> str:
        """发送音频数据，返回 base64 编码"""
        audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
        await self._output_queue.put(audio_bytes)
        return audio_b64

    async def get_output_stream(self) -> AsyncIterator[bytes]:
        """获取输出音频流"""
        while True:
            chunk = await self._output_queue.get()
            if chunk is None:
                break
            yield chunk

    def set_speaking(self, speaking: bool):
        """设置是否正在播放"""
        self._is_speaking = speaking

    @property
    def is_speaking(self) -> bool:
        """是否正在播放音频"""
        return self._is_speaking

    async def clear_input(self):
        """清空输入队列"""
        while not self._input_queue.empty():
            try:
                self._input_queue.get_nowait()
            except asyncio.QueueEmpty:
                break

    async def clear_output(self):
        """清空输出队列"""
        while not self._output_queue.empty():
            try:
                self._output_queue.get_nowait()
            except asyncio.QueueEmpty:
                break

    async def stop(self):
        """停止处理"""
        await self._input_queue.put(None)
        await self._output_queue.put(None)
