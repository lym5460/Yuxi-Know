"""Memeries Service - Memeries API 封装服务

提供音视频内容的上传、搜索、管理等功能。

职责:
- 封装 Memeries API 调用
- 处理音视频上传和索引
- 执行语义搜索
- 管理视频列表和详情
"""

import os
from typing import Any

import httpx

from src.utils import logger

# =============================================================================
# === 常量定义 ===
# =============================================================================

# 默认 API 端点
DEFAULT_MEMERIES_ENDPOINT = "https://api.memories.ai"

# 支持的媒体格式
SUPPORTED_VIDEO_FORMATS = frozenset({"mp4", "avi", "mov", "mkv", "webm"})
SUPPORTED_AUDIO_FORMATS = frozenset({"mp3", "wav", "m4a", "flac", "aac", "ogg"})
SUPPORTED_MEDIA_FORMATS = SUPPORTED_VIDEO_FORMATS | SUPPORTED_AUDIO_FORMATS


# =============================================================================
# === 文件格式验证 ===
# =============================================================================


def _get_file_extension(filename: str) -> str:
    """从文件名中提取扩展名（小写）"""
    if "." not in filename:
        return ""
    return filename.rsplit(".", 1)[-1].lower()


def _validate_file_format(filename: str) -> bool:
    """验证文件格式是否为支持的音视频格式"""
    ext = _get_file_extension(filename)
    return ext in SUPPORTED_MEDIA_FORMATS


def _get_media_type(filename: str) -> str:
    """根据文件扩展名判断媒体类型

    Returns:
        "video" | "audio" | "unknown"
    """
    ext = _get_file_extension(filename)
    if ext in SUPPORTED_VIDEO_FORMATS:
        return "video"
    if ext in SUPPORTED_AUDIO_FORMATS:
        return "audio"
    return "unknown"

# API 超时时间（秒）
API_TIMEOUT = 60

# 上传超时时间（秒）- 大文件需要更长时间
UPLOAD_TIMEOUT = 300

# 删除视频每次最大数量
MAX_DELETE_BATCH_SIZE = 100


# =============================================================================
# === Memeries Service ===
# =============================================================================


