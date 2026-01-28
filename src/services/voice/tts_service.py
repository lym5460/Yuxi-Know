"""TTS (Text-to-Speech) Service.

This module defines the TTS service interface and implementations.

Validates: Requirements 4.1, 4.2, 4.3
"""

import os
from collections.abc import AsyncIterator
from typing import Protocol, runtime_checkable

from src.utils import logger


@runtime_checkable
class TTSService(Protocol):
    """TTS Service Protocol.

    Defines the interface for text-to-speech synthesis services.
    Supports multiple providers (e.g., OpenAI TTS, Azure Speech, Edge TTS).

    Validates: Requirements 4.1
    """

    async def synthesize_stream(
        self,
        text_chunks: AsyncIterator[str],
        voice: str,
        speed: float = 1.0,
    ) -> AsyncIterator[bytes]:
        """Synthesize text to audio stream.

        Performs streaming speech synthesis, yielding audio chunks
        as they are generated without waiting for complete synthesis.

        Args:
            text_chunks: Async iterator of text chunks to synthesize
            voice: Voice identifier (provider-specific, e.g., "alloy", "zh-CN-XiaoxiaoNeural")
            speed: Speech speed multiplier (0.5 - 2.0, default 1.0)

        Yields:
            bytes: Audio data chunks (MP3/PCM format, 24kHz, 16bit, Mono)

        Raises:
            TTSError: If synthesis fails

        Validates: Requirements 4.2, 4.3
        """
        ...

    async def synthesize(
        self,
        text: str,
        voice: str,
        speed: float = 1.0,
    ) -> bytes:
        """Synthesize text to audio (non-streaming).

        Args:
            text: Text to synthesize
            voice: Voice identifier (provider-specific)
            speed: Speech speed multiplier (0.5 - 2.0, default 1.0)

        Returns:
            bytes: Complete audio data (MP3 format)

        Raises:
            TTSError: If synthesis fails
        """
        ...


class TTSError(Exception):
    """Exception raised when TTS synthesis fails.

    Validates: Requirements 4.5
    """

    def __init__(self, message: str, provider: str | None = None, cause: Exception | None = None):
        super().__init__(message)
        self.provider = provider
        self.cause = cause


