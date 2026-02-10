"""Property-based tests for Memeries search type merging (Property 5).

**Validates: Requirements 3.2, 5.5**

Tests that aquery() simultaneously executes BY_VIDEO and BY_AUDIO searches,
merges results, and sorts them by score in descending order.
"""

import os
import sys
import threading

sys.path.insert(0, os.getcwd())

from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest
from hypothesis import given, settings, strategies as st

from src.knowledge.base import KnowledgeBase


# =============================================================================
# === Strategies ===
# =============================================================================

video_nos = st.builds(lambda n: f"VI{n}", n=st.integers(min_value=1, max_value=999999999))

time_values = st.integers(min_value=0, max_value=36000).map(str)

scores = st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)

memeries_result_item = st.fixed_dictionaries({
    "videoNo": video_nos,
    "startTime": time_values,
    "endTime": time_values,
    "score": scores,
})

# BY_VIDEO 和 BY_AUDIO 各自的结果列表（0~8 个）
search_result_list = st.lists(memeries_result_item, min_size=0, max_size=8)

media_filenames = st.builds(
    lambda name, ext: f"{name}.{ext}",
    name=st.text(
        min_size=1,
        max_size=20,
        alphabet=st.characters(whitelist_categories=("L", "N"), whitelist_characters="_-"),
    ),
    ext=st.sampled_from(["mp4", "avi", "mov", "mkv", "webm", "mp3", "wav", "m4a", "flac", "aac", "ogg"]),
)

media_types = st.sampled_from(["video", "audio"])

media_urls = st.builds(
    lambda name: f"http://minio:9000/kb-files/{name}",
    name=st.text(
        min_size=1,
        max_size=30,
        alphabet=st.characters(whitelist_categories=("L", "N"), whitelist_characters="_-."),
    ),
)

query_texts = st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=("L", "N", "Z")))

top_k_values = st.integers(min_value=1, max_value=20)


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


def _collect_unique_video_nos(*result_lists: list[dict]) -> set[str]:
    """收集所有结果列表中的唯一 videoNo"""
    return {item["videoNo"] for items in result_lists for item in items}


def _setup_files_meta_for_video_nos(kb, video_nos_set: set[str], data):
    """为给定的 videoNo 集合设置文件元数据"""
    for i, video_no in enumerate(video_nos_set):
        file_id = f"file_{i}"
        kb.files_meta[file_id] = {
            "file_id": file_id,
            "filename": data.draw(media_filenames),
            "path": data.draw(media_urls),
            "status": "indexed",
            "media_type": data.draw(media_types),
            "memeries_video_no": video_no,
        }


# =============================================================================
# === Property Tests: 搜索类型合并 ===
# =============================================================================


