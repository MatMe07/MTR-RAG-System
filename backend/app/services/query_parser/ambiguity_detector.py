# query_parser/ambiguity_detector.py

from dataclasses import dataclass
from typing import List


@dataclass
class Ambiguity:
    field: str
    reason: str
    severity: str
    values: List[str]


class AmbiguityDetector:

    def detect(self, text: str, card_data: dict) -> list[Ambiguity]:
        result = []

        self._check_multiple_dn(text, result)
        self._check_multiple_angles(text, result)
        self._check_pressure_geometry_conflict(text, card_data, result)
        self._check_missing_item_type(text, card_data, result)

        return result

    def _check_multiple_dn(
        self,
        text: str,
        result: list[Ambiguity],
    ):
        import re

        values = re.findall(
            r"\b(?:dn|ду)\s*[-:]?\s*(\d+(?:[.,]\d+)?)",
            text.lower(),
        )

        unique = list(dict.fromkeys(values))

        if len(unique) > 1:
            result.append(
                Ambiguity(
                    field="geometry.dn",
                    reason="В запросе указано несколько DN",
                    severity="high",
                    values=unique,
                )
            )

    def _check_multiple_angles(
        self,
        text: str,
        result: list[Ambiguity],
    ):
        import re

        values = re.findall(
            r"\b(30|45|60|90)\s*°?\b",
            text.lower(),
        )

        unique = list(dict.fromkeys(values))

        if len(unique) > 1:
            result.append(
                Ambiguity(
                    field="geometry.angle",
                    reason="В запросе указано несколько возможных углов",
                    severity="medium",
                    values=unique,
                )
            )

    def _check_pressure_geometry_conflict(
        self,
        text: str,
        card_data: dict,
        result: list[Ambiguity],
    ):
        import re

        # Например:
        # "отвод 90 426 на 10"
        #
        # 10 не должен стать PN.
        if re.search(
            r"\b(?:отвод|труба|окш|ог)\b.*\d+\s+(?:на|x|х|×)\s+\d+",
            text.lower(),
        ):
            pressure = card_data.get("pressure", {})

            if pressure.get("pn") is not None:
                result.append(
                    Ambiguity(
                        field="pressure.pn",
                        reason=(
                            "Числовое значение может быть частью "
                            "геометрии изделия"
                        ),
                        severity="low",
                        values=[str(pressure["pn"])],
                    )
                )

    def _check_missing_item_type(
        self,
        text: str,
        card_data: dict,
        result: list[Ambiguity],
    ):
        if not card_data.get("item_type"):
            result.append(
                Ambiguity(
                    field="item_type",
                    reason="Не удалось определить тип изделия",
                    severity="high",
                    values=[],
                )
            )
