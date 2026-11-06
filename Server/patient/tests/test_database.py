"""
test_database.py — Phase 2/Final Phase Test

Verifies:
- Database path is correct
- Tables are auto-created on init
- All 6 tables exist
- Session factory works
"""

import os
import sys
import unittest

# Make patient module importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from patient.models.database import engine, SessionLocal, DATABASE_PATH


class TestDatabaseInit(unittest.TestCase):
    def test_database_path_within_server_data(self):
        """DB path must point inside Server/data/patient/ and end with .db"""
        self.assertIn("patient", DATABASE_PATH)
        self.assertTrue(DATABASE_PATH.endswith(".db"),
                        f"Expected .db path, got: {DATABASE_PATH}")

    def test_database_file_exists(self):
        """SQLite file must exist after init (auto-created on import)."""
        self.assertTrue(
            os.path.isfile(DATABASE_PATH),
            f"Database file not found at: {DATABASE_PATH}"
        )

    def test_all_tables_created(self):
        """All 6 patient tables must exist in the SQLite schema."""
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        required = {
            "patients",
            "patient_reports",
            "report_pages",
            "test_results",
            "trend_observations",
            "generated_patient_reports"
        }
        missing = required - set(tables)
        self.assertEqual(missing, set(), f"Missing tables: {missing}")

    def test_session_factory_creates_session(self):
        """SessionLocal must return a working SQLAlchemy session."""
        db = SessionLocal()
        try:
            # A simple query to verify session is live
            from sqlalchemy import text
            result = db.execute(text("SELECT 1")).scalar()
            self.assertEqual(result, 1)
        finally:
            db.close()

    def test_database_directory_exists(self):
        """Parent directory of the DB must exist."""
        parent = os.path.dirname(DATABASE_PATH)
        self.assertTrue(os.path.isdir(parent),
                        f"DB directory missing: {parent}")


if __name__ == "__main__":
    unittest.main()

