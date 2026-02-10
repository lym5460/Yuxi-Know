"""Memeries Knowledge Base - 基于 Memeries API 的媒体知识库实现

提供音视频文件的上传、索引和语义搜索功能。

职责:
- 继承 KnowledgeBase 基类
- 管理音视频文件的上传和索引
- 通过 Memeries API 执行语义搜索（BY_VIDEO 模式）
"""

import os

from src.knowledge.base import KnowledgeBase
from src.services.memeries_service import (
    SUPPORTED_AUDIO_FORMATS,
    SUPPORTED_VIDEO_FORMATS,
    _get_media_type,
    _validate_file_format,
)
from src.utils import logger


class MemeriesKB(KnowledgeBase):
    """基于 Memeries API 的媒体知识库实现"""

    # 支持的媒体格式（从 memeries_service 导入，保持一致性）
    SUPPORTED_VIDEO_FORMATS = SUPPORTED_VIDEO_FORMATS
    SUPPORTED_AUDIO_FORMATS = SUPPORTED_AUDIO_FORMATS

    def __init__(self, work_dir: str, **kwargs):
        """初始化 Memeries 知识库

        Args:
            work_dir: 工作目录
            **kwargs: 其他配置参数
        """
        super().__init__(work_dir)
        logger.info("MemeriesKB initialized")

    # Memeries 扩展字段名，这些字段存储在 processing_params 中以实现持久化
    _EXTRA_FIELDS = ("memeries_video_no", "media_type", "duration")

    async def _save_metadata(self) -> None:
        """保存前将 Memeries 扩展字段打包到 processing_params 中"""
        for file_meta in self.files_meta.values():
            params = file_meta.get("processing_params") or {}
            for field in self._EXTRA_FIELDS:
                if field in file_meta and file_meta[field] is not None:
                    params[field] = file_meta[field]
            file_meta["processing_params"] = params
        await super()._save_metadata()

    async def _load_metadata(self) -> None:
        """加载后从 processing_params 中解包 Memeries 扩展字段"""
        await super()._load_metadata()
        for file_meta in self.files_meta.values():
            params = file_meta.get("processing_params") or {}
            for field in self._EXTRA_FIELDS:
                if field in params:
                    file_meta[field] = params[field]


    @property
    def kb_type(self) -> str:
        """知识库类型标识"""
        return "memeries"

    def _validate_file_format(self, filename: str) -> bool:
        """验证文件格式是否为支持的音视频格式

        Args:
            filename: 文件名

        Returns:
            True 如果格式支持，否则 False
        """
        return _validate_file_format(filename)

    def _get_media_type(self, filename: str) -> str:
        """根据文件扩展名判断媒体类型

        Args:
            filename: 文件名

        Returns:
            "video" | "audio" | "unknown"
        """
        return _get_media_type(filename)

    async def _create_kb_instance(self, db_id: str, config: dict):
        """创建底层知识库实例（Memeries 不需要本地实例）"""
        # Memeries 是远程 API 服务，不需要创建本地实例
        return None

    async def _initialize_kb_instance(self, instance) -> None:
        """初始化底层知识库实例（Memeries 不需要初始化）"""
        # Memeries 是远程 API 服务，不需要初始化
        pass
    async def create_database(
        self,
        database_name: str,
        description: str,
        embed_info: dict | None = None,
        llm_info: dict | None = None,
        **kwargs,
    ) -> dict:
        """创建 memeries 类型知识库（创建前检查 API 配置）"""
        from src.services.memeries_service import get_memeries_service

        memeries_service = get_memeries_service()
        if not memeries_service.is_configured():
            raise ValueError(
                "Memeries API is not configured or API Key format is invalid. "
                "Please set a valid MEMERIES_API_KEY environment variable."
            )

        return await super().create_database(database_name, description, embed_info, llm_info, **kwargs)

    async def index_file(self, db_id: str, file_id: str, operator_id: str | None = None) -> dict:
        """上传文件到 Memeries 进行索引

        使用 db_id 作为 Memeries API 的 unique_id。
        状态映射: UNPARSE→indexing, PARSE→indexed, FAIL→error_indexing

        Args:
            db_id: 知识库 ID
            file_id: 文件 ID
            operator_id: 操作者 ID

        Returns:
            更新后的文件元数据
        """
        from src.knowledge.base import FileStatus
        from src.knowledge.utils.kb_utils import parse_minio_url
        from src.services.memeries_service import get_memeries_service
        from src.storage.minio import get_minio_client
        from src.utils.datetime_utils import utc_isoformat

        # 验证文件存在
        if file_id not in self.files_meta:
            raise ValueError(f"File {file_id} not found")

        file_meta = self.files_meta[file_id]
        current_status = file_meta.get("status")

        # 验证当前状态 - 只允许从这些状态开始索引
        allowed_statuses = {
            FileStatus.UPLOADED,
            FileStatus.INDEXING,  # 允许重新索引（如远程处理中断）
            FileStatus.ERROR_INDEXING,
            "failed",  # Legacy status
        }

        if current_status not in allowed_statuses:
            raise ValueError(
                f"Cannot index file with status '{current_status}'. "
                f"File must be in one of these states: {', '.join(allowed_statuses)}"
            )

        file_path = file_meta.get("path")
        if not file_path:
            raise ValueError(f"File {file_id} has no valid path in metadata")

        # 验证文件格式
        filename = file_meta.get("filename", "")
        if not self._validate_file_format(filename):
            raise ValueError(f"Unsupported file format: {filename}")

        # 清除之前的错误
        if "error" in file_meta:
            self.files_meta[file_id].pop("error", None)

        # 更新状态为 INDEXING
        self.files_meta[file_id]["status"] = FileStatus.INDEXING
        self.files_meta[file_id]["updated_at"] = utc_isoformat()
        if operator_id:
            self.files_meta[file_id]["updated_by"] = operator_id
        await self._save_metadata()

        # 添加到处理队列
        self._add_to_processing_queue(file_id)

        try:
            # 获取 Memeries 服务
            memeries_service = get_memeries_service()
            if not memeries_service.is_configured():
                raise ValueError("Memeries API is not configured. Please set MEMERIES_API_KEY.")

            # 从 MinIO 下载文件
            minio_client = get_minio_client()
            bucket_name, object_name = parse_minio_url(file_path)
            file_data = await minio_client.adownload_file(bucket_name, object_name)

            # 上传到 Memeries，使用 db_id 作为 unique_id
            callback_url = os.getenv("MEMERIES_CALLBACK_URL")
            result = await memeries_service.upload(
                file_path=filename,
                file_data=file_data,
                unique_id=db_id,
                retain_original_video=True,
                callback=callback_url,
            )

            # 提取 videoNo 和 videoStatus（数据可能嵌套在 data 字段中）
            # 兼容驼峰和蛇形命名
            data = result.get("data", result)
            video_no = data.get("videoNo") or data.get("video_no")
            video_status = data.get("videoStatus") or data.get("video_status") or "UNPARSE"

            # 状态映射: UNPARSE→indexing, PARSE→indexed, FAIL→error_indexing
            status_mapping = {
                "UNPARSE": FileStatus.INDEXING,
                "PARSE": FileStatus.INDEXED,
                "FAIL": FileStatus.ERROR_INDEXING,
            }
            new_status = status_mapping.get(video_status, FileStatus.INDEXING)

            # 更新文件元数据
            self.files_meta[file_id]["status"] = new_status
            self.files_meta[file_id]["memeries_video_no"] = video_no
            self.files_meta[file_id]["media_type"] = self._get_media_type(filename)
            self.files_meta[file_id]["updated_at"] = utc_isoformat()
            if operator_id:
                self.files_meta[file_id]["updated_by"] = operator_id

            # 如果处理失败，记录错误信息
            if new_status == FileStatus.ERROR_INDEXING:
                error_cause = result.get("cause", "Unknown error from Memeries")
                self.files_meta[file_id]["error"] = error_cause

            await self._save_metadata()

            logger.info(f"Indexed file {file_id} to Memeries, videoNo: {video_no}, status: {new_status}")
            return self.files_meta[file_id]

        except Exception as e:
            error_msg = str(e) or repr(e)
            logger.error(f"Failed to index file {file_id} to Memeries: {error_msg}", exc_info=True)

            self.files_meta[file_id]["status"] = FileStatus.ERROR_INDEXING
            self.files_meta[file_id]["error"] = error_msg
            self.files_meta[file_id]["updated_at"] = utc_isoformat()
            if operator_id:
                self.files_meta[file_id]["updated_by"] = operator_id
            await self._save_metadata()

            raise

        finally:
            # 从处理队列移除
            self._remove_from_processing_queue(file_id)

    async def aquery(self, query_text: str, db_id: str, agent_call: bool = False, **kwargs) -> list[dict]:
        """语义搜索媒体内容

        使用 BY_VIDEO 模式搜索，按 score 降序排列。

        Args:
            query_text: 搜索关键词
            db_id: 知识库 ID（用作 Memeries unique_id）
            agent_call: 是否由智能体调用
            **kwargs: 额外参数，支持 top_k

        Returns:
            标准化的媒体片段列表，每个片段包含:
            media_id, media_name, media_type, start_time, end_time, score, media_url
        """
        from src.services.memeries_service import get_memeries_service

        memeries_service = get_memeries_service()
        if not memeries_service.is_configured():
            logger.warning("Memeries API is not configured, returning empty results")
            return []

        query_params = self._get_query_params(db_id)
        merged_kwargs = {**query_params, **kwargs}
        top_k = int(merged_kwargs.get("top_k", 5))

        # 构建 videoNo → 文件信息 的映射
        video_no_map: dict[str, dict] = {}
        for file_id, meta in self.files_meta.items():
            video_no = meta.get("memeries_video_no")
            if video_no:
                video_no_map[video_no] = {
                    "file_id": file_id,
                    "filename": meta.get("filename", ""),
                    "media_type": meta.get("media_type", "unknown"),
                    "path": meta.get("path", ""),
                }

        # 仅使用 BY_VIDEO 搜索（BY_AUDIO 的 score 普遍接近 1.0，无法有效区分相关性）
        try:
            video_results = await memeries_service.search(
                search_param=query_text, search_type="BY_VIDEO",
                unique_id=db_id, top_k=top_k, filtering_level="medium",
            )
        except Exception as e:
            logger.error(f"Memeries search failed: {e}")
            return []

        # 日志：原始搜索结果
        logger.info(
            f"[Memeries aquery] query='{query_text}', db_id={db_id}, "
            f"video_results={len(video_results)}, video_no_map keys={list(video_no_map.keys())}"
        )
        for i, item in enumerate(video_results[:5]):
            logger.info(
                f"  [BY_VIDEO #{i}] videoNo={item.get('videoNo')}, videoName={item.get('videoName')}, "
                f"score={item.get('score')}, startTime={item.get('startTime')}, endTime={item.get('endTime')}"
            )

        if not video_results:
            logger.info(f"[Memeries aquery] BY_VIDEO 无结果")
            return []

        # 去重（同一 videoNo + startTime + endTime 视为重复，保留高分）
        seen: dict[tuple, dict] = {}
        for item in video_results:
            video_no = item.get("videoNo", "")
            start_time = float(item.get("startTime", 0))
            end_time = float(item.get("endTime", 0))
            score = float(item.get("score", 0))

            file_info = video_no_map.get(video_no, {})
            # URL 回退逻辑：优先使用 Memeries 返回的 video_url，为空则回退到 MinIO 路径
            memeries_video_url = item.get("video_url") or ""
            media_url = memeries_video_url if memeries_video_url else file_info.get("path", "")

            segment = {
                "media_id": video_no,
                "media_name": file_info.get("filename", "") or item.get("videoName", ""),
                "media_type": file_info.get("media_type", "unknown"),
                "start_time": start_time,
                "end_time": end_time,
                "score": score,
                "media_url": media_url,
                "file_id": file_info.get("file_id", ""),
                "db_id": db_id,
            }

            key = (video_no, start_time, end_time)
            if key not in seen or score > seen[key]["score"]:
                seen[key] = segment

        # 按 score 降序排列
        results = sorted(seen.values(), key=lambda x: x["score"], reverse=True)

        # 日志：最终排序后的结果
        logger.info(f"[Memeries aquery] merged & sorted: {len(results)} segments")
        for i, seg in enumerate(results[:5]):
            logger.info(
                f"  [Result #{i}] media_id={seg['media_id']}, media_name={seg['media_name']}, "
                f"score={seg['score']:.4f}, start={seg['start_time']}, end={seg['end_time']}, "
                f"file_id={seg['file_id']}, has_url={'yes' if seg['media_url'] else 'no'}"
            )
        return results

    async def update_content(self, db_id: str, file_ids: list[str], params: dict | None = None) -> list[dict]:
        """更新内容（媒体知识库不支持此操作）"""
        # 媒体文件不支持重新解析，需要重新上传
        raise NotImplementedError("Media files cannot be re-parsed. Please delete and re-upload.")

    async def delete_file(self, db_id: str, file_id: str) -> None:
        """删除文件（同时删除 MinIO 和 Memeries 中的数据）

        Args:
            db_id: 知识库 ID
            file_id: 文件 ID
        """
        from src.knowledge.utils.kb_utils import parse_minio_url
        from src.services.memeries_service import get_memeries_service
        from src.storage.minio import get_minio_client

        file_meta = self.files_meta.get(file_id)
        if not file_meta:
            logger.warning(f"File {file_id} not found in metadata, skipping delete")
            return

        # 删除 Memeries 索引（失败不阻塞后续操作）
        video_no = file_meta.get("memeries_video_no")
        if video_no:
            try:
                memeries_service = get_memeries_service()
                if memeries_service.is_configured():
                    await memeries_service.delete_videos([video_no], unique_id=db_id)
                    logger.info(f"Deleted video {video_no} from Memeries")
            except Exception as e:
                logger.error(f"Failed to delete video {video_no} from Memeries: {e}")

        # 删除 MinIO 中的原始文件
        file_path = file_meta.get("path")
        if file_path:
            try:
                minio_client = get_minio_client()
                bucket_name, object_name = parse_minio_url(file_path)
                await minio_client.adelete_file(bucket_name, object_name)
                logger.info(f"Deleted file {file_id} from MinIO")
            except Exception as e:
                logger.error(f"Failed to delete file {file_id} from MinIO: {e}")

        # 删除元数据和数据库记录
        del self.files_meta[file_id]
        from src.repositories.knowledge_file_repository import KnowledgeFileRepository

        await KnowledgeFileRepository().delete(file_id)
        await self._save_metadata()

    async def get_file_basic_info(self, db_id: str, file_id: str) -> dict:
        """获取文件基本信息（仅元数据）"""
        if file_id not in self.files_meta:
            raise Exception(f"File not found: {file_id}")
        return {"meta": self.files_meta[file_id]}

    async def async_get_database_info(self, db_id: str) -> dict | None:
        """获取数据库信息，通过 list_videos API 同步远程状态

        节流策略：如果没有正在索引的文件，最多每 30 秒同步一次远程状态。
        """
        import time

        info = super().get_database_info(db_id)
        if info is None:
            logger.debug(f"[Memeries] async_get_database_info: super() returned None for {db_id}")
            return None

        # 判断是否有正在索引的文件（需要频繁同步）
        has_pending = any(
            fmeta.get("database_id") == db_id and fmeta.get("status") in ("indexing", "uploaded")
            for fmeta in self.files_meta.values()
        )

        # 节流：无待处理文件时 30 秒同步一次，有待处理文件时 5 秒同步一次
        now = time.monotonic()
        cache_key = f"_last_sync_{db_id}"
        last_sync = getattr(self, cache_key, 0.0)
        throttle_interval = 5 if has_pending else 30
        should_sync = now - last_sync > throttle_interval

        if should_sync:
            setattr(self, cache_key, now)

            # 收集有 videoNo 的文件，用于与远程数据同步
            files_with_video_no = {
                fmeta.get("memeries_video_no"): fid
                for fid, fmeta in self.files_meta.items()
                if fmeta.get("database_id") == db_id and fmeta.get("memeries_video_no")
            }

            logger.debug(
                f"[Memeries] async_get_database_info for {db_id}: "
                f"{len(files_with_video_no)} files with video_no, pending={has_pending}"
            )

            if files_with_video_no:
                await self._sync_status_from_list_videos(db_id, files_with_video_no)

            # 对于没有 video_no 的文件，尝试通过 list_videos 按文件名恢复
            orphan_files = {
                fid: fmeta
                for fid, fmeta in self.files_meta.items()
                if fmeta.get("database_id") == db_id and not fmeta.get("memeries_video_no")
            }
            if orphan_files:
                await self._recover_orphan_files(db_id, orphan_files)

        # 刷新文件状态和 Memeries 扩展字段到返回值
        if info.get("files"):
            for file_id in info["files"]:
                if file_id in self.files_meta:
                    fmeta = self.files_meta[file_id]
                    info["files"][file_id]["status"] = fmeta.get("status", "done")
                    for field in ("memeries_video_no", "media_type", "duration", "size"):
                        if field in fmeta:
                            info["files"][file_id][field] = fmeta[field]

        return info

    async def _sync_status_from_list_videos(self, db_id: str, video_no_to_file_id: dict[str, str]) -> None:
        """通过 list_videos API 批量同步所有文件的远程状态"""
        from src.knowledge.base import FileStatus
        from src.services.memeries_service import get_memeries_service
        from src.utils.datetime_utils import utc_isoformat

        status_mapping = {
            "UNPARSE": FileStatus.INDEXING,
            "PARSE": FileStatus.INDEXED,
            "FAIL": FileStatus.ERROR_INDEXING,
        }

        memeries_service = get_memeries_service()
        if not memeries_service.is_configured():
            logger.warning(f"[Memeries sync] service not configured, skipping sync for {db_id}")
            return

        try:
            logger.debug(f"[Memeries sync] calling list_videos for {db_id}, tracking {len(video_no_to_file_id)} files")
            result = await memeries_service.list_videos(unique_id=db_id, size=200)
            data = result.get("data", result)
            videos = data.get("videos", [])
            logger.debug(f"[Memeries sync] got {len(videos)} videos from Memeries for {db_id}")
        except Exception as e:
            logger.warning(f"[Memeries sync] Failed to list videos from Memeries for {db_id}: {e}")
            return

        # 构建 videoNo → 远程视频信息 的映射
        remote_video_map: dict[str, dict] = {}
        for video in videos:
            video_no = video.get("video_no")
            if video_no:
                remote_video_map[video_no] = video

        changed = False
        for video_no, file_id in video_no_to_file_id.items():
            remote_video = remote_video_map.get(video_no)
            if not remote_video:
                continue

            remote_status = remote_video.get("status")
            new_status = status_mapping.get(remote_status) if remote_status else None

            # 同步状态
            if new_status:
                current_status = self.files_meta[file_id].get("status")
                if current_status != new_status:
                    self.files_meta[file_id]["status"] = new_status
                    self.files_meta[file_id]["updated_at"] = utc_isoformat()
                    if new_status == FileStatus.ERROR_INDEXING:
                        self.files_meta[file_id]["error"] = "Memeries processing failed"
                    elif "error" in self.files_meta[file_id]:
                        self.files_meta[file_id].pop("error", None)
                    changed = True
                    logger.info(f"Synced file {file_id} status from list_videos: {remote_status} -> {new_status}")

            # 同步 duration 和 size（Memeries 返回字符串，需转为整数）
            duration = remote_video.get("duration")
            if duration is not None:
                self.files_meta[file_id]["duration"] = int(duration)
            size = remote_video.get("size")
            if size is not None:
                self.files_meta[file_id]["size"] = int(size)

        if changed:
            await self._save_metadata()

    async def _recover_orphan_files(self, db_id: str, orphan_files: dict[str, dict]) -> None:
        """通过 list_videos 按文件名恢复缺失 video_no 的文件"""
        from src.knowledge.base import FileStatus
        from src.services.memeries_service import get_memeries_service
        from src.utils.datetime_utils import utc_isoformat

        memeries_service = get_memeries_service()
        if not memeries_service.is_configured():
            return

        try:
            result = await memeries_service.list_videos(unique_id=db_id, size=200)
            data = result.get("data", result)
            videos = data.get("videos", [])
            logger.debug(f"[Memeries] recover: list_videos returned {len(videos)} videos for {db_id}")
        except Exception as e:
            logger.debug(f"[Memeries] recover orphan files failed for {db_id}: {e}")
            return

        # 按文件名建立远程视频映射
        remote_by_name: dict[str, dict] = {}
        for video in videos:
            name = video.get("video_name")
            if name:
                remote_by_name[name] = video

        status_mapping = {
            "UNPARSE": FileStatus.INDEXING,
            "PARSE": FileStatus.INDEXED,
            "FAIL": FileStatus.ERROR_INDEXING,
        }

        changed = False
        for file_id, fmeta in orphan_files.items():
            filename = fmeta.get("filename") or fmeta.get("original_filename")
            if not filename:
                continue
            # Memeries 返回的 video_name 不含扩展名，需要去掉扩展名匹配
            name_without_ext = os.path.splitext(filename)[0]
            remote_video = remote_by_name.get(filename) or remote_by_name.get(name_without_ext)
            if not remote_video:
                continue

            video_no = remote_video.get("video_no")
            if not video_no:
                continue

            self.files_meta[file_id]["memeries_video_no"] = video_no
            self.files_meta[file_id]["media_type"] = self._get_media_type(filename)

            remote_status = remote_video.get("status")
            new_status = status_mapping.get(remote_status) if remote_status else None
            if new_status:
                self.files_meta[file_id]["status"] = new_status
                self.files_meta[file_id]["updated_at"] = utc_isoformat()

            duration = remote_video.get("duration")
            if duration is not None:
                self.files_meta[file_id]["duration"] = int(duration)
            size = remote_video.get("size")
            if size is not None:
                self.files_meta[file_id]["size"] = int(size)

            changed = True
            logger.info(f"[Memeries] Recovered orphan file {file_id}: video_no={video_no}, status={new_status}")

        if changed:
            await self._save_metadata()


    async def get_file_content(self, db_id: str, file_id: str) -> dict:
        """获取文件内容信息（媒体文件没有文本 chunks）"""
        if file_id not in self.files_meta:
            raise Exception(f"File not found: {file_id}")
        return {"lines": []}

    async def get_file_info(self, db_id: str, file_id: str) -> dict:
        """获取文件完整信息（基本信息+内容信息）"""
        if file_id not in self.files_meta:
            raise Exception(f"File not found: {file_id}")
        basic_info = await self.get_file_basic_info(db_id, file_id)
        content_info = await self.get_file_content(db_id, file_id)
        return {**basic_info, **content_info}

    def get_query_params_config(self, db_id: str, **kwargs) -> dict:
        """获取查询参数配置"""
        return {
            "type": "memeries",
            "options": [
                {
                    "key": "top_k",
                    "label": "返回数量",
                    "type": "number",
                    "default": 5,
                    "min": 1,
                    "max": 20,
                    "description": "返回的最大结果数量",
                }
            ],
        }
