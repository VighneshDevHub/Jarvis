# src/jarvis/tools/code.py
# ============================================
# Code Tool — developer automation
#
# Lets JARVIS help with coding workflows:
# - Git commands (status, log, diff, commit)
# - Run pytest and return results
# - Open projects in VS Code
# - Install pip packages
# - Check Python environment info
# ============================================

import subprocess
from pathlib import Path
from loguru import logger


class CodeTool:
    name = "code"

    def get_schemas(self) -> dict:
        return {
            "git_command": {
                "type": "function",
                "function": {
                    "name": "git_command",
                    "description": (
                        "Run a git command in a project directory and return the output. "
                        "Use for git status, git log, git diff, git commit, git push, git pull, etc."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "command": {
                                "type": "string",
                                "description": "Git command without the 'git' prefix, e.g. 'status', 'log --oneline -5', 'diff'",
                            },
                            "project_path": {
                                "type": "string",
                                "description": "Path to the git project folder. Defaults to current directory.",
                            },
                        },
                        "required": ["command"],
                    },
                },
            },
            "run_tests": {
                "type": "function",
                "function": {
                    "name": "run_tests",
                    "description": (
                        "Run pytest in a project directory and return test results. "
                        "Shows which tests passed, failed, and any error messages."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "project_path": {
                                "type": "string",
                                "description": "Path to the project to test. Defaults to current directory.",
                            },
                            "test_path": {
                                "type": "string",
                                "description": "Specific test file or folder to run, e.g. 'tests/test_tools.py'",
                            },
                        },
                        "required": [],
                    },
                },
            },
            "open_in_vscode": {
                "type": "function",
                "function": {
                    "name": "open_in_vscode",
                    "description": "Open a file or folder in VS Code.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "File or folder path to open in VS Code",
                            }
                        },
                        "required": ["path"],
                    },
                },
            },
            "pip_install": {
                "type": "function",
                "function": {
                    "name": "pip_install",
                    "description": "Install a Python package using pip.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "package": {
                                "type": "string",
                                "description": "Package name to install, e.g. 'requests' or 'numpy==1.24'",
                            }
                        },
                        "required": ["package"],
                    },
                },
            },
            "get_python_info": {
                "type": "function",
                "function": {
                    "name": "get_python_info",
                    "description": (
                        "Get information about the current Python environment: "
                        "version, installed packages, virtual env status."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": [],
                    },
                },
            },
            "run_python_file": {
                "type": "function",
                "function": {
                    "name": "run_python_file",
                    "description": "Run a Python script file and return its output.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "filepath": {
                                "type": "string",
                                "description": "Full path to the .py file to run",
                            },
                            "args": {
                                "type": "string",
                                "description": "Optional command line arguments to pass to the script",
                            },
                        },
                        "required": ["filepath"],
                    },
                },
            },
        }

    # ------------------------------------------------------------------
    # INTERNAL HELPERS
    # ------------------------------------------------------------------

    def _run(self, cmd: list, cwd: str = None, timeout: int = 30) -> str:
        """
        Run a subprocess command safely.
        Always returns a string, never raises.
        """
        try:
            result = subprocess.run(
                cmd,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            output = result.stdout.strip()
            if result.returncode != 0 and result.stderr:
                output += f"\n[stderr]: {result.stderr.strip()}"
            if not output:
                return "Command completed with no output."
            # Cap output
            if len(output) > 3000:
                output = output[:3000] + "\n... (output truncated)"
            return output
        except subprocess.TimeoutExpired:
            return f"Error: command timed out after {timeout}s"
        except FileNotFoundError as e:
            return f"Error: command not found — {e}"
        except Exception as e:
            logger.error(f"_run failed: {e}")
            return f"Error: {e}"

    def _resolve_path(self, path: str = None) -> str:
        """Resolve a path, defaulting to current directory."""
        if not path:
            return "."
        p = Path(path)
        if not p.exists():
            return None
        return str(p)

    # ------------------------------------------------------------------
    # TOOL IMPLEMENTATIONS
    # ------------------------------------------------------------------

    def git_command(self, command: str, project_path: str = None) -> str:
        """Run a git command in a project directory."""
        logger.info(f"git_command: git {command} in {project_path or '.'}")

        cwd = self._resolve_path(project_path)
        if cwd is None:
            return f"Error: path not found: {project_path}"

        # Build the git command as a list (safer than shell=True)
        parts = ["git"] + command.split()
        return self._run(parts, cwd=cwd)

    def run_tests(self, project_path: str = None, test_path: str = None) -> str:
        """Run pytest and return results."""
        logger.info(f"run_tests: {project_path or '.'} / {test_path or 'all'}")

        cwd = self._resolve_path(project_path)
        if cwd is None:
            return f"Error: path not found: {project_path}"

        cmd = ["python", "-m", "pytest", "-v", "--tb=short"]
        if test_path:
            cmd.append(test_path)

        return self._run(cmd, cwd=cwd, timeout=60)

    def open_in_vscode(self, path: str) -> str:
        """Open a file or folder in VS Code."""
        logger.info(f"open_in_vscode: {path}")
        try:
            p = Path(path)
            if not p.exists():
                return f"Error: path not found: {path}"
            subprocess.Popen(["code", str(p)], shell=True)
            return f"Opened in VS Code: {path}"
        except Exception as e:
            logger.error(f"open_in_vscode failed: {e}")
            return f"Error opening VS Code: {e}"

    def pip_install(self, package: str) -> str:
        """Install a pip package."""
        logger.info(f"pip_install: {package}")

        # Basic safety check — no shell injection
        if any(c in package for c in [";", "&", "|", "`", "$"]):
            return f"Error: invalid package name: {package}"

        return self._run(
            ["python", "-m", "pip", "install", package],
            timeout=60,
        )

    def get_python_info(self) -> str:
        """Get Python version and environment info."""
        logger.info("get_python_info called")
        try:
            version = self._run(["python", "--version"])
            pip_list = self._run(["python", "-m", "pip", "list", "--format=columns"])

            # Check if in a virtual environment
            import sys
            in_venv = (
                hasattr(sys, "real_prefix")
                or (hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix)
            )

            info = f"Python: {version}\n"
            info += f"Virtual env: {'Yes ✓' if in_venv else 'No'}\n"
            info += f"Executable: {sys.executable}\n\n"
            info += "Installed packages:\n"
            info += pip_list

            if len(info) > 3000:
                info = info[:3000] + "\n... (truncated)"

            return info
        except Exception as e:
            logger.error(f"get_python_info failed: {e}")
            return f"Error getting Python info: {e}"

    def run_python_file(self, filepath: str, args: str = "") -> str:
        """Run a Python script and return output."""
        logger.info(f"run_python_file: {filepath}")

        p = Path(filepath)
        if not p.exists():
            return f"Error: file not found: {filepath}"
        if p.suffix != ".py":
            return f"Error: not a Python file: {filepath}"

        cmd = ["python", str(p)]
        if args:
            cmd.extend(args.split())

        return self._run(cmd, cwd=str(p.parent), timeout=30)