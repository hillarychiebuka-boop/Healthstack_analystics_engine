import streamlit as st
import pandas as pd
import plotly.express as px
from db import db

@st.cache_data(ttl=3600)
def load_appointments_data():
    """
    Fetches raw individual appointment records with timestamps,
    facility details, and status for dynamic filtering by date/duration.
    """
    collection = db['appointments']
    pipeline = [
        {
            "$match": {
                "facility": { "$exists": True, "$ne": None },
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
            "$project": {
                "_id": 0,
                "documentId": { "$toString": "$_id" },
                "status": "$appointment_status",
                "type": { "$ifNull": ["$appointment_type", "General Consultation"] },
                "createdAt": { "$ifNull": ["$createdAt", "$appointment_date"] },
                "facilityName": {
                    "$cond": [
                        { "$gt": [{ "$size": "$facilityInfo" }, 0] },
                        { "$arrayElemAt": ["$facilityInfo.facilityName", 0] },
                        { "$toString": "$facility" }
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

    return df


@st.cache_data(ttl=3600)
def load_appointment_types():
    """
    Maintained for backward compatibility with app.py imports.
    Returns empty DataFrame as types are calculated dynamically in render_queue_tab.
    """
    return pd.DataFrame()


def render_queue_tab(filtered_appts, filtered_types=None, selected_facility="All Facilities"):
    """
    Renders appointment metrics dynamically aggregated according to selected date range and facility.
    """
    st.header(f"📅 Facility Appointment & Queue Management — [{selected_facility}]")
    st.caption("Real-time operational metrics across booked, checked-in, and completed patient visits.")

    if not filtered_appts.empty:
        # Define status mapping categories
        in_progress_statuses = [
            "Checked In", "CHECKED_IN", "ARRIVED", "With Nurse",
            "OTHER (WITH NURSE)", "With Doctor", "OTHER (WITH DOCTOR)", "OTHER (VITALS TAKEN)"
        ]
        scheduled_statuses = ["Scheduled", "SCHEDULED", "BOOKED"]
        completed_statuses = ["Completed", "COMPLETED", "SERVED", "OTHER (CHECKED OUT)", "Checked Out"]
        cancelled_statuses = ["Cancelled", "CANCELLED", "CANCELED", "NO_SHOW"]

        total_booked = len(filtered_appts)
        total_in_progress = filtered_appts['status'].isin(in_progress_statuses).sum()
        total_completed = filtered_appts['status'].isin(completed_statuses).sum()
        total_scheduled = filtered_appts['status'].isin(scheduled_statuses).sum()
        total_cancelled = filtered_appts['status'].isin(cancelled_statuses).sum()
        
        overall_completion_rate = (total_completed / total_booked * 100) if total_booked > 0 else 0

        app_col1, app_col2, app_col3, app_col4 = st.columns(4)
        app_col1.metric("Total Appointments", f"{total_booked:,}")
        app_col2.metric("Active Queue (Triage/Doctor)", f"{total_in_progress:,}")
        app_col3.metric("Completed Encounters", f"{total_completed:,}")
        app_col4.metric("Completion Rate", f"{overall_completion_rate:.1f}%")

        st.markdown("---")

        row_a1, row_a2 = st.columns(2)

        with row_a1:
            if selected_facility == "All Facilities":
                st.subheader("🏥 Top Facilities by Appointment Volume")
                top_app_data = (
                    filtered_appts.groupby("facilityName")
                    .size()
                    .reset_index(name="totalAppointments")
                    .sort_values(by="totalAppointments", ascending=False)
                    .head(10)
                )
            else:
                st.subheader(f"🏥 Facility Operational Volume Breakdown — [{selected_facility}]")
                top_app_data = (
                    filtered_appts.groupby("facilityName")
                    .size()
                    .reset_index(name="totalAppointments")
                )

            fig_app_vol = px.bar(
                top_app_data,
                x="totalAppointments",
                y="facilityName",
                orientation="h",
                labels={"totalAppointments": "Total Bookings", "facilityName": "Facility Name"},
                color="totalAppointments",
                color_continuous_scale="Teal",
                template="plotly_dark"
            )
            fig_app_vol.update_layout(yaxis=dict(autorange="reversed"), height=380)
            st.plotly_chart(fig_app_vol, use_container_width=True)

        with row_a2:
            st.subheader(f"📈 Appointment Lifecycle Breakdown — [{selected_facility}]")
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

        row_b1, row_b2 = st.columns(2)

        with row_b1:
            st.subheader(f"🩺 Appointment Types Distribution — [{selected_facility}]")
            type_summary = (
                filtered_appts.groupby("type")
                .size()
                .reset_index(name="count")
                .sort_values(by="count", ascending=False)
            )
            if not type_summary.empty:
                fig_type = px.bar(
                    type_summary,
                    x="type",
                    y="count",
                    labels={"type": "Appointment Type", "count": "Patient Count"},
                    color="count",
                    color_continuous_scale="Viridis",
                    template="plotly_dark"
                )
                fig_type.update_layout(height=380)
                st.plotly_chart(fig_type, use_container_width=True)
            else:
                st.info("No appointment type details available for selected facility.")

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

        # Dynamic Aggregated Raw Data Table with Timestamp
        with st.expander("🔍 View Raw Appointments Aggregated Data"):
            # Format timestamp for display
            filtered_appts['formatted_time'] = filtered_appts['createdAt'].dt.strftime('%Y-%m-%d %H:%M:%S')

            grouped_appts = (
                filtered_appts.groupby(['formatted_time', 'facilityName'])
                .agg(
                    Total_Booked_Appointments=('documentId', 'count'),
                    Active_Queue_Encounters=('status', lambda s: s.isin(in_progress_statuses).sum()),
                    Scheduled_Visits=('status', lambda s: s.isin(scheduled_statuses).sum()),
                    Completed_Visits=('status', lambda s: s.isin(completed_statuses).sum()),
                    Cancelled_NoShow_Visits=('status', lambda s: s.isin(cancelled_statuses).sum())
                )
                .reset_index()
            )
            grouped_appts['Completion_Rate'] = (
                (grouped_appts['Completed_Visits'] / grouped_appts['Total_Booked_Appointments']) * 100
            ).round(1)

            summary_table = grouped_appts.rename(columns={
                "formatted_time": "Date & Time (UTC)",
                "facilityName": "Facility Name",
                "Total_Booked_Appointments": "Total Booked Appointments",
                "Active_Queue_Encounters": "Active Queue Encounters",
                "Scheduled_Visits": "Scheduled Visits",
                "Completed_Visits": "Completed Visits",
                "Cancelled_NoShow_Visits": "Cancelled / No-Show Visits",
                "Completion_Rate": "Completion Rate (%)"
            }).sort_values(by="Date & Time (UTC)", ascending=False)

            st.dataframe(summary_table, use_container_width=True, hide_index=True)
    else:
        st.warning("⚠️ No appointment records found for the selected facility filter.")
