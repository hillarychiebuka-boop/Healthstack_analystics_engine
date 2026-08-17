import streamlit as st
import pandas as pd
import plotly.express as px
from db import db

@st.cache_data(ttl=3600)
def load_engagement_data():
    collection = db['logins']
    pipeline = [
        {
            "$match": {
                "type": "login",
                "facility._id": { "$exists": True, "$ne": None }
            }
        },
        {
            "$group": {
                "_id": {
                    "facility": "$facility.facilityName",
                    "date": { "$dateToString": { "format": "%Y-%m-%d", "date": "$createdAt" } }
                },
                "uniqueUsers": { "$addToSet": "$user._id" },
                "totalLogins": { "$sum": 1 }
            }
        },
        {
            "$project": {
                "_id": 0,
                "facility": "$_id.facility",
                "date": "$_id.date",
                "totalLogins": 1,
                "activeUsersCount": { "$size": "$uniqueUsers" }
            }
        },
        { "$sort": { "date": -1 } }
    ]
    data = pd.DataFrame(list(collection.aggregate(pipeline)))
    if not data.empty:
        data['date'] = pd.to_datetime(data['date'])
    return data

@st.cache_data(ttl=3600)
def load_hourly_data(selected_facility="All Facilities"):
    collection = db['logins']
    match_stage = { "type": "login" }
    
    if selected_facility != "All Facilities":
        match_stage["facility.facilityName"] = selected_facility

    hourly_pipeline = [
        { "$match": match_stage },
        { "$group": { "_id": { "$hour": "$createdAt" }, "totalLogins": { "$sum": 1 } } },
        { "$sort": { "_id": 1 } }
    ]
    df_h = pd.DataFrame(list(collection.aggregate(hourly_pipeline)))
    if not df_h.empty:
        df_h.rename(columns={'_id': 'hourOfDay'}, inplace=True)
    return df_h

def render_engagement_tab(filtered_logins, df_hourly, filtered_anomalies, selected_facility):
    st.header(f"📊 User Logins & Engagement Analytics — [{selected_facility}]")
    
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    kpi1.metric("Total Login Events", f"{filtered_logins['totalLogins'].sum():,}" if not filtered_logins.empty else "0")
    kpi2.metric("Active Facilities", f"{filtered_logins['facility'].nunique():,}" if not filtered_logins.empty else "0")
    kpi3.metric("Avg Daily Active Users", f"{int(filtered_logins['activeUsersCount'].mean()):,}" if not filtered_logins.empty and not filtered_logins['activeUsersCount'].isna().all() else "0")
    kpi4.metric("Off-Peak Anomaly Flags", f"{len(filtered_anomalies):,}", delta="Security Review", delta_color="inverse")

    st.markdown("---")

    row1_col1, row1_col2 = st.columns(2)

    with row1_col1:
        if selected_facility == "All Facilities":
            st.subheader("Top Active Facilities (User Engagement)")
            top_chart_data = (
                filtered_logins.groupby("facility", as_index=False)["activeUsersCount"]
                .sum()
                .sort_values(by="activeUsersCount", ascending=False)
                .head(10)
            )
            y_axis_col = "facility"
            y_label = "Facility Name"
        else:
            st.subheader(f"User Login Density — [{selected_facility}]")
            top_chart_data = (
                filtered_logins.groupby("date", as_index=False)["totalLogins"]
                .sum()
                .sort_values(by="totalLogins", ascending=False)
                .head(10)
            )
            top_chart_data['date_str'] = top_chart_data['date'].dt.strftime('%Y-%m-%d')
            y_axis_col = "date_str"
            y_label = "Date"

        fig_top10 = px.bar(
            top_chart_data,
            x="activeUsersCount" if selected_facility == "All Facilities" else "totalLogins",
            y=y_axis_col,
            orientation="h",
            labels={"activeUsersCount": "Active Users", "totalLogins": "Login Volume", y_axis_col: y_label},
            color="activeUsersCount" if selected_facility == "All Facilities" else "totalLogins",
            color_continuous_scale="Blues",
            template="plotly_dark"
        )
        fig_top10.update_layout(yaxis=dict(autorange="reversed"), showlegend=False, height=400)
        st.plotly_chart(fig_top10, use_container_width=True)

    with row1_col2:
        st.subheader(f"Peak Operational Hours — [{selected_facility}]")
        if not df_hourly.empty:
            fig_hourly = px.bar(
                df_hourly,
                x="hourOfDay",
                y="totalLogins",
                labels={"hourOfDay": "Hour of Day (0-23 UTC)", "totalLogins": "Login Volume"},
                color="totalLogins",
                color_continuous_scale="Cividis",
                template="plotly_dark"
            )
            fig_hourly.update_layout(height=400)
            st.plotly_chart(fig_hourly, use_container_width=True)
        else:
            st.info("No hourly login logs available for this facility.")

    st.subheader(f"System Login Velocity Over Time — [{selected_facility}]")
    if not filtered_logins.empty:
        daily_trend = filtered_logins.groupby("date", as_index=False)["totalLogins"].sum()
        fig_trend = px.line(
            daily_trend,
            x="date",
            y="totalLogins",
            labels={"date": "Date", "totalLogins": "Daily Logins"},
            template="plotly_dark"
        )
        fig_trend.update_traces(line_color="#00bc8c", line_width=2)
        fig_trend.update_layout(height=350)
        st.plotly_chart(fig_trend, use_container_width=True)

    with st.expander("🔍 View Raw Logins Aggregated Dataset"):
        clean_logins_display = filtered_logins.rename(columns={
            "facility": "Facility Name",
            "date": "Log Date",
            "totalLogins": "Total Login Events",
            "activeUsersCount": "Unique Active Users"
        })
        st.dataframe(clean_logins_display, use_container_width=True)