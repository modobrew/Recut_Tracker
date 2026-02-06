"""
Data loader for Recut Tracker dashboard.
Handles Excel parsing, data cleaning, and normalization.
"""

import pandas as pd
import numpy as np
from typing import Tuple, Optional


# =============================================================================
# COLUMN DEFINITIONS
# =============================================================================

# Sewing Repairs columns to keep (by index after setting proper header)
SEWING_REPAIRS_COLUMNS = [
    'Date',
    'Repair Discovered',
    'SKU-Colorway-Size',
    'PR#',
    'Total Qty',
    'Repair Qty',
    'Repair Time (min)',
    '% Repaired',
    'Reason for Repair',
    'Recut Qty',
    'Reason for Recut',
    'Fail Qty',
    'Reason for Fail',
    'Reason Code',
    'Manager',
    'SMO/PA',
    'CMO',
]

# Recut List columns to keep
RECUT_LIST_COLUMNS = [
    'CODE',
    'SKU',
    'Material',
    'Cut/Length',
    'QTY',
    'Operator/Order#',
    'Order#',
    'Document_No',
    'PA',
    'Time',
    'Date',
    'Due Date',
    'On list',
    'Done',
    'scrap?',
    'RECUT?',
    'FAILED?',
    'QTY Failed',
    'Date Scrapped',
]


# =============================================================================
# ERROR CODE DEPARTMENT MAPPING
# =============================================================================

# Sewing Repairs Reason Code -> Error Source
SEWING_REPAIRS_DEPT_MAP = {
    # Cutting Operator errors
    'A1A': 'Cutting Operator Error',
    'A1B': 'Cutting Operator Error',
    'A1C': 'Cutting Operator Error',
    'A1D': 'Cutting Operator Error',
    # Sewing Operator errors
    'A2A': 'Sewing Operator Error',
    'A2D': 'Sewing Operator Error',
    'S1': 'Sewing Operator Error',
    'S2': 'Sewing Operator Error',
    'S3': 'Sewing Operator Error',
    'S4': 'Sewing Operator Error',
    'S5': 'Sewing Operator Error',
    'S6': 'Sewing Operator Error',
    'S8': 'Sewing Operator Error',
    # Cutting Machine errors (Hot cut, Laser, Cold cut, Die clicker/Gerber)
    'A1': 'Cutting Machine Error',
    'B1C': 'Cutting Machine Error',
    'B1E': 'Cutting Machine Error',
    # Sewing Machine errors (Sewing machine, AMS)
    'A': 'Sewing Machine Error',
    'B2': 'Sewing Machine Error',
    # Other Machine errors
    'B3': 'Other Machine Error',
    # Material defects
    'C1': 'Material Defect',
    'C2': 'Material Defect',
    'C3': 'Material Defect',
}

# Recut List CODE -> Error Source
RECUT_LIST_DEPT_MAP = {
    # Sewing Operator errors
    'A': 'Sewing Operator Error',
    'A: SMO Error': 'Sewing Operator Error',
    'A: SMO ERROR': 'Sewing Operator Error',
    # Cutting Machine errors (Laser)
    'L': 'Cutting Machine Error',
    'L: Lazer error': 'Cutting Machine Error',
    # Sewing Machine errors (AMS)
    'AMS': 'Sewing Machine Error',
    'AMS: AMS error': 'Sewing Machine Error',
    # Other Machine errors (general machine error)
    'A*': 'Other Machine Error',
    'A* Machine Error': 'Other Machine Error',
    # Cutting Operator errors
    'B': 'Cutting Operator Error',
    'B: Wrong Material Cut': 'Cutting Operator Error',
    'C': 'Cutting Operator Error',
    'c': 'Cutting Operator Error',
    'C: Marking error': 'Cutting Operator Error',
    'F': 'Cutting Operator Error',
    'F: Material Cut Too Short': 'Cutting Operator Error',
    # Material defects
    'D': 'Material Defect',
    'D: Material Defect': 'Material Defect',
    # Other
    'E': 'Other',
    'E: Missing Pieces': 'Other',
    'P': 'Other',
    'P: PA Error': 'Other',
    'A/D': 'Other',
}


