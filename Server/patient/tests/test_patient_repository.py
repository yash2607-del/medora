"""
test_patient_repository.py — Phase 2/Final Phase Test

Verifies PatientRepository CRUD operations:
- upsert_patient
- upsert_report / get_report
- add_test_results / get_report_results
- add_report_pages / get_report_pages
- save_generated_report / get_generated_report
- clear_patient_trends / upsert_trend / get_patient_trends
- count helpers
- Patient scoping: Patient B cannot see Patient A's data
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from patient.models.database import SessionLocal
from patient.models.patient_models import (
    Patient, PatientReport, ReportPage, TestResult,
    TrendObservation, GeneratedPatientReport
)
from patient.repositories.patient_repository import PatientRepository


_PID_A = "REPO_TEST_PAT_A"
_PID_B = "REPO_TEST_PAT_B"
_RID_A = "REPO_TEST_REP_A"
_RID_B = "REPO_TEST_REP_B"


def _cleanup(db):
    for pid, rid in [(_PID_A, _RID_A), (_PID_B, _RID_B)]:
        db.query(GeneratedPatientReport).filter(GeneratedPatientReport.patient_id == pid).delete(synchronize_session=False)
        db.query(TrendObservation).filter(TrendObservation.patient_id == pid).delete(synchronize_session=False)
        db.query(TestResult).filter(TestResult.patient_id == pid).delete(synchronize_session=False)
        db.query(ReportPage).filter(ReportPage.report_id == rid).delete(synchronize_session=False)
        db.query(PatientReport).filter(PatientReport.patient_id == pid).delete(synchronize_session=False)
        db.query(Patient).filter(Patient.patient_id == pid).delete(synchronize_session=False)
    db.commit()


class TestPatientRepository(unittest.TestCase):
    def setUp(self):
        self.db = SessionLocal()
        _cleanup(self.db)
        self.repo = PatientRepository(self.db)

    def tearDown(self):
        _cleanup(self.db)
        self.db.close()

    def test_upsert_and_get_patient(self):
        p = self.repo.upsert_patient({
            "patient_id": _PID_A,
            "name": "Repo Test A",
            "age": 40,
            "gender": "Female",
            "synthetic": True
        })
        self.assertEqual(p.patient_id, _PID_A)
        fetched = self.repo.get_patient(_PID_A)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.name, "Repo Test A")

    def test_upsert_patient_is_idempotent(self):
        """Calling upsert twice should not duplicate the record."""
        self.repo.upsert_patient({"patient_id": _PID_A, "name": "First", "synthetic": True})
        self.repo.upsert_patient({"patient_id": _PID_A, "name": "Updated", "synthetic": True})
        all_patients = self.db.query(Patient).filter(Patient.patient_id == _PID_A).all()
        self.assertEqual(len(all_patients), 1)
        self.assertEqual(all_patients[0].name, "Updated")

    def test_upsert_and_get_report(self):
        self.repo.upsert_patient({"patient_id": _PID_A, "name": "Repo A", "synthetic": True})
        r = self.repo.upsert_report({
            "report_id": _RID_A,
            "patient_id": _PID_A,
            "report_date": "2026-06-01",
            "processing_status": "REPORT_READY"
        })
        self.assertEqual(r.report_id, _RID_A)
        fetched = self.repo.get_report(_PID_A, _RID_A)
        self.assertIsNotNone(fetched)

    def test_add_and_get_test_results(self):
        self.repo.upsert_patient({"patient_id": _PID_A, "name": "Repo A", "synthetic": True})
        self.repo.upsert_report({
            "report_id": _RID_A, "patient_id": _PID_A,
            "report_date": "2026-06-01", "processing_status": "REPORT_READY"
        })
        results_data = [
            {
                "result_id": f"{_RID_A}_T1",
                "patient_id": _PID_A,
                "report_id": _RID_A,
                "test_name_original": "Hemoglobin",
                "test_name_normalized": "Hemoglobin",
                "original_value": "14.5",
                "original_unit": "g/dL",
                "normalized_value": 14.5,
                "normalized_unit": "g/dL",
                "reference_low": 12.0,
                "reference_high": 17.0,
                "status": "NORMAL",
                "extraction_confidence": 0.95,
                "source_page": 1,
                "source_text": "Hemoglobin 14.5 g/dL 12-17"
            }
        ]
        added = self.repo.add_test_results(results_data)
        self.assertEqual(len(added), 1)
        fetched = self.repo.get_report_results(_PID_A, _RID_A)
        self.assertEqual(len(fetched), 1)
        self.assertEqual(fetched[0].test_name_normalized, "Hemoglobin")

    def test_patient_scoping_isolation(self):
        """Patient B must not be able to access Patient A's reports."""
        self.repo.upsert_patient({"patient_id": _PID_A, "name": "Pat A", "synthetic": True})
        self.repo.upsert_patient({"patient_id": _PID_B, "name": "Pat B", "synthetic": True})
        self.repo.upsert_report({
            "report_id": _RID_A, "patient_id": _PID_A,
            "report_date": "2026-06-01", "processing_status": "REPORT_READY"
        })
        # Pat B trying to access Pat A's report
        report = self.repo.get_report(_PID_B, _RID_A)
        self.assertIsNone(report, "Patient B should not be able to access Patient A's report")

    def test_report_pages_stored_and_retrieved(self):
        self.repo.upsert_patient({"patient_id": _PID_A, "name": "Pages A", "synthetic": True})
        self.repo.upsert_report({
            "report_id": _RID_A, "patient_id": _PID_A,
            "report_date": "2026-06-01", "processing_status": "REPORT_READY"
        })
        self.repo.add_report_pages([
            {"report_id": _RID_A, "page_number": 1, "ocr_text": "Page 1 content", "ocr_confidence": 0.95},
            {"report_id": _RID_A, "page_number": 2, "ocr_text": "Page 2 content", "ocr_confidence": 0.88},
        ])
        pages = self.repo.get_report_pages(_RID_A)
        self.assertEqual(len(pages), 2)
        self.assertEqual(pages[0].page_number, 1)

    def test_trend_clear_and_upsert(self):
        self.repo.upsert_patient({"patient_id": _PID_A, "name": "Trend A", "synthetic": True})
        self.repo.upsert_trend({
            "patient_id": _PID_A,
            "test_name": "Hemoglobin",
            "first_value": 11.0,
            "latest_value": 13.5,
            "trend": "improving",
            "persistence": "resolved"
        })
        trends = self.repo.get_patient_trends(_PID_A)
        self.assertEqual(len(trends), 1)

        # Now clear and re-add
        self.repo.clear_patient_trends(_PID_A)
        trends_after = self.repo.get_patient_trends(_PID_A)
        self.assertEqual(len(trends_after), 0)

    def test_save_and_get_generated_report(self):
        self.repo.upsert_patient({"patient_id": _PID_A, "name": "Gen A", "synthetic": True})
        self.repo.upsert_report({
            "report_id": _RID_A, "patient_id": _PID_A,
            "report_date": "2026-06-01", "processing_status": "REPORT_READY"
        })
        saved = self.repo.save_generated_report(
            patient_id=_PID_A,
            report_id=_RID_A,
            summary="Summary text",
            findings="Findings text",
            evidence_json='{"test": true}',
            disclaimer="For informational purposes only.",
            prompt_version="patient_report_v1"
        )
        self.assertIsNotNone(saved)
        fetched = self.repo.get_generated_report(_PID_A, _RID_A)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.summary, "Summary text")
        self.assertEqual(fetched.prompt_version, "patient_report_v1")

    def test_count_helpers(self):
        """Count helpers must return non-negative integers."""
        self.assertGreaterEqual(self.repo.count_patients(), 0)
        self.assertGreaterEqual(self.repo.count_reports(), 0)
        self.assertGreaterEqual(self.repo.count_test_results(), 0)


if __name__ == "__main__":
    unittest.main()

