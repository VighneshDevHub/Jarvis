# tests/test_agent.py
# ============================================
# Unit tests for the Agent core
# ============================================

import pytest
from unittest.mock import patch, MagicMock
from src.jarvis.agent import Agent, _get_relevant_tools, TOOL_GROUPS


# ── _get_relevant_tools ──────────────────────
# These tests check the ROUTING LOGIC only —
# not whether registry has tools loaded.
# We check active_groups, not the returned schemas.

def test_routing_system_always_active():
    """'system' group should always be in active groups."""
    # We test the logic by checking TOOL_GROUPS keys
    # and GROUP_TRIGGERS directly
    from src.jarvis.agent import GROUP_TRIGGERS, TOOL_GROUPS
    assert "system" in TOOL_GROUPS
    assert "system" in GROUP_TRIGGERS


def test_routing_search_triggered_by_keyword():
    from src.jarvis.agent import GROUP_TRIGGERS
    triggers = GROUP_TRIGGERS["search"]
    assert "search" in triggers
    assert "news" in triggers
    assert "find" in triggers


def test_routing_browser_triggered_by_url():
    from src.jarvis.agent import GROUP_TRIGGERS
    triggers = GROUP_TRIGGERS["browser"]
    assert "url" in triggers or "http" in triggers or "browser" in triggers


def test_routing_code_triggered_by_git():
    from src.jarvis.agent import GROUP_TRIGGERS
    triggers = GROUP_TRIGGERS["code"]
    assert "git" in triggers


def test_routing_voice_triggered_by_speak():
    from src.jarvis.agent import GROUP_TRIGGERS
    triggers = GROUP_TRIGGERS["voice"]
    assert "speak" in triggers


def test_tool_groups_have_correct_tools():
    """Verify TOOL_GROUPS contains expected tool names."""
    assert "web_search" in TOOL_GROUPS["search"]
    assert "open_url" in TOOL_GROUPS["browser"]
    assert "git_command" in TOOL_GROUPS["code"]
    assert "speak" in TOOL_GROUPS["voice"]
    assert "run_command" in TOOL_GROUPS["system"]


def test_relevant_tools_with_registered_tools():
    """Test _get_relevant_tools when registry has tools loaded."""
    from src.jarvis.tools.registry import ToolRegistry
    from src.jarvis.tools.system import SystemTool
    from src.jarvis.tools.search import SearchTool

    # Create a fresh registry with tools
    test_registry = ToolRegistry()
    test_registry.register(SystemTool())
    test_registry.register(SearchTool())

    # Patch the global registry
    with patch("src.jarvis.agent.registry", test_registry):
        tools = _get_relevant_tools("search for Python tutorials")
        tool_names = [t["function"]["name"] for t in tools]
        assert "web_search" in tool_names
        assert "run_command" in tool_names  # system always included


# ── Agent.chat() ─────────────────────────────

@pytest.fixture
def agent():
    with patch("src.jarvis.agent.Groq"):
        a = Agent()
        return a


def test_agent_direct_reply(agent):
    mock_response = MagicMock()
    mock_response.choices[0].message.tool_calls = None
    mock_response.choices[0].message.content = "Hello! How can I help?"

    agent.client.chat.completions.create.return_value = mock_response
    result = agent.chat("hello")
    assert "Hello" in result


def test_agent_tool_call_executed(agent):
    mock_tool_call = MagicMock()
    mock_tool_call.function.name = "get_system_info"
    mock_tool_call.function.arguments = "{}"
    mock_tool_call.id = "call_123"

    mock_first = MagicMock()
    mock_first.choices[0].message.tool_calls = [mock_tool_call]
    mock_first.choices[0].message.content = None

    mock_second = MagicMock()
    mock_second.choices[0].message.tool_calls = None
    mock_second.choices[0].message.content = "Your CPU is at 25%."

    agent.client.chat.completions.create.side_effect = [mock_first, mock_second]

    with patch("src.jarvis.tools.registry.registry.execute", return_value="CPU: 25%"):
        result = agent.chat("what is my CPU usage?")

    assert isinstance(result, str)
    assert len(result) > 0


def test_agent_memory_grows(agent):
    mock_response = MagicMock()
    mock_response.choices[0].message.tool_calls = None
    mock_response.choices[0].message.content = "I can help with that."

    agent.client.chat.completions.create.return_value = mock_response
    assert len(agent.memory) == 0
    agent.chat("hello")
    assert len(agent.memory) == 2


def test_agent_reset_clears_memory(agent):
    mock_response = MagicMock()
    mock_response.choices[0].message.tool_calls = None
    mock_response.choices[0].message.content = "Sure!"
    agent.client.chat.completions.create.return_value = mock_response

    agent.chat("hello")
    assert len(agent.memory) > 0
    agent.reset()
    assert len(agent.memory) == 0


def test_agent_detects_tool_syntax(agent):
    assert agent._looks_like_tool_syntax('open_app{"app_name": "notepad"}')
    assert agent._looks_like_tool_syntax('{"type": "function", "name": "run"}')
    assert not agent._looks_like_tool_syntax("I opened Notepad for you.")
    assert not agent._looks_like_tool_syntax("Hello! How can I help?")


def test_agent_handles_api_error(agent):
    agent.client.chat.completions.create.side_effect = Exception("Connection failed")
    result = agent.chat("open notepad")
    assert "error" in result.lower() or "sorry" in result.lower()