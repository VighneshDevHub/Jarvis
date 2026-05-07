# src/jarvis/memory/short_term.py
# ============================================
# Short-term memory: keeps the last N messages
# in a Python list (lives in process memory).
# This is what gets sent to the LLM each turn
# so it has conversation context.
# ============================================

from typing import Any


class ShortTermMemory:
    """
    Sliding window of the last `max_messages` turns.
    Stores both normal {"role": ..., "content": ...} dicts
    AND raw assistant message objects (for tool calls).
    """

    def __init__(self, max_messages: int = 20):
        self.max_messages = max_messages
        self._messages: list[Any] = []

    def add(self, role: str, content: str):
        """Add a plain text message (user or assistant)."""
        self._messages.append({"role": role, "content": content})
        self._trim()

    def add_raw(self, message):
        """
        Add a raw assistant message object (used when the model
        returns a tool call — the object has .tool_calls on it).
        """
        self._messages.append(message)
        self._trim()

    def extend_raw(self, messages: list):
        """Add multiple raw tool-result messages at once."""
        self._messages.extend(messages)
        self._trim()

    def get_messages(self) -> list:
        """
        Return messages in the format the Groq API expects.
        Raw objects are passed through as-is; dicts are passed as-is.
        """
        return self._messages

    def clear(self):
        """Wipe the conversation history."""
        self._messages = []

    def _trim(self):
        """Keep only the last max_messages entries."""
        if len(self._messages) > self.max_messages:
            self._messages = self._messages[-self.max_messages:]

    def __len__(self):
        return len(self._messages)