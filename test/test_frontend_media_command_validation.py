"""Tests for frontend media_command validation logic.

**Validates: Requirements 8.5**

Tests the frontend WebSocket media_command validation that:
- Valid commands with all required fields are accepted
- Invalid commands (missing fields, invalid action) are rejected
- Mirrors the validation logic in AgentChatComponent.vue handleVoiceMessage
"""

import os
import sys

sys.path.insert(0, os.getcwd())

import pytest
from hypothesis import given, settings, strategies as st


# =============================================================================
# === 前端验证逻辑的 Python 镜像 ===
# =============================================================================

VALID_ACTIONS = {"play", "pause", "seek", "stop"}


def validate_media_command(msg: dict) -> bool:
    """
    镜像 AgentChatComponent.vue 中 handleVoiceMessage 的 media_command 验证逻辑。

    验证规则：
    - msg.data 必须存在
    - data.action 必须是 play/pause/seek/stop 之一
    - data.media_id 必须存在且非空
    - data.media_type 必须存在且非空
    - data.media_url 必须存在且非空
    - data.start_time 不能是 undefined/null (None)
    """
    data = msg.get("data")
    if not data:
        return False
    if data.get("action") not in VALID_ACTIONS:
        return False
    if not data.get("media_id"):
        return False
    if not data.get("media_type"):
        return False
    if not data.get("media_url"):
        return False
    if data.get("start_time") is None:
        return False
    return True


# =============================================================================
# === Strategies ===
# =============================================================================

valid_actions = st.sampled_from(["play", "pause", "seek", "stop"])
valid_media_types = st.sampled_from(["video", "audio"])

valid_media_command_msg = st.fixed_dictionaries({
    "type": st.just("media_command"),
    "data": st.fixed_dictionaries({
        "action": valid_actions,
        "media_id": st.text(min_size=1, max_size=30, alphabet=st.characters(whitelist_categories=("L", "N"))),
        "media_type": valid_media_types,
        "media_url": st.builds(lambda p: f"http://minio:9000/{p}", p=st.text(min_size=1, max_size=30, alphabet="abcdefghijklmnopqrstuvwxyz0123456789/._-")),
        "start_time": st.floats(min_value=0, max_value=86400, allow_nan=False, allow_infinity=False),
        "end_time": st.one_of(st.none(), st.floats(min_value=0, max_value=86400, allow_nan=False, allow_infinity=False)),
        "description": st.one_of(st.none(), st.text(min_size=0, max_size=100)),
    }),
})

invalid_actions = st.text(min_size=1, max_size=20, alphabet="abcdefghijklmnopqrstuvwxyz").filter(
    lambda x: x not in VALID_ACTIONS
)


# =============================================================================
# === Property Tests ===
# =============================================================================


class TestFrontendMediaCommandValidation:
    """Property tests for frontend media_command validation (Property 8 - frontend part)."""

    @given(msg=valid_media_command_msg)
    @settings(max_examples=100)
    def test_valid_commands_accepted(self, msg: dict):
        """
        Property: For any media_command with valid action, media_id, media_type,
        media_url, and start_time, the frontend validation should accept it.

        **Validates: Requirements 8.5**
        """
        assert validate_media_command(msg) is True

    @given(
        action=invalid_actions,
        media_id=st.text(min_size=1, max_size=10, alphabet="abcdef"),
        media_url=st.just("http://minio:9000/test.mp4"),
    )
    @settings(max_examples=50)
    def test_invalid_action_rejected(self, action: str, media_id: str, media_url: str):
        """
        Property: Any media_command with an action not in {play, pause, seek, stop}
        should be rejected by the frontend.

        **Validates: Requirements 8.5**
        """
        msg = {
            "type": "media_command",
            "data": {
                "action": action,
                "media_id": media_id,
                "media_type": "video",
                "media_url": media_url,
                "start_time": 0,
            },
        }
        assert validate_media_command(msg) is False


# =============================================================================
# === Unit Tests ===
# =============================================================================


