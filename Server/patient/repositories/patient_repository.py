from typing import List, Optional, Dict, Any

from sqlalchemy.orm import Session
from sqlalchemy import func

from ..models.patient_models import (
    Patient,
    PatientReport,
    ReportPage,
    TestResult,
    TrendObservation,
    GeneratedPatientReport
)


class PatientRepository:
    def __init__(self, db: Session):
        self.db = db

    # ---------------------------------------------------------
    # Patient Profile Methods
    # ---------------------------------------------------------

    def get_patient(self, patient_id: str) -> Optional[Patient]:
        return (
            self.db.query(Patient)
            .filter(Patient.patient_id == patient_id)
            .first()
        )

    def list_patients(
        self,
        limit: int = 100,
        offset: int = 0
    ) -> List[Patient]:
        return (
            self.db.query(Patient)
            .offset(offset)
            .limit(limit)
            .all()
        )

    def upsert_patient(
        self,
        patient_data: Dict[str, Any]
    ) -> Patient:
        patient = self.get_patient(patient_data["patient_id"])

        if not patient:
            patient = Patient(**patient_data)
            self.db.add(patient)
        else:
            for k, v in patient_data.items():
                setattr(patient, k, v)

        self.db.commit()
        self.db.refresh(patient)

        return patient

    # ---------------------------------------------------------
    # Patient Report Methods
    # Strictly scoped by patient_id
    # ---------------------------------------------------------

    def get_report(
        self,
        patient_id: str,
        report_id: str
    ) -> Optional[PatientReport]:
        return (
            self.db.query(PatientReport)
            .filter(
                PatientReport.patient_id == patient_id,
                PatientReport.report_id == report_id
            )
            .first()
        )

    def list_patient_reports(
        self,
        patient_id: str
    ) -> List[PatientReport]:
        """
        Return all reports for a patient in deterministic
        chronological order.

        report_date is the primary ordering field.
        created_at is used as a tie-breaker when multiple
        reports have the same report_date.
        """
        return (
            self.db.query(PatientReport)
            .filter(
                PatientReport.patient_id == patient_id
            )
            .order_by(
                PatientReport.report_date.asc(),
                PatientReport.created_at.asc()
            )
            .all()
        )

    def upsert_report(
        self,
        report_data: Dict[str, Any]
    ) -> PatientReport:
        patient_id = report_data["patient_id"]
        report_id = report_data["report_id"]

        report = self.get_report(
            patient_id,
            report_id
        )

        if not report:
            report = PatientReport(**report_data)
            self.db.add(report)
        else:
            for k, v in report_data.items():
                setattr(report, k, v)

        self.db.commit()
        self.db.refresh(report)

        return report

    def update_report_status(
        self,
        patient_id: str,
        report_id: str,
        status: str,
        ocr_quality: Optional[float] = None,
        ocr_label: Optional[str] = None,
        error_msg: Optional[str] = None
    ) -> Optional[PatientReport]:

        report = self.get_report(
            patient_id,
            report_id
        )

        if report:
            report.processing_status = status

            if ocr_quality is not None:
                report.ocr_quality_score = ocr_quality

            # Store OCR label and error in metadata columns
            # if those columns exist on the model.
            if (
                ocr_label is not None
                and hasattr(report, "ocr_quality_label")
            ):
                report.ocr_quality_label = ocr_label

            if (
                error_msg is not None
                and hasattr(report, "processing_error")
            ):
                report.processing_error = error_msg

            self.db.commit()
            self.db.refresh(report)

        return report

    # ---------------------------------------------------------
    # Test Results Methods
    # Scoped by patient_id and optionally report_id
    # ---------------------------------------------------------

    def get_report_results(
        self,
        patient_id: str,
        report_id: str
    ) -> List[TestResult]:
        return (
            self.db.query(TestResult)
            .filter(
                TestResult.patient_id == patient_id,
                TestResult.report_id == report_id
            )
            .all()
        )

    def get_all_patient_results(
        self,
        patient_id: str
    ) -> List[TestResult]:
        """
        Return all historical test results for a patient
        across all reports chronologically.
        """
        return (
            self.db.query(TestResult)
            .join(
                PatientReport,
                TestResult.report_id == PatientReport.report_id
            )
            .filter(
                TestResult.patient_id == patient_id
            )
            .order_by(
                PatientReport.report_date.asc(),
                PatientReport.created_at.asc()
            )
            .all()
        )

    def add_test_results(
        self,
        results_data: List[Dict[str, Any]]
    ) -> List[TestResult]:

        if not results_data:
            return []

        ids = [r["result_id"] for r in results_data]
        existing_map = {
            r.result_id: r
            for r in self.db.query(TestResult).filter(TestResult.result_id.in_(ids)).all()
        } if ids else {}

        valid_cols = {c.name for c in TestResult.__table__.columns}
        added = []

        for r_data in results_data:
            cleaned_data = {k: v for k, v in r_data.items() if k in valid_cols}
            rid = cleaned_data.get("result_id")
            if rid in existing_map:
                existing = existing_map[rid]
                for k, v in cleaned_data.items():
                    setattr(existing, k, v)
                added.append(existing)
            else:
                res = TestResult(**cleaned_data)
                self.db.add(res)
                added.append(res)

        self.db.commit()

        return added

    # ---------------------------------------------------------
    # Report Pages
    # OCR text storage
    # ---------------------------------------------------------

    def add_report_pages(
        self,
        pages_data: List[Dict[str, Any]]
    ):
        for p in pages_data:
            page = ReportPage(**p)
            self.db.add(page)

        self.db.commit()

    def get_report_pages(
        self,
        report_id: str
    ) -> List[ReportPage]:
        return (
            self.db.query(ReportPage)
            .filter(
                ReportPage.report_id == report_id
            )
            .order_by(
                ReportPage.page_number.asc()
            )
            .all()
        )

    # ---------------------------------------------------------
    # Generated Patient Report Methods
    # ---------------------------------------------------------

    def save_generated_report(
        self,
        patient_id: str,
        report_id: str,
        summary: str,
        findings: str,
        evidence_json: str,
        disclaimer: str,
        prompt_version: str = "patient_report_v1"
    ) -> GeneratedPatientReport:

        existing = (
            self.db.query(GeneratedPatientReport)
            .filter(
                GeneratedPatientReport.patient_id == patient_id,
                GeneratedPatientReport.report_id == report_id
            )
            .first()
        )

        if existing:
            existing.summary = summary
            existing.findings = findings
            existing.evidence = evidence_json
            existing.disclaimer = disclaimer
            existing.prompt_version = prompt_version

            self.db.commit()
            self.db.refresh(existing)

            return existing

        gen_report = GeneratedPatientReport(
            patient_id=patient_id,
            report_id=report_id,
            summary=summary,
            findings=findings,
            evidence=evidence_json,
            disclaimer=disclaimer,
            prompt_version=prompt_version
        )

        self.db.add(gen_report)
        self.db.commit()
        self.db.refresh(gen_report)

        return gen_report

    def get_generated_report(
        self,
        patient_id: str,
        report_id: str
    ) -> Optional[GeneratedPatientReport]:

        return (
            self.db.query(GeneratedPatientReport)
            .filter(
                GeneratedPatientReport.patient_id == patient_id,
                GeneratedPatientReport.report_id == report_id
            )
            .first()
        )

    # ---------------------------------------------------------
    # Trend Methods
    # ---------------------------------------------------------

    def clear_patient_trends(
        self,
        patient_id: str
    ) -> None:
        """
        Delete all existing trend observations for a patient
        before recalculating.
        """
        self.db.query(TrendObservation).filter(
            TrendObservation.patient_id == patient_id
        ).delete(
            synchronize_session=False
        )

        self.db.commit()

    def upsert_trend(
        self,
        trend_data: Dict[str, Any]
    ) -> TrendObservation:
        """
        Insert a new trend observation.

        Trends are normally recalculated after
        clear_patient_trends().
        """
        trend = TrendObservation(
            **{
                k: v
                for k, v in trend_data.items()
                if hasattr(TrendObservation, k)
            }
        )

        self.db.add(trend)
        self.db.commit()
        self.db.refresh(trend)

        return trend

    def upsert_trends_bulk(
        self,
        trends_data: List[Dict[str, Any]]
    ) -> List[TrendObservation]:
        objects = [
            TrendObservation(
                **{
                    k: v
                    for k, v in t.items()
                    if hasattr(TrendObservation, k)
                }
            )
            for t in trends_data
        ]
        if objects:
            self.db.add_all(objects)
            self.db.commit()
        return objects

    def get_patient_trends(
        self,
        patient_id: str
    ) -> List[TrendObservation]:
        return (
            self.db.query(TrendObservation)
            .filter(
                TrendObservation.patient_id == patient_id
            )
            .all()
        )

    # ---------------------------------------------------------
    # Counts
    # ---------------------------------------------------------

    def count_patients(self) -> int:
        return self.db.query(Patient).count()

    def count_reports(self) -> int:
        return self.db.query(PatientReport).count()

    def count_test_results(self) -> int:
        return self.db.query(TestResult).count()

    # ---------------------------------------------------------
    # Report Deletion
    # ---------------------------------------------------------

    def delete_report(
        self,
        patient_id: str,
        report_id: str
    ) -> bool:
        """
        Delete one patient report and all patient-specific
        dependent data associated with it.

        Returns True when the report existed and was deleted.
        Returns False when the report was not found.
        """

        report = self.get_report(
            patient_id,
            report_id
        )

        if not report:
            return False

        # Delete test results belonging to this report.
        self.db.query(TestResult).filter(
            TestResult.patient_id == patient_id,
            TestResult.report_id == report_id
        ).delete(
            synchronize_session=False
        )

        # Delete OCR/page records belonging to this report.
        self.db.query(ReportPage).filter(
            ReportPage.report_id == report_id
        ).delete(
            synchronize_session=False
        )

        # Delete generated AI report(s) for this report.
        self.db.query(GeneratedPatientReport).filter(
            GeneratedPatientReport.patient_id == patient_id,
            GeneratedPatientReport.report_id == report_id
        ).delete(
            synchronize_session=False
        )

        # Delete the report itself.
        self.db.delete(report)

        self.db.commit()

        return True