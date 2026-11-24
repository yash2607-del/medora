"""
Initial demo data seeder.
Ensures tables exist and seeds default accounts and demo data on startup if absent.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
from patient.models.database import SessionLocal, init_db
from patient.models import patient_models
from auth.models import PatientAccount
from auth.security import hash_password

logger = logging.getLogger(__name__)

def seed_demo_data():
    """Seeds default demo patient & account if they don't already exist."""
    init_db()
    db = SessionLocal()
    try:
        # Check if PAT0001 exists from dataset import
        pat0001 = db.query(patient_models.Patient).filter(patient_models.Patient.patient_id == "PAT0001").first()
        target_patient_id = "PAT0001" if pat0001 else "P001"

        if target_patient_id == "P001":
            demo_patient = db.query(patient_models.Patient).filter(patient_models.Patient.patient_id == "P001").first()
            if not demo_patient:
                demo_patient = patient_models.Patient(
                    patient_id="P001",
                    name="Demo Patient",
                    age=35,
                    gender="Female",
                    city="Delhi",
                    state="Delhi",
                    country="India",
                    synthetic=True,
                )
                db.add(demo_patient)
                db.commit()

        # Ensure demo account exists (username: demo / password: demo1234)
        demo_account = db.query(PatientAccount).filter(PatientAccount.username == "demo").first()
        if not demo_account:
            demo_account = PatientAccount(
                patient_id=target_patient_id,
                username="demo",
                email="demo@example.com",
                password_hash=hash_password("demo1234"),
                is_active=True,
            )
            db.add(demo_account)
            db.commit()
            print(f"Created demo account 'demo' with password 'demo1234' linked to {target_patient_id}.")
        else:
            demo_account.is_active = True
            demo_account.password_hash = hash_password("demo1234")
            db.commit()

    except Exception as e:
        db.rollback()
        logger.warning(f"Demo seeding skipped or error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_demo_data()
