from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from .database import Base

class Patient(Base):
    __tablename__ = "patients"

    patient_id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    age = Column(Integer, nullable=True)
    gender = Column(String, nullable=True)
    city = Column(String, nullable=True)
    state = Column(String, nullable=True)
    country = Column(String, nullable=True)
    date_of_birth = Column(String, nullable=True)
    synthetic = Column  (Boolean, default=True)

    # Relationships
    reports = relationship("PatientReport", back_populates="patient", cascade="all, delete-orphan", order_by="PatientReport.report_date")
    test_results = relationship("TestResult", back_populates="patient", cascade="all, delete-orphan")
    trends = relationship("TrendObservation", back_populates="patient", cascade="all, delete-orphan")
    generated_reports = relationship("GeneratedPatientReport", back_populates="patient", cascade="all, delete-orphan")


class PatientReport(Base):
    __tablename__ = "patient_reports"

    report_id = Column(String, primary_key=True, index=True)
    patient_id = Column(String, ForeignKey("patients.patient_id"), nullable=False, index=True)
    report_sequence = Column(Integer, default=1)
    report_type = Column(String, default="Diagnostic Report")
    report_category = Column(String, nullable=True)
    laboratory = Column(String, default="Lords Pathology")
    collection_date = Column(String, nullable=True)
    report_date = Column(String, nullable=False, index=True)
    source_type = Column(String, default="digital_pdf") # digital_pdf, scanned_pdf, camera_image, dataset_import
    original_file = Column(String, nullable=True)
    processing_status = Column(String, default="REPORT_READY") 
    # Processing states: UPLOADED, PROCESSING, OCR_COMPLETE, EXTRACTION_COMPLETE, VALIDATED, ANALYZED, REPORT_READY, FAILED
    ocr_quality_score = Column(Float, default=1.0)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    patient = relationship("Patient", back_populates="reports")
    pages = relationship("ReportPage", back_populates="report", cascade="all, delete-orphan")
    results = relationship("TestResult", back_populates="report", cascade="all, delete-orphan")
    generated_report = relationship("GeneratedPatientReport", back_populates="report", uselist=False, cascade="all, delete-orphan")


class ReportPage(Base):
    __tablename__ = "report_pages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    report_id = Column(String, ForeignKey("patient_reports.report_id"), nullable=False, index=True)
    page_number = Column(Integer, default=1)
    ocr_text = Column(Text, nullable=True)
    ocr_confidence = Column(Float, default=1.0)

    # Relationships
    report = relationship("PatientReport", back_populates="pages")


class TestResult(Base):
    __tablename__ = "test_results"

    result_id = Column(String, primary_key=True, index=True)
    patient_id = Column(String, ForeignKey("patients.patient_id"), nullable=False, index=True)
    report_id = Column(String, ForeignKey("patient_reports.report_id"), nullable=False, index=True)
    test_name_original = Column(String, nullable=False)
    test_name_normalized = Column(String, nullable=False, index=True)
    original_value = Column(String, nullable=False)
    original_unit = Column(String, nullable=True)
    normalized_value = Column(Float, nullable=True)
    normalized_unit = Column(String, nullable=True)
    reference_low = Column(Float, nullable=True)
    reference_high = Column(Float, nullable=True)
    reference_text = Column(String, nullable=True)
    status = Column(String, nullable=False, default="NORMAL") # LOW, NORMAL, HIGH, ABNORMAL
    extraction_confidence = Column(Float, default=1.0)
    source_page = Column(Integer, default=1)
    source_text = Column(Text, nullable=True)

    # Relationships
    patient = relationship("Patient", back_populates="test_results")
    report = relationship("PatientReport", back_populates="results")


class TrendObservation(Base):
    __tablename__ = "trend_observations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    patient_id = Column(String, ForeignKey("patients.patient_id"), nullable=False, index=True)
    test_name = Column(String, nullable=False, index=True)
    first_value = Column(Float, nullable=True)
    latest_value = Column(Float, nullable=True)
    absolute_change = Column(Float, nullable=True)
    percentage_change = Column(Float, nullable=True)
    previous_status = Column(String, nullable=True)
    current_status = Column(String, nullable=True)
    trend = Column(String, nullable=True) # improving, worsening, stable, fluctuating
    persistence = Column(String, nullable=True) # persistently_abnormal, newly_abnormal, resolved, stable_normal
    evidence = Column(Text, nullable=True) # JSON structured string

    # Relationships
    patient = relationship("Patient", back_populates="trends")


class GeneratedPatientReport(Base):
    __tablename__ = "generated_patient_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    report_id = Column(String, ForeignKey("patient_reports.report_id"), nullable=False, unique=True, index=True)
    patient_id = Column(String, ForeignKey("patients.patient_id"), nullable=False, index=True)
    generated_at = Column(DateTime, default=datetime.utcnow)
    summary = Column(Text, nullable=False)
    findings = Column(Text, nullable=True)
    evidence = Column(Text, nullable=True) # JSON structured string
    disclaimer = Column(Text, nullable=False)
    prompt_version = Column(String, default="patient_report_v1")

    # Relationships
    patient = relationship("Patient", back_populates="generated_reports")
    report = relationship("PatientReport", back_populates="generated_report")

