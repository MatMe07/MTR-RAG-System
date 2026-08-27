from app.core.logging import get_logger
from .base import ToolResult, ToolError
from .tool_registry import ToolRegistry

log = get_logger("tools.executor")


class ToolExecutor:
    def __init__(self, dal, registry: ToolRegistry | None = None) -> None:
        self._dal = dal
        self._registry = registry or ToolRegistry()

    async def execute_tool(self, tool_name: str, input_data: dict) -> ToolResult:
        tool = self._registry.get_tool(tool_name)
        if tool is None:
            return ToolResult(
                success=False,
                error=ToolError(
                    code="NOT_FOUND",
                    message=f"Tool '{tool_name}' not found",
                ),
            )

        log.info(
            "tool_start",
            tool=tool_name,
            input_keys=list(input_data.keys()) if isinstance(input_data, dict) else [],
        )

        result = await tool.run(input_data, self._dal)

        if result.error:
            log.warn(
                "tool_error",
                tool=tool_name,
                error_code=result.error.code,
                error_msg=result.error.message,
                duration_ms=result.duration_ms,
            )
        else:
            log.info(
                "tool_done",
                tool=tool_name,
                duration_ms=result.duration_ms,
            )

        return result
