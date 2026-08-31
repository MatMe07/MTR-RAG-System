# test_warning_groups.py

""""Фаза C: группировка предупреждений по категориям (group_warnings)."""

import unittest

from app.services.agent.answer.warnings import group_warnings


class GroupWarningsTest(unittest.TestCase):
    def test_groups_by_category(self):
        warnings = [
            "Пригодность к H2S нельзя подтверждать только по совпадению DN и PN.",
            "ГОСТ не присваивает внутренний код КСМ Роснефти.",
            "Расчёт — черновик: нормы запаса требуют утверждения.",
            "Окончательный приоритет зависит от эксперта.",
            "Какая-то нераспознанная строка.",
        ]
        grouped = group_warnings(warnings)
        self.assertIn("Совместимость со средой", grouped)
        self.assertIn("Достоверность данных", grouped)
        self.assertIn("Планирование и закупка", grouped)
        self.assertIn("Экспертная проверка", grouped)
        self.assertIn("Прочее", grouped)

    def test_no_duplicate_rows(self):
        warnings = ["ГОСТ не присваивает код КСМ."]
        grouped = group_warnings(warnings)
        self.assertIn("ГОСТ не присваивает код КСМ.", grouped["Достоверность данных"])

    def test_total_flat_count_preserved(self):
        warnings = ["a h2s", "b гост", "c черновик"] * 2
        grouped = group_warnings(warnings)
        flat = [w for ws in grouped.values() for w in ws]
        self.assertEqual(len(flat), len(warnings))


if __name__ == "__main__":
    unittest.main()
