# backend/app/services/llm_service.py

import json
import re
from typing import Optional, Dict, Any
from langchain_openai import ChatOpenAI

from app.core.config import settings
from app.schemas import (
    Coating,
    Environment,
    Extraction,
    Geometry,
    ItemCard,
    Material,
    Normative,
    Pressure,
    Source,
)
from app.services.query_normalizer import normalize_query


QUERY_TO_CARD_PROMPT = """
Ты извлекаешь инженерные параметры изделия из пользовательского запроса.

Верни строго JSON по схеме ItemCard. Не добавляй текст до или после JSON.

Правила:
- Не выдумывай значения.
- Если параметр не указан, ставь null.
- Если пользователь ввел условное обозначение (ОКШ90-159x10-К48-09Г2С-УХЛ), сохрани его в поле designation.
- Если параметр указан неявно, запиши нормализованное значение.
- Считай ДУ, DU и "условный проход" синонимами DN.
- Считай Ру, PY и PU синонимами PN.
- Запись "426 на 10" или "426х10" означает размер 426x10, а не DN426.
- Слова "колено" и "отвод" в запросах на трубопроводные детали нормализуй как тип "отвод".
- Если пользователь говорит "сероводород", "H2S" - установи environment.medium = "H2S".
- Если пользователь говорит "для H2S", "с H2S", "сероводородная среда" - установи h2s_confirmed = true как требование запроса, а не как доказанный факт о кандидате.
- Если пользователь говорит "без H2S", "не для H2S" - установи h2s_confirmed = false.
- Если пользователь говорит "внутреннее покрытие" или "наружное покрытие", заполни блок coating.

Поля для поиска:
- тип изделия: отвод, труба, задвижка, заглушка, переход, тройник
- подтип: ОКШ, ОГ, ЗК
- DN / диаметр (число)
- угол для отводов (число)
- толщина стенки (число)
- PN/Ру или давление (число)
- марка стали (строка)
- класс прочности: К48, К52 (строка)
- среда: H2S, CO2, газ, вода, нефть
- внутреннее/наружное покрытие (true/false)
- ГОСТ/ТУ (строка)
- климатическое исполнение: У, УХЛ, ХЛ (строка)

Схема ответа:
{{
    "item_type": "отвод",
    "subtype": "ОКШ",
    "designation": "ОКШ90-159x10-К48-09Г2С-УХЛ",
    "geometry": {{"dn": 159, "wall_thickness": 10, "angle": 90}},
    "pressure": {{"pn": 160}},
    "material": {{"steel_grade": "09Г2С", "strength_class": "К48"}},
    "environment": {{"medium": "H2S", "h2s_confirmed": true, "co2_confirmed": null, "climate_version": "УХЛ"}},
    "coating": {{"inner_coating": true, "outer_coating": null}},
    "normative": {{"gost_tu": "ТУ 1469-048-78795288-2015"}},
    "extraction": {{"missing_fields": []}}
}}

Только JSON, без пояснений.
Запрос: {query}
"""

PASSPORT_TO_CARD_PROMPT = """
Ты извлекаешь параметры изделия из текста паспорта, OCR-результата или таблицы.

Верни строго JSON по схеме ItemCard. Не добавляй текст до или после JSON.

Главные правила:
- Не выдумывай значения.
- Если параметр не найден, ставь null.
- Если текст содержит таблицу в формате "Параметр | Значение" или "DN: 159 мм", извлекай параметры из неё.
- Если значения противоречат, выбери то, что встречается чаще или указано в таблице.
- Заводской номер не превращай в отдельный МТР.
- Не ищи mtr_code и ksm_code — их нет в паспорте.

Схема ответа:
{{
    "item_type": "отвод",
    "subtype": "ОКШ",
    "designation": "ОКШ90-159x10-К48-09Г2С-УХЛ",
    "geometry": {{"dn": 159, "wall_thickness": 10, "angle": 90}},
    "pressure": {{"pn": 160}},
    "material": {{"steel_grade": "09Г2С", "strength_class": "К48"}},
    "environment": {{"medium": "газ", "h2s_confirmed": null, "co2_confirmed": null, "climate_version": "УХЛ"}},
    "coating": {{"inner_coating": null, "outer_coating": true}},
    "normative": {{"gost_tu": "ТУ 1469-048-78795288-2015"}},
    "extraction": {{"missing_fields": ["mtr_code", "ksm_code"]}}
}}

Только JSON, без пояснений.
Текст: {text}
"""

EXPLAIN_MATCH_PROMPT = """
Ты формируешь короткое объяснение для эксперта по результату подбора МТР/КСМ.

Система рекомендательная. Не пиши, что решение окончательное. Не утверждай применимость изделия, если есть предупреждения или недостающие данные.

На вход ты получаешь результат матчинга.

Верни JSON:
{{
  "summary": "короткий вывод",
  "why_in_results": "почему кандидат попал в выдачу",
  "matched": ["..."],
  "warnings": ["..."],
  "expert_next_steps": ["..."],
  "source_note": "какие источники использованы"
}}

Правила:
- Пиши простым языком.
- Отделяй совпадения от предупреждений.
- Если покрытие не подтверждено, не отклоняй автоматически, а напиши, что эксперту нужно проверить покрытие.
- Если H2S/CO2 не подтверждены, напиши "требует проверки".
- Если это составная замена, явно напиши, что это не прямой аналог.
- Не выдумывай источники.

Результат:
{result}
"""


