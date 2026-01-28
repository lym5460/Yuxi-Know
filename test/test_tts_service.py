"""Test TTS Service implementations.

This module tests the TTS service interface and implementations.
"""

import asyncio

import pytest

from src.services.voice import EdgeTTSService, TTSError, TTSService, create_tts_service


class TestEdgeTTSService:
    """Tests for EdgeTTSService."""

    def test_implements_protocol(self):
        """Test that EdgeTTSService implements TTSService protocol."""
        service = EdgeTTSService()
        assert isinstance(service, TTSService)

    def test_default_voice(self):
        """Test default voice initialization."""
        service = EdgeTTSService()
        assert service.default_voice == "zh-CN-XiaoxiaoNeural"

    def test_custom_default_voice(self):
        """Test custom default voice initialization."""
        service = EdgeTTSService(default_voice="en-US-JennyNeural")
        assert service.default_voice == "en-US-JennyNeural"

    def test_speed_to_rate_normal(self):
        """Test speed to rate conversion for normal speed."""
        service = EdgeTTSService()
        assert service._speed_to_rate(1.0) == "+0%"

    def test_speed_to_rate_fast(self):
        """Test speed to rate conversion for fast speed."""
        service = EdgeTTSService()
        assert service._speed_to_rate(1.5) == "+50%"

    def test_speed_to_rate_slow(self):
        """Test speed to rate conversion for slow speed."""
        service = EdgeTTSService()
        assert service._speed_to_rate(0.5) == "-50%"

    def test_speed_to_rate_clamped_high(self):
        """Test speed to rate conversion clamps high values."""
        service = EdgeTTSService()
        # Speed > 2.0 should be clamped to 2.0 = +100%
        assert service._speed_to_rate(3.0) == "+100%"

    def test_speed_to_rate_clamped_low(self):
        """Test speed to rate conversion clamps low values."""
        service = EdgeTTSService()
        # Speed < 0.5 should be clamped to 0.5 = -50%
        assert service._speed_to_rate(0.1) == "-50%"

    @pytest.mark.asyncio
    async def test_synthesize_empty_text(self):
        """Test synthesize with empty text returns empty bytes."""
        service = EdgeTTSService()
        result = await service.synthesize("")
        assert result == b""

    @pytest.mark.asyncio
    async def test_synthesize_whitespace_text(self):
        """Test synthesize with whitespace text returns empty bytes."""
        service = EdgeTTSService()
        result = await service.synthesize("   ")
        assert result == b""

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_synthesize_basic(self):
        """Test basic synthesis produces audio data."""
        service = EdgeTTSService()
        result = await service.synthesize("你好")
        assert isinstance(result, bytes)
        assert len(result) > 0

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_synthesize_with_voice(self):
        """Test synthesis with specific voice."""
        service = EdgeTTSService()
        result = await service.synthesize("Hello", voice="en-US-JennyNeural")
        assert isinstance(result, bytes)
        assert len(result) > 0

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_synthesize_with_speed(self):
        """Test synthesis with speed adjustment."""
        service = EdgeTTSService()
        result = await service.synthesize("你好", speed=1.5)
        assert isinstance(result, bytes)
        assert len(result) > 0


class TestCreateTTSService:
    """Tests for create_tts_service factory function."""

    def test_create_edge_tts_service(self):
        """Test creating Edge TTS service."""
        service = create_tts_service("edge-tts")
        assert isinstance(service, EdgeTTSService)

    def test_create_edge_tts_service_with_voice(self):
        """Test creating Edge TTS service with custom voice."""
        service = create_tts_service("edge-tts", default_voice="en-US-JennyNeural")
        assert isinstance(service, EdgeTTSService)
        assert service.default_voice == "en-US-JennyNeural"

    def test_create_unsupported_provider(self):
        """Test creating service with unsupported provider raises error."""
        with pytest.raises(ValueError, match="Unsupported TTS provider"):
            create_tts_service("unsupported-provider")


class TestTTSError:
    """Tests for TTSError exception."""

    def test_error_message(self):
        """Test error message is set correctly."""
        error = TTSError("Test error")
        assert str(error) == "Test error"

    def test_error_provider(self):
        """Test provider is set correctly."""
        error = TTSError("Test error", provider="edge-tts")
        assert error.provider == "edge-tts"

    def test_error_cause(self):
        """Test cause is set correctly."""
        cause = ValueError("Original error")
        error = TTSError("Test error", cause=cause)
        assert error.cause is cause
