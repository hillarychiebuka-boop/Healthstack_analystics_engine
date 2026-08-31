import streamlit as st
import pandas as pd
import plotly.express as px
from db import db

@st.cache_data(ttl=3600)
def load_engagement_data():
    """
    Fetches raw login documents with facility details and full timestamps,
    matching the dynamic document-level pattern used in clinical.py.
    """
    pipeline = [
        {"$match": {"type": "login", "createdAt": {"$exists": True, "$ne": None}}},
        {
            "$project": {
                "_id": 0,
                "documentId": {"$toString": "$_id"},
                "userId": {"$ifNull": [{"$toString": "$user._id"}, "Anonymous"]},
                "facilityName": {
                    "$ifNull": [
                        "$facility.facilityName",
                        "$facilityDetails.facilityName",
                        "Unassigned Facility"
                    ]
                },
                "createdAt": 1
            }
        }
    ]

    raw_docs = list(db['logins'].aggregate(pipeline))
    df = pd.DataFrame(raw_docs)

    if not df.empty:
        df['createdAt'] = pd.to_datetime(df['createdAt'], errors='coerce', utc=True)
        df['date'] = df['createdAt'].dt.date
        df['hourOfDay'] = df['createdAt'].dt.hour
        df['facility'] = df['facilityName']

    return df


@st.cache_data(ttl=3600)
def load_hourly_data(selected_facility="All Facilities"):
    """
    Maintained for backward compatibility with app.py imports.
    Returns an empty DataFrame since hourly analytics are computed dynamically.
    """
    return pd.DataFrame()


def render_engagement_tab(filtered_logins, df_hourly=None, filtered_anomalies=None, selected_facility="All Facilities"):
    """
    Renders login metrics dynamically updated by the global time filter.
    """
    st.header(f"📊 User Logins & Engagement Analytics — [{selected_facility}]")
    st.caption("Operational visibility across system authentication logs, active user sessions, and peak system utilization.")

    if not filtered_logins.empty:
        total_logins = len(filtered_logins)
        active_facilities = filtered_logins['facilityName'].nunique()
        unique_users = filtered_logins['userId'].nunique()
        avg_daily_active = int(filtered_logins.groupby('date')['userId'].nunique().mean()) if not filtered_logins.empty else 0

        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        kpi1.metric("Total Login Events", f"{total_logins:,}")
        kpi2.metric("Active Facilities", f"{active_facilities:,}")
        kpi3.metric("Unique Active Users", f"{unique_users:,}")
        kpi4.metric("Avg Daily Active Users", f"{avg_daily_active:,}")

        st.markdown("---")

        row1_col1, row1_col2 = st.columns(2)

        with row1_col1:
            if selected_facility == "TARGETED_FACILITIES_RAW":
                st.subheader("🏥 Top Active Facilities (Unique Users)")
                top_chart_data = (
                    filtered_logins.groupby("facilityName")["userId"]
                    .nunique()
                    .reset_index(name="UniqueUsers")
                    .sort_values(by="UniqueUsers", ascending=False)
                    .head(10)
                )

                fig_top10 = px.bar(
                    top_chart_data,
                    x="UniqueUsers",
                    y="facilityName",
                    orientation="h",
                    labels={"UniqueUsers": "Unique Active Users", "facilityName": "Facility Name"},
                    color="UniqueUsers",
                    color_continuous_scale="Blues",
                    template="plotly_dark"
                )
                fig_top10.update_layout(yaxis=dict(autorange="reversed"), showlegend=False, height=380)
                st.plotly_chart(fig_top10, use_container_width=True)
            else:
                st.subheader(f"📅 Daily Login Volume — [{selected_facility}]")
                top_chart_data = (
                    filtered_logins.groupby("date")
                    .size()
                    .reset_index(name="TotalLogins")
                    .sort_values(by="TotalLogins", ascending=False)
                    .head(10)
                )
                top_chart_data['date_str'] = top_chart_data['date'].astype(str)

                fig_top10 = px.bar(
                    top_chart_data,
                    x="TotalLogins",
                    y="date_str",
                    orientation="h",
                    labels={"TotalLogins": "Login Volume", "date_str": "Date"},
                    color="TotalLogins",
                    color_continuous_scale="Blues",
                    template="plotly_dark"
                )
                fig_top10.update_layout(yaxis=dict(autorange="reversed"), showlegend=False, height=380)
                st.plotly_chart(fig_top10, use_container_width=True)

        with row1_col2:
            st.subheader(f"⏰ Peak Operational Hours — [{selected_facility}]")
            hourly_counts = (
                filtered_logins.groupby("hourOfDay")
                .size()
                .reset_index(name="LoginCount")
            )

            if not hourly_counts.empty:
                fig_hourly = px.bar(
                    hourly_counts,
                    x="hourOfDay",
                    y="LoginCount",
                    labels={"hourOfDay": "Hour of Day (0-23 UTC)", "LoginCount": "Login Volume"},
                    color="LoginCount",
                    color_continuous_scale="Cividis",
                    template="plotly_dark"
                )
                fig_hourly.update_layout(height=380)
                st.plotly_chart(fig_hourly, use_container_width=True)
            else:
                st.info("No hourly login logs available for this time selection.")

        st.markdown("---")

        st.subheader(f"📈 System Login Velocity Over Time — [{selected_facility}]")
        daily_trend = filtered_logins.groupby("date").size().reset_index(name="DailyLogins")
        
        fig_trend = px.line(
            daily_trend,
            x="date",
            y="DailyLogins",
            labels={"date": "Date", "DailyLogins": "Daily Logins"},
            template="plotly_dark"
        )
        fig_trend.update_traces(line_color="#00bc8c", line_width=2)
        fig_trend.update_layout(height=350)
        st.plotly_chart(fig_trend, use_container_width=True)

        # Dynamic Aggregated Raw Data Table with Timestamp
        with st.expander("🔍 View Raw Logins Aggregated Dataset"):
            # Format timestamp for display
            filtered_logins['formatted_time'] = filtered_logins['createdAt'].dt.strftime('%Y-%m-%d %H:%M:%S')

            summary_table = (
                filtered_logins.groupby(['formatted_time', 'facilityName'])
                .agg(
                    Total_Login_Events=('documentId', 'count'),
                    Unique_Active_Users=('userId', 'nunique')
                )
                .reset_index()
                .sort_values(by='formatted_time', ascending=False)
            )
            
            summary_table.columns = [
                "Date & Time (UTC)",
                "Facility Name",
                "Login Events",
                "Unique Active Users"
            ]
            
            st.dataframe(summary_table, use_container_width=True, hide_index=True)
    else:
        st.warning("⚠️ No login activity records found for the selected facility and timeframe.")
