"""
Recut Tracker Dashboard
A Streamlit app for tracking rework events (repairs, recuts, fails) across production.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

from utils.data_loader import (
    load_data,
    filter_by_date_range,
)
from utils.sku_utils import (
    add_parent_sku_column,
    get_parent_sku,
)
from utils.metrics import (
    calculate_totals,
    calculate_department_breakdown,
    calculate_cutting_manager_metrics,
    calculate_sewing_manager_metrics,
    calculate_production_manager_metrics,
    calculate_qc_manager_metrics,
    calculate_ops_director_metrics,
    get_cutting_recuts_by_material,
    get_cutting_recuts_by_parent_sku,
    get_smo_performance,
    get_repairs_by_parent_sku,
    get_top_problem_skus_repairs,
    get_top_problem_skus_recuts,
    get_detection_by_sku,
    get_skus_poor_inline_detection,
    get_error_types_by_detection,
    get_sku_investment_priority,
    get_top_error_types,
)


# =============================================================================
# PAGE CONFIG
# =============================================================================

st.set_page_config(
    page_title="Recut Tracker Dashboard",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="expanded",
)


# =============================================================================
# CUSTOM CSS
# =============================================================================

st.markdown("""
<style>
    .metric-card {
        background-color: #f0f2f6;
        border-radius: 10px;
        padding: 15px;
        text-align: center;
    }
    .metric-value {
        font-size: 2em;
        font-weight: bold;
        color: #1f77b4;
    }
    .metric-label {
        font-size: 0.9em;
        color: #666;
    }
    .insight-good {
        color: #28a745;
        padding: 5px 0;
    }
    .insight-warning {
        color: #ffc107;
        padding: 5px 0;
    }
    .insight-bad {
        color: #dc3545;
        padding: 5px 0;
    }
    .insight-info {
        color: #17a2b8;
        padding: 5px 0;
    }