class MemeriesService:
    """Memeries API 封装服务"""

    def __init__(self):
        self.endpoint = os.getenv("MEMERIES_API_ENDPOINT", DEFAULT_MEMERIES_ENDPOINT)
        self.api_key = os.getenv("MEMERIES_API_KEY")

        if not self.api_key:
            logger.warning("MEMERIES_API_KEY not configured, Memeries features will be unavailable")
        elif not self._validate_api_key_format(self.api_key):
            logger.warning("MEMERIES_API_KEY format is invalid, Memeries features may not work correctly")
        else:
            logger.info(f"MemeriesService initialized with endpoint: {self.endpoint}")

    def _get_headers(self) -> dict[str, str]:
        """获取 API 请求头"""
        return {
            "Authorization": f"Bearer {self.api_key}",
        }

    def is_configured(self) -> bool:
        """检查服务是否已正确配置（API Key 存在且格式有效）"""
        return bool(self.api_key) and self._validate_api_key_format(self.api_key)

    @staticmethod
    def _validate_api_key_format(api_key: str) -> bool:
        """验证 API Key 格式是否有效

        有效的 API Key 应为非空的、不含空白字符的字符串，且长度至少 8 个字符。
        """
        if not api_key or not api_key.strip():
            return False
        if api_key != api_key.strip():
            return False
        return len(api_key) >= 8

    async def upload(
        self,
        file_path: str,
        file_data: bytes,
        unique_id: str,
        retain_original_video: bool = True,
        callback: str | None = None,
    ) -> dict[str, Any]:
        """上传媒体文件到 Memeries

        POST /serve/api/v1/upload

        Args:
            file_path: 文件路径（用于获取文件名）
            file_data: 文件二进制数据
            unique_id: 知识库 db_id，用于区分不同工作空间
            retain_original_video: 是否保留原始文件
            callback: 回调 URL，Memeries 处理完成后会 POST 通知

        Returns:
            {"code": "0000", "data": {"videoNo": "VI...", "videoName": "...", "videoStatus": "UNPARSE"}}

        Raises:
            httpx.HTTPStatusError: API 请求失败
        """
        url = f"{self.endpoint}/serve/api/v1/upload"

        # 从路径中提取文件名
        filename = os.path.basename(file_path)

        async with httpx.AsyncClient(timeout=UPLOAD_TIMEOUT) as client:
            files = {"file": (filename, file_data)}
            data = {
                "unique_id": unique_id,
                "retain_original_video": str(retain_original_video).lower(),
            }
            if callback:
                data["callback"] = callback

            response = await client.post(
                url,
                headers=self._get_headers(),
                files=files,
                data=data,
            )
            response.raise_for_status()

            result = response.json()

            # 检查业务层错误（HTTP 200 但 API 返回失败）
            if result.get("failed") or result.get("success") is False:
                error_msg = result.get("msg", "Unknown API error")
                raise httpx.HTTPStatusError(
                    f"Memeries API error: {error_msg} (code={result.get('code')})",
                    request=response.request,
                    response=response,
                )

            logger.info(f"Uploaded file '{filename}' to Memeries, response: {result}")
            return result

    async def search(
        self,
        search_param: str,
        search_type: str,
        unique_id: str,
        top_k: int = 5,
        filtering_level: str = "medium",
    ) -> list[dict[str, Any]]:
        """语义搜索媒体内容

        POST /serve/api/v1/search

        Args:
            search_param: 搜索关键词
            search_type: 搜索类型 (BY_VIDEO, BY_AUDIO)
            unique_id: 知识库 db_id
            top_k: 返回结果数量
            filtering_level: 过滤级别 (low/medium/high)

        Returns:
            [{"videoNo": "...", "startTime": "13", "endTime": "18", "score": 0.52}]
        """
        url = f"{self.endpoint}/serve/api/v1/search"

        async with httpx.AsyncClient(timeout=API_TIMEOUT) as client:
            payload = {
                "search_param": search_param,
                "search_type": search_type,
                "unique_id": unique_id,
                "top_k": top_k,
                "filtering_level": filtering_level,
            }

            response = await client.post(
                url,
                headers=self._get_headers(),
                json=payload,
            )
            response.raise_for_status()

            result = response.json()
            # API 可能返回 {"results": [...]} 或直接返回列表
            if isinstance(result, dict):
                results = result.get("results", result.get("data", []))
            else:
                results = result if isinstance(result, list) else []

            logger.debug(f"Search '{search_param}' ({search_type}) returned {len(results)} results")
            return results

    async def list_videos(
        self,
        unique_id: str,
        page: int = 1,
        size: int = 100,
        status: str | None = None,
    ) -> dict[str, Any]:
        """获取视频列表

        POST /serve/api/v1/list_videos

        Args:
            unique_id: 知识库 db_id
            page: 页码
            size: 每页数量
            status: 过滤状态 (UNPARSE, PARSE, FAIL)

        Returns:
            {"total": 10, "videos": [...]}
        """
        url = f"{self.endpoint}/serve/api/v1/list_videos"

        async with httpx.AsyncClient(timeout=API_TIMEOUT) as client:
            payload: dict[str, Any] = {
                "unique_id": unique_id,
                "page": page,
                "size": size,
            }
            if status:
                payload["status"] = status

            response = await client.post(
                url,
                headers=self._get_headers(),
                json=payload,
            )
            response.raise_for_status()

            return response.json()

    async def get_video_details(
        self,
        video_no: str,
        unique_id: str,
    ) -> dict[str, Any]:
        """获取视频详情

        GET /serve/api/v1/get_private_video_details

        Args:
            video_no: 视频 ID
            unique_id: 知识库 db_id

        Returns:
            {"duration": "8", "video_url": "...", "status": "PARSE", ...}
        """
        url = f"{self.endpoint}/serve/api/v1/get_private_video_details"

        async with httpx.AsyncClient(timeout=API_TIMEOUT) as client:
            params = {
                "video_no": video_no,
                "unique_id": unique_id,
            }

            response = await client.get(
                url,
                headers=self._get_headers(),
                params=params,
            )
            response.raise_for_status()

            return response.json()

    async def delete_videos(
        self,
        video_nos: list[str],
        unique_id: str,
    ) -> bool:
        """删除视频

        POST /serve/api/v1/delete_videos

        每次最多删除 100 个视频，超过时自动分批处理。

        Args:
            video_nos: 视频 ID 列表
            unique_id: 知识库 db_id

        Returns:
            是否全部删除成功
        """
        if not video_nos:
            return True

        url = f"{self.endpoint}/serve/api/v1/delete_videos"
        all_success = True

        async with httpx.AsyncClient(timeout=API_TIMEOUT) as client:
            # 分批处理
            for i in range(0, len(video_nos), MAX_DELETE_BATCH_SIZE):
                batch = video_nos[i : i + MAX_DELETE_BATCH_SIZE]
                payload = {
                    "video_nos": batch,
                    "unique_id": unique_id,
                }

                try:
                    response = await client.post(
                        url,
                        headers=self._get_headers(),
                        json=payload,
                    )
                    response.raise_for_status()
                    logger.info(f"Deleted {len(batch)} videos from Memeries")
                except httpx.HTTPStatusError as e:
                    logger.error(f"Failed to delete videos batch: {e}")
                    all_success = False

        return all_success


# =============================================================================
# === 全局实例 ===
# =============================================================================

# 全局服务实例（延迟初始化）
_memeries_service: MemeriesService | None = None


def get_memeries_service() -> MemeriesService:
    """获取 Memeries 服务实例（单例模式）"""
    global _memeries_service
    if _memeries_service is None:
        _memeries_service = MemeriesService()
    return _memeries_service
