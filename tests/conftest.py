# tests/conftest.py
# ============================================
# Pytest configuration and shared fixtures
# ============================================

import pytest
import os
from pathlib import Path


def pytest_configure(config):
    """Set up test environment."""
    # Set a dummy API key so config.py doesn't crash during tests
    os.environ.setdefault("GROQ_API_KEY", "test_key_for_testing_only")


@pytest.fixture(scope="session")
def test_data_dir(tmp_path_factory):
    """Shared temp directory for all tests in the session."""
    return tmp_path_factory.mktemp("jarvis_test_data")


@pytest.fixture
def sample_text_file(tmp_path):
    """A sample text file for read/write tests."""
    f = tmp_path / "sample.txt"
    f.write_text("This is sample content for JARVIS tests.\nLine 2.\nLine 3.")
    return f


@pytest.fixture
def sample_python_file(tmp_path):
    """A sample Python file for code tool tests."""
    f = tmp_path / "sample.py"
    f.write_text('print("Hello from JARVIS test")\n')
    return f
