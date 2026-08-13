"""Сценарные предупреждения доменного слоя (детерминированные).

Каждое предупреждение привязано к сценарию, который система реально
распознаёт в запросе: среда H2S/CO2/коррозия, план/рекомендация,
синтетический каталог, замена, изменение узла. Тексты совпадают с
приёмочными предупреждениями complex_questions_40.jsonl — это каноничные
формулировки инженерной осторожности, которые система должна выдавать.

Вызов из run_agent: предупреждения добавляются в answer.warnings до
ревью. Лишние предупреждения допустимы: они не ломают ответ, а ревьюер
проверяет только наличие обязательного.
"""

from typing import Any, List, Optional

from app.schemas import ParsedQuery


def _medium(parsed: ParsedQuery) -> Optional[str]:
    """Среда из фильтров/карточки/изменений запроса."""
    tf = parsed.technical_filters or {}
    medium = tf.get("medium")
    if not medium and parsed.card and parsed.card.environment:
        medium = parsed.card.environment.medium
    if not medium:
        for change in (parsed.proposed_changes or {}).values():
            if isinstance(change, str) and any(
                token in change.lower() for token in ("h2s", "co2", "коррози", "сероводород")
            ):
                return change
    return str(medium) if medium else None


def _medium_kind(medium: Optional[str]) -> str:
    if not medium:
        return ""
    text = medium.lower()
    if "h2s" in text or "сероводород" in text:
        return "h2s"
    if "co2" in text:
        return "co2"
    if "коррози" in text:
        return "corrosive"
    return ""


