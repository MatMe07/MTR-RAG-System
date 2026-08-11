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
    ParsedQuery
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

ENTITY_EXTRACTION_PROMPT = """
Ты — специализированный инженерный ИИ-парсер. Твоя задача — извлечь параметры из запроса инженера и заполнить JSON-структуру строго по правилам.

ПРАВИЛА ИЗВЛЕЧЕНИЯ:
1. Выводи строго один объект JSON.
2. Извлекай параметры, только если они явно или синонимично указаны в тексте.
3. Если параметр не упомянут — пиши null (или пустой список [], объект {{}}). Никогда не выдумывай ГОСТы, давления (PN) или марки стали из головы.
4. "H2S", "сероводород" -> medium="H2S", h2s_confirmed=true.
5. "Север", "под Север", "УХЛ" -> climate_version="УХЛ".
6. Формат размеров: "159х10" означает dn=159.0, wall_thickness=10.0.

ПРИМЕР 1 (Запрос с неполными данными):
Запрос: "Нужен отвод 57х4 для сероводорода"
Ответ:
{{
    "operations": ["find"],
    "item_types": ["отвод"],
    "confidence": 0.9,
    "card": {{
        "item_type": "отвод",
        "geometry": {{"dn": 57.0, "wall_thickness": 4.0, "angle": null}},
        "pressure": {{"pn": null}},
        "material": {{"steel_grade": null, "strength_class": null}},
        "environment": {{"medium": "H2S", "h2s_confirmed": true, "co2_confirmed": false, "climate_version": null}},
        "normative": {{"gost_tu": null}}
    }},
    "ambiguities": ["Укажите угол отвода (например, 90, 60, 45 градусов) и марку стали."]
}}

ПРИМЕР 2 (Запрос без параметров, требующий уточнения):
Запрос: "замени задвижку"
Ответ:
{{
    "operations": ["replace"],
    "item_types": ["задвижка"],
    "confidence": 0.5,
    "card": {{
        "item_type": "задвижка",
        "geometry": {{"dn": null, "wall_thickness": null, "angle": null}},
        "pressure": {{"pn": null}},
        "material": {{"steel_grade": null, "strength_class": null}},
        "environment": {{"medium": null, "h2s_confirmed": false, "co2_confirmed": false, "climate_version": null}},
        "normative": {{"gost_tu": null}}
    }},
    "ambiguities": ["Укажите диаметр (DN) и давление (PN) задвижки для замены."]
}}

Текущий запрос инженера для обработки: "{query}"

Выведи заполненную структуру в формате JSON по аналогии с примерами:
"""


QUERY_VALIDATION_PROMPT = """
Ты проверяешь и исправляешь результат парсинга инженерного запроса.

Оригинальный запрос: {original_query}

Результат парсинга (может содержать ошибки):
{parsed_json}

Твоя задача:
1. Проверить, правильно ли определены:
   - operations (что нужно сделать: find, replace, check, plan, explain, calculate, compare, assemble)
   - item_type (тип изделия)
   - параметры (DN, угол, толщина, давление, материал, среда)
   - контекст (component_id, unit_id)

2. Если что-то пропущено или определено неверно — исправь.

3. Если запрос неполный — добавь вопросы в ambiguities.

4. Верни JSON с исправленными данными.

Формат ответа:
{{
    "operations": ["find", "replace"],
    "card": {{
        "item_type": "задвижка",
        "geometry": {{"dn": 150, "wall_thickness": null, "angle": null}},
        "pressure": {{"pn": 40}},
        "material": {{"steel_grade": null, "strength_class": null}},
        "environment": {{"medium": "H2S", "h2s_confirmed": true}}
    }},
    "filters": {{"dn": 150, "pn": 40, "medium": "H2S"}},
    "context": {{"component_id": "COMP-SYN-010"}},
    "ambiguities": ["Укажите DN задвижки"],
    "confidence": 0.9
}}

Правила:
- Если параметр не указан в запросе — ставь null
- НЕ выдумывай значения
- Если есть COMP-SYN-XXX или UNIT-SYN-XXX — сохрани в context

Только JSON, без пояснений.
"""
# backend/app/services/llm_service.py (только класс LLMService)

