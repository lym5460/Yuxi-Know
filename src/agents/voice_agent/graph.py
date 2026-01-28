"""Voice Agent - 语音智能体实现

继承 BaseAgent，添加语音交互能力。
"""

from typing import AsyncIterator

from langchain.agents import create_agent
from langchain.agents.middleware import ModelRetryMiddleware
from langgraph.graph.state import CompiledStateGraph

from src.agents.common import BaseAgent, load_chat_model
from src.agents.common.middlewares import (
    RuntimeConfigMiddleware,
    inject_attachment_context,
)
from src.services.mcp_service import get_tools_from_all_servers
from src.utils.logging_config import logger

from .context import VoiceContext

class VoiceAgent(BaseAgent):
    """语音智能体，继承 BaseAgent 的所有能力，添加语音交互支持"""

    name = "语音助手"
    description = "支持实时语音交互的智能体"
    capabilities = ["voice", "file_upload"]  # 支持语音和文件上传功能
    context_schema = VoiceContext

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    async def get_graph(self, **kwargs) -> CompiledStateGraph:
        """构建语音智能体图"""
        # 从文件加载配置，确保有默认值
        context = self.context_schema.from_file(module_name=self.module_name)
        all_mcp_tools = await get_tools_from_all_servers()

        # 确保 model 有值（使用 VoiceContext 的默认值）
        model_name = context.model if context.model else "siliconflow/deepseek-ai/DeepSeek-V3"
        logger.info(f"VoiceAgent 使用模型: {model_name}")

        graph = create_agent(
            model=load_chat_model(model_name),
            system_prompt=context.system_prompt,
            middleware=[
                inject_attachment_context,
                RuntimeConfigMiddleware(extra_tools=all_mcp_tools),
                ModelRetryMiddleware(),
            ],
            checkpointer=await self._get_checkpointer(),
        )

        return graph

    async def process_voice_input(
        self,
        text: str,
        context: VoiceContext,
    ) -> AsyncIterator[str]:
        """处理语音输入，返回流式文本响应"""
        yield f"收到语音输入: {text}"


def main():
    """测试入口"""
    pass


if __name__ == "__main__":
    main()
