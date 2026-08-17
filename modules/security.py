import streamlit as st
import pandas as pd
import plotly.express as px
from db import db

@st.cache_data(ttl=3600)
def load_security_anomalies():
    collection = db['logins']
    anomaly_pipeline = [
        {
            "$match": {
                "type": "login",
                "facility._id": { "$exists": True, "$ne": None }
            }
        },
        {
            "$project": {
                "_id": 0,
                "facility": "$facility.facilityName",
                "userEmail": "$user.email",
                "timestamp": "$createdAt",
                "hour": { "$hour": "$createdAt" }
            }
        },
        {
            "$match": {
                "$or": [
                    { "hour": { "$gte": 22 } },
                    { "hour": { "$lte": 4 } }
                ]
            }
        },
        { "$limit": 200 }
    ]
    return pd.DataFrame(list(collection.aggregate(anomaly_pipeline)))

def render_security_tab(filtered_anomalies, selected_facility):
    st.header(f"🛡️ Security & Access Anomaly Center — [{selected_facility}]")
    st.caption("Monitoring off-peak operational access events (10:00 PM – 4:00 AM) to maintain system governance.")

    if not filtered_anomalies.empty:
        s1, s2 = st.columns(2)
        s1.metric("Off-Peak Access Flags Detected", f"{len(filtered_anomalies):,}")
        s2.metric("Flagged Unique User Accounts", f"{filtered_anomalies['userEmail'].nunique():,}")

        st.markdown("---")

        sec_col1, sec_col2 = st.columns(2)

        with sec_col1:
            st.subheader(f"🌙 Off-Peak Logins Hour Distribution — [{selected_facility}]")
            hourly_anom = filtered_anomalies['hour'].value_counts().reset_index()
            hourly_anom.columns = ['Hour of Day (UTC)', 'Anomaly Count']
            
            fig_anom_h = px.bar(
                hourly_anom,
                x='Hour of Day (UTC)',
                y='Anomaly Count',
                color='Anomaly Count',
                color_continuous_scale='Reds',
                template='plotly_dark'
            )
            fig_anom_h.update_layout(height=380)
            st.plotly_chart(fig_anom_h, use_container_width=True)

        with sec_col2:
            st.subheader(f"⚠️ Flagged Accounts by Off-Peak Volume — [{selected_facility}]")
            user_anom = filtered_anomalies['userEmail'].value_counts().head(10).reset_index()
            user_anom.columns = ['User Email', 'Flagged Accesses']

            fig_anom_u = px.bar(
                user_anom,
                x='Flagged Accesses',
                y='User Email',
                orientation='h',
                color='Flagged Accesses',
                color_continuous_scale='Oranges',
                template='plotly_dark'
            )
            fig_anom_u.update_layout(yaxis=dict(autorange="reversed"), height=380, showlegend=False)
            st.plotly_chart(fig_anom_u, use_container_width=True)

        with st.expander("🔍 Inspect Security Anomaly Logs"):
            st.dataframe(filtered_anomalies, use_container_width=True)
    else:
        st.info("No security anomalies recorded for this facility.")