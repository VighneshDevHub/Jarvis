# src/jarvis/interfaces/cli.py
# ============================================
# CLI Interface — the simplest way to run JARVIS.
# A terminal REPL: type a message, get a reply.
#
# Special commands:
#   exit / quit / bye → shut down
#   /reset            → clear conversation memory
#   /tools            → list registered tools
#   /help             → show this list
# ============================================

from loguru import logger


BANNER = """
╔══════════════════════════════════════════════╗
║   JARVIS — AI Automation System              ║
║   Model : llama-3.3-70b (Groq)              ║
║   Type  : /help for commands, exit to quit   ║
╚══════════════════════════════════════════════╝
"""

HELP_TEXT = """
Available commands:
  /reset    — clear conversation memory
  /tools    — list all registered tools
  /help     — show this message
  exit      — quit JARVIS
"""


def run_cli(agent):
    """
    Start the CLI REPL.
    Accepts the agent instance so the interface is fully decoupled.
    """
    print(BANNER)

    while True:
        try:
            user_input = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nJARVIS: Shutting down. Goodbye.")
            break

        if not user_input:
            continue

        # --- Special slash commands ---
        if user_input.lower() in ("exit", "quit", "bye"):
            print("JARVIS: Goodbye.")
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

        if user_input.lower() == "/help":
            print(HELP_TEXT)
            continue

        # --- Normal message → agent ---
        print("JARVIS: thinking...", end="\r")
        try:
            reply = agent.chat(user_input)
            # Clear the "thinking..." line
            print(" " * 30, end="\r")
            print(f"JARVIS: {reply}\n")
        except Exception as e:
            logger.error(f"Agent error: {e}")
            print(f"JARVIS: Something went wrong — {e}\n")
