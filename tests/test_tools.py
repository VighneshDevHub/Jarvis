# tests/test_tools.py
# ============================================
# Unit tests for Phase 1 — System Tools
# Run with: python -m pytest tests/test_tools.py -v
# ============================================

import subprocess
import pytest
from unittest.mock import patch, MagicMock
from src.jarvis.tools.system import SystemTool


@pytest.fixture
def tool():
    return SystemTool()


# ── run_command ───────────────────────────────

def test_run_command_success(tool):
    result = tool.run_command("echo hello jarvis")
    assert "hello jarvis" in result.lower()


def test_run_command_timeout(tool):
    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("cmd", 15)):
        result = tool.run_command("sleep 9999")
    assert "timed out" in result


def test_run_command_empty_output(tool):
    # Commands that succeed with no output
    result = tool.run_command("echo.")
    assert result is not None


def test_run_command_invalid(tool):
    result = tool.run_command("this_command_does_not_exist_xyz")
    # Should return error string, not raise
    assert isinstance(result, str)


def test_run_command_truncates_long_output(tool):
    # Generate long output
    result = tool.run_command("python -c \"print('x' * 5000)\"")
    assert len(result) <= 3100  # 3000 + small buffer for truncation msg


# ── list_files ───────────────────────────────

def test_list_files_valid(tool, tmp_path):
    (tmp_path / "test.txt").write_text("hello")
    (tmp_path / "subdir").mkdir()
    result = tool.list_files(str(tmp_path))
    assert "test.txt" in result
    assert "subdir" in result


def test_list_files_not_found(tool):
    result = tool.list_files("C:\\this_path_does_not_exist_xyz_abc")
    assert "does not exist" in result


def test_list_files_empty_dir(tool, tmp_path):
    result = tool.list_files(str(tmp_path))
    assert "empty" in result.lower()


def test_list_files_not_a_directory(tool, tmp_path):
    f = tmp_path / "file.txt"
    f.write_text("hello")
    result = tool.list_files(str(f))
    assert "not a directory" in result.lower()


def test_list_files_sorts_dirs_first(tool, tmp_path):
    (tmp_path / "z_file.txt").write_text("hello")
    (tmp_path / "a_dir").mkdir()
    result = tool.list_files(str(tmp_path))
    dir_pos = result.find("a_dir")
    file_pos = result.find("z_file.txt")
    assert dir_pos < file_pos  # dirs before files


# ── read_file ────────────────────────────────

def test_read_file_success(tool, tmp_path):
    f = tmp_path / "readme.txt"
    f.write_text("hello jarvis")
    result = tool.read_file(str(f))
    assert "hello jarvis" in result


def test_read_file_not_found(tool):
    result = tool.read_file("C:\\nonexistent_file_xyz.txt")
    assert "not found" in result.lower()


def test_read_file_empty(tool, tmp_path):
    f = tmp_path / "empty.txt"
    f.write_text("")
    result = tool.read_file(str(f))
    assert "empty" in result.lower()


def test_read_file_truncates_large(tool, tmp_path):
    f = tmp_path / "large.txt"
    f.write_text("x" * 10000)
    result = tool.read_file(str(f))
    assert len(result) <= 5100
    assert "truncated" in result


# ── write_file ───────────────────────────────

def test_write_file_success(tool, tmp_path):
    filepath = str(tmp_path / "output.txt")
    result = tool.write_file(filepath, "test content")
    assert "written" in result.lower()
    from pathlib import Path
    assert Path(filepath).read_text() == "test content"


def test_write_file_creates_dirs(tool, tmp_path):
    filepath = str(tmp_path / "deep" / "nested" / "file.txt")
    result = tool.write_file(filepath, "nested content")
    assert "written" in result.lower()


def test_write_file_overwrites(tool, tmp_path):
    filepath = str(tmp_path / "file.txt")
    tool.write_file(filepath, "original")
    tool.write_file(filepath, "updated")
    from pathlib import Path
    assert Path(filepath).read_text() == "updated"


# ── open_app ─────────────────────────────────

@patch("subprocess.Popen")
def test_open_app_notepad(mock_popen, tool):
    result = tool.open_app("notepad")
    mock_popen.assert_called_once()
    assert "opened" in result.lower()


@patch("subprocess.Popen")
def test_open_app_vscode(mock_popen, tool):
    result = tool.open_app("vscode")
    mock_popen.assert_called_once()
    assert "opened" in result.lower()


@patch("subprocess.Popen")
def test_open_app_case_insensitive(mock_popen, tool):
    result = tool.open_app("NOTEPAD")
    assert "opened" in result.lower()


@patch("subprocess.Popen")
def test_open_app_unknown_still_tries(mock_popen, tool):
    # Unknown apps are attempted anyway
    result = tool.open_app("someapp.exe")
    mock_popen.assert_called_once()


# ── send_notification ────────────────────────

@patch("winotify.Notification")
def test_send_notification_success(mock_notif, tool):
    mock_instance = MagicMock()
    mock_notif.return_value = mock_instance
    result = tool.send_notification("Test", "Hello JARVIS")
    assert "sent" in result.lower()


# ── get_system_info ──────────────────────────

def test_get_system_info_returns_data(tool):
    result = tool.get_system_info()
    assert "CPU" in result
    assert "RAM" in result
    assert "Disk" in result


def test_get_system_info_has_percentages(tool):
    result = tool.get_system_info()
    assert "%" in result
