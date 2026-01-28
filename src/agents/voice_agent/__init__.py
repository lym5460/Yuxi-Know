"""Voice Agent - 语音智能体模块

支持实时语音交互的智能体，具备以下特性：
- 语音识别 (ASR) 支持
- 语音合成 (TTS) 支持
- 语音活动检测 (VAD)
- 用户打断处理
- 工具调用语音反馈
"""

from .context import VoiceContext
from .graph import VoiceAgent

__all__ = [
    "VoiceAgent",
    "VoiceContext",
]

# 模块元数据
__version__ = "1.0.0"
__author__ = "Yuxi-Know Team"
__description__ = "支持实时语音交互的智能体"
