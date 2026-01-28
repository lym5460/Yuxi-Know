"""Voice Agent Context - 语音智能体配置上下文

继承 BaseContext，添加语音相关的配置字段。
"""

from dataclasses import dataclass, field
from typing import Annotated

from src.agents.common.context import BaseContext

# 语音助手默认系统提示词
VOICE_SYSTEM_PROMPT = """你是一个友好的语音助手。请用简洁、自然的语言回答用户的问题。

## 输出格式要求（非常重要）：
- 禁止使用任何 Markdown 格式，包括：**加粗**、*斜体*、# 标题、- 列表、```代码块```、[链接](url) 等
- 禁止使用 HTML 标签
- 禁止使用表格
- 禁止使用 emoji 表情符号
- 数字和序号用口语表达，如"第一"、"第二"，而不是"1."、"2."
- 如果需要列举，用"首先"、"其次"、"然后"、"最后"等连接词

## 语言风格：
- 回答要简洁明了，适合语音播报
- 使用口语化的表达方式，像朋友聊天一样自然
- 避免使用过长的句子，每句话控制在 20 字以内
- 避免使用书面语和专业术语，用通俗易懂的语言
- 如果用户问的问题需要长篇回答，先给出简短总结，再问用户是否需要详细了解
"""


@dataclass(kw_only=True)
class VoiceContext(BaseContext):
    """语音智能体配置上下文

    继承 BaseContext 的所有配置，并添加语音相关的配置字段。
    """

    # 覆盖默认模型（确保有值）
    model: Annotated[str, {"__template_metadata__": {"kind": "llm"}}] = field(
        default="siliconflow/deepseek-ai/DeepSeek-V3",
        metadata={"name": "智能体模型", "description": "语音智能体使用的对话模型"},
    )

    # 覆盖默认系统提示词
    system_prompt: Annotated[str, {"__template_metadata__": {"kind": "prompt"}}] = field(
        default=VOICE_SYSTEM_PROMPT,
        metadata={"name": "系统提示词", "description": "语音智能体的角色和行为指导"},
    )

    # ASR 配置
    asr_provider: Annotated[str, {"__template_metadata__": {"kind": "select"}}] = field(
        default="local-whisper",
        metadata={
            "name": "语音识别服务",
            "options": ["openai", "local-whisper"],
            "description": "语音识别 (ASR) 服务提供商，local-whisper 使用本地 Whisper 服务",
        },
    )

    # TTS 配置
    tts_provider: Annotated[str, {"__template_metadata__": {"kind": "select"}}] = field(
        default="edge-tts",
        metadata={
            "name": "语音合成服务",
            "options": ["openai", "edge-tts"],
            "description": "语音合成 (TTS) 服务提供商",
        },
    )

    tts_voice: str = field(
        default="zh-CN-XiaoxiaoNeural",
        metadata={
            "name": "语音角色",
            "description": "TTS 语音角色，不同提供商支持不同的语音",
        },
    )

    tts_speed: float = field(
        default=1.0,
        metadata={
            "name": "语速",
            "description": "TTS 语速，范围 0.5-2.0",
        },
    )

    # VAD 配置
    vad_threshold: float = field(
        default=0.5,
        metadata={
            "name": "语音检测阈值",
            "description": "VAD 语音活动检测阈值，范围 0.0-1.0",
        },
    )

    silence_duration: float = field(
        default=0.8,
        metadata={
            "name": "静音时长",
            "description": "判定语音结束的静音时长（秒）",
        },
    )

    # 交互配置
    interrupt_enabled: bool = field(
        default=True,
        metadata={
            "name": "启用打断",
            "description": "是否允许用户打断智能体说话",
        },
    )

    interrupt_sensitivity: float = field(
        default=0.5,
        metadata={
            "name": "打断灵敏度",
            "description": "打断检测灵敏度，范围 0.0-1.0",
        },
    )

    tool_feedback_enabled: bool = field(
        default=True,
        metadata={
            "name": "工具反馈",
            "description": "是否在工具调用时提供语音反馈",
        },
    )

    tool_feedback_verbosity: Annotated[str, {"__template_metadata__": {"kind": "select"}}] = field(
        default="normal",
        metadata={
            "name": "反馈详细程度",
            "options": ["minimal", "normal", "verbose"],
            "description": "工具调用语音反馈的详细程度",
        },
    )

    # 会话配置
    session_timeout: int = field(
        default=300,
        metadata={
            "name": "会话超时",
            "description": "语音会话超时时间（秒）",
        },
    )
