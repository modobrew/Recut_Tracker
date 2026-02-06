"""
SKU utilities for Recut Tracker dashboard.
Handles Parent SKU rollup logic (same as ONE Tracker).
"""

import pandas as pd
from typing import Optional

# =============================================================================
# COLOR CODES - Only these, no others
# =============================================================================

COLOR_CODES = {
    'BK', 'CB', 'MC', 'MA', 'MB', 'MT', 'RG', 'WD', 'WG',
    'TB', 'TD', 'TJ', 'RD', 'ML', 'NG', 'NP', 'RT'
}

# SKUs that should NOT be modified (exceptions)
SKU_EXCEPTIONS = {
    'PI-CB',      # CB is part of product name, not a color
    'MI-556-TR',  # TR is not a color code
    'MI-556-SN',  # SN is not a color code
}

# Size codes (for reference, not removed in rollup)
SIZE_CODES = {'SM', 'MD', 'LG', 'XL', 'XXL', '05', '10', '15', '20', '25'}


# =============================================================================
# PARENT SKU ROLLUP
# =============================================================================

def get_parent_sku(sku: Optional[str]) -> Optional[str]:
    """
    Get the parent SKU by removing color codes.

    Rules:
    - Remove COLOR code only (from COLOR_CODES list)
    - Keep SIZE designation if present
    - Leave exceptions unchanged
    - CR is a product prefix, NOT a color code

    Examples:
        AC-ESE-BK -> AC-ESE (remove color BK)
        PC-F20-BK-LG -> PC-F20-LG (remove color BK, keep size LG)
        PI-CB -> PI-CB (exception - CB is part of product name)
        CR-AL-BK -> CR-AL (CR is prefix, remove color BK)

    Args:
        sku: The full SKU string

    Returns:
        The parent SKU with color codes removed
    """
    if pd.isna(sku) or sku is None:
        return None

    sku = str(sku).strip()
    if not sku:
        return None

    # Check exceptions - return unchanged
    if sku in SKU_EXCEPTIONS:
        return sku

    # Split by hyphen
    parts = sku.split('-')

    # Filter out color codes, keep everything else
    result_parts = [part for part in parts if part.upper() not in COLOR_CODES]

    # If nothing left after filtering (shouldn't happen), return original
    if not result_parts:
        return sku

    return '-'.join(result_parts)


def add_parent_sku_column(df: pd.DataFrame, sku_col: str = 'SKU') -> pd.DataFrame:
    """
    Add a Parent_SKU column to the DataFrame.

    Args:
        df: DataFrame containing SKU column
        sku_col: Name of the SKU column (default: 'SKU')

    Returns:
        DataFrame with Parent_SKU column added
    """
    if sku_col not in df.columns:
        # Try alternate column name for Sewing Repairs
        if 'SKU-Colorway-Size' in df.columns:
            sku_col = 'SKU-Colorway-Size'
        else:
            df['Parent_SKU'] = None
            return df

    df = df.copy()
    df['Parent_SKU'] = df[sku_col].apply(get_parent_sku)

    return df


# =============================================================================
# SKU AGGREGATION HELPERS
# =============================================================================

def aggregate_by_parent_sku(
    df: pd.DataFrame,
    value_cols: list,
    agg_funcs: dict = None
) -> pd.DataFrame:
    """
    Aggregate data by Parent SKU.

    Args:
        df: DataFrame with Parent_SKU column
        value_cols: Columns to aggregate
        agg_funcs: Dict of column -> aggregation function (default: sum)

    Returns:
        DataFrame aggregated by Parent_SKU
    """
    if 'Parent_SKU' not in df.columns:
        df = add_parent_sku_column(df)

    # Default to sum for all columns
    if agg_funcs is None:
        agg_funcs = {col: 'sum' for col in value_cols if col in df.columns}

    # Only include columns that exist
    agg_funcs = {k: v for k, v in agg_funcs.items() if k in df.columns}

    if not agg_funcs:
        return df.groupby('Parent_SKU').size().reset_index(name='Count')

    result = df.groupby('Parent_SKU').agg(agg_funcs).reset_index()

    return result


def get_top_skus_by_metric(
    df: pd.DataFrame,
    metric_col: str,
    n: int = 10,
    ascending: bool = False
) -> pd.DataFrame:
    """
    Get top N SKUs by a specific metric.

    Args:
        df: DataFrame (should be aggregated by Parent_SKU)
        metric_col: Column to sort by
        n: Number of top SKUs to return
        ascending: Sort ascending if True

    Returns:
        Top N SKUs sorted by metric
    """
    if metric_col not in df.columns:
        return df.head(n)

    return df.nlargest(n, metric_col) if not ascending else df.nsmallest(n, metric_col)


# =============================================================================
# MATERIAL TRACKING FOR RECUT LIST
# =============================================================================

def get_materials_for_sku(df: pd.DataFrame, parent_sku: str) -> list:
    """
    Get list of unique materials associated with a Parent SKU.

    Args:
        df: Recut List DataFrame with Parent_SKU and Material columns
        parent_sku: The Parent SKU to look up

    Returns:
        List of unique material codes
    """
    if 'Parent_SKU' not in df.columns or 'Material' not in df.columns:
        return []

    materials = df[df['Parent_SKU'] == parent_sku]['Material'].dropna().unique()
    return sorted(materials.tolist())


def aggregate_recuts_with_materials(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate recut data by Parent SKU with materials list.

    Args:
        df: Recut List DataFrame

    Returns:
        DataFrame with Parent_SKU, total recuts, and materials affected
    """
    if 'Parent_SKU' not in df.columns:
        df = add_parent_sku_column(df)

    # Aggregate quantities
    qty_agg = df.groupby('Parent_SKU')['QTY'].sum().reset_index()
    qty_agg.columns = ['Parent_SKU', 'Total_Recut_Pieces']

    # Get materials list per SKU
    materials_agg = df.groupby('Parent_SKU')['Material'].apply(
        lambda x: ', '.join(sorted(x.dropna().unique()))
    ).reset_index()
    materials_agg.columns = ['Parent_SKU', 'Materials_Affected']

    # Merge
    result = qty_agg.merge(materials_agg, on='Parent_SKU', how='left')

    return result.sort_values('Total_Recut_Pieces', ascending=False)
