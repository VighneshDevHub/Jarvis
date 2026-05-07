# src/jarvis/tools/registry.py
# ============================================
# Tool Registry — the central dispatcher.
#
# Every tool module registers itself here.
# The agent asks the registry for:
#   1. All tool schemas (sent to the LLM)
#   2. Execution of a specific tool by name
#
# To add a new tool: create a new class with
# get_schemas() and your methods, then call
# registry.register(YourTool()) in main.py.
# Nothing else needs to change.
# ============================================

from loguru import logger


class ToolRegistry:
    def __init__(self):
        # Maps tool function name → (instance, method_name)
        self._tools: dict[str, tuple] = {}
        # List of JSON schemas sent to the LLM
        self._schemas: list[dict] = []

    def register(self, tool_instance):
        """
        Register all methods of a tool instance.
        The tool must implement get_schemas() returning
        a dict of {function_name: json_schema}.
        """
        schemas = tool_instance.get_schemas()
        for name, schema in schemas.items():
            self._tools[name] = (tool_instance, name)
            self._schemas.append(schema)
            logger.debug(f"Registered tool: {name}")

    def get_schemas(self) -> list[dict]:
        """Return all schemas — passed to the Groq API."""
        return self._schemas

    def execute(self, name: str, **kwargs) -> str:
        """
        Execute a tool by function name.
        Always returns a string — never raises.
        """
        if name not in self._tools:
            logger.warning(f"Unknown tool called: {name}")
            return f"Error: unknown tool '{name}'"

        instance, method_name = self._tools[name]
        fn = getattr(instance, method_name)

        try:
            result = fn(**kwargs)
            return str(result)
        except Exception as e:
            logger.error(f"Tool '{name}' crashed: {e}")
            return f"Error running {name}: {str(e)}"

    def list_tools(self) -> list[str]:
        """Return names of all registered tools (for debugging)."""
        return list(self._tools.keys())


# Global singleton — import this everywhere
registry = ToolRegistry()