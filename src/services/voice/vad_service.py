"""VAD (Voice Activity Detection) Service.

This module defines the VAD service interface and Silero VAD implementation.
Uses Silero VAD model for accurate and lightweight voice activity detection.

Validates: Requirements 3.6
"""

import threading
from typing import Protocol, runtime_checkable

import numpy as np

from src.utils import logger


@runtime_checkable
class VADService(Protocol):
    """VAD Service Protocol.

    Defines the interface for voice activity detection.
    Used to detect speech boundaries in audio streams.

    Validates: Requirements 3.6
    """

    def detect_speech(self, audio_chunk: bytes) -> bool:
        """Detect if audio chunk contains speech.

        Args:
            audio_chunk: Audio data chunk (PCM format, 16kHz, 16bit, Mono)

        Returns:
            bool: True if speech is detected, False otherwise
        """
        ...

    def detect_speech_end(
        self,
        audio_chunks: list[bytes],
        silence_duration: float = 0.8,
    ) -> bool:
        """Detect if speech has ended based on silence duration.

        Analyzes recent audio chunks to determine if the speaker
        has stopped talking (silence detected for specified duration).

        Args:
            audio_chunks: List of recent audio chunks to analyze
            silence_duration: Required silence duration in seconds to
                            consider speech ended (default 0.8s)

        Returns:
            bool: True if speech has ended (silence detected), False otherwise
        """
        ...


class VADError(Exception):
    """Exception raised when VAD processing fails."""

    def __init__(self, message: str, cause: Exception | None = None):
        super().__init__(message)
        self.cause = cause


