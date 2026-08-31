# agent/verify/verifier.py
"""Quality gate: детерминированная проверка соответствия ответа запросу.

6 эвристики (§3.2 плана):
  1. intent_mismatch — item_types/unit_ids не покрыты components
  2. quantity_unmet  — units_count есть, но нет verdict по спросу/остатку
  3. scope_mismatch  — все компоненты одного типа, хотя запрошено несколько
  4. zero_stock_missing — LIST_OUT_OF_STOCK, но в componentsqty>0
  5. parameter_miss  — ambiguities непуст, нет clarification
  6. empty_or_expert_silent — status EXPERT, explanation пуст
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

log = logging.getLogger("mtr.agent.verify")


@dataclass
class Gap:
    type: str
    detail: str
    severity: str  # "low" | "med" | "high"


@dataclass
class VerificationResult:
    verdict: str  # "pass" | "review"
    reasons: List[str] = field(default_factory=list)
    gaps: List[Gap] = field(default_factory=list)


def _item_types_in_answer(components: List[Dict[str, Any]]) -> set:
    return {c.get("item_type") for c in components if c.get("item_type")}


def _has_verdict(components: List[Dict[str, Any]]) -> bool:
    for c in components:
        st = (c.get("status") or "").lower()
        if any(kw in st for kw in ("хватает", "не хватает", "дефицит", "достаточно", "срочно")):
            return True
        if c.get("detail") and any(kw in c["detail"].lower() for kw in ("критично", "рекомендуется")):
            return True
    return False


def _check_intent_mismatch(parsed: Any, components: List[Dict[str, Any]]) -> Optional[Gap]:
    item_types = list(getattr(parsed, "item_types", []) or [])
    unit_ids = list(getattr(parsed, "unit_ids", []) or [])
    intents = list(getattr(parsed, "intents", []) or [])

    if not item_types and not unit_ids:
        return None

    answer_types = _item_types_in_answer(components)
    missing_types = [t for t in item_types if t.lower() not in {a.lower() for a in answer_types}]

    missing_units = []
    if unit_ids:
        answer_units = {
            uid
            for c in components
            for uid in [c.get("unit_id") or _extract_unit(c)]
            if uid
        }
        missing_units = [u for u in unit_ids if u not in answer_units]

    if not missing_types and not missing_units:
        return None

    is_critical = any(
        it in intents for it in ("CHECK_SUFFICIENCY", "PLAN_REPAIR")
    ) and not _has_verdict(components)

    severity = "high" if is_critical or (missing_types and len(missing_types) >= 2) else "med"
    detail_parts = []
    if missing_types:
        detail_parts.append(f"не найдены типы: {', '.join(missing_types)}")
    if missing_units:
        detail_parts.append(f"не найдены участки: {', '.join(missing_units)}")
    return Gap(type="intent_mismatch", detail="; ".join(detail_parts), severity=severity)


def _extract_unit(component: Dict[str, Any]) -> Optional[str]:
    st = component.get("status") or ""
    if "участок:" in st:
        return st.split("участок:")[-1].strip().split()[0]
    if "установлен на unit:" in st:
        return st.split("unit:")[-1].strip()
    return None


def _check_quantity_unmet(parsed: Any, components: List[Dict[str, Any]]) -> Optional[Gap]:
    units_count = getattr(parsed, "units_count", None)
    if not units_count or units_count < 1:
        return None

    intents = list(getattr(parsed, "intents", []) or [])
    if not any(it in intents for it in ("CHECK_SUFFICIENCY", "LIST_OUT_OF_STOCK", "CHECK_STOCK")):
        return None

    if _has_verdict(components):
        return None

    return Gap(
        type="quantity_unmet",
        detail=f"запрошено {units_count} шт., но ответ не содержит сравнения спроса и остатка",
        severity="high",
    )


def _check_scope_mismatch(parsed: Any, components: List[Dict[str, Any]]) -> Optional[Gap]:
    item_types = list(getattr(parsed, "item_types", []) or [])
    if len(item_types) < 2:
        return None

    answer_types = _item_types_in_answer(components)
    if len(answer_types) >= 2:
        return None

    if not answer_types:
        return Gap(
            type="scope_mismatch",
            detail=f"запрошены типы {', '.join(item_types)}, ответ пуст",
            severity="med",
        )

    return Gap(
        type="scope_mismatch",
        detail=f"запрошены типы {', '.join(item_types)}, но в ответе только {', '.join(answer_types)}",
        severity="med",
    )


def _check_zero_stock_missing(parsed: Any, components: List[Dict[str, Any]]) -> Optional[Gap]:
    intents = list(getattr(parsed, "intents", []) or [])
    if "LIST_OUT_OF_STOCK" not in intents:
        return None

    has_in_stock = False
    for c in components:
        qty = c.get("quantity")
        if isinstance(qty, (int, float)) and qty > 0:
            has_in_stock = True
            break

    if not has_in_stock:
        return None

    return Gap(
        type="zero_stock_missing",
        detail="интент LIST_OUT_OF_STOCK, но в ответе есть позиции с остатком > 0",
        severity="med",
    )


def _check_parameter_miss(parsed: Any, components: List[Dict[str, Any]]) -> Optional[Gap]:
    ambiguities = list(getattr(parsed, "ambiguities", []) or [])
    if not ambiguities:
        return None

    answers_text = " ".join(c.get("status", "") + " " + (c.get("detail") or "") for c in components)
    if "уточн" in answers_text.lower() or " вопрос" in answers_text.lower():
        return None

    return Gap(
        type="parameter_miss",
        detail=f"ambiguities: {'; '.join(ambiguities[:3])}",
        severity="low",
    )


def _check_empty_or_expert_silent(
    parsed: Any,
    components: List[Dict[str, Any]],
    answer_text: str,
    warnings: List[str],
) -> Optional[Gap]:
    from ..answer.status import STATUS_EXPERT

    status = getattr(parsed, "status", "") or ""
    is_expert = (
        status == STATUS_EXPERT
        or status == "REQUIRES_EXPERT"
        or "требует экспертной" in (answer_text or "").lower()
    )
    if not is_expert:
        return None

    if not answer_text or not answer_text.strip():
        return Gap(
            type="empty_or_expert_silent",
            detail="status=EXPERT, answer пуст",
            severity="high",
        )

    has_real_recommendation = False
    for w in warnings:
        if "попробовать LLM" not in w and w.strip():
            has_real_recommendation = True
            break

    if not has_real_recommendation:
        return Gap(
            type="empty_or_expert_silent",
            detail="status=EXPERT, нет содержательных рекомендаций",
            severity="med",
        )

    return None


def verify_answer(parsed: Any, answer: Any) -> VerificationResult:
    """Основная функция quality gate. Принимает ParsedQuery + AgentAnswer."""
    components = [c.model_dump() if hasattr(c, "model_dump") else dict(c) for c in (answer.components or [])]
    answer_text = getattr(answer, "answer", "") or ""
    warnings = list(getattr(answer, "warnings", []) or [])

    gaps: List[Gap] = []

    for check in [
        lambda: _check_intent_mismatch(parsed, components),
        lambda: _check_quantity_unmet(parsed, components),
        lambda: _check_scope_mismatch(parsed, components),
        lambda: _check_zero_stock_missing(parsed, components),
        lambda: _check_parameter_miss(parsed, components),
        lambda: _check_empty_or_expert_silent(parsed, components, answer_text, warnings),
    ]:
        gap = check()
        if gap is not None:
            gaps.append(gap)

    max_severity = _max_severity(gaps)
    verdict = "review" if gaps else "pass"
    reasons = [f"[{g.severity}] {g.type}: {g.detail}" for g in gaps]

    log.info(
        "[Verifier] verdict=%s gaps=%d max_severity=%s reasons=%s",
        verdict, len(gaps), max_severity, reasons,
    )

    return VerificationResult(verdict=verdict, reasons=reasons, gaps=gaps)


def _max_severity(gaps: List[Gap]) -> str:
    if not gaps:
        return "none"
    order = {"high": 3, "med": 2, "low": 1}
    best = max(order.get(g.severity, 0) for g in gaps)
    for label, val in order.items():
        if val == best:
            return label
    return "none"
