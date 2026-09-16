# app/tests/test_safety_checks.py

"""P0: безопасный H2S/CO2-фильтр в search_catalog (filter-only-false).

Из результатов поиска для H2S/CO2-запроса исключаются карточки с ЯВНЫМ
значением h2s_confirmed=false / co2_confirmed=false. unknown (null) и true
остаются — unknown далее помечается verifier gap safety_unconfirmed.
"""

from app.services.agent.llm.refine_loop import run_refine_loop  # noqa: F401,E402  # порядок импорта (circular import)
from app.services.agent.tools.tool_dal import ToolDAL


class _Repo:
    """Фейковый репозиторий: только каталог, без семантического fallback."""

    def __init__(self, cards):
        self._cards = cards

    def get_catalog(self):
        return list(self._cards)


def _card(card_id, medium=None, h2s=None, co2=None):
    props = {}
    if medium is not None:
        props["medium"] = {"value": medium}
    if h2s is not None:
        props["h2s_confirmed"] = {"value": h2s}
    if co2 is not None:
        props["co2_confirmed"] = {"value": co2}
    return {
        "card_id": card_id,
        "item_type": "отвод",
        "name": card_id,
        "codes": {"ksm_code": f"KSM-{card_id}", "mtr_code": f"MTR-{card_id}"},
        "properties": props,
    }


def _dal(cards):
    return ToolDAL(_Repo(cards))


def _hits(records):
    return [r["card"]["card_id"] for r in records]


class TestH2SFilter:
    def test_h2s_query_keeps_true_and_null(self):
        cards = [
            _card("TRUE", medium="H2S", h2s=True),
            _card("NULL", medium="H2S", h2s=None),
            _card("FALSE", medium="H2S", h2s=False),
        ]
        out = _hits(_dal(cards).search_catalog({"item_type": "отвод", "medium": "H2S"}))
        assert out == ["TRUE", "NULL"]

    def test_h2s_flag_in_params(self):
        cards = [
            _card("TRUE", medium="газ", h2s=True),
            _card("FREE", medium="газ", h2s=False),
        ]
        out = _hits(_dal(cards).search_catalog({"item_type": "отвод", "h2s_confirmed": True}))
        assert out == ["TRUE"]

    def test_cyrillic_serovodorod(self):
        cards = [
            _card("OK", medium="сероводород", h2s=None),
            _card("NO", medium="сероводород", h2s=False),
        ]
        out = _hits(_dal(cards).search_catalog({"item_type": "отвод", "medium": "сероводород"}))
        assert out == ["OK"]

    def test_non_h2s_query_not_affected(self):
        cards = [
            _card("A", medium="пар", h2s=False),
            _card("B", medium="пар", h2s=True),
        ]
        out = _hits(_dal(cards).search_catalog({"item_type": "отвод", "medium": "пар"}))
        assert out == ["A", "B"]


class TestCO2Filter:
    def test_co2_excludes_explicit_false(self):
        cards = [
            _card("OK", medium="CO2", co2=True),
            _card("UNKNOWN", medium="CO2", co2=None),
            _card("NO", medium="CO2", co2=False),
        ]
        out = _hits(_dal(cards).search_catalog({"item_type": "отвод", "medium": "CO2"}))
        assert out == ["OK", "UNKNOWN"]


class TestCombined:
    def test_h2s_and_co2_independent(self):
        cards = [
            _card("H_TRUE_C_FALSE", medium="H2S/CO2", h2s=True, co2=False),
            _card("BOTH_TRUE", medium="H2S/CO2", h2s=True, co2=True),
            _card("H_FALSE", medium="H2S/CO2", h2s=False, co2=True),
        ]
        dal = _dal(cards)
        out = _hits(dal.search_catalog({"item_type": "отвод", "medium": "H2S/CO2"}))
        assert out == ["BOTH_TRUE"]
