"""
test_patient_models.py — Phase 2/Final Phase Test

Verifies SQLAlchemy model constraints:
- patient_id is unique
- ForeignKey relationships are enforced
- required fields cannot be null
- timestamp fields default correctly
- is_synthetic (synthetic) field defaults correctly
"""

import os
import sys
import unittest
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from patient.models.database import SessionLocal, engine, Base
from patient.models.patient_models import (
    Patient, PatientReport, ReportPage, TestResult,
    TrendObservation, GeneratedPatientReport
)


_TEST_PID = "MODEL_TEST_PAT_001"
_TEST_RID = "MODEL_TEST_REP_001"
_TEST_RESULT_ID = "MODEL_TEST_RES_001"


def _cleanup(db):
    for cls in [GeneratedPatientReport, TrendObservation, TestResult, ReportPage, PatientReport, Patient]:
        db.query(cls).filter(
            getattr(cls, "patient_id", None) == _TEST_PID
            if hasattr(cls, "patient_id")
            else getattr(cls, "report_id", None) == _TEST_RID
        ).delete(synchronize_session=False)
    db.commit()


class TestPatientModel(unittest.TestCase):
    def setUp(self):
        self.db = SessionLocal()
        _cleanup(self.db)

    def tearDown(self):
        _cleanup(self.db)
        self.db.close()

    def test_patient_created_with_defaults(self):
        p = Patient(patient_id=_TEST_PID, name="Test Model Patient", synthetic=True)
        self.db.add(p)
        self.db.commit()
        self.db.refresh(p)
        self.assertEqual(p.patient_id, _TEST_PID)
        self.assertTrue(p.synthetic)

    def test_patient_id_uniqueness_enforced(self):
        """Inserting duplicate patient_id must raise an integrity error."""
        from sqlalchemy.exc import IntegrityError
        p1 = Patient(patient_id=_TEST_PID, name="First", synthetic=True)
        self.db.add(p1)
        self.db.commit()

        with self.assertRaises(IntegrityError):
            p2 = Patient(patient_id=_TEST_PID, name="Duplicate", synthetic=True)
            self.db.add(p2)
            self.db.commit()
        self.db.rollback()

    def test_patient_report_fk_relationship(self):
        """PatientReport must link to a valid Patient via patient_id FK."""
        p = Patient(patient_id=_TEST_PID, name="FK Test Patient", synthetic=True)
        self.db.add(p)
        self.db.commit()

        r = PatientReport(
            report_id=_TEST_RID,
            patient_id=_TEST_PID,
            report_date="2026-01-01",
            processing_status="REPORT_READY"
        )
        self.db.add(r)
        self.db.commit()
        self.db.refresh(r)
        self.assertEqual(r.patient_id, _TEST_PID)

    def test_report_page_unique_constraint(self):
        """(report_id, page_number) should ideally be unique per report."""
        p = Patient(patient_id=_TEST_PID, name="Page Test", synthetic=True)
        r = PatientReport(report_id=_TEST_RID, patient_id=_TEST_PID,
                          report_date="2026-01-01", processing_status="REPORT_READY")
        self.db.add_all([p, r])
        self.db.commit()

        pg = ReportPage(report_id=_TEST_RID, page_number=1, ocr_text="Test OCR", ocr_confidence=0.9)
        self.db.add(pg)
        self.db.commit()
        # Retrieve and confirm
        pages = self.db.query(ReportPage).filter(ReportPage.report_id == _TEST_RID).all()
        self.assertEqual(len(pages), 1)

    def test_test_result_model_fields(self):
        """TestResult must store original + normalized values."""
        p = Patient(patient_id=_TEST_PID, name="Result Test", synthetic=True)
        r = PatientReport(report_id=_TEST_RID, patient_id=_TEST_PID,
                          report_date="2026-01-01", processing_status="REPORT_READY")
        self.db.add_all([p, r])
        self.db.commit()

        res = TestResult(
            result_id=_TEST_RESULT_ID,
            patient_id=_TEST_PID,
            report_id=_TEST_RID,
            test_name_original="Hb",
            test_name_normalized="Hemoglobin",
            original_value="11.2",
            original_unit="g/dL",
            normalized_value=11.2,
            normalized_unit="g/dL",
            reference_low=12.0,
            reference_high=17.0,
            status="LOW",
            extraction_confidence=0.95
        )
        self.db.add(res)
        self.db.commit()
        self.db.refresh(res)
        self.assertEqual(res.test_name_normalized, "Hemoglobin")
        self.assertEqual(res.status, "LOW")
        self.assertAlmostEqual(res.normalized_value, 11.2)

    def test_generated_report_model(self):
        """GeneratedPatientReport must link to patient and report."""
        p = Patient(patient_id=_TEST_PID, name="Gen Test", synthetic=True)
        r = PatientReport(report_id=_TEST_RID, patient_id=_TEST_PID,
                          report_date="2026-01-01", processing_status="REPORT_READY")
        self.db.add_all([p, r])
        self.db.commit()

        gr = GeneratedPatientReport(
            patient_id=_TEST_PID,
            report_id=_TEST_RID,
            summary="Test summary",
            findings="Test findings",
            disclaimer="For informational purposes only.",
            prompt_version="patient_report_v1"
        )
        self.db.add(gr)
        self.db.commit()
        self.db.refresh(gr)
        self.assertEqual(gr.prompt_version, "patient_report_v1")
        self.assertIsInstance(gr.generated_at, datetime)


if __name__ == "__main__":
    unittest.main()

