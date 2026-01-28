"""VoiceSessionManager 单元测试"""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.services.voice.session_manager import (
    VoiceSession,
    VoiceSessionConfig,
    VoiceSessionManager,
    VoiceSessionStatus,
    get_voice_session_manager,
)


@pytest.fixture
def mock_websocket():
    """创建模拟的 WebSocket"""
    ws = MagicMock()
    ws.send_json = AsyncMock()
    ws.close = AsyncMock()
    return ws


@pytest.fixture
def session_manager():
    """创建会话管理器实例"""
    return VoiceSessionManager(timeout_check_interval=1.0)


class TestVoiceSessionConfig:
    """VoiceSessionConfig 测试"""

    def test_default_config(self):
        """测试默认配置"""
        config = VoiceSessionConfig()
        assert config.asr_provider == "openai"
        assert config.tts_provider == "edge-tts"
        assert config.tts_voice == "zh-CN-XiaoxiaoNeural"
        assert config.tts_speed == 1.0
        assert config.session_timeout == 300

    def test_from_dict(self):
        """测试从字典创建配置"""
        data = {
            "asr_provider": "faster-whisper",
            "tts_provider": "openai",
            "tts_voice": "alloy",
            "session_timeout": 600,
        }
        config = VoiceSessionConfig.from_dict(data)
        assert config.asr_provider == "faster-whisper"
        assert config.tts_provider == "openai"
        assert config.tts_voice == "alloy"
        assert config.session_timeout == 600

    def test_to_dict(self):
        """测试转换为字典"""
        config = VoiceSessionConfig()
        data = config.to_dict()
        assert "asr_provider" in data
        assert "tts_provider" in data
        assert "session_timeout" in data

    def test_update(self):
        """测试更新配置"""
        config = VoiceSessionConfig()
        config.update({"tts_speed": 1.5, "vad_threshold": 0.7})
        assert config.tts_speed == 1.5
        assert config.vad_threshold == 0.7


class TestVoiceSession:
    """VoiceSession 测试"""

    def test_session_creation(self, mock_websocket):
        """测试会话创建"""
        session = VoiceSession(
            session_id="test-session-1",
            user_id="user-1",
            agent_id="voice_agent",
            thread_id="thread-1",
            websocket=mock_websocket,
        )
        assert session.session_id == "test-session-1"
        assert session.user_id == "user-1"
        assert session.status == VoiceSessionStatus.IDLE
        assert session.thread_id == "thread-1"

    def test_update_activity(self, mock_websocket):
        """测试更新活动时间"""
        session = VoiceSession(
            session_id="test-session-1",
            user_id="user-1",
            agent_id="voice_agent",
            thread_id="thread-1",
            websocket=mock_websocket,
        )
        old_activity = session.last_activity
        session.update_activity()
        assert session.last_activity >= old_activity

    def test_audio_buffer(self, mock_websocket):
        """测试音频缓冲区"""
        session = VoiceSession(
            session_id="test-session-1",
            user_id="user-1",
            agent_id="voice_agent",
            thread_id="thread-1",
            websocket=mock_websocket,
        )
        # 添加音频块
        session.add_audio_chunk(b"audio1")
        session.add_audio_chunk(b"audio2")
        assert session.get_audio_buffer_size() == 12

        # 清空缓冲区
        buffer = session.clear_audio_buffer()
        assert len(buffer) == 2
        assert session.get_audio_buffer_size() == 0

    def test_to_dict(self, mock_websocket):
        """测试序列化"""
        session = VoiceSession(
            session_id="test-session-1",
            user_id="user-1",
            agent_id="voice_agent",
            thread_id="thread-1",
            websocket=mock_websocket,
        )
        data = session.to_dict()
        assert data["session_id"] == "test-session-1"
        assert data["user_id"] == "user-1"
        assert data["status"] == "idle"


