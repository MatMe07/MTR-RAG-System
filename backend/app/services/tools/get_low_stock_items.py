from .base import BaseTool, ToolResult, ToolError


class GetLowStockItemsTool(BaseTool):
    name = "get_low_stock_items"
    description = "Получение позиций с низкими остатками на складе"
    input_schema = {
        "type": "object",
        "properties": {
            "threshold": {
                "type": "number",
                "default": 2.0,
                "description": "Порог остатка (меньше которого считается низким)",
            },
            "unit_code": {
                "type": "string",
                "description": "Код участка для фильтрации (опционально)",
            },
        },
    }

    async def execute(self, input_data: dict, dal) -> ToolResult:
        threshold = input_data.get("threshold", 2.0)
        unit_code = input_data.get("unit_code")

        if unit_code:
            unit_inventory = await dal.get_unit_inventory(unit_code)
            if hasattr(unit_inventory, "components"):
                all_components = unit_inventory.components
            else:
                all_components = unit_inventory if isinstance(unit_inventory, list) else []

            low_stock = []
            for comp in all_components:
                stock_qty = 0.0
                if hasattr(comp, "stock") and comp.stock:
                    stock_qty = comp.stock.quantity or 0.0
                elif isinstance(comp, dict):
                    stock_qty = (comp.get("stock") or {}).get("quantity", 0.0)

                if stock_qty < threshold:
                    item = (
                        comp.model_dump() if hasattr(comp, "model_dump") else comp
                    )
                    low_stock.append(item)

            return ToolResult(
                success=True,
                data={
                    "items": low_stock,
                    "total_count": len(low_stock),
                    "threshold": threshold,
                    "unit_code": unit_code,
                },
            )

        items = await dal.get_low_stock_items(threshold)

        if hasattr(items, "items"):
            result_items = [
                i.model_dump() if hasattr(i, "model_dump") else i for i in items.items
            ]
        elif isinstance(items, list):
            result_items = [
                i.model_dump() if hasattr(i, "model_dump") else i for i in items
            ]
        else:
            result_items = []

        return ToolResult(
            success=True,
            data={
                "items": result_items,
                "total_count": len(result_items),
                "threshold": threshold,
            },
        )