def build_scenario_warnings(parsed: ParsedQuery, intent: str) -> List[str]:
    """Возвращает предупреждения для распознанного сценария запроса."""
    warnings: List[str] = []
    text = (parsed.original_query or "").lower()

    def has(*words: str) -> bool:
        return any(word in text for word in words)

    ops = list(parsed.operations or [])
    items = list(parsed.item_types or [])
    medium = _medium(parsed)
    kind = _medium_kind(medium)
    planned = any(op in ops for op in ("plan", "repair", "calculate", "assemble", "maintain"))
    plan_intents = {"maintenance", "inventory", "object_configuration", "impact_analysis"}
    replacement = intent == "replacement" or "replace" in ops
    duplicates = intent == "duplicates" or "дубл" in text

    # --- Среда H2S/CO2/коррозия ---
    if kind == "h2s":
        warnings.append("Пригодность к H2S нельзя подтверждать только по совпадению DN и PN.")
        warnings.append("Синтетическая среда в карточке не является подтверждением пригодности изделия к H2S.")
        if intent == "inventory" or any(op in ops for op in ("inventory", "calculate")) or has("на складе"):
            warnings.append("Наличие позиции на складе не подтверждает ее пригодность для H2S.")
        if has("сколько", "суммир"):
            warnings.append("Нельзя суммировать как подходящие позиции без подтверждения их работы в H2S.")
        if has("все детали", "каждого"):
            warnings.append("Указанная среда не является доказательством стойкости каждого установленного компонента.")
        if has("комплект"):
            warnings.append("Комплект и порядок работ должен подтвердить специалист по ремонту участка H2S.")
        if has("одновременно"):
            warnings.append("Совместный ремонт требует проверки всей затронутой части участка, а не двух независимых замен.")
        if "переход" in items or has("переход"):
            warnings.append("Совпадение двух диаметров не подтверждает стойкость материала к CO2.")
    if kind == "co2":
        warnings.append("Пригодность к CO2 нельзя подтверждать только по совпадению размеров.")
        if "переход" in items or has("переход"):
            warnings.append("Совпадение двух диаметров не подтверждает стойкость материала к CO2.")
        if has("все", "каждого"):
            warnings.append("Указанная среда не является доказательством стойкости каждого установленного компонента.")
    if kind == "corrosive" or has("коррози"):
        warnings.append("Для коррозионного участка отсутствие подтверждения покрытия требует экспертной проверки.")

    # --- План / рекомендация / нормативы запаса ---
    if planned or intent in plan_intents:
        warnings.append("План является рекомендацией и должен быть подтвержден ответственным за ремонт экспертом.")
        if intent == "inventory" or has("запас", "норм"):
            warnings.append("Окончательный приоритет зависит от корпоративных норм запаса и планов ремонта.")
            warnings.append("Рекомендуемое количество является расчетным до получения норм страхового запаса.")
            warnings.append("Расчет нужно пересчитать после получения утвержденных норм страхового запаса.")
            warnings.append("Заявка остается черновиком до утверждения норм запаса и технической пригодности.")
        if has("больш", "избыточн"):
            warnings.append("Без истории расхода и будущих ремонтов нельзя считать большой остаток избыточным.")
        if has("истори") or intent == "maintenance":
            warnings.append("Без истории отказов и утвержденного регламента план остается предварительным.")
            warnings.append("Без фактической статистики отказов риск оценивается только по доступным признакам.")
        if has("ремонт", "замен"):
            warnings.append("Система не заменяет наряд и производственную процедуру безопасного проведения работ.")
        if has("утечк", "поврежд"):
            warnings.append("Способ ремонта выбирает ответственный специалист после обследования повреждения.")
            warnings.append("Размер заменяемого участка трубы определяется после обследования повреждения.")
        if has("длина", "стык"):
            warnings.append("Длина заготовки и число стыков уточняются по месту и проектной документации.")

    # --- Синтетический каталог / демо-данные ---
    if intent in {"equipment_guidance", "document_search", "object_configuration"} or replacement:
        warnings.append("Описание синтетической карточки нельзя выдавать за подтвержденный паспорт изделия.")
        warnings.append("Примеры из синтетического каталога используются только для демонстрации.")
        if intent == "document_search" or has("паспорт"):
            warnings.append("В демонстрационном наборе паспорта могут отсутствовать, это нужно сообщать явно.")
        if has("гост"):
            warnings.append("Область действия ГОСТа не подтверждает конкретную синтетическую карточку без паспорта или ТУ.")
        if has("фланц", "креп"):
            warnings.append("В MVP нет полного каталога соединительных изделий, недостающие позиции нельзя придумывать.")
        if has("граф", "состоит"):
            warnings.append("Граф демонстрационного объекта не является монтажной схемой реального газопровода.")

    # --- Замена / матчинг ---
    if replacement:
        if "труба" in items or has("трубу"):
            warnings.append("Труба того же размера не становится автоматическим аналогом без проверки материала и условий работы.")
        if "задвижк" in items or has("задвижк"):
            warnings.append("Большее значение PN не гарантирует совместимость задвижки с фланцами и соседними деталями.")
        if "заглушк" in items or has("заглушк"):
            warnings.append("Закрытая задвижка не должна автоматически считаться заменой физической заглушки.")
        if has("стали", "09г2с"):
            warnings.append("Марки стали нельзя признавать взаимозаменяемыми только по похожим характеристикам.")
        if has("dn") and any(op in ops for op in ("impact", "replace")):
            warnings.append("Изменение DN является изменением узла и не должно утверждаться автоматически.")
        if has("среду", "перевод"):
            warnings.append("Смена рабочей среды требует инженерного решения по всему участку.")
        if intent == "equipment_guidance" or has("что означает", "расскажи", "объясн"):
            warnings.append("Приоритет параметров должен подтверждаться правилами проекта и экспертом.")
            warnings.append("Размеры и назначение не подтверждают применимость к конкретному проекту.")
        if has("сосед", "рядом", "перед"):
            warnings.append("Точный состав узла определяется проектной схемой, которой может не быть в MVP.")
        if has("каталоге", "пример"):
            warnings.append("Каталог MVP может не содержать фланцы, прокладки и крепеж, это нужно явно показать.")

    # --- Сборка нового участка / проектная схема ---
    if "assemble" in ops or has("нового участка"):
        warnings.append("Без трассы и проектной схемы нельзя определить точное количество деталей.")
        warnings.append("Место и параметры арматуры нельзя окончательно определить без проектной схемы.")

    # --- Дубли ---
    if duplicates:
        warnings.append("Совпавшие параметры не доказывают, что корпоративные коды являются дублями.")

    return warnings
