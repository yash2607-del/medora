import os
import glob
import pandas as pd
from langchain_core.documents import Document
from typing import List


class ExcelLoader:
    """
    Loads diagnostic test data from an Excel file and converts
    each row into a LangChain Document with structured metadata.
    """

    def __init__(self, excel_path: str = None):
        if excel_path is None:
            base_dir = os.path.dirname(os.path.dirname(__file__))
            excel_dir = os.path.join(base_dir, "data", "excel")
            default_candidates = [
                os.path.join(excel_dir, "Lord Test MRP and DOS Complete Details External.xlsx"),
                os.path.join(excel_dir, "LORDS Directory of Service.Chatbot xlsx.xlsx"),
            ]
            
            found_path = None
            for cand in default_candidates:
                if os.path.exists(cand):
                    found_path = cand
                    break
            
            if not found_path and os.path.exists(excel_dir):
                xlsx_files = [
                    os.path.join(excel_dir, f)
                    for f in os.listdir(excel_dir)
                    if f.endswith(".xlsx") and not f.startswith("~$")
                ]
                if xlsx_files:
                    found_path = xlsx_files[0]

            excel_path = found_path or default_candidates[0]

        self.excel_path = excel_path

    def load_documents(self) -> List[Document]:
        """
        Reads sheets from the Excel file, converts each test row into a
        human-readable text block, and wraps it in a LangChain Document.
        """
        if not os.path.exists(self.excel_path):
            raise FileNotFoundError(
                f"Excel file not found at: {self.excel_path}"
            )

        print(f"Loading Excel file: {self.excel_path}")

        xl = pd.ExcelFile(self.excel_path)
        all_documents: List[Document] = []

        # Find relevant sheet(s)
        target_sheets = [
            s for s in xl.sheet_names
            if any(k in s.strip().lower() for k in ["external", "chatbot", "dos", "sheet1"])
        ]
        if not target_sheets:
            target_sheets = xl.sheet_names

        for sheet_name in target_sheets:
            print(f"  Processing sheet: '{sheet_name}'")
            df_raw = pd.read_excel(self.excel_path, sheet_name=sheet_name, header=None)

            # Auto-detect header row
            header_idx = None
            for r in range(min(15, len(df_raw))):
                row_vals = [str(v).strip().upper() for v in df_raw.iloc[r].dropna()]
                if any(x in row_vals for x in ["TEST NAME", "TEST CODE", "MRP"]):
                    header_idx = r
                    break

            if header_idx is not None:
                headers = [str(c).strip() for c in df_raw.iloc[header_idx]]
                df = df_raw.iloc[header_idx + 1:].copy()
                df.columns = headers
            else:
                df = pd.read_excel(self.excel_path, sheet_name=sheet_name)
                df.columns = [str(c).strip() for c in df.columns]

            # Drop completely empty rows
            df.dropna(how="all", inplace=True)

            # Check if row 0 has sub-headers (like original legacy file format)
            sub_headers = df.iloc[0] if not df.empty else None
            has_subheaders = False
            if sub_headers is not None:
                sub_str = " ".join([str(v) for v in sub_headers.dropna()]).upper()
                if "B2B" in sub_str or "P&L" in sub_str or "MRP" in sub_str:
                    has_subheaders = True

            col_definitions = []
            last_main_col = ""
            for col in df.columns:
                col_name = str(col).strip()
                sub = str(sub_headers.get(col, '')).strip() if (has_subheaders and sub_headers is not None) else ''

                if not col_name.startswith('Unnamed:') and not col_name.startswith('Base Rate'):
                    if col_name not in ['Feb', 'Mar', 'Apr', 'Total']:
                        last_main_col = col_name

                include = True
                final_name = col_name

                # Exclude B2B, P&L, Counts
                if any(k in sub.upper() for k in ['B2B', 'P&L', 'NET MRP']) or any(k in col_name.upper() for k in ['B2B', 'P&L']):
                    include = False
                elif 'MRP' in sub.upper():
                    final_name = f"{last_main_col} MRP Price".strip()
                elif col_name.upper() == 'MRP':
                    final_name = "MRP Price"
                elif sub and sub != 'nan' and has_subheaders:
                    final_name = sub.title()
                elif col_name.startswith('Unnamed:') or col_name == 'nan':
                    include = False

                col_definitions.append({
                    'original': col,
                    'clean_name': final_name,
                    'include': include
                })

            df_data = df.iloc[1:] if has_subheaders else df

            for idx, row in df_data.iterrows():
                parts = []
                test_name = ""
                test_code = ""
                dept = ""
                mrp_val = ""

                for col_def in col_definitions:
                    if not col_def['include']:
                        continue

                    val = row.get(col_def['original'])
                    if pd.notna(val) and str(val).strip() and str(val).strip() != '-':
                        v_str = str(val).strip()
                        c_name = col_def['clean_name']
                        
                        if "MRP" in c_name.upper() and not v_str.startswith("₹"):
                            try:
                                # Format nicely if numeric
                                num_val = float(v_str.replace(",", ""))
                                v_display = f"₹{int(num_val) if num_val.is_integer() else num_val}"
                            except ValueError:
                                v_display = f"₹{v_str}"
                            parts.append(f"{c_name}: {v_display}")
                            mrp_val = v_display
                        else:
                            parts.append(f"{c_name}: {v_str}")

                        if "TEST NAME" in c_name.upper():
                            test_name = v_str
                        elif "TEST CODE" in c_name.upper():
                            test_code = v_str
                        elif "DEPARTMENT" in c_name.upper():
                            dept = v_str

                if not parts:
                    continue

                page_content = "\n".join(parts)

                metadata = {
                    "source": "diagnostic_directory",
                    "sheet": sheet_name,
                    "row_index": int(idx),
                }
                if test_name:
                    metadata["test_name"] = test_name
                if test_code:
                    metadata["test_code"] = test_code
                if dept:
                    metadata["department"] = dept
                if mrp_val:
                    metadata["mrp"] = mrp_val

                all_documents.append(
                    Document(page_content=page_content, metadata=metadata)
                )

        print(f"Total diagnostic test documents loaded: {len(all_documents)}")
        return all_documents


if __name__ == "__main__":
    loader = ExcelLoader()
    docs = loader.load_documents()
    if docs:
        print(f"\nSample document (first test):\n{docs[0].page_content}")
        print(f"\nMetadata: {docs[0].metadata}")
