"""Tests for MediaPlayCommand data model.

**Validates: Requirements 8.3, 8.4**

Tests the media play command protocol including:
- Valid command creation and serialization
- WebSocket message format correctness
- Action type validation (play/pause/seek/stop)
- Invalid command rejection
"""

import os
import sys

sys.path.insert(0, os.getcwd())

import pytest
from hypothesis import given, settings, strategies as st
from pydantic import ValidationError

from src.services.media_command import MediaPlayCommand


# =============================================================================
# === Strategies ===
# =============================================================================

valid_actions = st.sampled_from(["play", "pause", "seek", "stop"])
valid_media_types = st.sampled_from(["video", "audio"])

# 生成有效的 MediaPlayCommand 数据
valid_command_data = st.fixed_dictionaries({
    "action": valid_actions,
    "media_id": st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=("L", "N"))),
    "media_type": valid_media_types,
    "media_url": st.builds(lambda path: f"http://minio:9000/{path}", path=st.text(min_size=1, max_size=50, alphabet="abcdefghijklmnopqrstuvwxyz0123456789/-_.")),
    "start_time": st.floats(min_value=0, max_value=86400, allow_nan=False, allow_infinity=False),
    "end_time": st.one_of(st.none(), st.floats(min_value=0, max_value=86400, allow_nan=False, allow_infinity=False)),
    "description": st.one_of(st.none(), st.text(min_size=1, max_size=200)),
})

invalid_actions = st.text(min_size=1, max_size=20, alphabet="abcdefghijklmnopqrstuvwxyz").filter(
    lambda x: x not in {"play", "pause", "seek", "stop"}
)

invalid_media_types = st.text(min_size=1, max_size=20, alphabet="abcdefghijklmnopqrstuvwxyz").filter(
    lambda x: x not in {"video", "audio"}
)


# =============================================================================
# === Property Tests ===
# =============================================================================


class TestMediaPlayCommandProtocol:
    """Property tests for MediaPlayCommand protocol validation (Property 8)."""

    @given(data=valid_command_data)
    @settings(max_examples=100)
    def test_valid_commands_create_successfully(self, data: dict):
        """
        Property: For any valid combination of action/media_type/fields,
        MediaPlayCommand should be created without error.

        **Validates: Requirements 8.3**
        """
        cmd = MediaPlayCommand(**data)
        assert cmd.action == data["action"]
        assert cmd.media_id == data["media_id"]
        assert cmd.media_type == data["media_type"]
        assert cmd.media_url == data["media_url"]
        assert cmd.start_time == data["start_time"]

    @given(data=valid_command_data)
    @settings(max_examples=100)
    def test_ws_message_format(self, data: dict):
        """
        Property: For any valid command, to_ws_message() must return
        {"type": "media_command", "data": {...}} with all required fields.

        **Validates: Requirements 8.3**
        """
        cmd = MediaPlayCommand(**data)
        msg = cmd.to_ws_message()

        assert msg["type"] == "media_command"
        assert isinstance(msg["data"], dict)

        # 必需字段始终存在
        msg_data = msg["data"]
        assert "action" in msg_data
        assert "media_id" in msg_data
        assert "media_type" in msg_data
        assert "media_url" in msg_data
        assert "start_time" in msg_data

    @given(data=valid_command_data)
    @settings(max_examples=100)
    def test_ws_message_excludes_none_fields(self, data: dict):
        """
        Property: For any valid command, to_ws_message() should exclude
        None-valued optional fields from the data payload.

        **Validates: Requirements 8.3**
        """
        cmd = MediaPlayCommand(**data)
        msg = cmd.to_ws_message()
        msg_data = msg["data"]

        if data["end_time"] is None:
            assert "end_time" not in msg_data
        else:
            assert msg_data["end_time"] == data["end_time"]

        if data["description"] is None:
            assert "description" not in msg_data
        else:
            assert msg_data["description"] == data["description"]

    @given(action=valid_actions)
    @settings(max_examples=20)
    def test_all_action_types_accepted(self, action: str):
        """
        Property: All four action types (play/pause/seek/stop) must be accepted.

        **Validates: Requirements 8.4**
        """
        cmd = MediaPlayCommand(
            action=action,
            media_id="VI123456",
            media_type="video",
            media_url="http://minio:9000/test.mp4",
            start_time=0,
        )
        assert cmd.action == action

    @given(action=invalid_actions)
    @settings(max_examples=50)
    def test_invalid_action_rejected(self, action: str):
        """
        Property: Any action not in {play, pause, seek, stop} must be rejected.

        **Validates: Requirements 8.4**
        """
        with pytest.raises(ValidationError):
            MediaPlayCommand(
                action=action,
                media_id="VI123456",
                media_type="video",
                media_url="http://minio:9000/test.mp4",
                start_time=0,
            )

    @given(media_type=invalid_media_types)
    @settings(max_examples=50)
    def test_invalid_media_type_rejected(self, media_type: str):
        """
        Property: Any media_type not in {video, audio} must be rejected.

        **Validates: Requirements 8.3**
        """
        with pytest.raises(ValidationError):
            MediaPlayCommand(
                action="play",
                media_id="VI123456",
                media_type=media_type,
                media_url="http://minio:9000/test.mp4",
                start_time=0,
            )


