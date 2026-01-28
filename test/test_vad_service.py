"""Test VAD Service Implementation.

This module tests the Silero VAD service implementation.
"""

import numpy as np
import pytest


class TestSileroVADService:
    """Tests for SileroVADService."""

    def test_create_vad_service_silero(self):
        """Test creating VAD service with silero provider."""
        from src.services.voice import create_vad_service

        service = create_vad_service(provider="silero", threshold=0.5)
        assert service is not None
        assert service.threshold == 0.5
        assert service.sample_rate == 16000

    def test_create_vad_service_invalid_provider(self):
        """Test creating VAD service with invalid provider raises error."""
        from src.services.voice import create_vad_service

        with pytest.raises(ValueError, match="Unsupported VAD provider"):
            create_vad_service(provider="invalid")

    def test_create_vad_service_invalid_sample_rate(self):
        """Test creating VAD service with invalid sample rate raises error."""
        from src.services.voice import VADError, create_vad_service

        with pytest.raises(VADError, match="Unsupported sample rate"):
            create_vad_service(provider="silero", sample_rate=44100)

    def test_create_vad_service_invalid_threshold(self):
        """Test creating VAD service with invalid threshold raises error."""
        from src.services.voice import VADError, create_vad_service

        with pytest.raises(VADError, match="Threshold must be between"):
            create_vad_service(provider="silero", threshold=1.5)

    def test_detect_speech_empty_audio(self):
        """Test detect_speech with empty audio returns False."""
        from src.services.voice import create_vad_service

        service = create_vad_service(provider="silero")
        result = service.detect_speech(b"")
        assert result is False

    def test_detect_speech_silence(self):
        """Test detect_speech with silence returns False."""
        from src.services.voice import create_vad_service

        service = create_vad_service(provider="silero", threshold=0.5)

        # Generate 1 second of silence (16kHz, 16-bit, mono)
        # 16000 samples * 2 bytes = 32000 bytes
        silence = np.zeros(16000, dtype=np.int16).tobytes()

        result = service.detect_speech(silence)
        assert result is False

    def test_detect_speech_with_tone(self):
        """Test detect_speech with a tone signal.

        Note: A pure tone may or may not be detected as speech
        depending on the model. This test verifies the function
        runs without error.
        """
        from src.services.voice import create_vad_service

        service = create_vad_service(provider="silero", threshold=0.5)

        # Generate a 440Hz tone (1 second, 16kHz, 16-bit, mono)
        sample_rate = 16000
        duration = 1.0
        frequency = 440
        t = np.linspace(0, duration, int(sample_rate * duration), dtype=np.float32)
        tone = (np.sin(2 * np.pi * frequency * t) * 32767 * 0.5).astype(np.int16)

        # Should not raise an error
        result = service.detect_speech(tone.tobytes())
        assert isinstance(result, bool)

    def test_detect_speech_small_chunk(self):
        """Test detect_speech with chunk smaller than minimum returns False."""
        from src.services.voice import create_vad_service

        service = create_vad_service(provider="silero")

        # Generate a very small chunk (100 samples = 200 bytes)
        small_chunk = np.zeros(100, dtype=np.int16).tobytes()

        result = service.detect_speech(small_chunk)
        assert result is False

    def test_detect_speech_end_empty_chunks(self):
        """Test detect_speech_end with empty chunks returns False."""
        from src.services.voice import create_vad_service

        service = create_vad_service(provider="silero")
        result = service.detect_speech_end([])
        assert result is False

    def test_detect_speech_end_with_silence(self):
        """Test detect_speech_end with silence returns True (speech ended)."""
        from src.services.voice import create_vad_service

        service = create_vad_service(provider="silero", threshold=0.5)

        # Generate 1 second of silence
        silence = np.zeros(16000, dtype=np.int16).tobytes()

        # Pass multiple chunks of silence
        result = service.detect_speech_end([silence], silence_duration=0.5)
        assert result is True

    def test_detect_speech_end_insufficient_audio(self):
        """Test detect_speech_end with insufficient audio returns False."""
        from src.services.voice import create_vad_service

        service = create_vad_service(provider="silero")

        # Generate only 0.1 seconds of audio
        short_audio = np.zeros(1600, dtype=np.int16).tobytes()

        # Request 0.8 seconds of silence detection
        result = service.detect_speech_end([short_audio], silence_duration=0.8)
        assert result is False

    def test_get_speech_probability(self):
        """Test get_speech_probability returns valid probability."""
        from src.services.voice import create_vad_service

        service = create_vad_service(provider="silero")

        # Generate silence
        silence = np.zeros(16000, dtype=np.int16).tobytes()

        prob = service.get_speech_probability(silence)
        assert 0.0 <= prob <= 1.0

    def test_get_speech_probability_empty(self):
        """Test get_speech_probability with empty audio returns 0."""
        from src.services.voice import create_vad_service

        service = create_vad_service(provider="silero")
        prob = service.get_speech_probability(b"")
        assert prob == 0.0

    def test_reset(self):
        """Test reset method doesn't raise error."""
        from src.services.voice import create_vad_service

        service = create_vad_service(provider="silero")
        # Should not raise
        service.reset()

    def test_model_caching(self):
        """Test that model is cached between instances."""
        from src.services.voice import SileroVADService

        # Create two instances
        service1 = SileroVADService(threshold=0.3)
        service2 = SileroVADService(threshold=0.7)

        # They should share the same model
        assert service1.model is service2.model

    def test_protocol_compliance(self):
        """Test that SileroVADService implements VADService protocol."""
        from src.services.voice import SileroVADService, VADService

        service = SileroVADService()
        assert isinstance(service, VADService)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
