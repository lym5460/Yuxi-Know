"""Unit tests for MemeriesKB methods (Task 2.5).

Tests _create_kb_instance, _initialize_kb_instance, update_content,
get_file_basic_info, get_file_content, get_file_info, and get_query_params_config.
"""

import os
import sys

sys.path.insert(0, os.getcwd())

import pytest
import pytest_asyncio

from src.knowledge.implementations.memeries import MemeriesKB


@pytest_asyncio.fixture
async def memeries_kb(tmp_path):
    """Create a MemeriesKB instance with a temporary work directory."""
    kb = MemeriesKB(work_dir=str(tmp_path))
    # 模拟已加载的 files_meta
    kb.files_meta = {
        "file_001": {
            "filename": "test_video.mp4",
            "path": "http://minio:9000/kb-files/test_video.mp4",
            "status": "indexed",
            "media_type": "video",
            "memeries_video_no": "VI123456",
            "duration": 120,
        },
        "file_002": {
            "filename": "test_audio.mp3",
            "path": "http://minio:9000/kb-files/test_audio.mp3",
            "status": "indexing",
            "media_type": "audio",
            "memeries_video_no": "VI789012",
        },
    }
    return kb


class TestCreateAndInitialize:
    """Tests for _create_kb_instance and _initialize_kb_instance."""

    @pytest.mark.asyncio
    async def test_create_kb_instance_returns_none(self, memeries_kb):
        """Memeries 是远程 API，不需要本地实例。"""
        result = await memeries_kb._create_kb_instance("db_001", {})
        assert result is None

    @pytest.mark.asyncio
    async def test_initialize_kb_instance_is_noop(self, memeries_kb):
        """初始化应为空操作，不抛出异常。"""
        await memeries_kb._initialize_kb_instance(None)


class TestUpdateContent:
    """Tests for update_content."""

    @pytest.mark.asyncio
    async def test_update_content_raises_not_implemented(self, memeries_kb):
        """媒体文件不支持重新解析。"""
        with pytest.raises(NotImplementedError):
            await memeries_kb.update_content("db_001", ["file_001"])


class TestGetFileBasicInfo:
    """Tests for get_file_basic_info."""

    @pytest.mark.asyncio
    async def test_returns_meta_for_existing_file(self, memeries_kb):
        """返回包含 meta 键的字典。"""
        result = await memeries_kb.get_file_basic_info("db_001", "file_001")
        assert "meta" in result
        assert result["meta"]["filename"] == "test_video.mp4"
        assert result["meta"]["media_type"] == "video"

    @pytest.mark.asyncio
    async def test_raises_for_nonexistent_file(self, memeries_kb):
        """不存在的文件应抛出异常。"""
        with pytest.raises(Exception, match="File not found"):
            await memeries_kb.get_file_basic_info("db_001", "nonexistent")


class TestGetFileContent:
    """Tests for get_file_content."""

    @pytest.mark.asyncio
    async def test_returns_empty_lines(self, memeries_kb):
        """媒体文件没有文本 chunks，返回空 lines。"""
        result = await memeries_kb.get_file_content("db_001", "file_001")
        assert result == {"lines": []}

    @pytest.mark.asyncio
    async def test_raises_for_nonexistent_file(self, memeries_kb):
        """不存在的文件应抛出异常。"""
        with pytest.raises(Exception, match="File not found"):
            await memeries_kb.get_file_content("db_001", "nonexistent")


class TestGetFileInfo:
    """Tests for get_file_info."""

    @pytest.mark.asyncio
    async def test_merges_basic_and_content_info(self, memeries_kb):
        """应合并 basic_info 和 content_info。"""
        result = await memeries_kb.get_file_info("db_001", "file_001")
        assert "meta" in result
        assert "lines" in result
        assert result["meta"]["filename"] == "test_video.mp4"
        assert result["lines"] == []

    @pytest.mark.asyncio
    async def test_raises_for_nonexistent_file(self, memeries_kb):
        """不存在的文件应抛出异常。"""
        with pytest.raises(Exception, match="File not found"):
            await memeries_kb.get_file_info("db_001", "nonexistent")


class TestGetQueryParamsConfig:
    """Tests for get_query_params_config."""

    def test_returns_memeries_type(self, memeries_kb):
        """type 应为 memeries。"""
        config = memeries_kb.get_query_params_config("db_001")
        assert config["type"] == "memeries"

    def test_has_top_k_option(self, memeries_kb):
        """应包含 top_k 选项。"""
        config = memeries_kb.get_query_params_config("db_001")
        options = config["options"]
        assert len(options) >= 1
        top_k = options[0]
        assert top_k["key"] == "top_k"
        assert top_k["type"] == "number"
        assert top_k["default"] == 5
        assert top_k["min"] == 1
        assert top_k["max"] == 20


class TestKbType:
    """Tests for kb_type property."""

    def test_kb_type_is_memeries(self, memeries_kb):
        assert memeries_kb.kb_type == "memeries"
