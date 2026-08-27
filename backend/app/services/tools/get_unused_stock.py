from .base import BaseTool, ToolResult, ToolError


class GetUnusedStockTool(BaseTool):
    name = "get_unused_stock"
    description = (
        "Получение неиспользуемых складских позиций: "
        "объединяет данные графа (не установлены) и склада"
    )
    input_schema = {
        "type": "object",
        "properties": {
            "min_qty": {
                "type": "number",
                "default": 50,
                "description": "Минимальное количество на складе",
            },
        },
    }

    async def execute(self, input_data: dict, dal) -> ToolResult:
        min_qty = input_data.get("min_qty", 50)

        unused_items = await dal.get_unused_stock(min_qty)

        if hasattr(unused_items, "items"):
            result_items = [
                i.model_dump() if hasattr(i, "model_dump") else i
                for i in unused_items.items
            ]
        elif isinstance(unused_items, list):
            result_items = [
                i.model_dump() if hasattr(i, "model_dump") else i
                for i in unused_items
            ]
        else:
            result_items = []

        return ToolResult(
            success=True,
            data={
                "items": result_items,
                "total_count": len(result_items),
                "min_qty": min_qty,
            },
        )
