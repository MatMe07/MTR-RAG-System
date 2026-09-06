# agent/parsing/classifier.py

"""Классификатор запроса по 7 группам (Этап 1, §1A).

Rule-based скоринг по ключевым словам (1A.1) + контекстные переопределения
(1A.2), комбинирование по правилам 1A.5:
- rule-группа с confidence > 0.7 — берём её (DETERMINED);
- несколько групп с равным весом — LLM-fallback (если передан llm);
- неуверенность / пустой запрос — UNCLEAR (1A.6).

Ключевые слова и контекстные переопределения подтягиваются из DynamicRules
(group_keywords / contextual_overrides); при недоступной БД используются
дефолты кода (baseline, §1A.1).
"""

import re
from typing import Any, Callable, Dict, List, Optional

from ..rules.dynamic_rules import get_dynamic_rules

# Группы в порядке презентации (§1A).
GROUP_ORDER: List[str] = [
    "ПОИСК",
    "СКЛАД",
    "РЕМОНТ",
    "ЗАМЕНА",
    "АНАЛИЗ",
    "ОБЪЯСНЕНИЕ",
    "ДОКУМЕНТЫ",
]

# Базовые словари (§1A.1) — baseline кода, дополняются из БД.
DEFAULT_GROUP_KEYWORDS: Dict[str, List[str]] = {
    "ПОИСК": [
        "найди", "найти", "покажи", "подбери", "подобрать", "какой", "какая",
        "вариант", "подходящий", "код", "артикул", "номер",
    ],
    "СКЛАД": [
        "склад", "остаток", "остатки", "наличие", "сколько", "есть в наличии",
        "отсутств", "нет в наличии", "запас", "штук", "закуп",
    ],
    "РЕМОНТ": [
        "сломался", "ремонт", "замена", "отказал", "поврежд", "авария",
        "поломк", "почини", "обслужив",
    ],
    "ЗАМЕНА": [
        "замени", "заменить", "аналог", "вместо", "подбери замену",
        "замена на", "взаимозаменяем",
    ],
    "АНАЛИЗ": [
        "изменится", "последствия", "влияние", "что будет", "риск",
        "опасность", "проверить", "оцени", "проверка",
    ],
    "ОБЪЯСНЕНИЕ": [
        "объясни", "объяснить", "расскажи", "что значит", "чем отличается",
        "опиши", "расшифруй", "разница",
    ],
    "ДОКУМЕНТЫ": [
        "паспорт", "гост", "лнд", "документ", "документы",
        "сертификат", "разрешение", "стандарт",
    ],
}

# Короткие ключевые слова — только по границам слова (чтобы «нет» не матчился
# внутри «подняться», «ту» не матчился внутри произвольных слов).
_WORD_BOUNDARY = r"(?<![а-яёa-z0-9])%s(?![а-яёa-z0-9])"

# Контекстные переопределения кода (§1A.2): target, AND-words, boost.
CONTEXTUAL_RULES: List[Dict[str, Any]] = [
    {"target": "ЗАМЕНА", "words": ["подбери", "замену"], "boost": 3},
    {"target": "ДОКУМЕНТЫ", "words": ["расскажи", "паспорт"], "boost": 3},
    {"target": "ДОКУМЕНТЫ", "words": ["расскажи", "гост"], "boost": 3},
    {"target": "ДОКУМЕНТЫ", "words": ["найди", "паспорт"], "boost": 3},
    {"target": "ДОКУМЕНТЫ", "words": ["найди", "гост"], "boost": 3},
    {"target": "ДОКУМЕНТЫ", "words": ["найти", "паспорт"], "boost": 3},
    {"target": "ДОКУМЕНТЫ", "words": ["найти", "гост"], "boost": 3},
    {"target": "РЕМОНТ", "words": ["сломался", "замени"], "boost": 3},
    {"target": "РЕМОНТ", "words": ["сломался", "замену"], "boost": 3},
]

# «Заменить DN… на DN…» / «вместо DN… поставить DN…» → ЗАМЕНА.
_DN_CHANGE_RE = re.compile(
    r"(замен[а-яё]*|вместо)\s*(?:(?:d\w*|д\w*|ду)\s*)?\d{2,4}\s*на\s*(?:(?:d\w*|д\w*|ду)\s*)?\d{2,4}",
    re.IGNORECASE,
)
_NEGATION_START_RE = re.compile(r"^\s*нет[\s,.;:!?]", re.IGNORECASE)
# «ТУ 14-3-...» — ссылка на норму (а не местоимение «ту»).
_TU_RE = re.compile(r"\bту\s*\d", re.IGNORECASE)

RULE_CONFIDENCE_THRESHOLD = 0.7
# Минимальная уверенность одиночной группы (1A.5: ML < 0.5 → UNCLEAR).
MIN_RULE_CONFIDENCE = 0.5


