"""Voice Services Module.

This module provides voice-related services for the Voice Agent:
- ASR (Automatic Speech Recognition) Service
- TTS (Text-to-Speech) Service
- VAD (Voice Activity Detection) Service
- Session Manager (Voice Session Management)
"""

from src.services.voice.asr_service import (
    ASRError,
    ASRService,
    OpenAIASRService,
    TranscriptionResult,
    create_asr_service,
)
from src.services.voice.session_manager import (
    SessionState,
    VoiceSession,
    VoiceSessionManager,
    voice_session_manager,
)
from src.services.voice.tts_service import (
    EdgeTTSService,
    OpenAITTSService,
    TTSError,
    TTSService,
    create_tts_service,
)
from src.services.voice.vad_service import (
    SileroVADService,
    VADError,
    VADService,
    create_vad_service,
)
from src.services.voice.audio_handler import (
    AudioChunk,
    AudioStreamHandler,
)
from src.services.voice.interrupt_handler import (
    InterruptConfig,
    InterruptHandler,
)
from src.services.voice.tool_feedback import (
    FeedbackVerbosity,
    ToolFeedbackGenerator,
)
from src.services.voice.error_handler import (
    RetryConfig,
    log_error,
    retry_with_backoff,
)

__all__ = [
    # ASR
    "ASRService",
    "ASRError",
    "OpenAIASRService",
    "TranscriptionResult",
    "create_asr_service",
    # TTS
    "TTSService",
    "TTSError",
    "EdgeTTSService",
    "OpenAITTSService",
    "create_tts_service",
    # VAD
    "VADService",
    "VADError",
    "SileroVADService",
    "create_vad_service",
    # Session Manager
    "SessionState",
    "VoiceSession",
    "VoiceSessionManager",
    "voice_session_manager",
    # Audio Handler
    "AudioChunk",
    "AudioStreamHandler",
    # Interrupt Handler
    "InterruptConfig",
    "InterruptHandler",
    # Tool Feedback
    "FeedbackVerbosity",
    "ToolFeedbackGenerator",
    # Error Handler
    "RetryConfig",
    "log_error",
    "retry_with_backoff",
]
