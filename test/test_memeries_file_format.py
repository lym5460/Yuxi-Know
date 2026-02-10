"""Property-based tests for Memeries file format validation.

**Validates: Requirements 1.3, 1.4**

Tests the file format validation and media type detection functions
using property-based testing with Hypothesis.
"""

import os
import sys

# Add project root to path
sys.path.insert(0, os.getcwd())

import pytest
from hypothesis import given, settings, strategies as st

from src.services.memeries_service import (
    SUPPORTED_AUDIO_FORMATS,
    SUPPORTED_MEDIA_FORMATS,
    SUPPORTED_VIDEO_FORMATS,
    _get_file_extension,
    _get_media_type,
    _validate_file_format,
)


# =============================================================================
# === Strategies ===
# =============================================================================

# 生成有效的视频文件名
video_filenames = st.builds(
    lambda name, ext: f"{name}.{ext}",
    name=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=("L", "N"), whitelist_characters="_-")),
    ext=st.sampled_from(list(SUPPORTED_VIDEO_FORMATS)),
)

# 生成有效的音频文件名
audio_filenames = st.builds(
    lambda name, ext: f"{name}.{ext}",
    name=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=("L", "N"), whitelist_characters="_-")),
    ext=st.sampled_from(list(SUPPORTED_AUDIO_FORMATS)),
)

# 生成有效的媒体文件名（视频或音频）
valid_media_filenames = st.one_of(video_filenames, audio_filenames)

# 生成无效的文件扩展名
invalid_extensions = st.text(min_size=1, max_size=10, alphabet="abcdefghijklmnopqrstuvwxyz0123456789").filter(
    lambda x: x.lower() not in SUPPORTED_MEDIA_FORMATS
)

# 生成无效的文件名
invalid_filenames = st.one_of(
    # 带无效扩展名的文件
    st.builds(
        lambda name, ext: f"{name}.{ext}",
        name=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=("L", "N"), whitelist_characters="_-")),
        ext=invalid_extensions,
    ),
    # 无扩展名的文件
    st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=("L", "N"), whitelist_characters="_-")).filter(
        lambda x: "." not in x
    ),
)


# =============================================================================
# === Property Tests ===
# =============================================================================


class TestFileFormatValidation:
    """Property tests for _validate_file_format function."""

    @given(filename=valid_media_filenames)
    @settings(max_examples=100)
    def test_valid_formats_return_true(self, filename: str):
        """
        Property: For any filename with a supported media extension,
        _validate_file_format returns True.

        **Validates: Requirements 1.3**
        """
        assert _validate_file_format(filename) is True

    @given(filename=invalid_filenames)
    @settings(max_examples=100)
    def test_invalid_formats_return_false(self, filename: str):
        """
        Property: For any filename without a supported media extension,
        _validate_file_format returns False.

        **Validates: Requirements 1.4**
        """
        assert _validate_file_format(filename) is False

    def test_all_video_formats_supported(self):
        """Verify all documented video formats are supported."""
        expected_formats = {"mp4", "avi", "mov", "mkv", "webm"}
        for fmt in expected_formats:
            assert _validate_file_format(f"test.{fmt}") is True
            assert _validate_file_format(f"test.{fmt.upper()}") is True

    def test_all_audio_formats_supported(self):
        """Verify all documented audio formats are supported."""
        expected_formats = {"mp3", "wav", "m4a", "flac", "aac", "ogg"}
        for fmt in expected_formats:
            assert _validate_file_format(f"test.{fmt}") is True
            assert _validate_file_format(f"test.{fmt.upper()}") is True


class TestMediaTypeDetection:
    """Property tests for _get_media_type function."""

    @given(filename=video_filenames)
    @settings(max_examples=100)
    def test_video_files_return_video(self, filename: str):
        """
        Property: For any filename with a video extension,
        _get_media_type returns "video".

        **Validates: Requirements 1.3**
        """
        assert _get_media_type(filename) == "video"

    @given(filename=audio_filenames)
    @settings(max_examples=100)
    def test_audio_files_return_audio(self, filename: str):
        """
        Property: For any filename with an audio extension,
        _get_media_type returns "audio".

        **Validates: Requirements 1.3**
        """
        assert _get_media_type(filename) == "audio"

    @given(filename=invalid_filenames)
    @settings(max_examples=100)
    def test_invalid_files_return_unknown(self, filename: str):
        """
        Property: For any filename without a supported media extension,
        _get_media_type returns "unknown".

        **Validates: Requirements 1.4**
        """
        assert _get_media_type(filename) == "unknown"

    def test_media_type_consistency(self):
        """Verify media type detection is consistent with format validation."""
        # Video formats
        for fmt in SUPPORTED_VIDEO_FORMATS:
            filename = f"test.{fmt}"
            assert _validate_file_format(filename) is True
            assert _get_media_type(filename) == "video"

        # Audio formats
        for fmt in SUPPORTED_AUDIO_FORMATS:
            filename = f"test.{fmt}"
            assert _validate_file_format(filename) is True
            assert _get_media_type(filename) == "audio"


class TestFileExtensionExtraction:
    """Property tests for _get_file_extension function."""

    @given(name=st.text(min_size=1, max_size=50, alphabet="abcdefghijklmnopqrstuvwxyz"), ext=st.text(min_size=1, max_size=10, alphabet="abcdefghijklmnopqrstuvwxyz"))
    @settings(max_examples=100)
    def test_extension_extraction(self, name: str, ext: str):
        """
        Property: For any filename with format "name.ext",
        _get_file_extension returns the lowercase extension.
        """
        filename = f"{name}.{ext}"
        assert _get_file_extension(filename) == ext.lower()

    def test_no_extension(self):
        """Files without extension return empty string."""
        assert _get_file_extension("filename") == ""
        assert _get_file_extension("no_dot_here") == ""

    def test_multiple_dots(self):
        """Files with multiple dots return the last extension."""
        assert _get_file_extension("file.name.mp4") == "mp4"
        assert _get_file_extension("archive.tar.gz") == "gz"

    def test_case_insensitive(self):
        """Extension extraction is case-insensitive."""
        assert _get_file_extension("video.MP4") == "mp4"
        assert _get_file_extension("audio.WAV") == "wav"
