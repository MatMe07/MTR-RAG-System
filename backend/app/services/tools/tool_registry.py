from typing import Dict, List

from .base import BaseTool
from .search_catalog import SearchCatalogTool
from .get_component import GetComponentTool
from .search_by_passport import SearchByPassportTool
from .check_stock import CheckStockTool
from .get_low_stock_items import GetLowStockItemsTool
from .get_unused_stock import GetUnusedStockTool
from .get_unit_structure import GetUnitStructureTool
from .get_neighbors import GetNeighborsTool
from .is_installed_anywhere import IsInstalledAnywhereTool
from .check_compatibility import CheckCompatibilityTool
from .check_compatibility_batch import CheckCompatibilityBatchTool
from .search_norms import SearchNormsTool
from .get_component_history import GetComponentHistoryTool


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: Dict[str, BaseTool] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        tools = [
            SearchCatalogTool(),
            GetComponentTool(),
            SearchByPassportTool(),
            CheckStockTool(),
            GetLowStockItemsTool(),
            GetUnusedStockTool(),
            GetUnitStructureTool(),
            GetNeighborsTool(),
            IsInstalledAnywhereTool(),
            CheckCompatibilityTool(),
            CheckCompatibilityBatchTool(),
            SearchNormsTool(),
            GetComponentHistoryTool(),
        ]
        for tool in tools:
            self._tools[tool.name] = tool

    def register(self, tool: BaseTool) -> None:
        self._tools[tool.name] = tool

    def get_tool(self, name: str) -> BaseTool | None:
        return self._tools.get(name)

    def get_all_tools(self) -> Dict[str, BaseTool]:
        return dict(self._tools)

    def get_tool_descriptions_for_llm(self) -> List[dict]:
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.input_schema,
            }
            for tool in self._tools.values()
        ]
