"""ASR (Automatic Speech Recognition) Service.

This module defines the ASR service interface and implementations.

Validates: Requirements 3.1, 3.2, 3.3, 3.4
"""

import io
import os
import wave
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from openai import AsyncOpenAI

from src.utils import logger


@dataclass
class TranscriptionResult:
    """Result of speech transcription.

    Attributes:
        text: The transcribed text
        is_final: Whether this is the final transcription result
        confidence: Confidence score of the transcription (0.0 - 1.0)
        language: Detected language code (e.g., "zh", "en")
    """

    text: str
    is_final: bool = False
    confidence: float = 1.0
    language: str = "auto"
    metadata: dict = field(default_factory=dict)


@runtime_checkable
class ASRService(Protocol):
    """ASR Service Protocol.

    Defines the interface for speech recognition services.
    Supports multiple providers (e.g., OpenAI Whisper, Azure Speech, local Whisper).

    Validates: Requirements 3.1
    """

    async def transcribe_stream(
        self,
        audio_chunks: AsyncIterator[bytes],
        language: str = "auto",
    ) -> AsyncIterator[TranscriptionResult]:
        """Transcribe audio stream to text.

        Performs streaming speech recognition, yielding partial results
        as they become available.

        Args:
            audio_chunks: Async iterator of audio data chunks (PCM/WAV/WebM format)
            language: Target language code or "auto" for automatic detection.
                     Supports "zh" (Chinese), "en" (English), and "auto".

        Yields:
            TranscriptionResult: Partial or final transcription results.
                - Partial results have is_final=False
                - Final result has is_final=True

        Raises:
            ASRError: If transcription fails

        Validates: Requirements 3.2, 3.3, 3.4
        """
        ...

    async def transcribe(
        self,
        audio_data: bytes,
        language: str = "auto",
    ) -> TranscriptionResult:
        """Transcribe audio data to text (non-streaming).

        Args:
            audio_data: Audio data (PCM/WAV/WebM format)
            language: Target language code or "auto" for automatic detection.

        Returns:
            TranscriptionResult: Final transcription result.

        Raises:
            ASRError: If transcription fails
        """
        ...


class ASRError(Exception):
    """Exception raised when ASR processing fails.

    Validates: Requirements 3.5
    """

    def __init__(self, message: str, provider: str | None = None, cause: Exception | None = None):
        super().__init__(message)
        self.provider = provider
        self.cause = cause


