import os
import re

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from auth.models import PatientAccount
from auth.schemas import (
    SignupRequest,
    LoginRequest,
    LoginResponse,
    AuthMeResponse,
    LogoutResponse,
)
from auth.security import hash_password, verify_password
from auth.session import (
    create_session,
    get_authenticated_account,
    revoke_session,
)
from patient.models.database import get_db
from patient.models.patient_models import Patient


router = APIRouter()

SESSION_COOKIE_NAME = "patient_session"
COOKIE_MAX_AGE = 24 * 60 * 60


def set_session_cookie(response: Response, token: str):
    # Render sets RENDER=true or RENDER_SERVICE_ID in environment
    is_prod = bool(os.getenv("RENDER") or os.getenv("RENDER_SERVICE_ID") or os.getenv("ENVIRONMENT") == "production")
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        max_age=COOKIE_MAX_AGE,
        httponly=True,
        secure=True if is_prod else False,
        samesite="none" if is_prod else "lax",
        path="/",
    )


def clear_session_cookie(response: Response):
    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        path="/",
    )


def generate_patient_id(db: Session) -> str:
    existing_ids = db.query(Patient.patient_id).all()

    numbers = []

    for row in existing_ids:
        patient_id = row[0]
        match = re.fullmatch(r"P(\d+)", patient_id)

        if match:
            numbers.append(int(match.group(1)))

    next_number = max(numbers, default=0) + 1

    return f"P{next_number:03d}"


@router.post(
    "/signup",
    response_model=LoginResponse,
    status_code=status.HTTP_201_CREATED,
)
def signup(
    payload: SignupRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    username = payload.username.strip()
    email = str(payload.email).strip().lower() if payload.email else None

    if db.query(PatientAccount).filter(
        PatientAccount.username == username
    ).first():
        raise HTTPException(
            status_code=409,
            detail="Username is already registered.",
        )

    if email and db.query(PatientAccount).filter(
        PatientAccount.email == email
    ).first():
        raise HTTPException(
            status_code=409,
            detail="Email is already registered.",
        )

    patient_id = generate_patient_id(db)

    patient = Patient(
        patient_id=patient_id,
        name=payload.name.strip(),
        age=payload.age,
        gender=payload.gender.strip(),
        city=payload.city.strip(),
        state=payload.state.strip() if payload.state else None,
        country=payload.country.strip() if payload.country else None,
        synthetic=False,
    )

    account = PatientAccount(
        patient_id=patient_id,
        username=username,
        email=email,
        password_hash=hash_password(payload.password),
        is_active=True,
    )

    try:
        db.add(patient)
        db.add(account)
        db.commit()
        db.refresh(account)

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Registration conflict. Please try another username or email.",
        )

    raw_token = create_session(
        db=db,
        account=account,
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None,
    )

    set_session_cookie(response, raw_token)

    return LoginResponse(
        authenticated=True,
        username=account.username,
        patient_id=account.patient_id,
        token=raw_token,
    )


@router.post(
    "/login",
    response_model=LoginResponse,
)
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    username = payload.username.strip()

    account = (
        db.query(PatientAccount)
        .filter(PatientAccount.username == username)
        .first()
    )

    if not account or not account.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
        )

    if not verify_password(
        payload.password,
        account.password_hash,
    ):
        account.failed_login_attempts += 1
        db.commit()

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
        )

    raw_token = create_session(
        db=db,
        account=account,
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None,
    )

    set_session_cookie(response, raw_token)

    return LoginResponse(
        authenticated=True,
        username=account.username,
        patient_id=account.patient_id,
        token=raw_token,
    )


@router.get(
    "/me",
    response_model=AuthMeResponse,
)
def me(
    request: Request,
    db: Session = Depends(get_db),
):
    raw_token = request.cookies.get(SESSION_COOKIE_NAME)
    if not raw_token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            raw_token = auth_header.split(" ", 1)[1].strip()

    account = get_authenticated_account(
        db,
        raw_token,
    )

    if not account:
        return AuthMeResponse(authenticated=False)

    return AuthMeResponse(
        authenticated=True,
        username=account.username,
        patient_id=account.patient_id,
    )


@router.post(
    "/logout",
    response_model=LogoutResponse,
)
def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    raw_token = request.cookies.get(SESSION_COOKIE_NAME)

    revoke_session(db, raw_token)
    clear_session_cookie(response)

    return LogoutResponse(
        authenticated=False,
        message="Logged out successfully.",
    )