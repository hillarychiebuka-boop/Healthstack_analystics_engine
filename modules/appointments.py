import streamlit as st
import pandas as pd
import plotly.express as px
from db import db

@st.cache_data(ttl=3600)
def load_appointments_data():
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
            "$addFields": {
                "facilityName": {
                    "$cond": [
                        { "$gt": [{ "$size": "$facilityInfo" }, 0] },
                        { "$arrayElemAt": ["$facilityInfo.facilityName", 0] },
                        { "$toString": "$facility" }
                    ]
                }
            }
        },
        {
            "$group": {
                "_id": "$facilityName",
                "totalAppointments": { "$sum": 1 },
                "inProgressCount": {
                    "$sum": {
                        "$cond": [
                            { "$in": [ "$appointment_status", [
                                "Checked In", "CHECKED_IN", "ARRIVED", 
                                "With Nurse", "OTHER (WITH NURSE)", 
                                "With Doctor", "OTHER (WITH DOCTOR)", 
                                "OTHER (VITALS TAKEN)"
                            ] ] },
                            1, 0
                        ]
                    }
                },
                "scheduledCount": {
                    "$sum": {
                        "$cond": [
                            { "$in": [ "$appointment_status", ["Scheduled", "SCHEDULED", "BOOKED"] ] },
                            1, 0
                        ]
                    }
                },
                "completedCount": {
                    "$sum": {
                        "$cond": [
                            { "$in": [ "$appointment_status", ["Completed", "COMPLETED", "SERVED", "OTHER (CHECKED OUT)", "Checked Out"] ] },
                            1, 0
                        ]
                    }
                },
                "cancelledCount": {
                    "$sum": {
                        "$cond": [
                            { "$in": [ "$appointment_status", ["Cancelled", "CANCELLED", "CANCELED", "NO_SHOW"] ] },
                            1, 0
                        ]
                    }
                }
            }
        },
        {
            "$project": {
                "_id": 0,
                "facility": "$_id",
                "totalAppointments": 1,
                "inProgressCount": 1,
                "scheduledCount": 1,
                "completedCount": 1,
                "cancelledCount": 1,
                "completionRate": {
                    "$cond": [
                        { "$gt": ["$totalAppointments", 0] },
                        {
                            "$multiply": [
                                { "$divide": ["$completedCount", "$totalAppointments"] },
                                100
                            ]
                        },
                        0
                    ]
                }
            }
        }
    ]
    return pd.DataFrame(list(collection.aggregate(pipeline)))

@st.cache_data(ttl=3600)
def load_appointment_types():
    collection = db['appointments']
    pipeline = [
        {
            "$match": {
                "appointment_type": { "$exists": True, "$ne": None }
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
            "$addFields": {
                "facilityName": {
                    "$cond": [
                        { "$gt": [{ "$size": "$facilityInfo" }, 0] },
                        { "$arrayElemAt": ["$facilityInfo.facilityName", 0] },
                        { "$toString": "$facility" }
                    ]
                }
            }
        },
        {
            "$group": {
                "_id": {
                    "facility": "$facilityName",
                    "type": "$appointment_type"
                },
                "count": { "$sum": 1 }
            }
        },
        {
            "$project": {
                "_id": 0,
                "facility": "$_id.facility",
                "type": "$_id.type",
                "count": 1
            }
        }
    ]
    return pd.DataFrame(list(collection.aggregate(pipeline)))

def render_queue_tab(filtered_appts, filtered_types, selected_facility):
    st.header(f"📅 Facility Appointment & Queue Management — [{selected_facility}]")
    st.caption("Real-time operational metrics across booked, checked-in, and completed patient visits.")

    if not filtered_appts.empty:
        app_col1, app_col2, app_col3, app_col4 = st.columns(4)
        
        total_booked = filtered_appts['totalAppointments'].sum()
        total_completed = filtered_appts['completedCount'].sum()
        total_in_progress = filtered_appts['inProgressCount'].sum()
        overall_completion_rate = (total_completed / total_booked * 100) if total_booked > 0 else 0

        app_col1.metric("Total Appointments", f"{total_booked:,}")
        app_col2.metric("Active Queue (Triage/Doctor)", f"{total_in_progress:,}")
        app_col3.metric("Completed Encounters", f"{total_completed:,}")
        app_col4.metric("Completion Rate", f"{overall_completion_rate:.1f}%")

        st.markdown("---")

        row_a1, row_a2 = st.columns(2)

        with row_a1:
            if selected_facility == "All Facilities":
                st.subheader("🏥 Top Facilities by Appointment Volume")
                top_app_data = filtered_appts.sort_values(by="totalAppointments", ascending=False).head(10)
            else:
                st.subheader(f"🏥 Facility Operational Volume Breakdown — [{selected_facility}]")
                top_app_data = filtered_appts.copy()

            fig_app_vol = px.bar(
                top_app_data,
                x="totalAppointments",
                y="facility",
                orientation="h",
                labels={"totalAppointments": "Total Bookings", "facility": "Facility Name"},
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
                "Count": [
                    filtered_appts['scheduledCount'].sum(),
                    filtered_appts['inProgressCount'].sum(),
                    filtered_appts['completedCount'].sum(),
                    filtered_appts['cancelledCount'].sum()
                ]
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
            if not filtered_types.empty:
                type_summary = filtered_types.groupby("type", as_index=False)["count"].sum().sort_values(by="count", ascending=False)
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

        with st.expander("🔍 View Raw Appointments Aggregated Data"):
            clean_appts_display = filtered_appts.rename(columns={
                "facility": "Facility Name",
                "totalAppointments": "Total Booked Appointments",
                "inProgressCount": "Active Queue Encounters",
                "scheduledCount": "Scheduled Visits",
                "completedCount": "Completed Visits",
                "cancelledCount": "Cancelled / No-Show Visits",
                "completionRate": "Completion Rate (%)"
            })
            st.dataframe(clean_appts_display, use_container_width=True)
    else:
        st.warning("⚠️ No appointment records found for the selected facility filter.")