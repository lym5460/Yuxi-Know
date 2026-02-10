"""Property-based tests for Memeries URL fallback logic (Property 10).

**Validates: Requirements 4.5**

Tests that when Memeries video_url is empty or null, the system falls back
to the MinIO stored original file URL as the playback address.
"""

import os
import sys
import threading

sys.path.insert(0, os.getcwd())

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from hypothesis import given, settings, strategies as st

from src.knowledge.base import KnowledgeBase


# =============================================================================
# === Strategies ===
# =============================================================================

video_nos = st.builds(lambda n: f"VI{n}", n=st.integers(min_value=1, max_value=999999999))

time_values = st.integers(min_value=0, max_value=36000).map(str)

scores = st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)

# 非空的 video_url（Memeries 返回的播放地址）
non_empty_video_urls = st.builds(
    lambda name: f"https://memeries.example.com/videos/{name}.mp4",
    name=st.text(
        min_size=1,
        max_size=20,
        alphabet=st.characters(whitelist_categories=("L", "N"), whitelist_characters="_-"),
    ),
)

# 空或 null 的 video_url
empty_video_urls = st.sampled_from(["", None])

minio_paths = st.builds(
    lambda name: f"http://minio:9000/kb-files/{name}",
    name=st.text(
        min_size=1,
        max_size=30,
        alphabet=st.characters(whitelist_categories=("L", "N"), whitelist_characters="_-."),
    ),
)

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


def _make_search_result(video_no: str, start_time: str, end_time: str, score: float, video_url=None) -> dict:
    """构建 Memeries 搜索结果项"""
    result = {
        "videoNo": video_no,
        "startTime": start_time,
        "endTime": end_time,
        "score": score,
    }
    if video_url is not None:
        result["video_url"] = video_url
    return result


# =============================================================================
# === Property Tests: URL 回退逻辑 ===
# =============================================================================


class TestUrlFallback:
    """Property tests for URL fallback logic.

    **Validates: Requirements 4.5**
    """

    @given(
        video_no=video_nos,
        start_time=time_values,
        end_time=time_values,
        score=scores,
        video_url=non_empty_video_urls,
        minio_path=minio_paths,
        filename=media_filenames,
        media_type=media_types,
    )
    @settings(max_examples=100)
    @pytest.mark.asyncio
    async def test_uses_video_url_when_provided(
        self,
        video_no: str,
        start_time: str,
        end_time: str,
        score: float,
        video_url: str,
        minio_path: str,
        filename: str,
        media_type: str,
    ):
        """
        Property: When Memeries returns a non-empty video_url, it must be used
        as the media_url in the result, NOT the MinIO path.

        **Validates: Requirements 4.5**
        """
        kb = _build_memeries_kb()
        kb.files_meta["file_1"] = {
            "filename": filename,
            "path": minio_path,
            "status": "indexed",
            "media_type": media_type,
            "memeries_video_no": video_no,
        }

        search_result = _make_search_result(video_no, start_time, end_time, score, video_url=video_url)

        mock_service = MagicMock()
        mock_service.is_configured = MagicMock(return_value=True)
        mock_service.search = AsyncMock(side_effect=[[search_result], []])

        with patch("src.services.memeries_service.get_memeries_service", return_value=mock_service):
            results = await kb.aquery(query_text="test", db_id="test_db")

        assert len(results) == 1
        assert results[0]["media_url"] == video_url, (
            f"Expected media_url to be Memeries video_url '{video_url}', "
            f"but got '{results[0]['media_url']}'"
        )

    @given(
        video_no=video_nos,
        start_time=time_values,
        end_time=time_values,
        score=scores,
        empty_url=empty_video_urls,
        minio_path=minio_paths,
        filename=media_filenames,
        media_type=media_types,
    )
    @settings(max_examples=100)
    @pytest.mark.asyncio
    async def test_falls_back_to_minio_when_video_url_empty(
        self,
        video_no: str,
        start_time: str,
        end_time: str,
        score: float,
        empty_url: str | None,
        minio_path: str,
        filename: str,
        media_type: str,
    ):
        """
        Property: When Memeries video_url is empty or null, the system must
        fall back to the MinIO stored original file URL as the playback address.

        **Validates: Requirements 4.5**
        """
        kb = _build_memeries_kb()
        kb.files_meta["file_1"] = {
            "filename": filename,
            "path": minio_path,
            "status": "indexed",
            "media_type": media_type,
            "memeries_video_no": video_no,
        }

        search_result = _make_search_result(video_no, start_time, end_time, score, video_url=empty_url)

        mock_service = MagicMock()
        mock_service.is_configured = MagicMock(return_value=True)
        mock_service.search = AsyncMock(side_effect=[[search_result], []])

        with patch("src.services.memeries_service.get_memeries_service", return_value=mock_service):
            results = await kb.aquery(query_text="test", db_id="test_db")

        assert len(results) == 1
        assert results[0]["media_url"] == minio_path, (
            f"Expected media_url to fall back to MinIO path '{minio_path}', "
            f"but got '{results[0]['media_url']}'"
        )

    @given(
        video_no=video_nos,
        start_time=time_values,
        end_time=time_values,
        score=scores,
        minio_path=minio_paths,
        filename=media_filenames,
        media_type=media_types,
    )
    @settings(max_examples=100)
    @pytest.mark.asyncio
    async def test_falls_back_to_minio_when_video_url_absent(
        self,
        video_no: str,
        start_time: str,
        end_time: str,
        score: float,
        minio_path: str,
        filename: str,
        media_type: str,
    ):
        """
        Property: When Memeries search result does not contain a video_url field
        at all, the system must fall back to the MinIO stored original file URL.

        **Validates: Requirements 4.5**
        """
        kb = _build_memeries_kb()
        kb.files_meta["file_1"] = {
            "filename": filename,
            "path": minio_path,
            "status": "indexed",
            "media_type": media_type,
            "memeries_video_no": video_no,
        }

        # 不包含 video_url 字段
        search_result = _make_search_result(video_no, start_time, end_time, score)

        mock_service = MagicMock()
        mock_service.is_configured = MagicMock(return_value=True)
        mock_service.search = AsyncMock(side_effect=[[search_result], []])

        with patch("src.services.memeries_service.get_memeries_service", return_value=mock_service):
            results = await kb.aquery(query_text="test", db_id="test_db")

        assert len(results) == 1
        assert results[0]["media_url"] == minio_path, (
            f"Expected media_url to fall back to MinIO path '{minio_path}', "
            f"but got '{results[0]['media_url']}'"
        )
