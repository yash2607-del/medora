"""
PDF Extraction Engine using PyMuPDF (fitz) and pypdf fallback.
Extracts multi-page text, layout blocks, and structured tables with provenance metadata.
"""

import os
from typing import List, Dict, Any
from .ocr_service import BaseOCRService

try:
    import fitz # PyMuPDF
    HAVE_FITZ = True
except ImportError:
    HAVE_FITZ = False

try:
    import pypdf
    HAVE_PYPDF = True
except ImportError:
    HAVE_PYPDF = False


class PDFProcessor(BaseOCRService):
    def extract_text(self, file_path: str) -> List[Dict[str, Any]]:
        if not os.path.exists(file_path):
            return []

        pages = []
        if HAVE_FITZ:
            try:
                doc = fitz.open(file_path)
                for page_num in range(len(doc)):
                    page = doc[page_num]
                    text = page.get_text("text")
                    # PyMuPDF digital extract confidence is high if text found
                    conf = 0.98 if len(text.strip()) > 30 else 0.5
                    pages.append({
                        "page_number": page_num + 1,
                        "text": text,
                        "confidence": conf
                    })
                doc.close()
                if pages and any(len(p["text"].strip()) > 0 for p in pages):
                    return pages
            except Exception as e:
                print(f"[PyMuPDF Warning] Fallback due to: {e}")

        # Fallback to pypdf
        if HAVE_PYPDF:
            try:
                reader = pypdf.PdfReader(file_path)
                for i, page in enumerate(reader.pages):
                    text = page.extract_text() or ""
                    pages.append({
                        "page_number": i + 1,
                        "text": text,
                        "confidence": 0.95 if len(text.strip()) > 30 else 0.4
                    })
                return pages
            except Exception as e:
                print(f"[pypdf Warning] Fallback failed: {e}")

        return pages

    def extract_layout(self, file_path: str) -> List[Dict[str, Any]]:
        layout_pages = []
        if HAVE_FITZ:
            try:
                doc = fitz.open(file_path)
                for page_num in range(len(doc)):
                    page = doc[page_num]
                    blocks = page.get_text("blocks") # (x0, y0, x1, y1, text, block_no, block_type)
                    page_blocks = []
                    for b in blocks:
                        if len(b) >= 5 and b[4].strip():
                            page_blocks.append({
                                "bbox": [b[0], b[1], b[2], b[3]],
                                "text": b[4].strip()
                            })
                    layout_pages.append({
                        "page_number": page_num + 1,
                        "blocks": page_blocks
                    })
                doc.close()
            except Exception as e:
                print(f"[PDF Layout Error] {e}")
        return layout_pages

    def extract_tables(self, file_path: str) -> List[List[List[str]]]:
        all_tables = []
        if HAVE_FITZ:
            try:
                doc = fitz.open(file_path)
                for page in doc:
                    if hasattr(page, "find_tables"):
                        tables = page.find_tables()
                        for table in tables:
                            all_tables.append(table.extract())
                doc.close()
            except Exception as e:
                print(f"[PDF Table Extract Error] {e}")
        return all_tables

