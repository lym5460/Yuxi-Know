"""测试 memeries 类型知识库的工具绑定逻辑。

验证 get_kb_based_tools() 为 memeries 类型知识库创建专用的媒体检索工具，
同时不影响其他类型知识库的工具创建。

Validates: Requirements 5.1, 5.2, 5.3, 5.6
"""

from unittest.mock import AsyncMock, patch

import pytest

from src.agents.common.tools import (
    CommonKnowledgeRetriever,
    KnowledgeRetrieverModel,
    MediaRetrieverModel,
    get_kb_based_tools,
)


def _make_retriever_info(name: str, kb_type: str, description: str = "") -> dict:
    """构造模拟的 retriever_info 字典"""
    retriever = AsyncMock(return_value=[{"content": "test"}])
    return {
        "name": name,
        "description": description,
        "retriever": retriever,
        "metadata": {"kb_type": kb_type},
    }


@pytest.fixture
def mock_retrievers():
    """模拟包含多种类型知识库的 retrievers"""
    return {
        "db_memeries_001": _make_retriever_info("医学视频库", "memeries", "医学手术视频"),
        "db_lightrag_001": _make_retriever_info("文档库", "lightrag", "技术文档"),
        "db_milvus_001": _make_retriever_info("向量库", "milvus", "向量检索"),
    }


class TestMemeriesToolCreation:
    """测试 memeries 类型知识库工具创建"""

    def test_memeries_tool_uses_media_retriever_model(self, mock_retrievers):
        """memeries 类型应使用 MediaRetrieverModel 作为 args_schema"""
        with patch("src.agents.common.tools.knowledge_base") as mock_kb:
            mock_kb.get_retrievers.return_value = {
                "db_memeries_001": mock_retrievers["db_memeries_001"],
            }
            tools = get_kb_based_tools()

        assert len(tools) == 1
        assert tools[0].args_schema is MediaRetrieverModel

    def test_memeries_tool_description_contains_media_keywords(self, mock_retrievers):
        """memeries 工具描述应包含媒体相关关键词"""
        with patch("src.agents.common.tools.knowledge_base") as mock_kb:
            mock_kb.get_retrievers.return_value = {
                "db_memeries_001": mock_retrievers["db_memeries_001"],
            }
            tools = get_kb_based_tools()

        assert len(tools) == 1
        desc = tools[0].description
        assert "媒体" in desc
        assert "音视频" in desc
        assert "get_mindmap" not in desc

    def test_memeries_tool_has_knowledgebase_tag(self, mock_retrievers):
        """memeries 工具应带有 knowledgebase 标签"""
        with patch("src.agents.common.tools.knowledge_base") as mock_kb:
            mock_kb.get_retrievers.return_value = {
                "db_memeries_001": mock_retrievers["db_memeries_001"],
            }
            tools = get_kb_based_tools()

        assert len(tools) == 1
        assert "knowledgebase" in tools[0].metadata.get("tag", [])

    def test_memeries_tool_name_from_kb_name(self, mock_retrievers):
        """工具名称应基于知识库名称"""
        with patch("src.agents.common.tools.knowledge_base") as mock_kb:
            mock_kb.get_retrievers.return_value = {
                "db_memeries_001": mock_retrievers["db_memeries_001"],
            }
            tools = get_kb_based_tools()

        assert tools[0].name == "医学视频库"


class TestOtherKBTypesUnaffected:
    """测试其他类型知识库不受 memeries 支持的影响"""

    def test_lightrag_still_uses_knowledge_retriever_model(self, mock_retrievers):
        """lightrag 类型应继续使用 KnowledgeRetrieverModel"""
        with patch("src.agents.common.tools.knowledge_base") as mock_kb:
            mock_kb.get_retrievers.return_value = {
                "db_lightrag_001": mock_retrievers["db_lightrag_001"],
            }
            tools = get_kb_based_tools()

        assert len(tools) == 1
        assert tools[0].args_schema is KnowledgeRetrieverModel

    def test_milvus_still_uses_common_knowledge_retriever(self, mock_retrievers):
        """milvus 类型应继续使用 CommonKnowledgeRetriever"""
        with patch("src.agents.common.tools.knowledge_base") as mock_kb:
            mock_kb.get_retrievers.return_value = {
                "db_milvus_001": mock_retrievers["db_milvus_001"],
            }
            tools = get_kb_based_tools()

        assert len(tools) == 1
        assert tools[0].args_schema is CommonKnowledgeRetriever

    def test_lightrag_description_contains_mindmap(self, mock_retrievers):
        """lightrag 工具描述应包含思维导图操作"""
        with patch("src.agents.common.tools.knowledge_base") as mock_kb:
            mock_kb.get_retrievers.return_value = {
                "db_lightrag_001": mock_retrievers["db_lightrag_001"],
            }
            tools = get_kb_based_tools()

        assert "get_mindmap" in tools[0].description


