"""集成测试: Memeries 媒体知识库上传、搜索和端到端流程

通过 Mock Memeries API 测试完整的上传、搜索和删除流程。
"""

import os
import sys
import threading

sys.path.insert(0, os.getcwd())

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.knowledge.base import FileStatus, KnowledgeBase


# =============================================================================
# === Helpers ===
# =============================================================================


def _build_kb():
    """创建最小化的 MemeriesKB 实例"""
    from src.knowledge.implementations.memeries import MemeriesKB

    if KnowledgeBase._processing_lock is None:
        KnowledgeBase._processing_lock = threading.Lock()

    kb = MemeriesKB.__new__(MemeriesKB)
    kb.work_dir = "/tmp/test_kb"
    kb.files_meta = {}
    kb.databases_meta = {}
    return kb


def _mock_memeries_service(*, configured=True, upload_return=None, search_return=None, delete_return=True):
    """创建 mock MemeriesService"""
    svc = MagicMock()
    svc.is_configured.return_value = configured
    svc.upload = AsyncMock(return_value=upload_return or {})
    svc.search = AsyncMock(return_value=search_return or [])
    svc.delete_videos = AsyncMock(return_value=delete_return)
    svc.get_video_details = AsyncMock(return_value={})
    return svc


# =============================================================================
# === Task 11.1: 上传流程集成测试 ===
# =============================================================================


