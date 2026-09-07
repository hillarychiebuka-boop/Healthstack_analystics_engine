import streamlit as st
import pandas as pd
import plotly.express as px
from db import db
from taxonomy import standardize_department_dataframe


@st.cache_data(ttl=60)
def load_appointments_data():
    """
    Fetches raw appointments, resolving facility and locationId lookup,
    then applies taxonomy mapping for standardized department analysis.
    """
    collection = db['appointments']
    pipeline = [
        {
            "$match": {
                "appointment_status": { "$exists": True, "$ne": None }
            }
        },
        {
            "$lookup": {
                "from": "facilities",
                "localField": "facility",
                "foreignField": "_id",
                "as": "facilityInfo"
            }
        },
        {
            "$lookup": {
                "from": "departments",
                "localField": "locationId",
                "foreignField": "_id",
                "as": "deptInfo"
            }
        },
        {
            "$lookup": {
                "from": "locations",
                "localField": "locationId",
                "foreignField": "_id",
                "as": "locationInfo"
            }
        },
        {
            "$project": {
                "_id": 0,
                "documentId": { "$toString": "$_id" },
                "status": "$appointment_status",
                "appointment_type": { "$ifNull": ["$appointment_type", "General Consultation"] },
                "createdAt": { "$ifNull": ["$createdAt", "$appointment_date"] },
                "facilityName": {
                    "$cond": [
                        { "$gt": [{ "$size": "$facilityInfo" }, 0] },
                        { "$arrayElemAt": ["$facilityInfo.facilityName", 0] },
                        { "$toString": "$facility" }
                    ]
                },
                "department": {
                    "$cond": [
                        { "$gt": [{ "$size": "$deptInfo" }, 0] },
                        { "$arrayElemAt": ["$deptInfo.name", 0] },
                        {
                            "$cond": [
                                { "$gt": [{ "$size": "$locationInfo" }, 0] },
                                { "$arrayElemAt": ["$locationInfo.name", 0] },
                                { "$ifNull": ["$department", "Undefined"] }
                            ]
                        }
                    ]
                }
            }
        }
    ]

    df = pd.DataFrame(list(collection.aggregate(pipeline)))

    if not df.empty:
        df['createdAt'] = pd.to_datetime(df['createdAt'], errors='coerce', utc=True)
        df['date'] = df['createdAt'].dt.date
        df['facility'] = df['facilityName']
        df = standardize_department_dataframe(df, dept_column="department")

    return df


@st.cache_data(ttl=60)
def load_appointment_types():
    return pd.DataFrame()


def get_shmc_specialized_schedule():
    data = [
        {"Clinic": "Wellness Clinic", "Month": "August", "Booked_Count": 49},
        {"Clinic": "Wellness Clinic", "Month": "September", "Booked_Count": 67},
        {"Clinic": "Nephrology Clinic", "Month": "August", "Booked_Count": 48},
        {"Clinic": "Nephrology Clinic", "Month": "September", "Booked_Count": 45},
        {"Clinic": "Nephrology Clinic", "Month": "October", "Booked_Count": 29},
        {"Clinic": "Dietician Clinic", "Month": "August", "Booked_Count": 21},
        {"Clinic": "Dietician Clinic", "Month": "September", "Booked_Count": 23},
        {"Clinic": "Dietician Clinic", "Month": "October", "Booked_Count": 47},
    ]
    return pd.DataFrame(data)


