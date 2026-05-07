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

SYSTEM_PROMPT = """You are JARVIS, an AI assistant that controls a Windows laptop.

You have access to tools that let you:
- Run shell commands
- Open applications
- Read and write files
- Search the web
- Send desktop notifications
- Get system information

Guidelines:
- Use tools to complete tasks — don't just describe what you would do.
- Be concise in your replies. After using a tool, briefly explain what you did and the result.
- If a task needs multiple steps, do them one by one.
- For greetings, questions, or conversations — reply with plain text. NO tool calls.
- Only use send_notification when the user explicitly asks for a notification or reminder.
- If you cannot do something with the available tools, say so clearly and explain why.
- Always prefer the most specific tool for the job.
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
        response = self.client.chat.completions.create(
            model=settings.jarvis_model,
            messages=messages,
            tools=registry.get_schemas(),
            tool_choice="auto",
            max_tokens=settings.jarvis_max_tokens,
        )

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
            fn_args = json.loads(tool_call.function.arguments)

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

        final_response = self.client.chat.completions.create(
            model=settings.jarvis_model,
            messages=final_messages,
            max_tokens=settings.jarvis_max_tokens,
        )

        reply = final_response.choices[0].message.content or "(no response)"
        self.memory.add("assistant", reply)
        logger.info(f"JARVIS: {reply[:80]}...")
        return reply

    def reset(self):
        """Clear conversation history."""
        self.memory.clear()
        logger.info("Memory cleared.")
        return "Memory cleared."