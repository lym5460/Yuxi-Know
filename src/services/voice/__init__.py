"""Voice Services Module.

使用豆包端到端实时语音大模型 API 实现语音交互。
"""

from src.services.voice.doubao_realtime import (
    DoubaoConfig,
    DoubaoRealtimeClient,
    EventID,
)

__all__ = [
    "DoubaoConfig",
    "DoubaoRealtimeClient",
    "EventID",
]
