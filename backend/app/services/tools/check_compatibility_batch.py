from .base import BaseTool, ToolResult, ToolError

MAX_BATCH_SIZE = 50


class CheckCompatibilityBatchTool(BaseTool):
    name = "check_compatibility_batch"
    description = "Пакетная проверка совместимости нескольких компонентов"
    input_schema = {
        "type": "object",
        "properties": {
            "ksm_codes": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Список кодов КСМ (макс. 50)",
            },
            "context": {
                "type": "object",
                "description": "CompatibilityContext",
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
        "required": ["ksm_codes", "context"],
    }

    def validate_input(self, input_data: dict) -> bool:
        codes = input_data.get("ksm_codes")
        if not isinstance(codes, list) or len(codes) == 0:
            return False
        ctx = input_data.get("context")
        return isinstance(ctx, dict) and "medium" in ctx and "pn" in ctx

    async def execute(self, input_data: dict, dal) -> ToolResult:
        ksm_codes = input_data["ksm_codes"]

        if len(ksm_codes) > MAX_BATCH_SIZE:
            return ToolResult(
                success=False,
                error=ToolError(
                    code="BATCH_TOO_LARGE",
                    message=f"Batch size {len(ksm_codes)} exceeds maximum {MAX_BATCH_SIZE}",
                ),
            )

        context = input_data["context"]
        results = []

        for code in ksm_codes:
            try:
                component = await dal.get_component(code)
                if component is None:
                    results.append({
                        "ksm_code": code,
                        "compatible": False,
                        "error": "Component not found",
                    })
                    continue

                compat = await dal.check_compatibility(code, context)
                if hasattr(compat, "model_dump"):
                    data = compat.model_dump()
                elif isinstance(compat, dict):
                    data = compat
                else:
                    data = {"compatible": bool(compat)}

                data["ksm_code"] = code
                results.append(data)
            except Exception as e:
                results.append({
                    "ksm_code": code,
                    "compatible": False,
                    "error": str(e),
                })

        return ToolResult(
            success=True,
            data={
                "results": results,
                "total_checked": len(results),
                "compatible_count": sum(1 for r in results if r.get("compatible")),
                "incompatible_count": sum(1 for r in results if not r.get("compatible")),
            },
        )
