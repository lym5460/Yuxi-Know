"""Property-based tests for MediaPlayer type selection (Property 7).

**Validates: Requirements 6.1**

Tests that the MediaPlayer component renders the correct HTML element
based on media_type: "video" renders <video>, "audio" renders <audio>.

The Vue component template is parsed and its conditional rendering logic
is simulated to verify the property across random inputs.
"""

import os
import re
import sys

sys.path.insert(0, os.getcwd())

import pytest
from hypothesis import given, settings, strategies as st

# =============================================================================
# === Component Template Parser ===
# =============================================================================

COMPONENT_PATH = os.path.join(os.path.dirname(__file__), "fixtures", "MediaPlayer.vue")


def read_component_template() -> str:
    """Read the <template> section from MediaPlayer.vue."""
    with open(COMPONENT_PATH, encoding="utf-8") as f:
        content = f.read()
    match = re.search(r"<template>(.*?)</template>", content, re.DOTALL)
    assert match, "MediaPlayer.vue must have a <template> section"
    return match.group(1)


def extract_conditional_elements(template: str) -> list[dict]:
    """
    Extract elements with v-if/v-else-if/v-else directives.
    Returns list of dicts with keys: tag, condition, directive.
    """
    pattern = r"<(\w+)\s[^>]*?(?:v-(if|else-if|else))(?:=\"([^\"]*)\")?\s*[^>]*?>"
    elements = []
    for match in re.finditer(pattern, template):
        tag = match.group(1)
        directive = match.group(2)
        condition = match.group(3) if match.group(3) else None
        elements.append({"tag": tag, "condition": condition, "directive": directive})
    return elements


def simulate_render(media_type: str, template: str) -> str | None:
    """
    Simulate Vue conditional rendering for a given media_type.
    Evaluates v-if/v-else-if/v-else chains on video/audio elements.
    Returns the HTML tag that would be rendered.
    """
    elements = extract_conditional_elements(template)
    media_elements = [e for e in elements if e["tag"] in ("video", "audio")]

    if not media_elements:
        return None

    for elem in media_elements:
        if elem["directive"] in ("if", "else-if"):
            condition = elem["condition"]
            if condition and _evaluate_condition(condition, media_type):
                return elem["tag"]
        elif elem["directive"] == "else":
            return elem["tag"]

    return None


def _evaluate_condition(condition: str, media_type: str) -> bool:
    """Evaluate a Vue template condition like "mediaType === 'video'"."""
    condition = condition.strip()
    match = re.match(r"(?:props\.)?mediaType\s*===\s*['\"](\w+)['\"]", condition)
    if match:
        return match.group(1) == media_type
    return False


# =============================================================================
# === Strategies ===
# =============================================================================

valid_media_types = st.sampled_from(["video", "audio"])

media_urls = st.builds(
    lambda name, ext: f"http://minio:9000/kb-files/{name}.{ext}",
    name=st.text(min_size=1, max_size=20, alphabet="abcdefghijklmnopqrstuvwxyz0123456789"),
    ext=st.sampled_from(["mp4", "avi", "mov", "mp3", "wav", "m4a"]),
)

play_commands = st.fixed_dictionaries({
    "media_type": valid_media_types,
    "media_url": media_urls,
    "start_time": st.floats(min_value=0, max_value=7200, allow_nan=False, allow_infinity=False),
})


# =============================================================================
# === Property Tests ===
# =============================================================================


class TestMediaPlayerTypeSelection:
    """Property tests for MediaPlayer type selection (Property 7).

    **Validates: Requirements 6.1**
    """

    @classmethod
    def setup_class(cls):
        cls.template = read_component_template()

    @given(command=play_commands)
    @settings(max_examples=100)
    def test_media_type_determines_rendered_element(self, command: dict):
        """
        Property 7: For any play command, if media_type is "video" then
        a <video> element is rendered; if "audio" then <audio> is rendered.

        **Validates: Requirements 6.1**
        """
        media_type = command["media_type"]
        rendered_tag = simulate_render(media_type, self.template)
        assert rendered_tag == media_type, (
            f"Expected <{media_type}> for media_type='{media_type}', got <{rendered_tag}>"
        )

    @given(media_type=st.just("video"))
    @settings(max_examples=50)
    def test_video_type_renders_video_element(self, media_type: str):
        """
        Property: media_type="video" always renders a <video> element.

        **Validates: Requirements 6.1**
        """
        assert simulate_render(media_type, self.template) == "video"

    @given(media_type=st.just("audio"))
    @settings(max_examples=50)
    def test_audio_type_renders_audio_element(self, media_type: str):
        """
        Property: media_type="audio" always renders an <audio> element.

        **Validates: Requirements 6.1**
        """
        assert simulate_render(media_type, self.template) == "audio"


class TestTemplateStructure:
    """Verify the component template has the correct conditional structure."""

    @classmethod
    def setup_class(cls):
        cls.template = read_component_template()

    def test_template_has_video_and_audio_elements(self):
        """Template must contain both <video> and <audio> elements."""
        assert "<video" in self.template
        assert "<audio" in self.template

    def test_video_has_v_if_checking_media_type(self):
        """The <video> element must use v-if/v-else-if checking mediaType."""
        elements = extract_conditional_elements(self.template)
        video_els = [e for e in elements if e["tag"] == "video"]
        assert any(
            e["condition"] and "mediaType" in e["condition"] and "'video'" in e["condition"]
            for e in video_els
        ), "Video element must check mediaType === 'video'"

    def test_audio_is_fallback_via_v_else(self):
        """The <audio> element should use v-else as fallback."""
        elements = extract_conditional_elements(self.template)
        audio_els = [e for e in elements if e["tag"] == "audio"]
        assert any(e["directive"] == "else" for e in audio_els), "Audio element should use v-else"

    def test_video_and_audio_mutually_exclusive(self):
        """Only one of video/audio renders for any valid media_type."""
        for mt in ["video", "audio"]:
            assert simulate_render(mt, self.template) == mt