class SileroVADService:
    """Silero VAD Service Implementation.

    Uses Silero VAD model for voice activity detection.
    Silero VAD is a lightweight, accurate, and fast VAD model
    that works well for real-time speech detection.

    Audio requirements:
    - Sample rate: 16000 Hz (or 8000 Hz)
    - Format: float32 normalized to [-1, 1]
    - Mono channel

    Validates: Requirements 3.6
    """

    # Supported sample rates
    SUPPORTED_SAMPLE_RATES = {8000, 16000}

    # Default sample rate
    DEFAULT_SAMPLE_RATE = 16000

    # Minimum audio chunk size for VAD (in samples)
    # Silero VAD works best with chunks of 256, 512, or 768 samples for 16kHz
    MIN_CHUNK_SAMPLES = 512

    # Model cache for singleton pattern
    _model_cache: dict = {}
    _model_lock = threading.Lock()

    def __init__(
        self,
        threshold: float = 0.5,
        sample_rate: int = 16000,
    ):
        """Initialize Silero VAD Service.

        Args:
            threshold: Speech detection threshold (0.0 - 1.0).
                      Higher values require more confidence for speech detection.
                      Default: 0.5
            sample_rate: Audio sample rate in Hz. Must be 8000 or 16000.
                        Default: 16000

        Raises:
            VADError: If model loading fails or invalid parameters
        """
        if sample_rate not in self.SUPPORTED_SAMPLE_RATES:
            raise VADError(
                f"Unsupported sample rate: {sample_rate}. "
                f"Supported: {self.SUPPORTED_SAMPLE_RATES}"
            )

        if not 0.0 <= threshold <= 1.0:
            raise VADError(f"Threshold must be between 0.0 and 1.0, got: {threshold}")

        self.threshold = threshold
        self.sample_rate = sample_rate

        # Load model (cached)
        self.model, self.utils = self._load_model()

        logger.debug(
            f"Silero VAD Service initialized with threshold={threshold}, "
            f"sample_rate={sample_rate}"
        )

    @classmethod
    def _load_model(cls):
        """Load Silero VAD model with caching.

        Uses a singleton pattern to avoid reloading the model
        on each instantiation.

        Returns:
            tuple: (model, utils) from torch.hub.load

        Raises:
            VADError: If model loading fails
        """
        cache_key = "silero_vad"

        with cls._model_lock:
            if cache_key in cls._model_cache:
                logger.debug("Using cached Silero VAD model")
                return cls._model_cache[cache_key]

            try:
                import torch

                # Set number of threads to 1 for inference efficiency
                torch.set_num_threads(1)

                logger.info("Loading Silero VAD model...")

                model, utils = torch.hub.load(
                    repo_or_dir="snakers4/silero-vad",
                    model="silero_vad",
                    force_reload=False,
                    trust_repo=True,
                )

                # Cache the model
                cls._model_cache[cache_key] = (model, utils)

                logger.info("Silero VAD model loaded successfully")
                return model, utils

            except ImportError as e:
                raise VADError(
                    "torch is required for Silero VAD. Install with: pip install torch",
                    cause=e,
                ) from e
            except Exception as e:
                logger.error(f"Failed to load Silero VAD model: {e}")
                raise VADError(f"Failed to load Silero VAD model: {e}", cause=e) from e

    def _pcm_to_float32(self, audio_chunk: bytes) -> np.ndarray:
        """Convert PCM audio bytes to float32 numpy array.

        Converts 16-bit PCM audio to float32 normalized to [-1, 1].

        Args:
            audio_chunk: Raw PCM audio data (16-bit, mono)

        Returns:
            np.ndarray: Float32 audio array normalized to [-1, 1]
        """
        # Convert bytes to int16 array
        audio_int16 = np.frombuffer(audio_chunk, dtype=np.int16)

        # Normalize to float32 [-1, 1]
        audio_float32 = audio_int16.astype(np.float32) / 32768.0

        return audio_float32

    def _get_speech_probability(self, audio_array: np.ndarray) -> float:
        """Get speech probability for audio array.

        Args:
            audio_array: Float32 audio array normalized to [-1, 1]

        Returns:
            float: Speech probability (0.0 - 1.0)
        """
        import torch

        # Convert to torch tensor
        audio_tensor = torch.from_numpy(audio_array)

        # Get speech probability
        speech_prob = self.model(audio_tensor, self.sample_rate).item()

        return speech_prob

    def detect_speech(self, audio_chunk: bytes) -> bool:
        """Detect if audio chunk contains speech.

        Args:
            audio_chunk: Audio data chunk (PCM format, 16kHz, 16bit, Mono)

        Returns:
            bool: True if speech is detected, False otherwise

        Raises:
            VADError: If detection fails
        """
        if not audio_chunk:
            return False

        try:
            # Convert PCM to float32
            audio_array = self._pcm_to_float32(audio_chunk)

            # Check minimum chunk size
            if len(audio_array) < self.MIN_CHUNK_SAMPLES:
                logger.debug(
                    f"Audio chunk too small ({len(audio_array)} samples), "
                    f"minimum is {self.MIN_CHUNK_SAMPLES}"
                )
                return False

            # Get speech probability
            speech_prob = self._get_speech_probability(audio_array)

            # Compare with threshold
            is_speech = speech_prob >= self.threshold

            logger.debug(
                f"VAD: speech_prob={speech_prob:.3f}, "
                f"threshold={self.threshold}, is_speech={is_speech}"
            )

            return is_speech

        except Exception as e:
            logger.error(f"VAD speech detection failed: {e}")
            raise VADError(f"Speech detection failed: {e}", cause=e) from e

    def detect_speech_end(
        self,
        audio_chunks: list[bytes],
        silence_duration: float = 0.8,
    ) -> bool:
        """Detect if speech has ended based on silence duration.

        Analyzes recent audio chunks to determine if the speaker
        has stopped talking (silence detected for specified duration).

        Args:
            audio_chunks: List of recent audio chunks to analyze
            silence_duration: Required silence duration in seconds to
                            consider speech ended (default 0.8s)

        Returns:
            bool: True if speech has ended (silence detected), False otherwise

        Raises:
            VADError: If detection fails
        """
        if not audio_chunks:
            return False

        try:
            # Calculate required samples for silence duration
            # At 16kHz, 16-bit mono: 1 second = 32000 bytes = 16000 samples
            bytes_per_sample = 2  # 16-bit = 2 bytes
            samples_per_second = self.sample_rate
            required_silence_samples = int(silence_duration * samples_per_second)

            # Concatenate audio chunks
            all_audio = b"".join(audio_chunks)

            # Convert to float32
            audio_array = self._pcm_to_float32(all_audio)

            # Calculate how many samples we have
            total_samples = len(audio_array)

            if total_samples < required_silence_samples:
                # Not enough audio to determine silence
                logger.debug(
                    f"Not enough audio for silence detection: "
                    f"{total_samples} < {required_silence_samples} samples"
                )
                return False

            # Analyze the last `silence_duration` seconds of audio
            # Split into chunks and check each for speech
            chunk_size = self.MIN_CHUNK_SAMPLES
            start_sample = max(0, total_samples - required_silence_samples)
            end_sample = total_samples

            # Get the audio segment to analyze
            segment = audio_array[start_sample:end_sample]

            # Process in chunks and check for any speech
            speech_detected_in_segment = False
            num_chunks = len(segment) // chunk_size

            for i in range(num_chunks):
                chunk_start = i * chunk_size
                chunk_end = chunk_start + chunk_size
                chunk = segment[chunk_start:chunk_end]

                speech_prob = self._get_speech_probability(chunk)

                if speech_prob >= self.threshold:
                    speech_detected_in_segment = True
                    break

            # Speech has ended if no speech detected in the silence duration
            speech_ended = not speech_detected_in_segment

            logger.debug(
                f"VAD speech end detection: analyzed {num_chunks} chunks, "
                f"speech_detected={speech_detected_in_segment}, "
                f"speech_ended={speech_ended}"
            )

            return speech_ended

        except Exception as e:
            logger.error(f"VAD speech end detection failed: {e}")
            raise VADError(f"Speech end detection failed: {e}", cause=e) from e

    def reset(self):
        """Reset VAD model state.

        Call this when starting a new audio stream to clear
        any internal state from previous processing.
        """
        # Silero VAD model has internal state that should be reset
        # between different audio streams
        if hasattr(self.model, "reset_states"):
            self.model.reset_states()
            logger.debug("VAD model state reset")

    def get_speech_probability(self, audio_chunk: bytes) -> float:
        """Get speech probability for audio chunk.

        Useful for getting the raw probability value instead of
        just a boolean result.

        Args:
            audio_chunk: Audio data chunk (PCM format, 16kHz, 16bit, Mono)

        Returns:
            float: Speech probability (0.0 - 1.0)

        Raises:
            VADError: If detection fails
        """
        if not audio_chunk:
            return 0.0

        try:
            audio_array = self._pcm_to_float32(audio_chunk)

            if len(audio_array) < self.MIN_CHUNK_SAMPLES:
                return 0.0

            return self._get_speech_probability(audio_array)

        except Exception as e:
            logger.error(f"VAD get speech probability failed: {e}")
            raise VADError(f"Get speech probability failed: {e}", cause=e) from e


def create_vad_service(
    provider: str = "silero",
    threshold: float = 0.5,
    sample_rate: int = 16000,
    **kwargs,
) -> VADService:
    """Factory function to create VAD service instances.

    Args:
        provider: VAD provider name. Currently only "silero" is supported.
        threshold: Speech detection threshold (0.0 - 1.0). Default: 0.5
        sample_rate: Audio sample rate in Hz. Default: 16000
        **kwargs: Additional provider-specific configuration options

    Returns:
        VADService: A VAD service instance

    Raises:
        ValueError: If provider is not supported

    Validates: Requirements 3.6
    """
    if provider == "silero":
        return SileroVADService(
            threshold=threshold,
            sample_rate=sample_rate,
            **kwargs,
        )
    else:
        raise ValueError(
            f"Unsupported VAD provider: {provider}. Supported: silero"
        )
