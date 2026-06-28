# src/jarvis/main.py
# ============================================
# JARVIS Entry Point
#
# This file wires everything together:
#   1. Sets up logging
#   2. Loads config (validates .env)
#   3. Registers all tool modules
#   4. Creates the agent
#   5. Launches the chosen interface
#
# Run with:
#   python -m src.jarvis.main              (text mode)
#   python -m src.jarvis.main --voice      (voice mode)
#   python -m src.jarvis.main --mode cli   (default)
# ============================================

import sys
import argparse
from pathlib import Path
from loguru import logger


def setup_logging(log_level: str):
    """Configure loguru: pretty console output + rotating file."""
    logger.remove()

    # Console: clean, coloured, INFO and above
    logger.add(
        sys.stderr,
        level=log_level,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}",
        colorize=True,
    )

    # File: full detail, rotating, kept 14 days
    log_dir = Path("data/logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    logger.add(
        log_dir / "jarvis_{time:YYYY-MM-DD}.log",
        rotation="10 MB",
        retention="14 days",
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {module}:{function}:{line} | {message}",
    )


def register_tools():
    """
    Register every tool module here.
    To add a new tool:
      1. Create src/jarvis/tools/your_tool.py
      2. Import and register it below.
    """
    from .tools.registry import registry

    # Phase 1 — system control
    from .tools.system import SystemTool
    registry.register(SystemTool())

    # Phase 2 — browser, search, code
    from .tools.browser import BrowserTool
    registry.register(BrowserTool())

    from .tools.search import SearchTool
    registry.register(SearchTool())

    from .tools.code import CodeTool
    registry.register(CodeTool())

    # Phase 3 — voice
    from .tools.voice import VoiceTool
    registry.register(VoiceTool())

    # Phase 4 — uncomment when built
    # from .memory.long_term import LongTermMemory
    # Phase 5 — uncomment when built
    # from .tools.email_tool import EmailTool

    logger.info(f"Tools registered: {registry.list_tools()}")


def main():
    parser = argparse.ArgumentParser(description="JARVIS AI Automation System")
    parser.add_argument(
        "--mode",
        choices=["cli", "gui", "tray"],
        default="cli",
        help="Interface to launch (default: cli)",
    )
    parser.add_argument(
        "--voice",
        action="store_true",
        help="Start with voice mode enabled",
    )
    args = parser.parse_args()

    # 1. Load config
    from .config import settings
    setup_logging(settings.jarvis_log_level)

    logger.info("=" * 50)
    logger.info("JARVIS starting up")
    logger.info(f"Mode   : {args.mode}")
    logger.info(f"Voice  : {args.voice}")
    logger.info(f"Model  : {settings.jarvis_model}")
    logger.info("=" * 50)

    # 2. Register all tools
    register_tools()

    # 3. Create the agent
    from .agent import Agent
    agent = Agent()

    # 4. Launch interface
    if args.mode == "cli":
        from .interfaces.cli import run_cli
        run_cli(agent, voice_mode=args.voice)

    elif args.mode == "gui":
        logger.warning("GUI not built yet — launching CLI. (Phase 5)")
        from .interfaces.cli import run_cli
        run_cli(agent, voice_mode=args.voice)

    elif args.mode == "tray":
        logger.warning("Tray not built yet — launching CLI. (Phase 5)")
        from .interfaces.cli import run_cli
        run_cli(agent, voice_mode=args.voice)


if __name__ == "__main__":
    main()