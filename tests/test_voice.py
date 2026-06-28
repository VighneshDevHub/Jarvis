# tests/test_voice.py
# ============================================
# Unit tests for Phase 3 — Voice Tool
# ============================================

import pytest
import numpy as np
from unittest.mock import patch, MagicMock
from src.jarvis.tools.voice import VoiceTool


@pytest.fixture
def tool():
    return VoiceTool()


# ── speak ────────────────────────────────────

def test_speak_success(tool):
    mock_engine = MagicMock()
    tool._tts_engine = mock_engine
    result = tool.speak("Hello JARVIS")
    mock_engine.say.assert_called_once()
    mock_engine.runAndWait.assert_called_once()
    assert "spoken" in result.lower()


def test_speak_cleans_markdown(tool):
    mock_engine = MagicMock()
    tool._tts_engine = mock_engine
    tool.speak("**Bold text** and `code` here")
    call_args = mock_engine.say.call_args[0][0]
    assert "**" not in call_args
    assert "`" not in call_args


def test_speak_truncates_long_text(tool):
    mock_engine = MagicMock()
    tool._tts_engine = mock_engine
    long_text = "word " * 200
    tool.speak(long_text)
    call_args = mock_engine.say.call_args[0][0]
    assert len(call_args) <= 520


def test_speak_handles_engine_error(tool):
    mock_engine = MagicMock()
    mock_engine.say.side_effect = Exception("TTS crashed")
    tool._tts_engine = mock_engine
    result = tool.speak("Hello")
    assert "error" in result.lower()


def test_speak_empty_string(tool):
    mock_engine = MagicMock()
    tool._tts_engine = mock_engine
    result = tool.speak("")
    assert isinstance(result, str)


# ── set_voice_speed ──────────────────────────

def test_set_voice_speed_normal(tool):
    mock_engine = MagicMock()
    tool._tts_engine = mock_engine
    result = tool.set_voice_speed(175)
    mock_engine.setProperty.assert_called_with("rate", 175)
    assert "175" in result


def test_set_voice_speed_clamps_too_low(tool):
    mock_engine = MagicMock()
    tool._tts_engine = mock_engine
    tool.set_voice_speed(50)
    call_args = mock_engine.setProperty.call_args[0]
    assert call_args[1] >= 100


def test_set_voice_speed_clamps_too_high(tool):
    mock_engine = MagicMock()
    tool._tts_engine = mock_engine
    tool.set_voice_speed(999)
    call_args = mock_engine.setProperty.call_args[0]
    assert call_args[1] <= 400


# ── listen_once ──────────────────────────────

@patch("sounddevice.rec")
@patch("sounddevice.wait")
def test_listen_once_detects_speech(mock_wait, mock_rec, tool):
    fake_audio = np.random.randn(80000, 1).astype("float32") * 0.1
    mock_rec.return_value = fake_audio

    mock_model = MagicMock()
    mock_model.transcribe.return_value = {"text": "open notepad"}
    tool._whisper_model = mock_model

    result = tool.listen_once(duration=5)
    assert "open notepad" in result


@patch("sounddevice.rec")
@patch("sounddevice.wait")
def test_listen_once_no_speech(mock_wait, mock_rec, tool):
    fake_audio = np.zeros((80000, 1), dtype="float32")
    mock_rec.return_value = fake_audio

    mock_model = MagicMock()
    mock_model.transcribe.return_value = {"text": ""}
    tool._whisper_model = mock_model

    result = tool.listen_once(duration=5)
    assert "no speech" in result.lower()


@patch("sounddevice.rec")
@patch("sounddevice.wait")
def test_listen_once_single_word_still_returned(mock_wait, mock_rec, tool):
    """Single word transcriptions ARE returned — noise filter is energy-based."""
    fake_audio = np.random.randn(80000, 1).astype("float32") * 0.1
    mock_rec.return_value = fake_audio

    mock_model = MagicMock()
    mock_model.transcribe.return_value = {"text": "um"}
    tool._whisper_model = mock_model

    result = tool.listen_once(duration=5)
    # Single word is returned as-is (not filtered as noise)
    assert isinstance(result, str)
    assert len(result) > 0


# ── test_microphone ──────────────────────────

def test_microphone_check_returns_string(tool):
    """test_microphone always returns a string."""
    with patch("sounddevice.query_devices") as mock_query:
        mock_query.return_value = {
            "name": "Realtek Microphone",
            "max_input_channels": 2,
        }
        result = tool.test_microphone()
        assert isinstance(result, str)


def test_microphone_no_device(tool):
    with patch("sounddevice.query_devices", side_effect=Exception("No device")):
        result = tool.test_microphone()
    assert "failed" in result.lower() or "error" in result.lower()


# ── speak_async ──────────────────────────────

def test_speak_async_does_not_block(tool):
    """speak_async returns immediately without waiting for speech."""
    import time
    mock_engine = MagicMock()

    original_speak = tool.speak

    def slow_speak(text):
        time.sleep(0.5)
        return "Spoken successfully."

    tool.speak = slow_speak

    start = time.time()
    tool.speak_async("This is a test message")
    elapsed = time.time() - start

    assert elapsed < 0.2
    tool.speak = original_speak