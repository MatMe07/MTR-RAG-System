# backend/app/tests/test_ocr.py

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.services.ocr_service import OCRService


def test_ocr(pdf_path: str):
    print(f"Тестируем OCR на файле: {pdf_path}")
    print("-" * 50)

    ocr = OCRService(use_paddle=True)

    try:
        results = ocr.extract_text_from_pdf(pdf_path)
    except Exception as e:
        print(f"Ошибка: {e}")
        return

    print(f"Всего страниц: {len(results)}")
    print("-" * 50)

    for page in results:
        print(f"\n--- Страница {page['page_number']} ---")
        print(f"Уверенность: {page['confidence']:.2%}")
        print(f"Текст ({len(page['text'])} символов):")

        text_preview = page['text'][:300]
        if len(page['text']) > 300:
            text_preview += "..."
        print(text_preview if text_preview else "(текст не распознан)")

        if page['tables']:
            print(f"\nНайдено таблиц: {len(page['tables'])}")
            for i, table in enumerate(page['tables']):
                print(f"\nТаблица {i+1}: {table['row_count']} строк, {table['col_count']} колонок")
                print("-" * 30)
                for row in table['rows']:
                    print(" | ".join(row))
                print("-" * 30)

    print("\n" + "-" * 50)
    print("Тест завершен")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("pdf_path", help="Путь к PDF-файлу")
    args = parser.parse_args()

    test_ocr(args.pdf_path)
