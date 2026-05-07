# src/jarvis/tools/system.py
# ============================================
# System Tool — controls files, apps, shell,
# and system info on Windows.
#
# Every method:
#   - Takes simple typed arguments
#   - Returns a plain string (success or error)
#   - Never raises an exception to the caller
#   - Has a timeout on anything that can hang
# ============================================

import os
import shutil
import subprocess
from pathlib import Path

import psutil
from loguru import logger
from winotify import Notification, audio


class SystemTool:
    name = "system"

    # ------------------------------------------------------------------
    # SCHEMA DEFINITION
    # The LLM reads these to know what tools exist and how to call them.
    # ------------------------------------------------------------------

    def get_schemas(self) -> dict:
        return {
            "run_command": {
                "type": "function",
                "function": {
                    "name": "run_command",
                    "description": (
                        "Run any Windows CMD or PowerShell command and return its output. "
                        "Use for git, pip, dir, tasklist, ipconfig, echo, mkdir, etc."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "command": {
                                "type": "string",
                                "description": "The shell command to run, e.g. 'git status' or 'dir C:\\Users'",
                            }
                        },
                        "required": ["command"],
                    },
                },
            },
            "open_app": {
                "type": "function",
                "function": {
                    "name": "open_app",
                    "description": (
                        "Open a Windows application by name. "
                        "Supports: notepad, calculator, paint, chrome, firefox, "
                        "vscode, explorer, taskmgr, word, excel, powerpoint."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "app_name": {
                                "type": "string",
                                "description": "App name, e.g. 'notepad', 'chrome', 'vscode'",
                            }
                        },
                        "required": ["app_name"],
                    },
                },
            },
            "list_files": {
                "type": "function",
                "function": {
                    "name": "list_files",
                    "description": "List all files and folders at a given directory path.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "Directory path, e.g. 'C:\\Users\\you\\Documents'",
                            }
                        },
                        "required": ["path"],
                    },
                },
            },
            "read_file": {
                "type": "function",
                "function": {
                    "name": "read_file",
                    "description": "Read and return the contents of any text file.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "filepath": {
                                "type": "string",
                                "description": "Full path to the file to read",
                            }
                        },
                        "required": ["filepath"],
                    },
                },
            },
            "write_file": {
                "type": "function",
                "function": {
                    "name": "write_file",
                    "description": "Write or create a text file with the given content. Overwrites if it exists.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "filepath": {
                                "type": "string",
                                "description": "Full path to write to",
                            },
                            "content": {
                                "type": "string",
                                "description": "Text content to write",
                            },
                        },
                        "required": ["filepath", "content"],
                    },
                },
            },
            "send_notification": {
                "type": "function",
                "function": {
                    "name": "send_notification",
                    "description": "Send a Windows desktop toast notification with a title and message.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "title": {
                                "type": "string",
                                "description": "Notification title",
                            },
                            "message": {
                                "type": "string",
                                "description": "Notification body text",
                            },
                        },
                        "required": ["title", "message"],
                    },
                },
            },
            "get_system_info": {
                "type": "function",
                "function": {
                    "name": "get_system_info",
                    "description": (
                        "Get current system information: CPU usage, RAM usage, "
                        "disk space, and running process count."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": [],
                    },
                },
            },
        }

    # ------------------------------------------------------------------
    # IMPLEMENTATIONS
    # ------------------------------------------------------------------

    def run_command(self, command: str) -> str:
        """Run a shell command, return output (max 3000 chars)."""
        logger.info(f"run_command: {command}")
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=15,
            )
            output = result.stdout.strip() or result.stderr.strip()
            if not output:
                return "Command completed successfully (no output)."
            # Truncate very long output so it fits in the context window
            if len(output) > 3000:
                output = output[:3000] + "\n... (output truncated)"
            return output
        except subprocess.TimeoutExpired:
            return "Error: command timed out after 15 seconds."
        except Exception as e:
            logger.error(f"run_command failed: {e}")
            return f"Error: {e}"

    def open_app(self, app_name: str) -> str:
        """Open a Windows application by friendly name."""
        logger.info(f"open_app: {app_name}")

        APP_MAP = {
            "notepad":        "notepad.exe",
            "calculator":     "calc.exe",
            "calc":           "calc.exe",
            "paint":          "mspaint.exe",
            "chrome":         "chrome.exe",
            "google chrome":  "chrome.exe",
            "firefox":        "firefox.exe",
            "explorer":       "explorer.exe",
            "file explorer":  "explorer.exe",
            "vscode":         "code",
            "vs code":        "code",
            "visual studio code": "code",
            "taskmgr":        "taskmgr.exe",
            "task manager":   "taskmgr.exe",
            "word":           "winword.exe",
            "excel":          "excel.exe",
            "powerpoint":     "powerpnt.exe",
            "cmd":            "cmd.exe",
            "terminal":       "wt.exe",
            "powershell":     "powershell.exe",
        }

        key = app_name.lower().strip()
        exe = APP_MAP.get(key, app_name)

        try:
            subprocess.Popen(exe, shell=True)
            return f"Opened {app_name} successfully."
        except Exception as e:
            logger.error(f"open_app failed: {e}")
            return f"Could not open '{app_name}': {e}"

    def list_files(self, path: str) -> str:
        """List files and directories at a path."""
        logger.info(f"list_files: {path}")
        try:
            p = Path(path)
            if not p.exists():
                return f"Path does not exist: {path}"
            if not p.is_dir():
                return f"Not a directory: {path}"

            items = list(p.iterdir())
            if not items:
                return f"Directory is empty: {path}"

            # Sort: folders first, then files
            folders = sorted([i for i in items if i.is_dir()], key=lambda x: x.name.lower())
            files = sorted([i for i in items if i.is_file()], key=lambda x: x.name.lower())

            lines = [f"Contents of {path}:\n"]
            for f in folders:
                lines.append(f"  [DIR]  {f.name}")
            for f in files:
                size = f.stat().st_size
                size_str = f"{size:,} bytes" if size < 1024 else f"{size//1024:,} KB"
                lines.append(f"  [FILE] {f.name}  ({size_str})")

            return "\n".join(lines)
        except PermissionError:
            return f"Permission denied: {path}"
        except Exception as e:
            logger.error(f"list_files failed: {e}")
            return f"Error listing files: {e}"

    def read_file(self, filepath: str) -> str:
        """Read a text file and return its contents."""
        logger.info(f"read_file: {filepath}")
        try:
            p = Path(filepath)
            if not p.exists():
                return f"File not found: {filepath}"
            if not p.is_file():
                return f"Not a file: {filepath}"

            content = p.read_text(encoding="utf-8", errors="replace")
            if not content.strip():
                return "File is empty."
            # Truncate large files
            if len(content) > 5000:
                return content[:5000] + "\n... (file truncated — showing first 5000 chars)"
            return content
        except Exception as e:
            logger.error(f"read_file failed: {e}")
            return f"Error reading file: {e}"

    def write_file(self, filepath: str, content: str) -> str:
        """Write content to a file, creating directories if needed."""
        logger.info(f"write_file: {filepath}")
        try:
            p = Path(filepath)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
            return f"File written successfully: {filepath} ({len(content)} chars)"
        except Exception as e:
            logger.error(f"write_file failed: {e}")
            return f"Error writing file: {e}"

    def send_notification(self, title: str, message: str) -> str:
        """Send a Windows desktop toast notification."""
        logger.info(f"send_notification: {title}")
        try:
            toast = Notification(
                app_id="JARVIS",
                title=title,
                msg=message,
                duration="short",
            )
            toast.set_audio(audio.Default, loop=False)
            toast.show()
            return "Notification sent."
        except Exception as e:
            logger.error(f"send_notification failed: {e}")
            return f"Notification failed: {e}"

    def get_system_info(self) -> str:
        """Return CPU, RAM, disk, and process info."""
        logger.info("get_system_info called")
        try:
            cpu = psutil.cpu_percent(interval=1)
            ram = psutil.virtual_memory()
            disk = psutil.disk_usage("C:\\")
            proc_count = len(psutil.pids())

            return (
                f"System Info:\n"
                f"  CPU usage:     {cpu}%\n"
                f"  RAM used:      {ram.used // (1024**2):,} MB / {ram.total // (1024**2):,} MB ({ram.percent}%)\n"
                f"  Disk C: used:  {disk.used // (1024**3):,} GB / {disk.total // (1024**3):,} GB ({disk.percent}%)\n"
                f"  Running procs: {proc_count}"
            )
        except Exception as e:
            logger.error(f"get_system_info failed: {e}")
            return f"Error getting system info: {e}"