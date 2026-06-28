# tests/test_code.py
# ============================================
# Unit tests for Phase 2 — Code Tool
# Run with: python -m pytest tests/test_code.py -v
# ============================================

import subprocess
import pytest
from unittest.mock import patch, MagicMock
from src.jarvis.tools.code import CodeTool


@pytest.fixture
def tool():
    return CodeTool()


# ── git_command ──────────────────────────────

def test_git_command_status(tool, tmp_path):
    # Init a real git repo for testing
    subprocess.run(["git", "init"], cwd=str(tmp_path), capture_output=True)
    result = tool.git_command("status", project_path=str(tmp_path))
    assert isinstance(result, str)
    assert len(result) > 0


def test_git_command_invalid_path(tool):
    result = tool.git_command("status", project_path="C:\\nonexistent_xyz_abc")
    assert "not found" in result.lower()


def test_git_command_log(tool, tmp_path):
    subprocess.run(["git", "init"], cwd=str(tmp_path), capture_output=True)
    result = tool.git_command("log --oneline", project_path=str(tmp_path))
    assert isinstance(result, str)


# ── run_tests ────────────────────────────────

def test_run_tests_with_passing_test(tool, tmp_path):
    # Create a simple passing test
    test_file = tmp_path / "test_sample.py"
    test_file.write_text("def test_pass():\n    assert True\n")
    result = tool.run_tests(project_path=str(tmp_path))
    assert "passed" in result.lower() or "1" in result


def test_run_tests_with_failing_test(tool, tmp_path):
    test_file = tmp_path / "test_fail.py"
    test_file.write_text("def test_fail():\n    assert False\n")
    result = tool.run_tests(project_path=str(tmp_path))
    assert "failed" in result.lower() or "FAILED" in result


def test_run_tests_invalid_path(tool):
    result = tool.run_tests(project_path="C:\\nonexistent_xyz_abc")
    assert "not found" in result.lower()


# ── open_in_vscode ───────────────────────────

@patch("subprocess.Popen")
def test_open_in_vscode_valid_path(mock_popen, tool, tmp_path):
    result = tool.open_in_vscode(str(tmp_path))
    mock_popen.assert_called_once()
    assert "vs code" in result.lower() or "vscode" in result.lower()


def test_open_in_vscode_invalid_path(tool):
    result = tool.open_in_vscode("C:\\nonexistent_xyz_abc")
    assert "not found" in result.lower()


# ── pip_install ──────────────────────────────

@patch("subprocess.run")
def test_pip_install_valid_package(mock_run, tool):
    mock_run.return_value = MagicMock(
        stdout="Successfully installed requests",
        stderr="",
        returncode=0,
    )
    result = tool.pip_install("requests")
    assert isinstance(result, str)


def test_pip_install_blocks_injection(tool):
    # Shell injection characters should be rejected
    result = tool.pip_install("requests; rm -rf /")
    assert "invalid" in result.lower()


def test_pip_install_blocks_ampersand(tool):
    result = tool.pip_install("requests && echo hacked")
    assert "invalid" in result.lower()


# ── get_python_info ──────────────────────────

def test_get_python_info_returns_version(tool):
    result = tool.get_python_info()
    assert "Python" in result
    assert "3." in result  # Python 3.x


def test_get_python_info_shows_venv_status(tool):
    result = tool.get_python_info()
    assert "Virtual env" in result


def test_get_python_info_shows_executable(tool):
    result = tool.get_python_info()
    assert "Executable" in result


# ── run_python_file ──────────────────────────

def test_run_python_file_success(tool, tmp_path):
    script = tmp_path / "hello.py"
    script.write_text("print('hello from jarvis')\n")
    result = tool.run_python_file(str(script))
    assert "hello from jarvis" in result


def test_run_python_file_not_found(tool):
    result = tool.run_python_file("C:\\nonexistent_script.py")
    assert "not found" in result.lower()


def test_run_python_file_not_python(tool, tmp_path):
    f = tmp_path / "file.txt"
    f.write_text("hello")
    result = tool.run_python_file(str(f))
    assert "not a python" in result.lower()


def test_run_python_file_with_error(tool, tmp_path):
    script = tmp_path / "error.py"
    script.write_text("raise ValueError('test error')\n")
    result = tool.run_python_file(str(script))
    assert isinstance(result, str)  # Should not crash JARVIS
