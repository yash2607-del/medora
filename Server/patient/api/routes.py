"""
Patient Intelligence Layer — API Routes

All patient data lives in SQLite; nothing is written to ChromaDB.

Authentication:
- Patient identity comes from the authenticated server-side session.
- Frontend-supplied patient_id values are NOT trusted.
- Existing patient_id parameters are temporarily retained for
  frontend compatibility, but the backend always uses the session's
  patient_id.
"""

import os
from typing import List, Optional

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    UploadFile,
    File,
    Form,
    Query,
    Request,
)
from sqlalchemy.orm import Session

from auth.models import PatientAccount
from auth.session import get_authenticated_account

from ..models.database import get_db
from ..services.patient_service import PatientService
from ..schemas.patient_schemas import (
    PatientOut,
    PatientReportOut,
    PatientReportDetail,
    TestResultOut,
    PatientChatRequest,
    PatientChatResponse,
    ReportEvidenceResponse,
)

router = APIRouter()

# ── Config ────────────────────────────────────────────────────────────────────

_MAX_MB = int(os.getenv("PATIENT_MAX_UPLOAD_MB", "20"))


# ── Authentication Dependency ─────────────────────────────────────────────────


def get_current_account(
    request: Request,
    db: Session = Depends(get_db),
) -> PatientAccount:
    """
    Resolve the authenticated patient account from the server-side
    session cookie.

    The frontend cannot choose the patient identity.
    """

    raw_token = request.cookies.get("patient_session")

    account = get_authenticated_account(
        db=db,
        raw_token=raw_token,
    )

    if not account:
        raise HTTPException(
            status_code=401,
            detail="Authentication required.",
        )

    if not account.is_active:
        raise HTTPException(
            status_code=403,
            detail="Patient account is inactive.",
        )

    return account


def get_current_patient_id(
    account: PatientAccount = Depends(get_current_account),
) -> str:
    """
    Get the patient ID belonging to the authenticated account.

    This is the ONLY patient identity used by protected patient routes.
    """

    if not account.patient_id:
        raise HTTPException(
            status_code=403,
            detail="No patient is associated with this account.",
        )

    return account.patient_id


# ── Patient Profiles ─────────────────────────────────────────────────────────


@router.get(
    "/patients",
    response_model=List[PatientOut],
)
def get_patients(
    db: Session = Depends(get_db),
    patient_id: str = Depends(get_current_patient_id),
):
    """
    Return only the authenticated patient's profile.

    This temporarily preserves the existing frontend contract, which
    expects a list for PatientSelector.
    """

    service = PatientService(db)

    profile = service.get_patient_profile(patient_id)

    if not profile:
        raise HTTPException(
            status_code=404,
            detail="Patient not found.",
        )

    return [profile]


@router.get(
    "/patients/{patient_id}",
    response_model=PatientOut,
)
def get_patient(
    patient_id: str,
    db: Session = Depends(get_db),
    current_patient_id: str = Depends(get_current_patient_id),
):
    """
    Return the authenticated patient's profile.

    The path patient_id is deliberately NOT trusted.
    """

    if patient_id != current_patient_id:
        raise HTTPException(
            status_code=403,
            detail="You are not authorized to access this patient.",
        )

    service = PatientService(db)

    profile = service.get_patient_profile(
        current_patient_id
    )

    if not profile:
        raise HTTPException(
            status_code=404,
            detail="Patient not found.",
        )

    return profile


# ── Reports List & Detail ─────────────────────────────────────────────────────


@router.get(
    "/reports",
    response_model=List[PatientReportOut],
)
def get_patient_reports(
    # Kept temporarily for frontend compatibility.
    patient_id: Optional[str] = Query(
        None,
        description="Deprecated. Patient identity comes from session.",
    ),
    db: Session = Depends(get_db),
    current_patient_id: str = Depends(get_current_patient_id),
):
    service = PatientService(db)

    return service.get_patient_reports_summary(
        current_patient_id
    )


