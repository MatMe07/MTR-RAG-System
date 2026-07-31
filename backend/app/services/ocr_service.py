# backend/app/services/ocr_service.py

import os
from typing import List, Dict, Any
from docling.document_converter import DocumentConverter
from docling.datamodel.pipeline_options import (PdfPipelineOptions,AcceleratorOptions,
    AcceleratorDevice, EasyOcrOptions)
from docling.datamodel.base_models import InputFormat
from docling.document_converter import DocumentConverter, PdfFormatOption

class OCRService:
    def __init__(self):
        pipeline_options = PdfPipelineOptions()
        pipeline_options.do_ocr = True
        pipeline_options.do_table_structure = True
        pipeline_options.ocr_options = EasyOcrOptions(
            lang=["ru", "en"]
        )
        
        pipeline_options.accelerator_options = AcceleratorOptions(
            num_threads=4,
            device=AcceleratorDevice.AUTO  
        )
        self.converter = DocumentConverter(
                format_options={
                    InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
                }
            )

    def extract_text_from_pdf(self, pdf_path: str) -> List[Dict[str, Any]]:
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"Файл не найден: {pdf_path}")

        result = self.converter.convert(pdf_path)
        doc_dict = result.document.export_to_dict()

        pages_data = {}
        tables_data = {}

        for text_item in doc_dict.get("texts", []):
            page_no = text_item.get("prov", [{}])[0].get("page_no")
            if page_no is None:
                continue
            if page_no not in pages_data:
                pages_data[page_no] = []
            pages_data[page_no].append(text_item.get("text", ""))

        for table_item in doc_dict.get("tables", []):
            page_no = table_item.get("prov", [{}])[0].get("page_no")
            if page_no is None:
                continue
            if page_no not in tables_data:
                tables_data[page_no] = []
            grid = table_item.get("data", {}).get("grid", [])
            rows = []
            for row in grid:
                row_texts = [cell.get("text", "") for cell in row]
                rows.append(row_texts)
            tables_data[page_no].append({
                "rows": rows,
                "headers": rows[0] if rows else []
            })

        results = []
        all_pages = set(pages_data.keys()) | set(tables_data.keys())
        for page_num in sorted(all_pages):
            text = "\n".join(pages_data.get(page_num, []))
            tables = tables_data.get(page_num, [])
            results.append({
                "page_number": page_num,
                "text": text,
                "tables": tables,
                "confidence": 0.95,
                "rotation": 0
            })
        # print(results)
        return results

    def extract_text_from_bytes(self, file_bytes: bytes, file_name: str = "document.pdf") -> List[Dict[str, Any]]:
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name
        try:
            return self.extract_text_from_pdf(tmp_path)
        finally:
            os.unlink(tmp_path)


def get_ocr_service() -> OCRService:
    return OCRService()