class TestUploadIntegration:
    """Mock Memeries API 测试完整上传流程"""

    @pytest.mark.asyncio
    async def test_upload_success_unparse_status(self):
        """上传成功，Memeries 返回 UNPARSE 状态 → 文件状态为 indexing"""
        kb = _build_kb()
        file_id = "file_001"
        db_id = "db_test"
        kb.files_meta[file_id] = {
            "filename": "lecture.mp4",
            "path": "http://minio:9000/kb-files/lecture.mp4",
            "status": FileStatus.UPLOADED,
        }

        mock_svc = _mock_memeries_service(
            upload_return={"videoNo": "VI100001", "videoName": "lecture.mp4", "videoStatus": "UNPARSE"}
        )
        mock_minio = MagicMock()
        mock_minio.adownload_file = AsyncMock(return_value=b"fake_video_data")

        with (
            patch("src.services.memeries_service.get_memeries_service", return_value=mock_svc),
            patch("src.storage.minio.get_minio_client", return_value=mock_minio),
            patch("src.knowledge.utils.kb_utils.parse_minio_url", return_value=("kb-files", "lecture.mp4")),
            patch.object(kb, "_save_metadata", new_callable=AsyncMock),
        ):
            result = await kb.index_file(db_id=db_id, file_id=file_id)

        # 验证 Memeries upload 被正确调用
        mock_svc.upload.assert_called_once_with(
            file_path="lecture.mp4",
            file_data=b"fake_video_data",
            unique_id=db_id,
            retain_original_video=True,
        )
        # 验证状态映射
        assert result["status"] == FileStatus.INDEXING
        assert result["memeries_video_no"] == "VI100001"
        assert result["media_type"] == "video"

    @pytest.mark.asyncio
    async def test_upload_success_parse_status(self):
        """上传成功，Memeries 返回 PARSE 状态 → 文件状态为 indexed"""
        kb = _build_kb()
        file_id = "file_002"
        db_id = "db_test"
        kb.files_meta[file_id] = {
            "filename": "podcast.mp3",
            "path": "http://minio:9000/kb-files/podcast.mp3",
            "status": FileStatus.UPLOADED,
        }

        mock_svc = _mock_memeries_service(
            upload_return={"videoNo": "VI200002", "videoName": "podcast.mp3", "videoStatus": "PARSE"}
        )
        mock_minio = MagicMock()
        mock_minio.adownload_file = AsyncMock(return_value=b"fake_audio_data")

        with (
            patch("src.services.memeries_service.get_memeries_service", return_value=mock_svc),
            patch("src.storage.minio.get_minio_client", return_value=mock_minio),
            patch("src.knowledge.utils.kb_utils.parse_minio_url", return_value=("kb-files", "podcast.mp3")),
            patch.object(kb, "_save_metadata", new_callable=AsyncMock),
        ):
            result = await kb.index_file(db_id=db_id, file_id=file_id)

        assert result["status"] == FileStatus.INDEXED
        assert result["memeries_video_no"] == "VI200002"
        assert result["media_type"] == "audio"

    @pytest.mark.asyncio
    async def test_upload_fail_status(self):
        """上传后 Memeries 返回 FAIL 状态 → 文件状态为 error_indexing"""
        kb = _build_kb()
        file_id = "file_003"
        db_id = "db_test"
        kb.files_meta[file_id] = {
            "filename": "broken.avi",
            "path": "http://minio:9000/kb-files/broken.avi",
            "status": FileStatus.UPLOADED,
        }

        mock_svc = _mock_memeries_service(
            upload_return={"videoNo": "VI300003", "videoStatus": "FAIL", "cause": "Codec not supported"}
        )
        mock_minio = MagicMock()
        mock_minio.adownload_file = AsyncMock(return_value=b"data")

        with (
            patch("src.services.memeries_service.get_memeries_service", return_value=mock_svc),
            patch("src.storage.minio.get_minio_client", return_value=mock_minio),
            patch("src.knowledge.utils.kb_utils.parse_minio_url", return_value=("kb-files", "broken.avi")),
            patch.object(kb, "_save_metadata", new_callable=AsyncMock),
        ):
            result = await kb.index_file(db_id=db_id, file_id=file_id)

        assert result["status"] == FileStatus.ERROR_INDEXING
        assert result["error"] == "Codec not supported"

    @pytest.mark.asyncio
    async def test_upload_api_error_marks_error_indexing(self):
        """Memeries API 异常 → 文件状态为 error_indexing 并抛出异常"""
        kb = _build_kb()
        file_id = "file_004"
        db_id = "db_test"
        kb.files_meta[file_id] = {
            "filename": "video.mkv",
            "path": "http://minio:9000/kb-files/video.mkv",
            "status": FileStatus.UPLOADED,
        }

        mock_svc = _mock_memeries_service()
        mock_svc.upload = AsyncMock(side_effect=Exception("Connection refused"))
        mock_minio = MagicMock()
        mock_minio.adownload_file = AsyncMock(return_value=b"data")

        with (
            patch("src.services.memeries_service.get_memeries_service", return_value=mock_svc),
            patch("src.storage.minio.get_minio_client", return_value=mock_minio),
            patch("src.knowledge.utils.kb_utils.parse_minio_url", return_value=("kb-files", "video.mkv")),
            patch.object(kb, "_save_metadata", new_callable=AsyncMock),
        ):
            with pytest.raises(Exception, match="Connection refused"):
                await kb.index_file(db_id=db_id, file_id=file_id)

        assert kb.files_meta[file_id]["status"] == FileStatus.ERROR_INDEXING

    @pytest.mark.asyncio
    async def test_upload_rejects_unsupported_format(self):
        """上传不支持的文件格式 → 抛出 ValueError"""
        kb = _build_kb()
        file_id = "file_005"
        kb.files_meta[file_id] = {
            "filename": "document.pdf",
            "path": "http://minio:9000/kb-files/document.pdf",
            "status": FileStatus.UPLOADED,
        }

        with pytest.raises(ValueError, match="Unsupported file format"):
            await kb.index_file(db_id="db_test", file_id=file_id)

    @pytest.mark.asyncio
    async def test_upload_retry_from_error_indexing(self):
        """从 error_indexing 状态重新上传"""
        kb = _build_kb()
        file_id = "file_006"
        db_id = "db_test"
        kb.files_meta[file_id] = {
            "filename": "retry.wav",
            "path": "http://minio:9000/kb-files/retry.wav",
            "status": FileStatus.ERROR_INDEXING,
            "error": "Previous error",
        }

        mock_svc = _mock_memeries_service(
            upload_return={"videoNo": "VI600006", "videoStatus": "PARSE"}
        )
        mock_minio = MagicMock()
        mock_minio.adownload_file = AsyncMock(return_value=b"audio_data")

        with (
            patch("src.services.memeries_service.get_memeries_service", return_value=mock_svc),
            patch("src.storage.minio.get_minio_client", return_value=mock_minio),
            patch("src.knowledge.utils.kb_utils.parse_minio_url", return_value=("kb-files", "retry.wav")),
            patch.object(kb, "_save_metadata", new_callable=AsyncMock),
        ):
            result = await kb.index_file(db_id=db_id, file_id=file_id)

        assert result["status"] == FileStatus.INDEXED
        assert "error" not in result


