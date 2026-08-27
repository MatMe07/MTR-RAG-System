from .base import BaseTool, ToolResult, ToolError


class GetComponentTool(BaseTool):
    name = "get_component"
    description = "Получение карточки компонента по идентификатору (KSM/MTR/COMP)"
    input_schema = {
        "type": "object",
        "properties": {
            "identifier": {"type": "string", "description": "KSM, MTR или COMP код"},
            "detail_level": {
                "type": "string",
                "default": "basic",
                "enum": ["basic", "full"],
            },
        },
        "required": ["identifier"],
    }

    def validate_input(self, input_data: dict) -> bool:
        return bool(input_data.get("identifier"))

    async def execute(self, input_data: dict, dal) -> ToolResult:
        identifier = input_data["identifier"]
        detail_level = input_data.get("detail_level", "basic")

        component = await dal.get_component(identifier)

        if component is None:
            return ToolResult(
                success=False,
                error=ToolError(code="NOT_FOUND", message=f"Component '{identifier}' not found"),
            )

        data = (
            component.model_dump() if hasattr(component, "model_dump") else component
        )
        return ToolResult(success=True, data=data)
