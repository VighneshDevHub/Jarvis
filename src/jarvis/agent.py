# src/jarvis/agent.py
# ============================================
# JARVIS Core Agent
#
# This is the brain. It:
#   1. Receives user input (text)
#   2. Sends it to Groq with all tool schemas
#   3. If Groq picks a tool → executes it via registry
#   4. Feeds the result back to Groq for a final reply
#   5. Saves everything to short-term memory
#
# The agent never does I/O directly.
# All I/O happens in the interface layer (cli.py, gui.py, etc.)
# ============================================

import json

from groq import Groq
from loguru import logger

from .config import settings
from .memory.short_term import ShortTermMemory
from .tools.registry import registry

SYSTEM_PROMPT = """You are JARVIS, a professional AI automation assistant for Windows.

CORE PRINCIPLES:
1. Use tools immediately to fulfill requests. If you need information, use a tool to get it.
2. NEVER use pseudo-XML tags like <function> or tags like [TOOL_CALL].
3. When using tools, the Groq API will handle the formatting. You just need to select the tool and provide parameters.
4. After a tool returns a result, provide a brief, natural summary to the user.
5. If a task requires multiple steps (e.g., create folder, then create file), do them one by one.

TOOL GUIDELINES:
- run_command: Use for shell operations.
- open_app: Use for launching Windows applications.
- list_files / read_file / write_file: Use for file system operations. Prefer relative paths to the current directory unless absolute paths are necessary.
- search_web: Use for real-time information.
- send_notification: Only use if explicitly asked.
- get_system_info: Use for CPU, RAM, etc.

CONVERSATION:
- For greetings or general questions, reply with plain text.
- Be concise, helpful, and professional.
"""


class Agent:
    def __init__(self):
        self.client = Groq(api_key=settings.groq_api_key)
        self.memory = ShortTermMemory(max_messages=settings.jarvis_max_history)
        logger.info(f"JARVIS agent initialised | model={settings.jarvis_model}")

    def chat(self, user_input: str) -> str:
        """
        Process one user message and return JARVIS's reply.
        This is the main entry point called by every interface.
        """
        logger.info(f"User: {user_input}")
        self.memory.add("user", user_input)

        # Build the full message list: system prompt + history
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        messages += self.memory.get_messages()

        # --- First LLM call ---
        # The model reads the message + tool list and decides:
        # (a) answer directly, or (b) call one or more tools
        try:
            response = self.client.chat.completions.create(
                model=settings.jarvis_model,
                messages=messages,
                tools=registry.get_schemas(),
                tool_choice="auto",
                max_tokens=settings.jarvis_max_tokens,
                parallel_tool_calls=False,   # ← ADD THIS

            )
        except Exception as e:
            logger.error(f"Groq API error (call 1): {e}")
            if "tool_use_failed" in str(e):
                return (
                    "I'm sorry, I had trouble formatting the tool call correctly. "
                    "Please try rephrasing your request or ask me to do it one step at a time."
                )
            return f"Sorry, I encountered an error with the AI: {str(e)}"

        msg = response.choices[0].message

        # --- No tool call → return text directly ---
        if not msg.tool_calls:
            reply = msg.content or "(no response)"
            self.memory.add("assistant", reply)
            logger.info(f"JARVIS (direct): {reply[:80]}...")
            return reply

        # --- Tool call(s) → execute each one ---
        # Save the assistant's tool-call message to memory
        self.memory.add_raw(msg)

        tool_results = []
        for tool_call in msg.tool_calls:
            fn_name = tool_call.function.name
            raw_args = tool_call.function.arguments
            
            try:
                fn_args = json.loads(raw_args) if raw_args and raw_args.strip() else {}
                # Handle cases where LLM sends "null" or json.loads returns None
                if fn_args is None:
                    fn_args = {}
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse tool arguments: {raw_args}")
                fn_args = {}
            
            logger.info(f"Tool → {fn_name}({fn_args})")

            # Execute via registry (never raises — always returns string)
            result = registry.execute(fn_name, **fn_args)

            logger.info(f"Result → {result[:120]}")

            tool_results.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result,
            })

        # Save tool results to memory
        self.memory.extend_raw(tool_results)

        # --- Second LLM call ---
        # Now the model knows what happened and writes a natural reply
        final_messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        final_messages += self.memory.get_messages()

        try:
            final_response = self.client.chat.completions.create(
                model=settings.jarvis_model,
                messages=final_messages,
                max_tokens=settings.jarvis_max_tokens,
            )
        except Exception as e:
            logger.error(f"Groq API error (call 2): {e}")
            return f"I performed the task, but had trouble writing a summary: {str(e)}"

        reply = final_response.choices[0].message.content or "(no response)"
        self.memory.add("assistant", reply)
        logger.info(f"JARVIS: {reply[:80]}...")
        return reply

    def reset(self):
        """Clear conversation history."""
        self.memory.clear()
        logger.info("Memory cleared.")
        return "Memory cleared."