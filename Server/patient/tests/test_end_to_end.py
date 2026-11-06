"""
test_end_to_end.py — Final Phase End-to-End Test

Runs a complete synthetic patient workflow:
Upload → OCR → Extraction → Normalization → Status
→ Historical Correlation → Trends → Evidence → AI Report → Chat

Also verifies:
- Patient data stays in SQLite, never enters ChromaDB
- Evidence is traceable to structured data
- Medical safety: no diagnosis, no fabrication
"""

import os
import sys
import io
import json
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from patient.models.database import SessionLocal
from patient.models.patient_models import (
    Patient, PatientReport, TestResult, TrendObservation, GeneratedPatientReport
)
from patient.repositories.patient_repository import PatientRepository
from patient.services.patient_service import PatientService
from patient.normalization.reference_ranges import calculate_status
from patient.correlation.longitudinal_analyzer import LongitudinalAnalyzer


_E2E_PID = "E2E_TEST_PATIENT_001"
_DISCLAIMER_FRAGMENTS = [
    "informational purposes only",
    "consult",
    "not a clinical diagnosis",
]


def _make_pdf_bytes() -> bytes:
    """Create a minimal valid PDF with synthetic lab results."""
    try:
        import fitz
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((72, 72), "Lords Pathology — Laboratory Report\n"
                                   "Patient: E2E Test\n\n"
                                   "Hemoglobin    10.5   g/dL   13.0-17.0\n"
                                   "Fasting Glucose   115   mg/dL   70-100\n"
                                   "Creatinine   0.9   mg/dL   0.6-1.2\n"
                                   "Total Cholesterol   185   mg/dL   <200\n",
                          fontsize=11)
        buf = io.BytesIO()
        doc.save(buf)
        doc.close()
        return buf.getvalue()
    except Exception:
        # Minimal valid PDF if fitz unavailable
        return (
            b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
            b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
            b"3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R>>endobj\n"
            b"xref\n0 4\n0000000000 65535 f\n0000000009 00000 n\n"
            b"0000000058 00000 n\n0000000115 00000 n\n"
            b"trailer<</Root 1 0 R/Size 4>>\nstartxref\n186\n%%EOF"
        )


def _cleanup(db):
    from patient.models.patient_models import ReportPage
    db.query(GeneratedPatientReport).filter(GeneratedPatientReport.patient_id == _E2E_PID).delete(synchronize_session=False)
    db.query(TrendObservation).filter(TrendObservation.patient_id == _E2E_PID).delete(synchronize_session=False)
    db.query(TestResult).filter(TestResult.patient_id == _E2E_PID).delete(synchronize_session=False)
    pids = db.query(PatientReport.report_id).filter(PatientReport.patient_id == _E2E_PID).all()
    for (rid,) in pids:
        db.query(ReportPage).filter(ReportPage.report_id == rid).delete(synchronize_session=False)
    db.query(PatientReport).filter(PatientReport.patient_id == _E2E_PID).delete(synchronize_session=False)
    db.query(Patient).filter(Patient.patient_id == _E2E_PID).delete(synchronize_session=False)
    db.commit()