</style>
""", unsafe_allow_html=True)


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def display_metric_card(label: str, value, delta: str = None, delta_color: str = "normal"):
    """Display a metric with optional delta."""
    st.metric(label=label, value=value, delta=delta, delta_color=delta_color)


def display_insight(text: str, level: str = "info"):
    """Display an insight bullet with appropriate styling."""
    icons = {
        "good": "✅",
        "warning": "⚠️",
        "bad": "🔴",
        "info": "📊",
    }
    icon = icons.get(level, "•")
    st.markdown(f"{icon} {text}")


def create_pie_chart(df: pd.DataFrame, names_col: str, values_col: str, title: str):
    """Create a pie chart."""
    fig = px.pie(
        df,
        names=names_col,
        values=values_col,
        title=title,
        hole=0.3,
    )
    fig.update_traces(
        textposition='outside',
        textinfo='percent+label',
        textfont_size=16,
        pull=[0.02] * len(df),  # Slight separation between slices
    )
    fig.update_layout(
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5, font=dict(size=14)),
        height=550,
        margin=dict(t=60, b=100, l=40, r=40),
        title_font_size=18,
    )
    return fig


def create_bar_chart(df: pd.DataFrame, x_col: str, y_col: str, title: str, orientation: str = 'v'):
    """Create a bar chart."""
    if orientation == 'h':
        fig = px.bar(df, x=y_col, y=x_col, orientation='h', title=title)
    else:
        fig = px.bar(df, x=x_col, y=y_col, title=title)
    fig.update_layout(height=350)
    return fig


def create_line_chart(df: pd.DataFrame, x_col: str, y_col: str, title: str):
    """Create a line chart."""
    fig = px.line(df, x=x_col, y=y_col, title=title, markers=True)
    fig.update_layout(height=350)
    return fig


def create_trend_data(df: pd.DataFrame, date_col: str, value_col: str, freq: str = 'W'):
    """Aggregate data by time period for trend charts."""
    if date_col not in df.columns:
        return pd.DataFrame()

    df = df.copy()
    df[date_col] = pd.to_datetime(df[date_col])

    # Group by period
    df['Period'] = df[date_col].dt.to_period(freq)
    trend = df.groupby('Period')[value_col].sum().reset_index()
    trend['Period'] = trend['Period'].astype(str)

    return trend


# =============================================================================
# SIDEBAR
# =============================================================================

st.sidebar.title("🔧 Recut Tracker")
st.sidebar.markdown("---")

# File upload
uploaded_file = st.sidebar.file_uploader(
    "Upload Rework Tracker Excel file",
    type=['xlsx', 'xlsm'],
    help="Upload the Rework_Tracker file containing 2025 Sewing Repairs and Recut List sheets"
)

if uploaded_file is None:
    st.title("🔧 Recut Tracker Dashboard")
    st.info("👈 Please upload a Rework Tracker Excel file to get started.")
    st.markdown("""
    ### About This Dashboard

    This dashboard analyzes rework data (repairs, recuts, fails) to help identify problem areas
    and improve production quality.

    **Supported Roles:**
    - **Cutting Manager** - Cutting errors, recuts by material/SKU
    - **Sewing Manager** - Repairs, SMO performance, detection location
    - **Production Manager** - Holistic view, department breakdown
    - **QC Manager** - Detection effectiveness (Sewing vs QC)
    - **Operations Director** - Strategic view, trends, investment priorities

    **Required File Structure:**
    - Sheet: "2025 Sewing Repairs" - Order-level repair tracking
    - Sheet: "Recut List" - Individual recut piece tracking
    """)
    st.stop()


# =============================================================================
# LOAD DATA
# =============================================================================

@st.cache_data
def load_cached_data(file):
    """Load and cache the data."""
    return load_data(file)


try:
    sewing_repairs, recut_list = load_cached_data(uploaded_file)
except Exception as e:
    st.error(f"Error loading file: {str(e)}")
    st.stop()


# =============================================================================
# SIDEBAR FILTERS
# =============================================================================

st.sidebar.markdown("---")
st.sidebar.subheader("Filters")

# Role selector
role = st.sidebar.selectbox(
    "Select Role",
    options=[
        "Production Manager",
        "Cutting Manager",
        "Sewing Manager",
        "QC Manager",
        "Operations Director",
    ],
    index=0,
)

# Date range filter
st.sidebar.markdown("**Date Range**")

# Get date range from data
min_date_repairs = sewing_repairs['Date'].min() if 'Date' in sewing_repairs.columns else datetime(2025, 1, 1)
max_date_repairs = sewing_repairs['Date'].max() if 'Date' in sewing_repairs.columns else datetime.now()
min_date_recuts = recut_list['Date'].min() if 'Date' in recut_list.columns else datetime(2025, 1, 1)
max_date_recuts = recut_list['Date'].max() if 'Date' in recut_list.columns else datetime.now()

min_date = min(min_date_repairs, min_date_recuts)
max_date = max(max_date_repairs, max_date_recuts)

# Default to current month
default_start = max_date.replace(day=1) if pd.notna(max_date) else datetime.now().replace(day=1)
default_end = max_date if pd.notna(max_date) else datetime.now()

# Month presets
preset = st.sidebar.selectbox(
    "Quick Select",
    options=["Custom", "Current Month", "Last 30 Days", "Last 90 Days", "Year to Date", "All Time"],
    index=0,
)

if preset == "Current Month":
    start_date = datetime.now().replace(day=1)
    end_date = datetime.now()
elif preset == "Last 30 Days":
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
elif preset == "Last 90 Days":
    end_date = datetime.now()
    start_date = end_date - timedelta(days=90)
elif preset == "Year to Date":
    start_date = datetime(datetime.now().year, 1, 1)
    end_date = datetime.now()
elif preset == "All Time":
    start_date = min_date
    end_date = max_date
else:
    col1, col2 = st.sidebar.columns(2)
    with col1:
        start_date = st.date_input("Start", value=default_start, min_value=min_date, max_value=max_date)
    with col2:
        end_date = st.date_input("End", value=default_end, min_value=min_date, max_value=max_date)

# Convert to datetime
start_date = pd.to_datetime(start_date)
end_date = pd.to_datetime(end_date)

# Filter data by date range
filtered_repairs = filter_by_date_range(sewing_repairs, start_date, end_date)
filtered_recuts = filter_by_date_range(recut_list, start_date, end_date)

# Show data counts
st.sidebar.markdown("---")
st.sidebar.markdown(f"**Data Loaded:**")
st.sidebar.markdown(f"- Repairs: {len(filtered_repairs):,} records")
st.sidebar.markdown(f"- Recuts: {len(filtered_recuts):,} records")
st.sidebar.markdown(f"- Date Range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")


# =============================================================================
# MAIN CONTENT - ROLE VIEWS
# =============================================================================

st.title(f"🔧 Recut Tracker - {role}")
st.markdown(f"*Analyzing data from {start_date.strftime('%b %d, %Y')} to {end_date.strftime('%b %d, %Y')}*")
st.markdown("---")


# =============================================================================
# CUTTING MANAGER VIEW
# =============================================================================

if role == "Cutting Manager":
    # Get metrics
    metrics = calculate_cutting_manager_metrics(filtered_repairs, filtered_recuts)

    # Summary Cards - Row 1: Recut List metrics
    st.subheader("Summary Metrics")
    st.markdown("**From Recut List (individual pieces):**")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        display_metric_card("Total Recut Pieces", f"{metrics['total_recut_pieces']:,}")
    with col2:
        display_metric_card("Cutting Errors (B)", f"{metrics['cutting_errors']:,}")
    with col3:
        display_metric_card("Marking Errors (C)", f"{metrics['marking_errors']:,}")
    with col4:
        display_metric_card("Cut Too Short (F)", f"{metrics['cut_short_errors']:,}")

    # Summary Cards - Row 2: Sewing Repairs metrics
    st.markdown("**From Sewing Repairs (order-level incidents with A1x codes):**")
    col5, col6, col7, col8 = st.columns(4)
    with col5:
        display_metric_card("Cutting Incidents", f"{metrics['total_cutting_incidents']:,}")
    with col6:
        display_metric_card("Recut Qty", f"{metrics['recut_qty_from_repairs']:,}")
    with col7:
        display_metric_card("Fail Qty", f"{metrics['fail_qty_from_cutting']:,}")
    with col8:
        display_metric_card("Kitting Errors (A1C)", f"{metrics['kitting_errors']:,}")

    st.markdown("---")

    # Key Insights
    st.subheader("Key Insights")
    display_insight(f"{metrics['total_recut_pieces']:,} recut pieces this period from cutting-related errors.", "info")

    if metrics['marking_errors'] > metrics['cutting_errors']:
        display_insight("Marking errors exceed cutting errors - review marking process.", "warning")

    if metrics['kitting_errors'] > 0:
        display_insight(f"{metrics['kitting_errors']} kitting errors recorded - verify kitting procedures.", "warning")

    if metrics['cut_short_errors'] > metrics['cutting_errors']:
        display_insight(f"Cut-too-short errors ({metrics['cut_short_errors']}) are significant - check cutting calibration.", "warning")

    st.markdown("---")

    # Charts
    st.subheader("Visualizations")
    col1, col2 = st.columns(2)

    with col1:
        # Error Type Breakdown
        error_data = pd.DataFrame({
            'Error Type': ['Cutting Errors', 'Marking Errors', 'Kitting Errors', 'Cut Too Short'],
            'Count': [metrics['cutting_errors'], metrics['marking_errors'], metrics['kitting_errors'], metrics['cut_short_errors']]
        })
        error_data = error_data[error_data['Count'] > 0]
        if len(error_data) > 0:
            fig = create_pie_chart(error_data, 'Error Type', 'Count', 'Error Type Breakdown')
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        # Recuts over time
        cutting_recuts = filtered_recuts[filtered_recuts['Department'] == 'Cutting Operator Error']
        if len(cutting_recuts) > 0:
            trend = create_trend_data(cutting_recuts, 'Date', 'QTY', 'W')
            if len(trend) > 0:
                fig = create_line_chart(trend, 'Period', 'QTY', 'Recut Pieces Over Time (Weekly)')
                st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # Tables
    st.subheader("Tables")

    tab1, tab2, tab3, tab4 = st.tabs(["Recuts by Material", "Recuts by Parent SKU", "Recut List Detail", "Sewing Repairs Detail"])

    with tab1:
        st.markdown("*From Recut List - B/C/F codes*")
        material_data = get_cutting_recuts_by_material(filtered_recuts)
        if len(material_data) > 0:
            st.dataframe(material_data.head(20), use_container_width=True, hide_index=True)
        else:
            st.info("No cutting-related recuts in selected period.")

    with tab2:
        st.markdown("*From Recut List - B/C/F codes*")
        sku_data = get_cutting_recuts_by_parent_sku(filtered_recuts)
        if len(sku_data) > 0:
            st.dataframe(sku_data.head(20), use_container_width=True, hide_index=True)
        else:
            st.info("No cutting-related recuts in selected period.")

    with tab3:
        st.markdown("*Individual recut pieces from Recut List (B/C/F codes)*")
        cutting_recuts_detail = filtered_recuts[filtered_recuts['Department'] == 'Cutting Operator Error']
        if len(cutting_recuts_detail) > 0:
            detail_cols = ['Date', 'Document_No', 'SKU', 'Material', 'Cut/Length', 'QTY', 'CODE', 'PA']
            detail_cols = [c for c in detail_cols if c in cutting_recuts_detail.columns]
            st.dataframe(cutting_recuts_detail[detail_cols].sort_values('Date', ascending=False).head(50), use_container_width=True, hide_index=True)
        else:
            st.info("No cutting-related recuts in selected period.")

    with tab4:
        st.markdown("*Order-level incidents from Sewing Repairs (A1x codes)*")
        cutting_repairs = filtered_repairs[filtered_repairs['Department'] == 'Cutting Operator Error']
        if len(cutting_repairs) > 0:
            detail_cols = ['Date', 'PR#', 'SKU-Colorway-Size', 'Recut Qty', 'Fail Qty', 'Reason Code', 'CMO', 'Reason for Recut']
            detail_cols = [c for c in detail_cols if c in cutting_repairs.columns]
            st.dataframe(cutting_repairs[detail_cols].sort_values('Date', ascending=False).head(50), use_container_width=True, hide_index=True)
        else:
            st.info("No cutting incidents (A1x codes) in Sewing Repairs for selected period.")


# =============================================================================
# SEWING MANAGER VIEW
# =============================================================================

elif role == "Sewing Manager":
    # Get metrics
    metrics = calculate_sewing_manager_metrics(filtered_repairs, filtered_recuts)

    # Summary Cards - Row 1
    st.subheader("Summary Metrics")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        display_metric_card("Total Repairs", f"{metrics['total_repairs']:,}")
    with col2:
        display_metric_card("Total Repair Time (hrs)", f"{metrics['total_repair_time_hrs']:,}")
    with col3:
        display_metric_card("Avg Time/Repair (min)", f"{metrics['avg_time_per_repair']:.1f}")
    with col4:
        display_metric_card("Total Fails", f"{metrics['total_fails']:,}")

    # Summary Cards - Row 2
    col5, col6, col7, col8 = st.columns(4)
    with col5:
        display_metric_card("% Caught at Sewing", f"{metrics['pct_caught_sewing']:.1f}%")
    with col6:
        display_metric_card("% Caught at QC", f"{metrics['pct_caught_qc']:.1f}%")
    with col7:
        display_metric_card("Recuts (Sewing Errors)", f"{metrics['total_recuts_sewing_errors']:,}")
    with col8:
        display_metric_card("Sewing Error Incidents", f"{metrics['sewing_error_incidents']:,}")

    st.markdown("---")

    # Key Insights
    st.subheader("Key Insights")
    total_hrs = metrics['total_repair_time_hrs']
    display_insight(f"{metrics['total_repairs']:,} total repairs consuming {total_hrs:,.1f} hours ({total_hrs/8:.1f} FTE days) of repair time.", "info")

    if metrics['pct_caught_qc'] > metrics['pct_caught_sewing']:
        display_insight(f"More issues caught at QC ({metrics['pct_caught_qc']:.1f}%) than Sewing ({metrics['pct_caught_sewing']:.1f}%) - improve inline detection.", "warning")
    elif metrics['pct_caught_sewing'] >= 70:
        display_insight(f"Good inline detection - {metrics['pct_caught_sewing']:.1f}% of issues caught at Sewing before QC.", "good")
    else:
        display_insight(f"{metrics['pct_caught_sewing']:.1f}% caught at Sewing - room for improvement (target: 70%).", "warning")

    if metrics['avg_time_per_repair'] > 10:
        display_insight(f"Average repair time is {metrics['avg_time_per_repair']:.1f} min - investigate high-effort repairs.", "warning")

    st.markdown("---")

    # Charts
    st.subheader("Visualizations")
    col1, col2 = st.columns(2)

    with col1:
        # Detection Location Pie
        detection_data = pd.DataFrame({
            'Location': ['Caught at Sewing', 'Caught at QC'],
            'Count': [metrics['caught_at_sewing'], metrics['caught_at_qc']]
        })
        fig = create_pie_chart(detection_data, 'Location', 'Count', 'Detection Location')
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # Repairs over time
        if len(filtered_repairs) > 0:
            trend = create_trend_data(filtered_repairs, 'Date', 'Repair Qty', 'W')
            if len(trend) > 0:
                fig = create_line_chart(trend, 'Period', 'Repair Qty', 'Repairs Over Time (Weekly)')
                st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # Tables
    st.subheader("Tables")

    tab1, tab2, tab3, tab4 = st.tabs(["Top SKUs by Repairs", "Top SKUs by Time", "SMO Performance", "Recuts (Sewing Errors)"])

    with tab1:
        repairs_by_sku = get_repairs_by_parent_sku(filtered_repairs)
        if len(repairs_by_sku) > 0:
            st.dataframe(repairs_by_sku.head(15), use_container_width=True, hide_index=True)

    with tab2:
        repairs_by_sku = get_repairs_by_parent_sku(filtered_repairs)
        if len(repairs_by_sku) > 0:
            by_time = repairs_by_sku.sort_values('Total_Repair_Time_Min', ascending=False)
            st.dataframe(by_time.head(15), use_container_width=True, hide_index=True)

    with tab3:
        smo_data = get_smo_performance(filtered_repairs)
        if len(smo_data) > 0:
            st.dataframe(smo_data.head(20), use_container_width=True, hide_index=True)
        else:
            st.info("No SMO data available.")

    with tab4:
        sewing_recuts = filtered_recuts[filtered_recuts['Department'] == 'Sewing Operator Error']
        if len(sewing_recuts) > 0:
            sewing_recuts = add_parent_sku_column(sewing_recuts)
            recut_agg = sewing_recuts.groupby('Parent_SKU').agg({
                'QTY': 'sum',
                'Material': lambda x: ', '.join(x.dropna().unique()[:3])
            }).reset_index()
            recut_agg.columns = ['Parent_SKU', 'Recut_Pieces', 'Materials']
            recut_agg = recut_agg.sort_values('Recut_Pieces', ascending=False)
            st.dataframe(recut_agg.head(20), use_container_width=True, hide_index=True)
        else:
            st.info("No sewing-related recuts in selected period.")


# =============================================================================
# PRODUCTION MANAGER VIEW
# =============================================================================

elif role == "Production Manager":
    # Get metrics
    metrics = calculate_production_manager_metrics(filtered_repairs, filtered_recuts)

    # Summary Cards - Row 1
    st.subheader("Summary Metrics")
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        display_metric_card("Total Rework Events", f"{metrics['total_rework_events']:,}")
    with col2:
        display_metric_card("Total Repairs", f"{metrics['total_repairs']:,}")
    with col3:
        display_metric_card("Total Repair Time (hrs)", f"{metrics['total_repair_time_hrs']:,}")
    with col4:
        display_metric_card("Total Recut Pieces", f"{metrics['total_recut_pieces']:,}")
    with col5:
        display_metric_card("Total Fails", f"{metrics['total_fails']:,}")

    # Summary Cards - Row 2: Error Source Breakdown
    st.markdown("**Error Source Breakdown:**")
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        display_metric_card("% Cutting Operator", f"{metrics['pct_cutting_operator_errors']:.1f}%")
    with col2:
        display_metric_card("% Sewing Operator", f"{metrics['pct_sewing_operator_errors']:.1f}%")
    with col3:
        display_metric_card("% Cutting Machine", f"{metrics['pct_cutting_machine_errors']:.1f}%")
    with col4:
        display_metric_card("% Sewing Machine", f"{metrics['pct_sewing_machine_errors']:.1f}%")
    with col5:
        display_metric_card("% Material Defect", f"{metrics['pct_material_defects']:.1f}%")

    st.markdown("---")

    # Key Insights
    st.subheader("Key Insights")
    display_insight(f"{metrics['total_rework_events']:,} total rework events consuming {metrics['total_repair_time_hrs']:,.1f} hours of repair time this period.", "info")

    # Find primary error source
    error_sources = [
        ('Cutting Operator', metrics['pct_cutting_operator_errors']),
        ('Sewing Operator', metrics['pct_sewing_operator_errors']),
        ('Cutting Machine', metrics['pct_cutting_machine_errors']),
        ('Sewing Machine', metrics['pct_sewing_machine_errors']),
        ('Material Defect', metrics['pct_material_defects']),
    ]
    primary = max(error_sources, key=lambda x: x[1])
    if primary[1] > 40:
        display_insight(f"{primary[1]:.1f}% of issues originate from {primary[0]} errors.", "warning")

    if metrics['total_fails'] > 0:
        display_insight(f"{metrics['total_fails']:,} units failed/scrapped this period - monitor material loss.", "warning")

    st.markdown("---")

    # Charts
    st.subheader("Visualizations")
    col1, col2 = st.columns(2)

    with col1:
        # Error Source breakdown
        dept_data = calculate_department_breakdown(filtered_repairs, filtered_recuts)
        if len(dept_data) > 0:
            fig = create_pie_chart(dept_data, 'Error_Source', 'Incidents', 'Rework by Error Source')
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        # Rework over time
        if len(filtered_repairs) > 0:
            trend = create_trend_data(filtered_repairs, 'Date', 'Repair Qty', 'W')
            if len(trend) > 0:
                fig = create_line_chart(trend, 'Period', 'Repair Qty', 'Repairs Over Time (Weekly)')
                st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # Tables
    st.subheader("Tables")

    tab1, tab2, tab3, tab4 = st.tabs(["Top SKUs (Repairs)", "Top SKUs (Recuts)", "By Error Source", "Recent Incidents"])

    with tab1:
        top_repairs = get_top_problem_skus_repairs(filtered_repairs, 15)
        if len(top_repairs) > 0:
            st.dataframe(top_repairs, use_container_width=True, hide_index=True)

    with tab2:
        top_recuts = get_top_problem_skus_recuts(filtered_recuts, 15)
        if len(top_recuts) > 0:
            st.dataframe(top_recuts, use_container_width=True, hide_index=True)

    with tab3:
        dept_data = calculate_department_breakdown(filtered_repairs, filtered_recuts)
        if len(dept_data) > 0:
            # Rename for display
            dept_display = dept_data.rename(columns={'Total_Repair_Time_Min': 'Total_Repair_Time_Min'})
            st.dataframe(dept_display, use_container_width=True, hide_index=True)

    with tab4:
        if len(filtered_repairs) > 0:
            detail_cols = ['Date', 'PR#', 'SKU-Colorway-Size', 'Repair Qty', 'Recut Qty', 'Fail Qty', 'Reason Code', 'Repair Time (min)']
            detail_cols = [c for c in detail_cols if c in filtered_repairs.columns]
            recent = filtered_repairs[detail_cols].sort_values('Date', ascending=False).head(50)
            # Rename column for display
            recent = recent.rename(columns={'Repair Time (min)': 'Total_Repair_Time_Min'})
            st.dataframe(recent, use_container_width=True, hide_index=True)


# =============================================================================
# QC MANAGER VIEW
# =============================================================================

elif role == "QC Manager":
    # Get metrics
    metrics = calculate_qc_manager_metrics(filtered_repairs)

    # Summary Cards - Row 1
    st.subheader("Summary Metrics")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        display_metric_card("Total Issues", f"{metrics['total_issues']:,}")
    with col2:
        display_metric_card("Caught at Sewing", f"{metrics['caught_at_sewing']:,}")
    with col3:
        display_metric_card("Caught at QC", f"{metrics['caught_at_qc']:,}")
    with col4:
        display_metric_card("% Caught at Sewing", f"{metrics['pct_caught_sewing']:.1f}%")

    # Summary Cards - Row 2
    col5, col6, col7, col8 = st.columns(4)
    with col5:
        display_metric_card("% Caught at QC", f"{metrics['pct_caught_qc']:.1f}%")
    with col6:
        display_metric_card("Repairs (QC-Caught)", f"{metrics['repairs_from_qc_caught']:,}")
    with col7:
        display_metric_card("Fails (QC-Caught)", f"{metrics['fails_from_qc_caught']:,}")
    with col8:
        st.metric(label="Target: % at Sewing", value="≥70%")

    st.markdown("---")

    # Key Insights
    st.subheader("Key Insights")

    if metrics['pct_caught_sewing'] >= 70:
        display_insight(f"Strong inline detection - {metrics['pct_caught_sewing']:.1f}% of issues caught at Sewing before reaching QC.", "good")
    elif metrics['pct_caught_qc'] > 50:
        display_insight(f"More than half of issues caught at QC ({metrics['pct_caught_qc']:.1f}%) - inline detection needs improvement.", "bad")
    else:
        display_insight(f"{metrics['pct_caught_qc']:.1f}% of issues caught at QC - room for improvement in inline detection.", "warning")

    display_insight(f"{metrics['pct_caught_sewing']:.1f}% caught at Sewing - goal is to increase early detection.", "info")

    st.markdown("---")

    # Charts
    st.subheader("Visualizations")
    col1, col2 = st.columns(2)

    with col1:
        # Detection split pie
        detection_data = pd.DataFrame({
            'Location': ['Caught at Sewing', 'Caught at QC'],
            'Count': [metrics['caught_at_sewing'], metrics['caught_at_qc']]
        })
        fig = create_pie_chart(detection_data, 'Location', 'Count', 'Detection Location Split')
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # Detection over time (stacked or grouped bar)
        if len(filtered_repairs) > 0 and 'Repair Discovered' in filtered_repairs.columns:
            filtered_repairs['Period'] = pd.to_datetime(filtered_repairs['Date']).dt.to_period('W').astype(str)
            detection_trend = filtered_repairs.groupby(['Period', 'Repair Discovered']).size().reset_index(name='Count')
            if len(detection_trend) > 0:
                fig = px.bar(detection_trend, x='Period', y='Count', color='Repair Discovered',
                            title='Detection Location Over Time (Weekly)', barmode='stack')
                fig.update_layout(height=350)
                st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # Tables
    st.subheader("Tables")

    tab1, tab2, tab3, tab4 = st.tabs(["Poor Inline Detection", "Error Types by Location", "Detection by SKU", "QC-Caught Detail"])

    with tab1:
        poor_detection = get_skus_poor_inline_detection(filtered_repairs, 50.0)
        if len(poor_detection) > 0:
            st.markdown("*SKUs where >50% of issues caught at QC (should be caught earlier)*")
            st.dataframe(poor_detection.head(20), use_container_width=True, hide_index=True)
        else:
            st.success("No SKUs with poor inline detection (>50% caught at QC).")

    with tab2:
        error_types = get_error_types_by_detection(filtered_repairs)
        if len(error_types) > 0:
            st.dataframe(error_types.head(20), use_container_width=True, hide_index=True)

    with tab3:
        detection_by_sku = get_detection_by_sku(filtered_repairs)
        if len(detection_by_sku) > 0:
            st.dataframe(detection_by_sku.head(20), use_container_width=True, hide_index=True)

    with tab4:
        qc_caught = filtered_repairs[filtered_repairs['Repair Discovered'] == 'QC']
        if len(qc_caught) > 0:
            detail_cols = ['Date', 'PR#', 'SKU-Colorway-Size', 'Repair Qty', 'Fail Qty', 'Reason Code', 'Reason for Repair']
            detail_cols = [c for c in detail_cols if c in qc_caught.columns]
            st.dataframe(qc_caught[detail_cols].sort_values('Date', ascending=False).head(50), use_container_width=True, hide_index=True)
        else:
            st.info("No QC-caught issues in selected period.")


# =============================================================================
# OPERATIONS DIRECTOR VIEW
# =============================================================================

elif role == "Operations Director":
    # Get metrics
    metrics = calculate_ops_director_metrics(filtered_repairs, filtered_recuts)

    # Summary Cards - Row 1
    st.subheader("Summary Metrics")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        display_metric_card("Total Rework Events", f"{metrics['total_rework_events']:,}")
    with col2:
        display_metric_card("Total Repair Time (hrs)", f"{metrics['total_repair_time_hrs']:,}")
    with col3:
        display_metric_card("Recut Pieces", f"{metrics['total_recut_pieces']:,}")
    with col4:
        display_metric_card("Total Fails", f"{metrics['total_fails']:,}")

    # Summary Cards - Row 2
    col5, col6, col7, col8 = st.columns(4)
    with col5:
        display_metric_card("Top Problem SKU", f"{metrics['top_problem_sku']}")
    with col6:
        display_metric_card("Top SKU Rework Count", f"{metrics['top_problem_sku_rework']:,}")
    with col7:
        display_metric_card("Primary Error Source", f"{metrics['primary_error_source']}")
    with col8:
        display_metric_card("Primary Source %", f"{metrics['primary_error_source_pct']:.1f}%")

    st.markdown("---")

    # Key Insights
    st.subheader("Key Insights")

    hrs = metrics['total_repair_time_hrs']
    fte_days = hrs / 8
    display_insight(f"{metrics['total_rework_events']:,} total rework events consuming {hrs:,.1f} hours (~{fte_days:.1f} FTE days) of labor this period.", "info")

    display_insight(f"Primary error source: {metrics['primary_error_source']} ({metrics['primary_error_source_pct']:.1f}% of issues) - coordinate with {metrics['primary_error_source']} Manager.", "info")

    display_insight(f"Top investment priority: SKU {metrics['top_problem_sku']} with {metrics['top_problem_sku_rework']} rework events.", "warning")

    if metrics['total_fails'] > 0:
        display_insight(f"{metrics['total_fails']:,} units failed/scrapped - material loss to monitor.", "warning")

    # Top 5 Error Types callout
    st.markdown("**Top 5 Error Types:**")
    top_errors = get_top_error_types(filtered_repairs, filtered_recuts, 5)
    if len(top_errors) > 0:
        for _, row in top_errors.iterrows():
            error_type = row['Error_Type']
            incidents = row['Incidents']
            # Truncate long error type names
            if len(str(error_type)) > 50:
                error_type = str(error_type)[:47] + "..."
            st.markdown(f"- {error_type}: {incidents:,} incidents")
    else:
        st.markdown("- No error data available")

    st.markdown("---")

    # Charts
    st.subheader("Visualizations")
    col1, col2 = st.columns(2)

    with col1:
        # Error Source breakdown
        dept_data = calculate_department_breakdown(filtered_repairs, filtered_recuts)
        if len(dept_data) > 0:
            fig = create_pie_chart(dept_data, 'Error_Source', 'Incidents', 'Rework by Error Source')
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        # Monthly trend (if enough data)
        if len(filtered_repairs) > 0:
            trend = create_trend_data(filtered_repairs, 'Date', 'Repair Qty', 'M')
            if len(trend) > 1:
                fig = create_line_chart(trend, 'Period', 'Repair Qty', 'Monthly Rework Trend')
                st.plotly_chart(fig, use_container_width=True)
            else:
                trend = create_trend_data(filtered_repairs, 'Date', 'Repair Qty', 'W')
                if len(trend) > 0:
                    fig = create_line_chart(trend, 'Period', 'Repair Qty', 'Weekly Rework Trend')
                    st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # Tables
    st.subheader("Tables")

    tab1, tab2 = st.tabs(["SKU Investment Priority", "Error Source Summary"])

    with tab1:
        st.markdown("*SKUs ranked by total rework - prioritize for training, work instructions, or R&D review*")
        investment = get_sku_investment_priority(filtered_repairs, filtered_recuts, 15)
        if len(investment) > 0:
            st.dataframe(investment, use_container_width=True, hide_index=True)

    with tab2:
        dept_data = calculate_department_breakdown(filtered_repairs, filtered_recuts)
        if len(dept_data) > 0:
            # Add Repair Time in hours
            if 'Total_Repair_Time_Min' in dept_data.columns:
                dept_data['Total_Repair_Time_Hrs'] = (dept_data['Total_Repair_Time_Min'] / 60).round(1)
            display_cols = ['Error_Source', 'Incidents', 'Pct_of_Total', 'Repair_Qty', 'Recut_Pieces', 'Fail_Qty', 'Total_Repair_Time_Hrs']
            display_cols = [c for c in display_cols if c in dept_data.columns]
            st.dataframe(dept_data[display_cols], use_container_width=True, hide_index=True)


# =============================================================================
# FOOTER
# =============================================================================

st.markdown("---")
st.markdown("*Recut Tracker Dashboard | Data updates on file upload*")
