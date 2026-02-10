"""Property-based tests for Memeries API request parameter completeness.

**Validates: Requirements 2.2, 3.3**

Tests that upload and search API calls always include all required parameters,
regardless of the input values provided.
"""

import os
import sys

# Add project root to path
sys.path.insert(0, os.getcwd())

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from hypothesis import given, settings, strategies as st

from src.services.memeries_service import MemeriesService


# =============================================================================
# === Strategies ===
# =============================================================================

# 生成有效的文件路径
file_paths = st.builds(
    lambda name, ext: f"/data/{name}.{ext}",
    name=st.text(
        min_size=1,
        max_size=30,
        alphabet=st.characters(whitelist_categories=("L", "N"), whitelist_characters="_-"),
    ),
    ext=st.sampled_from(["mp4", "avi", "mov", "mkv", "webm", "mp3", "wav", "m4a"]),
)

# 生成文件二进制数据
file_data = st.binary(min_size=1, max_size=1024)

# 生成 unique_id
unique_ids = st.text(
    min_size=1,
    max_size=50,
    alphabet=st.characters(whitelist_categories=("L", "N"), whitelist_characters="_-"),
)

# 生成 retain_original_video 布尔值
retain_flags = st.booleans()

# 生成搜索关键词
search_params = st.text(min_size=1, max_size=100)

# 生成搜索类型
search_types = st.sampled_from(["BY_VIDEO", "BY_AUDIO"])

# 生成 top_k 值
top_k_values = st.integers(min_value=1, max_value=100)


# =============================================================================
# === Helpers ===
# =============================================================================


def _create_service() -> MemeriesService:
    """创建一个已配置的 MemeriesService 实例"""
    with patch.dict(os.environ, {"MEMERIES_API_KEY": "test-key", "MEMERIES_API_ENDPOINT": "https://test.api"}):
        return MemeriesService()


def _make_mock_response(json_data: dict | list | None = None, status_code: int = 200) -> MagicMock:
    """创建 mock HTTP 响应"""
    response = MagicMock(spec=httpx.Response)
    response.status_code = status_code
    response.json.return_value = json_data or {}
    response.raise_for_status = MagicMock()
    return response


# =============================================================================
# === Property Tests: Upload API 参数完整性 ===
# =============================================================================


class TestUploadApiParams:
    """Property tests for upload API request parameter completeness.

    **Validates: Requirements 2.2**
    """

    @given(
        path=file_paths,
        data=file_data,
        uid=unique_ids,
        retain=retain_flags,
    )
    @settings(max_examples=100)
    @pytest.mark.asyncio
    async def test_upload_contains_required_params(
        self,
        path: str,
        data: bytes,
        uid: str,
        retain: bool,
    ):
        """
        Property: For any valid upload inputs, the HTTP request always contains
        file, unique_id, and retain_original_video parameters.

        **Validates: Requirements 2.2**
        """
        service = _create_service()
        mock_response = _make_mock_response({"videoNo": "VI123", "videoName": "test", "videoStatus": "UNPARSE"})

        captured_kwargs: dict = {}

        async def capture_post(url, **kwargs):
            captured_kwargs.update(kwargs)
            return mock_response

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.post = capture_post
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("src.services.memeries_service.httpx.AsyncClient", return_value=mock_client):
            await service.upload(
                file_path=path,
                file_data=data,
                unique_id=uid,
                retain_original_video=retain,
            )

        # 验证 file 参数存在
        assert "files" in captured_kwargs, "Upload request must contain 'files' parameter"
        files_param = captured_kwargs["files"]
        assert "file" in files_param, "files dict must contain 'file' key"

        # 验证 data 参数包含 unique_id 和 retain_original_video
        assert "data" in captured_kwargs, "Upload request must contain 'data' parameter"
        data_param = captured_kwargs["data"]
        assert "unique_id" in data_param, "data must contain 'unique_id'"
        assert "retain_original_video" in data_param, "data must contain 'retain_original_video'"

        # 验证参数值正确
        assert data_param["unique_id"] == uid
        assert data_param["retain_original_video"] == str(retain).lower()

    @given(
        path=file_paths,
        data=file_data,
        uid=unique_ids,
    )
    @settings(max_examples=100)
    @pytest.mark.asyncio
    async def test_upload_file_data_matches_input(
        self,
        path: str,
        data: bytes,
        uid: str,
    ):
        """
        Property: For any upload, the file data in the request matches the input data.

        **Validates: Requirements 2.2**
        """
        service = _create_service()
        mock_response = _make_mock_response({"videoNo": "VI123", "videoName": "test", "videoStatus": "UNPARSE"})

        captured_kwargs: dict = {}

        async def capture_post(url, **kwargs):
            captured_kwargs.update(kwargs)
            return mock_response

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.post = capture_post
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("src.services.memeries_service.httpx.AsyncClient", return_value=mock_client):
            await service.upload(file_path=path, file_data=data, unique_id=uid)

        # 验证文件数据
        files_param = captured_kwargs["files"]
        _filename, file_bytes = files_param["file"]
        assert file_bytes == data, "File data in request must match input"


# =============================================================================
# === Property Tests: Search API 参数完整性 ===
# =============================================================================


class TestSearchApiParams:
    """Property tests for search API request parameter completeness.

    **Validates: Requirements 3.3**
    """

    @given(
        param=search_params,
        stype=search_types,
        uid=unique_ids,
        k=top_k_values,
    )
    @settings(max_examples=100)
    @pytest.mark.asyncio
    async def test_search_contains_required_params(
        self,
        param: str,
        stype: str,
        uid: str,
        k: int,
    ):
        """
        Property: For any valid search inputs, the HTTP request always contains
        search_param, search_type, unique_id, and top_k parameters.

        **Validates: Requirements 3.3**
        """
        service = _create_service()
        mock_response = _make_mock_response({"results": []})

        captured_kwargs: dict = {}

        async def capture_post(url, **kwargs):
            captured_kwargs.update(kwargs)
            return mock_response

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.post = capture_post
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("src.services.memeries_service.httpx.AsyncClient", return_value=mock_client):
            await service.search(
                search_param=param,
                search_type=stype,
                unique_id=uid,
                top_k=k,
            )

        # 验证 json payload 包含所有必需参数
        assert "json" in captured_kwargs, "Search request must use JSON payload"
        payload = captured_kwargs["json"]

        assert "search_param" in payload, "Payload must contain 'search_param'"
        assert "search_type" in payload, "Payload must contain 'search_type'"
        assert "unique_id" in payload, "Payload must contain 'unique_id'"
        assert "top_k" in payload, "Payload must contain 'top_k'"

    @given(
        param=search_params,
        stype=search_types,
        uid=unique_ids,
        k=top_k_values,
    )
    @settings(max_examples=100)
    @pytest.mark.asyncio
    async def test_search_params_match_input(
        self,
        param: str,
        stype: str,
        uid: str,
        k: int,
    ):
        """
        Property: For any search, the request parameters match the input values exactly.

        **Validates: Requirements 3.3**
        """
        service = _create_service()
        mock_response = _make_mock_response({"results": []})

        captured_kwargs: dict = {}

        async def capture_post(url, **kwargs):
            captured_kwargs.update(kwargs)
            return mock_response

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.post = capture_post
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("src.services.memeries_service.httpx.AsyncClient", return_value=mock_client):
            await service.search(
                search_param=param,
                search_type=stype,
                unique_id=uid,
                top_k=k,
            )

        payload = captured_kwargs["json"]
        assert payload["search_param"] == param
        assert payload["search_type"] == stype
        assert payload["unique_id"] == uid
        assert payload["top_k"] == k