class TestSearchTypeMerge:
    """Property tests for search type merging.

    **Validates: Requirements 3.2, 5.5**
    """

    @given(
        video_results=search_result_list,
        audio_results=search_result_list,
        query_text=query_texts,
        data=st.data(),
    )
    @settings(max_examples=100)
    @pytest.mark.asyncio
    async def test_aquery_calls_search_for_both_types(
        self,
        video_results: list[dict],
        audio_results: list[dict],
        query_text: str,
        data,
    ):
        """
        Property: For any media search request, aquery() must call
        MemeriesService.search() exactly twice — once with search_type='BY_VIDEO'
        and once with search_type='BY_AUDIO'.

        **Validates: Requirements 3.2, 5.5**
        """
        kb = _build_memeries_kb()
        all_video_nos = _collect_unique_video_nos(video_results, audio_results)
        _setup_files_meta_for_video_nos(kb, all_video_nos, data)

        mock_service = MagicMock()
        mock_service.is_configured = MagicMock(return_value=True)
        mock_service.search = AsyncMock(side_effect=[video_results, audio_results])

        with patch("src.services.memeries_service.get_memeries_service", return_value=mock_service):
            await kb.aquery(query_text=query_text, db_id="test_db")

        # 验证 search 被调用了恰好 2 次
        assert mock_service.search.call_count == 2, (
            f"Expected exactly 2 search calls, got {mock_service.search.call_count}"
        )

        # 验证两次调用分别使用了 BY_VIDEO 和 BY_AUDIO
        search_types_called = {c.kwargs.get("search_type") for c in mock_service.search.call_args_list}
        assert search_types_called == {"BY_VIDEO", "BY_AUDIO"}, (
            f"Expected search types {{'BY_VIDEO', 'BY_AUDIO'}}, got {search_types_called}"
        )

    @given(
        video_results=search_result_list,
        audio_results=search_result_list,
        data=st.data(),
    )
    @settings(max_examples=100)
    @pytest.mark.asyncio
    async def test_merged_results_sorted_by_score_descending(
        self,
        video_results: list[dict],
        audio_results: list[dict],
        data,
    ):
        """
        Property: For any combination of BY_VIDEO and BY_AUDIO search results,
        the merged output must be sorted by score in descending order.

        **Validates: Requirements 3.2, 5.5**
        """
        kb = _build_memeries_kb()
        all_video_nos = _collect_unique_video_nos(video_results, audio_results)
        _setup_files_meta_for_video_nos(kb, all_video_nos, data)

        mock_service = MagicMock()
        mock_service.is_configured = MagicMock(return_value=True)
        mock_service.search = AsyncMock(side_effect=[video_results, audio_results])

        with patch("src.services.memeries_service.get_memeries_service", return_value=mock_service):
            results = await kb.aquery(query_text="test", db_id="test_db")

        # 验证结果按 score 降序排列
        if len(results) > 1:
            result_scores = [r["score"] for r in results]
            for i in range(len(result_scores) - 1):
                assert result_scores[i] >= result_scores[i + 1], (
                    f"Results not sorted by score descending: "
                    f"score[{i}]={result_scores[i]} < score[{i + 1}]={result_scores[i + 1]}. "
                    f"All scores: {result_scores}"
                )

    @given(
        video_results=st.lists(memeries_result_item, min_size=1, max_size=5),
        audio_results=st.lists(memeries_result_item, min_size=1, max_size=5),
        data=st.data(),
    )
    @settings(max_examples=100)
    @pytest.mark.asyncio
    async def test_merged_results_contain_items_from_both_searches(
        self,
        video_results: list[dict],
        audio_results: list[dict],
        data,
    ):
        """
        Property: For any non-empty BY_VIDEO and BY_AUDIO results with distinct keys,
        the merged output should contain items originating from both search types.

        **Validates: Requirements 3.2, 5.5**
        """
        # 确保 video 和 audio 结果使用不同的 videoNo，避免去重影响
        used_nos = set()
        distinct_video_results = []
        for item in video_results:
            key = (item["videoNo"], item["startTime"], item["endTime"])
            if key not in used_nos:
                used_nos.add(key)
                distinct_video_results.append(item)

        distinct_audio_results = []
        for item in audio_results:
            key = (item["videoNo"], item["startTime"], item["endTime"])
            if key not in used_nos:
                used_nos.add(key)
                distinct_audio_results.append(item)

        # 如果去重后某一方为空，跳过此测试用例
        if not distinct_video_results or not distinct_audio_results:
            return

        kb = _build_memeries_kb()
        all_video_nos = _collect_unique_video_nos(distinct_video_results, distinct_audio_results)
        _setup_files_meta_for_video_nos(kb, all_video_nos, data)

        mock_service = MagicMock()
        mock_service.is_configured = MagicMock(return_value=True)
        mock_service.search = AsyncMock(side_effect=[distinct_video_results, distinct_audio_results])

        with patch("src.services.memeries_service.get_memeries_service", return_value=mock_service):
            results = await kb.aquery(query_text="test", db_id="test_db")

        # 合并后的结果数量应等于两个列表的总和（因为 key 都不同）
        expected_count = len(distinct_video_results) + len(distinct_audio_results)
        assert len(results) == expected_count, (
            f"Expected {expected_count} merged results "
            f"({len(distinct_video_results)} video + {len(distinct_audio_results)} audio), "
            f"got {len(results)}"
        )
