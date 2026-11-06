"""
OCR Service Interface & Quality Assessment.
Defines abstract interface for text, layout, and table extraction with quality scoring.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import re

class BaseOCRService(ABC):
    @abstractmethod
    def extract_text(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Extract text from file.
        Returns list of pages:
        [ {"page_number": int, "text": str, "confidence": float}, ... ]
        """
        pass

    @abstractmethod
    def extract_layout(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Extract layout blocks with coordinates and line structures.
        """
        pass

    @abstractmethod
    def extract_tables(self, file_path: str) -> List[List[List[str]]]:
        """
        Extract structured tabular data if present.
        """
        pass

    @staticmethod
    def calculate_quality(pages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculates OCR quality score (0.0 to 1.0) based on:
        - confidence scores
        - text volume
        - presence of suspicious / garbled characters (, excessive non-alphanumeric)
        - recognition of clinical key terms (e.g., Result, Reference, Unit, Test, etc.)
        """
        if not pages:
            return {
                "score": 0.0,
                "is_low_quality": True,
                "warning": "No text could be extracted from the file. Please upload a clearer report."
            }

        total_chars = 0
        garbled_chars = 0
        avg_confidence = 0.0

        medical_keywords = [
            "test", "result", "unit", "reference", "range", "normal",
            "serum", "blood", "pathology", "haemoglobin", "glucose",
            "cholesterol", "alt", "ast", "creatinine"
        ]
        found_keywords = set()

        for page in pages:
            text = page.get("text", "")
            conf = page.get("confidence", 0.9)
            avg_confidence += conf
            total_chars += len(text)

            # Count garbled characters or replacement chars
            garbled_chars += len(re.findall(r'[^\x20-\x7E\n\r\t]', text))
            
            # Check keywords
            lower_text = text.lower()
            for kw in medical_keywords:
                if kw in lower_text:
                    found_keywords.add(kw)

        avg_confidence = avg_confidence / len(pages) if pages else 0.0

        if total_chars < 50:
            return {
                "score": 0.2,
                "is_low_quality": True,
                "warning": "Report quality is low. Very little readable text was detected. Please upload a clearer report."
            }

        garbled_ratio = garbled_chars / max(total_chars, 1)
        keyword_coverage = min(len(found_keywords) / 4.0, 1.0)

        # Quality formula
        quality_score = (avg_confidence * 0.4) + (keyword_coverage * 0.4) + ((1.0 - min(garbled_ratio * 10, 1.0)) * 0.2)
        quality_score = round(max(0.0, min(quality_score, 1.0)), 2)

        is_low = quality_score < 0.65
        warning = None
        if is_low:
            warning = "Report quality is low. Some values may not have been read correctly. Please upload a clearer report."

        return {
            "score": quality_score,
            "is_low_quality": is_low,
            "warning": warning,
            "total_chars": total_chars,
            "garbled_ratio": round(garbled_ratio, 3),
            "medical_keywords_found": list(found_keywords)
        }