# =============================================================================
# === Unit Tests ===
# =============================================================================


class TestMediaPlayCommandUnit:
    """Unit tests for MediaPlayCommand."""

    def test_basic_play_command(self):
        """Test creating a basic play command."""
        cmd = MediaPlayCommand(
            action="play",
            media_id="VI123456",
            media_type="video",
            media_url="http://minio:9000/kb-files/test.mp4",
            start_time=13,
            end_time=18,
            description="手术切口缝合片段",
        )
        assert cmd.action == "play"
        assert cmd.media_id == "VI123456"
        assert cmd.media_type == "video"
        assert cmd.start_time == 13
        assert cmd.end_time == 18

    def test_to_ws_message_full(self):
        """Test WebSocket message with all fields."""
        cmd = MediaPlayCommand(
            action="play",
            media_id="VI123456",
            media_type="video",
            media_url="http://minio:9000/kb-files/test.mp4",
            start_time=13,
            end_time=18,
            description="片段描述",
        )
        msg = cmd.to_ws_message()

        assert msg == {
            "type": "media_command",
            "data": {
                "action": "play",
                "media_id": "VI123456",
                "media_type": "video",
                "media_url": "http://minio:9000/kb-files/test.mp4",
                "start_time": 13,
                "end_time": 18,
                "description": "片段描述",
            },
        }

    def test_to_ws_message_minimal(self):
        """Test WebSocket message with only required fields."""
        cmd = MediaPlayCommand(
            action="stop",
            media_id="VI999",
            media_type="audio",
            media_url="http://minio:9000/audio.mp3",
            start_time=0,
        )
        msg = cmd.to_ws_message()

        assert msg["type"] == "media_command"
        assert msg["data"] == {
            "action": "stop",
            "media_id": "VI999",
            "media_type": "audio",
            "media_url": "http://minio:9000/audio.mp3",
            "start_time": 0,
        }
        assert "end_time" not in msg["data"]
        assert "description" not in msg["data"]

    def test_missing_required_field_raises(self):
        """Test that missing required fields raise ValidationError."""
        with pytest.raises(ValidationError):
            MediaPlayCommand(
                action="play",
                media_type="video",
                media_url="http://test.mp4",
                start_time=0,
                # missing media_id
            )

    def test_seek_command(self):
        """Test seek action command."""
        cmd = MediaPlayCommand(
            action="seek",
            media_id="VI100",
            media_type="video",
            media_url="http://minio:9000/video.mp4",
            start_time=42.5,
        )
        assert cmd.action == "seek"
        assert cmd.start_time == 42.5

    def test_pause_command(self):
        """Test pause action command."""
        cmd = MediaPlayCommand(
            action="pause",
            media_id="VI100",
            media_type="audio",
            media_url="http://minio:9000/audio.mp3",
            start_time=0,
        )
        assert cmd.action == "pause"
        assert cmd.media_type == "audio"
