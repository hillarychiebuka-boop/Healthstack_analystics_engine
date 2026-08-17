import streamlit as st
import pandas as pd
import plotly.express as px
from db import db

@st.cache_data(ttl=3600)
def load_clinical_consultations():
    pipeline = [
        {"$match": {"createdAt": {"$exists": True, "$ne": None}}},
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
                "from": "users",
                "localField": "createdBy",
                "foreignField": "_id",
                "as": "userInfo"
            }
        },
        {
            "$project": {
                "_id": 0,
                "documentId": {"$toString": "$_id"},
                "facilityName": {
                    "$cond": [
                        {"$gt": [{"$size": "$facilityInfo"}, 0]},
                        {"$arrayElemAt": ["$facilityInfo.facilityName", 0]},
                        "Unassigned Facility"
                    ]
                },
                "practitionerName": {
                    "$cond": [
                        {"$gt": [{"$size": "$userInfo"}, 0]},
                        {
                            "$concat": [
                                {"$ifNull": [{"$arrayElemAt": ["$userInfo.firstname", 0]}, "Staff"]},
                                " ",
                                {"$ifNull": [{"$arrayElemAt": ["$userInfo.lastname", 0]}, "Member"]}
                            ]
                        },
                        "System / Unassigned"
                    ]
                },
                "rawDocType": {"$ifNull": ["$documentType", "General Consultation"]},
                "clientId": {"$ifNull": [{"$toString": "$client"}, "Anonymous Patient"]},
                "status": {"$ifNull": ["$status", "completed"]},
                "createdAt": 1
            }
        }
    ]

    raw_docs = list(db['clinicaldocuments'].aggregate(pipeline))
    df = pd.DataFrame(raw_docs)

    if not df.empty:
        df['createdAt'] = pd.to_datetime(df['createdAt'])
        df['date'] = df['createdAt'].dt.date
        df['dayOfWeek'] = df['createdAt'].dt.day_name()

        def categorize_doc_type(doc_type):
            dt = str(doc_type).lower().strip()
            if any(k in dt for k in ['general consultation', 'doctor note', 'primary assessment', 'clinical']):
                return 'General Consultations'
            elif any(k in dt for k in ['vitals', 'nurse', 'nursing', 'duty report']):
                return 'Nursing & Triage'
            elif any(k in dt for k in ['lab', 'laboratory', 'diagnostic', 'ecg']):
                return 'Diagnostic & Lab'
            elif 'radiology' in dt:
                return 'Radiology & Imaging'
            elif 'prescription' in dt:
                return 'Pharmacy & Prescriptions'
            elif any(k in dt for k in ['anc', 'dental', 'sleep', 'physiotherapy', 'heamodialysis', 'osteoporosis', 'back pain', 'nutrition', 'dietary']):
                return 'Specialized Clinics & ANC'
            elif any(k in dt for k in ['operation', 'surgical', 'caesarean']):
                return 'Surgical & Procedures'
            else:
                return 'Other Clinical Notes'

        df['clinicalDomain'] = df['rawDocType'].apply(categorize_doc_type)

    return df

def render_clinical_tab(filtered_consults, selected_facility):
    st.header(f"🩺 Outpatient Encounters & Clinical Consultations — [{selected_facility}]")
    st.caption("Operational visibility across clinical documentation records, practitioner workloads, and clinical domains.")

    if not filtered_consults.empty:
        m1, m2, m3, m4 = st.columns(4)
        
        total_encounters = len(filtered_consults)
        unique_patients = filtered_consults['clientId'].nunique()
        active_practitioners = filtered_consults['practitionerName'].nunique()
        avg_daily_volume = int(filtered_consults.groupby('date')['documentId'].count().mean()) if not filtered_consults.empty else 0

        m1.metric("Total Encounters Logged", f"{total_encounters:,}")
        m2.metric("Unique Patients Served", f"{unique_patients:,}")
        m3.metric("Active Practitioners", f"{active_practitioners:,}")
        m4.metric("Avg Daily Encounters", f"{avg_daily_volume:,}")

        st.markdown("---")

        col1, col2 = st.columns(2)

        with col1:
            st.subheader(f"📊 Encounters by Clinical Domain — [{selected_facility}]")
            domain_counts = (
                filtered_consults['clinicalDomain']
                .value_counts()
                .reset_index()
            )
            domain_counts.columns = ['Clinical Domain', 'Encounters']

            fig_domain = px.bar(
                domain_counts,
                x='Encounters',
                y='Clinical Domain',
                orientation='h',
                color='Encounters',
                color_continuous_scale='Tealgrn',
                template='plotly_dark'
            )
            fig_domain.update_layout(yaxis=dict(autorange="reversed"), height=380, showlegend=False)
            st.plotly_chart(fig_domain, use_container_width=True)

        with col2:
            if selected_facility == "All Facilities":
                st.subheader("🏥 Top 10 Facilities by Clinical Encounters")
                fac_counts = (
                    filtered_consults['facilityName']
                    .value_counts()
                    .head(10)
                    .reset_index()
                )
                fac_counts.columns = ['Facility Name', 'Encounters']

                fig_fac = px.bar(
                    fac_counts,
                    x='Encounters',
                    y='Facility Name',
                    orientation='h',
                    color='Encounters',
                    color_continuous_scale='Viridis',
                    template='plotly_dark'
                )
                fig_fac.update_layout(yaxis=dict(autorange="reversed"), height=380, showlegend=False)
                st.plotly_chart(fig_fac, use_container_width=True)
            else:
                st.subheader(f"👨‍⚕️ Top Active Practitioners — [{selected_facility}]")
                doc_counts = (
                    filtered_consults['practitionerName']
                    .value_counts()
                    .head(10)
                    .reset_index()
                )
                doc_counts.columns = ['Practitioner Name', 'Encounters']

                fig_docs = px.bar(
                    doc_counts,
                    x='Encounters',
                    y='Practitioner Name',
                    orientation='h',
                    color='Encounters',
                    color_continuous_scale='Blues',
                    template='plotly_dark'
                )
                fig_docs.update_layout(yaxis=dict(autorange="reversed"), height=380, showlegend=False)
                st.plotly_chart(fig_docs, use_container_width=True)

        st.markdown("---")

        st.subheader(f"📈 Outpatient Encounter Velocity Over Time — [{selected_facility}]")
        daily_trends = (
            filtered_consults.groupby(['date', 'clinicalDomain'])
            .size()
            .reset_index(name='Encounters')
        )

        fig_trend = px.area(
            daily_trends,
            x='date',
            y='Encounters',
            color='clinicalDomain',
            labels={'date': 'Encounter Date', 'clinicalDomain': 'Clinical Domain'},
            template='plotly_dark',
            color_discrete_sequence=px.colors.qualitative.Bold
        )
        fig_trend.update_layout(height=380, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        st.plotly_chart(fig_trend, use_container_width=True)

        with st.expander("🔍 Inspect Processed Clinical Documents Records"):
            display_cols = ['createdAt', 'facilityName', 'practitionerName', 'rawDocType', 'clinicalDomain', 'status']
            st.dataframe(
                filtered_consults[display_cols].sort_values(by='createdAt', ascending=False),
                use_container_width=True
            )
    else:
        st.warning("⚠️ No clinical consultation records found for the selected facility filter.")