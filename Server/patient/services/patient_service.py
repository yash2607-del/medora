"""
Patient Intelligence Orchestration Service.

Connects ingestion, OCR, extraction, normalization,
longitudinal analysis, and AI explanation workflows.

Security:
- File size limits enforced
- Filenames sanitized
- Per-patient upload subdirectory
- SHA-256 file hash for duplicate detection
- Errors surfaced safely
"""

import os
import re
import shutil
import uuid
import hashlib
from datetime import datetime
from typing import Dict, Any, List, Optional

from sqlalchemy.orm import Session

from ..repositories.patient_repository import PatientRepository
from ..ocr.pdf_processor import PDFProcessor
from ..ocr.image_processor import ImageProcessor
from ..ocr.ocr_service import BaseOCRService
from ..extraction.test_extractor import TestExtractor
from ..correlation.longitudinal_analyzer import LongitudinalAnalyzer
from ..generation.patient_report_generator import PatientReportGenerator
from ..generation.patient_chat_service import PatientChatService


# ── Upload directory ──────────────────────────────────────────────────────────

UPLOAD_BASE_DIR = os.path.join(
    os.path.dirname(
        os.path.dirname(
            os.path.dirname(
                os.path.abspath(__file__)
            )
        )
    ),
    "data",
    "patient",
    "uploads",
)

os.makedirs(UPLOAD_BASE_DIR, exist_ok=True)


# ── Config ─────────────────────────────────────────────────────────────────────

MAX_UPLOAD_BYTES = (
    int(os.getenv("PATIENT_MAX_UPLOAD_MB", "20")) * 1024 * 1024
)

ALLOWED_EXTENSIONS = {
    ".pdf",
    ".jpg",
    ".jpeg",
    ".png",
}

ALLOWED_MIME_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/jpg",
    "application/octet-stream",
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _safe_filename(original: str) -> str:
    name = os.path.basename(original)
    name = re.sub(r"[^\w\.\-]", "_", name)
    return name[:120]


def _patient_upload_dir(patient_id: str) -> str:
    safe_pid = re.sub(r"[^\w\-]", "_", patient_id)[:40]

    path = os.path.join(
        UPLOAD_BASE_DIR,
        safe_pid,
    )

    os.makedirs(path, exist_ok=True)

    return path


def _sha256(file_path: str) -> str:
    h = hashlib.sha256()

    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)

    return h.hexdigest()


def _ocr_quality_label(score: float) -> str:
    if score >= 0.75:
        return "GOOD"

    elif score >= 0.50:
        return "FAIR"

    return "POOR"