class TestFrontendMediaCommandValidationUnit:
    """Unit tests for frontend media_command validation."""

    def test_valid_play_command(self):
        """有效的 play 指令应被接受"""
        msg = {
            "type": "media_command",
            "data": {
                "action": "play",
                "media_id": "VI123456",
                "media_type": "video",
                "media_url": "http://minio:9000/kb-files/test.mp4",
                "start_time": 13,
                "end_time": 18,
                "description": "手术切口缝合片段",
            },
        }
        assert validate_media_command(msg) is True

    def test_valid_pause_command(self):
        """有效的 pause 指令应被接受"""
        msg = {
            "type": "media_command",
            "data": {
                "action": "pause",
                "media_id": "VI123456",
                "media_type": "audio",
                "media_url": "http://minio:9000/audio.mp3",
                "start_time": 0,
            },
        }
        assert validate_media_command(msg) is True

    def test_valid_seek_command(self):
        """有效的 seek 指令应被接受"""
        msg = {
            "type": "media_command",
            "data": {
                "action": "seek",
                "media_id": "VI100",
                "media_type": "video",
                "media_url": "http://minio:9000/video.mp4",
                "start_time": 42.5,
            },
        }
        assert validate_media_command(msg) is True

    def test_valid_stop_command(self):
        """有效的 stop 指令应被接受"""
        msg = {
            "type": "media_command",
            "data": {
                "action": "stop",
                "media_id": "VI999",
                "media_type": "audio",
                "media_url": "http://minio:9000/audio.mp3",
                "start_time": 0,
            },
        }
        assert validate_media_command(msg) is True

    def test_start_time_zero_is_valid(self):
        """start_time=0 应被接受（0 是有效值）"""
        msg = {
            "type": "media_command",
            "data": {
                "action": "play",
                "media_id": "VI123",
                "media_type": "video",
                "media_url": "http://minio:9000/test.mp4",
                "start_time": 0,
            },
        }
        assert validate_media_command(msg) is True

    def test_missing_data_rejected(self):
        """缺少 data 字段的指令应被拒绝"""
        msg = {"type": "media_command"}
        assert validate_media_command(msg) is False

    def test_empty_data_rejected(self):
        """空 data 的指令应被拒绝"""
        msg = {"type": "media_command", "data": {}}
        assert validate_media_command(msg) is False

    def test_missing_action_rejected(self):
        """缺少 action 的指令应被拒绝"""
        msg = {
            "type": "media_command",
            "data": {
                "media_id": "VI123",
                "media_type": "video",
                "media_url": "http://test.mp4",
                "start_time": 0,
            },
        }
        assert validate_media_command(msg) is False

    def test_invalid_action_rejected(self):
        """无效的 action 应被拒绝"""
        msg = {
            "type": "media_command",
            "data": {
                "action": "rewind",
                "media_id": "VI123",
                "media_type": "video",
                "media_url": "http://test.mp4",
                "start_time": 0,
            },
        }
        assert validate_media_command(msg) is False

    def test_missing_media_id_rejected(self):
        """缺少 media_id 的指令应被拒绝"""
        msg = {
            "type": "media_command",
            "data": {
                "action": "play",
                "media_type": "video",
                "media_url": "http://test.mp4",
                "start_time": 0,
            },
        }
        assert validate_media_command(msg) is False

    def test_missing_media_type_rejected(self):
        """缺少 media_type 的指令应被拒绝"""
        msg = {
            "type": "media_command",
            "data": {
                "action": "play",
                "media_id": "VI123",
                "media_url": "http://test.mp4",
                "start_time": 0,
            },
        }
        assert validate_media_command(msg) is False

    def test_missing_media_url_rejected(self):
        """缺少 media_url 的指令应被拒绝"""
        msg = {
            "type": "media_command",
            "data": {
                "action": "play",
                "media_id": "VI123",
                "media_type": "video",
                "start_time": 0,
            },
        }
        assert validate_media_command(msg) is False

    def test_missing_start_time_rejected(self):
        """缺少 start_time 的指令应被拒绝"""
        msg = {
            "type": "media_command",
            "data": {
                "action": "play",
                "media_id": "VI123",
                "media_type": "video",
                "media_url": "http://test.mp4",
            },
        }
        assert validate_media_command(msg) is False

    def test_null_start_time_rejected(self):
        """start_time=None 的指令应被拒绝"""
        msg = {
            "type": "media_command",
            "data": {
                "action": "play",
                "media_id": "VI123",
                "media_type": "video",
                "media_url": "http://test.mp4",
                "start_time": None,
            },
        }
        assert validate_media_command(msg) is False

    def test_optional_fields_not_required(self):
        """可选字段（end_time, description）不是必需的"""
        msg = {
            "type": "media_command",
            "data": {
                "action": "play",
                "media_id": "VI123",
                "media_type": "video",
                "media_url": "http://minio:9000/test.mp4",
                "start_time": 10,
            },
        }
        assert validate_media_command(msg) is True