# =============================================================================
# === Task 11.2: 搜索流程集成测试 ===
# =============================================================================


class TestSearchIntegration:
    """Mock Memeries API 测试搜索和结果合并"""

    @pytest.mark.asyncio
    async def test_search_merges_video_and_audio_results(self):
        """搜索同时执行 BY_VIDEO 和 BY_AUDIO，结果合并并按 score 降序"""
        kb = _build_kb()
        db_id = "db_search"
        kb.files_meta["file_a"] = {
            "filename": "lecture.mp4",
            "media_type": "video",
            "memeries_video_no": "VI001",
            "path": "http://minio:9000/kb-files/lecture.mp4",
            "status": FileStatus.INDEXED,
        }

        video_results = [
            {"videoNo": "VI001", "startTime": "10", "endTime": "20", "score": 0.8},
        ]
        audio_results = [
            {"videoNo": "VI001", "startTime": "30", "endTime": "40", "score": 0.9},
        ]

        mock_svc = _mock_memeries_service()
        mock_svc.search = AsyncMock(side_effect=[video_results, audio_results])

        with patch("src.services.memeries_service.get_memeries_service", return_value=mock_svc):
            results = await kb.aquery(query_text="关键内容", db_id=db_id)

        # 验证两次搜索调用
        assert mock_svc.search.call_count == 2
        calls = mock_svc.search.call_args_list
        assert calls[0].kwargs["search_type"] == "BY_VIDEO"
        assert calls[1].kwargs["search_type"] == "BY_AUDIO"

        # 验证结果按 score 降序
        assert len(results) == 2
        assert results[0]["score"] == 0.9
        assert results[1]["score"] == 0.8

    @pytest.mark.asyncio
    async def test_search_deduplicates_same_segment(self):
        """相同 videoNo + startTime + endTime 的结果去重，保留高分"""
        kb = _build_kb()
        db_id = "db_dedup"
        kb.files_meta["file_b"] = {
            "filename": "talk.mp4",
            "media_type": "video",
            "memeries_video_no": "VI002",
            "path": "http://minio:9000/kb-files/talk.mp4",
            "status": FileStatus.INDEXED,
        }

        # 同一片段在 BY_VIDEO 和 BY_AUDIO 中都出现
        video_results = [
            {"videoNo": "VI002", "startTime": "5", "endTime": "15", "score": 0.6},
        ]
        audio_results = [
            {"videoNo": "VI002", "startTime": "5", "endTime": "15", "score": 0.85},
        ]

        mock_svc = _mock_memeries_service()
        mock_svc.search = AsyncMock(side_effect=[video_results, audio_results])

        with patch("src.services.memeries_service.get_memeries_service", return_value=mock_svc):
            results = await kb.aquery(query_text="重复片段", db_id=db_id)

        # 去重后只有一条，保留高分
        assert len(results) == 1
        assert results[0]["score"] == 0.85

    @pytest.mark.asyncio
    async def test_search_result_fields_complete(self):
        """搜索结果包含所有必需字段"""
        kb = _build_kb()
        db_id = "db_fields"
        kb.files_meta["file_c"] = {
            "filename": "interview.m4a",
            "media_type": "audio",
            "memeries_video_no": "VI003",
            "path": "http://minio:9000/kb-files/interview.m4a",
            "status": FileStatus.INDEXED,
        }

        mock_svc = _mock_memeries_service()
        mock_svc.search = AsyncMock(side_effect=[
            [{"videoNo": "VI003", "startTime": "0", "endTime": "10", "score": 0.7}],
            [],
        ])

        with patch("src.services.memeries_service.get_memeries_service", return_value=mock_svc):
            results = await kb.aquery(query_text="访谈", db_id=db_id)

        assert len(results) == 1
        required_fields = {"media_id", "media_name", "media_type", "start_time", "end_time", "score", "media_url"}
        assert required_fields.issubset(results[0].keys())
        assert results[0]["media_name"] == "interview.m4a"
        assert results[0]["media_type"] == "audio"
        assert isinstance(results[0]["start_time"], float)
        assert isinstance(results[0]["end_time"], float)

    @pytest.mark.asyncio
    async def test_search_empty_results(self):
        """搜索无结果时返回空列表"""
        kb = _build_kb()
        mock_svc = _mock_memeries_service()
        mock_svc.search = AsyncMock(return_value=[])

        with patch("src.services.memeries_service.get_memeries_service", return_value=mock_svc):
            results = await kb.aquery(query_text="不存在的内容", db_id="db_empty")

        assert results == []

    @pytest.mark.asyncio
    async def test_search_api_error_returns_empty(self):
        """搜索 API 异常时返回空列表"""
        kb = _build_kb()
        mock_svc = _mock_memeries_service()
        mock_svc.search = AsyncMock(side_effect=Exception("API timeout"))

        with patch("src.services.memeries_service.get_memeries_service", return_value=mock_svc):
            results = await kb.aquery(query_text="超时", db_id="db_error")

        assert results == []

    @pytest.mark.asyncio
    async def test_search_url_fallback_to_minio(self):
        """Memeries video_url 为空时回退到 MinIO URL"""
        kb = _build_kb()
        db_id = "db_fallback"
        minio_url = "http://minio:9000/kb-files/fallback.mp4"
        kb.files_meta["file_d"] = {
            "filename": "fallback.mp4",
            "media_type": "video",
            "memeries_video_no": "VI004",
            "path": minio_url,
            "status": FileStatus.INDEXED,
        }

        mock_svc = _mock_memeries_service()
        # video_url 为空
        mock_svc.search = AsyncMock(side_effect=[
            [{"videoNo": "VI004", "startTime": "0", "endTime": "5", "score": 0.5, "video_url": ""}],
            [],
        ])

        with patch("src.services.memeries_service.get_memeries_service", return_value=mock_svc):
            results = await kb.aquery(query_text="回退", db_id=db_id)

        assert len(results) == 1
        assert results[0]["media_url"] == minio_url


