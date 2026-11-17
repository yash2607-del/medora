"""
Initial demo data seeder.
Ensures tables exist and seeds a default demo patient and demo account on startup if absent.
"""
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
        # 1. Ensure demo patient exists
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
            logger.info("Demo patient P001 created.")

        # 2. Ensure demo account exists (username: demo / password: demo1234)
        demo_account = db.query(PatientAccount).filter(PatientAccount.username == "demo").first()
        if not demo_account:
            # Check if P001 is already linked to another account
            existing_p001_acc = db.query(PatientAccount).filter(PatientAccount.patient_id == "P001").first()
            if existing_p001_acc:
                existing_p001_acc.username = "demo"
                existing_p001_acc.password_hash = hash_password("demo1234")
                existing_p001_acc.is_active = True
                db.commit()
                logger.info("Updated existing P001 account to username 'demo'.")
            else:
                demo_account = PatientAccount(
                    patient_id="P001",
                    username="demo",
                    email=None,
                    password_hash=hash_password("demo1234"),
                    is_active=True,
                )
                db.add(demo_account)
                db.commit()
                logger.info("Created demo account 'demo' with password 'demo1234'.")
    except Exception as e:
        db.rollback()
        logger.warning(f"Demo seeding skipped or error: {e}")
    finally:
        db.close()
