"""Normalize Russian engineering wording and expose detected aliases."""

from __future__ import annotations

import csv
import re
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_ALIASES_PATH = REPO_ROOT / "data" / "domain" / "query_aliases.csv"


@lru_cache(maxsize=4)
def load_query_aliases(
    path: str = str(DEFAULT_ALIASES_PATH),
) -> tuple[dict[str, Any], ...]:
    with Path(path).open("r", encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file, delimiter=";"))

    aliases = []
    for row in rows:
        alias = (row.get("alias") or "").strip().casefold()
        canonical = (row.get("canonical") or "").strip().casefold()
        category = (row.get("category") or "").strip()
        if not alias or not canonical or not category:
            continue
        aliases.append(
            {
                "category": category,
                "canonical": canonical,
                "alias": alias,
                "automatic": (row.get("automatic") or "").casefold()
                == "true",
                "description": (row.get("description") or "").strip(),
            }
        )
    return tuple(aliases)


def _alias_pattern(alias: str) -> re.Pattern[str]:
    escaped = re.escape(alias).replace(r"\ ", r"\s+")
    prefix = r"(?<![\w])" if alias[0].isalnum() else ""
    suffix = r"(?![\w])" if alias[-1].isalnum() else ""
    return re.compile(prefix + escaped + suffix, re.IGNORECASE)


def _base_normalize(query: str) -> str:
    text = unicodedata.normalize("NFKC", query).casefold().replace("ё", "е")
    text = re.sub(
        r"(?P<left>\d+(?:[.,]\d+)?)\s*(?:x|х|×|на)\s*"
        r"(?P<right>\d+(?:[.,]\d+)?)",
        lambda match: (
            f"{match.group('left').replace(',', '.')}x"
            f"{match.group('right').replace(',', '.')}"
        ),
        text,
    )
    text = re.sub(r"(?<=\d)\s*(?:°|град(?:ус(?:а|ов)?)?\.?)", "", text)
    return " ".join(text.split())


def normalize_query(query: str) -> dict[str, Any]:
    normalized = _base_normalize(query)
    detected = []
    seen = set()

    aliases = sorted(
        load_query_aliases(),
        key=lambda row: len(row["alias"]),
        reverse=True,
    )
    for row in aliases:
        pattern = _alias_pattern(row["alias"])
        if not pattern.search(normalized):
            continue

        key = (row["category"], row["canonical"], row["alias"])
        if key not in seen:
            detected.append(dict(row))
            seen.add(key)

        if row["automatic"] and row["alias"] != row["canonical"]:
            normalized = pattern.sub(row["canonical"], normalized)

    normalized = " ".join(normalized.split())
    return {
        "original_text": query,
        "normalized_text": normalized,
        "detected_aliases": detected,
    }
