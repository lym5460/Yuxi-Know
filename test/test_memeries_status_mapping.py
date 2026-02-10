"""Property-based tests for Memeries videoStatus mapping correctness.

**Validates: Requirements 2.4, 2.5**

Tests that Memeries videoStatus values are correctly mapped to internal FileStatus:
- UNPARSE → indexing
- PARSE → indexed
- FAIL → error_indexing
- API errors → error_indexing
"""

import os
import sys
import threading

# Add project root to path
sys.path.insert(0, os.getcwd())

from unittest.mock import AsyncMock, patch

import pytest
from hypothesis import given, settings, strategies as st

from src.knowledge.base import FileStatus, KnowledgeBase


# =============================================================================
# === 状态映射常量（与 index_file 中的映射保持一致） ===
# =============================================================================

STATUS_MAPPING = {
    "UNPARSE": FileStatus.INDEXING,
    "PARSE": FileStatus.INDEXED,
    "FAIL": FileStatus.ERROR_INDEXING,
}

KNOWN_STATUSES = st.sampled_from(["UNPARSE", "PARSE", "FAIL"])

# 生成未知状态字符串（排除已知状态）
UNKNOWN_STATUSES = st.text(min_size=1, max_size=20).filter(lambda s: s not in STATUS_MAPPING)


# =============================================================================
# === Helpers ===
# =============================================================================


def _build_memeries_kb():
    """创建一个最小化的 MemeriesKB 实例用于测试状态映射"""
    from src.knowledge.implementations.memeries import MemeriesKB

    # 确保类级别的锁已初始化
    if KnowledgeBase._processing_lock is None:
        KnowledgeBase._processing_lock = threading.Lock()

    kb = MemeriesKB.__new__(MemeriesKB)
    kb.work_dir = "/tmp/test_kb"
    kb.files_meta = {}
    return kb


def _setup_file_meta(kb, file_id: str = "test_file_001"):
    """为 KB 实例设置一个可索引的文件元数据"""
    kb.files_meta[file_id] = {
        "file_id": file_id,
        "filename": "test_video.mp4",
        "path": "http://minio:9000/kb-files/test_video.mp4",
        "status": FileStatus.UPLOADED,
        "media_type": "video",
    }
    return file_id


async def _run_index_file(kb, file_id, upload_response=None, upload_error=None, configured=True):
    """执行 index_file 并返回结果，封装所有必要的 mock"""
    from unittest.mock import MagicMock

    mock_service = AsyncMock()
    # is_configured 是同步方法，使用 MagicMock 避免返回 coroutine
    mock_service.is_configured = MagicMock(return_value=configured)
    if upload_error:
        mock_service.upload = AsyncMock(side_effect=upload_error)
    else:
        mock_service.upload = AsyncMock(return_value=upload_response or {})

    mock_minio = AsyncMock()
    mock_minio.adownload_file = AsyncMock(return_value=b"fake_data")

    with (
        patch("src.services.memeries_service.get_memeries_service", return_value=mock_service),
        patch("src.storage.minio.get_minio_client", return_value=mock_minio),
        patch("src.knowledge.utils.kb_utils.parse_minio_url", return_value=("bucket", "object")),
        patch.object(kb, "_save_metadata", new_callable=AsyncMock),
    ):
        return await kb.index_file(db_id="test_db", file_id=file_id)


# =============================================================================
# === Property Tests: 已知状态映射正确性 ===
# =============================================================================


