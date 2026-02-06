"""
Metrics calculations for Recut Tracker dashboard.
KPI functions for each role view.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, Tuple

from .sku_utils import add_parent_sku_column, aggregate_recuts_with_materials


# =============================================================================
# COMMON METRICS
# =============================================================================

def calculate_totals(
    sewing_repairs: pd.DataFrame,
    recut_list: pd.DataFrame
) -> Dict[str, Any]:
    """
    Calculate common totals across both data sources.

    Returns dict with:
        - total_repairs: Sum of Repair Qty
        - total_repair_time_min: Sum of Repair Time (min)
        - total_repair_time_hrs: Sum of Repair Time in hours
        - total_recut_pieces: Sum of QTY from Recut List
        - total_fails: Sum of Fail Qty
        - total_incidents_repairs: Count of Sewing Repairs records
        - total_incidents_recuts: Count of Recut List records
        - total_rework_events: Combined count
    """
    total_repairs = sewing_repairs['Repair Qty'].sum() if 'Repair Qty' in sewing_repairs.columns else 0
    total_repair_time_min = sewing_repairs['Repair Time (min)'].sum() if 'Repair Time (min)' in sewing_repairs.columns else 0
    total_recut_pieces = recut_list['QTY'].sum() if 'QTY' in recut_list.columns else 0
    total_fails = sewing_repairs['Fail Qty'].sum() if 'Fail Qty' in sewing_repairs.columns else 0
    total_recut_qty_repairs = sewing_repairs['Recut Qty'].sum() if 'Recut Qty' in sewing_repairs.columns else 0

    return {
        'total_repairs': int(total_repairs),
        'total_repair_time_min': int(total_repair_time_min),
        'total_repair_time_hrs': round(total_repair_time_min / 60, 1),
        'total_recut_pieces': int(total_recut_pieces),
        'total_recut_qty_repairs': int(total_recut_qty_repairs),
        'total_fails': int(total_fails),
        'total_incidents_repairs': len(sewing_repairs),
        'total_incidents_recuts': len(recut_list),
        'total_rework_events': len(sewing_repairs) + len(recut_list),
    }


def calculate_error_source_breakdown(
    sewing_repairs: pd.DataFrame,
    recut_list: pd.DataFrame
) -> pd.DataFrame:
    """
    Calculate incident counts by Error Source.

    Returns DataFrame with columns:
        - Error_Source
        - Incidents (count)
        - Pct_of_Total
        - Repair_Qty (from Sewing Repairs)
        - Recut_Pieces (from Recut List)
        - Fail_Qty
        - Total_Repair_Time_Min
    """
    # Count by error source from each source
    repairs_by_dept = sewing_repairs.groupby('Department').agg({
        'Repair Qty': 'sum',
        'Fail Qty': 'sum',
        'Recut Qty': 'sum',
        'Repair Time (min)': 'sum',
    }).reset_index()
    repairs_by_dept['Incidents_Repairs'] = sewing_repairs.groupby('Department').size().values

    recuts_by_dept = recut_list.groupby('Department').agg({
        'QTY': 'sum',
    }).reset_index()
    recuts_by_dept['Incidents_Recuts'] = recut_list.groupby('Department').size().values
    recuts_by_dept.columns = ['Department', 'Recut_Pieces', 'Incidents_Recuts']

    # Merge
    result = repairs_by_dept.merge(recuts_by_dept, on='Department', how='outer').fillna(0)

    # Calculate totals
    result['Incidents'] = result['Incidents_Repairs'] + result['Incidents_Recuts']
    total_incidents = result['Incidents'].sum()
    result['Pct_of_Total'] = (result['Incidents'] / total_incidents * 100).round(1) if total_incidents > 0 else 0

    # Rename columns
    result = result.rename(columns={
        'Department': 'Error_Source',
        'Repair Qty': 'Repair_Qty',
        'Fail Qty': 'Fail_Qty',
        'Recut Qty': 'Recut_Qty',
        'Repair Time (min)': 'Total_Repair_Time_Min',
    })

    # Select and order columns
    cols = ['Error_Source', 'Incidents', 'Pct_of_Total', 'Repair_Qty', 'Recut_Pieces', 'Fail_Qty', 'Total_Repair_Time_Min']
    result = result[[c for c in cols if c in result.columns]]

    return result.sort_values('Incidents', ascending=False)


# Keep old function name for backward compatibility
def calculate_department_breakdown(sewing_repairs: pd.DataFrame, recut_list: pd.DataFrame) -> pd.DataFrame:
    """Alias for calculate_error_source_breakdown for backward compatibility."""
    return calculate_error_source_breakdown(sewing_repairs, recut_list)


# =============================================================================
# CUTTING MANAGER METRICS
# =============================================================================

def calculate_cutting_manager_metrics(
    sewing_repairs: pd.DataFrame,
    recut_list: pd.DataFrame
) -> Dict[str, Any]:
    """
    Calculate metrics specific to Cutting Manager view.
    Focuses on A1x codes (Sewing Repairs) and B/C/F codes (Recut List).
    """
    # Filter to cutting-related records
    cutting_repairs = sewing_repairs[sewing_repairs['Department'] == 'Cutting Operator Error']
    cutting_recuts = recut_list[recut_list['Department'] == 'Cutting Operator Error']

    # Total recut pieces from Recut List (B/C/F codes)
    total_recut_pieces = cutting_recuts['QTY'].sum() if len(cutting_recuts) > 0 else 0

    # Cutting incidents from Sewing Repairs (A1x codes)
    total_cutting_incidents = len(cutting_repairs)
    recut_qty_from_repairs = cutting_repairs['Recut Qty'].sum() if 'Recut Qty' in cutting_repairs.columns else 0
    fail_qty_from_cutting = cutting_repairs['Fail Qty'].sum() if 'Fail Qty' in cutting_repairs.columns else 0

    # Error type breakdown from Sewing Repairs
    cutting_errors = len(cutting_repairs[cutting_repairs['Reason Code'].str.contains('A1A', na=False, case=False)]) if 'Reason Code' in cutting_repairs.columns else 0
    marking_errors_repairs = len(cutting_repairs[cutting_repairs['Reason Code'].str.contains('A1B', na=False, case=False)]) if 'Reason Code' in cutting_repairs.columns else 0
    kitting_errors = len(cutting_repairs[cutting_repairs['Reason Code'].str.contains('A1C', na=False, case=False)]) if 'Reason Code' in cutting_repairs.columns else 0

    # Error type breakdown from Recut List
    cutting_errors_recuts = len(cutting_recuts[cutting_recuts['CODE'].str.upper().str.startswith('B', na=False)]) if 'CODE' in cutting_recuts.columns else 0
    marking_errors_recuts = len(cutting_recuts[cutting_recuts['CODE'].str.upper().str.startswith('C', na=False)]) if 'CODE' in cutting_recuts.columns else 0
    cut_short_errors = len(cutting_recuts[cutting_recuts['CODE'].str.upper().str.startswith('F', na=False)]) if 'CODE' in cutting_recuts.columns else 0

    return {
        'total_recut_pieces': int(total_recut_pieces),
        'total_cutting_incidents': int(total_cutting_incidents),
        'recut_qty_from_repairs': int(recut_qty_from_repairs),
        'fail_qty_from_cutting': int(fail_qty_from_cutting),
        'cutting_errors': int(cutting_errors + cutting_errors_recuts),
        'marking_errors': int(marking_errors_repairs + marking_errors_recuts),
        'kitting_errors': int(kitting_errors),
        'cut_short_errors': int(cut_short_errors),
    }


def get_cutting_recuts_by_material(recut_list: pd.DataFrame) -> pd.DataFrame:
    """
    Get recut pieces by material for Cutting Manager.
    Filters to B/C/F codes only.
    """
    cutting_recuts = recut_list[recut_list['Department'] == 'Cutting Operator Error'].copy()

    if len(cutting_recuts) == 0:
        return pd.DataFrame(columns=['Material', 'Total_Recut_Pieces', 'Cutting_Errors', 'Marking_Errors', 'Cut_Too_Short'])

    # Aggregate by material
    result = cutting_recuts.groupby('Material').agg({
        'QTY': 'sum',
    }).reset_index()
    result.columns = ['Material', 'Total_Recut_Pieces']

    # Add error type breakdown
    def count_by_code_prefix(df, material, prefix):
        subset = df[(df['Material'] == material) & (df['CODE'].str.upper().str.startswith(prefix, na=False))]
        return subset['QTY'].sum()

    result['Cutting_Errors'] = result['Material'].apply(lambda m: count_by_code_prefix(cutting_recuts, m, 'B'))
    result['Marking_Errors'] = result['Material'].apply(lambda m: count_by_code_prefix(cutting_recuts, m, 'C'))
    result['Cut_Too_Short'] = result['Material'].apply(lambda m: count_by_code_prefix(cutting_recuts, m, 'F'))

    return result.sort_values('Total_Recut_Pieces', ascending=False)


def get_cutting_recuts_by_parent_sku(recut_list: pd.DataFrame) -> pd.DataFrame:
    """
    Get recut pieces by Parent SKU for Cutting Manager.
    Includes materials affected.
    """
    cutting_recuts = recut_list[recut_list['Department'] == 'Cutting Operator Error'].copy()

    if len(cutting_recuts) == 0:
        return pd.DataFrame(columns=['Parent_SKU', 'Total_Recut_Pieces', 'Materials_Affected'])

    cutting_recuts = add_parent_sku_column(cutting_recuts)

    return aggregate_recuts_with_materials(cutting_recuts)


# =============================================================================
# SEWING MANAGER METRICS
# =============================================================================

def calculate_sewing_manager_metrics(
    sewing_repairs: pd.DataFrame,
    recut_list: pd.DataFrame
) -> Dict[str, Any]:
    """
    Calculate metrics specific to Sewing Manager view.
    """
    total_repairs = sewing_repairs['Repair Qty'].sum() if 'Repair Qty' in sewing_repairs.columns else 0
    total_repair_time_min = sewing_repairs['Repair Time (min)'].sum() if 'Repair Time (min)' in sewing_repairs.columns else 0
    total_fails = sewing_repairs['Fail Qty'].sum() if 'Fail Qty' in sewing_repairs.columns else 0

    # Avg time per repair
    avg_time_per_repair = (total_repair_time_min / total_repairs) if total_repairs > 0 else 0

    # Detection location
    total_records = len(sewing_repairs)
    caught_at_sewing = len(sewing_repairs[sewing_repairs['Repair Discovered'] == 'SEWING'])
    caught_at_qc = len(sewing_repairs[sewing_repairs['Repair Discovered'] == 'QC'])

    pct_caught_sewing = (caught_at_sewing / total_records * 100) if total_records > 0 else 0
    pct_caught_qc = (caught_at_qc / total_records * 100) if total_records > 0 else 0

    # Sewing errors from Recut List (A codes)
    sewing_recuts = recut_list[recut_list['Department'] == 'Sewing Operator Error']
    total_recuts_sewing = sewing_recuts['QTY'].sum() if len(sewing_recuts) > 0 else 0

    # Sewing-specific incidents
    sewing_errors = sewing_repairs[sewing_repairs['Department'] == 'Sewing Operator Error']
    sewing_error_incidents = len(sewing_errors)

    return {
        'total_repairs': int(total_repairs),
        'total_repair_time_min': int(total_repair_time_min),
        'total_repair_time_hrs': round(total_repair_time_min / 60, 1),
        'avg_time_per_repair': round(avg_time_per_repair, 1),
        'total_fails': int(total_fails),
        'caught_at_sewing': int(caught_at_sewing),
        'caught_at_qc': int(caught_at_qc),
        'pct_caught_sewing': round(pct_caught_sewing, 1),
        'pct_caught_qc': round(pct_caught_qc, 1),
        'total_recuts_sewing_errors': int(total_recuts_sewing),
        'sewing_error_incidents': int(sewing_error_incidents),
    }


def get_smo_performance(sewing_repairs: pd.DataFrame) -> pd.DataFrame:
    """
    Get SMO performance summary with Parent SKU count.
    """
    if 'SMO/PA' not in sewing_repairs.columns:
        return pd.DataFrame(columns=['SMO', 'Repair_Qty', 'Total_Repair_Time_Min', 'Avg_Time_Per_Repair', 'Fail_Qty', 'Parent_SKUs_Repaired'])

    # Add Parent SKU column if not present
    df = add_parent_sku_column(sewing_repairs, 'SKU-Colorway-Size')

    result = df.groupby('SMO/PA').agg({
        'Repair Qty': 'sum',
        'Repair Time (min)': 'sum',
        'Fail Qty': 'sum',
        'Parent_SKU': 'nunique',  # Count distinct Parent SKUs
    }).reset_index()

    result.columns = ['SMO', 'Repair_Qty', 'Total_Repair_Time_Min', 'Fail_Qty', 'Parent_SKUs_Repaired']
    result['Avg_Time_Per_Repair'] = (result['Total_Repair_Time_Min'] / result['Repair_Qty']).round(1)
    result['Avg_Time_Per_Repair'] = result['Avg_Time_Per_Repair'].fillna(0)

    # Reorder columns
    result = result[['SMO', 'Repair_Qty', 'Total_Repair_Time_Min', 'Avg_Time_Per_Repair', 'Fail_Qty', 'Parent_SKUs_Repaired']]

    # Remove None/NaN SMOs
    result = result[result['SMO'].notna()]

    return result.sort_values('Repair_Qty', ascending=False)


def get_repairs_by_parent_sku(sewing_repairs: pd.DataFrame) -> pd.DataFrame:
    """
    Get repairs aggregated by Parent SKU.
    """
    df = add_parent_sku_column(sewing_repairs, 'SKU-Colorway-Size')

    result = df.groupby('Parent_SKU').agg({
        'Repair Qty': 'sum',
        'Repair Time (min)': 'sum',
        'Fail Qty': 'sum',
        'Recut Qty': 'sum',
    }).reset_index()

    result.columns = ['Parent_SKU', 'Repair_Qty', 'Total_Repair_Time_Min', 'Fail_Qty', 'Recut_Qty']
    result['Avg_Time_Per_Repair'] = (result['Total_Repair_Time_Min'] / result['Repair_Qty']).round(1)
    result['Avg_Time_Per_Repair'] = result['Avg_Time_Per_Repair'].fillna(0)

    # Remove None/NaN SKUs
    result = result[result['Parent_SKU'].notna()]

    return result.sort_values('Repair_Qty', ascending=False)


# =============================================================================
# PRODUCTION MANAGER METRICS
# =============================================================================

def calculate_production_manager_metrics(
    sewing_repairs: pd.DataFrame,
    recut_list: pd.DataFrame
) -> Dict[str, Any]:
    """
    Calculate metrics specific to Production Manager view.
    Holistic view across both data sources.
    """
    totals = calculate_totals(sewing_repairs, recut_list)

    # Error Source percentages
    dept_breakdown = calculate_department_breakdown(sewing_repairs, recut_list)
    total_incidents = dept_breakdown['Incidents'].sum()

    def get_dept_pct(error_source_name):
        dept_row = dept_breakdown[dept_breakdown['Error_Source'] == error_source_name]
        return dept_row['Pct_of_Total'].values[0] if len(dept_row) > 0 else 0

    # Combine machine error percentages
    pct_cutting_machine = get_dept_pct('Cutting Machine Error')
    pct_sewing_machine = get_dept_pct('Sewing Machine Error')
    pct_other_machine = get_dept_pct('Other Machine Error')
    pct_total_machine = pct_cutting_machine + pct_sewing_machine + pct_other_machine

    return {
        **totals,
        'pct_cutting_operator_errors': round(get_dept_pct('Cutting Operator Error'), 1),
        'pct_sewing_operator_errors': round(get_dept_pct('Sewing Operator Error'), 1),
        'pct_cutting_machine_errors': round(pct_cutting_machine, 1),
        'pct_sewing_machine_errors': round(pct_sewing_machine, 1),
        'pct_other_machine_errors': round(pct_other_machine, 1),
        'pct_total_machine_errors': round(pct_total_machine, 1),
        'pct_material_defects': round(get_dept_pct('Material Defect'), 1),
    }


def get_top_problem_skus_repairs(sewing_repairs: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    """
    Get top problem SKUs by repair quantity.
    """
    df = get_repairs_by_parent_sku(sewing_repairs)
    df['Total_Rework'] = df['Repair_Qty'] + df['Recut_Qty'] + df['Fail_Qty']
    return df.head(n)


def get_top_problem_skus_recuts(recut_list: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    """
    Get top problem SKUs by recut pieces.
    """
    df = add_parent_sku_column(recut_list)

    # Aggregate with error type info
    result = df.groupby('Parent_SKU').agg({
        'QTY': 'sum',
        'CODE': lambda x: ', '.join(x.dropna().unique()[:3]),  # Top 3 error codes
    }).reset_index()

    result.columns = ['Parent_SKU', 'Recut_Pieces', 'Top_Error_Types']
    result = result[result['Parent_SKU'].notna()]

    return result.sort_values('Recut_Pieces', ascending=False).head(n)


# =============================================================================
# QC MANAGER METRICS
# =============================================================================

def calculate_qc_manager_metrics(sewing_repairs: pd.DataFrame) -> Dict[str, Any]:
    """
    Calculate metrics specific to QC Manager view.
    Focuses on detection location (Sewing vs QC).
    """
    total_records = len(sewing_repairs)
    caught_at_sewing = len(sewing_repairs[sewing_repairs['Repair Discovered'] == 'SEWING'])
    caught_at_qc = len(sewing_repairs[sewing_repairs['Repair Discovered'] == 'QC'])

    pct_caught_sewing = (caught_at_sewing / total_records * 100) if total_records > 0 else 0
    pct_caught_qc = (caught_at_qc / total_records * 100) if total_records > 0 else 0

    # Repairs/Fails from QC-caught issues
    qc_caught = sewing_repairs[sewing_repairs['Repair Discovered'] == 'QC']
    repairs_from_qc = qc_caught['Repair Qty'].sum() if 'Repair Qty' in qc_caught.columns else 0
    fails_from_qc = qc_caught['Fail Qty'].sum() if 'Fail Qty' in qc_caught.columns else 0

    return {
        'total_issues': int(total_records),
        'caught_at_sewing': int(caught_at_sewing),
        'caught_at_qc': int(caught_at_qc),
        'pct_caught_sewing': round(pct_caught_sewing, 1),
        'pct_caught_qc': round(pct_caught_qc, 1),
        'repairs_from_qc_caught': int(repairs_from_qc),
        'fails_from_qc_caught': int(fails_from_qc),
    }


def get_detection_by_sku(sewing_repairs: pd.DataFrame) -> pd.DataFrame:
    """
    Get detection location breakdown by Parent SKU.
    """
    df = add_parent_sku_column(sewing_repairs, 'SKU-Colorway-Size')

    # Count by SKU and detection location
    result = df.groupby('Parent_SKU').agg({
        'Repair Discovered': [
            'count',
            lambda x: (x == 'SEWING').sum(),
            lambda x: (x == 'QC').sum(),
        ]
    }).reset_index()

    result.columns = ['Parent_SKU', 'Total_Issues', 'Caught_at_Sewing', 'Caught_at_QC']

    # Calculate percentages
    result['Pct_at_Sewing'] = (result['Caught_at_Sewing'] / result['Total_Issues'] * 100).round(1)
    result['Pct_at_QC'] = (result['Caught_at_QC'] / result['Total_Issues'] * 100).round(1)

    result = result[result['Parent_SKU'].notna()]

    return result.sort_values('Total_Issues', ascending=False)


def get_skus_poor_inline_detection(sewing_repairs: pd.DataFrame, threshold: float = 50.0) -> pd.DataFrame:
    """
    Get SKUs where more than threshold% of issues are caught at QC.
    """
    df = get_detection_by_sku(sewing_repairs)
    return df[df['Pct_at_QC'] > threshold].sort_values('Caught_at_QC', ascending=False)


def get_error_types_by_detection(sewing_repairs: pd.DataFrame) -> pd.DataFrame:
    """
    Get error type breakdown by detection location.
    """
    if 'Reason Code' not in sewing_repairs.columns:
        return pd.DataFrame()

    result = sewing_repairs.groupby('Reason Code').agg({
        'Repair Discovered': [
            'count',
            lambda x: (x == 'SEWING').sum(),
            lambda x: (x == 'QC').sum(),
        ]
    }).reset_index()

    result.columns = ['Reason_Code', 'Total', 'Caught_at_Sewing', 'Caught_at_QC']
    result['Pct_at_QC'] = (result['Caught_at_QC'] / result['Total'] * 100).round(1)

    return result.sort_values('Total', ascending=False)


# =============================================================================
# OPERATIONS DIRECTOR METRICS
# =============================================================================

def calculate_ops_director_metrics(
    sewing_repairs: pd.DataFrame,
    recut_list: pd.DataFrame
) -> Dict[str, Any]:
    """
    Calculate metrics specific to Operations Director view.
    High-level strategic metrics with hours (not minutes).
    """
    totals = calculate_totals(sewing_repairs, recut_list)

    # Get top problem SKU
    repairs_by_sku = get_repairs_by_parent_sku(sewing_repairs)
    top_sku = repairs_by_sku['Parent_SKU'].iloc[0] if len(repairs_by_sku) > 0 else 'N/A'
    top_sku_rework = (repairs_by_sku['Repair_Qty'].iloc[0] +
                      repairs_by_sku['Recut_Qty'].iloc[0] +
                      repairs_by_sku['Fail_Qty'].iloc[0]) if len(repairs_by_sku) > 0 else 0

    # Get primary error source
    dept_breakdown = calculate_department_breakdown(sewing_repairs, recut_list)
    primary_dept = dept_breakdown['Error_Source'].iloc[0] if len(dept_breakdown) > 0 else 'N/A'
    primary_dept_pct = dept_breakdown['Pct_of_Total'].iloc[0] if len(dept_breakdown) > 0 else 0

    return {
        'total_rework_events': totals['total_rework_events'],
        'total_repair_time_hrs': totals['total_repair_time_hrs'],
        'total_recut_pieces': totals['total_recut_pieces'],
        'total_fails': totals['total_fails'],
        'top_problem_sku': top_sku,
        'top_problem_sku_rework': int(top_sku_rework),
        'primary_error_source': primary_dept,
        'primary_error_source_pct': round(primary_dept_pct, 1),
    }


def get_top_error_types(
    sewing_repairs: pd.DataFrame,
    recut_list: pd.DataFrame,
    n: int = 5
) -> pd.DataFrame:
    """
    Get top N error types (Reason Codes) by incident count.
    Combines data from both sheets.
    """
    # From Sewing Repairs
    if 'Reason Code' in sewing_repairs.columns:
        repairs_errors = sewing_repairs.groupby('Reason Code').agg({
            'Repair Qty': 'sum',
            'Fail Qty': 'sum',
        }).reset_index()
        repairs_errors['Incidents'] = sewing_repairs.groupby('Reason Code').size().values
        repairs_errors.columns = ['Error_Type', 'Repair_Qty', 'Fail_Qty', 'Incidents']
    else:
        repairs_errors = pd.DataFrame(columns=['Error_Type', 'Repair_Qty', 'Fail_Qty', 'Incidents'])

    # From Recut List
    if 'CODE' in recut_list.columns:
        recut_errors = recut_list.groupby('CODE').agg({
            'QTY': 'sum',
        }).reset_index()
        recut_errors['Incidents'] = recut_list.groupby('CODE').size().values
        recut_errors.columns = ['Error_Type', 'Recut_Pieces', 'Incidents_Recut']
    else:
        recut_errors = pd.DataFrame(columns=['Error_Type', 'Recut_Pieces', 'Incidents_Recut'])

    # Combine (keep them separate since error codes are different between sheets)
    # Just use Sewing Repairs for now as it has more structured reason codes
    result = repairs_errors.sort_values('Incidents', ascending=False).head(n)

    return result


def get_sku_investment_priority(
    sewing_repairs: pd.DataFrame,
    recut_list: pd.DataFrame,
    n: int = 15
) -> pd.DataFrame:
    """
    Get SKU investment priority list for Operations Director.
    Combines data from both sources.
    """
    # Get repairs data
    repairs_by_sku = get_repairs_by_parent_sku(sewing_repairs)
    repairs_by_sku = repairs_by_sku[['Parent_SKU', 'Repair_Qty', 'Total_Repair_Time_Min', 'Fail_Qty', 'Recut_Qty']]

    # Get recuts data
    recuts_by_sku = add_parent_sku_column(recut_list)
    recuts_agg = recuts_by_sku.groupby('Parent_SKU').agg({
        'QTY': 'sum',
        'CODE': lambda x: x.mode()[0] if len(x.mode()) > 0 else 'N/A',
    }).reset_index()
    recuts_agg.columns = ['Parent_SKU', 'Recut_Pieces', 'Primary_Error_Type']

    # Merge
    result = repairs_by_sku.merge(recuts_agg, on='Parent_SKU', how='outer').fillna(0)

    # Calculate totals
    result['Total_Rework'] = result['Repair_Qty'] + result['Recut_Pieces'] + result['Fail_Qty']
    result['Total_Repair_Time_Hrs'] = (result['Total_Repair_Time_Min'] / 60).round(1)

    # Select columns
    result = result[['Parent_SKU', 'Repair_Qty', 'Recut_Pieces', 'Fail_Qty', 'Total_Rework', 'Total_Repair_Time_Hrs', 'Primary_Error_Type']]

    # Clean up
    result = result[result['Parent_SKU'].notna()]
    result = result[result['Parent_SKU'] != 0]

    return result.sort_values('Total_Rework', ascending=False).head(n)