class EdgeTTSService:
    """Edge TTS Service Implementation.

    Uses Microsoft Edge's free TTS service via the edge-tts library.
    Supports streaming synthesis for low latency.

    Validates: Requirements 4.1, 4.2, 4.3
    """

    # Default voices for different languages
    DEFAULT_VOICES = {
        "zh": "zh-CN-XiaoxiaoNeural",
        "en": "en-US-JennyNeural",
    }

    # Popular voice options
    AVAILABLE_VOICES = [
        # Chinese voices
        "zh-CN-XiaoxiaoNeural",  # Female, warm
        "zh-CN-YunxiNeural",  # Male, professional
        "zh-CN-YunjianNeural",  # Male, news anchor
        "zh-CN-XiaoyiNeural",  # Female, lively
        # English voices
        "en-US-JennyNeural",  # Female, conversational
        "en-US-GuyNeural",  # Male, conversational
        "en-US-AriaNeural",  # Female, professional
        "en-US-DavisNeural",  # Male, professional
        # Other languages
        "ja-JP-NanamiNeural",  # Japanese female
        "ko-KR-SunHiNeural",  # Korean female
    ]

    def __init__(self, default_voice: str | None = None):
        """Initialize Edge TTS Service.

        Args:
            default_voice: Default voice to use if not specified in synthesis calls.
                          Defaults to "zh-CN-XiaoxiaoNeural".
        """
        self.default_voice = default_voice or self.DEFAULT_VOICES["zh"]
        logger.debug(f"Edge TTS Service initialized with default voice: {self.default_voice}")

    def _speed_to_rate(self, speed: float) -> str:
        """Convert speed multiplier to Edge TTS rate format.

        Edge TTS uses percentage format like "+20%" or "-20%".

        Args:
            speed: Speed multiplier (0.5 - 2.0)

        Returns:
            str: Rate string in Edge TTS format (e.g., "+20%", "-50%")
        """
        # Clamp speed to valid range
        speed = max(0.5, min(2.0, speed))

        # Convert to percentage change
        # speed 1.0 = +0%, speed 1.5 = +50%, speed 0.5 = -50%
        percentage = int((speed - 1.0) * 100)

        if percentage >= 0:
            return f"+{percentage}%"
        else:
            return f"{percentage}%"

    async def synthesize(
        self,
        text: str,
        voice: str | None = None,
        speed: float = 1.0,
    ) -> bytes:
        """Synthesize text to audio (non-streaming).

        Args:
            text: Text to synthesize
            voice: Voice identifier (e.g., "zh-CN-XiaoxiaoNeural")
            speed: Speech speed multiplier (0.5 - 2.0, default 1.0)

        Returns:
            bytes: Complete audio data (MP3 format)

        Raises:
            TTSError: If synthesis fails

        Validates: Requirements 4.3
        """
        if not text or not text.strip():
            return b""

        try:
            import edge_tts
        except ImportError as e:
            raise TTSError(
                "edge-tts library not installed. Install with: pip install edge-tts",
                provider="edge-tts",
                cause=e,
            ) from e

        voice = voice or self.default_voice
        rate = self._speed_to_rate(speed)

        try:
            logger.debug(f"Edge TTS synthesizing: '{text[:50]}...' with voice={voice}, rate={rate}")

            communicate = edge_tts.Communicate(text, voice, rate=rate)
            audio_data = bytearray()

            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_data.extend(chunk["data"])

            logger.debug(f"Edge TTS synthesis complete: {len(audio_data)} bytes")
            return bytes(audio_data)

        except Exception as e:
            logger.error(f"Edge TTS synthesis failed: {e}")
            raise TTSError(f"Synthesis failed: {e}", provider="edge-tts", cause=e) from e

    async def synthesize_stream(
        self,
        text_chunks: AsyncIterator[str],
        voice: str | None = None,
        speed: float = 1.0,
    ) -> AsyncIterator[bytes]:
        """Synthesize text stream to audio stream.

        Performs streaming speech synthesis, yielding audio chunks
        as they are generated. This implementation:
        1. Accumulates text chunks until a sentence boundary is detected
        2. Synthesizes each sentence and yields audio chunks
        3. Continues until all text is processed

        Args:
            text_chunks: Async iterator of text chunks to synthesize
            voice: Voice identifier (e.g., "zh-CN-XiaoxiaoNeural")
            speed: Speech speed multiplier (0.5 - 2.0, default 1.0)

        Yields:
            bytes: Audio data chunks (MP3 format)

        Raises:
            TTSError: If synthesis fails

        Validates: Requirements 4.2, 4.3
        """
        try:
            import edge_tts
        except ImportError as e:
            raise TTSError(
                "edge-tts library not installed. Install with: pip install edge-tts",
                provider="edge-tts",
                cause=e,
            ) from e

        voice = voice or self.default_voice
        rate = self._speed_to_rate(speed)

        # Sentence boundary characters
        sentence_endings = {"。", "！", "？", ".", "!", "?", "\n"}

        text_buffer = ""

        try:
            async for chunk in text_chunks:
                text_buffer += chunk

                # Check for sentence boundaries
                while True:
                    # Find the first sentence ending
                    end_pos = -1
                    for i, char in enumerate(text_buffer):
                        if char in sentence_endings:
                            end_pos = i
                            break

                    if end_pos == -1:
                        # No complete sentence yet, continue accumulating
                        break

                    # Extract the sentence (including the ending character)
                    sentence = text_buffer[: end_pos + 1].strip()
                    text_buffer = text_buffer[end_pos + 1 :]

                    if sentence:
                        # Synthesize and yield audio chunks
                        logger.debug(f"Edge TTS streaming: '{sentence[:30]}...'")
                        communicate = edge_tts.Communicate(sentence, voice, rate=rate)

                        async for audio_chunk in communicate.stream():
                            if audio_chunk["type"] == "audio":
                                yield audio_chunk["data"]

            # Process remaining text in buffer
            if text_buffer.strip():
                logger.debug(f"Edge TTS streaming final: '{text_buffer[:30]}...'")
                communicate = edge_tts.Communicate(text_buffer.strip(), voice, rate=rate)

                async for audio_chunk in communicate.stream():
                    if audio_chunk["type"] == "audio":
                        yield audio_chunk["data"]

        except TTSError:
            raise
        except Exception as e:
            logger.error(f"Edge TTS stream synthesis failed: {e}")
            raise TTSError(f"Stream synthesis failed: {e}", provider="edge-tts", cause=e) from e


