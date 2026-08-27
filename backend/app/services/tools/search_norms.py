from .base import BaseTool, ToolResult, ToolError


class SearchNormsTool(BaseTool):
    name = "search_norms"
    description = "Поиск по нормативной базе (ГОСТ, ТУ, наименования)"
    input_schema = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Поисковый запрос"},
            "limit": {
                "type": "integer",
                "default": 5,
                "description": "Максимальное количество результатов",
            },
            "document_type": {
                "type": "string",
                "description": "Тип документа для фильтрации (опционально)",
            },
        },
        "required": ["query"],
    }

    def validate_input(self, input_data: dict) -> bool:
        return bool(input_data.get("query"))

    async def execute(self, input_data: dict, dal) -> ToolResult:
        query = input_data["query"]
        limit = input_data.get("limit", 5)
        document_type = input_data.get("document_type")

        results = await dal.search_norms(query, limit, document_type)

        if isinstance(results, list):
            items = results
        else:
            items = []

        return ToolResult(
            success=True,
            data={
                "items": items,
                "total_count": len(items),
                "query": query,
            },
        )
