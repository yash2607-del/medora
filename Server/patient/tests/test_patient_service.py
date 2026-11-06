"""
Unit and Integration Tests for PatientService, OCR pipeline, and Generation without network sockets.
Can run cleanly inside sandboxed execution.
"""

import sys
import os
import unittest
import io

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from patient.models.database import SessionLocal, init_db
from patient.services.patient_service import PatientService
from patient.models.patient_models import Patient, PatientReport, TestResult, TrendObservation

class TestPatientService(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        cls.db = SessionLocal()
        cls.service = PatientService(cls.db)

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def test_01_list_patients(self):
        patients = self.service.list_patients()
        self.assertGreaterEqual(len(patients), 100)
        p1 = next((p for p in patients if p["patient_id"] == "PAT0001"), None)
        self.assertIsNotNone(p1)
        self.assertEqual(p1["name"], "Aarav Sharma")
        self.assertGreaterEqual(p1["total_reports"], 3)

    def test_02_patient_profile(self):
        prof = self.service.get_patient_profile("PAT0001")
        self.assertIsNotNone(prof)
        self.assertEqual(prof["patient_id"], "PAT0001")
        self.assertEqual(prof["country"], "India")

    def test_03_reports_summary(self):
        reports = self.service.get_patient_reports_summary("PAT0001")
        self.assertEqual(len(reports), 3)
        for r in reports:
            self.assertIn("abnormal_count", r)
            self.assertIn("report_date", r)
            self.assertIn("laboratory", r)

    def test_04_report_detail_and_provenance(self):
        detail = self.service.get_report_detail("PAT0001", "REP0001")
        self.assertIsNotNone(detail)
        self.assertEqual(detail["report_id"], "REP0001")
        self.assertGreater(len(detail["results"]), 0)
        
        # Verify provenance fields exist
        res = detail["results"][0]
        self.assertIn("test_name_normalized", res)
        self.assertIn("status", res)
        self.assertIn("source_page", res)
        self.assertIn("source_text", res)

    def test_05_longitudinal_trends(self):
        trends = self.service.refresh_patient_trends("PAT0001")
        self.assertGreater(len(trends), 0)
        for t in trends:
            self.assertIn("test_name", t)
            self.assertIn("trend", t)
            self.assertIn("persistence", t)
            self.assertIn("deterministic_statement", t)

    def test_06_ai_patient_report_generation(self):
        gen = self.service.generate_patient_ai_report("PAT0001", "REP0001")
        self.assertIsNotNone(gen)
        self.assertIn("summary", gen)
        self.assertIn("findings", gen)
        self.assertIn("disclaimer", gen)
        self.assertIn("evidence", gen)
        self.assertIn("informational purposes only", gen["disclaimer"].lower())

    def test_07_patient_chat(self):
        resp = self.service.chat("PAT0001", "Which results are abnormal?")
        self.assertIsNotNone(resp)
        self.assertIn("answer", resp)
        self.assertIn("evidence", resp)
        self.assertIn("disclaimer", resp)

    def test_08_mock_upload_pipeline(self):
        import fitz
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text(
            (50, 50),
            "Lords Pathology - Diagnostic Report\n"
            "Hemoglobin   13.5   g/dL   12.0 - 17.0\n"
            "SGPT   85   U/L   7 - 56\n"
            "Fasting Glucose   110   mg/dL   70 - 100\n"
        )
        pdf_bytes = doc.tobytes()
        fake_file = io.BytesIO(pdf_bytes)
        
        # Process upload
        res = self.service.process_uploaded_report(
            patient_id="TEST_UPL_PAT",
            file_obj=fake_file,
            filename="test_report.pdf",
            report_date="2025-06-01"
        )
        self.assertIsNotNone(res)
        self.assertEqual(res["patient_id"], "TEST_UPL_PAT")
        self.assertIn("report_id", res)
        self.assertGreater(res["total_extracted_tests"], 0)
        
        # Clean up uploaded test patient
        self.db.query(TestResult).filter(TestResult.patient_id == "TEST_UPL_PAT").delete()
        self.db.query(PatientReport).filter(PatientReport.patient_id == "TEST_UPL_PAT").delete()
        self.db.query(Patient).filter(Patient.patient_id == "TEST_UPL_PAT").delete()
        self.db.commit()

if __name__ == "__main__":
    unittest.main()
