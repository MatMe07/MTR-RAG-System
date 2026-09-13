# test_json_utils.py

"""Проверка извлечения JSON из прозаического вывода LLM (P3.3)."""

import unittest

from app.services.agent.llm.json_utils import extract_json_object


class ExtractJsonObjectTest(unittest.TestCase):
    def test_pure_json(self):
        self.assertEqual(extract_json_object('{"a": 1}'), {"a": 1})

    def test_prose_around_json(self):
        text = 'Нашёл деталь: {"action": "finish", "final_answer": "ok"} — вот лист.'
        data = extract_json_object(text)
        self.assertEqual(data["action"], "finish")

    def test_code_fences(self):
        text = "Ответ: ```json\n{\"action\": \"ask_user\", \"question\": \"DN?\"}\n```"
        data = extract_json_object(text)
        self.assertEqual(data["action"], "ask_user")

    def test_object_with_braces_inside_string(self):
        # Грех жадного regex: `}` внутри строкового значения не должен ломать разбор.
        text = '{"action": "finish", "final_answer": "деталь {A} и {B} — обе есть"}'
        data = extract_json_object(text)
        self.assertEqual(data["final_answer"], "деталь {A} и {B} — обе есть")

    def test_first_valid_object_when_multiple(self):
        text = '{"a": 1} затем {"b": 2}'
        self.assertEqual(extract_json_object(text), {"a": 1})

    def test_no_json_returns_none(self):
        self.assertIsNone(extract_json_object("просто текст без json"))
        self.assertIsNone(extract_json_object(""))


if __name__ == "__main__":
    unittest.main()