# =============================================================================
# === Task 11.3: 端到端测试（上传 → 搜索 → 删除） ===
# =============================================================================


class TestEndToEnd:
    """测试从上传到搜索到删除的完整流程"""

    @pytest.mark.asyncio
    async def test_full_lifecycle_upload_search_delete(self):
        """完整生命周期：上传文件 → 搜索内容 → 删除文件"""
        kb = _build_kb()
        file_id = "file_e2e"
        db_id = "db_e2e"
        filename = "surgery.mp4"
        minio_path = "http://minio:9000/kb-files/surgery.mp4"

        # === Phase 1: 上传 ===
        kb.files_meta[file_id] = {
            "filename": filename,
            "path": minio_path,
            "status": FileStatus.UPLOADED,
        }

        mock_svc = _mock_memeries_service(
            upload_return={"videoNo": "VI999999", "videoName": filename, "videoStatus": "PARSE"}
        )
        mock_minio = MagicMock()
        mock_minio.adownload_file = AsyncMock(return_value=b"video_bytes")
        mock_minio.adelete_file = AsyncMock()

        mock_file_repo = MagicMock()
        mock_file_repo.delete = AsyncMock()

        with (
            patch("src.services.memeries_service.get_memeries_service", return_value=mock_svc),
            patch("src.storage.minio.get_minio_client", return_value=mock_minio),
            patch("src.knowledge.utils.kb_utils.parse_minio_url", return_value=("kb-files", "surgery.mp4")),
            patch.object(kb, "_save_metadata", new_callable=AsyncMock),
        ):
            upload_result = await kb.index_file(db_id=db_id, file_id=file_id)

        assert upload_result["status"] == FileStatus.INDEXED
        assert upload_result["memeries_video_no"] == "VI999999"
        assert upload_result["media_type"] == "video"

        # === Phase 2: 搜索 ===
        mock_svc.search = AsyncMock(side_effect=[
            [{"videoNo": "VI999999", "startTime": "13", "endTime": "18", "score": 0.92}],
            [{"videoNo": "VI999999", "startTime": "25", "endTime": "30", "score": 0.75}],
        ])

        with patch("src.services.memeries_service.get_memeries_service", return_value=mock_svc):
            search_results = await kb.aquery(query_text="手术缝合", db_id=db_id)

        assert len(search_results) == 2
        assert search_results[0]["score"] == 0.92
        assert search_results[0]["media_id"] == "VI999999"
        assert search_results[0]["media_name"] == filename
        assert search_results[0]["start_time"] == 13.0
        assert search_results[0]["end_time"] == 18.0

        # === Phase 3: 删除 ===
        with (
            patch("src.services.memeries_service.get_memeries_service", return_value=mock_svc),
            patch("src.storage.minio.get_minio_client", return_value=mock_minio),
            patch("src.knowledge.utils.kb_utils.parse_minio_url", return_value=("kb-files", "surgery.mp4")),
            patch("src.repositories.knowledge_file_repository.KnowledgeFileRepository", return_value=mock_file_repo),
            patch.object(kb, "_save_metadata", new_callable=AsyncMock),
        ):
            await kb.delete_file(db_id=db_id, file_id=file_id)

        # 验证 Memeries 和 MinIO 都被调用
        mock_svc.delete_videos.assert_called_once_with(["VI999999"], unique_id=db_id)
        mock_minio.adelete_file.assert_called_once_with("kb-files", "surgery.mp4")
        # 元数据已清理
        assert file_id not in kb.files_meta

    @pytest.mark.asyncio
    async def test_lifecycle_upload_fail_retry_search(self):
        """上传失败 → 重试成功 → 搜索"""
        kb = _build_kb()
        file_id = "file_retry"
        db_id = "db_retry"
        kb.files_meta[file_id] = {
            "filename": "audio.flac",
            "path": "http://minio:9000/kb-files/audio.flac",
            "status": FileStatus.UPLOADED,
        }

        # 第一次上传失败
        mock_svc = _mock_memeries_service()
        mock_svc.upload = AsyncMock(side_effect=Exception("Server error"))
        mock_minio = MagicMock()
        mock_minio.adownload_file = AsyncMock(return_value=b"audio_data")

        with (
            patch("src.services.memeries_service.get_memeries_service", return_value=mock_svc),
            patch("src.storage.minio.get_minio_client", return_value=mock_minio),
            patch("src.knowledge.utils.kb_utils.parse_minio_url", return_value=("kb-files", "audio.flac")),
            patch.object(kb, "_save_metadata", new_callable=AsyncMock),
        ):
            with pytest.raises(Exception, match="Server error"):
                await kb.index_file(db_id=db_id, file_id=file_id)

        assert kb.files_meta[file_id]["status"] == FileStatus.ERROR_INDEXING

        # 重试成功
        mock_svc.upload = AsyncMock(
            return_value={"videoNo": "VI888888", "videoStatus": "PARSE"}
        )

        with (
            patch("src.services.memeries_service.get_memeries_service", return_value=mock_svc),
            patch("src.storage.minio.get_minio_client", return_value=mock_minio),
            patch("src.knowledge.utils.kb_utils.parse_minio_url", return_value=("kb-files", "audio.flac")),
            patch.object(kb, "_save_metadata", new_callable=AsyncMock),
        ):
            result = await kb.index_file(db_id=db_id, file_id=file_id)

        assert result["status"] == FileStatus.INDEXED

        # 搜索
        mock_svc.search = AsyncMock(side_effect=[
            [{"videoNo": "VI888888", "startTime": "0", "endTime": "60", "score": 0.88}],
            [],
        ])

        with patch("src.services.memeries_service.get_memeries_service", return_value=mock_svc):
            results = await kb.aquery(query_text="音频内容", db_id=db_id)

        assert len(results) == 1
        assert results[0]["media_type"] == "audio"
        assert results[0]["score"] == 0.88
