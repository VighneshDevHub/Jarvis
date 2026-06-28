# src/jarvis/agent.py
# ============================================
# JARVIS Core Agent
#
# This is the brain. It:
#   1. Receives user input (text)
#   2. Sends it to Groq with relevant tool schemas
#   3. If Groq picks a tool → executes it via registry
#   4. Feeds the result back to Groq for a final reply
#   5. Saves everything to short-term memory
# ============================================

import json
import time

from groq import Groq
from loguru import logger

from .config import settings
from .memory.short_term import ShortTermMemory
from .tools.registry import registry

SYSTEM_PROMPT = """You are JARVIS, an AI assistant that controls a Windows laptop.

You have access to tools that let you:
- Run shell commands and open applications
- Read and write files
- Browse the web and take screenshots
- Search the web for information
- Run git commands and developer tools
- Send desktop notifications and get system info
- Listen to voice input and speak replies

STRICT RULES:
- ALWAYS use tools to complete tasks — never describe what you would do.
- NEVER output raw function call syntax like open_app{"app_name": "x"} — use the actual tool.
- For greetings or simple questions — reply with plain text only, NO tool calls.
- Only use send_notification when explicitly asked.
- Always show the FULL tool result — never summarise or shorten it.
- When asked to search AND open — use get_top_url then open_url.
- For multi-step tasks — execute each step one at a time using tools.
- NEVER accept, store, or use passwords or credentials.
- If login is needed — open the login page and tell user to enter credentials manually.
- For multi-step tasks: execute ONE tool at a time.
  After each tool result, decide the next single action.
  Never plan multiple steps — just do the next one.
"""

# Keywords that map to specific tool groups
# This lets us send only relevant tools per request
# reducing token usage and improving tool call accuracy
TOOL_GROUPS = {
    "system": ["run_command", "open_app", "list_files", "read_file",
                "write_file", "send_notification", "get_system_info"],
    "browser": ["open_url", "scrape_text", "take_screenshot",
                 "click_element", "fill_form", "get_page_title"],
    "search":  ["web_search", "news_search", "get_top_url", "search_and_summarise"],
    "code":    ["git_command", "run_tests", "open_in_vscode",
                "pip_install", "get_python_info", "run_python_file"],
    "voice":   ["listen_once", "speak", "set_voice_speed"],
}

# Keywords that trigger each group
GROUP_TRIGGERS = {
    "system": ["open", "run", "list", "read", "write", "file", "folder",
                "directory", "create", "delete", "move", "copy", "app",
                "application", "notepad", "chrome", "notify", "notification",
                "cpu", "ram", "memory", "disk", "system", "command", "mkdir",
                "execute", "launch", "start", "kill", "process"],
    "browser": ["browse", "browser", "website", "url", "http", "screenshot",
                 "click", "form", "page", "tab", "chrome", "firefox", "web",
                 "scrape", "visit", "navigate", "goto", "github", "youtube"],
    "search":  ["search", "find", "look up", "google", "news", "latest",
                 "what is", "who is", "how to", "tutorial", "learn",
                 "summarise", "summarize", "information", "tell me about"],
    "code":    ["code", "vscode", "vs code", "git", "commit", "push", "pull",
                "test", "pytest", "pip", "install", "python", "script",
                "repository", "branch", "langchain", "django", "flask",
                "function", "class", "import", "package", "library"],
    "voice":   ["speak", "say", "listen", "voice", "hear", "microphone",
                "talk", "tell me", "read aloud"],
}


def _get_relevant_tools(user_input: str) -> list:
    """
    Return only the tool schemas relevant to this message.
    This reduces tokens and improves tool calling accuracy.
    Always includes system tools as a baseline.
    """
    text = user_input.lower()
    active_groups = {"system"}  # always include system tools

    for group, triggers in GROUP_TRIGGERS.items():
        if any(trigger in text for trigger in triggers):
            active_groups.add(group)

    # Collect tool names for active groups
    active_tool_names = set()
    for group in active_groups:
        active_tool_names.update(TOOL_GROUPS.get(group, []))

    # Filter schemas to only active tools
    all_schemas = registry.get_schemas()
    relevant = [s for s in all_schemas
                if s["function"]["name"] in active_tool_names]

    logger.debug(f"Active groups: {active_groups} → {len(relevant)} tools")
    return relevant


