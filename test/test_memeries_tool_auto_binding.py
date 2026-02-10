"""Property Test: 工具自动绑定 (Property 6)

验证绑定了 memeries 类型知识库的智能体（无论是 chatbot、voice_agent 还是 deep_agent），
应自动获得该知识库的媒体检索工具。

对于任意数量（1~N）的 memeries 知识库，get_kb_based_tools() 应：
- 为每个知识库创建恰好一个工具
- 每个工具使用 MediaRetrieverModel 作为 args_schema
- 每个工具的 metadata 包含 "knowledgebase" tag
- 每个工具的 metadata 包含 kb_type "memeries"

**Validates: Requirements 5.2, 8.1**
"""

import os
import sys

# Add project root to path
sys.path.insert(0, os.getcwd())

from unittest.mock import AsyncMock, patch

from hypothesis import given, settings
from hypothesis import strategies as st

from src.agents.common.tools import MediaRetrieverModel, get_kb_based_tools

# --- Strategies ---

# 生成合法的知识库名称（非空中英文字符串，长度 1~30）
kb_name_strategy = st.text(
    alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyz医学视频音频教程资料库测试数据"),
    min_size=1,
    max_size=30,
)

# 生成知识库描述（可为空）
kb_description_strategy = st.text(
    alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyz这是一个关于音视频内容的知识库描述信息"),
    min_size=0,
    max_size=50,
)

# 生成单个 memeries 知识库信息
memeries_kb_strategy = st.tuples(kb_name_strategy, kb_description_strategy)

# 生成 1~10 个 memeries 知识库列表
memeries_kb_list_strategy = st.lists(memeries_kb_strategy, min_size=1, max_size=10)


def _build_retrievers(kb_list: list[tuple[str, str]]) -> dict:
    """根据知识库列表构造 mock retrievers 字典"""
    retrievers = {}
    for i, (name, description) in enumerate(kb_list):
        db_id = f"db_memeries_{i:03d}"
        retrievers[db_id] = {
            "name": name,
            "description": description,
            "retriever": AsyncMock(return_value=[]),
            "metadata": {"kb_type": "memeries"},
        }
    return retrievers


# --- Property Tests ---


@given(kb_list=memeries_kb_list_strategy)
@settings(max_examples=100)
def test_tool_count_matches_kb_count(kb_list: list[tuple[str, str]]):
    """属性：memeries 知识库数量 == 生成的工具数量

    **Validates: Requirements 5.2, 8.1**
    """
    retrievers = _build_retrievers(kb_list)
    with patch("src.agents.common.tools.knowledge_base") as mock_kb:
        mock_kb.get_retrievers.return_value = retrievers
        tools = get_kb_based_tools()

    assert len(tools) == len(kb_list)


@given(kb_list=memeries_kb_list_strategy)
@settings(max_examples=100)
def test_all_tools_use_media_retriever_model(kb_list: list[tuple[str, str]]):
    """属性：每个 memeries 工具的 args_schema 都是 MediaRetrieverModel

    **Validates: Requirements 5.2, 8.1**
    """
    retrievers = _build_retrievers(kb_list)
    with patch("src.agents.common.tools.knowledge_base") as mock_kb:
        mock_kb.get_retrievers.return_value = retrievers
        tools = get_kb_based_tools()

    for tool in tools:
        assert tool.args_schema is MediaRetrieverModel


@given(kb_list=memeries_kb_list_strategy)
@settings(max_examples=100)
def test_all_tools_have_knowledgebase_tag(kb_list: list[tuple[str, str]]):
    """属性：每个 memeries 工具的 metadata 都包含 "knowledgebase" tag

    **Validates: Requirements 5.2, 8.1**
    """
    retrievers = _build_retrievers(kb_list)
    with patch("src.agents.common.tools.knowledge_base") as mock_kb:
        mock_kb.get_retrievers.return_value = retrievers
        tools = get_kb_based_tools()

    for tool in tools:
        assert "knowledgebase" in tool.metadata.get("tag", [])


@given(kb_list=memeries_kb_list_strategy)
@settings(max_examples=100)
def test_all_tools_have_memeries_kb_type(kb_list: list[tuple[str, str]]):
    """属性：每个 memeries 工具的 metadata 中 kb_type 为 "memeries"

    **Validates: Requirements 5.2, 8.1**
    """
    retrievers = _build_retrievers(kb_list)
    with patch("src.agents.common.tools.knowledge_base") as mock_kb:
        mock_kb.get_retrievers.return_value = retrievers
        tools = get_kb_based_tools()

    for tool in tools:
        assert tool.metadata.get("kb_type") == "memeries"
