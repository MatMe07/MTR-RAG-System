from .base import BaseTool, ToolResult, ToolError


class CheckStockTool(BaseTool):
    name = "check_stock"
    description = "Проверка остатков на складе по списку кодов КСМ"
    input_schema = {
        "type": "object",
        "properties": {
            "ksm_codes": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Список кодов КСМ для проверки",
            },
        },
        "required": ["ksm_codes"],
    }

    def validate_input(self, input_data: dict) -> bool:
        codes = input_data.get("ksm_codes")
        return isinstance(codes, list) and len(codes) > 0

    async def execute(self, input_data: dict, dal) -> ToolResult:
        ksm_codes = input_data["ksm_codes"]

        stock_data = await dal.check_stock(ksm_codes)

        return ToolResult(success=True, data=stock_data)
