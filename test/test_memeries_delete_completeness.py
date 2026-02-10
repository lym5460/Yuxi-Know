"""Property-based tests for Memeries delete completeness (Property 9).

**Validates: Requirements 9.3**

Tests that delete_file() simultaneously cleans up both MinIO files and Memeries indexes.
If Memeries delete fails, MinIO delete still proceeds.
If MinIO delete fails, metadata is still cleaned up.
Files without memeries_video_no skip the Memeries delete call.
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

file_ids = st.builds(
    lambda n: f"file_{n}",
    n=st.integers(min_value=1, max_value=999999),
)

db_ids = st.builds(
    lambda n: f"db_{n}",
    n=st.integers(min_value=1, max_value=999999),
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

minio_paths = st.builds(
    lambda name: f"http://minio:9000/kb-files/{name}",
    name=st.text(
        min_size=1,
        max_size=30,
        alphabet=st.characters(whitelist_categories=("L", "N"), whitelist_characters="_-."),
    ),
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


def _make_file_meta(*, filename: str, path: str, video_no: str | None = None) -> dict:
    """构建文件元数据"""
    meta = {
        "filename": filename,
        "path": path,
        "status": "indexed",
        "media_type": "video",
    }
    if video_no is not None:
        meta["memeries_video_no"] = video_no
    return meta


def _create_mocks(*, memeries_configured: bool = True, memeries_delete_side_effect=None, minio_delete_side_effect=None):
    """创建 mock 对象"""
    mock_service = MagicMock()
    mock_service.is_configured = MagicMock(return_value=memeries_configured)
    mock_service.delete_videos = AsyncMock(side_effect=memeries_delete_side_effect)

    mock_minio = MagicMock()
    mock_minio.adelete_file = AsyncMock(side_effect=minio_delete_side_effect)

    mock_file_repo_instance = MagicMock()
    mock_file_repo_instance.delete = AsyncMock()

    return mock_service, mock_minio, mock_file_repo_instance


# =============================================================================
# === Property Tests: 删除完整性 ===
# =============================================================================


class TestDeleteCompleteness:
    """Property tests for delete completeness.

    **Validates: Requirements 9.3**
    """

    @given(
        file_id=file_ids,
        db_id=db_ids,
        video_no=video_nos,
        filename=media_filenames,
        path=minio_paths,
    )
    @settings(max_examples=100)
    @pytest.mark.asyncio
    async def test_delete_calls_both_minio_and_memeries(
        self,
        file_id: str,
        db_id: str,
        video_no: str,
        filename: str,
        path: str,
    ):
        """
        Property: For any file with a memeries_video_no, delete_file() must call
        both MinIO delete and Memeries delete_videos.

        **Validates: Requirements 9.3**
        """
        kb = _build_memeries_kb()
        kb.files_meta[file_id] = _make_file_meta(filename=filename, path=path, video_no=video_no)

        mock_service, mock_minio, mock_file_repo = _create_mocks()

        with (
            patch("src.services.memeries_service.get_memeries_service", return_value=mock_service),
            patch("src.storage.minio.get_minio_client", return_value=mock_minio),
            patch("src.knowledge.utils.kb_utils.parse_minio_url", return_value=("bucket", "object")),
            patch("src.repositories.knowledge_file_repository.KnowledgeFileRepository", return_value=mock_file_repo),
            patch.object(kb, "_save_metadata", new_callable=AsyncMock),
        ):
            await kb.delete_file(db_id=db_id, file_id=file_id)

        # 验证 Memeries delete_videos 被调用
        mock_service.delete_videos.assert_called_once_with([video_no], unique_id=db_id)

        # 验证 MinIO adelete_file 被调用
        mock_minio.adelete_file.assert_called_once_with("bucket", "object")

    @given(
        file_id=file_ids,
        db_id=db_ids,
        video_no=video_nos,
        filename=media_filenames,
        path=minio_paths,
    )
    @settings(max_examples=100)
    @pytest.mark.asyncio
    async def test_minio_delete_proceeds_when_memeries_fails(
        self,
        file_id: str,
        db_id: str,
        video_no: str,
        filename: str,
        path: str,
    ):
        """
        Property: If Memeries delete fails, MinIO delete must still proceed.
        Errors are logged but do not block MinIO file deletion.

        **Validates: Requirements 9.3**
        """
        kb = _build_memeries_kb()
        kb.files_meta[file_id] = _make_file_meta(filename=filename, path=path, video_no=video_no)

        mock_service, mock_minio, mock_file_repo = _create_mocks(
            memeries_delete_side_effect=Exception("Memeries API error"),
        )

        with (
            patch("src.services.memeries_service.get_memeries_service", return_value=mock_service),
            patch("src.storage.minio.get_minio_client", return_value=mock_minio),
            patch("src.knowledge.utils.kb_utils.parse_minio_url", return_value=("bucket", "object")),
            patch("src.repositories.knowledge_file_repository.KnowledgeFileRepository", return_value=mock_file_repo),
            patch.object(kb, "_save_metadata", new_callable=AsyncMock),
        ):
            await kb.delete_file(db_id=db_id, file_id=file_id)

        # Memeries 失败后，MinIO 删除仍然被调用
        mock_minio.adelete_file.assert_called_once_with("bucket", "object")

    @given(
        file_id=file_ids,
        db_id=db_ids,
        video_no=video_nos,
        filename=media_filenames,
        path=minio_paths,
    )
    @settings(max_examples=100)
    @pytest.mark.asyncio
    async def test_metadata_cleaned_when_minio_fails(
        self,
        file_id: str,
        db_id: str,
        video_no: str,
        filename: str,
        path: str,
    ):
        """
        Property: If MinIO delete fails, metadata must still be cleaned up
        (file removed from files_meta and database record deleted).

        **Validates: Requirements 9.3**
        """
        kb = _build_memeries_kb()
        kb.files_meta[file_id] = _make_file_meta(filename=filename, path=path, video_no=video_no)

        mock_service, mock_minio, mock_file_repo = _create_mocks(
            minio_delete_side_effect=Exception("MinIO connection error"),
        )

        with (
            patch("src.services.memeries_service.get_memeries_service", return_value=mock_service),
            patch("src.storage.minio.get_minio_client", return_value=mock_minio),
            patch("src.knowledge.utils.kb_utils.parse_minio_url", return_value=("bucket", "object")),
            patch("src.repositories.knowledge_file_repository.KnowledgeFileRepository", return_value=mock_file_repo),
            patch.object(kb, "_save_metadata", new_callable=AsyncMock),
        ):
            await kb.delete_file(db_id=db_id, file_id=file_id)

        # 元数据应被清理
        assert file_id not in kb.files_meta, "File should be removed from files_meta even if MinIO delete fails"

        # 数据库记录应被删除
        mock_file_repo.delete.assert_called_once_with(file_id)

    @given(
        file_id=file_ids,
        db_id=db_ids,
        filename=media_filenames,
        path=minio_paths,
    )
    @settings(max_examples=100)
    @pytest.mark.asyncio
    async def test_skip_memeries_delete_without_video_no(
        self,
        file_id: str,
        db_id: str,
        filename: str,
        path: str,
    ):
        """
        Property: Files without memeries_video_no must skip the Memeries
        delete_videos call, but still delete from MinIO and clean metadata.

        **Validates: Requirements 9.3**
        """
        kb = _build_memeries_kb()
        # 不设置 memeries_video_no
        kb.files_meta[file_id] = _make_file_meta(filename=filename, path=path, video_no=None)

        mock_service, mock_minio, mock_file_repo = _create_mocks()

        with (
            patch("src.services.memeries_service.get_memeries_service", return_value=mock_service),
            patch("src.storage.minio.get_minio_client", return_value=mock_minio),
            patch("src.knowledge.utils.kb_utils.parse_minio_url", return_value=("bucket", "object")),
            patch("src.repositories.knowledge_file_repository.KnowledgeFileRepository", return_value=mock_file_repo),
            patch.object(kb, "_save_metadata", new_callable=AsyncMock),
        ):
            await kb.delete_file(db_id=db_id, file_id=file_id)

        # Memeries delete_videos 不应被调用
        mock_service.delete_videos.assert_not_called()

        # MinIO 删除仍然被调用
        mock_minio.adelete_file.assert_called_once()

        # 元数据应被清理
        assert file_id not in kb.files_meta
