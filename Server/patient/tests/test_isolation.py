"""
Critical Patient Data Isolation & Privacy Tests.
Verifies Section 3 & 24:
1. Patient medical data never enters the company ChromaDB collection.
2. Patient data access is strictly isolated by patient_id (Patient A cannot access Patient B).
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from patient.models.database import SessionLocal, init_db
from patient.models.patient_models import TestResult, Patient, PatientReport
from patient.services.patient_service import PatientService
from patient.repositories.patient_repository import PatientRepository
from vectordb.chroma_client import ChromaClient

class TestPatientIsolation(unittest.TestCase):
    def setUp(self):
        init_db()
        self.db = SessionLocal()
        self.service = PatientService(self.db)
        self.repo = PatientRepository(self.db)

    def tearDown(self):
        # Clean up any test isolation records so database remains pristine
        test_pids = ["TEST_ISOLATION_PAT", "PAT_A", "PAT_B"]
        for pid in test_pids:
            self.db.query(TestResult).filter(TestResult.patient_id == pid).delete()
            self.db.query(PatientReport).filter(PatientReport.patient_id == pid).delete()
            self.db.query(Patient).filter(Patient.patient_id == pid).delete()
        self.db.commit()
        self.db.close()

    def test_patient_data_never_enters_company_chromadb(self):
        """Verifies company ChromaDB vector store contains NO patient report records."""
        chroma = ChromaClient(collection_name="lord_diagnostics")
        chroma_collection = chroma.vector_store._collection
        initial_count = chroma_collection.count()

        # Perform patient operations
        p = self.repo.upsert_patient({
            "patient_id": "TEST_ISOLATION_PAT",
            "name": "Isolation Test Patient",
            "age": 45,
            "gender": "Female"
        })

        rep = self.repo.upsert_report({
            "report_id": "TEST_ISOLATION_REP",
            "patient_id": "TEST_ISOLATION_PAT",
            "report_date": "2025-05-01",
            "laboratory": "Lords Pathology"
        })

        self.repo.add_test_results([{
            "result_id": "TEST_ISOLATION_RES1",
            "patient_id": "TEST_ISOLATION_PAT",
            "report_id": "TEST_ISOLATION_REP",
            "test_name_original": "SGPT",
            "test_name_normalized": "ALT",
            "original_value": "88",
            "normalized_value": 88.0,
            "normalized_unit": "U/L",
            "status": "HIGH"
        }])

        # Re-check ChromaDB count
        post_count = chroma_collection.count()
        self.assertEqual(initial_count, post_count, "ChromaDB count altered! Patient data must NOT enter ChromaDB!")

        # Query ChromaDB for patient test ID to ensure zero results
        results = chroma.vector_store.similarity_search("TEST_ISOLATION_PAT", k=3)
        for doc in results:
            self.assertNotIn("TEST_ISOLATION_PAT", doc.page_content)
            self.assertNotIn("TEST_ISOLATION_PAT", str(doc.metadata))

    def test_patient_cross_access_prevention(self):
        """Verifies Patient A cannot access Patient B's report data."""
        # Patient A
        self.repo.upsert_patient({"patient_id": "PAT_A", "name": "Patient A"})
        self.repo.upsert_report({
            "report_id": "REP_A_001",
            "patient_id": "PAT_A",
            "report_date": "2025-01-01"
        })

        # Patient B
        self.repo.upsert_patient({"patient_id": "PAT_B", "name": "Patient B"})

        # Patient B attempts to get Patient A's report
        b_accessed_report = self.repo.get_report(patient_id="PAT_B", report_id="REP_A_001")
        self.assertIsNone(b_accessed_report, "Patient B was able to access Patient A's report!")

if __name__ == "__main__":
    unittest.main()