@router.get(
    "/reports/{report_id}",
    response_model=PatientReportDetail,
)
def get_report_detail(
    report_id: str,
    patient_id: Optional[str] = Query(
        None,
        description="Deprecated. Patient identity comes from session.",
    ),
    db: Session = Depends(get_db),
    current_patient_id: str = Depends(get_current_patient_id),
):
    service = PatientService(db)

    detail = service.get_report_detail(
        current_patient_id,
        report_id,
    )

    if not detail:
        raise HTTPException(
            status_code=404,
            detail="Report not found.",
        )

    return detail


@router.get(
    "/reports/{report_id}/results",
    response_model=List[TestResultOut],
)
def get_report_results(
    report_id: str,
    patient_id: Optional[str] = Query(
        None,
        description="Deprecated. Patient identity comes from session.",
    ),
    db: Session = Depends(get_db),
    current_patient_id: str = Depends(get_current_patient_id),
):
    service = PatientService(db)

    detail = service.get_report_detail(
        current_patient_id,
        report_id,
    )

    if not detail:
        raise HTTPException(
            status_code=404,
            detail="Report not found.",
        )

    return detail["results"]


# ── Report Status Polling ─────────────────────────────────────────────────────


@router.get("/reports/{report_id}/status")
def get_report_status(
    report_id: str,
    patient_id: Optional[str] = Query(
        None,
        description="Deprecated. Patient identity comes from session.",
    ),
    db: Session = Depends(get_db),
    current_patient_id: str = Depends(get_current_patient_id),
):
    """
    Lightweight status polling endpoint.
    """

    service = PatientService(db)

    status = service.get_report_status(
        current_patient_id,
        report_id,
    )

    if not status:
        raise HTTPException(
            status_code=404,
            detail="Report not found.",
        )

    return status


# ── Report Upload ─────────────────────────────────────────────────────────────


@router.post("/reports/upload")
async def upload_report(
    # Kept temporarily so the current frontend does not break.
    # It is NOT used to determine the patient.
    patient_id: Optional[str] = Form(
        None,
        description="Deprecated. Patient identity comes from session.",
    ),
    file: UploadFile = File(...),
    report_date: Optional[str] = Form(None),
    report_category: Optional[str] = Form("Diagnostic Panel"),
    laboratory: Optional[str] = Form("Lords Pathology"),
    db: Session = Depends(get_db),
    current_patient_id: str = Depends(get_current_patient_id),
):
    """
    Upload and synchronously process a patient lab report.

    Patient identity is derived exclusively from the authenticated
    session.
    """

    service = PatientService(db)

    # Pre-flight validation
    try:
        service.validate_upload(
            filename=file.filename or "upload.bin",
            content_type=file.content_type,
            file_size=None,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )

    try:
        result = service.process_uploaded_report(
            patient_id=current_patient_id,
            file_obj=file.file,
            filename=file.filename or "upload.bin",
            content_type=file.content_type,
            report_date=report_date,
            report_category=report_category,
            laboratory=laboratory,
        )

        return result

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )

    except RuntimeError as e:
        raise HTTPException(
            status_code=422,
            detail=str(e),
        )

    except Exception:
        import traceback

        traceback.print_exc()

        raise HTTPException(
            status_code=500,
            detail="Upload processing error. Please try again.",
        )


# ── Patient History Timeline ──────────────────────────────────────────────────


@router.get("/history")
def get_patient_history(
    patient_id: Optional[str] = Query(
        None,
        description="Deprecated. Patient identity comes from session.",
    ),
    db: Session = Depends(get_db),
    current_patient_id: str = Depends(get_current_patient_id),
):
    service = PatientService(db)

    return service.get_patient_reports_summary(
        current_patient_id
    )


# ── Longitudinal Trends ───────────────────────────────────────────────────────


@router.get("/trends")
def get_patient_trends(
    patient_id: Optional[str] = Query(
        None,
        description="Deprecated. Patient identity comes from session.",
    ),
    db: Session = Depends(get_db),
    current_patient_id: str = Depends(get_current_patient_id),
):
    service = PatientService(db)

    return service.refresh_patient_trends(
        current_patient_id
    )


# ── Summary / Dashboard ───────────────────────────────────────────────────────


