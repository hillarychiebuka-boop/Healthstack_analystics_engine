import streamlit as st
from db import TARGET_FACILITIES_RAW
from taxonomy import extract_unique_departments


def get_sidebar_filters(
    df_logins=None,
    df_appointments=None,
    df_consults=None,
    df_financials=None,
    df_inventory=None,
    df_sales=None,
    df_lab=None,
    df_clients=None,
):
    """
    Renders Enterprise Controls in the sidebar:
    1. Clean target facility dropdown
    2. Dynamic outpatient/clinical department filter dropdown
    3. Time horizon / duration filter dropdown
    """
    st.sidebar.markdown("### Enterprise Controls")

    # 1. FACILITY FILTER CONTROL
    target_facility_options = ["All Facilities"] + sorted(TARGET_FACILITIES_RAW)

    selected_facility = st.sidebar.selectbox(
        "Select Target Facility",
        options=target_facility_options,
        index=0,
        key="facility_filter_v3",
        help="Restricted to target active health facilities."
    )

    st.sidebar.markdown("---")

    # 2. DEPARTMENT FILTER CONTROL
    # extract_unique_departments already prepends "All Departments" cleanly as index 0
    department_options = extract_unique_departments(
        df_appointments, df_consults, df_sales, df_lab, df_clients
    )

    selected_department = st.sidebar.selectbox(
        "Filter Department",
        options=department_options,
        index=0,
        key="department_filter_v1",
        help="Filter metrics by clinical unit or specialty."
    )

    st.sidebar.markdown("---")

    # 3. REPORTING TIME HORIZON / DURATION CONTROL
    duration_options = [
        "All Time",
        "Last 7 Days",
        "Last 30 Days",
        "Quarterly (Last 90 Days)",
        "Yearly (Last 365 Days)"
    ]

    selected_duration = st.sidebar.selectbox(
        "Reporting Time Horizon",
        options=duration_options,
        index=0,
        key="duration_filter_v1",
        help="Filter metrics across all tabs for executive review."
    )

    st.sidebar.caption("Select a time window to evaluate recent operational performance.")

    return selected_facility, selected_duration, selected_department
