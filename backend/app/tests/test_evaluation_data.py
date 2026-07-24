import csv
import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def read_jsonl(path: Path):
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


class EvaluationDataTest(unittest.TestCase):
    def test_document_manifest_uses_known_dcd_values(self):
        taxonomy = json.loads(
            (REPO_ROOT / "docs/domain/dcd_taxonomy.json").read_text(encoding="utf-8")
        )
        collection_codes = {
            collection["code"]
            for collection in taxonomy["collections"]
        }
        with (REPO_ROOT / "data/sample/document_manifest.csv").open(
            "r",
            encoding="utf-8",
            newline="",
        ) as file:
            documents = list(csv.DictReader(file, delimiter=";"))

        self.assertEqual(len(documents), 20)
        self.assertEqual(len({row["document_id"] for row in documents}), 20)
        for row in documents:
            self.assertEqual(row["domain_code"], taxonomy["domain"]["code"])
            self.assertIn(row["collection_code"], collection_codes)
            self.assertTrue(
                (REPO_ROOT / "data/sample" / row["file_name"]).is_file(),
                row["file_name"],
            )

    def test_complex_queries_and_assertions_are_consistent(self):
        complex_queries = read_jsonl(
            REPO_ROOT / "data/evaluation/complex_queries.jsonl"
        )
        assertions = read_jsonl(
            REPO_ROOT / "data/evaluation/golden_assertions.jsonl"
        )
        with (REPO_ROOT / "data/sample/golden_dataset.csv").open(
            "r",
            encoding="utf-8",
            newline="",
        ) as file:
            golden_ids = {
                row["case_id"]
                for row in csv.DictReader(file, delimiter=";")
            }

        self.assertEqual(len(complex_queries), 10)
        self.assertEqual(len({row["case_id"] for row in complex_queries}), 10)
        self.assertTrue(
            all(
                row["expected_route"] in {"ordinary", "clarification", "agent"}
                for row in complex_queries
            )
        )
        self.assertTrue(
            {row["case_id"] for row in assertions}.issubset(golden_ids)
        )


if __name__ == "__main__":
    unittest.main()