class OpenAITTSService:
    """OpenAI TTS Service Implementation.

    Uses OpenAI's TTS API for speech synthesis.
    Supports streaming synthesis for low latency.

    Validates: Requirements 4.1, 4.2, 4.3
    """

    # Available voices
    AVAILABLE_VOICES = ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]

    # Available models
    AVAILABLE_MODELS = ["tts-1", "tts-1-hd"]

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str = "tts-1",
        default_voice: str = "alloy",
    ):
        """Initialize OpenAI TTS Service.

        Args:
            api_key: OpenAI API key. If None, uses OPENAI_API_KEY env var.
            base_url: OpenAI API base URL. If None, uses OPENAI_API_BASE env var.
            model: TTS model to use (default: "tts-1")
            default_voice: Default voice to use (default: "alloy")
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.base_url = base_url or os.getenv("OPENAI_API_BASE")
        self.model = model
        self.default_voice = default_voice

        if not self.api_key:
            raise TTSError("OpenAI API key not provided", provider="openai")

        # Import here to avoid import errors if openai is not installed
        from openai import AsyncOpenAI

        self.client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)
        logger.debug(f"OpenAI TTS Service initialized with model: {model}, voice: {default_voice}")

    def _speed_to_openai_speed(self, speed: float) -> float:
        """Convert speed multiplier to OpenAI speed format.

        OpenAI TTS accepts speed from 0.25 to 4.0.

        Args:
            speed: Speed multiplier (0.5 - 2.0)

        Returns:
            float: Speed value for OpenAI API
        """
        # Clamp to OpenAI's valid range
        return max(0.25, min(4.0, speed))

    async def synthesize(
        self,
        text: str,
        voice: str | None = None,
        speed: float = 1.0,
    ) -> bytes:
        """Synthesize text to audio (non-streaming).

        Args:
            text: Text to synthesize
            voice: Voice identifier (e.g., "alloy", "nova")
            speed: Speech speed multiplier (0.25 - 4.0, default 1.0)

        Returns:
            bytes: Complete audio data (MP3 format)

        Raises:
            TTSError: If synthesis fails

        Validates: Requirements 4.3
        """
        if not text or not text.strip():
            return b""

        voice = voice or self.default_voice
        openai_speed = self._speed_to_openai_speed(speed)

        try:
            logger.debug(f"OpenAI TTS synthesizing: '{text[:50]}...' with voice={voice}, speed={openai_speed}")

            response = await self.client.audio.speech.create(
                model=self.model,
                voice=voice,
                input=text,
                speed=openai_speed,
                response_format="mp3",
            )

            audio_data = response.content
            logger.debug(f"OpenAI TTS synthesis complete: {len(audio_data)} bytes")
            return audio_data

        except Exception as e:
            logger.error(f"OpenAI TTS synthesis failed: {e}")
            raise TTSError(f"Synthesis failed: {e}", provider="openai", cause=e) from e

    async def synthesize_stream(
        self,
        text_chunks: AsyncIterator[str],
        voice: str | None = None,
        speed: float = 1.0,
    ) -> AsyncIterator[bytes]:
        """Synthesize text stream to audio stream.

        OpenAI TTS API supports streaming responses. This implementation:
        1. Accumulates text chunks until a sentence boundary is detected
        2. Sends each sentence to OpenAI API with streaming enabled
        3. Yields audio chunks as they are received

        Args:
            text_chunks: Async iterator of text chunks to synthesize
            voice: Voice identifier (e.g., "alloy", "nova")
            speed: Speech speed multiplier (0.25 - 4.0, default 1.0)

        Yields:
            bytes: Audio data chunks (MP3 format)

        Raises:
            TTSError: If synthesis fails

        Validates: Requirements 4.2, 4.3
        """
        voice = voice or self.default_voice
        openai_speed = self._speed_to_openai_speed(speed)

        # Sentence boundary characters
        sentence_endings = {"。", "！", "？", ".", "!", "?", "\n"}

        text_buffer = ""

        try:
            async for chunk in text_chunks:
                text_buffer += chunk

                # Check for sentence boundaries
                while True:
                    # Find the first sentence ending
                    end_pos = -1
                    for i, char in enumerate(text_buffer):
                        if char in sentence_endings:
                            end_pos = i
                            break

                    if end_pos == -1:
                        # No complete sentence yet, continue accumulating
                        break

                    # Extract the sentence (including the ending character)
                    sentence = text_buffer[: end_pos + 1].strip()
                    text_buffer = text_buffer[end_pos + 1 :]

                    if sentence:
                        # Synthesize and yield audio chunks using streaming
                        logger.debug(f"OpenAI TTS streaming: '{sentence[:30]}...'")

                        async with self.client.audio.speech.with_streaming_response.create(
                            model=self.model,
                            voice=voice,
                            input=sentence,
                            speed=openai_speed,
                            response_format="mp3",
                        ) as response:
                            async for audio_chunk in response.iter_bytes(chunk_size=4096):
                                yield audio_chunk

            # Process remaining text in buffer
            if text_buffer.strip():
                logger.debug(f"OpenAI TTS streaming final: '{text_buffer[:30]}...'")

                async with self.client.audio.speech.with_streaming_response.create(
                    model=self.model,
                    voice=voice,
                    input=text_buffer.strip(),
                    speed=openai_speed,
                    response_format="mp3",
                ) as response:
                    async for audio_chunk in response.iter_bytes(chunk_size=4096):
                        yield audio_chunk

        except TTSError:
            raise
        except Exception as e:
            logger.error(f"OpenAI TTS stream synthesis failed: {e}")
            raise TTSError(f"Stream synthesis failed: {e}", provider="openai", cause=e) from e


def create_tts_service(provider: str = "edge-tts", **kwargs) -> TTSService:
    """Factory function to create TTS service instances.

    Args:
        provider: TTS provider name. Supported: "edge-tts", "openai"
        **kwargs: Provider-specific configuration options
            For edge-tts:
                - default_voice: Default voice (e.g., "zh-CN-XiaoxiaoNeural")
            For openai:
                - api_key: OpenAI API key
                - base_url: OpenAI API base URL
                - model: TTS model (default: "tts-1")
                - default_voice: Default voice (default: "alloy")

    Returns:
        TTSService: A TTS service instance

    Raises:
        ValueError: If provider is not supported

    Validates: Requirements 4.1
    """
    if provider == "edge-tts":
        return EdgeTTSService(**kwargs)
    elif provider == "openai":
        return OpenAITTSService(**kwargs)
    else:
        raise ValueError(f"Unsupported TTS provider: {provider}. Supported: edge-tts, openai")
