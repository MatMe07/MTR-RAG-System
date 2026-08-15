"""Stable JSON and CSV exports for search and agent results."""

from __future__ import annotations

import csv
import io
import json
from typing import Any


def result_to_json(result: dict[str, Any]) -> str:
    return json.dumps(result, ensure_ascii=False, indent=2, default=str)


def rows_to_csv(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return ""
    buffer = io.StringIO(newline="")
    fieldnames = list(rows[0])
    writer = csv.DictWriter(buffer, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow(
            {
                key: json.dumps(value, ensure_ascii=False)
                if isinstance(value, (dict, list))
                else value
                for key, value in row.items()
            }
        )
    return buffer.getvalue()


def agent_component_export_rows(result: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "ksm_code": item.get("ksm_code"),
            "mtr_code": item.get("mtr_code"),
            "name": item.get("name"),
            "item_type": item.get("item_type"),
            "quantity": item.get("quantity"),
            "status": item.get("status"),
            "detail": item.get("detail"),
            "source_id": item.get("source_id"),
        }
        for item in (result.get("agent") or {}).get("components") or []
        if isinstance(item, dict)
    ]


def candidate_export_rows(result: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "rank": item.get("rank"),
            "mtr_code": item.get("mtr_code"),
            "ksm_code": item.get("ksm_code"),
            "name": item.get("candidate_name"),
            "match_percent": item.get("match_percent"),
            "status": item.get("status"),
            "warnings": item.get("warnings") or [],
        }
        for item in result.get("candidates") or []
        if isinstance(item, dict)
    ]