@router.get("/summary")
def get_patient_summary(
    patient_id: Optional[str] = Query(
        None,
        description="Deprecated. Patient identity comes from session.",
    ),
    db: Session = Depends(get_db),
    current_patient_id: str = Depends(get_current_patient_id),
):
    service = PatientService(db)

    profile = service.get_patient_profile(
        current_patient_id
    )

    if not profile:
        raise HTTPException(
            status_code=404,
            detail="Patient not found.",
        )

    reports = service.get_patient_reports_summary(
        current_patient_id
    )

    latest_report = None

    if reports:
        latest_report = service.get_report_detail(
            current_patient_id,
            reports[-1]["report_id"],
        )

    trends = service.refresh_patient_trends(
        current_patient_id
    )

    return {
        "patient": profile,
        "reports_count": len(reports),
        "latest_report": latest_report,
        "key_trends": trends[:8],
    }


# ── AI Report Generation & Evidence ──────────────────────────────────────────


@router.post("/reports/{report_id}/generate")
def generate_ai_report(
    report_id: str,
    patient_id: Optional[str] = Query(
        None,
        description="Deprecated. Patient identity comes from session.",
    ),
    db: Session = Depends(get_db),
    current_patient_id: str = Depends(get_current_patient_id),
):
    """
    Generate or retrieve cached AI patient report.

    Evidence is pre-computed deterministically; the LLM only explains
    the structured patient evidence.
    """

    service = PatientService(db)

    try:
        return service.generate_patient_ai_report(
            current_patient_id,
            report_id,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=404,
            detail=str(e),
        )

    except Exception:
        raise HTTPException(
            status_code=500,
            detail=(
                "AI report generation encountered an error. "
                "Please try again."
            ),
        )


@router.get(
    "/reports/{report_id}/evidence",
    response_model=ReportEvidenceResponse,
)
def get_report_evidence(
    report_id: str,
    patient_id: Optional[str] = Query(
        None,
        description="Deprecated. Patient identity comes from session.",
    ),
    db: Session = Depends(get_db),
    current_patient_id: str = Depends(get_current_patient_id),
):
    """
    Return structured evidence for each finding in the report.
    """

    service = PatientService(db)

    detail = service.get_report_detail(
        current_patient_id,
        report_id,
    )

    if not detail:
        raise HTTPException(
            status_code=404,
            detail="Report not found.",
        )

    items = []

    for r in detail["results"]:
        items.append(
            {
                "test_name": r["test_name_normalized"],
                "current_value": r["normalized_value"],
                "previous_value": r.get("previous_value"),
                "unit": r["normalized_unit"],
                "reference_low": r["reference_low"],
                "reference_high": r["reference_high"],
                "status": r["status"],
                "source_page": r["source_page"],
                "source_text": r["source_text"],
                "report_id": report_id,
                "report_date": detail["report_date"],
            }
        )

    return {
        "report_id": report_id,
        "patient_id": current_patient_id,
        "report_date": detail["report_date"],
        "items": items,
    }


# ── Patient Conversational Chat ───────────────────────────────────────────────


@router.post(
    "/chat",
    response_model=PatientChatResponse,
)
def patient_chat(
    request: PatientChatRequest,
    db: Session = Depends(get_db),
    current_patient_id: str = Depends(get_current_patient_id),
):
    """
    Patient-specific question answering.

    Grounded exclusively in the authenticated patient's SQLite
    records. This endpoint does NOT query ChromaDB.
    """

    service = PatientService(db)

    try:
        return service.chat(
            patient_id=current_patient_id,
            query=request.query,
            report_id=request.report_id,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=404,
            detail=str(e),
        )

    except Exception:
        raise HTTPException(
            status_code=500,
            detail=(
                "Could not process your question. "
                "Please try again."
            ),
        )


# ── Health Check ──────────────────────────────────────────────────────────────


@router.get("/health")
def patient_health():
    """
    Health check intentionally remains public.
    """

    return {
        "status": "ok",
        "module": "Patient Intelligence Layer",
        "max_upload_mb": _MAX_MB,
    }