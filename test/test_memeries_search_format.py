"""Property-based tests for Memeries search result format completeness.

**Validates: Requirements 3.4, 5.4**

Tests that aquery() search results always contain all required fields
(media_id, media_name, media_type, start_time, end_time, score, media_url)
and that start_time/end_time are numeric types.
"""

import os
import sys
import threading

# Add project root to path
sys.path.insert(0, os.getcwd())

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from hypothesis import given, settings, strategies as st

from src.knowledge.base import KnowledgeBase


# =============================================================================
# === 常量定义 ===
# =============================================================================

REQUIRED_FIELDS = {"media_id", "media_name", "media_type", "start_time", "end_time", "score", "media_url"}

NUMERIC_FIELDS = {"start_time", "end_time"}


# =============================================================================
# === Strategies ===
# =============================================================================

# 生成 Memeries API 返回的 videoNo（VI 前缀 + 数字）
video_nos = st.builds(lambda n: f"VI{n}", n=st.integers(min_value=1, max_value=999999999))

# 生成时间值（Memeries API 返回字符串格式的数字）
time_values = st.one_of(
    st.integers(min_value=0, max_value=36000).map(str),
    st.floats(min_value=0, max_value=36000, allow_nan=False, allow_infinity=False).map(lambda f: str(round(f, 2))),
)

# 生成 score 值
scores = st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)

# 生成单个 Memeries API 搜索结果项
memeries_result_item = st.fixed_dictionaries({
    "videoNo": video_nos,
    "startTime": time_values,
    "endTime": time_values,
    "score": scores,
})

# 生成搜索结果列表（1~10 个结果）
memeries_result_list = st.lists(memeries_result_item, min_size=1, max_size=10)

# 生成文件名
media_filenames = st.builds(
    lambda name, ext: f"{name}.{ext}",
    name=st.text(
        min_size=1,
        max_size=20,
        alphabet=st.characters(whitelist_categories=("L", "N"), whitelist_characters="_-"),
    ),
    ext=st.sampled_from(["mp4", "avi", "mov", "mkv", "webm", "mp3", "wav", "m4a", "flac", "aac", "ogg"]),
)

# 生成媒体类型
media_types = st.sampled_from(["video", "audio"])

# 生成 MinIO URL
media_urls = st.builds(
    lambda name: f"http://minio:9000/kb-files/{name}",
    name=st.text(min_size=1, max_size=30, alphabet=st.characters(whitelist_categories=("L", "N"), whitelist_characters="_-.")),
)


# =============================================================================
# === Helpers ===
# =============================================================================


def _build_memeries_kb():
    """创建一个最小化的 MemeriesKB 实例用于测试"""
    from src.knowledge.implementations.memeries import MemeriesKB

    if KnowledgeBase._processing_lock is None:
        KnowledgeBase._processing_lock = threading.Lock()

    kb = MemeriesKB.__new__(MemeriesKB)
    kb.work_dir = "/tmp/test_kb"
    kb.files_meta = {}
    kb.databases_meta = {}
    return kb


def _setup_files_meta(kb, result_items, filenames, m_types, urls):
    """根据搜索结果中的 videoNo 设置对应的文件元数据"""
    for i, item in enumerate(result_items):
        video_no = item["videoNo"]
        file_id = f"file_{i}"
        kb.files_meta[file_id] = {
            "file_id": file_id,
            "filename": filenames[i],
            "path": urls[i],
            "status": "indexed",
            "media_type": m_types[i],
            "memeries_video_no": video_no,
        }


async def _run_aquery(kb, search_results):
    """执行 aquery 并返回结果，mock Memeries search API"""
    mock_service = MagicMock()
    mock_service.is_configured = MagicMock(return_value=True)
    # BY_VIDEO 返回全部结果，BY_AUDIO 返回空列表（避免重复）
    mock_service.search = AsyncMock(side_effect=[search_results, []])

    with patch("src.services.memeries_service.get_memeries_service", return_value=mock_service):
        return await kb.aquery(query_text="test query", db_id="test_db")


# =============================================================================
# === Property Tests: 搜索结果字段完整性 ===
# =============================================================================


class TestSearchResultFieldCompleteness:
    """Property tests for search result field completeness.

    **Validates: Requirements 3.4, 5.4**
    """

    @given(
        results=memeries_result_list,
        data=st.data(),
    )
    @settings(max_examples=100)
    @pytest.mark.asyncio
    async def test_results_contain_all_required_fields(self, results: list[dict], data):
        """
        Property: For any Memeries search response, each result item processed by
        aquery() must contain all required fields: media_id, media_name, media_type,
        start_time, end_time, score, media_url.

        **Validates: Requirements 3.4, 5.4**
        """
        # 为每个结果项生成对应的文件元数据
        filenames = [data.draw(media_filenames) for _ in results]
        m_types = [data.draw(media_types) for _ in results]
        urls = [data.draw(media_urls) for _ in results]

        kb = _build_memeries_kb()
        _setup_files_meta(kb, results, filenames, m_types, urls)

        query_results = await _run_aquery(kb, results)

        # 去重后结果数量可能小于输入，但每个结果都必须包含所有字段
        assert len(query_results) > 0, "Should return at least one result"

        for item in query_results:
            missing = REQUIRED_FIELDS - set(item.keys())
            assert not missing, (
                f"Result item missing required fields: {missing}. "
                f"Got keys: {set(item.keys())}"
            )


# =============================================================================
# === Property Tests: start_time 和 end_time 数字类型 ===
# =============================================================================


class TestSearchResultTimeTypes:
    """Property tests for start_time and end_time numeric types.

    **Validates: Requirements 3.4, 5.4**
    """

    @given(
        results=memeries_result_list,
        data=st.data(),
    )
    @settings(max_examples=100)
    @pytest.mark.asyncio
    async def test_start_time_and_end_time_are_numeric(self, results: list[dict], data):
        """
        Property: For any search result, start_time and end_time must be numeric
        types (int or float), even when the Memeries API returns them as strings.

        **Validates: Requirements 3.4, 5.4**
        """
        filenames = [data.draw(media_filenames) for _ in results]
        m_types = [data.draw(media_types) for _ in results]
        urls = [data.draw(media_urls) for _ in results]

        kb = _build_memeries_kb()
        _setup_files_meta(kb, results, filenames, m_types, urls)

        query_results = await _run_aquery(kb, results)

        assert len(query_results) > 0, "Should return at least one result"

        for item in query_results:
            for field in NUMERIC_FIELDS:
                value = item[field]
                assert isinstance(value, (int, float)), (
                    f"'{field}' must be numeric (int or float), "
                    f"but got {type(value).__name__}: {value!r}"
                )
