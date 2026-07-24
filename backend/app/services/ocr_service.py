import os
import re
from typing import List, Dict, Any, Optional
import fitz
import numpy as np
import cv2

os.environ["FLAGS_use_onednn"] = "0"
os.environ["FLAGS_allocator_strategy"] = "naive_best_fit"

try:
    from paddleocr import PaddleOCR
    PADDLE_AVAILABLE = True
except ImportError:
    PADDLE_AVAILABLE = False
    print("PaddleOCR не установлен.")


class OCRService:
    def __init__(self, use_paddle: bool = True):
        self.use_paddle = use_paddle and PADDLE_AVAILABLE
        self._ocr = None

    @property
    def ocr(self):
        if self._ocr is None and self.use_paddle:
            self._ocr = PaddleOCR(
                use_textline_orientation=True,
                lang='ru',
                enable_mkldnn=False
            )
        return self._ocr

    def extract_text_from_pdf(self, pdf_path: str) -> List[Dict[str, Any]]:
        results = []

        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"Файл не найден: {pdf_path}")

        if not self.use_paddle:
            return self._extract_text_fallback(pdf_path)

        doc = fitz.open(pdf_path)

        for page_num in range(len(doc)):
            page = doc[page_num]
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            img_data = np.frombuffer(pix.samples, dtype=np.uint8).reshape((pix.h, pix.w, pix.n))

            if pix.n == 3:
                img_data = cv2.cvtColor(img_data, cv2.COLOR_RGB2BGR)

            try:
                result = list(self.ocr.predict(img_data))[0]

                page_lines = []
                confidence = 0.0

                if result and 'rec_texts' in result:
                    page_lines = result['rec_texts']
                    confidence = result.get('rec_scores', [0.0])[0] if result.get('rec_scores') else 0.0
                elif result:
                    for line in result:
                        if isinstance(line, list) and len(line) > 1:
                            page_lines.append(line[0])

                text = '\n'.join(page_lines)

                tables = self._extract_tables_from_text(text, page_lines)

                results.append({
                    'page_number': page_num + 1,
                    'text': text,
                    'confidence': confidence if confidence else 0.8,
                    'tables': tables,
                    'rotation': 0
                })

            except Exception as e:
                print(f"Ошибка OCR на странице {page_num + 1}: {e}")
                results.append({
                    'page_number': page_num + 1,
                    'text': f"Ошибка: {e}",
                    'confidence': 0.0,
                    'tables': [],
                    'rotation': 0
                })

        doc.close()
        return results

    def _extract_tables_from_text(self, text: str, lines: List[str]) -> List[Dict[str, Any]]:
        tables = []

        if not lines:
            return tables

        table_candidates = []
        current_table = []

        for line in lines:
            cleaned = line.strip()
            if not cleaned:
                if current_table:
                    table_candidates.append(current_table)
                    current_table = []
                continue

            is_table_row = False

            if re.search(r'\s{2,}', cleaned):
                is_table_row = True

            if re.search(r'\d+\s*(?:мм|МПа|°|кг|см|дюйм)', cleaned):
                is_table_row = True

            if any(marker in cleaned for marker in ['DN', 'PN', 'ГОСТ', 'ТУ']):
                is_table_row = True

            if is_table_row:
                current_table.append(cleaned)
            else:
                if current_table:
                    table_candidates.append(current_table)
                    current_table = []

        if current_table:
            table_candidates.append(current_table)

        for table_lines in table_candidates:
            if len(table_lines) < 2:
                continue

            parsed = self._parse_table_auto(table_lines)
            if parsed:
                tables.append(parsed)

        return tables

    def _parse_table_auto(self, lines: List[str]) -> Dict[str, Any]:

        if not lines:
            return {}

        rows = []
        for line in lines:
            cleaned = line.strip()
            if not cleaned:
                continue

            # Пытаемся разбить по множественным пробелам
            parts = re.split(r'\s{2,}', cleaned)
            parts = [p.strip() for p in parts if p.strip()]

            if not parts:
                parts = re.split(r'\t+', cleaned)
                parts = [p.strip() for p in parts if p.strip()]

            if not parts:
                parts = [cleaned]

            rows.append(parts)

        if not rows:
            return {}

        max_cols = max(len(row) for row in rows)
        for row in rows:
            while len(row) < max_cols:
                row.append('')

        return {
            'rows': rows,
            'headers': rows[0] if rows else [],
            'row_count': len(rows),
            'col_count': max_cols,
            'confidence': 0.85
        }

    def _extract_text_fallback(self, pdf_path: str) -> List[Dict[str, Any]]:
        doc = fitz.open(pdf_path)
        results = []

        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text()

            results.append({
                'page_number': page_num + 1,
                'text': text,
                'confidence': 0.0,
                'tables': [],
                'rotation': 0
            })

        doc.close()
        return results


def get_ocr_service() -> 'OCRService':
    return OCRService(use_paddle=PADDLE_AVAILABLE)