class GroupClassifier:
    """Классификация пользовательского запроса по 7 группам (§1A).

    llm — опциональный callable llm_classify(text) -> группа (для tie-break
    §1A.4/1A.5). По умолчанию None (офлайн): равные веса → UNCLEAR.
    """

    def __init__(
        self,
        rules: Optional[Any] = None,
        llm: Optional[Callable[[str], Optional[str]]] = None,
    ):
        self._rules = rules or get_dynamic_rules()
        self._llm = llm
        self._keywords = self._load_keywords()
        self._overrides = self._load_overrides()

    # ------------------------------------------------------------- словари
    def _load_keywords(self) -> Dict[str, List[str]]:
        out: Dict[str, List[str]] = {}
        for group in GROUP_ORDER:
            merged = list(DEFAULT_GROUP_KEYWORDS.get(group, []))
            try:
                for kw in self._rules.get_keywords(group) or []:
                    kw = str(kw).strip()
                    if kw and kw not in merged:
                        merged.append(kw)
            except Exception:  # noqa: BLE001  (БД недоступна — дефолты)
                pass
            out[group] = merged
        return out

    def _load_overrides(self) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        try:
            for o in self._rules.get_overrides() or []:
                trigger = (o.get("trigger") or "").strip()
                target = (o.get("target") or "").strip().upper()
                if trigger and target:
                    out.append({
                        "trigger": trigger.lower(),
                        "target": target,
                        "boost": max(1, int(o.get("priority") or 0)),
                    })
        except Exception:  # noqa: BLE001
            pass
        return out

    # ------------------------------------------------------------- скоринг
    @staticmethod
    def _keyword_re(kw: str) -> re.Pattern:
        if len(kw) <= 4:
            return re.compile(_WORD_BOUNDARY % re.escape(kw), re.IGNORECASE)
        return re.compile(re.escape(kw), re.IGNORECASE)

    def _score(self, lower: str) -> Dict[str, Any]:
        negation = bool(_NEGATION_START_RE.match(lower))
        scores: Dict[str, int] = {g: 0 for g in GROUP_ORDER}
        matched: Dict[str, List[str]] = {g: [] for g in GROUP_ORDER}

        for group, kws in self._keywords.items():
            for kw in kws:
                if negation and kw == "нет":
                    continue
                if self._keyword_re(kw).search(lower):
                    scores[group] += 1
                    matched[group].append(kw)

        # «Замена DN… на DN…» (1A.2).
        if _DN_CHANGE_RE.search(lower):
            scores["ЗАМЕНА"] += 2
            matched["ЗАМЕНА"].append("DN->DN")

        # «ТУ <цифра>» — ссылка на норматив (сильный маркер).
        if _TU_RE.search(lower):
            scores["ДОКУМЕНТЫ"] += 2
            matched["ДОКУМЕНТЫ"].append("ТУ<номер")

        # Контекстные правила кода.
        for rule in CONTEXTUAL_RULES:
            words = rule.get("words", [])
            if all(w in lower for w in words):
                scores[rule["target"]] += rule.get("boost", 1)
                matched[rule["target"]].append("context:" + "+".join(words))

        # Переопределения из БД (contextual_overrides): триггер-фраза в тексте.
        for o in self._overrides:
            if o["trigger"] in lower:
                scores[o["target"]] += o["boost"]
                if o["target"] in matched:
                    matched[o["target"]].append("override:" + o["trigger"])

        return {"scores": scores, "matched": matched}

    # ------------------------------------------------------------- решение
    def classify(self, text: str) -> Dict[str, Any]:
        """Возвращает результат классификации:

        {
          'status': 'DETERMINED' | 'UNCLEAR',
          'top_group': str | None,
          'confidence': float,
          'groups': [{'group', 'score', 'confidence', 'matched'}]
        }
        """
        text = text or ""
        lower = text.lower()
        result = self._score(lower)
        scores = result["scores"]
        matched = result["matched"]

        total = sum(scores.values())
        if total == 0:
            return self._unclear(text, scores, matched)

        ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
        top_group, top_score = ranked[0]
        confidence = round(top_score / total, 3)

        # Tie между первой и второй группой (равный вес).
        second_score = ranked[1][1] if len(ranked) > 1 else 0
        ties = [g for g, s in ranked if s == top_score]

        groups_out = [
            {
                "group": g,
                "score": s,
                "confidence": round(s / total, 3) if total else 0.0,
                "matched": matched.get(g, []),
            }
            for g, s in ranked
        ]

        if confidence >= RULE_CONFIDENCE_THRESHOLD and len(ties) == 1:
            return {
                "status": "DETERMINED",
                "top_group": top_group,
                "confidence": confidence,
                "groups": groups_out,
            }

        # Одиночная группа, но неуверенно (0.5–0.7): берём как слабую гипотезу.
        if len(ties) == 1 and confidence >= MIN_RULE_CONFIDENCE:
            return {
                "status": "DETERMINED",
                "top_group": top_group,
                "confidence": confidence,
                "groups": groups_out,
                "weak": True,
            }

        # Равные веса → LLM-fallback (§1A.4); недоступен → UNCLEAR (§1A.5).
        if len(ties) > 1:
            llm_group = self._llm_classify(text)
            if llm_group and llm_group in GROUP_ORDER:
                return {
                    "status": "DETERMINED",
                    "top_group": llm_group,
                    "confidence": confidence,
                    "groups": groups_out,
                    "llm_fallback": True,
                }

        return self._unclear(text, scores, matched, groups=groups_out)

    def _llm_classify(self, text: str) -> Optional[str]:
        if not self._llm:
            return None
        try:
            return self._llm(text)
        except Exception:  # noqa: BLE001
            return None

    @staticmethod
    def _unclear(text: str, scores: Dict[str, int], matched: Dict[str, List[str]], groups: Optional[List[Dict[str, Any]]] = None):
        if groups is None:
            total = sum(scores.values())
            groups = [
                {
                    "group": g,
                    "score": s,
                    "confidence": round(s / total, 3) if total else 0.0,
                    "matched": matched.get(g, []),
                }
                for g, s in sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
                if s > 0
            ]
        return {
            "status": "UNCLEAR",
            "top_group": None,
            "confidence": 0.0,
            "groups": groups,
            "detail": "Нет уверенной группы" if text else "Пустой запрос",
        }


_classifier: Optional[GroupClassifier] = None


def get_group_classifier() -> GroupClassifier:
    global _classifier
    if _classifier is None:
        _classifier = GroupClassifier()
    return _classifier


def reset_group_classifier() -> None:
    global _classifier
    _classifier = None