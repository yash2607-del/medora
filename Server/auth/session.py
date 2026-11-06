from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session

from auth.models import PatientAccount, PatientSession
from auth.security import (
    generate_session_token,
    hash_session_token,
)


SESSION_DURATION_HOURS = 24


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def create_session(
    db: Session,
    account: PatientAccount,
    user_agent: Optional[str] = None,
    ip_address: Optional[str] = None,
) -> str:
    """
    Create a new authenticated patient session.

    Returns the raw session token. The raw token is returned only so
    the API layer can place it into an HttpOnly cookie.
    """

    raw_token = generate_session_token()
    token_hash = hash_session_token(raw_token)

    now = utc_now()
    expires_at = now + timedelta(hours=SESSION_DURATION_HOURS)

    session = PatientSession(
        account_id=account.id,
        token_hash=token_hash,
        created_at=now,
        expires_at=expires_at,
        last_seen_at=now,
        revoked=False,
        user_agent=user_agent,
        ip_address=ip_address,
    )

    db.add(session)

    account.last_login_at = now
    account.failed_login_attempts = 0

    db.commit()
    db.refresh(session)

    return raw_token


def get_session(
    db: Session,
    raw_token: Optional[str],
) -> Optional[PatientSession]:
    """
    Resolve a browser session token to an active database session.

    Expired or revoked sessions are treated as unauthenticated.
    """

    if not raw_token:
        return None

    token_hash = hash_session_token(raw_token)

    session = (
        db.query(PatientSession)
        .filter(
            PatientSession.token_hash == token_hash,
            PatientSession.revoked.is_(False),
        )
        .first()
    )

    if not session:
        return None

    now = utc_now()

    if session.expires_at <= now:
        session.revoked = True
        db.commit()
        return None

    session.last_seen_at = now
    db.commit()

    return session


def get_authenticated_account(
    db: Session,
    raw_token: Optional[str],
) -> Optional[PatientAccount]:
    """
    Resolve a valid session to its patient account.
    """

    session = get_session(db, raw_token)

    if not session:
        return None

    return (
        db.query(PatientAccount)
        .filter(
            PatientAccount.id == session.account_id,
            PatientAccount.is_active.is_(True),
        )
        .first()
    )


def revoke_session(
    db: Session,
    raw_token: Optional[str],
) -> bool:
    """
    Revoke one authenticated session.
    """

    if not raw_token:
        return False

    token_hash = hash_session_token(raw_token)

    session = (
        db.query(PatientSession)
        .filter(
            PatientSession.token_hash == token_hash,
            PatientSession.revoked.is_(False),
        )
        .first()
    )

    if not session:
        return False

    session.revoked = True
    db.commit()

    return True


def revoke_all_sessions(
    db: Session,
    account_id: int,
) -> int:
    """
    Revoke every active session belonging to an account.

    Useful later for a "Log out everywhere" feature.
    """

    sessions = (
        db.query(PatientSession)
        .filter(
            PatientSession.account_id == account_id,
            PatientSession.revoked.is_(False),
        )
        .all()
    )

    for session in sessions:
        session.revoked = True

    db.commit()

    return len(sessions)