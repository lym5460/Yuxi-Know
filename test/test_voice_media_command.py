"""Tests for voice WebSocket media command sending.

**Validates: Requirements 8.2**

Tests that memeries knowledge base search results are correctly detected
and converted to media_command WebSocket messages.
"""

import os
import sys

sys.path.insert(0, os.getcwd())

import pytest
from hypothesis import given, settings, strategies as st

from src.services.media_command import MediaPlayCommand


# =============================================================================
# === Strategies ===
# =============================================================================

# 模拟 memeries aquery 返回的媒体片段
valid_memeries_results = st.fixed_dictionaries({
    "media_id": st.text(min_size=1, max_size=30, alphabet=st.characters(whitelist_categories=("L", "N"))),
    "media_name": st.text(min_size=0, max_size=50),
    "media_type": st.sampled_from(["video", "audio"]),
    "start_time": st.floats(min_value=0, max_value=86400, allow_nan=False, allow_infinity=False),
    "end_time": st.floats(min_value=0, max_value=86400, allow_nan=False, allow_infinity=False),
    "score": st.floats(min_value=0, max_value=1, allow_nan=False, allow_infinity=False),
    "media_url": st.builds(lambda p: f"http://minio:9000/{p}", p=st.text(min_size=1, max_size=30, alphabet="abcdefghijklmnopqrstuvwxyz0123456789/._-")),
})


def is_media_result(result: dict) -> bool:
    """检测 memeries 结果是否包含必要的媒体字段（与 voice_router 中的逻辑一致）"""
    if not isinstance(result, dict):
        return False
    media_id = result.get("media_id")
    media_type = result.get("media_type")
    start_time = result.get("start_time")
    return bool(media_id and media_type and start_time is not None)


def build_media_command(result: dict) -> MediaPlayCommand:
    """从 memeries 结果构建 MediaPlayCommand（与 voice_router 中的逻辑一致）"""
    return MediaPlayCommand(
        action="play",
        media_id=result["media_id"],
        media_type=result["media_type"] if result["media_type"] in ("video", "audio") else "video",
        media_url=result.get("media_url", ""),
        start_time=float(result["start_time"]),
        end_time=float(result["end_time"]) if result.get("end_time") else None,
        description=result.get("media_name"),
    )


# =============================================================================
# === Property Tests ===
# =============================================================================


class TestMemeriesMediaDetection:
    """Property tests for detecting media results from memeries KB."""

    @given(result=valid_memeries_results)
    @settings(max_examples=100)
    def test_valid_memeries_result_detected_as_media(self, result: dict):
        """
        Property: Any valid memeries search result with media_id, media_type,
        and start_time should be detected as a media result.

        **Validates: Requirements 8.2**
        """
        assert is_media_result(result) is True

    @given(result=valid_memeries_results)
    @settings(max_examples=100)
    def test_valid_memeries_result_converts_to_play_command(self, result: dict):
        """
        Property: Any valid memeries result should convert to a MediaPlayCommand
        with action="play" and correct WebSocket message format.

        **Validates: Requirements 8.2**
        """
        cmd = build_media_command(result)
        assert cmd.action == "play"
        assert cmd.media_id == result["media_id"]
        assert cmd.start_time == float(result["start_time"])

        msg = cmd.to_ws_message()
        assert msg["type"] == "media_command"
        assert msg["data"]["action"] == "play"

    @given(result=valid_memeries_results)
    @settings(max_examples=50)
    def test_media_command_preserves_media_url(self, result: dict):
        """
        Property: The media_url from memeries result should be preserved
        in the MediaPlayCommand.

        **Validates: Requirements 8.2**
        """
        cmd = build_media_command(result)
        assert cmd.media_url == result["media_url"]


# =============================================================================
# === Unit Tests ===
# =============================================================================