# =============================================================================
# NAME NORMALIZATION
# =============================================================================

def normalize_name(name: Optional[str]) -> Optional[str]:
    """
    Normalize a name to title case.
    Handles None/NaN values and strips whitespace.
    """
    if pd.isna(name) or name is None:
        return None
    name = str(name).strip()
    if not name:
        return None
    return name.title()


def normalize_smo_name(name: Optional[str]) -> Optional[str]:
    """
    Normalize SMO name format: First initial + Last name -> capitalize both.
    Examples: "jsmith" -> "JSmith", "JFERNANDEZ" -> "JFernandez", "dkennedy" -> "DKennedy"
    """
    if pd.isna(name) or name is None:
        return None
    name = str(name).strip()
    if not name:
        return None

    # If name is all caps or all lower, format as first letter cap + rest title case
    # Assume format is: first initial + last name (e.g., JSMITH, jsmith)
    if len(name) <= 1:
        return name.upper()

    # Capitalize first letter (initial) and first letter of remaining (last name start)
    first_initial = name[0].upper()
    rest = name[1:]

    # Find where the "last name" starts - capitalize it
    # If all same case, assume second char is start of last name
    if rest:
        last_name = rest[0].upper() + rest[1:].lower() if len(rest) > 1 else rest.upper()
        return first_initial + last_name

    return first_initial


# =============================================================================
# BOOLEAN COLUMN CLEANING
# =============================================================================

def clean_boolean(value) -> bool:
    """
    Clean boolean column values.
    Treats True, 'True', 'true', 'X', 'x', 'Y', 'y', '1', 1 as True.
    Everything else (including garbage values) as False.
    """
    if pd.isna(value):
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value == 1
    value = str(value).strip().lower()
    return value in ('true', 'x', 'y', '1', 'yes')


# =============================================================================
# DEPARTMENT CLASSIFICATION
# =============================================================================

def get_department_from_reason_code(reason_code: Optional[str]) -> str:
    """
    Map Sewing Repairs Reason Code to Error Source.
    Extracts the code prefix and maps to error source category.
    """
    if pd.isna(reason_code) or reason_code is None:
        return 'Unknown'

    code = str(reason_code).strip()

    # Try exact match first
    if code in SEWING_REPAIRS_DEPT_MAP:
        return SEWING_REPAIRS_DEPT_MAP[code]

    # Try to extract prefix (e.g., "A1A - Cutting Operator: Cutting Error" -> "A1A")
    prefix = code.split(' ')[0].split('-')[0].strip()
    if prefix in SEWING_REPAIRS_DEPT_MAP:
        return SEWING_REPAIRS_DEPT_MAP[prefix]

    # Check if starts with known patterns
    if code.startswith('A1') and not code.startswith('A1A') and not code.startswith('A1B') and not code.startswith('A1C') and not code.startswith('A1D'):
        return 'Cutting Machine Error'  # A1 = Laser error
    elif code.startswith('A1'):
        return 'Cutting Operator Error'
    elif code.startswith('A2') or code.startswith('S'):
        return 'Sewing Operator Error'
    elif code.startswith('B1C') or code.startswith('B1E'):
        return 'Cutting Machine Error'
    elif code.startswith('B2'):
        return 'Sewing Machine Error'
    elif code.startswith('B'):
        return 'Other Machine Error'
    elif code.startswith('C'):
        return 'Material Defect'

    return 'Other'


def get_department_from_recut_code(code: Optional[str]) -> str:
    """
    Map Recut List CODE to Error Source.
    """
    if pd.isna(code) or code is None:
        return 'Unknown'

    code = str(code).strip()

    # Try exact match first
    if code in RECUT_LIST_DEPT_MAP:
        return RECUT_LIST_DEPT_MAP[code]

    # Try lowercase match
    if code.lower() in {k.lower(): v for k, v in RECUT_LIST_DEPT_MAP.items()}:
        for k, v in RECUT_LIST_DEPT_MAP.items():
            if k.lower() == code.lower():
                return v

    # Check first character
    first_char = code[0].upper() if code else ''
    if first_char == 'A' and '*' in code:
        return 'Other Machine Error'
    elif first_char == 'A' and 'AMS' in code.upper():
        return 'Sewing Machine Error'
    elif first_char == 'A':
        return 'Sewing Operator Error'
    elif first_char == 'B':
        return 'Cutting Operator Error'
    elif first_char == 'C':
        return 'Cutting Operator Error'
    elif first_char == 'D':
        return 'Material Defect'
    elif first_char == 'E':
        return 'Other'
    elif first_char == 'F':
        return 'Cutting Operator Error'
    elif first_char == 'L':
        return 'Cutting Machine Error'
    elif first_char == 'P':
        return 'Other'

    return 'Other'