def render_queue_tab(
    filtered_appts: pd.DataFrame,
    filtered_types=None,
    selected_facility: str = "All Facilities",
    selected_department: str = "All Departments"
):
    """
    Renders appointment queue performance filtered by facility and standardized department.
    """
    st.header(f"📅 Appointment & Queue Management — [{selected_facility}]")
    
    if selected_department != "All Departments":
        st.caption(f"Filtering active dataset for Canonical Department: **{selected_department}**")
        df_display = filtered_appts[filtered_appts['canonical_department'] == selected_department].copy()
    else:
        st.caption("Displaying operational data across all facility departments.")
        df_display = filtered_appts.copy()

    if not df_display.empty:
        in_progress_statuses = [
            "Checked In", "CHECKED_IN", "ARRIVED", "With Nurse",
            "OTHER (WITH NURSE)", "With Doctor", "OTHER (WITH DOCTOR)", "OTHER (VITALS TAKEN)"
        ]
        scheduled_statuses = ["Scheduled", "SCHEDULED", "BOOKED"]
        completed_statuses = [
            "Completed", "COMPLETED", "SERVED", "OTHER (CHECKED OUT)", "Checked Out", "FINAL", "APPROVED"
        ]
        cancelled_statuses = ["Cancelled", "CANCELLED", "CANCELED", "NO_SHOW"]

        total_booked = len(df_display)
        total_in_progress = df_display['status'].isin(in_progress_statuses).sum()
        total_completed = df_display['status'].isin(completed_statuses).sum()
        total_scheduled = df_display['status'].isin(scheduled_statuses).sum()
        total_cancelled = df_display['status'].isin(cancelled_statuses).sum()

        overall_completion_rate = (total_completed / total_booked * 100) if total_booked > 0 else 0

        # KPI Metrics
        app_col1, app_col2, app_col3, app_col4 = st.columns(4)
        app_col1.metric("Total Appointments", f"{total_booked:,}")
        app_col2.metric("Active Queue (Triage/Doctor)", f"{total_in_progress:,}")
        app_col3.metric("Completed Appointments", f"{total_completed:,}")
        app_col4.metric("Completion Rate", f"{overall_completion_rate:.1f}%")

        st.markdown("---")

        row_a1, row_a2 = st.columns(2)

        with row_a1:
            # Updated Metric Title: Top Department by Appointment Volume
            st.subheader(f"📊 Top Department by Appointment Volume — [{selected_facility}]")
            
            dept_app_data = (
                df_display.groupby("canonical_department")
                .size()
                .reset_index(name="totalAppointments")
                .sort_values(by="totalAppointments", ascending=False)
            )

            fig_dept_vol = px.bar(
                dept_app_data,
                x="canonical_department",
                y="totalAppointments",
                labels={"totalAppointments": "Total Bookings", "canonical_department": "Canonical Department"},
                color="totalAppointments",
                color_continuous_scale="Teal",
                template="plotly_dark"
            )
            fig_dept_vol.update_layout(height=380, xaxis_tickangle=-25)
            st.plotly_chart(fig_dept_vol, use_container_width=True)

        with row_a2:
            st.subheader(f"📈 Lifecycle Breakdown — [{selected_facility}]")
            status_totals = pd.DataFrame({
                "Status": ["Booked/Scheduled", "Active Queue (Nurse/Doctor)", "Completed", "Cancelled/No-Show"],
                "Count": [total_scheduled, total_in_progress, total_completed, total_cancelled]
            })
            fig_status_pie = px.pie(
                status_totals,
                names="Status",
                values="Count",
                color="Status",
                color_discrete_map={
                    "Booked/Scheduled": "#3498db",
                    "Active Queue (Nurse/Doctor)": "#f1c40f",
                    "Completed": "#2ecc71",
                    "Cancelled/No-Show": "#e74c3c"
                },
                template="plotly_dark",
                hole=0.4
            )
            fig_status_pie.update_layout(height=380)
            st.plotly_chart(fig_status_pie, use_container_width=True)

        st.markdown("---")

        # Daily Trend Chart
        st.subheader(f"📈 Daily Appointment Volume Trends Over Time — [{selected_facility}]")
        daily_trend_data = (
            df_display.groupby("date")
            .size()
            .reset_index(name="dailyAppointments")
            .sort_values(by="date", ascending=True)
        )

        fig_daily_line = px.line(
            daily_trend_data,
            x="date",
            y="dailyAppointments",
            labels={"dailyAppointments": "Appointments Count", "date": "Date"},
            markers=True,
            template="plotly_dark"
        )
        fig_daily_line.update_traces(line_color="#00D4B2", line_width=3)
        fig_daily_line.update_layout(height=350)
        st.plotly_chart(fig_daily_line, use_container_width=True)

        st.markdown("---")

        row_b1, row_b2 = st.columns(2)

        with row_b1:
            st.subheader(f"🩺 Appointment Types Distribution — [{selected_facility}]")
            type_summary = (
                df_display.groupby("appointment_type")
                .size()
                .reset_index(name="count")
                .sort_values(by="count", ascending=False)
            )
            fig_type = px.bar(
                type_summary,
                x="appointment_type",
                y="count",
                labels={"appointment_type": "Appointment Type", "count": "Patient Count"},
                color="count",
                color_continuous_scale="Viridis",
                template="plotly_dark"
            )
            fig_type.update_layout(height=380)
            st.plotly_chart(fig_type, use_container_width=True)

        with row_b2:
            st.subheader(f"⏱️ Queue Completion Efficiency — [{selected_facility}]")
            queue_comparison = pd.DataFrame({
                "Operational Stage": ["In-Progress (Triage/Doctor)", "Fully Completed Encounters"],
                "Patient Count": [total_in_progress, total_completed]
            })
            fig_queue_comp = px.bar(
                queue_comparison,
                x="Operational Stage",
                y="Patient Count",
                color="Operational Stage",
                color_discrete_sequence=["#f39c12", "#27ae60"],
                template="plotly_dark"
            )
            fig_queue_comp.update_layout(height=380, showlegend=False)
            st.plotly_chart(fig_queue_comp, use_container_width=True)

        st.markdown("---")
        with st.expander("🔍 View Raw Appointments & Aggregated Daily Datasets"):
            tab_daily, tab_granular = st.tabs(["📅 Daily Aggregated Metrics", "📋 Individual Event Log Traceability"])

            with tab_daily:
                daily_grouped = (
                    df_display.groupby(['date', 'facilityName', 'canonical_department'])
                    .agg(
                        Total_Booked_Appointments=('documentId', 'count'),
                        Active_Queue_Encounters=('status', lambda s: s.isin(in_progress_statuses).sum()),
                        Scheduled_Visits=('status', lambda s: s.isin(scheduled_statuses).sum()),
                        Completed_Visits=('status', lambda s: s.isin(completed_statuses).sum()),
                        Cancelled_NoShow_Visits=('status', lambda s: s.isin(cancelled_statuses).sum())
                    )
                    .reset_index()
                )
                daily_grouped['Completion_Rate'] = (
                    (daily_grouped['Completed_Visits'] / daily_grouped['Total_Booked_Appointments']) * 100
                ).round(1)

                st.dataframe(daily_grouped, use_container_width=True, hide_index=True)

            with tab_granular:
                audit_df = df_display.copy()
                audit_df['Timestamp (UTC)'] = audit_df['createdAt'].dt.strftime('%Y-%m-%d %H:%M:%S')

                # Shows both Raw Department and Master Canonical Department for traceability
                granular_table = audit_df[[
                    'Timestamp (UTC)', 'facilityName', 'raw_department', 'canonical_department', 'appointment_type', 'status', 'documentId'
                ]].rename(columns={
                    'raw_department': 'Raw DB Department',
                    'canonical_department': 'Master Standardized Department',
                    'appointment_type': 'Appointment Type',
                    'status': 'Status',
                    'documentId': 'Document ID'
                }).sort_values(by='Timestamp (UTC)', ascending=False)

                st.dataframe(granular_table, use_container_width=True, hide_index=True)
    else:
        st.warning("⚠️ No appointment records match the selected facility and department filter.")
