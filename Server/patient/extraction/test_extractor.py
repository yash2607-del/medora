"""
Medical Test Result Extractor.

Parses:
1. OCR text lines
2. Structured PDF table rows

into normalized medical test records.
"""

import re
from typing import List, Dict, Any, Optional

from ..normalization.normalizer import TestNormalizer
from ..normalization.dictionary import CANONICAL_TEST_MAPPINGS


class TestExtractor:

    KNOWN_TEST_NAMES = list(CANONICAL_TEST_MAPPINGS.keys())

    EXCLUDED_PAGE_TITLES = [
        "machine & qc",
        "quality control",
        "laboratory equipment dashboard",
        "equipment details",
        "health advisory",
        "supplement suggestions",
        "about healthians",
        "credibility check",
        "how we control report accuracy",
        "summary & vital parameters",
        "report summary",
        "terms & conditions",
        "wellness guide",
        "patient advisory",
        "lifestyle recommendations",
        "doctor consultation",
        "frequently asked questions",
        "faq",
    ]

    SECTION_STOP_KEYWORDS = [
        "INTERPRETATION",
        "REMARKS",
        "NOTE:",
        "NOTES:",
        "CLINICAL SIGNIFICANCE",
        "RECOMMENDATIONS",
        "DISCLAIMER",
        "REFERENCE GROUP",
        "GUIDELINES",
        "VITAMIN D STATUS",
        "USES:",
        "INCREASED IN:",
        "DECREASED IN:",
        "COMMENTS:",
        "COMMENT:",
        "TEST REQUIREMENTS:",
        "IMPORTANT INSTRUCTIONS",
        "POTENTIAL SOURCES OF VARIATION",
        "BIO REF RANGE FOR",
    ]

    METADATA_LINE_PREFIXES = [
        "method:", "machine:", "instrument:", "patient name", "age/gender",
        "order id", "booking id", "sample", "sin no", "page ", "barcode",
        "customer since", "referred by", "collection date", "report date",
        "report generated", "report status", "testing note", "no diagnosis",
        "to order,", "physical recommended", "make your muscles", "remember,"
    ]

    CLINICAL_UNITS = {
        'mg/dl', 'mg/l', 'g/dl', 'g/l', 'u/l', 'iu/l', 'ug/dl', 'mcg/dl', 'ng/ml', 'pg/ml',
        'mmol/l', 'umol/l', 'meq/l', 'uiu/ml', 'miu/l', '10^3/ul', '10^6/ul', '%', 'ratio',
        'ml/min', 'fl', 'pg', '/cumm', 'cells/hpf', 'cells/lpf', 'index', 'sec', 'seconds',
        'iu/ml', 'copies/ml', 'g/l', 'mg/24hr', 'vol%', '/hpf', 'ml', '10^3/ul', 'cumm',
        'cells/cumm', 'hpf', 'lpf', 'percent'
    }

    DISQUALIFY_WORDS = {
        'is', 'are', 'was', 'were', 'for', 'with', 'from', 'that', 'this', 'have', 'has',
        'call', 'order', 'please', 'should', 'could', 'would', 'about', 'after', 'before',
        'your', 'must', 'partake', 'activity', 'minutes', 'hours', 'days', 'times', 'years',
        'frequency', 'description', 'department', 'machine', 'analyzer', 'instrument',
        'customer', 'received', 'collected', 'booking', 'barcode', 'sample', 'referred',
        'delivery', 'performed', 'variant', 'guidelines', 'method', 'technology', 'quality',
        'feature', 'optimal', 'desirable', 'borderline', 'risk', 'category', 'therapy',
        'action', 'assessment', 'assessments', 'presence', 'determine', 'prompt',
        'values', 'deficiency', 'insufficiency', 'sufficiency', 'toxicity',
        'trimester', 'pregnancy', 'undergo', 'undergoes', 'recommends', 'considered',
        'variation', 'circulating', 'steroid', 'regulating', 'mineralization',
        'causes', 'rickets', 'osteomalacia', 'intoxication', 'exposure', 'malabsorption',
        'dietary', 'coeliac', 'inflammatory', 'bowel', 'pancreatic', 'throughput',
        'utilizing', 'fusion', 'delivering', 'sigma', 'standards', 'performance'
    }

    REFERENCE_BRACKET_NAMES = {
        'deficiency', 'insufficiency', 'sufficiency', 'toxicity',
        'optimal', 'desirable', 'borderline', 'borderline high', 'high', 'very high',
        'normal', 'low', 'at risk', 'prediabetes', 'diabetes', 'diagnosing diabetes',
        'mild', 'moderate', 'severe', 'low risk', 'moderate risk', 'high risk',
        'extreme risk', 'category a', 'category b', 'category c', 'non diabetic',
        'first trimester', 'second trimester', 'third trimester', 'pregnancy interval',
        'adult', 'pediatric'
    }

    EXCLUDED_METADATA = [
        "age / gender", "age/gender", "agegender", "testing note", "testingnote",
        "synthetic report", "syntheticreport", "patient name", "patientname",
        "patient id", "patientid", "patient identifier", "date of birth",
        "dateofbirth", "collection date", "collectiondate", "report date",
        "reportdate", "laboratory", "diagnostic panel", "diagnosticpanel",
        "report category", "reportcategory", "lords pathology", "lordspathology"
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
            page_conf = float(page.get("confidence", 0.95) or 0.95)
            text = page.get("text", "") or ""

            # Check if this page is a non-clinical page (equipment, advisory, cover)
            if "Test Results" not in text:
                lower_text = text.lower()
                if any(title in lower_text for title in cls.EXCLUDED_PAGE_TITLES):
                    continue

            for line in text.splitlines():
                line_clean = cls._clean_line(line)
                if not line_clean:
                    continue

                # Stop extracting if interpretation / remarks / guidelines reached on this page
                if any(line_clean.upper().startswith(s) for s in cls.SECTION_STOP_KEYWORDS):
                    break

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
        # 2. Extract from structured PDF tables (supplementary)
        # ---------------------------------------------------------

        def _canonical_key(name: str) -> str:
            return re.sub(r'[^a-zA-Z0-9]', '', name).lower()

        existing_test_keys = {
            _canonical_key(r["test_name_normalized"])
            for r in extracted_results
        }
        existing_test_keys.update({
            _canonical_key(r["test_name_original"])
            for r in extracted_results
        })

        for table in tables or []:
            rows = cls._normalize_table(table)
            for row in rows:
                parsed = cls._parse_table_row(row)
                if not parsed:
                    continue

                test_name_cand = parsed.get("test_name", "")
                norm_cand = TestNormalizer.normalize_test_name(test_name_cand)
                key_norm = _canonical_key(norm_cand)
                key_orig = _canonical_key(test_name_cand)

                if key_norm in existing_test_keys or key_orig in existing_test_keys:
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
                    existing_test_keys.add(key_norm)
                    existing_test_keys.add(key_orig)

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
            "test_name_original": processed["test_name_original"],
            "test_name_normalized": processed["test_name_normalized"],
            "original_value": processed["original_value"],
            "original_unit": processed["original_unit"],
            "normalized_value": processed["normalized_value"],
            "normalized_unit": processed["normalized_unit"],
            "reference_low": processed["reference_low"],
            "reference_high": processed["reference_high"],
            "reference_text": processed["reference_text"],
            "status": processed["status"],
            "deterministic_reasons": processed.get(
                "deterministic_reasons",
                [],
            ),
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

        # Reject numbered footnotes or lists: e.g. "1. ", "7. "
        if re.match(r'^\s*\d+[\.\)]\s+', line):
            return None

        lower_line = line.lower()
        if any(lower_line.startswith(p) for p in cls.METADATA_LINE_PREFIXES):
            return None

        # Reject reference bracket lines or guideline subheaders
        if any(lower_line.startswith(p) for p in [
            "first trimester", "second trimester", "third trimester",
            "pregnancy interval", "bio ref range", "vitamin d status",
            "deficiency", "insufficiency", "sufficiency", "optimal",
            "borderline", "reference group", "interpretation"
        ]):
            return None

        # Must have a numeric test result
        val_m = re.search(r'\s+(?P<val>[<>]?\s*\d+(?:\.\d+)?)\s+', line)
        if not val_m:
            return None

        name_part = line[:val_m.start()].strip()
        value = val_m.group('val').strip()
        remainder = line[val_m.end():].strip()

        # Check if candidate looks like a medical test name
        if not cls._looks_like_test_name(name_part):
            return None

        # Parse reference range and unit from remainder
        ref_low = None
        ref_high = None
        ref_text = None
        unit = None

        range_m = re.search(r'(?P<low>\d+(?:\.\d+)?)\s*(?:-|–|to)\s*(?P<high>\d+(?:\.\d+)?)', remainder, re.IGNORECASE)
        less_m = re.search(r'<\s*=?\s*(?P<high>\d+(?:\.\d+)?)', remainder)
        greater_m = re.search(r'>\s*=?\s*(?P<low>\d+(?:\.\d+)?)', remainder)

        unit_part = remainder
        if range_m:
            ref_low = float(range_m.group('low'))
            ref_high = float(range_m.group('high'))
            ref_text = f"{ref_low} - {ref_high}"
            unit_part = remainder[:range_m.start()]
        elif less_m:
            ref_high = float(less_m.group('high'))
            ref_low = 0.0
            ref_text = f"<{ref_high}"
            unit_part = remainder[:less_m.start()]
        elif greater_m:
            ref_low = float(greater_m.group('low'))
            ref_text = f">{ref_low}"
            unit_part = remainder[:greater_m.start()]

        clean_u = re.sub(r'(?:Desirable|Optimal|Borderline|High|Low|Risk|Method|Machine|\:)+', '', unit_part, flags=re.IGNORECASE).strip()
        u_match = re.search(r'[A-Za-z0-9%/^–\.]+', clean_u)
        if u_match:
            unit = u_match.group(0)

        # Check unit and range validity
        clean_u_check = unit.strip().lower().replace(' ', '') if unit else ''
        has_valid_unit = (clean_u_check in cls.CLINICAL_UNITS) or any(
            clean_u_check.startswith(u)
            for u in ['mg/dl', 'g/dl', 'u/l', '10^3', 'ratio', 'mmol', '%', 'ug', 'pg', 'ng']
        )
        has_valid_range = (ref_low is not None) or (ref_high is not None)

        if not has_valid_unit and not has_valid_range:
            norm_name = TestNormalizer.normalize_test_name(name_part)
            if norm_name == "Unknown Test" or norm_name == name_part:
                return None

        return {
            "test_name": name_part,
            "value": value,
            "unit": unit,
            "ref_low": ref_low,
            "ref_high": ref_high,
            "ref_text": ref_text or "Reference range not specified",
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
        if any(joined.lower().startswith(p) for p in cls.METADATA_LINE_PREFIXES):
            return None

        # Locate test name
        name_index = None
        for i, cell in enumerate(cells):
            if cls._looks_like_test_name(cell):
                name_index = i
                break

        if name_index is None:
            return None

        test_name = cells[name_index]

        # Find numeric result after test name
        value_index = None
        value = None
        for i in range(name_index + 1, len(cells)):
            cell_val = cells[i].strip()
            v_match = re.search(r'(?P<val>[<>]?\s*\d+(?:\.\d+)?)', cell_val)
            if v_match:
                value_index = i
                value = v_match.group('val').strip()
                break

        if value_index is None or value is None:
            return None

        # Unit and reference interval
        unit = None
        ref_low = None
        ref_high = None
        ref_text = None

        if value_index + 1 < len(cells):
            unit_candidate = cells[value_index + 1].strip()
            clean_u = unit_candidate.lower().replace(' ', '')
            if clean_u in cls.CLINICAL_UNITS or any(clean_u.startswith(u) for u in ['mg/dl', 'g/dl', 'u/l', '10^3', 'ratio', 'mmol', '%', 'ug', 'pg', 'ng']):
                unit = unit_candidate

        # Find reference interval in remaining cells
        for j in range(value_index + 1, len(cells)):
            cell_text = cells[j]
            range_m = re.search(r'(?P<low>\d+(?:\.\d+)?)\s*(?:-|–|to)\s*(?P<high>\d+(?:\.\d+)?)', cell_text)
            less_m = re.search(r'<\s*=?\s*(?P<high>\d+(?:\.\d+)?)', cell_text)
            greater_m = re.search(r'>\s*=?\s*(?P<low>\d+(?:\.\d+)?)', cell_text)
            if range_m:
                ref_low = float(range_m.group('low'))
                ref_high = float(range_m.group('high'))
                ref_text = f"{ref_low} - {ref_high}"
                break
            elif less_m:
                ref_high = float(less_m.group('high'))
                ref_low = 0.0
                ref_text = f"<{ref_high}"
                break
            elif greater_m:
                ref_low = float(greater_m.group('low'))
                ref_text = f">{ref_low}"
                break

        clean_u_check = unit.strip().lower().replace(' ', '') if unit else ''
        has_valid_unit = (clean_u_check in cls.CLINICAL_UNITS) or any(
            clean_u_check.startswith(u)
            for u in ['mg/dl', 'g/dl', 'u/l', '10^3', 'ratio', 'mmol', '%', 'ug', 'pg', 'ng']
        )
        has_valid_range = (ref_low is not None) or (ref_high is not None)

        if not has_valid_unit and not has_valid_range:
            norm_name = TestNormalizer.normalize_test_name(test_name)
            if norm_name == "Unknown Test" or norm_name == test_name:
                return None

        return {
            "test_name": test_name,
            "value": value,
            "unit": unit,
            "ref_low": ref_low,
            "ref_high": ref_high,
            "ref_text": ref_text or "Reference range not specified",
        }

    # =================================================================
    # Table normalization
    # =================================================================

    @classmethod
    def _clean_cell_value(cls, cell: Any) -> str:
        if cell is None:
            return ""
        s = str(cell).strip()
        # Repair broken decimal breaks: e.g. '108\n.' -> '10.8'
        s = re.sub(r'(\d+)(\d)\s*\n\s*\.', r'\1.\2', s)
        s = re.sub(r'(\d+)(\d)\s+(\d+)(\d)\s*\n\s*\.\s*-\s*\.', r'\1.\2 - \3.\4', s)
        s = re.sub(r'(\d+)\s*\n\s*-\s*', r'\1 - ', s)
        return cls._clean_line(s)

    @classmethod
    def _normalize_table(
        cls,
        table: Any,
    ) -> List[List[str]]:

        if table is None:
            return []

        if isinstance(table, list):
            normalized = []
            for row in table:
                if isinstance(row, (list, tuple)):
                    normalized.append([
                        cls._clean_cell_value(cell)
                        for cell in row
                        if cell is not None
                    ])
                elif isinstance(row, str):
                    normalized.append(
                        [
                            cls._clean_cell_value(x)
                            for x in re.split(r"\t+|\|", row)
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

        cleaned = line.replace("\r", " ").replace("\xa0", " ").replace("–", "-").replace("—", "-")
        cleaned = re.sub(r"\s+", " ", cleaned)
        return cleaned.strip()

    @classmethod
    def _looks_like_test_name(
        cls,
        name: str,
    ) -> bool:

        cleaned = name.strip()
        if len(cleaned) < 2 or len(cleaned) > 55:
            return False

        if len(cleaned.split()) > 7:
            return False

        if ':' in cleaned or ';' in cleaned:
            return False

        # Reject if starts with digits (e.g. numbered list like "1. ", "7. ")
        if re.match(r'^\s*\d+[\.\)\-]', cleaned):
            return False

        # Reject bullets or symbols at start
        if re.match(r'^[\-\*\•\–\—\:\>\<\=]', cleaned):
            return False

        lower_name = cleaned.lower()

        # Reject dangling prepositions or conjunctions at the end
        if lower_name.endswith((' of', ' in', ' for', ' with', ' as', ' to', ' by', ' and', ' or', ' at', ' the', ' is', ' are', ' was', ' were', ' that')):
            return False

        # Reject reference bracket names
        if lower_name in cls.REFERENCE_BRACKET_NAMES:
            return False

        if any(lower_name.startswith(p) for p in [
            "first trimester", "second trimester", "third trimester",
            "pregnancy interval", "bio ref range", "vitamin d status",
            "reference group"
        ]):
            return False

        words_in_name = set(re.findall(r'\b[a-z]+\b', lower_name))
        if words_in_name & cls.DISQUALIFY_WORDS:
            return False

        compressed = re.sub(r'[^a-zA-Z0-9]', '', lower_name)
        for meta in cls.EXCLUDED_METADATA:
            if meta in lower_name or re.sub(r'[^a-zA-Z0-9]', '', meta) in compressed:
                return False

        # Reject pure numbers or date-like strings
        if re.fullmatch(r'[\d\.\-\s/]+', cleaned):
            return False

        return True
