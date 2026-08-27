from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any
import time


@dataclass
class ToolError:
    code: str  # NOT_FOUND, INVALID_PARAMS, DAL_ERROR, TIMEOUT, BATCH_TOO_LARGE
    message: str
    details: dict = field(default_factory=dict)


@dataclass
class ToolResult:
    success: bool
    data: Any = None
    error: ToolError | None = None
    duration_ms: int = 0


class BaseTool(ABC):
    name: str = ""
    description: str = ""
    input_schema: dict = {}
    output_schema: dict = {}

    @abstractmethod
    async def execute(self, input_data: dict, dal) -> ToolResult:
        pass

    def validate_input(self, input_data: dict) -> bool:
        return True

    async def run(self, input_data: dict, dal) -> ToolResult:
        start = time.time()
        if not self.validate_input(input_data):
            return ToolResult(
                success=False,
                error=ToolError(code="INVALID_PARAMS", message="Invalid input"),
            )
        try:
            result = await self.execute(input_data, dal)
            result.duration_ms = int((time.time() - start) * 1000)
            return result
        except Exception as e:
            return ToolResult(
                success=False,
                error=ToolError(code="DAL_ERROR", message=str(e)),
                duration_ms=int((time.time() - start) * 1000),
            )
