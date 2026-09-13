# agent/verify/verifier.py
"""Quality gate: детерминированная проверка соответствия ответа запросу.

Эвристики (§3.2 плана):
  1. intent_mismatch — item_types/unit_ids не покрыты components
  2. quantity_unmet  — units_count есть, но нет verdict по спросу/остатку
  3. inventory_reply_missing — складской интент без заключения по остаткам/заявке
  4. scope_mismatch  — все компоненты одного типа, хотя запрошено несколько
  5. zero_stock_missing — LIST_OUT_OF_STOCK, но в componentsqty>0
  6. parameter_miss  — ambiguities непуст, нет clarification
  7. empty_or_expert_silent — status EXPERT, explanation пуст
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

log = logging.getLogger("mtr.agent.verify")

_MORPH = None


def _morph():
    """Ленивая pymorphy2 (normal_form для русского слова); None при недоступности."""
    global _MORPH
    if _MORPH is None:
        try:
            from pymorphy2 import MorphAnalyzer

            _MORPH = MorphAnalyzer()
        except Exception:  # noqa: BLE001
            _MORPH = False
    return _MORPH or None


def _covers_types(text: str, types: List[str]) -> bool:
    """Покрыт ли каждый запрошенный тип словами текста (с учётом морфологии).

    «задвижки/задвижек» → «задвижка», «трубы» → «труба». Фолбэк на стем
    (усечение последней буквы) если pymorphy недоступен.
    """
    words = [w for w in re.split(r"\W+", text.lower()) if w]
    if not words:
        return False

    word_lemmas = set(words)
    m = _morph()
    if m is not None:
        for w in words:
            try:
                nf = m.parse(w)[0].normal_form.lower()
                if nf:
                    word_lemmas.add(nf)
            except Exception:  # noqa: BLE001
                pass

    for t in types:
        t_forms = {t, t[:-1] if len(t) > 2 else t}
        if m is not None:
            try:
                nf = m.parse(t)[0].normal_form.lower()
                if nf:
                    t_forms.add(nf)
            except Exception:  # noqa: BLE001
                pass
        if not (set(t_forms) & word_lemmas):
            return False
    return True


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
    uid = component.get("unit_id")
    if uid:
        return str(uid).strip() or None
    for field_key in ("status", "detail"):
        st = component.get(field_key) or ""
        for marker in ("участок:", "установлен на unit:", "установлен на "):
            idx = st.find(marker)
            if idx == -1:
                continue
            rest = st[idx + len(marker):].strip()
            if rest:
                return rest.split()[0]
    return None


_INVENTORY_VERDICT_KWS = (
    "на складе", "остаток", "нет позиций", "хватает", "не хватает",
    "дефицит", "достаточно", "пополнен", "срочность", "заявк",
    "требуется закуп",
)
_INVENTORY_ABSENT_KWS = (
    "нет данных", "нет информации", "нет сведений", "не удалось",
    "недостаточно данных", "ничего не найдено", "нет в каталоге",
)


def _check_inventory_reply(
    parsed: Any,
    components: List[Dict[str, Any]],
    answer_text: str,
    purchase_recommendation: Optional[str],
) -> Optional[Gap]:
    """Склады/заявка: интент проверки запаса требует заключения по остаткам (F5).

    Если в components/объяснении нет ни вердикта по остаткам, ни рекомендации
    по закупке — gap inventory_reply_missing (эскалация C1/C2 дооформит текст).
    """
    intents = list(getattr(parsed, "intents", []) or [])
    stock_intents = {"CHECK_STOCK", "CHECK_MINIMUM_STOCK", "LIST_OUT_OF_STOCK",
                     "CHECK_SUFFICIENCY"}
    if not (set(intents) & stock_intents):
        return None

    # LIST_OUT_OF_STOCK: позиции с нулевым остатком сами являются вердиктом.
    if "LIST_OUT_OF_STOCK" in intents:
        if any(
            isinstance(c.get("quantity"), (int, float)) and c.get("quantity") == 0
            for c in components
        ):
            return None

    comps_text = " ".join(
        f"{c.get('status') or ''} {(c.get('detail') or '')}" for c in components
    ).lower()
    hay = f"{str(answer_text or '').lower()} {comps_text}"
    if any(k in hay for k in _INVENTORY_ABSENT_KWS):
        return None  # честный «нет данных» — не дефект
    if purchase_recommendation:
        return None
    if any(k in hay for k in _INVENTORY_VERDICT_KWS):
        return None
    return Gap(
        type="inventory_reply_missing",
        detail="интент проверки запаса, но ответ не содержит заключения по остаткам/заявке",
        severity="med",
    )


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


_QUANTITY_VERDICT_KWS = (
    "хватает", "не хватает", "дефицит", "достаточно",
    "недостаточно", "срочно", "в наличии",
)
_STOCK_ABSENT_KWS = (
    "нет на складе", "нет в наличии", "нет остатка",
    "отсутствует", "не числится", "снят с учёта",
)
# Негативные маркеры: текст может упоминать типы/verdict, но в отрицательном
# контексте («нет информации о типах переход и отвод»). Такое покрытие НЕ закрывает gap.
_NEGATIVE_MARKERS = (
    "нет информации", "нет данных", "нет сведений", "не найдено",
    "не удалось", "невозможно", "недоступно", "недостаточно данных",
    "нет в каталоге", "ничего не найдено", "отсутствует информация",
    "данные отсутствуют", "укажите", "уточните запрос", "лимит попыток",
)


def _recheck_with_explanation(
    parsed: Any,
    answer_text: str,
    recommendations: List[str],
    gaps: List[Gap],
) -> List[Gap]:
    """Вторая стадия гейта: закрывает ли текст explanation/рекомендаций gaps.

    Эскалации C1/C2 пишут только в текстовую часть (explanation) и не меняют
    components. Стадия снимает gap только при явном текстовом покрытии:
      - quantity_unmet     — вердикт-слова (хватает, не хватает, дефицит, ...);
      - scope_mismatch     — в тексте перечислены все запрошенные типы;
      - intent_mismatch    — те же типы покрыты (при наличии unit_ids не снимаем);
      - zero_stock_missing — явные слова об отсутствии (нет на складе, ...).
    Первая (строгая по components) стадия остаётся неизменной.
    """
    if not gaps:
        return gaps

    text = "\n".join(p for p in (answer_text, " ".join(recommendations)) if p).lower()
    if not text.strip():
        return gaps

    requested = [t.lower() for t in (getattr(parsed, "item_types", None) or []) if t]
    unit_ids = [u for u in (getattr(parsed, "unit_ids", None) or []) if u]

    kept: List[Gap] = []
    resolved: List[str] = []
    has_negatives = any(m in text for m in _NEGATIVE_MARKERS)
    for g in gaps:
        closed = False
        if not has_negatives:
            if g.type == "quantity_unmet":
                closed = any(kw in text for kw in _QUANTITY_VERDICT_KWS)
            elif g.type == "scope_mismatch" and requested:
                closed = _covers_types(text, requested)
            elif g.type == "intent_mismatch" and requested and not unit_ids:
                closed = _covers_types(text, requested)
            elif g.type == "zero_stock_missing":
                closed = any(kw in text for kw in _STOCK_ABSENT_KWS)
            elif g.type == "inventory_reply_missing":
                closed = any(kw in text for kw in _INVENTORY_VERDICT_KWS)

        if closed:
            resolved.append(g.type)
        else:
            kept.append(g)

    if resolved:
        log.info("[Verifier] recheck_with_explanation closed: %s", resolved)
    return kept


def verify_answer(parsed: Any, answer: Any) -> VerificationResult:
    """Основная функция quality gate. Принимает ParsedQuery + AgentAnswer."""
    components = [c.model_dump() if hasattr(c, "model_dump") else dict(c) for c in (answer.components or [])]
    answer_text = getattr(answer, "explanation", "") or ""
    warnings = list(getattr(answer, "warnings", []) or [])

    gaps: List[Gap] = []

    purchase_recommendation = getattr(answer, "purchase_recommendation", None) or ""

    for check in [
        lambda: _check_intent_mismatch(parsed, components),
        lambda: _check_quantity_unmet(parsed, components),
        lambda: _check_inventory_reply(parsed, components, answer_text, purchase_recommendation),
        lambda: _check_scope_mismatch(parsed, components),
        lambda: _check_zero_stock_missing(parsed, components),
        lambda: _check_parameter_miss(parsed, components),
        lambda: _check_empty_or_expert_silent(parsed, components, answer_text, warnings),
    ]:
        gap = check()
        if gap is not None:
            gaps.append(gap)

    recommendations = list(getattr(answer, "recommendations", []) or [])
    gaps = _recheck_with_explanation(parsed, answer_text, recommendations, gaps)

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
