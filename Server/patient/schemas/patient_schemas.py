from typing import List, Optional, Any, Dict
from datetime import datetime
from pydantic import BaseModel, Field

# Test Result Schemas
class TestResultBase(BaseModel):
    test_name_original: str
    test_name_normalized: str
    original_value: str
    original_unit: Optional[str] = None
    normalized_value: Optional[float] = None
    normalized_unit: Optional[str] = None
    reference_low: Optional[float] = None
    reference_high: Optional[float] = None
    reference_text: Optional[str] = None
    status: str
    extraction_confidence: float = 1.0
    source_page: int = 1
    source_text: Optional[str] = None

class TestResultCreate(TestResultBase):
    result_id: str
    patient_id: str
    report_id: str

class TestResultOut(TestResultBase):
    result_id: str
    patient_id: str
    report_id: str

    class Config:
        from_attributes = True

# Report Page Schemas
class ReportPageOut(BaseModel):
    id: int
    report_id: str
    page_number: int
    ocr_text: Optional[str] = None
    ocr_confidence: float = 1.0

    class Config:
        from_attributes = True

# Patient Report Schemas
class PatientReportBase(BaseModel):
    patient_id: str
    report_sequence: int = 1
    report_type: str = "Diagnostic Report"
    report_category: Optional[str] = None
    laboratory: str = "Lords Pathology"
    collection_date: Optional[str] = None
    report_date: str
    source_type: str = "digital_pdf"
    original_file: Optional[str] = None
    processing_status: str = "REPORT_READY"
    ocr_quality_score: float = 1.0

class PatientReportCreate(PatientReportBase):
    report_id: str

class PatientReportOut(PatientReportBase):
    report_id: str
    created_at: datetime
    abnormal_count: Optional[int] = 0
    total_tests: Optional[int] = 0

    class Config:
        from_attributes = True

class PatientReportDetail(PatientReportOut):
    results: List[TestResultOut] = []
    pages: List[ReportPageOut] = []

# Trend Observation Schemas
class TrendObservationOut(BaseModel):
    id: Optional[int] = None
    patient_id: str
    test_name: str
    first_value: Optional[float] = None
    latest_value: Optional[float] = None
    absolute_change: Optional[float] = None
    percentage_change: Optional[float] = None
    previous_status: Optional[str] = None
    current_status: Optional[str] = None
    trend: Optional[str] = None
    persistence: Optional[str] = None
    evidence: Optional[Any] = None

    class Config:
        from_attributes = True

# Generated Report Schemas
class GeneratedPatientReportOut(BaseModel):
    id: Optional[int] = None
    report_id: str
    patient_id: str
    generated_at: datetime
    summary: str
    findings: Optional[str] = None
    evidence: Optional[Any] = None
    disclaimer: str
    prompt_version: str

    class Config:
        from_attributes = True

# Patient Profile Schemas
class PatientBase(BaseModel):
    patient_id: str
    name: str
    age: Optional[int] = None
    gender: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = "India"
    date_of_birth: Optional[str] = None
    synthetic: bool = True

class PatientCreate(PatientBase):
    pass

class PatientOut(PatientBase):
    total_reports: Optional[int] = 0
    latest_report_date: Optional[str] = None

    class Config:
        from_attributes = True

# Patient Chat Schemas
class PatientChatRequest(BaseModel):
    patient_id: str
    query: str
    report_id: Optional[str] = None

class PatientChatResponse(BaseModel):
    answer: str
    patient_id: str
    evidence: List[Dict[str, Any]] = []
    disclaimer: str

# Evidence Schemas
class EvidenceItem(BaseModel):
    test_name: str
    current_value: Optional[float] = None
    previous_value: Optional[float] = None
    unit: Optional[str] = None
    reference_low: Optional[float] = None
    reference_high: Optional[float] = None
    status: str
    source_page: Optional[int] = None
    source_text: Optional[str] = None
    report_id: str
    report_date: Optional[str] = None

class ReportEvidenceResponse(BaseModel):
    report_id: str
    patient_id: str
    report_date: str
    items: List[EvidenceItem] = []

