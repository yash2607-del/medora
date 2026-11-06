from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Integer,
    String,
    Text,
    ForeignKey,
    Index,
)

from patient.models.database import Base


class PatientAccount(Base):
    """
    Authentication account associated with exactly one patient.

    Authentication identity is separate from the Patient clinical
    record. The patient_id links the authenticated account to the
    existing patient data.
    """

    __tablename__ = "patient_accounts"

    id = Column(Integer, primary_key=True, autoincrement=True)

    patient_id = Column(
        String,
        ForeignKey("patients.patient_id"),
        nullable=False,
        unique=True,
        index=True,
    )

    username = Column(
        String,
        nullable=False,
        unique=True,
        index=True,
    )

    email = Column(
        String,
        nullable=True,
        unique=True,
        index=True,
    )

    password_hash = Column(
        String,
        nullable=False,
    )

    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
    )

    created_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )

    last_login_at = Column(
        DateTime,
        nullable=True,
    )

    failed_login_attempts = Column(
        Integer,
        nullable=False,
        default=0,
    )

    locked_until = Column(
        DateTime,
        nullable=True,
    )


class PatientSession(Base):
    """
    Server-side authenticated session.

    The browser receives only the random session token through an
    HttpOnly cookie. The token is stored as a hash in the database.
    """

    __tablename__ = "patient_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)

    account_id = Column(
        Integer,
        ForeignKey("patient_accounts.id"),
        nullable=False,
        index=True,
    )

    token_hash = Column(
        String,
        nullable=False,
        unique=True,
        index=True,
    )

    created_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )

    expires_at = Column(
        DateTime,
        nullable=False,
        index=True,
    )

    last_seen_at = Column(
        DateTime,
        nullable=True,
    )

    revoked = Column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
    )

    user_agent = Column(
        Text,
        nullable=True,
    )

    ip_address = Column(
        String,
        nullable=True,
    )


Index(
    "ix_patient_sessions_active_expiry",
    PatientSession.revoked,
    PatientSession.expires_at,
)