class TestMixedKBTypes:
    """测试混合类型知识库场景"""

    def test_all_types_create_tools(self, mock_retrievers):
        """所有类型的知识库都应创建对应的工具"""
        with patch("src.agents.common.tools.knowledge_base") as mock_kb:
            mock_kb.get_retrievers.return_value = mock_retrievers
            tools = get_kb_based_tools()

        assert len(tools) == 3
        tool_names = {t.name for t in tools}
        assert "医学视频库" in tool_names
        assert "文档库" in tool_names
        assert "向量库" in tool_names

    def test_mixed_types_correct_schemas(self, mock_retrievers):
        """混合类型场景下每个工具应使用正确的 args_schema"""
        with patch("src.agents.common.tools.knowledge_base") as mock_kb:
            mock_kb.get_retrievers.return_value = mock_retrievers
            tools = get_kb_based_tools()

        schema_map = {t.name: t.args_schema for t in tools}
        assert schema_map["医学视频库"] is MediaRetrieverModel
        assert schema_map["文档库"] is KnowledgeRetrieverModel
        assert schema_map["向量库"] is CommonKnowledgeRetriever


class TestMediaRetrieverWrapper:
    """测试媒体检索器包装函数的行为"""

    @pytest.mark.asyncio
    async def test_media_retriever_calls_underlying_retriever(self, mock_retrievers):
        """媒体检索器应调用底层的 retriever 函数"""
        with patch("src.agents.common.tools.knowledge_base") as mock_kb:
            mock_kb.get_retrievers.return_value = {
                "db_memeries_001": mock_retrievers["db_memeries_001"],
            }
            tools = get_kb_based_tools()

        await tools[0].ainvoke({"query_text": "手术缝合"})
        mock_retrievers["db_memeries_001"]["retriever"].assert_called_once_with("手术缝合")

    @pytest.mark.asyncio
    async def test_media_retriever_returns_empty_message(self, mock_retrievers):
        """当检索无结果时应返回提示信息"""
        mock_retrievers["db_memeries_001"]["retriever"].return_value = []
        with patch("src.agents.common.tools.knowledge_base") as mock_kb:
            mock_kb.get_retrievers.return_value = {
                "db_memeries_001": mock_retrievers["db_memeries_001"],
            }
            tools = get_kb_based_tools()

        result = await tools[0].ainvoke({"query_text": "不存在的内容"})
        assert "没有找到" in result
        assert "音视频片段" in result

    @pytest.mark.asyncio
    async def test_media_retriever_handles_error(self, mock_retrievers):
        """当检索出错时应返回错误信息"""
        mock_retrievers["db_memeries_001"]["retriever"].side_effect = Exception("API 连接失败")
        with patch("src.agents.common.tools.knowledge_base") as mock_kb:
            mock_kb.get_retrievers.return_value = {
                "db_memeries_001": mock_retrievers["db_memeries_001"],
            }
            tools = get_kb_based_tools()

        result = await tools[0].ainvoke({"query_text": "测试"})
        assert "媒体检索失败" in result


class TestMediaRetrieverModel:
    """测试 MediaRetrieverModel 参数模型"""

    def test_query_text_required(self):
        """query_text 应为必填参数"""
        with pytest.raises(Exception):
            MediaRetrieverModel()

    def test_operation_defaults_to_search(self):
        """operation 应默认为 'search'"""
        model = MediaRetrieverModel(query_text="测试")
        assert model.operation == "search"

    def test_accepts_query_text(self):
        """应接受 query_text 参数"""
        model = MediaRetrieverModel(query_text="手术缝合技术")
        assert model.query_text == "手术缝合技术"
