"""VoiceSessionManager 独立测试脚本"""

import asyncio
from unittest.mock import AsyncMock, MagicMock

from src.services.voice.session_manager import (
    VoiceSession,
    VoiceSessionConfig,
    VoiceSessionManager,
    VoiceSessionStatus,
)


async def run_tests():
    print("=== 测试 VoiceSessionConfig ===")

    # 测试默认配置
    config = VoiceSessionConfig()
    assert config.asr_provider == "openai"
    assert config.tts_provider == "edge-tts"
    assert config.session_timeout == 300
    print("✓ 默认配置测试通过")

    # 测试从字典创建
    data = {"asr_provider": "faster-whisper", "session_timeout": 600}
    config = VoiceSessionConfig.from_dict(data)
    assert config.asr_provider == "faster-whisper"
    assert config.session_timeout == 600
    print("✓ from_dict 测试通过")

    # 测试更新配置
    config.update({"tts_speed": 1.5})
    assert config.tts_speed == 1.5
    print("✓ update 测试通过")

    print()
    print("=== 测试 VoiceSession ===")

    # 创建模拟 WebSocket
    mock_ws = MagicMock()
    mock_ws.send_json = AsyncMock()
    mock_ws.close = AsyncMock()

    # 测试会话创建
    session = VoiceSession(
        session_id="test-1",
        user_id="user-1",
        agent_id="voice_agent",
        thread_id="thread-1",
        websocket=mock_ws,
    )
    assert session.status == VoiceSessionStatus.IDLE
    assert session.user_id == "user-1"
    print("✓ 会话创建测试通过")

    # 测试音频缓冲区
    session.add_audio_chunk(b"audio1")
    session.add_audio_chunk(b"audio2")
    assert session.get_audio_buffer_size() == 12
    buffer = session.clear_audio_buffer()
    assert len(buffer) == 2
    assert session.get_audio_buffer_size() == 0
    print("✓ 音频缓冲区测试通过")

    print()
    print("=== 测试 VoiceSessionManager ===")

    manager = VoiceSessionManager(timeout_check_interval=1.0)

    # 测试创建会话 (Requirements 6.1, 6.6)
    ws1 = MagicMock()
    session1 = await manager.create_session(
        user_id="user-1",
        agent_id="voice_agent",
        websocket=ws1,
    )
    assert session1.user_id == "user-1"
    assert session1.thread_id is not None
    assert manager.get_active_session_count() == 1
    print("✓ 创建会话测试通过 (Requirements 6.1)")

    # 测试获取会话
    retrieved = await manager.get_session(session1.session_id)
    assert retrieved is not None
    assert retrieved.session_id == session1.session_id
    print("✓ 获取会话测试通过")

    # 测试通过 WebSocket 获取会话
    retrieved = await manager.get_session_by_websocket(ws1)
    assert retrieved is not None
    print("✓ 通过 WebSocket 获取会话测试通过")

    # 测试多用户并发会话 (Requirements 6.6)
    ws2 = MagicMock()
    ws3 = MagicMock()
    await manager.create_session(user_id="user-1", agent_id="agent2", websocket=ws2)
    await manager.create_session(user_id="user-2", agent_id="agent1", websocket=ws3)

    user1_sessions = await manager.get_user_sessions("user-1")
    assert len(user1_sessions) == 2
    user2_sessions = await manager.get_user_sessions("user-2")
    assert len(user2_sessions) == 1
    print("✓ 多用户并发会话测试通过 (Requirements 6.6)")

    # 测试更新会话状态
    await manager.update_session_status(session1.session_id, VoiceSessionStatus.LISTENING)
    updated = await manager.get_session(session1.session_id)
    assert updated.status == VoiceSessionStatus.LISTENING
    print("✓ 更新会话状态测试通过")

    # 测试更新会话配置
    await manager.update_session_config(session1.session_id, {"tts_speed": 1.5})
    updated = await manager.get_session(session1.session_id)
    assert updated.config.tts_speed == 1.5
    print("✓ 更新会话配置测试通过")

    # 测试移除会话 (Requirements 6.3)
    result = await manager.remove_session(session1.session_id)
    assert result is True
    assert await manager.get_session(session1.session_id) is None
    print("✓ 移除会话测试通过 (Requirements 6.3)")

    # 测试会话超时 (Requirements 6.4)
    short_config = VoiceSessionConfig(session_timeout=1)
    ws4 = MagicMock()
    timeout_session = await manager.create_session(
        user_id="user-timeout",
        agent_id="voice_agent",
        websocket=ws4,
        config=short_config,
    )
    assert not timeout_session.is_timeout()
    await asyncio.sleep(1.5)
    assert timeout_session.is_timeout()
    print("✓ 会话超时测试通过 (Requirements 6.4)")

    # 测试关闭所有会话
    await manager.close_all_sessions()
    assert manager.get_active_session_count() == 0
    print("✓ 关闭所有会话测试通过")

    print()
    print("=== 所有测试通过! ===")


if __name__ == "__main__":
    asyncio.run(run_tests())
