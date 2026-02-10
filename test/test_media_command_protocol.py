"""Property Test: 播放指令协议验证 (Property 8)

**Validates: Requirements 8.3, 8.4, 8.5**

综合验证播放指令协议的属性测试：
- 验证指令包含必需字段 (action, media_id, media_type, media_url, start_time)
- 验证 action 类型有效性 (play/pause/seek/stop)
- 验证无效指令被忽略（后端拒绝 + 前端忽略）
- 验证后端与前端验证逻辑的一致性
"""

import os
import sys

sys.path.insert(0, os.getcwd())

import pytest
from hypothesis import given, settings, strategies as st
from pydantic import ValidationError

from src.services.media_command import MediaPlayCommand

# =============================================================================
# === 前端验证逻辑镜像（与 test_frontend_media_command_validation.py 一致）===
# =============================================================================

VALID_ACTIONS = {"play", "pause", "seek", "stop"}
REQUIRED_FIELDS = {"action", "media_id", "media_type", "media_url", "start_time"}


def validate_media_command(msg: dict) -> bool:
    """镜像前端 media_command 验证逻辑"""
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
non_empty_text = st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=("L", "N")))
url_text = st.builds(
    lambda p: f"http://minio:9000/{p}",
    p=st.text(min_size=1, max_size=30, alphabet="abcdefghijklmnopqrstuvwxyz0123456789/._-"),
)
valid_start_time = st.floats(min_value=0, max_value=86400, allow_nan=False, allow_infinity=False)

# 完整的有效指令数据
valid_command_data = st.fixed_dictionaries({
    "action": valid_actions,
    "media_id": non_empty_text,
    "media_type": valid_media_types,
    "media_url": url_text,
    "start_time": valid_start_time,
    "end_time": st.one_of(st.none(), st.floats(min_value=0, max_value=86400, allow_nan=False, allow_infinity=False)),
    "description": st.one_of(st.none(), st.text(min_size=0, max_size=100)),
})

# 无效 action 策略
invalid_actions = st.text(min_size=1, max_size=20, alphabet="abcdefghijklmnopqrstuvwxyz").filter(
    lambda x: x not in VALID_ACTIONS
)

# 要移除的必需字段名
required_field_to_remove = st.sampled_from(list(REQUIRED_FIELDS))


# =============================================================================
# === Property Tests: 播放指令协议验证 (Property 8) ===
# =============================================================================


class TestMediaCommandProtocol:
    """Property 8: 播放指令协议验证

    For any 播放指令 JSON，必须包含 action、media_id、media_type、media_url、start_time 字段，
    且 action 必须是 play/pause/seek/stop 之一。无效指令应被忽略并记录警告。
    """

    @given(data=valid_command_data)
    @settings(max_examples=100)
    def test_valid_command_contains_all_required_fields(self, data: dict):
        """
        Property: 任何有效的播放指令都必须包含所有必需字段。

        验证通过 Pydantic 模型创建的指令，转换为 WS 消息后，
        data 部分始终包含 action、media_id、media_type、media_url、start_time。

        **Validates: Requirements 8.3**
        """
        cmd = MediaPlayCommand(**data)
        msg = cmd.to_ws_message()
        msg_data = msg["data"]

        for field in REQUIRED_FIELDS:
            assert field in msg_data, f"必需字段 '{field}' 缺失"

    @given(data=valid_command_data)
    @settings(max_examples=100)
    def test_valid_command_action_is_valid_type(self, data: dict):
        """
        Property: 任何有效指令的 action 必须是 play/pause/seek/stop 之一。

        **Validates: Requirements 8.4**
        """
        cmd = MediaPlayCommand(**data)
        assert cmd.action in VALID_ACTIONS

    @given(action=invalid_actions)
    @settings(max_examples=100)
    def test_invalid_action_rejected_by_backend(self, action: str):
        """
        Property: 任何不在 {play, pause, seek, stop} 中的 action 都应被后端拒绝。

        **Validates: Requirements 8.4**
        """
        with pytest.raises(ValidationError):
            MediaPlayCommand(
                action=action,
                media_id="VI123",
                media_type="video",
                media_url="http://minio:9000/test.mp4",
                start_time=0,
            )

    @given(
        field=required_field_to_remove,
        action=valid_actions,
        media_id=non_empty_text,
        media_type=valid_media_types,
        media_url=url_text,
        start_time=valid_start_time,
    )
    @settings(max_examples=100)
    def test_missing_any_required_field_rejected_by_frontend(
        self, field: str, action: str, media_id: str, media_type: str, media_url: str, start_time: float
    ):
        """
        Property: 缺少任意一个必需字段的指令都应被前端验证拒绝。

        **Validates: Requirements 8.5**
        """
        data = {
            "action": action,
            "media_id": media_id,
            "media_type": media_type,
            "media_url": media_url,
            "start_time": start_time,
        }
        # 移除一个必需字段
        del data[field]

        msg = {"type": "media_command", "data": data}
        assert validate_media_command(msg) is False, f"缺少 '{field}' 的指令应被拒绝"

    @given(data=valid_command_data)
    @settings(max_examples=100)
    def test_backend_frontend_validation_consistency(self, data: dict):
        """
        Property: 后端接受的有效指令，前端验证也应接受。
        确保后端和前端的验证逻辑一致。

        **Validates: Requirements 8.3, 8.5**
        """
        # 后端创建成功
        cmd = MediaPlayCommand(**data)
        ws_msg = cmd.to_ws_message()

        # 前端验证也应通过
        assert validate_media_command(ws_msg) is True, "后端接受的指令，前端也应接受"

    @given(
        action=invalid_actions,
        media_id=non_empty_text,
        media_url=url_text,
        start_time=valid_start_time,
    )
    @settings(max_examples=100)
    def test_invalid_action_rejected_by_both_backend_and_frontend(
        self, action: str, media_id: str, media_url: str, start_time: float
    ):
        """
        Property: 无效 action 的指令应同时被后端和前端拒绝。

        **Validates: Requirements 8.4, 8.5**
        """
        # 后端拒绝
        with pytest.raises(ValidationError):
            MediaPlayCommand(
                action=action,
                media_id=media_id,
                media_type="video",
                media_url=media_url,
                start_time=start_time,
            )

        # 前端也拒绝
        msg = {
            "type": "media_command",
            "data": {
                "action": action,
                "media_id": media_id,
                "media_type": "video",
                "media_url": media_url,
                "start_time": start_time,
            },
        }
        assert validate_media_command(msg) is False
