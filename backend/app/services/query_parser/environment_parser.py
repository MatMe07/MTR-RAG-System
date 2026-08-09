# query_parser/environment_parser.py

import re
from typing import Dict, Any

from .dictionaries import MEDIUM_ALIASES, CLIMATE_ALIASES


class EnvironmentParser:

    def parse(self, text: str) -> Dict[str, Any]:
        result = {
            "medium": None,
            "h2s_confirmed": None,
            "co2_confirmed": None,
            "temperature_min_c": None,
            "climate_version": None,
        }

        normalized = text.lower()
        
        has_unit_h2s = bool(re.search(r'unit[\-_\s]*h2s', normalized, re.IGNORECASE))
        has_unit_co2 = bool(re.search(r'unit[\-_\s]*co2', normalized, re.IGNORECASE))

        # ---------------------------------------------------------
        # 0. Проверка: H2S/CO2 в названии UNIT – ИСПРАВЛЕНО
        # ---------------------------------------------------------
        # Усиленная проверка на UNIT-...-H2S-... или UNIT_SYN_H2S
        if has_unit_h2s or has_unit_co2:
            # Среда в названии участка – игнорируем
            pass
        else:
            # ---------------------------------------------------------
            # 1. Среда
            # ---------------------------------------------------------
            for alias, medium in MEDIUM_ALIASES.items():
                if re.search(rf"(?<![а-яёa-z]){re.escape(alias)}(?![а-яёa-z])", normalized):
                    result["medium"] = medium
                    if medium == "H2S":
                        result["h2s_confirmed"] = True
                    elif medium == "CO2":
                        result["co2_confirmed"] = True
                    break

            if re.search(r"(?:для|с|на)\s+h2s", normalized):
                result["h2s_confirmed"] = True
                if result["medium"] is None:
                    result["medium"] = "H2S"

            if re.search(r"(?:для|с|на)\s+co2", normalized):
                result["co2_confirmed"] = True
                if result["medium"] is None:
                    result["medium"] = "CO2"

        # ---------------------------------------------------------
        # 2. Климат
        # ---------------------------------------------------------
        result["climate_version"] = self._parse_climate(text)

        # ---------------------------------------------------------
        # 3. Температура
        # ---------------------------------------------------------
        temp_keywords = r"(?:температур[аы]|град|до\s*|от\s*|при\s*)"
        temp_match = re.search(
            rf"{temp_keywords}([-+]?\d+(?:[.,]\d+)?)",
            normalized,
            re.IGNORECASE
        )
        if temp_match:
            result["temperature_min_c"] = float(temp_match.group(1).replace(',', '.'))

        return result

    def _parse_climate(self, text: str) -> str:
        """Извлекает климатическое исполнение с проверкой контекста"""
        text_lower = text.lower()
        
        # 1. Сначала ищем составные: УХЛ, УХЛ1, ХЛ, ХЛ1, Т
        for alias, climate in CLIMATE_ALIASES.items():
            if alias in ['ухл', 'ухл1', 'хл', 'хл1', 'т']:
                if re.search(rf"(?<![а-яёa-z]){re.escape(alias)}(?![а-яёa-z])", text_lower):
                    return climate

        # 2. Ищем "У" как климатическое исполнение
        #    ТОЛЬКО если это не предлог "у" в начале предложения или части слова
        #    Ищем "У" в конце строки, после запятой, после тире, или в скобках
        climate_u_patterns = [
            r',\s*у\b',           # ", у" после запятой
            r'\s+у\b',            # " у" отдельно
            r'\(у\)',             # "(у)" в скобках
            r'исполнени[ея]\s+у\b',  # "исполнение У"
            r'климат\s+у\b',      # "климат У"
            r'\bу\s*[,;]',        # "у," или "у;"
            r'-\s*у\b',           # "- у" после тире
            r'у\s+[хл]',          # часть УХЛ, но это уже обработано выше
        ]
        
        for pattern in climate_u_patterns:
            if re.search(pattern, text_lower):
                return "У"

        # 3. Если "у" стоит отдельно и НЕ является предлогом
        #    Проверяем: после "у" должно быть слово, которое не является глаголом/местоимением
        #    И "у" не должно быть в начале предложения
        words = re.findall(r'\b\w+\b', text_lower)
        for i, word in enumerate(words):
            if word == 'у' and i > 0:
                # Проверяем, что это не предлог "у меня", "у нас", "у него"
                next_word = words[i + 1] if i + 1 < len(words) else ''
                if next_word in ['меня', 'нас', 'него', 'нее', 'них', 'вас', 'тебя', 'себя']:
                    continue  # это предлог
                # Проверяем, что перед "у" не стоит точка или начало предложения
                prev_word = words[i - 1] if i - 1 >= 0 else ''
                if prev_word and prev_word not in [',', ';', 'и', 'а', 'но', 'или']:
                    # Если перед "у" есть слово, и это не часть фразы "У меня"
                    # и "у" не в начале предложения
                    return "У"

        return None