class Agent:
    def __init__(self):
        self.client = Groq(api_key=settings.groq_api_key)
        self.memory = ShortTermMemory(max_messages=settings.jarvis_max_history)
        logger.info(f"JARVIS agent initialised | model={settings.jarvis_model}")

    def chat(self, user_input: str) -> str:
        """
        Process one user message and return JARVIS reply.
        Called by every interface (CLI, GUI, tray, API).
        """
        logger.info(f"User: {user_input}")
        self.memory.add("user", user_input)

        # Get only relevant tools for this message
        relevant_tools = _get_relevant_tools(user_input)

        # Build message list
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        messages += self.memory.get_messages()

        # --- First LLM call ---
        try:
            response = self._call_api(
                messages=messages,
                tools=relevant_tools,
                tool_choice="auto",
            )
        except Exception as e:
            logger.error(f"Groq API error (call 1): {e}")
            return f"Sorry, I encountered an error with the AI: {e}"

        msg = response.choices[0].message

        # --- No tool call → return text directly ---
        if not msg.tool_calls:
            reply = msg.content or "(no response)"
            # Check if model accidentally output tool syntax as text
            if self._looks_like_tool_syntax(reply):
                logger.warning("Model output tool syntax as text — retrying with reminder")
                return self._retry_with_reminder(user_input, relevant_tools)
            self.memory.add("assistant", reply)
            logger.info(f"JARVIS (direct): {reply[:80]}...")
            return reply

        # --- Tool call(s) → execute each one ---
        self.memory.add_raw(msg)

        tool_results = []
        for tool_call in msg.tool_calls:
            fn_name = tool_call.function.name
            raw_args = tool_call.function.arguments
            fn_args = json.loads(raw_args) if raw_args and raw_args.strip() else {}

            logger.info(f"Tool → {fn_name}({fn_args})")
            result = registry.execute(fn_name, **(fn_args or {}))
            logger.info(f"Result → {result[:120]}")

            tool_results.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result,
            })

        self.memory.extend_raw(tool_results)

        # --- Second LLM call → natural language reply ---
        final_messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        final_messages += self.memory.get_messages()

        try:
            final_response = self._call_api(
                messages=final_messages,
                tools=None,
            )
            reply = final_response.choices[0].message.content or "(no response)"
        except Exception as e:
            logger.error(f"Groq API error (call 2): {e}")
            reply = "I performed the task, but had trouble writing a summary."

        self.memory.add("assistant", reply)
        logger.info(f"JARVIS: {reply[:80]}...")
        return reply

    def _call_api(self, messages, tools=None, tool_choice="auto"):
        """Make a Groq API call with retry on rate limit."""
        kwargs = {
            "model": settings.jarvis_model,
            "messages": messages,
            "max_tokens": settings.jarvis_max_tokens,
            "parallel_tool_calls": False,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = tool_choice

        try:
            return self.client.chat.completions.create(**kwargs)
        except Exception as e:
            # Rate limit — wait and retry once
            if "429" in str(e):
                logger.warning("Rate limit hit — waiting 15s and retrying...")
                time.sleep(15)
                return self.client.chat.completions.create(**kwargs)
            raise

    def _looks_like_tool_syntax(self, text: str) -> bool:
        """Detect if the model output raw tool syntax instead of calling the tool."""
        indicators = [
            '{"app_name"', '{"command"', '{"url"', '{"query"',
            '{"filepath"', '{"path"', 'open_app{', 'run_command{',
            '"type": "function"', '<function=',
        ]
        return any(ind in text for ind in indicators)

    def _retry_with_reminder(self, user_input: str, tools: list) -> str:
        """Retry with a stronger reminder to use tool calling."""
        reminder = (
            "IMPORTANT: You must use the tool calling mechanism to execute actions. "
            "Do NOT output function call syntax as text. "
            "Use the tools provided to complete this task: " + user_input
        )
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": reminder},
        ]
        try:
            response = self._call_api(messages=messages, tools=tools, tool_choice="required")
            msg = response.choices[0].message
            if msg.tool_calls:
                # Execute the tool
                tool_call = msg.tool_calls[0]
                fn_name = tool_call.function.name
                raw_args = tool_call.function.arguments
                fn_args = json.loads(raw_args) if raw_args and raw_args.strip() else {}
                result = registry.execute(fn_name, **(fn_args or {}))
                logger.info(f"Retry tool result: {result[:100]}")
                return f"Done: {result}"
            return msg.content or "(no response)"
        except Exception as e:
            logger.error(f"Retry failed: {e}")
            return f"Error: {e}"

    def reset(self):
        """Clear conversation history."""
        self.memory.clear()
        logger.info("Memory cleared.")
        return "Memory cleared."