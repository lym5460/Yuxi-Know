"""Voice Agent Context - 语音智能体配置上下文

使用豆包端到端实时语音大模型 API。
"""

from dataclasses import dataclass, field
from typing import Annotated

from src.agents.common.context import BaseContext


@dataclass(kw_only=True)
class VoiceContext(BaseContext):
    """语音智能体配置上下文 - 豆包端到端模式

    使用豆包 Realtime API，无需单独配置 ASR/LLM/TTS。
    """

    # 豆包模型版本
    doubao_model: Annotated[str, {"__template_metadata__": {"kind": "select"}}] = field(
        default="O",
        metadata={
            "name": "模型版本",
            "options": ["O", "SC", "1.2.1.0", "2.2.0.0"],
            "description": "O=精品音色, SC=克隆音色, 1.2.1.0=O2.0版本, 2.2.0.0=SC2.0版本",
        },
    )

    # 豆包音色
    doubao_voice: Annotated[str, {"__template_metadata__": {"kind": "select"}}] = field(
        default="zh_female_vv_jupiter_bigtts",
        metadata={
            "name": "语音音色",
            "options": [
                "zh_female_vv_jupiter_bigtts",
                "zh_female_xiaohe_jupiter_bigtts",
                "zh_male_yunzhou_jupiter_bigtts",
                "zh_male_xiaotian_jupiter_bigtts",
            ],
            "description": "vv=活泼女声, xiaohe=甜美女声, yunzhou=沉稳男声, xiaotian=磁性男声",
        },
    )

    # 角色名称
    bot_name: str = field(
        default="语析助手",
        metadata={
            "name": "角色名称",
            "description": "语音助手的名称，最长20个字符",
        },
    )

    # 角色设定
    system_role: Annotated[str, {"__template_metadata__": {"kind": "prompt"}}] = field(
        default="你是一个友好的智能助手，擅长回答各种问题。回答要简洁明了，适合语音播报。",
        metadata={
            "name": "角色设定",
            "description": "描述角色的背景、设定等",
        },
    )

    # 说话风格
    speaking_style: str = field(
        default="",
        metadata={
            "name": "说话风格",
            "description": "配置对话风格，如'说话温柔'、'口吻活泼'等",
        },
    )

    # 静音判定时长
    silence_duration_ms: int = field(
        default=1500,
        metadata={
            "name": "静音判定时长",
            "description": "判断用户停止说话的时间（毫秒），范围 500-50000",
        },
    )

    # 打断开关
    interrupt_enabled: bool = field(
        default=True,
        metadata={
            "name": "启用打断",
            "description": "是否允许用户打断智能体说话",
        },
    )

    # 会话超时
    session_timeout: int = field(
        default=300,
        metadata={
            "name": "会话超时",
            "description": "语音会话超时时间（秒）",
        },
    )
