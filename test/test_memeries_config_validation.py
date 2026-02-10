"""Memeries 配置验证测试

测试 MemeriesService 的 API Key 配置验证逻辑和 MemeriesKB 创建时的配置检查。

Validates: Requirements 10.2, 10.3, 10.4
"""

from unittest.mock import MagicMock, patch

import pytest

from src.services.memeries_service import MemeriesService


# =============================================================================
# === API Key 格式验证测试 (Requirement 10.3) ===
# =============================================================================


class TestValidateApiKeyFormat:
    """测试 _validate_api_key_format 静态方法"""

    def test_valid_key(self):
        """有效的 API Key 应返回 True"""
        assert MemeriesService._validate_api_key_format("sk-abcdef12345678") is True

    def test_valid_key_exactly_8_chars(self):
        """恰好 8 个字符的 key 应有效"""
        assert MemeriesService._validate_api_key_format("12345678") is True

    def test_empty_string(self):
        """空字符串应返回 False"""
        assert MemeriesService._validate_api_key_format("") is False

    def test_too_short(self):
        """少于 8 个字符应返回 False"""
        assert MemeriesService._validate_api_key_format("short") is False
        assert MemeriesService._validate_api_key_format("1234567") is False

    def test_whitespace_only(self):
        """纯空白字符应返回 False"""
        assert MemeriesService._validate_api_key_format("        ") is False

    def test_leading_trailing_whitespace(self):
        """前后有空白字符应返回 False"""
        assert MemeriesService._validate_api_key_format("  sk-abcdef12  ") is False
        assert MemeriesService._validate_api_key_format(" sk-abcdef12") is False
        assert MemeriesService._validate_api_key_format("sk-abcdef12 ") is False


# =============================================================================
# === is_configured 测试 (Requirement 10.2) ===
# =============================================================================


class TestIsConfigured:
    """测试 is_configured 方法"""

    @patch.dict("os.environ", {"MEMERIES_API_KEY": "valid-api-key-12345"}, clear=False)
    def test_configured_with_valid_key(self):
        """有效 API Key 时 is_configured 返回 True"""
        service = MemeriesService()
        assert service.is_configured() is True

    @patch.dict("os.environ", {}, clear=False)
    def test_not_configured_without_key(self):
        """未设置 API Key 时 is_configured 返回 False"""
        import os

        os.environ.pop("MEMERIES_API_KEY", None)
        service = MemeriesService()
        assert service.is_configured() is False

    @patch.dict("os.environ", {"MEMERIES_API_KEY": "short"}, clear=False)
    def test_not_configured_with_invalid_format(self):
        """API Key 格式无效时 is_configured 返回 False"""
        service = MemeriesService()
        assert service.is_configured() is False


# =============================================================================
# === 初始化日志测试 (Requirement 10.4) ===
# =============================================================================


class TestInitLogging:
    """测试 MemeriesService 初始化时的日志行为（不阻止系统启动）"""

    @patch.dict("os.environ", {}, clear=False)
    def test_no_crash_when_key_missing(self):
        """API Key 缺失时系统不应崩溃"""
        import os

        os.environ.pop("MEMERIES_API_KEY", None)
        # 初始化不应抛出异常
        service = MemeriesService()
        assert service is not None
        assert service.is_configured() is False

    @patch.dict("os.environ", {"MEMERIES_API_KEY": "short"}, clear=False)
    def test_no_crash_when_key_format_invalid(self):
        """API Key 格式无效时系统不应崩溃"""
        service = MemeriesService()
        assert service is not None
        assert service.is_configured() is False

    @patch.dict("os.environ", {"MEMERIES_API_KEY": "valid-api-key-12345"}, clear=False)
    def test_no_crash_when_configured(self):
        """配置正确时系统正常初始化"""
        service = MemeriesService()
        assert service is not None
        assert service.is_configured() is True

    @patch.dict("os.environ", {}, clear=False)
    @patch("src.services.memeries_service.logger")
    def test_warning_logged_when_key_missing(self, mock_logger):
        """API Key 缺失时应记录警告日志"""
        import os

        os.environ.pop("MEMERIES_API_KEY", None)
        MemeriesService()
        mock_logger.warning.assert_called_once()
        assert "not configured" in mock_logger.warning.call_args[0][0]

    @patch.dict("os.environ", {"MEMERIES_API_KEY": "short"}, clear=False)
    @patch("src.services.memeries_service.logger")
    def test_warning_logged_when_key_format_invalid(self, mock_logger):
        """API Key 格式无效时应记录警告日志"""
        MemeriesService()
        mock_logger.warning.assert_called_once()
        assert "invalid" in mock_logger.warning.call_args[0][0].lower()


# =============================================================================
# === 创建知识库时的配置检查 (Requirement 10.2) ===
# =============================================================================


class TestCreateDatabaseConfigCheck:
    """测试创建 memeries 知识库时的配置验证"""

    @pytest.mark.asyncio
    async def test_create_database_raises_when_not_configured(self):
        """API Key 未配置时创建知识库应抛出 ValueError"""
        from src.knowledge.implementations.memeries import MemeriesKB

        mock_service = MagicMock()
        mock_service.is_configured = MagicMock(return_value=False)

        with patch("src.services.memeries_service.get_memeries_service", return_value=mock_service):
            kb = MemeriesKB(work_dir="/tmp/test")
            with pytest.raises(ValueError, match="not configured"):
                await kb.create_database("test_kb", "test description")

    @pytest.mark.asyncio
    async def test_create_database_succeeds_when_configured(self):
        """API Key 已配置时创建知识库应正常执行"""
        from src.knowledge.implementations.memeries import MemeriesKB

        mock_service = MagicMock()
        mock_service.is_configured = MagicMock(return_value=True)

        with (
            patch("src.services.memeries_service.get_memeries_service", return_value=mock_service),
            patch.object(MemeriesKB, "_save_metadata", return_value=None),
        ):
            kb = MemeriesKB(work_dir="/tmp/test")
            kb.databases_meta = {}
            result = await kb.create_database("test_kb", "test description")
            assert result is not None
            assert result["name"] == "test_kb"
            assert result["kb_type"] == "memeries"
