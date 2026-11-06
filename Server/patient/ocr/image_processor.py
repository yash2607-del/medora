"""
Image Processor for report photographs, scanned JPG/PNG images.
Handles contrast, sharpness, image metrics, and pluggable OCR engine.
"""

import os
from typing import List, Dict, Any
from PIL import Image, ImageStat
from .ocr_service import BaseOCRService

class ImageProcessor(BaseOCRService):
    def __init__(self):
        self.have_tesseract = False
        try:
            import pytesseract
            self.pytesseract = pytesseract
            self.have_tesseract = True
        except ImportError:
            self.pytesseract = None

    def assess_image_clarity(self, image_path: str) -> Dict[str, Any]:
        """
        Calculates image resolution, contrast, and brightness to detect blurry or dark photos.
        """
        try:
            with Image.open(image_path) as img:
                w, h = img.size
                stat = ImageStat.Stat(img.convert("L"))
                variance = stat.var[0] if stat.var else 0.0
                mean_brightness = stat.mean[0] if stat.mean else 128.0

                is_blurry = variance < 50.0 # low contrast / blurry
                is_too_dark = mean_brightness < 40.0
                is_too_bright = mean_brightness > 240.0

                confidence = 0.9
                if is_blurry or is_too_dark or is_too_bright:
                    confidence = 0.4
                elif w < 800 or h < 800:
                    confidence = 0.6

                return {
                    "width": w,
                    "height": h,
                    "variance": variance,
                    "mean_brightness": mean_brightness,
                    "confidence": confidence,
                    "is_acceptable": not (is_blurry or is_too_dark)
                }
        except Exception as e:
            return {"confidence": 0.2, "is_acceptable": False, "error": str(e)}

    def extract_text(self, file_path: str) -> List[Dict[str, Any]]:
        if not os.path.exists(file_path):
            return []

        clarity = self.assess_image_clarity(file_path)
        extracted_text = ""
        conf = clarity.get("confidence", 0.7)

        # 1. Try pytesseract if installed
        if self.have_tesseract and self.pytesseract:
            try:
                with Image.open(file_path) as img:
                    extracted_text = self.pytesseract.image_to_string(img)
            except Exception as e:
                print(f"[Tesseract Warning] {e}")

        # 2. If no text or pytesseract not present, inspect with PyMuPDF or return empty
        if not extracted_text:
            try:
                import fitz
                # Create a temporary PDF from the image and extract or check layout
                doc = fitz.open(file_path)
                for page in doc:
                    extracted_text += page.get_text()
                doc.close()
            except Exception:
                pass

        return [{
            "page_number": 1,
            "text": extracted_text,
            "confidence": conf
        }]

    def extract_layout(self, file_path: str) -> List[Dict[str, Any]]:
        return [{
            "page_number": 1,
            "blocks": []
        }]

    def extract_tables(self, file_path: str) -> List[List[List[str]]]:
        return []

