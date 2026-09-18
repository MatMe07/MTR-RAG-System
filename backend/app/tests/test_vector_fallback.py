# app/tests/test_vector_fallback.py

"""P2-20: семантический fallback в search_catalog помечает результаты source="vector_fallback".

Атрибутный (детерминированный) путь не трогается; при пустом детерминированном
поиске результаты semantic-провайдера получают метку и доводятся до полной карточки.
"""

from app.services.agent.llm.refine_loop import run_refine_loop  # noqa: F401,E402  # порядок импорта (circular import)
from app.services.agent.tools.tool_dal import ToolDAL


def _card(card_id, ksm=None):
    return {
        "card_id": card_id,
        "item_type": "задвижка",
        "name": card_id,
        "codes": {"ksm_code": ksm or f"KSM-{card_id}", "mtr_code": f"MTR-{card_id}"},
        "properties": {"dn": {"value": 100}},
    }


class _RepoNoSemantic:
    """Атрибутный каталог без semantic-метода."""

    def __init__(self, cards):
        self._cards = cards

    def get_catalog(self):
        return list(self._cards)


class _RepoWithSemantic:
    """Пустой каталог + семантический fallback."""

    def __init__(self, hits):
        self._hits = hits

    def get_catalog(self):
        return []

    def get_card_by_ksm(self, ksm):
        for h in self._hits:
            if h["card"].get("codes", {}).get("ksm_code") == ksm:
                return h["card"]
        return None

    def search_catalog_semantic(self, query, limit=5):
        return [dict(h) for h in self._hits]


class TestVectorFallbackLabel:
    def test_attribute_path_not_tagged(self):
        cards = [_card("A"), _card("B")]
        out = ToolDAL(_RepoNoSemantic(cards)).search_catalog({"item_type": "задвижка"})
        assert out, "атрибутный путь должен вернуть результат"
        assert all("source" not in r for r in out)
        assert [r["card"]["card_id"] for r in out] == ["A", "B"]

    def test_fallback_hits_tagged(self):
        hits = [{"card": _card("V1", ksm="KSM-V1"), "score": 0.91}]
        out = ToolDAL(_RepoWithSemantic(hits)).search_catalog({"item_type": "нет-такого"})
        assert len(out) == 1
        assert out[0]["source"] == "vector_fallback"
        assert out[0]["card"]["card_id"] == "V1"
        assert out[0]["score"] == 0.91

    def test_update_component_from_partial_payload(self):
        partial = {
            "ksm_code": "KSM-PART",
            "text": "задвижка клиновая",
            "item_type": "задвижка",
        }
        full = _card("FULL", ksm="KSM-PART")
        hits = [{"card": partial, "score": 0.8}]

        class _RepoFull(_RepoWithSemantic):
            def __init__(self):
                super().__init__(hits)

            def get_card_by_ksm(self, ksm):
                return full if ksm == "KSM-PART" else None

        out = ToolDAL(_RepoFull()).search_catalog({"item_type": "задвижка"})
        assert out[0]["card"]["card_id"] == "FULL"
        assert (out[0]["card"].get("codes") or {}).get("ksm_code") == "KSM-PART"

    def test_fallback_request_is_semantic_query(self):
        captured = {}

        class _RepoCapture(_RepoNoSemantic):
            def get_catalog(self):
                return []

            def search_catalog_semantic(self, query, limit=5):
                captured["query"] = query
                captured["limit"] = limit
                return [{"card": _card("X"), "score": 0.5}]

        out = ToolDAL(_RepoCapture([])).search_catalog(
            {"item_type": "задвижка", "dn": 100, "pn": 16}
        )
        assert out and out[0]["source"] == "vector_fallback"
        assert "задвижка" in captured["query"]
        assert "100" in captured["query"]
        assert captured["limit"] == 5