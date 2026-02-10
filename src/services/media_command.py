"""媒体播放指令协议

定义 WebSocket 媒体播放指令的数据模型和消息格式。

用于语音智能体通过 WebSocket 向前端发送播放控制指令，
支持 play、pause、seek、stop 四种操作。

Validates: Requirements 8.3, 8.4
"""

from typing import Any, Literal

from pydantic import BaseModel


class MediaPlayCommand(BaseModel):
    """媒体播放指令数据模型

    WebSocket 消息格式:
        {
            "type": "media_command",
            "data": {
                "action": "play",
                "media_id": "VI123456",
                "media_type": "video",
                "media_url": "http://...",
                "start_time": 13,
                "end_time": 18,
                "description": "片段描述"
            }
        }
    """

    action: Literal["play", "pause", "seek", "stop"]
    media_id: str
    media_type: Literal["video", "audio"]
    media_url: str
    start_time: float
    end_time: float | None = None
    description: str | None = None

    def to_ws_message(self) -> dict[str, Any]:
        """转换为 WebSocket 消息格式"""
        return {
            "type": "media_command",
            "data": self.model_dump(exclude_none=True),
        }
