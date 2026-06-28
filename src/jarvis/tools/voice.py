# src/jarvis/tools/voice.py
# ============================================
# Voice Tool — Speech In + Speech Out
#
# STT: openai-whisper (runs fully locally)
#   - Records your microphone
#   - Transcribes audio to text
#   - No internet needed, completely private
#
# TTS: pyttsx3 (offline Windows SAPI voices)
#   - Converts JARVIS replies to speech
#   - Uses built-in Windows voices
#   - No internet needed
#
# Models available for Whisper:
#   tiny   — fastest, least accurate (~1s)
#   base   — good balance (default) (~2s)
#   small  — more accurate (~5s)
#   medium — very accurate (~10s)
#   large  — best quality (~30s)
# ============================================

import threading
import queue
import time
from loguru import logger


class VoiceTool:
    name = "voice"

    def __init__(self):
        self._whisper_model = None
        self._tts_engine = None
        self._model_name = "base"
        self._is_speaking = False
        self._speak_queue = queue.Queue()
        self._speak_thread = None
        logger.info("VoiceTool initialised (models load on first use)")

    # ------------------------------------------------------------------
    # SCHEMA DEFINITIONS
    # ------------------------------------------------------------------

    def get_schemas(self) -> dict:
        return {
            "listen_once": {
                "type": "function",
                "function": {
                    "name": "listen_once",
                    "description": (
                        "Record audio from the microphone for a set duration "
                        "and return the transcribed text. Use when the user "
                        "wants JARVIS to listen for a voice command."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "duration": {
                                "type": "integer",
                                "description": "How many seconds to record (default 5)",
                            }
                        },
                        "required": [],
                    },
                },
            },
            "speak": {
                "type": "function",
                "function": {
                    "name": "speak",
                    "description": (
                        "Convert text to speech and play it aloud. "
                        "Use when the user wants JARVIS to say something out loud."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "text": {
                                "type": "string",
                                "description": "Text to speak aloud",
                            }
                        },
                        "required": ["text"],
                    },
                },
            },
            "set_voice_speed": {
                "type": "function",
                "function": {
                    "name": "set_voice_speed",
                    "description": "Set how fast JARVIS speaks. Normal is 175 words per minute.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "rate": {
                                "type": "integer",
                                "description": "Words per minute. 150=slow, 175=normal, 200=fast, 250=very fast",
                            }
                        },
                        "required": ["rate"],
                    },
                },
            },
        }

    # ------------------------------------------------------------------
    # INTERNAL: lazy model loading
    # ------------------------------------------------------------------

    def _load_whisper(self):
        """Load Whisper model on first use (takes 5-10 seconds)."""
        if self._whisper_model is None:
            logger.info(f"Loading Whisper '{self._model_name}' model...")
            import whisper
            self._whisper_model = whisper.load_model(self._model_name)
            logger.info("Whisper model loaded and ready")
        return self._whisper_model

    def _load_tts(self):
        """Initialise pyttsx3 TTS engine on first use."""
        if self._tts_engine is None:
            import pyttsx3
            self._tts_engine = pyttsx3.init()
            self._tts_engine.setProperty("rate", 175)
            self._tts_engine.setProperty("volume", 1.0)

            # Use the best available Windows voice
            voices = self._tts_engine.getProperty("voices")
            if voices:
                # Prefer English voices
                english = [v for v in voices if "en" in v.id.lower()]
                if english:
                    self._tts_engine.setProperty("voice", english[0].id)
                    logger.info(f"TTS voice: {english[0].name}")

            logger.info("TTS engine ready")
        return self._tts_engine

    # ------------------------------------------------------------------
    # TOOL IMPLEMENTATIONS
    # ------------------------------------------------------------------

    def listen_once(self, duration: int = 5) -> str:
        """
        Record audio from microphone and transcribe it using Whisper.
        Returns the transcribed text string.
        """
        logger.info(f"listen_once: recording for {duration}s")
        try:
            import sounddevice as sd
            import numpy as np

            model = self._load_whisper()

            sample_rate = 16000  # Whisper requires 16kHz
            logger.info(f"Recording for {duration} seconds...")

            # Record audio
            audio = sd.rec(
                int(duration * sample_rate),
                samplerate=sample_rate,
                channels=1,
                dtype="float32",
            )
            sd.wait()  # Wait until recording is done

            # Flatten to 1D array
            audio_flat = audio.flatten()

            # Transcribe
            logger.info("Transcribing audio...")
            result = model.transcribe(
                audio_flat,
                fp16=False,  # Use fp32 for CPU compatibility
                language="en",
            )

            text = result["text"].strip()
            logger.info(f"Transcribed: {text}")

            if not text:
                return "No speech detected. Please try again."

            return text

        except ImportError as e:
            return f"Missing dependency: {e}. Run: pip install sounddevice numpy openai-whisper"
        except Exception as e:
            logger.error(f"listen_once failed: {e}")
            return f"Error recording audio: {e}"

    def speak(self, text: str) -> str:
        """
        Convert text to speech and play it.
        Runs in the current thread — blocks until speech is done.
        """
        logger.info(f"speak: {text[:60]}...")
        try:
            engine = self._load_tts()

            # Clean up text for speech
            # Remove markdown, URLs, special chars that sound bad
            clean = text
            clean = clean.replace("**", "").replace("*", "")
            clean = clean.replace("```", "").replace("`", "")
            clean = clean.replace("#", "").replace("→", "goes to")
            clean = clean.replace("✅", "done").replace("❌", "failed")

            # Truncate very long text
            if len(clean) > 500:
                clean = clean[:500] + "... and more."

            engine.say(clean)
            engine.runAndWait()
            return "Spoken successfully."

        except Exception as e:
            logger.error(f"speak failed: {e}")
            return f"Error speaking: {e}"

    def set_voice_speed(self, rate: int) -> str:
        """Set TTS speaking rate in words per minute."""
        logger.info(f"set_voice_speed: {rate} wpm")
        try:
            engine = self._load_tts()
            rate = max(100, min(400, rate))  # Clamp between 100-400
            engine.setProperty("rate", rate)
            return f"Voice speed set to {rate} words per minute."
        except Exception as e:
            logger.error(f"set_voice_speed failed: {e}")
            return f"Error setting speed: {e}"

    # ------------------------------------------------------------------
    # PUBLIC HELPERS (used directly by cli.py voice mode)
    # ------------------------------------------------------------------

    def transcribe_file(self, audio_path: str) -> str:
        """Transcribe an existing audio file."""
        try:
            model = self._load_whisper()
            result = model.transcribe(audio_path, fp16=False, language="en")
            return result["text"].strip()
        except Exception as e:
            logger.error(f"transcribe_file failed: {e}")
            return ""

    def speak_async(self, text: str):
        """Speak text in a background thread so JARVIS stays responsive."""
        t = threading.Thread(target=self.speak, args=(text,), daemon=True)
        t.start()

    def test_microphone(self) -> str:
        """Quick test to verify microphone is working."""
        try:
            import sounddevice as sd
            devices = sd.query_devices()
            input_devices = [d for d in devices if d["max_input_channels"] > 0]
            if not input_devices:
                return "No microphone found. Please connect a microphone."
            default = sd.query_devices(kind="input")
            return f"Microphone ready: {default['name']}"
        except Exception as e:
            return f"Microphone test failed: {e}"