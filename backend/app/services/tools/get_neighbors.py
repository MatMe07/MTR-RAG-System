from .base import BaseTool, ToolResult, ToolError


class GetNeighborsTool(BaseTool):
    name = "get_neighbors"
    description = "Получение соседних компонентов по графу объекта"
    input_schema = {
        "type": "object",
        "properties": {
            "ksm_code": {"type": "string", "description": "Код КСМ исходного компонента"},
            "depth": {
                "type": "integer",
                "default": 1,
                "description": "Глубина поиска (1-5)",
            },
            "direction": {
                "type": "string",
                "default": "both",
                "enum": ["upstream", "downstream", "both"],
                "description": "Направление поиска в графе",
            },
        },
        "required": ["ksm_code"],
    }

    def validate_input(self, input_data: dict) -> bool:
        if not input_data.get("ksm_code"):
            return False
        depth = input_data.get("depth", 1)
        return isinstance(depth, int) and 1 <= depth <= 5

    async def execute(self, input_data: dict, dal) -> ToolResult:
        ksm_code = input_data["ksm_code"]
        depth = input_data.get("depth", 1)
        direction = input_data.get("direction", "both")

        neighbors = await dal.get_neighbors(ksm_code, depth, direction)

        if isinstance(neighbors, list):
            items = [
                n.model_dump() if hasattr(n, "model_dump") else n for n in neighbors
            ]
        else:
            items = []

        return ToolResult(
            success=True,
            data={
                "ksm_code": ksm_code,
                "depth": depth,
                "direction": direction,
                "neighbors": items,
                "total_count": len(items),
            },
        )
