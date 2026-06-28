# src/jarvis/interfaces/cli.py
# ============================================
# CLI Interface — terminal REPL with voice mode
#
# Two modes:
#   Normal mode: type commands, read replies
#   Voice mode:  type /voice to enable,
#                press ENTER to record 5 seconds,
#                JARVIS transcribes + sends + speaks reply
#
# Special commands (both modes):
#   exit / quit / bye  → shut down
#   /reset             → clear memory
#   /tools             → list tools
#   /voice             → toggle voice mode on/off
#   /help              → show commands
# ============================================

from loguru import logger
from ..config import settings


HELP_TEXT = """
Available commands:
  /reset    — clear conversation memory
  /tools    — list all registered tools
  /voice    — toggle voice input/output on/off
  /help     — show this message
  exit      — quit JARVIS
"""


def get_banner(model: str, voice: bool = False) -> str:
    voice_str = "ON" if voice else "OFF"
    return f"""
+----------------------------------------------+
|   JARVIS - AI Automation System              |
|   Model : {model:<34}|
|   Voice : {voice_str:<34}|
|   Type  : /help for commands, exit to quit   |
+----------------------------------------------+"""


def run_cli(agent, voice_mode: bool = False):
    """
    Start the CLI REPL.
    voice_mode=True enables microphone input + TTS output.
    """
    voice_tool = None

    # If voice mode requested at startup, load it now
    if voice_mode:
        voice_tool = _load_voice()
        if voice_tool is None:
            voice_mode = False

    print(get_banner(settings.jarvis_model, voice_mode))

    if voice_mode:
        print("Voice mode ON — press ENTER (empty) to record, or just type normally.\n")

    while True:
        try:
            # ── VOICE INPUT ──────────────────────────
            if voice_mode and voice_tool:
                raw = input("You [ENTER=record / type=text]: ").strip()

                if raw == "":
                    # Empty enter = record voice
                    print("Recording 5 seconds... speak now!")
                    user_input = voice_tool.listen_once(duration=5)
                    print(f"You (voice): {user_input}")
                else:
                    user_input = raw

            # ── TEXT INPUT ───────────────────────────
            else:
                user_input = input("You: ").strip()

        except (KeyboardInterrupt, EOFError):
            print("\nJARVIS: Shutting down. Goodbye.")
            if voice_mode and voice_tool:
                voice_tool.speak("Goodbye.")
            break

        if not user_input:
            continue

        # ── SPECIAL COMMANDS ─────────────────────────
        if user_input.lower() in ("exit", "quit", "bye"):
            print("JARVIS: Goodbye.")
            if voice_mode and voice_tool:
                voice_tool.speak("Goodbye.")
            break

        if user_input.lower() == "/reset":
            agent.reset()
            print("JARVIS: Memory cleared. Fresh start.")
            continue

        if user_input.lower() == "/tools":
            from ..tools.registry import registry
            tools = registry.list_tools()
            print(f"JARVIS: {len(tools)} tools registered:")
            for t in tools:
                print(f"  • {t}")
            continue

        if user_input.lower() == "/voice":
            # Toggle voice mode on/off
            if not voice_mode:
                voice_tool = _load_voice()
                if voice_tool:
                    voice_mode = True
                    print("JARVIS: Voice mode ON. Press ENTER (empty) to record.")
                else:
                    print("JARVIS: Could not enable voice. Check install.")
            else:
                voice_mode = False
                print("JARVIS: Voice mode OFF.")
            # Reprint banner with updated status
            print(get_banner(settings.jarvis_model, voice_mode))
            continue

        if user_input.lower() == "/help":
            print(HELP_TEXT)
            continue

        # ── SEND TO AGENT ─────────────────────────────
        print("JARVIS: thinking...", end="\r", flush=True)
        try:
            reply = agent.chat(user_input)
            print(" " * 40, end="\r")  # Clear "thinking..."
            print(f"JARVIS: {reply}\n")

            # Speak reply if voice mode is on
            if voice_mode and voice_tool:
                voice_tool.speak_async(reply)

        except Exception as e:
            logger.error(f"Agent error: {e}")
            print(f"JARVIS: Something went wrong — {e}\n")


def _load_voice():
    """Try to load VoiceTool. Returns instance or None."""
    try:
        from ..tools.voice import VoiceTool
        vt = VoiceTool()
        mic = vt.test_microphone()
        logger.info(f"Voice loaded: {mic}")
        print(f"  Microphone: {mic}")
        return vt
    except Exception as e:
        logger.error(f"Voice load failed: {e}")
        print(f"  Voice error: {e}")
        return None