class PatientService:

    def __init__(self, db: Session):
        self.db = db
        self.repo = PatientRepository(db)

        self.pdf_proc = PDFProcessor()
        self.img_proc = ImageProcessor()

        self.report_gen = PatientReportGenerator()
        self.chat_svc = PatientChatService()

    # ── Patient Profiles ──────────────────────────────────────────────────────

    def list_patients(self) -> List[Dict[str, Any]]:

        patients = self.repo.list_patients()

        out = []

        for p in patients:

            reports = self.repo.list_patient_reports(
                p.patient_id
            )

            latest_date = (
                reports[-1].report_date
                if reports
                else None
            )

            out.append({
                "patient_id": p.patient_id,
                "name": p.name,
                "age": p.age,
                "gender": p.gender,
                "city": p.city,
                "state": p.state,
                "country": p.country,
                "date_of_birth": p.date_of_birth,
                "synthetic": p.synthetic,
                "total_reports": len(reports),
                "latest_report_date": latest_date,
            })

        return out

    def get_patient_profile(
        self,
        patient_id: str,
    ) -> Optional[Dict[str, Any]]:

        p = self.repo.get_patient(patient_id)

        if not p:
            return None

        reports = self.repo.list_patient_reports(
            patient_id
        )

        return {
            "patient_id": p.patient_id,
            "name": p.name,
            "age": p.age,
            "gender": p.gender,
            "city": p.city,
            "state": p.state,
            "country": p.country,
            "date_of_birth": p.date_of_birth,
            "synthetic": p.synthetic,
            "total_reports": len(reports),
            "latest_report_date": (
                reports[-1].report_date
                if reports
                else None
            ),
        }

    # ── Debug Data Cleanup ────────────────────────────────────────────────────

    def cleanup_debug_reports(
        self,
        patient_id: str = "P001",
    ) -> Dict[str, Any]:
        """
        Remove known duplicate/debug uploads created during development.

        This is intentionally limited to the known synthetic P001 debug
        reports and does not delete the newest valid report.

        KEEP:
            REP_3925C689

        DELETE:
            REP_EA6B9D0D
            REP_F8B330DD
            REP_51A74B9B
            REP_C27BE1E2
            REP_BD1883EF
            REP_E5752428
            REP_367622E4
            REP_B40A27F7
            REP_CD8A8ADC
        """

        if patient_id != "P001":
            raise ValueError(
                "Debug cleanup is restricted to synthetic patient P001."
            )

        reports_to_delete = [
            "REP_EA6B9D0D",
            "REP_F8B330DD",
            "REP_51A74B9B",
            "REP_C27BE1E2",
            "REP_BD1883EF",
            "REP_E5752428",
            "REP_367622E4",
            "REP_B40A27F7",
            "REP_CD8A8ADC",
        ]

        preserved_report_id = "REP_3925C689"

        deleted = []
        not_found = []

        for report_id in reports_to_delete:
            deleted_ok = self.repo.delete_report(
                patient_id=patient_id,
                report_id=report_id,
            )

            if deleted_ok:
                deleted.append(report_id)
            else:
                not_found.append(report_id)

        # Recalculate trends using only the remaining reports.
        trends = self.refresh_patient_trends(
            patient_id
        )

        remaining_reports = self.repo.list_patient_reports(
            patient_id
        )

        return {
            "patient_id": patient_id,
            "deleted_report_ids": deleted,
            "not_found_report_ids": not_found,
            "preserved_report_id": preserved_report_id,
            "remaining_report_ids": [
                report.report_id
                for report in remaining_reports
            ],
            "remaining_report_count": len(
                remaining_reports
            ),
            "trend_count": len(trends),
        }

    # ── Upload Validation ─────────────────────────────────────────────────────

    def validate_upload(
        self,
        filename: str,
        content_type: Optional[str],
        file_size: Optional[int],
    ) -> None:

        ext = os.path.splitext(filename)[1].lower()

        if ext not in ALLOWED_EXTENSIONS:
            raise ValueError(
                f"Unsupported file format '{ext}'. "
                f"Accepted formats: PDF, JPG, JPEG, PNG."
            )

        if content_type and content_type not in ALLOWED_MIME_TYPES:
            raise ValueError(
                f"Unexpected content type '{content_type}'. "
                f"Please upload a valid PDF or image file."
            )

        if file_size is not None and file_size > MAX_UPLOAD_BYTES:

            mb = MAX_UPLOAD_BYTES // (1024 * 1024)

            raise ValueError(
                f"File is too large. Maximum allowed size is {mb} MB."
            )

    # ── Report Upload & Processing ────────────────────────────────────────────

    def process_uploaded_report(
        self,
        patient_id: str,
        file_obj,
        filename: str,
        content_type: Optional[str] = None,
        file_size: Optional[int] = None,
        report_date: Optional[str] = None,
        report_category: Optional[str] = "Diagnostic Panel",
        laboratory: Optional[str] = "Lords Pathology",
    ) -> Dict[str, Any]:

        """
        Full pipeline:

        Validate
        → Save
        → OCR
        → Quality
        → Table Extraction
        → Test Extraction
        → Normalization
        → Trend Update
        → REPORT_READY

        Patient data stays exclusively in SQLite.
        It never enters ChromaDB.
        """

        # ── 0. Validate ────────────────────────────────────────────────────────

        self.validate_upload(
            filename,
            content_type,
            file_size,
        )

        # ── 1. Ensure patient record ──────────────────────────────────────────

        patient = self.repo.get_patient(
            patient_id
        )

        if not patient:

            patient = self.repo.upsert_patient({
                "patient_id": patient_id,
                "name": f"Patient {patient_id}",
                "country": "India",
                "synthetic": False,
            })

        # ── 2. Save file safely ────────────────────────────────────────────────

        ext = os.path.splitext(filename)[1].lower()

        safe_orig = _safe_filename(
            filename
        )

        unique_file_name = (
            f"{uuid.uuid4().hex}{ext}"
        )

        upload_dir = _patient_upload_dir(
            patient_id
        )

        saved_path = os.path.join(
            upload_dir,
            unique_file_name,
        )

        with open(saved_path, "wb") as buffer:
            shutil.copyfileobj(
                file_obj,
                buffer,
            )

        # ── 3. File hash ──────────────────────────────────────────────────────

        file_hash = _sha256(
            saved_path
        )

        actual_size = os.path.getsize(
            saved_path
        )

        if actual_size > MAX_UPLOAD_BYTES:

            os.remove(saved_path)

            mb = MAX_UPLOAD_BYTES // (1024 * 1024)

            raise ValueError(
                f"Uploaded file exceeds the {mb} MB limit after writing."
            )

        # ── 4. Create report record ───────────────────────────────────────────

        report_id = (
            f"REP_{uuid.uuid4().hex[:8].upper()}"
        )

        resolved_date = (
            report_date
            or datetime.utcnow().strftime("%Y-%m-%d")
        )

        source_type = (
            "digital_pdf"
            if ext == ".pdf"
            else "camera_image"
        )

        # Determine the next report sequence for this patient.
        #
        # Do NOT use len(reports) + 1 because existing reports may have
        # duplicate sequence values due to earlier/debug uploads.
        #
        # Instead, find the highest sequence already assigned and increment it.

        existing_reports = self.repo.list_patient_reports(
            patient_id
        )

        if existing_reports:

            max_sequence = max(
                (
                    report.report_sequence or 0
                    for report in existing_reports
                ),
                default=0,
            )

            report_sequence = max_sequence + 1

        else:

            report_sequence = 1

        self.repo.upsert_report({
            "report_id": report_id,
            "patient_id": patient_id,
            "report_sequence": report_sequence,
            "report_type": "Diagnostic Report",
            "report_category": report_category,
            "laboratory": (
                laboratory
                or "Lords Pathology"
            ),
            "collection_date": resolved_date,
            "report_date": resolved_date,
            "source_type": source_type,
            "original_file": safe_orig,
            "processing_status": "UPLOADED",
            "ocr_quality_score": 1.0,
        })

        # ── 5. Update to PROCESSING ───────────────────────────────────────────

        self.repo.update_report_status(
            patient_id,
            report_id,
            "PROCESSING",
        )

        # ── 6. OCR / Text Extraction ───────────────────────────────────────────

        try:

            ocr_processor = (
                self.pdf_proc
                if ext == ".pdf"
                else self.img_proc
            )

            pages = ocr_processor.extract_text(
                saved_path
            )

        except Exception as e:

            self.repo.update_report_status(
                patient_id,
                report_id,
                "FAILED",
                error_msg="OCR engine error",
            )

            raise RuntimeError(
                "OCR processing failed. Please try again."
            ) from e

        # ── 7. Quality Assessment ──────────────────────────────────────────────

        quality = BaseOCRService.calculate_quality(
            pages
        )

        quality_label = _ocr_quality_label(
            quality["score"]
        )

        self.repo.update_report_status(
            patient_id=patient_id,
            report_id=report_id,
            status="OCR_COMPLETE",
            ocr_quality=quality["score"],
            ocr_label=quality_label,
        )

        # ── 8. Store page OCR data ─────────────────────────────────────────────

        pages_to_save = [
            {
                "report_id": report_id,
                "page_number": p.get("page_number", 1),
                "ocr_text": p.get("text", ""),
                "ocr_confidence": p.get("confidence", 0.9),
            }
            for p in pages
        ]

        self.repo.add_report_pages(
            pages_to_save
        )

        # ── 9. Test Extraction (Fast Line-Based First) ────────────────────────
        tables = []
        try:
            extracted = TestExtractor.extract_from_pages(
                pages=pages,
                report_id=report_id,
                patient_id=patient_id,
                laboratory=(laboratory or "Lords Pathology"),
                tables=None,
            )

            # Lazy table fallback only if text extraction produced 0 tests
            if not extracted and ext == ".pdf":
                try:
                    tables = ocr_processor.extract_tables(saved_path)
                    if tables:
                        extracted = TestExtractor.extract_from_pages(
                            pages=pages,
                            report_id=report_id,
                            patient_id=patient_id,
                            laboratory=(laboratory or "Lords Pathology"),
                            tables=tables,
                        )
                except Exception as e:
                    print(f"[Table Fallback Warning] {e}")

        except Exception as e:
            self.repo.update_report_status(
                patient_id,
                report_id,
                "FAILED",
                error_msg="Extraction error",
            )
            raise RuntimeError(
                "Test extraction failed. Please check report format."
            ) from e

        # ── 10. Save Extracted Results & Update Status ─────────────────────────
        saved_results = self.repo.add_test_results(extracted)

        # ── 11. Longitudinal Trend Recalculation ───────────────────────────────
        self.refresh_patient_trends(patient_id)

        # ── 12. Final Status (Single consolidated update) ─────────────────────
        self.repo.update_report_status(
            patient_id=patient_id,
            report_id=report_id,
            status="REPORT_READY",
            ocr_quality=quality["score"],
            ocr_label=quality_label,
        )

        return {
            "report_id": report_id,
            "patient_id": patient_id,
            "report_date": resolved_date,
            "processing_status": "REPORT_READY",
            "ocr_quality": {
                "score": quality["score"],
                "label": quality_label,
                "is_low_quality": quality.get(
                    "is_low_quality",
                    False,
                ),
                "medical_keywords_found": quality.get(
                    "medical_keywords_found",
                    [],
                ),
            },
            "file_hash": file_hash,
            "total_extracted_tests": len(
                saved_results
            ),
            "warning": quality.get(
                "warning"
            ),
        }

    # ── Report Status ──────────────────────────────────────────────────────────

    def get_report_status(
        self,
        patient_id: str,
        report_id: str,
    ) -> Optional[Dict[str, Any]]:

        report = self.repo.get_report(
            patient_id,
            report_id,
        )

        if not report:
            return None

        return {
            "report_id": report.report_id,
            "patient_id": report.patient_id,
            "processing_status": report.processing_status,
            "ocr_quality_score": report.ocr_quality_score,
            "created_at": report.created_at,
        }

    # ── Reports & Results ──────────────────────────────────────────────────────

    def get_patient_reports_summary(
        self,
        patient_id: str,
    ) -> List[Dict[str, Any]]:

        reports = self.repo.list_patient_reports(
            patient_id
        )

        out = []

        for r in reports:

            results = self.repo.get_report_results(
                patient_id,
                r.report_id,
            )

            abnormals = [
                x
                for x in results
                if x.status in ("HIGH", "LOW")
            ]

            out.append({
                "report_id": r.report_id,
                "patient_id": r.patient_id,
                "report_sequence": r.report_sequence,
                "report_type": r.report_type,
                "report_date": r.report_date,
                "collection_date": r.collection_date,
                "laboratory": r.laboratory,
                "report_category": r.report_category,
                "source_type": r.source_type,
                "original_file": r.original_file,
                "processing_status": r.processing_status,
                "ocr_quality_score": r.ocr_quality_score,
                "created_at": r.created_at,
                "total_tests": len(results),
                "abnormal_count": len(abnormals),
            })

        return out

    def get_report_detail(
        self,
        patient_id: str,
        report_id: str,
    ) -> Optional[Dict[str, Any]]:

        report = self.repo.get_report(
            patient_id,
            report_id,
        )

        if not report:
            return None

        results = self.repo.get_report_results(
            patient_id,
            report_id,
        )

        return {
            "report_id": report.report_id,
            "patient_id": report.patient_id,
            "report_sequence": report.report_sequence,
            "report_type": report.report_type,
            "report_date": report.report_date,
            "collection_date": report.collection_date,
            "laboratory": report.laboratory,
            "report_category": report.report_category,
            "processing_status": report.processing_status,
            "ocr_quality_score": report.ocr_quality_score,
            "created_at": report.created_at,
            "results": [
                {
                    "result_id": r.result_id,
                    "patient_id": r.patient_id,
                    "report_id": r.report_id,
                    "test_name_original": r.test_name_original,
                    "test_name_normalized": r.test_name_normalized,
                    "original_value": r.original_value,
                    "original_unit": r.original_unit,
                    "normalized_value": r.normalized_value,
                    "normalized_unit": r.normalized_unit,
                    "reference_low": r.reference_low,
                    "reference_high": r.reference_high,
                    "reference_text": r.reference_text,
                    "status": r.status,
                    "extraction_confidence": r.extraction_confidence,
                    "source_page": r.source_page,
                    "source_text": r.source_text,
                }
                for r in results
            ],
        }

    # ── Trend Engine ───────────────────────────────────────────────────────────

    def refresh_patient_trends(
        self,
        patient_id: str,
    ) -> List[Dict[str, Any]]:

        all_results = self.repo.get_all_patient_results(
            patient_id
        )

        reports = self.repo.list_patient_reports(patient_id)
        report_dates = {r.report_id: r.report_date for r in reports}

        records_dict = [
            {
                "report_id": r.report_id,
                "report_date": report_dates.get(r.report_id, ""),
                "test_name_original": r.test_name_original,
                "test_name_normalized": r.test_name_normalized,
                "normalized_value": r.normalized_value,
                "normalized_unit": r.normalized_unit,
                "reference_low": r.reference_low,
                "reference_high": r.reference_high,
                "status": r.status,
            }
            for r in all_results
        ]

        trends = LongitudinalAnalyzer.compute_all_patient_trends(
            patient_id,
            records_dict,
        )

        self.repo.clear_patient_trends(
            patient_id
        )

        trend_objects = [
            {
                "patient_id": patient_id,
                "test_name": t["test_name"],
                "first_value": t.get("first_value"),
                "latest_value": t.get("current_value"),
                "absolute_change": t.get("absolute_change"),
                "percentage_change": t.get("percentage_change"),
                "previous_status": t.get("previous_status"),
                "current_status": t.get("current_status"),
                "trend": t.get("trend"),
                "persistence": t.get("persistence"),
                "evidence": str(
                    t.get("evidence", "")
                ),
            }
            for t in trends
        ]

        self.repo.upsert_trends_bulk(trend_objects)

        return trends

    # ── AI Report Generation ──────────────────────────────────────────────────

    def generate_patient_ai_report(
        self,
        patient_id: str,
        report_id: str,
    ) -> Dict[str, Any]:

        existing = self.repo.get_generated_report(
            patient_id,
            report_id,
        )

        if existing:

            return {
                "report_id": existing.report_id,
                "patient_id": existing.patient_id,
                "generated_at": existing.generated_at,
                "summary": existing.summary,
                "findings": existing.findings,
                "evidence": existing.evidence,
                "disclaimer": existing.disclaimer,
                "prompt_version": existing.prompt_version,
            }

        patient = self.repo.get_patient(
            patient_id
        )

        report = self.repo.get_report(
            patient_id,
            report_id,
        )

        if not report or not patient:
            raise ValueError(
                "Report or Patient not found"
            )

        results = self.repo.get_report_results(
            patient_id,
            report_id,
        )

        trends = self.refresh_patient_trends(
            patient_id
        )

        patient_profile = {
            "patient_id": patient.patient_id,
            "name": patient.name,
            "age": patient.age,
            "gender": patient.gender,
        }

        report_meta = {
            "report_id": report.report_id,
            "report_date": report.report_date,
            "laboratory": report.laboratory,
            "report_category": report.report_category,
        }

        results_data = [
            {
                "test_name_normalized": r.test_name_normalized,
                "normalized_value": r.normalized_value,
                "normalized_unit": r.normalized_unit,
                "reference_text": r.reference_text,
                "status": r.status,
            }
            for r in results
        ]

        gen_out = self.report_gen.generate_report(
            patient_profile=patient_profile,
            report_meta=report_meta,
            current_results=results_data,
            longitudinal_trends=trends,
        )

        import json

        saved = self.repo.save_generated_report(
            patient_id=patient_id,
            report_id=report_id,
            summary=gen_out["summary"],
            findings=gen_out["findings"],
            evidence_json=json.dumps(
                gen_out["evidence"]
            ),
            disclaimer=gen_out["disclaimer"],
            prompt_version=gen_out["prompt_version"],
        )

        return {
            "report_id": saved.report_id,
            "patient_id": saved.patient_id,
            "generated_at": saved.generated_at,
            "summary": saved.summary,
            "findings": saved.findings,
            "evidence": gen_out["evidence"],
            "disclaimer": saved.disclaimer,
            "prompt_version": saved.prompt_version,
        }

    # ── Patient Chat ───────────────────────────────────────────────────────────

    def chat(
        self,
        patient_id: str,
        query: str,
        report_id: Optional[str] = None,
    ) -> Dict[str, Any]:

        patient = self.repo.get_patient(
            patient_id
        )

        if not patient:
            raise ValueError(
                f"Patient {patient_id} not found"
            )

        patient_profile = {
            "patient_id": patient.patient_id,
            "name": patient.name,
            "age": patient.age,
            "gender": patient.gender,
        }

        reports = self.repo.list_patient_reports(patient_id)
        report_map = {r.report_id: r for r in reports}

        target_report = None
        is_all_reports = False

        if report_id and str(report_id).strip().lower() not in ["all", "all_reports", "null", "none"]:
            target_report = self.repo.get_report(
                patient_id,
                report_id,
            )
            # If specified report not found, fallback to latest or all
            if not target_report and reports:
                target_report = reports[-1]
        else:
            is_all_reports = True

        recent_results = []

        if not is_all_reports and target_report:
            res_list = self.repo.get_report_results(
                patient_id,
                target_report.report_id,
            )

            recent_results = [
                {
                    "test_name_original": r.test_name_original,
                    "test_name_normalized": r.test_name_normalized,
                    "normalized_value": r.normalized_value,
                    "normalized_unit": r.normalized_unit,
                    "reference_text": r.reference_text,
                    "status": r.status,
                    "source_page": r.source_page,
                    "source_text": r.source_text,
                    "report_id": target_report.report_id,
                    "report_date": target_report.report_date,
                    "laboratory": target_report.laboratory or "Lords Pathology",
                }
                for r in res_list
            ]
        else:
            all_res_list = self.repo.get_all_patient_results(patient_id)

            recent_results = [
                {
                    "test_name_original": r.test_name_original,
                    "test_name_normalized": r.test_name_normalized,
                    "normalized_value": r.normalized_value,
                    "normalized_unit": r.normalized_unit,
                    "reference_text": r.reference_text,
                    "status": r.status,
                    "source_page": r.source_page,
                    "source_text": r.source_text,
                    "report_id": r.report_id,
                    "report_date": report_map.get(r.report_id).report_date if report_map.get(r.report_id) else None,
                    "laboratory": report_map.get(r.report_id).laboratory if report_map.get(r.report_id) else "Lords Pathology",
                }
                for r in all_res_list
            ]

        trends = self.refresh_patient_trends(
            patient_id
        )

        available_reports = [
            {
                "report_id": r.report_id,
                "report_date": r.report_date,
                "laboratory": r.laboratory or "Lords Pathology",
            }
            for r in reports
        ]

        if not is_all_reports and target_report:
            report_meta = {
                "report_id": target_report.report_id,
                "scope": "single_report",
                "report_date": target_report.report_date,
                "laboratory": target_report.laboratory or "Lords Pathology",
                "available_reports": available_reports,
            }
        else:
            report_meta = {
                "report_id": None,
                "scope": "all_reports",
                "report_date": "All Historical Reports",
                "laboratory": "Lords Pathology & Affiliates",
                "available_reports": available_reports,
            }

        return self.chat_svc.answer_question(
            patient_profile=patient_profile,
            query=query,
            recent_results=recent_results,
            patient_trends=trends,
            report_meta=report_meta,
        )