"""
Medical Test Result Extractor.

Parses:
1. OCR text lines
2. Structured PDF table rows

into normalized medical test records.

Deterministic only. No LLM is used here.
"""

import re
from typing import List, Dict, Any, Optional

from ..normalization.normalizer import TestNormalizer
from ..normalization.dictionary import CANONICAL_TEST_MAPPINGS


class TestExtractor:

    KNOWN_TEST_NAMES = list(CANONICAL_TEST_MAPPINGS.keys())

    EXCLUDED_LINE_PATTERNS = [
        "test name",
        "reference interval",
        "reference range",
        "patient name",
        "patient id",
        "patient identifier",
        "date of birth",
        "collection date",
        "report date",
        "laboratory",
        "diagnostic panel",
        "testing note",
        "synthetic report",
        "for testing",
        "page",
        "phone",
        "barcode",
        "address",
        "email",
        "doctor",
        "dr.",
    ]

    @classmethod
    def extract_from_pages(
        cls,
        pages: List[Dict[str, Any]],
        report_id: str,
        patient_id: str,
        laboratory: str = "Lords Pathology",
        tables: Optional[List[Any]] = None,
    ) -> List[Dict[str, Any]]:

        extracted_results: List[Dict[str, Any]] = []

        # ---------------------------------------------------------
        # 1. Extract from normal OCR text
        # ---------------------------------------------------------

        for page in pages or []:

            page_num = page.get("page_number", 1)

            page_conf = float(
                page.get("confidence", 0.95) or 0.95
            )

            text = page.get("text", "") or ""

            for line in text.splitlines():

                line_clean = cls._clean_line(line)

                if not line_clean:
                    continue

                parsed = cls._parse_line(line_clean)

                if not parsed:
                    continue

                result = cls._build_result(
                    parsed=parsed,
                    report_id=report_id,
                    patient_id=patient_id,
                    page_num=page_num,
                    page_conf=page_conf,
                    source_text=line_clean,
                    laboratory=laboratory,
                    existing_count=len(extracted_results),
                )

                if result:
                    extracted_results.append(result)

        # ---------------------------------------------------------
        # 2. Extract from structured PDF tables
        # ---------------------------------------------------------

        for table in tables or []:

            rows = cls._normalize_table(table)

            for row in rows:

                parsed = cls._parse_table_row(row)

                if not parsed:
                    continue

                result = cls._build_result(
                    parsed=parsed,
                    report_id=report_id,
                    patient_id=patient_id,
                    page_num=parsed.get("page_num", 1),
                    page_conf=0.98,
                    source_text=" | ".join(row),
                    laboratory=laboratory,
                    existing_count=len(extracted_results),
                )

                if result:
                    extracted_results.append(result)

        # ---------------------------------------------------------
        # 3. Remove duplicate OCR/table matches
        # ---------------------------------------------------------

        deduped = []
        seen = set()

        for result in extracted_results:

            key = (
                result["test_name_normalized"].lower(),
                str(result["normalized_value"]),
                str(result["normalized_unit"]),
                str(result["reference_low"]),
                str(result["reference_high"]),
            )

            if key in seen:
                continue

            seen.add(key)
            deduped.append(result)

        # Re-number IDs after deduplication
        for index, result in enumerate(deduped, start=1):

            page_num = result.get("source_page", 1)

            result["result_id"] = (
                f"{report_id}_P{page_num}_{index}"
            )

        return deduped

    # =================================================================
    # Result construction
    # =================================================================

    @classmethod
    def _build_result(
        cls,
        parsed: Dict[str, Any],
        report_id: str,
        patient_id: str,
        page_num: int,
        page_conf: float,
        source_text: str,
        laboratory: str,
        existing_count: int,
    ) -> Optional[Dict[str, Any]]:

        orig_name = parsed["test_name"]
        value = parsed["value"]
        unit = parsed.get("unit")
        ref_low = parsed.get("ref_low")
        ref_high = parsed.get("ref_high")
        ref_text = parsed.get("ref_text")

        try:

            processed = TestNormalizer.process_test_entry(
                test_name_original=orig_name,
                raw_value=value,
                raw_unit=unit,
                printed_ref_low=ref_low,
                printed_ref_high=ref_high,
                printed_ref_text=ref_text,
                laboratory=laboratory,
            )

        except Exception:
            return None

        if not processed:
            return None

        confidence = round(
            min(
                max(
                    float(page_conf) * 0.95,
                    0.0,
                ),
                1.0,
            ),
            2,
        )

        return {
            "result_id": (
                f"{report_id}_P{page_num}_"
                f"{existing_count + 1}"
            ),
            "patient_id": patient_id,
            "report_id": report_id,
            "test_name_original": orig_name,
            "test_name_normalized": processed[
                "test_name_normalized"
            ],
            "original_value": processed[
                "original_value"
            ],
            "original_unit": processed[
                "original_unit"
            ],
            "normalized_value": processed[
                "normalized_value"
            ],
            "normalized_unit": processed[
                "normalized_unit"
            ],
            "reference_low": processed[
                "reference_low"
            ],
            "reference_high": processed[
                "reference_high"
            ],
            "reference_text": processed[
                "reference_text"
            ],
            "status": processed[
                "status"
            ],
            "extraction_confidence": confidence,
            "source_page": page_num,
            "source_text": source_text,
        }

    # =================================================================
    # OCR line parser
    # =================================================================

    @classmethod
    def _parse_line(
        cls,
        line: str,
    ) -> Optional[Dict[str, Any]]:

        if not line:
            return None

        if cls._is_excluded_line(line):
            return None

        # Find first numeric result.
        value_match = re.search(
            r"(?P<value>[<>]?\s*\d+(?:\.\d+)?)",
            line,
        )

        if not value_match:
            return None

        value = value_match.group("value").strip()

        name_part = line[
            :value_match.start()
        ].strip()

        name_part = re.sub(
            r"[:\-\|]+$",
            "",
            name_part,
        ).strip()

        if not cls._looks_like_test_name(name_part):
            return None

        remainder = line[
            value_match.end():
        ].strip()

        ref_low = None
        ref_high = None
        ref_text = None

        # 12.0 - 15.5
        range_match = re.search(
            r"(?P<low>\d+(?:\.\d+)?)"
            r"\s*(?:-|to)\s*"
            r"(?P<high>\d+(?:\.\d+)?)",
            remainder,
            flags=re.IGNORECASE,
        )

        if range_match:

            ref_low = float(
                range_match.group("low")
            )

            ref_high = float(
                range_match.group("high")
            )

            ref_text = range_match.group(0)

            unit_part = remainder[
                :range_match.start()
            ].strip()

        else:

            unit_part = remainder

            less_match = re.search(
                r"<\s*(\d+(?:\.\d+)?)",
                remainder,
            )

            greater_match = re.search(
                r">\s*(\d+(?:\.\d+)?)",
                remainder,
            )

            if less_match:

                ref_low = 0.0
                ref_high = float(
                    less_match.group(1)
                )

                ref_text = less_match.group(0)

                unit_part = remainder[
                    :less_match.start()
                ].strip()

            elif greater_match:

                ref_low = float(
                    greater_match.group(1)
                )

                ref_high = None

                ref_text = greater_match.group(0)

                unit_part = remainder[
                    :greater_match.start()
                ].strip()

        unit_part = re.sub(
            r"[\(\)]",
            "",
            unit_part,
        ).strip()

        unit = None

        if unit_part:

            # Common unit patterns.
            unit_match = re.match(
                r"^([A-Za-z0-9µμ/%\^\*\.\-_]+)",
                unit_part,
            )

            if unit_match:
                unit = unit_match.group(1)

        if ref_text is None and remainder:
            ref_text = remainder

        return {
            "test_name": name_part,
            "value": value,
            "unit": unit,
            "ref_low": ref_low,
            "ref_high": ref_high,
            "ref_text": ref_text,
        }

    # =================================================================
    # Structured table parser
    # =================================================================

    @classmethod
    def _parse_table_row(
        cls,
        row: List[str],
    ) -> Optional[Dict[str, Any]]:

        if not row:
            return None

        cells = [
            cls._clean_line(str(cell))
            for cell in row
            if cell is not None
        ]

        cells = [
            cell
            for cell in cells
            if cell
        ]

        if len(cells) < 2:
            return None

        joined = " | ".join(cells)

        if cls._is_excluded_line(joined):
            return None

        # Locate test name.
        name_index = None

        for i, cell in enumerate(cells):

            if cls._looks_like_test_name(cell):
                name_index = i
                break

        if name_index is None:
            return None

        test_name = cells[name_index]

        # Find numeric result after test name.
        value_index = None
        value = None

        for i in range(
            name_index + 1,
            len(cells),
        ):

            match = re.fullmatch(
                r"[<>]?\s*\d+(?:\.\d+)?",
                cells[i],
            )

            if match:

                value_index = i
                value = cells[i]
                break

        # Sometimes table extraction combines columns.
        if value_index is None:

            for i in range(
                name_index + 1,
                len(cells),
            ):

                parsed = cls._parse_line(
                    f"{test_name} {cells[i]}"
                )

                if parsed:
                    return parsed

            return None

        remaining = cells[
            value_index + 1:
        ]

        unit = None
        ref_low = None
        ref_high = None
        ref_text = None

        # Unit usually appears immediately after value.
        if remaining:

            candidate = remaining[0]

            if re.match(
                r"^[A-Za-z0-9µμ/%\^\*\.\-_]+$",
                candidate,
            ):
                unit = candidate
                remaining = remaining[1:]

        # Reference range may be one cell:
        # "12.0 - 15.5"
        # or two cells: "12.0", "15.5"
        reference_text = " ".join(
            remaining
        ).strip()

        range_match = re.search(
            r"(\d+(?:\.\d+)?)"
            r"\s*(?:-|to)"
            r"\s*"
            r"(\d+(?:\.\d+)?)",
            reference_text,
            flags=re.IGNORECASE,
        )

        if range_match:

            ref_low = float(
                range_match.group(1)
            )

            ref_high = float(
                range_match.group(2)
            )

            ref_text = range_match.group(0)

        else:

            # Handle two separate numeric cells.
            numeric_cells = []

            for cell in remaining:

                if re.fullmatch(
                    r"\d+(?:\.\d+)?",
                    cell,
                ):
                    numeric_cells.append(cell)

            if len(numeric_cells) >= 2:

                ref_low = float(
                    numeric_cells[0]
                )

                ref_high = float(
                    numeric_cells[1]
                )

                ref_text = (
                    f"{numeric_cells[0]} - "
                    f"{numeric_cells[1]}"
                )

            elif reference_text:

                ref_text = reference_text

        return {
            "test_name": test_name,
            "value": value,
            "unit": unit,
            "ref_low": ref_low,
            "ref_high": ref_high,
            "ref_text": ref_text,
        }

    # =================================================================
    # Table normalization
    # =================================================================

    @classmethod
    def _normalize_table(
        cls,
        table: Any,
    ) -> List[List[str]]:

        if table is None:
            return []

        # PyMuPDF table.extract() normally returns:
        #
        # [
        #   ["Test", "Result", "Unit", "Reference"],
        #   ["Hemoglobin", "10.8", "g/dL", "12.0-15.5"],
        # ]

        if isinstance(table, list):

            normalized = []

            for row in table:

                if isinstance(row, (list, tuple)):

                    normalized.append([
                        cls._clean_line(
                            str(cell)
                        )
                        for cell in row
                        if cell is not None
                    ])

                elif isinstance(row, str):

                    normalized.append(
                        [
                            cls._clean_line(x)
                            for x in re.split(
                                r"\t+|\|",
                                row,
                            )
                        ]
                    )

            return normalized

        return []

    # =================================================================
    # Helpers
    # =================================================================

    @classmethod
    def _clean_line(
        cls,
        line: str,
    ) -> str:

        if not line:
            return ""

        cleaned = line.replace(
            "\r",
            " ",
        )

        cleaned = cleaned.replace(
            "\xa0",
            " ",
        )

        cleaned = cleaned.replace(
            "–",
            "-",
        )

        cleaned = cleaned.replace(
            "—",
            "-",
        )

        cleaned = re.sub(
            r"\s+",
            " ",
            cleaned,
        )

        return cleaned.strip()

    @classmethod
    def _is_excluded_line(
        cls,
        line: str,
    ) -> bool:

        lower_line = line.lower()

        return any(
            pattern in lower_line
            for pattern in cls.EXCLUDED_LINE_PATTERNS
        )

    @classmethod
    def _looks_like_test_name(
        cls,
        name: str,
    ) -> bool:

        cleaned = name.strip()

        if len(cleaned) < 2:
            return False

        if len(cleaned) > 80:
            return False

        lower_name = cleaned.lower()

        # ---------------------------------------------------------
        # Explicitly reject patient/report metadata
        # ---------------------------------------------------------

        excluded_metadata = [
            "age / gender",
            "age/gender",
            "testing note",
            "synthetic report",
            "patient name",
            "patient id",
            "patient identifier",
            "date of birth",
            "collection date",
            "report date",
            "laboratory",
            "diagnostic panel",
        ]

        if any(
            metadata in lower_name
            for metadata in excluded_metadata
        ):
            return False

        # ---------------------------------------------------------
        # Known dictionary mappings
        # ---------------------------------------------------------

        for known in cls.KNOWN_TEST_NAMES:

            if known.lower() in lower_name:
                return True

        # ---------------------------------------------------------
        # Common laboratory terms
        # ---------------------------------------------------------

        medical_terms = [
            "hemoglobin",
            "haemoglobin",
            "wbc",
            "white blood",
            "rbc",
            "red blood",
            "platelet",
            "glucose",
            "fasting glucose",
            "creatinine",
            "urea",
            "bilirubin",
            "albumin",
            "protein",
            "cholesterol",
            "triglyceride",
            "hdl",
            "ldl",
            "alt",
            "sgpt",
            "ast",
            "sgot",
            "alkaline phosphatase",
            "alp",
            "sodium",
            "potassium",
            "calcium",
            "chloride",
            "tsh",
            "t3",
            "t4",
            "vitamin",
            "iron",
            "ferritin",
            "uric acid",
            "esr",
            "crp",
        ]

        if any(
            term in lower_name
            for term in medical_terms
        ):
            return True

        # ---------------------------------------------------------
        # Generic metadata rejection
        # ---------------------------------------------------------

        if re.search(
            r"\b(note|report|date|name|address|phone|id)\b",
            lower_name,
        ):
            return False

        # ---------------------------------------------------------
        # Final fallback
        # ---------------------------------------------------------

        return bool(
            re.search(
                r"[A-Za-z]",
                cleaned,
            )
        )
