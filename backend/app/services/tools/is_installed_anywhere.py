from .base import BaseTool, ToolResult, ToolError


class IsInstalledAnywhereTool(BaseTool):
    name = "is_installed_anywhere"
    description = "Проверка, установлен ли компонент (КСМ) хотя бы на одном участке"
    input_schema = {
        "type": "object",
        "properties": {
            "ksm_code": {"type": "string", "description": "Код КСМ для проверки"},
        },
        "required": ["ksm_code"],
    }

    def validate_input(self, input_data: dict) -> bool:
        return bool(input_data.get("ksm_code"))

    async def execute(self, input_data: dict, dal) -> ToolResult:
        ksm_code = input_data["ksm_code"]

        is_installed = await dal.is_installed_anywhere(ksm_code)

        return ToolResult(
            success=True,
            data={
                "ksm_code": ksm_code,
                "is_installed": bool(is_installed),
            },
        )
