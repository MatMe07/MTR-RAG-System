# test_source_lnd_section.py

"""P1-14: типизированная lnd_section в Source/AgentSource.

- format_sources отдаёт lnd_section из типизированного поля (fallback: id);
- search_norms проставляет lnd_section ЛНД-фрагментам (путь репозитория и fallback).
"""

import unittest

from app.schemas import AgentSource
from app.services.agent.answer.status import format_sources
from app.services.agent.tools.tool_dal import ToolDAL


class SourceLndSectionTest(unittest.TestCase):
    def test_format_sources_uses_typed_lnd_section(self):
        sources = [
            AgentSource(kind="lnd", id="лнд-7", lnd_section="раздел 4", fragment="..."),
        ]
        items = format_sources(sources)
        self.assertEqual(items[0]["type"], "lnd")
        self.assertEqual(items[0]["lnd_section"], "раздел 4")
        self.assertEqual(items[0]["description"], "...")

    def test_format_sources_fallback_to_id(self):
        sources = [AgentSource(kind="lnd", id="лнд-7", fragment="фрагмент")]
        items = format_sources(sources)
        self.assertEqual(items[0]["lnd_section"], "лнд-7")

    def test_format_sources_dict_rows(self):
        rows = [{"kind": "lnd", "id": "лнд-9", "lnd_section": "глава 3", "fragment": "x"}]
        items = format_sources(rows)
        self.assertEqual(items[0]["lnd_section"], "глава 3")

    def test_repo_path_decorates_lnd_fragments(self):
        class _Repo:
            def search_norms(self, query, limit=5, document_type=None):
                return [{
                    "fragment_id": "LND-0001",
                    "document_id": "lnd_extract.md",
                    "document_type": "ЛНД",
                    "title": "ЛНД",
                    "text": "Требование: применение прокладок по разделу 4",
                }]

            def get_regulation(self):
                return {}

        dal = ToolDAL(_Repo())
        frags = dal.search_norms("прокладки")
        self.assertEqual(frags[0]["lnd_section"], "раздел 4")

    def test_fallback_token_matcher_decorates_lnd(self):
        class _Repo:
            def get_regulation(self):
                return {"important_limitations": ["Среда: применять по главе 2"]}

        dal = ToolDAL(_Repo())
        frags = dal.search_norms("главе")
        self.assertTrue(frags)
        self.assertEqual(frags[0]["lnd_section"], "глава 2")


if __name__ == "__main__":
    unittest.main()
