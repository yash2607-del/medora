import getpass

from patient.models.database import SessionLocal, init_db
from patient.models.patient_models import Patient
from auth.models import PatientAccount
from auth.security import hash_password


def create_demo_account():
    init_db()

    db = SessionLocal()

    try:
        patient_id = "P001"
        username = "patient_p001"

        patient = (
            db.query(Patient)
            .filter(Patient.patient_id == patient_id)
            .first()
        )

        if not patient:
            print(
                f"Patient {patient_id} does not exist."
            )
            print(
                "Create/import the patient record first."
            )
            return

        existing = (
            db.query(PatientAccount)
            .filter(
                PatientAccount.username == username
            )
            .first()
        )

        if existing:
            print(
                f"Account '{username}' already exists."
            )
            print(
                f"Linked patient: {existing.patient_id}"
            )
            return

        print()
        print("Creating demo patient account")
        print(f"Patient: {patient_id}")
        print(f"Username: {username}")
        print()

        password = getpass.getpass(
            "Enter demo password: "
        )

        password_confirm = getpass.getpass(
            "Confirm demo password: "
        )

        if not password:
            print("Password cannot be empty.")
            return

        if password != password_confirm:
            print("Passwords do not match.")
            return

        account = PatientAccount(
            patient_id=patient_id,
            username=username,
            password_hash=hash_password(password),
            is_active=True,
            email=None,
            failed_login_attempts=0,
        )

        db.add(account)
        db.commit()

        print()
        print("Demo account created successfully.")
        print()
        print(f"Username: {username}")
        print(f"Patient:  {patient_id}")
        print()
        print(
            "The password is stored only as a secure hash."
        )

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    create_demo_account()