class LLMService:
    def __init__(self):
        self.api_key = settings.OPENROUTER_API_KEY
        self.base_url = settings.OPENROUTER_BASE_URL
        self.model = settings.LLM_MODEL
        self.temperature = settings.LLM_TEMPERATURE
        self._llm = None

    @property
    def llm(self):
        if self._llm is None:
            if not self.api_key:
                raise ValueError(
                    "OPENROUTER_API_KEY не задан. Добавьте его в .env"
                )
            self._llm = ChatOpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                model=self.model,
                temperature=self.temperature
            )
        return self._llm

    def parse_query(self, query: str) -> ItemCard:
        normalized = normalize_query(query)
        prompt = QUERY_TO_CARD_PROMPT.format(
            query=normalized["normalized_text"]
        )
        # print(prompt)
        # print(self.llm)
        response = self.llm.invoke(prompt).content
        print(response)
        return self._extract_card_from_response(
            response,
            {"type": "user_query", "text": query}
        )

    def extract_card_from_text(self, text: str, source: Dict[str, Any]) -> ItemCard:
        prompt = PASSPORT_TO_CARD_PROMPT.format(text=text[:4000])
        response = self.llm.invoke(prompt).content
        return self._extract_card_from_response(response, source)

    def generate_explanation(self, result: Dict[str, Any]) -> Dict[str, Any]:
        prompt = EXPLAIN_MATCH_PROMPT.format(result=json.dumps(result, ensure_ascii=False))
        response = self.llm.invoke(prompt).content
        return self._parse_explanation_response(response)

    def _extract_card_from_response(self, response: str, source: Dict[str, Any]) -> ItemCard:
        try:
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if not json_match:
                return self._empty_card(source)
            data = json.loads(json_match.group())
            source_copy = {k: v for k, v in source.items() if k != "type"}
            # print(data)
            # print(source_copy)
            return ItemCard(
                card_id=None,
                mtr_code=None,
                ksm_code=None,
                item_type=data.get('item_type', ''),
                subtype=data.get('subtype'),
                designation=data.get('designation'),
                name=data.get('name'),
                geometry=Geometry(
                    dn=data.get('geometry', {}).get('dn'),
                    wall_thickness=data.get('geometry', {}).get('wall_thickness'),
                    angle=data.get('geometry', {}).get('angle')
                ),
                pressure=Pressure(
                    pn=data.get('pressure', {}).get('pn')
                ),
                material=Material(
                    steel_grade=data.get('material', {}).get('steel_grade'),
                    strength_class=data.get('material', {}).get('strength_class'),
                    standard=data.get('material', {}).get('standard')
                ),
                environment=Environment(
                    medium=data.get('environment', {}).get('medium'),
                    h2s_confirmed=data.get('environment', {}).get('h2s_confirmed'),
                    co2_confirmed=data.get('environment', {}).get('co2_confirmed'),
                    climate_version=data.get('environment', {}).get('climate_version')
                ),
                coating=Coating(
                    inner_coating=data.get('coating', {}).get('inner_coating'),
                    outer_coating=data.get('coating', {}).get('outer_coating')
                ),
                normative=Normative(
                    gost_tu=data.get('normative', {}).get('gost_tu')
                ),
                extraction=Extraction(
                    confidence=data.get('extraction', {}).get('confidence'),
                    method=data.get('extraction', {}).get('method')
                    or "user_query",
                    missing_fields=data.get('extraction', {}).get(
                        'missing_fields', []
                    ),
                ),
                sources=[Source( type="LLM",  **source_copy)]
            )
        except Exception:
            return self._empty_card(source)

    def _parse_explanation_response(self, response: str) -> Dict[str, Any]:
        try:
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if not json_match:
                return {
                    "summary": "Объяснение не сгенерировано.",
                    "why_in_results": "",
                    "matched": [],
                    "warnings": [],
                    "expert_next_steps": [],
                    "source_note": ""
                }
            return json.loads(json_match.group())
        except Exception:
            return {
                "summary": "Ошибка генерации объяснения.",
                "why_in_results": "",
                "matched": [],
                "warnings": [],
                "expert_next_steps": [],
                "source_note": ""
            }

    def _empty_card(self, source: Dict[str, Any]) -> ItemCard:
        return ItemCard(
            card_id=None,
            mtr_code=None,
            ksm_code=None,
            item_type="",
            subtype=None,
            designation=None,
            name=None,
            geometry=Geometry(),
            pressure=Pressure(),
            material=Material(),
            environment=Environment(),
            coating=Coating(),
            normative=Normative(),
            sources=[Source(type="llm", **source)]
        )