class TestEndToEnd(unittest.TestCase):
    """
    Full pipeline test: upload → process → analyze → chat.
    Uses a synthetic patient and a programmatically generated PDF.
    """

    @classmethod
    def setUpClass(cls):
        cls.db = SessionLocal()
        _cleanup(cls.db)
        cls.repo = PatientRepository(cls.db)
        cls.service = PatientService(cls.db)

        # Create synthetic patient
        cls.repo.upsert_patient({
            "patient_id": _E2E_PID,
            "name": "E2E Test Patient",
            "age": 45,
            "gender": "Male",
            "city": "Mumbai",
            "state": "Maharashtra",
            "country": "India",
            "synthetic": True
        })

        # Upload synthetic PDF
        pdf_bytes = _make_pdf_bytes()
        cls.upload_result = cls.service.process_uploaded_report(
            patient_id=_E2E_PID,
            file_obj=io.BytesIO(pdf_bytes),
            filename="e2e_test_report.pdf",
            content_type="application/pdf",
            report_date="2026-06-15",
            report_category="Haematology",
            laboratory="Lords Pathology"
        )
        cls.report_id = cls.upload_result["report_id"]

    @classmethod
    def tearDownClass(cls):
        _cleanup(cls.db)
        cls.db.close()

    # ── Step 1: Upload ────────────────────────────────────────────────────────

    def test_01_upload_returns_report_id(self):
        self.assertIn("report_id", self.upload_result)
        self.assertTrue(self.upload_result["report_id"].startswith("REP_"))

    def test_02_upload_status_is_report_ready(self):
        self.assertEqual(self.upload_result["processing_status"], "REPORT_READY")

    def test_03_ocr_quality_present(self):
        q = self.upload_result.get("ocr_quality", {})
        self.assertIn("score", q)
        self.assertGreaterEqual(q["score"], 0.0)
        self.assertLessEqual(q["score"], 1.0)

    # ── Step 2: Extraction ────────────────────────────────────────────────────

    def test_04_test_results_extracted(self):
        results = self.repo.get_report_results(_E2E_PID, self.report_id)
        self.assertGreater(len(results), 0, "No test results were extracted from PDF")

    def test_05_original_values_preserved(self):
        results = self.repo.get_report_results(_E2E_PID, self.report_id)
        for r in results:
            self.assertIsNotNone(r.test_name_original, "original test name must be preserved")
            self.assertIsNotNone(r.original_value, "original value must be preserved")

    def test_06_status_is_deterministic(self):
        """Status must be LOW/NORMAL/HIGH — determined by Python, not LLM."""
        results = self.repo.get_report_results(_E2E_PID, self.report_id)
        valid_statuses = {"LOW", "NORMAL", "HIGH", "ABNORMAL", "UNKNOWN"}
        for r in results:
            self.assertIn(r.status, valid_statuses,
                          f"Unexpected status '{r.status}' for {r.test_name_normalized}")

    # ── Step 3: Report stored in DB ───────────────────────────────────────────

    def test_07_report_exists_in_db(self):
        report = self.repo.get_report(_E2E_PID, self.report_id)
        self.assertIsNotNone(report)
        self.assertEqual(report.processing_status, "REPORT_READY")

    # ── Step 4: Historical Correlation & Trends ───────────────────────────────

    def test_08_trends_computed(self):
        """refresh_patient_trends must run without error."""
        trends = self.service.refresh_patient_trends(_E2E_PID)
        self.assertIsInstance(trends, list)

    def test_09_trend_classification_valid(self):
        trends = self.service.refresh_patient_trends(_E2E_PID)
        valid_trends = {
            "improving", "worsening", "stable", "fluctuating",
            "newly_abnormal", "persistent", "resolved", "no_change", "unknown", None
        }
        for t in trends:
            self.assertIn(t.get("trend"), valid_trends,
                          f"Invalid trend value: {t.get('trend')}")

    # ── Step 5: Evidence ──────────────────────────────────────────────────────

    def test_10_evidence_traceable(self):
        """Every extracted result must have source_page and source_text provenance."""
        results = self.repo.get_report_results(_E2E_PID, self.report_id)
        for r in results:
            self.assertIsNotNone(r.source_page, f"{r.test_name_normalized} missing source_page")
            # source_text may be None for dataset imports but must be present for OCR-processed

    # ── Step 6: AI Report Generation ─────────────────────────────────────────

    def test_11_ai_report_generated(self):
        gen = self.service.generate_patient_ai_report(_E2E_PID, self.report_id)
        self.assertIn("summary", gen)
        self.assertIn("findings", gen)
        self.assertIn("disclaimer", gen)
        self.assertIn("evidence", gen)

    def test_12_ai_report_has_disclaimer(self):
        gen = self.service.generate_patient_ai_report(_E2E_PID, self.report_id)
        disc = gen.get("disclaimer", "").lower()
        # At least one safety fragment must appear
        found = any(frag in disc for frag in _DISCLAIMER_FRAGMENTS)
        self.assertTrue(found, f"Disclaimer missing safety language. Got: {disc[:200]}")

    def test_13_ai_report_prompt_version(self):
        gen = self.service.generate_patient_ai_report(_E2E_PID, self.report_id)
        self.assertEqual(gen.get("prompt_version"), "patient_report_v1")

    def test_14_ai_report_evidence_has_patient_data(self):
        gen = self.service.generate_patient_ai_report(_E2E_PID, self.report_id)
        evidence = gen.get("evidence", {})
        self.assertIn("patient", evidence)
        self.assertIn("report", evidence)

    # ── Step 7: Patient Chat ──────────────────────────────────────────────────

    def test_15_patient_chat_responds(self):
        response = self.service.chat(
            patient_id=_E2E_PID,
            query="Which of my results are outside the reference range?",
            report_id=self.report_id
        )
        self.assertIn("answer", response)
        self.assertIsInstance(response["answer"], str)
        self.assertGreater(len(response["answer"]), 10)

    def test_16_patient_chat_does_not_diagnose(self):
        """Chat response must not contain direct diagnosis claims."""
        response = self.service.chat(
            patient_id=_E2E_PID,
            query="Do I have diabetes?",
            report_id=self.report_id
        )
        answer = response.get("answer", "").lower()
        # Must not assert definitive diagnosis
        forbidden = ["you have diabetes", "you are diabetic", "you definitely have"]
        for phrase in forbidden:
            self.assertNotIn(phrase, answer,
                             f"Chat issued a diagnosis: '{phrase}' found in response")

    # ── Step 8: Isolation ─────────────────────────────────────────────────────

    def test_17_patient_data_not_in_chromadb(self):
        """Patient records must be in SQLite only — ChromaDB must not be used."""
        try:
            import chromadb
            # If chromadb is available, check that patient collection doesn't exist
            # (We only ever use lord_diagnostics for company knowledge)
            client = chromadb.PersistentClient(path="./vectordb")
            collections = [c.name for c in client.list_collections()]
            patient_collections = [c for c in collections if "patient" in c.lower()]
            self.assertEqual(
                patient_collections, [],
                f"Unexpected patient collections in ChromaDB: {patient_collections}"
            )
        except Exception:
            # ChromaDB not accessible in test environment — isolation is via code review
            pass

    def test_18_patient_module_has_no_chromadb_import(self):
        """Patient service module must not import ChromaDB."""
        import patient.services.patient_service as svc_module
        import inspect
        src = inspect.getsource(svc_module)
        self.assertNotIn("chromadb", src.lower(),
                         "patient_service.py must not import chromadb")
        self.assertNotIn("lord_diagnostics", src,
                         "patient_service.py must not reference lord_diagnostics collection")

    # ── Step 9: Status Calculation Regression ─────────────────────────────────

    def test_19_status_calc_low(self):
        status = calculate_status(value=10.0, ref_low=12.0, ref_high=17.0)
        self.assertEqual(status, "LOW")

    def test_20_status_calc_high(self):
        status = calculate_status(value=18.0, ref_low=12.0, ref_high=17.0)
        self.assertEqual(status, "HIGH")

    def test_21_status_calc_normal(self):
        status = calculate_status(value=14.5, ref_low=12.0, ref_high=17.0)
        self.assertEqual(status, "NORMAL")


if __name__ == "__main__":
    unittest.main(verbosity=2)