# =============================================================================
# DATA LOADERS
# =============================================================================

def load_sewing_repairs(xlsx: pd.ExcelFile) -> pd.DataFrame:
    """
    Load and clean the 2025 Sewing Repairs sheet.

    Returns:
        DataFrame with cleaned sewing repairs data.
    """
    # Read sheet - first row contains headers but pandas reads it as data row 0
    df = pd.read_excel(xlsx, sheet_name='2025 Sewing Repairs', header=0)

    # Set proper column names from first data row
    df.columns = df.iloc[0]
    df = df[1:].reset_index(drop=True)

    # Keep only needed columns (handle missing columns gracefully)
    available_cols = [col for col in SEWING_REPAIRS_COLUMNS if col in df.columns]
    df = df[available_cols].copy()

    # Parse dates
    if 'Date' in df.columns:
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')

    # Convert numeric columns
    numeric_cols = ['Total Qty', 'Repair Qty', 'Repair Time (min)', 'Recut Qty', 'Fail Qty']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)

    if '% Repaired' in df.columns:
        df['% Repaired'] = pd.to_numeric(df['% Repaired'], errors='coerce')

    # Normalize names
    if 'Manager' in df.columns:
        df['Manager'] = df['Manager'].apply(normalize_name)
    if 'CMO' in df.columns:
        df['CMO'] = df['CMO'].apply(normalize_name)
    # SMO uses special formatting (first initial + last name)
    if 'SMO/PA' in df.columns:
        df['SMO/PA'] = df['SMO/PA'].apply(normalize_smo_name)

    # Normalize Repair Discovered
    if 'Repair Discovered' in df.columns:
        df['Repair Discovered'] = df['Repair Discovered'].apply(
            lambda x: str(x).upper().strip() if pd.notna(x) else None
        )
        # Standardize to SEWING or QC
        df['Repair Discovered'] = df['Repair Discovered'].replace({
            'SEWING': 'SEWING',
            'QC': 'QC',
            'Qc': 'QC',
            'qc': 'QC',
        })

    # Add department classification
    if 'Reason Code' in df.columns:
        df['Department'] = df['Reason Code'].apply(get_department_from_reason_code)
    else:
        df['Department'] = 'Unknown'

    # Remove rows with no valid data (no date and no quantities)
    df = df.dropna(subset=['Date'], how='all')
    df = df[~((df['Repair Qty'] == 0) & (df['Recut Qty'] == 0) & (df['Fail Qty'] == 0))]

    return df


def load_recut_list(xlsx: pd.ExcelFile) -> pd.DataFrame:
    """
    Load and clean the Recut List sheet.

    Returns:
        DataFrame with cleaned recut list data.
    """
    df = pd.read_excel(xlsx, sheet_name='Recut List', header=0)

    # Keep only needed columns
    available_cols = [col for col in RECUT_LIST_COLUMNS if col in df.columns]
    df = df[available_cols].copy()

    # Parse dates
    date_cols = ['Date', 'Due Date', 'Date Scrapped']
    for col in date_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')

    # Convert numeric columns
    if 'QTY' in df.columns:
        df['QTY'] = pd.to_numeric(df['QTY'], errors='coerce').fillna(0).astype(int)
    if 'QTY Failed' in df.columns:
        df['QTY Failed'] = pd.to_numeric(df['QTY Failed'], errors='coerce').fillna(0).astype(int)

    # Clean boolean columns
    bool_cols = ['On list', 'Done', 'scrap?', 'RECUT?', 'FAILED?']
    for col in bool_cols:
        if col in df.columns:
            df[col] = df[col].apply(clean_boolean)

    # Normalize names
    name_cols = ['Operator/Order#', 'PA']
    for col in name_cols:
        if col in df.columns:
            df[col] = df[col].apply(normalize_name)

    # Normalize CODE (strip whitespace, handle case variations)
    if 'CODE' in df.columns:
        df['CODE'] = df['CODE'].apply(lambda x: str(x).strip() if pd.notna(x) else None)

    # Add department classification
    if 'CODE' in df.columns:
        df['Department'] = df['CODE'].apply(get_department_from_recut_code)
    else:
        df['Department'] = 'Unknown'

    # Remove rows with no valid data
    df = df.dropna(subset=['Date'], how='all')
    df = df[df['QTY'] > 0]

    return df


