# repository/providers/norms_fragments.py
"""Построение нормативных фрагментов из общего источника (нормативная матрица
+ выдержка ЛНД). Используется провайдером норм для индексации в Qdrant.
"""

import re
from pathlib import Path
from typing import Any, Dict, List, Optional


def _project_root(depth: int) -> Path:
    return Path(__file__).parents[depth]


def _regulation_path() -> Path:
    for base in [_project_root(6), Path.cwd()]:
        p = base / "data" / "regulation" / "regulation_matrix.json"
        if p.exists():
            return p
    return Path.cwd() / "data" / "regulation" / "regulation_matrix.json"


def _lnd_path() -> Path:
    for base in [_project_root(6), Path.cwd()]:
        for p in [
            base / "data" / "sample" / "documents" / "lnd_extract.md",
            Path.cwd() / "data" / "sample" / "documents" / "lnd_extract.md",
        ]:
            if p.exists():
                return p
    return _project_root(6) / "data" / "sample" / "documents" / "lnd_extract.md"


def _load_regulation() -> Dict[str, Any]:
    import json

    path = _regulation_path()
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def build_norm_fragments(regulation: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """Фрагменты нормативов: важные ограничения, профили сред, заменённые
    стандарты (из regulation_matrix.json) и строки лнд_extract.md."""
    reg = regulation if regulation is not None else _load_regulation()
    fragments: List[Dict[str, Any]] = []

    for i, lim in enumerate(reg.get("important_limitations", [])):
        fragments.append(
            {
                "fragment_id": f"REG-LIM-{i + 1:03d}",
                "document_id": "regulation_matrix.json",
                "document_type": "ЛНД",
                "title": "Важное ограничение (матрица нормативов)",
                "text": lim,
                "source": "regulation_matrix.json",
            }
        )
    for i, prof in enumerate(reg.get("medium_profiles", [])):
        fragments.append(
            {
                "fragment_id": f"REG-MED-{i + 1:03d}",
                "document_id": "regulation_matrix.json",
                "document_type": "ЛНД",
                "title": f"Профиль среды: {prof.get('name')}",
                "text": "Требуемые подтверждения: "
                + ", ".join(prof.get("required_evidence", [])),
                "source": "regulation_matrix.json",
            }
        )
    for i, std in enumerate(reg.get("replaced_standards", [])):
        fragments.append(
            {
                "fragment_id": f"REG-STD-{i + 1:03d}",
                "document_id": "regulation_matrix.json",
                "document_type": "ГОСТ",
                "title": f"Замена стандарта {std.get('standard')}",
                "text": f"{std.get('standard')} → {std.get('replacement')} ({std.get('status')})",
                "source": "regulation_matrix.json",
            }
        )

    path = _lnd_path()
    try:
        if path.exists():
            for i, line in enumerate(path.read_text(encoding="utf-8", errors="ignore").splitlines()):
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                doc_type = "ЛНД"
                if "ГОСТ" in line:
                    doc_type = "ГОСТ"
                elif "ТУ " in line or line.startswith("ТУ"):
                    doc_type = "ТУ"
                fragments.append(
                    {
                        "fragment_id": f"LND-{i + 1:04d}",
                        "document_id": "lnd_extract.md",
                        "document_type": doc_type,
                        "title": doc_type,
                        "text": line,
                        "source": str(path),
                    }
                )
    except OSError:
        pass

    return fragments