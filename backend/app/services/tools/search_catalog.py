from app.models.pydantic.schemas import SearchParams
from .base import BaseTool, ToolResult, ToolError


class SearchCatalogTool(BaseTool):
    name = "search_catalog"
    description = "Поиск компонентов в каталоге МТР по параметрам"
    input_schema = {
        "type": "object",
        "properties": {
            "params": {
                "type": "object",
                "description": "SearchParams: item_type, dn, pn, steel_grade, medium, angle, climate, gost_tu, mtr_code, ksm_code",
            },
            "detail_level": {
                "type": "string",
                "default": "basic",
                "enum": ["basic", "full"],
            },
        },
        "required": ["params"],
    }

    def validate_input(self, input_data: dict) -> bool:
        return isinstance(input_data.get("params"), dict)

    async def execute(self, input_data: dict, dal) -> ToolResult:
        params = SearchParams(**input_data["params"])
        detail_level = input_data.get("detail_level", "basic")

        result = await dal.search_catalog(params)

        if hasattr(result, "items"):
            items = [
                item.model_dump() if hasattr(item, "model_dump") else item
                for item in result.items
            ]
            data = {
                "items": items,
                "total_count": result.total_count,
                "offset": result.offset,
                "limit": result.limit,
                "has_more": result.has_more,
            }
        else:
            data = {"items": list(result) if result else [], "total_count": 0}

        return ToolResult(success=True, data=data)