class TestVoiceMediaCommandUnit:
    """Unit tests for voice WebSocket media command integration."""

    def test_detect_media_result_with_all_fields(self):
        """完整的 memeries 结果应被检测为媒体结果"""
        result = {
            "media_id": "VI123456",
            "media_name": "手术视频.mp4",
            "media_type": "video",
            "start_time": 13.0,
            "end_time": 18.0,
            "score": 0.85,
            "media_url": "http://minio:9000/kb-files/test.mp4",
        }
        assert is_media_result(result) is True

    def test_detect_media_result_missing_media_id(self):
        """缺少 media_id 的结果不应被检测为媒体结果"""
        result = {
            "media_type": "video",
            "start_time": 13.0,
            "media_url": "http://minio:9000/test.mp4",
        }
        assert is_media_result(result) is False

    def test_detect_media_result_missing_media_type(self):
        """缺少 media_type 的结果不应被检测为媒体结果"""
        result = {
            "media_id": "VI123456",
            "start_time": 13.0,
            "media_url": "http://minio:9000/test.mp4",
        }
        assert is_media_result(result) is False

    def test_detect_media_result_missing_start_time(self):
        """缺少 start_time 的结果不应被检测为媒体结果"""
        result = {
            "media_id": "VI123456",
            "media_type": "video",
            "media_url": "http://minio:9000/test.mp4",
        }
        assert is_media_result(result) is False

    def test_detect_non_dict_result(self):
        """非 dict 类型的结果不应被检测为媒体结果"""
        assert is_media_result("not a dict") is False
        assert is_media_result(42) is False
        assert is_media_result(None) is False

    def test_detect_media_result_with_zero_start_time(self):
        """start_time=0 的结果应被检测为媒体结果（0 是有效值）"""
        result = {
            "media_id": "VI123456",
            "media_type": "video",
            "start_time": 0,
            "media_url": "http://minio:9000/test.mp4",
        }
        assert is_media_result(result) is True

    def test_build_media_command_basic(self):
        """从 memeries 结果构建基本的播放指令"""
        result = {
            "media_id": "VI123456",
            "media_name": "手术视频.mp4",
            "media_type": "video",
            "start_time": 13.0,
            "end_time": 18.0,
            "score": 0.85,
            "media_url": "http://minio:9000/kb-files/test.mp4",
        }
        cmd = build_media_command(result)
        assert cmd.action == "play"
        assert cmd.media_id == "VI123456"
        assert cmd.media_type == "video"
        assert cmd.media_url == "http://minio:9000/kb-files/test.mp4"
        assert cmd.start_time == 13.0
        assert cmd.end_time == 18.0
        assert cmd.description == "手术视频.mp4"

    def test_build_media_command_ws_message_format(self):
        """构建的播放指令应生成正确的 WebSocket 消息格式"""
        result = {
            "media_id": "VI123456",
            "media_name": "手术切口缝合片段",
            "media_type": "video",
            "start_time": 13,
            "end_time": 18,
            "score": 0.9,
            "media_url": "http://minio:9000/kb-files/test.mp4",
        }
        cmd = build_media_command(result)
        msg = cmd.to_ws_message()

        assert msg == {
            "type": "media_command",
            "data": {
                "action": "play",
                "media_id": "VI123456",
                "media_type": "video",
                "media_url": "http://minio:9000/kb-files/test.mp4",
                "start_time": 13.0,
                "end_time": 18.0,
                "description": "手术切口缝合片段",
            },
        }

    def test_build_media_command_without_end_time(self):
        """没有 end_time 时，WebSocket 消息中不应包含 end_time"""
        result = {
            "media_id": "VI123456",
            "media_name": "片段",
            "media_type": "audio",
            "start_time": 5.0,
            "end_time": 0,  # falsy value
            "score": 0.7,
            "media_url": "http://minio:9000/audio.mp3",
        }
        cmd = build_media_command(result)
        msg = cmd.to_ws_message()
        assert "end_time" not in msg["data"]

    def test_build_media_command_unknown_media_type_defaults_to_video(self):
        """未知的 media_type 应默认为 video"""
        result = {
            "media_id": "VI123456",
            "media_name": "文件",
            "media_type": "unknown",
            "start_time": 0,
            "media_url": "http://minio:9000/file",
        }
        cmd = build_media_command(result)
        assert cmd.media_type == "video"

    def test_milvus_result_not_detected_as_media(self):
        """普通 Milvus 知识库结果（无媒体字段）不应被检测为媒体结果"""
        result = {
            "content": "这是一段文档内容",
            "metadata": {"source": "doc.pdf"},
            "score": 0.9,
        }
        assert is_media_result(result) is False
