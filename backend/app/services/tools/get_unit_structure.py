from .base import BaseTool, ToolResult, ToolError


class GetUnitStructureTool(BaseTool):
    name = "get_unit_structure"
    description = "Получение состава участка ( inventory) с пагинацией"
    input_schema = {
        "type": "object",
        "properties": {
            "unit_code": {"type": "string", "description": "Код участка"},
            "limit": {
                "type": "integer",
                "default": 20,
                "description": "Количество элементов (макс. 100)",
            },
            "offset": {
                "type": "integer",
                "default": 0,
                "description": "Смещение для пагинации",
            },
        },
        "required": ["unit_code"],
    }

    def validate_input(self, input_data: dict) -> bool:
        return bool(input_data.get("unit_code"))

    async def execute(self, input_data: dict, dal) -> ToolResult:
        unit_code = input_data["unit_code"]
        limit = min(input_data.get("limit", 20), 100)
        offset = input_data.get("offset", 0)

        inventory = await dal.get_unit_inventory(unit_code)

        if hasattr(inventory, "components"):
            all_components = inventory.components
        elif isinstance(inventory, list):
            all_components = inventory
        else:
            return ToolResult(
                success=True,
                data={
                    "unit_code": unit_code,
                    "items": [],
                    "total_count": 0,
                    "offset": offset,
                    "limit": limit,
                    "has_more": False,
                },
            )

        total = len(all_components)
        paginated = all_components[offset : offset + limit]

        items = [
            comp.model_dump() if hasattr(comp, "model_dump") else comp
            for comp in paginated
        ]

        return ToolResult(
            success=True,
            data={
                "unit_code": unit_code,
                "items": items,
                "total_count": total,
                "offset": offset,
                "limit": limit,
                "has_more": (offset + limit) < total,
            },
        )