class OpenAIASRService:
    """OpenAI Whisper ASR Service Implementation.

    Uses OpenAI's Whisper API for speech recognition.
    Since Whisper API doesn't support true streaming, this implementation
    uses a buffered approach:
    1. Accumulates audio chunks until enough data is available
    2. Sends to Whisper API for transcription
    3. Yields results as they become available

    Validates: Requirements 3.1, 3.2, 3.3, 3.4
    """

    # Minimum audio buffer size before sending to API (in bytes)
    # At 16kHz, 16-bit mono, 1 second = 32000 bytes
    MIN_BUFFER_SIZE = 32000  # ~1 second of audio

    # Maximum audio buffer size (in bytes)
    # At 16kHz, 16-bit mono, 30 seconds = 960000 bytes
    MAX_BUFFER_SIZE = 960000  # ~30 seconds of audio

    # Supported languages
    SUPPORTED_LANGUAGES = {"zh", "en", "auto"}

    # Language code mapping for OpenAI API
    LANGUAGE_MAP = {
        "zh": "zh",
        "en": "en",
        "auto": None,  # Let Whisper auto-detect
    }

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str = "whisper-1",
        sample_rate: int = 16000,
        channels: int = 1,
        sample_width: int = 2,  # 16-bit = 2 bytes
    ):
        """Initialize OpenAI ASR Service.

        Args:
            api_key: OpenAI API key. If None, uses OPENAI_API_KEY env var.
            base_url: OpenAI API base URL. If None, uses OPENAI_API_BASE env var.
            model: Whisper model to use (default: "whisper-1")
            sample_rate: Audio sample rate in Hz (default: 16000)
            channels: Number of audio channels (default: 1, mono)
            sample_width: Sample width in bytes (default: 2, 16-bit)
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.base_url = base_url or os.getenv("OPENAI_API_BASE")
        self.model = model
        self.sample_rate = sample_rate
        self.channels = channels
        self.sample_width = sample_width

        if not self.api_key:
            raise ASRError("OpenAI API key not provided", provider="openai")

        self.client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)
        logger.debug(f"OpenAI ASR Service initialized with model: {model}")

    def _pcm_to_wav(self, pcm_data: bytes) -> bytes:
        """Convert PCM audio data to WAV format.

        Args:
            pcm_data: Raw PCM audio data

        Returns:
            bytes: WAV formatted audio data
        """
        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, "wb") as wav_file:
            wav_file.setnchannels(self.channels)
            wav_file.setsampwidth(self.sample_width)
            wav_file.setframerate(self.sample_rate)
            wav_file.writeframes(pcm_data)
        wav_buffer.seek(0)
        return wav_buffer.read()

    def _estimate_confidence(self, text: str, duration_seconds: float) -> float:
        """Estimate confidence score based on transcription characteristics.

        Since OpenAI Whisper API doesn't provide confidence scores directly,
        we estimate based on:
        - Text length relative to audio duration
        - Presence of common transcription artifacts

        Args:
            text: Transcribed text
            duration_seconds: Audio duration in seconds

        Returns:
            float: Estimated confidence score (0.0 - 1.0)
        """
        if not text or not text.strip():
            return 0.0

        # Base confidence
        confidence = 0.85

        # Adjust based on text density (characters per second)
        # Normal speech: ~3-5 characters per second for Chinese, ~10-15 for English
        chars_per_second = len(text) / max(duration_seconds, 0.1)

        if chars_per_second < 1:
            # Very sparse transcription, might be noise
            confidence -= 0.2
        elif chars_per_second > 20:
            # Very dense, might have issues
            confidence -= 0.1

        # Check for common artifacts
        artifacts = ["[音乐]", "[掌声]", "[笑声]", "[MUSIC]", "[APPLAUSE]", "[LAUGHTER]"]
        for artifact in artifacts:
            if artifact in text:
                confidence -= 0.05

        return max(0.0, min(1.0, confidence))

    def _detect_language(self, text: str) -> str:
        """Detect language from transcribed text.

        Simple heuristic based on character ranges.

        Args:
            text: Transcribed text

        Returns:
            str: Detected language code ("zh", "en", or "auto")
        """
        if not text:
            return "auto"

        chinese_chars = sum(1 for c in text if "\u4e00" <= c <= "\u9fff")
        total_chars = len(text.replace(" ", ""))

        if total_chars == 0:
            return "auto"

        chinese_ratio = chinese_chars / total_chars

        if chinese_ratio > 0.3:
            return "zh"
        elif chinese_ratio < 0.1:
            return "en"
        else:
            return "auto"

    async def transcribe(
        self,
        audio_data: bytes,
        language: str = "auto",
    ) -> TranscriptionResult:
        """Transcribe audio data to text (non-streaming).

        Args:
            audio_data: Audio data (PCM format expected)
            language: Target language code or "auto" for automatic detection.

        Returns:
            TranscriptionResult: Final transcription result.

        Raises:
            ASRError: If transcription fails

        Validates: Requirements 3.3, 3.4
        """
        if not audio_data:
            return TranscriptionResult(text="", is_final=True, confidence=0.0, language=language)

        try:
            # Convert PCM to WAV format for API
            wav_data = self._pcm_to_wav(audio_data)

            # Calculate audio duration
            duration_seconds = len(audio_data) / (self.sample_rate * self.channels * self.sample_width)

            # Prepare language parameter
            lang_param = self.LANGUAGE_MAP.get(language)

            # Create file-like object for API
            audio_file = io.BytesIO(wav_data)
            audio_file.name = "audio.wav"

            # Call Whisper API
            logger.debug(f"Calling Whisper API with {len(audio_data)} bytes of audio")

            transcription = await self.client.audio.transcriptions.create(
                model=self.model,
                file=audio_file,
                language=lang_param,
                response_format="verbose_json",
            )

            text = transcription.text.strip() if transcription.text else ""

            # Detect language if auto
            detected_language = language
            if language == "auto" and hasattr(transcription, "language"):
                detected_language = transcription.language or self._detect_language(text)
            elif language == "auto":
                detected_language = self._detect_language(text)

            # Estimate confidence
            confidence = self._estimate_confidence(text, duration_seconds)

            # Build metadata
            metadata = {
                "duration": duration_seconds,
                "model": self.model,
            }
            if hasattr(transcription, "segments") and transcription.segments:
                metadata["segments"] = len(transcription.segments)

            logger.debug(f"Transcription result: '{text[:50]}...' (confidence: {confidence:.2f})")

            return TranscriptionResult(
                text=text,
                is_final=True,
                confidence=confidence,
                language=detected_language,
                metadata=metadata,
            )

        except Exception as e:
            logger.error(f"OpenAI ASR transcription failed: {e}")
            raise ASRError(f"Transcription failed: {e}", provider="openai", cause=e) from e

    async def transcribe_stream(
        self,
        audio_chunks: AsyncIterator[bytes],
        language: str = "auto",
    ) -> AsyncIterator[TranscriptionResult]:
        """Transcribe audio stream to text.

        Since OpenAI Whisper API doesn't support true streaming,
        this implementation uses a buffered approach:
        1. Accumulates audio chunks until MIN_BUFFER_SIZE is reached
        2. Sends accumulated audio to Whisper API
        3. Yields partial results as they become available
        4. Continues until all audio is processed

        Args:
            audio_chunks: Async iterator of audio data chunks (PCM format)
            language: Target language code or "auto" for automatic detection.

        Yields:
            TranscriptionResult: Partial or final transcription results.

        Raises:
            ASRError: If transcription fails

        Validates: Requirements 3.2, 3.3, 3.4
        """
        audio_buffer = bytearray()
        accumulated_text = ""
        chunk_count = 0

        try:
            async for chunk in audio_chunks:
                audio_buffer.extend(chunk)
                chunk_count += 1

                # Process when buffer reaches minimum size
                if len(audio_buffer) >= self.MIN_BUFFER_SIZE:
                    # Transcribe current buffer
                    result = await self.transcribe(bytes(audio_buffer), language)

                    if result.text:
                        # Yield partial result
                        new_text = result.text
                        if new_text != accumulated_text:
                            accumulated_text = new_text
                            yield TranscriptionResult(
                                text=new_text,
                                is_final=False,
                                confidence=result.confidence,
                                language=result.language,
                                metadata={**result.metadata, "chunk_count": chunk_count},
                            )

                    # Check if buffer is getting too large
                    if len(audio_buffer) >= self.MAX_BUFFER_SIZE:
                        # Clear buffer but keep last portion for context
                        keep_size = self.MIN_BUFFER_SIZE // 2
                        audio_buffer = audio_buffer[-keep_size:]
                        logger.debug(f"Buffer overflow, keeping last {keep_size} bytes")

            # Process remaining audio in buffer
            if len(audio_buffer) > 0:
                result = await self.transcribe(bytes(audio_buffer), language)

                # Yield final result
                yield TranscriptionResult(
                    text=result.text,
                    is_final=True,
                    confidence=result.confidence,
                    language=result.language,
                    metadata={**result.metadata, "chunk_count": chunk_count, "total_bytes": len(audio_buffer)},
                )
            else:
                # No audio data, yield empty final result
                yield TranscriptionResult(
                    text="",
                    is_final=True,
                    confidence=0.0,
                    language=language,
                )

        except ASRError:
            raise
        except Exception as e:
            logger.error(f"OpenAI ASR stream transcription failed: {e}")
            raise ASRError(f"Stream transcription failed: {e}", provider="openai", cause=e) from e


def create_asr_service(provider: str = "openai", **kwargs) -> ASRService:
    """Factory function to create ASR service instances.

    Args:
        provider: ASR provider name. Supported: "openai", "local-whisper"
        **kwargs: Provider-specific configuration options

    Returns:
        ASRService: An ASR service instance

    Raises:
        ValueError: If provider is not supported

    Validates: Requirements 3.1
    """
    if provider == "openai":
        return OpenAIASRService(**kwargs)
    elif provider == "local-whisper":
        return LocalWhisperASRService(**kwargs)
    else:
        raise ValueError(f"Unsupported ASR provider: {provider}. Supported: openai, local-whisper")


class LocalWhisperASRService:
    """Local Whisper ASR Service Implementation.

    Uses a local faster-whisper-server (Docker) for speech recognition.
    The server provides an OpenAI-compatible API at /v1/audio/transcriptions.

    Validates: Requirements 3.1, 3.2, 3.3, 3.4
    """

    # Minimum audio buffer size before sending to API (in bytes)
    MIN_BUFFER_SIZE = 32000  # ~1 second of audio at 16kHz

    # Maximum audio buffer size (in bytes)
    MAX_BUFFER_SIZE = 960000  # ~30 seconds of audio

    def __init__(
        self,
        api_url: str | None = None,
        model: str | None = None,
        sample_rate: int = 16000,
        channels: int = 1,
        sample_width: int = 2,
    ):
        """Initialize Local Whisper ASR Service.

        Args:
            api_url: Whisper server URL. If None, uses WHISPER_API_URL env var.
            model: Whisper model name (for logging only, model is set on server).
            sample_rate: Audio sample rate in Hz (default: 16000)
            channels: Number of audio channels (default: 1, mono)
            sample_width: Sample width in bytes (default: 2, 16-bit)
        """
        self.api_url = api_url or os.getenv("WHISPER_API_URL", "http://whisper:8000")
        self.model = model or os.getenv("WHISPER_MODEL", "Systran/faster-whisper-small")
        self.sample_rate = sample_rate
        self.channels = channels
        self.sample_width = sample_width

        # Use httpx for async HTTP requests
        import httpx

        self.http_client = httpx.AsyncClient(timeout=120.0)  # 增加超时时间到 120 秒
        logger.info(f"Local Whisper ASR Service initialized: {self.api_url}")

    def _pcm_to_wav(self, pcm_data: bytes) -> bytes:
        """Convert PCM audio data to WAV format."""
        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, "wb") as wav_file:
            wav_file.setnchannels(self.channels)
            wav_file.setsampwidth(self.sample_width)
            wav_file.setframerate(self.sample_rate)
            wav_file.writeframes(pcm_data)
        wav_buffer.seek(0)
        return wav_buffer.read()

    def _detect_language(self, text: str) -> str:
        """Detect language from transcribed text."""
        if not text:
            return "auto"

        chinese_chars = sum(1 for c in text if "\u4e00" <= c <= "\u9fff")
        total_chars = len(text.replace(" ", ""))

        if total_chars == 0:
            return "auto"

        chinese_ratio = chinese_chars / total_chars

        if chinese_ratio > 0.3:
            return "zh"
        elif chinese_ratio < 0.1:
            return "en"
        else:
            return "auto"

    async def transcribe(
        self,
        audio_data: bytes,
        language: str = "auto",
    ) -> TranscriptionResult:
        """Transcribe audio data to text (non-streaming).

        Args:
            audio_data: Audio data (PCM format expected)
            language: Target language code or "auto" for automatic detection.

        Returns:
            TranscriptionResult: Final transcription result.

        Raises:
            ASRError: If transcription fails
        """
        if not audio_data:
            return TranscriptionResult(text="", is_final=True, confidence=0.0, language=language)

        try:
            # Convert PCM to WAV format
            wav_data = self._pcm_to_wav(audio_data)

            # Calculate audio duration
            duration_seconds = len(audio_data) / (self.sample_rate * self.channels * self.sample_width)

            # Prepare request
            url = f"{self.api_url}/v1/audio/transcriptions"

            # 使用 multipart/form-data 格式
            files = {"file": ("audio.wav", wav_data, "audio/wav")}
            data = {"response_format": "json"}

            # Add language if specified (不是 auto)
            if language and language != "auto":
                data["language"] = language

            logger.debug(f"Calling local Whisper API with {len(audio_data)} bytes of audio")

            # Send request
            response = await self.http_client.post(url, files=files, data=data)

            # 检查响应状态
            if response.status_code != 200:
                error_text = response.text
                logger.error(f"Whisper API error: {response.status_code} - {error_text}")
                raise ASRError(f"Whisper API error: {response.status_code}", provider="local-whisper")

            result = response.json()
            logger.debug(f"Whisper API response: {result}")

            # 响应可能是字符串或对象
            if isinstance(result, str):
                text = result.strip()
            else:
                text = result.get("text", "").strip()

            # Detect language if auto
            detected_language = language
            if language == "auto":
                detected_language = self._detect_language(text)

            # Estimate confidence (local whisper doesn't provide confidence)
            confidence = 0.9 if text else 0.0

            logger.info(f"Local Whisper result: '{text}' (duration: {duration_seconds:.2f}s)")

            return TranscriptionResult(
                text=text,
                is_final=True,
                confidence=confidence,
                language=detected_language,
                metadata={"duration": duration_seconds, "model": self.model},
            )

        except ASRError:
            raise
        except Exception as e:
            logger.error(f"Local Whisper ASR transcription failed: {e}", exc_info=True)
            raise ASRError(f"Transcription failed: {e}", provider="local-whisper", cause=e) from e

    async def transcribe_stream(
        self,
        audio_chunks: AsyncIterator[bytes],
        language: str = "auto",
    ) -> AsyncIterator[TranscriptionResult]:
        """Transcribe audio stream to text.

        Uses buffered approach similar to OpenAI implementation.

        Args:
            audio_chunks: Async iterator of audio data chunks (PCM format)
            language: Target language code or "auto" for automatic detection.

        Yields:
            TranscriptionResult: Partial or final transcription results.

        Raises:
            ASRError: If transcription fails
        """
        audio_buffer = bytearray()
        accumulated_text = ""
        chunk_count = 0

        try:
            async for chunk in audio_chunks:
                audio_buffer.extend(chunk)
                chunk_count += 1

                # Process when buffer reaches minimum size
                if len(audio_buffer) >= self.MIN_BUFFER_SIZE:
                    result = await self.transcribe(bytes(audio_buffer), language)

                    if result.text:
                        new_text = result.text
                        if new_text != accumulated_text:
                            accumulated_text = new_text
                            yield TranscriptionResult(
                                text=new_text,
                                is_final=False,
                                confidence=result.confidence,
                                language=result.language,
                                metadata={**result.metadata, "chunk_count": chunk_count},
                            )

                    # Check buffer overflow
                    if len(audio_buffer) >= self.MAX_BUFFER_SIZE:
                        keep_size = self.MIN_BUFFER_SIZE // 2
                        audio_buffer = audio_buffer[-keep_size:]
                        logger.debug(f"Buffer overflow, keeping last {keep_size} bytes")

            # Process remaining audio
            if len(audio_buffer) > 0:
                result = await self.transcribe(bytes(audio_buffer), language)
                yield TranscriptionResult(
                    text=result.text,
                    is_final=True,
                    confidence=result.confidence,
                    language=result.language,
                    metadata={**result.metadata, "chunk_count": chunk_count, "total_bytes": len(audio_buffer)},
                )
            else:
                yield TranscriptionResult(text="", is_final=True, confidence=0.0, language=language)

        except ASRError:
            raise
        except Exception as e:
            logger.error(f"Local Whisper ASR stream transcription failed: {e}")
            raise ASRError(f"Stream transcription failed: {e}", provider="local-whisper", cause=e) from e

    async def close(self):
        """Close the HTTP client."""
        await self.http_client.aclose()