class TestVoiceSessionManager:
    """VoiceSessionManager 测试"""

    @pytest.mark.asyncio
    async def test_create_session(self, session_manager, mock_websocket):
        """测试创建会话 - Requirements 6.1, 6.6"""
        session = await session_manager.create_session(
            user_id="user-1",
            agent_id="voice_agent",
            websocket=mock_websocket,
        )
        assert session.user_id == "user-1"
        assert session.agent_id == "voice_agent"
        assert session.thread_id is not None
        assert session_manager.get_active_session_count() == 1

    @pytest.mark.asyncio
    async def test_create_session_with_thread_id(self, session_manager, mock_websocket):
        """测试使用指定 thread_id 创建会话 - Requirements 6.1"""
        session = await session_manager.create_session(
            user_id="user-1",
            agent_id="voice_agent",
            websocket=mock_websocket,
            thread_id="existing-thread-123",
        )
        assert session.thread_id == "existing-thread-123"

    @pytest.mark.asyncio
    async def test_get_session(self, session_manager, mock_websocket):
        """测试获取会话"""
        session = await session_manager.create_session(
            user_id="user-1",
            agent_id="voice_agent",
            websocket=mock_websocket,
        )
        retrieved = await session_manager.get_session(session.session_id)
        assert retrieved is not None
        assert retrieved.session_id == session.session_id

    @pytest.mark.asyncio
    async def test_get_session_by_websocket(self, session_manager, mock_websocket):
        """测试通过 WebSocket 获取会话"""
        session = await session_manager.create_session(
            user_id="user-1",
            agent_id="voice_agent",
            websocket=mock_websocket,
        )
        retrieved = await session_manager.get_session_by_websocket(mock_websocket)
        assert retrieved is not None
        assert retrieved.session_id == session.session_id

    @pytest.mark.asyncio
    async def test_get_user_sessions(self, session_manager, mock_websocket):
        """测试获取用户的所有会话 - Requirements 6.6"""
        # 创建多个会话
        ws1 = MagicMock()
        ws2 = MagicMock()
        await session_manager.create_session(user_id="user-1", agent_id="agent1", websocket=ws1)
        await session_manager.create_session(user_id="user-1", agent_id="agent2", websocket=ws2)
        await session_manager.create_session(user_id="user-2", agent_id="agent1", websocket=mock_websocket)

        user1_sessions = await session_manager.get_user_sessions("user-1")
        assert len(user1_sessions) == 2

        user2_sessions = await session_manager.get_user_sessions("user-2")
        assert len(user2_sessions) == 1

    @pytest.mark.asyncio
    async def test_remove_session(self, session_manager, mock_websocket):
        """测试移除会话 - Requirements 6.3"""
        session = await session_manager.create_session(
            user_id="user-1",
            agent_id="voice_agent",
            websocket=mock_websocket,
        )
        session_id = session.session_id

        result = await session_manager.remove_session(session_id)
        assert result is True
        assert await session_manager.get_session(session_id) is None
        assert session_manager.get_active_session_count() == 0

    @pytest.mark.asyncio
    async def test_update_session_status(self, session_manager, mock_websocket):
        """测试更新会话状态"""
        session = await session_manager.create_session(
            user_id="user-1",
            agent_id="voice_agent",
            websocket=mock_websocket,
        )
        await session_manager.update_session_status(session.session_id, VoiceSessionStatus.LISTENING)
        updated = await session_manager.get_session(session.session_id)
        assert updated.status == VoiceSessionStatus.LISTENING

    @pytest.mark.asyncio
    async def test_update_session_config(self, session_manager, mock_websocket):
        """测试更新会话配置"""
        session = await session_manager.create_session(
            user_id="user-1",
            agent_id="voice_agent",
            websocket=mock_websocket,
        )
        await session_manager.update_session_config(session.session_id, {"tts_speed": 1.5})
        updated = await session_manager.get_session(session.session_id)
        assert updated.config.tts_speed == 1.5

    @pytest.mark.asyncio
    async def test_session_timeout(self, session_manager, mock_websocket):
        """测试会话超时 - Requirements 6.4"""
        # 创建一个超时时间很短的会话
        config = VoiceSessionConfig(session_timeout=1)
        session = await session_manager.create_session(
            user_id="user-1",
            agent_id="voice_agent",
            websocket=mock_websocket,
            config=config,
        )

        # 初始不应该超时
        assert not session.is_timeout()

        # 等待超时
        await asyncio.sleep(1.5)
        assert session.is_timeout()

    @pytest.mark.asyncio
    async def test_concurrent_sessions(self, session_manager):
        """测试并发会话 - Requirements 6.6"""
        # 创建多个并发会话
        sessions = []
        for i in range(5):
            ws = MagicMock()
            session = await session_manager.create_session(
                user_id=f"user-{i}",
                agent_id="voice_agent",
                websocket=ws,
            )
            sessions.append(session)

        assert session_manager.get_active_session_count() == 5

        # 每个会话应该独立
        for i, session in enumerate(sessions):
            assert session.user_id == f"user-{i}"
            retrieved = await session_manager.get_session(session.session_id)
            assert retrieved is not None

    @pytest.mark.asyncio
    async def test_close_all_sessions(self, session_manager):
        """测试关闭所有会话"""
        for i in range(3):
            ws = MagicMock()
            await session_manager.create_session(
                user_id=f"user-{i}",
                agent_id="voice_agent",
                websocket=ws,
            )

        assert session_manager.get_active_session_count() == 3
        await session_manager.close_all_sessions()
        assert session_manager.get_active_session_count() == 0


class TestGlobalSessionManager:
    """全局会话管理器测试"""

    def test_get_voice_session_manager(self):
        """测试获取全局实例"""
        manager1 = get_voice_session_manager()
        manager2 = get_voice_session_manager()
        assert manager1 is manager2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