class TestKnownStatusMapping:
    """Property tests for known Memeries videoStatus mapping.

    **Validates: Requirements 2.4, 2.5**
    """

    @given(video_status=KNOWN_STATUSES)
    @settings(max_examples=100)
    @pytest.mark.asyncio
    async def test_known_status_maps_correctly(self, video_status: str):
        """
        Property: For any known Memeries videoStatus (UNPARSE, PARSE, FAIL),
        the system maps it to the correct internal FileStatus.

        - UNPARSE → indexing
        - PARSE → indexed
        - FAIL → error_indexing

        **Validates: Requirements 2.4, 2.5**
        """
        kb = _build_memeries_kb()
        file_id = _setup_file_meta(kb)

        upload_response = {
            "videoNo": "VI123456",
            "videoName": "test_video.mp4",
            "videoStatus": video_status,
            "cause": "some error" if video_status == "FAIL" else None,
        }

        result = await _run_index_file(kb, file_id, upload_response=upload_response)

        expected_status = STATUS_MAPPING[video_status]
        assert result["status"] == expected_status, (
            f"videoStatus '{video_status}' should map to '{expected_status}', "
            f"but got '{result['status']}'"
        )

    @given(video_status=st.sampled_from(["FAIL"]))
    @settings(max_examples=30)
    @pytest.mark.asyncio
    async def test_fail_records_error_info(self, video_status: str):
        """
        Property: FAIL status always maps to 'error_indexing' and records error info.

        **Validates: Requirements 2.4, 2.5**
        """
        kb = _build_memeries_kb()
        file_id = _setup_file_meta(kb)

        upload_response = {
            "videoNo": "VI777",
            "videoName": "test.mp4",
            "videoStatus": video_status,
            "cause": "Processing failed due to codec issue",
        }

        result = await _run_index_file(kb, file_id, upload_response=upload_response)

        assert result["status"] == FileStatus.ERROR_INDEXING
        assert "error" in result, "FAIL status should record error information"


# =============================================================================
# === Property Tests: 未知状态默认映射 ===
# =============================================================================


class TestUnknownStatusMapping:
    """Property tests for unknown/unexpected videoStatus values.

    **Validates: Requirements 2.4**
    """

    @given(video_status=UNKNOWN_STATUSES)
    @settings(max_examples=100)
    @pytest.mark.asyncio
    async def test_unknown_status_defaults_to_indexing(self, video_status: str):
        """
        Property: For any unknown videoStatus value, the system defaults to 'indexing'.

        **Validates: Requirements 2.4**
        """
        kb = _build_memeries_kb()
        file_id = _setup_file_meta(kb)

        upload_response = {
            "videoNo": "VI555",
            "videoName": "test.mp4",
            "videoStatus": video_status,
        }

        result = await _run_index_file(kb, file_id, upload_response=upload_response)

        assert result["status"] == FileStatus.INDEXING, (
            f"Unknown videoStatus '{video_status}' should default to 'indexing', "
            f"but got '{result['status']}'"
        )


# =============================================================================
# === Property Tests: API 错误导致 error_indexing ===
# =============================================================================


class TestApiErrorStatusMapping:
    """Property tests for API error handling and status mapping.

    **Validates: Requirements 2.5**
    """

    @given(
        error_msg=st.text(min_size=1, max_size=100).filter(lambda s: s.strip()),
    )
    @settings(max_examples=100)
    @pytest.mark.asyncio
    async def test_api_error_maps_to_error_indexing(self, error_msg: str):
        """
        Property: For any API error during upload, the file status is set to 'error_indexing'
        and the error message is recorded.

        **Validates: Requirements 2.5**
        """
        kb = _build_memeries_kb()
        file_id = _setup_file_meta(kb)

        with pytest.raises(Exception):
            await _run_index_file(kb, file_id, upload_error=Exception(error_msg))

        assert kb.files_meta[file_id]["status"] == FileStatus.ERROR_INDEXING, (
            f"API error should set status to 'error_indexing', "
            f"but got '{kb.files_meta[file_id]['status']}'"
        )
        assert "error" in kb.files_meta[file_id], "API error should record error message"
        assert kb.files_meta[file_id]["error"] == error_msg

    @given(data=st.data())
    @settings(max_examples=50)
    @pytest.mark.asyncio
    async def test_unconfigured_api_maps_to_error_indexing(self, data):
        """
        Property: When Memeries API is not configured, the file status is set to 'error_indexing'.

        **Validates: Requirements 2.5**
        """
        kb = _build_memeries_kb()
        file_id = _setup_file_meta(kb)

        with pytest.raises(Exception):
            await _run_index_file(kb, file_id, configured=False)

        assert kb.files_meta[file_id]["status"] == FileStatus.ERROR_INDEXING
