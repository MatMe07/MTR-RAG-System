from .base import BaseTool, ToolResult, ToolError


class CheckCompatibilityTool(BaseTool):
    name = "check_compatibility"
    description = "Проверка совместимости компонента с заданным контекстом эксплуатации"
    input_schema = {
        "type": "object",
        "properties": {
            "ksm_code": {"type": "string", "description": "Код КСМ компонента"},
            "context": {
                "type": "object",
                "description": (
                    "CompatibilityContext: medium, pn, temperature, "
                    "climate, has_coating, gost_tu"
                ),
                "properties": {
                    "medium": {"type": "string"},
                    "pn": {"type": "number"},
                    "temperature": {"type": "number"},
                    "climate": {"type": "string"},
                    "has_coating": {"type": "boolean"},
                    "gost_tu": {"type": "string"},
                },
                "required": ["medium", "pn"],
            },
        },
        "required": ["ksm_code", "context"],
    }

    def validate_input(self, input_data: dict) -> bool:
        if not input_data.get("ksm_code"):
            return False
        ctx = input_data.get("context")
        return isinstance(ctx, dict) and "medium" in ctx and "pn" in ctx

    async def execute(self, input_data: dict, dal) -> ToolResult:
        ksm_code = input_data["ksm_code"]
        context = input_data["context"]

        component = await dal.get_component(ksm_code)
        if component is None:
            return ToolResult(
                success=False,
                error=ToolError(
                    code="NOT_FOUND",
                    message=f"Component '{ksm_code}' not found",
                ),
            )

        result = await dal.check_compatibility(ksm_code, context)

        if hasattr(result, "model_dump"):
            data = result.model_dump()
        elif isinstance(result, dict):
            data = result
        else:
            data = {"compatible": bool(result)}

        data["ksm_code"] = ksm_code

        return ToolResult(success=True, data=data)