class LLMService:
    def __init__(self):
        self.use_local = getattr(settings, "USE_LOCAL_LLM", False)
        
        self.api_key = "ollama" if self.use_local else settings.OPENROUTER_API_KEY
        self.base_url = "http://localhost:11434/v1" if self.use_local else settings.OPENROUTER_BASE_URL
        self.model = "qwen2.5:3b" if self.use_local else settings.LLM_MODEL
        self.temperature = settings.LLM_TEMPERATURE
        self._llm = None

    @property
    def llm(self):
        if self._llm is None:
            if not self.use_local and not self.api_key:
                raise ValueError("OPENROUTER_API_KEY не задан. Добавьте его в .env")
                
            # Дополнительные параметры для гарантированного JSON в режиме Ollama
            extra_kwargs = {}
            if self.use_local:
                extra_kwargs["model_kwargs"] = {"response_format": {"type": "json_object"}}

            self._llm = ChatOpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                model=self.model,
                temperature=self.temperature,
                **extra_kwargs
            )
        return self._llm

    def parse_query(self, query: str) -> ItemCard:
        if re.match(r'^[A-Z]{3}-[A-Z]{3}-[A-Z]{3}-\d{6}$', query.strip()):
            return ItemCard(
                item_type="",
                mtr_code=query.strip(),
                sources=[Source(type="user_query", fragment=query)]
            )
        normalized = normalize_query(query)
        prompt = QUERY_TO_CARD_PROMPT.format(query=normalized["normalized_text"])
        response = self.llm.invoke(prompt).content
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

    def parse_engineering_query(self, query: str) -> ParsedQuery:
        # 1. Быстрая проверка регуляркой (остается без изменений)
        if re.match(r"^[A-Z]{3}-[A-Z]{3}-[A-Z]{3}-\d{6}$", query.strip()):
            return ParsedQuery(
                original_query=query,
                operations=["find"],
                technical_filters={"mtr_code": query.strip()},
                confidence=1.0,
            )

        # 2. Привязываем схему ParsedQuery к нашей модели
        # Благодаря этому LangChain сам заставит Ollama/Qwen вернуть структуру строго по схеме
        structured_llm = self.llm.with_structured_output(ParsedQuery)

        # 3. Вызываем модель
        try:
            # Передаем промпт и текст
            prompt = ENTITY_EXTRACTION_PROMPT.format(query=query)

            # МАГИЯ: invoke вернет НЕ строку, а уже готовый объект класса ParsedQuery!
            # Все вложенные Geometry, Pressure, Material уже будут внутри, проверенные на типы данных.
            parsed_result = structured_llm.invoke(prompt)

            # Проставляем исходный запрос, если нужно
            parsed_result.original_query = query
            return parsed_result

        except Exception as e:
            # Если модель не смогла заполнить схему или упала ошибка сети
            return ParsedQuery(
                original_query=query,
                ambiguities=[f"Ошибка структурирования: {str(e)}"],
                confidence=0.0,
            )

    def _extract_card_from_response(self, response: str, source: Dict[str, Any]) -> ItemCard:
        try:
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if not json_match:
                return self._empty_card(source)
            data = json.loads(json_match.group())
            source_copy = {k: v for k, v in source.items() if k != "type"}
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
                    method=data.get('extraction', {}).get('method') or "user_query",
                    missing_fields=data.get('extraction', {}).get('missing_fields', []),
                ),
                sources=[Source(type="LLM", **source_copy)]
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
    def validate_and_correct_query(self, parsed: ParsedQuery) -> ParsedQuery:
        """
        Проверяет и исправляет результат гибридного парсинга с помощью LLM.
        """
        # Если confidence высокий и нет ambiguities — возвращаем как есть
        if parsed.confidence >= 0.8 and not parsed.ambiguities:
            return parsed

        # Формируем промпт для LLM
        prompt = QUERY_VALIDATION_PROMPT.format(
            original_query=parsed.original_query,
            parsed_json=parsed.model_dump_json(indent=2)
        )
        
        try:
            response = self.llm.invoke(prompt).content
            data = json.loads(response)
            
            # Обновляем parsed данными от LLM
            corrected = self._apply_llm_corrections(parsed, data)
            corrected.confidence = data.get("confidence", parsed.confidence)
            
            return corrected
        except Exception as e:
            # Если LLM упала — возвращаем исходный
            parsed.ambiguities.append(f"LLM проверка не удалась: {str(e)}")
            return parsed

    def _apply_llm_corrections(self, parsed: ParsedQuery, corrections: Dict) -> ParsedQuery:
        """Применяет исправления от LLM к ParsedQuery."""
        
        # Исправляем операции
        if corrections.get("operations"):
            parsed.operations = corrections["operations"]
        
        # Исправляем карточку
        if corrections.get("card"):
            card_data = corrections["card"]
            if parsed.card:
                # Обновляем существующую карточку
                if card_data.get("item_type"):
                    parsed.card.item_type = card_data["item_type"]
                if card_data.get("subtype"):
                    parsed.card.subtype = card_data["subtype"]
                if card_data.get("designation"):
                    parsed.card.designation = card_data["designation"]
                if card_data.get("geometry"):
                    geo = card_data["geometry"]
                    if geo.get("dn"):
                        parsed.card.geometry.dn = geo["dn"]
                    if geo.get("wall_thickness"):
                        parsed.card.geometry.wall_thickness = geo["wall_thickness"]
                    if geo.get("angle"):
                        parsed.card.geometry.angle = geo["angle"]
                if card_data.get("pressure") and card_data["pressure"].get("pn"):
                    parsed.card.pressure.pn = card_data["pressure"]["pn"]
                if card_data.get("material"):
                    if card_data["material"].get("steel_grade"):
                        parsed.card.material.steel_grade = card_data["material"]["steel_grade"]
                    if card_data["material"].get("strength_class"):
                        parsed.card.material.strength_class = card_data["material"]["strength_class"]
                if card_data.get("environment"):
                    if card_data["environment"].get("medium"):
                        parsed.card.environment.medium = card_data["environment"]["medium"]
                    if card_data["environment"].get("h2s_confirmed") is not None:
                        parsed.card.environment.h2s_confirmed = card_data["environment"]["h2s_confirmed"]
                    if card_data["environment"].get("climate_version"):
                        parsed.card.environment.climate_version = card_data["environment"]["climate_version"]
        
        # Исправляем фильтры
        if corrections.get("filters"):
            parsed.technical_filters.update(corrections["filters"])
        
        # Исправляем контекст
        if corrections.get("context"):
            if corrections["context"].get("unit_id"):
                parsed.unit_context["unit_id"] = corrections["context"]["unit_id"]
                parsed.unit_ids.append(corrections["context"]["unit_id"])
            if corrections["context"].get("component_id"):
                parsed.component_context["component_id"] = corrections["context"]["component_id"]
                parsed.component_ids.append(corrections["context"]["component_id"])
        
        # Исправляем неоднозначности
        if corrections.get("ambiguities") is not None:
            parsed.ambiguities = corrections["ambiguities"]
        
        # Обновляем confidence_details
        parsed.confidence_details["llm_correction"] = corrections.get("confidence", 0.9)
        
        return parsed
    def _empty_card(self, source: Dict[str, Any]) -> ItemCard:
        source_copy = {k: v for k, v in source.items() if k != "type"}
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
            sources=[Source(type="llm", **source_copy)]
        )
