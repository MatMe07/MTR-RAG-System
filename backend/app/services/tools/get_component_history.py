from .base import BaseTool, ToolResult, ToolError


class GetComponentHistoryTool(BaseTool):
    name = "get_component_history"
    description = "Получение истории изменений компонента"
    input_schema = {
        "type": "object",
        "properties": {
            "ksm_code": {"type": "string", "description": "Код КСМ компонента"},
            "limit": {
                "type": "integer",
                "default": 10,
                "description": "Количество записей",
            },
            "offset": {
                "type": "integer",
                "default": 0,
                "description": "Смещение для пагинации",
            },
        },
        "required": ["ksm_code"],
    }

    def validate_input(self, input_data: dict) -> bool:
        return bool(input_data.get("ksm_code"))

    async def execute(self, input_data: dict, dal) -> ToolResult:
        ksm_code = input_data["ksm_code"]
        limit = input_data.get("limit", 10)
        offset = input_data.get("offset", 0)

        result = await dal.get_component_history(ksm_code, limit, offset)

        if hasattr(result, "items"):
            items = [
                h.model_dump() if hasattr(h, "model_dump") else h for h in result.items
            ]
            data = {
                "items": items,
                "total_count": result.total_count,
                "offset": result.offset,
                "limit": result.limit,
                "has_more": result.has_more,
            }
        elif isinstance(result, list):
            data = {
                "items": result,
                "total_count": len(result),
                "offset": offset,
                "limit": limit,
                "has_more": False,
            }
        else:
            data = {
                "items": [],
                "total_count": 0,
                "offset": offset,
                "limit": limit,
                "has_more": False,
            }

        data["ksm_code"] = ksm_code
        return ToolResult(success=True, data=data)
