from .base import BaseTool, ToolResult, ToolError


WEIGHTS = {
    "dn": 0.30,
    "pn": 0.25,
    "material": 0.20,
    "angle": 0.15,
    "medium": 0.10,
}


class SearchByPassportTool(BaseTool):
    name = "search_by_passport"
    description = (
        "Поиск по паспорту: извлекает параметры из документа и "
        "ищет кандидатов в каталоге по каждому параметру с confidence > 0.6"
    )
    input_schema = {
        "type": "object",
        "properties": {
            "document_id": {
                "type": "string",
                "description": "ID загруженного паспорта/документа",
            },
        },
        "required": ["document_id"],
    }

    def validate_input(self, input_data: dict) -> bool:
        return bool(input_data.get("document_id"))

    async def execute(self, input_data: dict, dal) -> ToolResult:
        document_id = input_data["document_id"]

        passport_data = await dal.get_passport_params(document_id)
        if not passport_data:
            return ToolResult(
                success=False,
                error=ToolError(
                    code="NOT_FOUND",
                    message=f"No extracted params for document '{document_id}'",
                ),
            )

        params = passport_data.get("params", [])
        if not params:
            return ToolResult(
                success=False,
                error=ToolError(
                    code="NOT_FOUND",
                    message=f"No params extracted from document '{document_id}'",
                ),
            )

        high_confidence_params = [
            p for p in params if (p.get("confidence") or 0) > 0.6
        ]
        if not high_confidence_params:
            high_confidence_params = params

        param_map: dict[str, str] = {}
        for p in high_confidence_params:
            field_name = (p.get("field_name") or "").lower()
            normalized = p.get("normalized_value") or p.get("raw_value") or ""
            if field_name and normalized:
                param_map[field_name] = normalized

        from app.models.pydantic.schemas import SearchParams

        search_params = SearchParams()
        if "dn" in param_map:
            try:
                search_params.dn = int(float(param_map["dn"]))
            except (ValueError, TypeError):
                pass
        if "pn" in param_map:
            try:
                search_params.pn = float(param_map["pn"])
            except (ValueError, TypeError):
                pass
        if "material" in param_map or "steel_grade" in param_map:
            search_params.steel_grade = param_map.get("material") or param_map.get("steel_grade")
        if "angle" in param_map:
            try:
                search_params.angle = int(float(param_map["angle"]))
            except (ValueError, TypeError):
                pass
        if "medium" in param_map:
            search_params.medium = param_map["medium"]
        if "item_type" in param_map:
            search_params.item_type = param_map["item_type"]

        catalog_result = await dal.search_catalog(search_params)

        if hasattr(catalog_result, "items"):
            candidates = [
                item.model_dump() if hasattr(item, "model_dump") else item
                for item in catalog_result.items
            ]
        else:
            candidates = list(catalog_result) if catalog_result else []

        weighted_results = []
        for cand in candidates:
            score = _compute_weighted_score(cand, param_map)
            weighted_results.append({**cand, "weighted_score": score})

        weighted_results.sort(key=lambda x: x["weighted_score"], reverse=True)

        return ToolResult(
            success=True,
            data={
                "extracted_params": params,
                "high_confidence_params": high_confidence_params,
                "candidates": weighted_results[:20],
                "total_found": len(weighted_results),
            },
        )


def _compute_weighted_score(candidate: dict, param_map: dict) -> float:
    total_weight = 0.0
    matched_weight = 0.0

    attrs = candidate.get("attributes") or {}
    if isinstance(attrs, dict):
        dn_val = attrs.get("dn")
        pn_val = attrs.get("pn")
        material_val = attrs.get("steel_grade") or attrs.get("material")
        angle_val = attrs.get("angle")
    else:
        dn_val = pn_val = material_val = angle_val = None

    for key, weight in WEIGHTS.items():
        if key not in param_map:
            continue
        total_weight += weight
        raw_wanted = param_map[key]

        if key == "dn":
            try:
                wanted = float(raw_wanted)
                if dn_val is not None and abs(float(dn_val) - wanted) <= wanted * 0.1:
                    matched_weight += weight
            except (ValueError, TypeError):
                pass
        elif key == "pn":
            try:
                wanted = float(raw_wanted)
                if pn_val is not None and abs(float(pn_val) - wanted) <= wanted * 0.1:
                    matched_weight += weight
            except (ValueError, TypeError):
                pass
        elif key == "material":
            if material_val and str(material_val).lower() == str(raw_wanted).lower():
                matched_weight += weight
        elif key == "angle":
            try:
                wanted = float(raw_wanted)
                if angle_val is not None and float(angle_val) == wanted:
                    matched_weight += weight
            except (ValueError, TypeError):
                pass
        elif key == "medium":
            medium_val = attrs.get("medium") or ""
            if str(medium_val).lower() == str(raw_wanted).lower():
                matched_weight += weight

    return matched_weight / total_weight if total_weight > 0 else 0.0