def load_data(file) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Load both sheets from the Rework Tracker Excel file.

    Args:
        file: File path or file-like object (from Streamlit uploader)

    Returns:
        Tuple of (sewing_repairs_df, recut_list_df)
    """
    xlsx = pd.ExcelFile(file)

    sewing_repairs = load_sewing_repairs(xlsx)
    recut_list = load_recut_list(xlsx)

    return sewing_repairs, recut_list


# =============================================================================
# FILTERING FUNCTIONS
# =============================================================================

def filter_by_date_range(
    df: pd.DataFrame,
    start_date: Optional[pd.Timestamp] = None,
    end_date: Optional[pd.Timestamp] = None,
    date_col: str = 'Date'
) -> pd.DataFrame:
    """
    Filter DataFrame by date range.
    """
    if date_col not in df.columns:
        return df

    filtered = df.copy()

    if start_date is not None:
        filtered = filtered[filtered[date_col] >= start_date]

    if end_date is not None:
        filtered = filtered[filtered[date_col] <= end_date]

    return filtered


def filter_by_department(
    df: pd.DataFrame,
    departments: list
) -> pd.DataFrame:
    """
    Filter DataFrame by department(s).
    """
    if 'Department' not in df.columns or not departments:
        return df

    return df[df['Department'].isin(departments)]


def filter_sewing_repairs_by_detection(
    df: pd.DataFrame,
    detection_location: str
) -> pd.DataFrame:
    """
    Filter Sewing Repairs by detection location (SEWING or QC).
    """
    if 'Repair Discovered' not in df.columns:
        return df

    return df[df['Repair Discovered'] == detection_location.upper()]


def filter_recut_list_by_codes(
    df: pd.DataFrame,
    codes: list
) -> pd.DataFrame:
    """
    Filter Recut List by error codes.
    Handles partial matches (e.g., 'A' matches 'A: SMO Error').
    """
    if 'CODE' not in df.columns or not codes:
        return df

    def matches_any_code(code):
        if pd.isna(code):
            return False
        code_str = str(code).strip().upper()
        for c in codes:
            c_upper = c.upper()
            # Exact match or starts with
            if code_str == c_upper or code_str.startswith(c_upper + ':') or code_str.startswith(c_upper + ' '):
                return True
            # Also check if the code starts with the filter
            if code_str.startswith(c_upper):
                return True
        return False

    return df[df['CODE'].apply(matches_any_code)]


# =============================================================================
# CUTTING MANAGER SPECIFIC FILTERS
# =============================================================================

def get_cutting_errors_sewing_repairs(df: pd.DataFrame) -> pd.DataFrame:
    """Get cutting-related records from Sewing Repairs (A1x codes)."""
    return filter_by_department(df, ['Cutting'])


def get_cutting_errors_recut_list(df: pd.DataFrame) -> pd.DataFrame:
    """Get cutting-related records from Recut List (B, C, F codes)."""
    return filter_by_department(df, ['Cutting'])


# =============================================================================
# SEWING MANAGER SPECIFIC FILTERS
# =============================================================================

def get_sewing_errors_sewing_repairs(df: pd.DataFrame) -> pd.DataFrame:
    """Get sewing-related records from Sewing Repairs (A2x, S codes)."""
    return filter_by_department(df, ['Sewing'])


def get_sewing_errors_recut_list(df: pd.DataFrame) -> pd.DataFrame:
    """Get sewing-related records from Recut List (A codes)."""
    return filter_by_department(df, ['Sewing'])
