import streamlit as st
import plotly.express as px
import pandas as pd
import numpy as np

def render_patient_engagement_tab(df_clients, selected_facility="All Facilities"):
    """
    Renders Production Executive Patient Engagement Dashboard.
    """
    st.subheader("👥 Patient Engagement & Registration Engine")
    st.markdown("Population analytics, registration velocity, clinical age cohorts, and demographic profiles.")

    if df_clients.empty:
        st.warning("⚠️ No client registration records available for the selected facility.")
        return

    # ---------------------------------------------------------
    # 1. EXECUTIVE KPI CARDS
    # ---------------------------------------------------------
    total_patients = len(df_clients)
    valid_age_df = df_clients.dropna(subset=['ageGroup'])
    data_completeness = (len(valid_age_df) / total_patients * 100) if total_patients > 0 else 0.0

    new_patients = len(df_clients[df_clients['patientType'] == 'New Registration'])
    hmo_patients = len(df_clients[df_clients['coverageType'] == 'HMO Covered'])
    cash_patients = len(df_clients[df_clients['coverageType'] == 'Cash Out-of-Pocket'])
    hmo_rate = (hmo_patients / total_patients * 100) if total_patients > 0 else 0.0
    avg_age = df_clients['age'].dropna().mean()

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Total Patient Base", f"{total_patients:,}")
    k2.metric("New Registrations (30d)", f"{new_patients:,}")
    k3.metric("HMO Covered Base", f"{hmo_patients:,}", delta=f"{hmo_rate:.1f}% Share")
    k4.metric("Cash Out-of-Pocket", f"{cash_patients:,}")
    k5.metric("Average Patient Age", f"{avg_age:.1f} yrs" if pd.notnull(avg_age) else "N/A", help=f"Data Completeness: {data_completeness:.1f}%")

    st.markdown("---")

    # ---------------------------------------------------------
    # 2. DEMOGRAPHICS & GENDER BREAKDOWN (DONUT & BAR CHARTS)
    # ---------------------------------------------------------
    r1_col1, r1_col2, r1_col3 = st.columns([1.2, 1, 1])

    with r1_col1:
        st.markdown("##### 📊 Clinical Demographic Cohorts")
        # Filter out NaN/Unknown from the bar chart for professional rendering
        age_counts = valid_age_df['ageGroup'].value_counts().reindex(
            ["Infant (0-1)", "Pediatric (2-12)", "Youth (13-24)", "Adult (25-59)", "Senior (60+)"]
        ).dropna().reset_index()
        age_counts.columns = ['Demographic Group', 'Patient Count']

        fig_age = px.bar(
            age_counts,
            x='Demographic Group',
            y='Patient Count',
            color='Demographic Group',
            color_discrete_sequence=px.colors.qualitative.Bold,
            text='Patient Count'
        )
        fig_age.update_traces(texttemplate='%{text:,}', textposition='outside')
        fig_age.update_layout(
            height=340, 
            showlegend=False, 
            margin=dict(l=10, r=10, t=20, b=10),
            xaxis_title=None,
            yaxis_title="Patients"
        )
        st.plotly_chart(fig_age, use_container_width=True)

    with r1_col2:
        st.markdown("##### 🚻 Gender Split")
        gender_counts = df_clients['gender'].value_counts().reset_index()
        gender_counts.columns = ['Gender', 'Count']

        fig_gender = px.pie(
            gender_counts,
            names='Gender',
            values='Count',
            hole=0.55,
            color='Gender',
            color_discrete_map={'FEMALE': '#E91E63', 'MALE': '#1E88E5', 'UNSPECIFIED': '#9E9E9E'}
        )
        fig_gender.update_traces(textposition='inside', textinfo='percent+label')
        fig_gender.update_layout(height=340, showlegend=False, margin=dict(l=10, r=10, t=20, b=10))
        st.plotly_chart(fig_gender, use_container_width=True)

    with r1_col3:
        st.markdown("##### 💳 Payer Coverage Model")
        pay_counts = df_clients['coverageType'].value_counts().reset_index()
        pay_counts.columns = ['Coverage Type', 'Count']

        fig_pay = px.pie(
            pay_counts,
            names='Coverage Type',
            values='Count',
            hole=0.55,
            color_discrete_sequence=['#00B0FF', '#FF9100', '#00E676']
        )
        fig_pay.update_traces(textposition='inside', textinfo='percent+label')
        fig_pay.update_layout(height=340, showlegend=False, margin=dict(l=10, r=10, t=20, b=10))
        st.plotly_chart(fig_pay, use_container_width=True)

    st.markdown("---")

    # ---------------------------------------------------------
    # 3. DAILY / MONTHLY ACTIVE PATIENT VOLUME (DAP / MAP)
    # ---------------------------------------------------------
    r2_col1, r2_col2 = st.columns([2.2, 1])

    with r2_col1:
        st.markdown("##### 📈 Active Patient Volume Trends (DAP / MAP)")
        
        # Controls for switching granularity
        time_frame = st.radio(
            "Select View Granularity:",
            options=["Monthly Active Patients (MAP)", "Daily Active Patients (DAP)"],
            horizontal=True,
            key="active_patient_granularity"
        )

        df_active = df_clients.dropna(subset=['regDate']).copy()

        if "Daily" in time_frame:
            df_active['TimePeriod'] = df_active['regDate'].dt.date
            x_title = "Date"
        else:
            df_active['TimePeriod'] = df_active['regDate'].dt.to_period('M').dt.to_timestamp()
            x_title = "Month"

        active_counts = df_active.groupby('TimePeriod')['_id'].nunique().reset_index(name='Unique Active Patients')

        fig_active = px.line(
            active_counts,
            x='TimePeriod',
            y='Unique Active Patients',
            markers=True,
            line_shape='spline',
            color_discrete_sequence=['#00E5FF']
        )
        fig_active.update_traces(
            line=dict(width=3),
            marker=dict(size=6, symbol='circle', color='#FFFFFF', line=dict(width=2, color='#00E5FF'))
        )
        fig_active.update_layout(
            height=320,
            margin=dict(l=10, r=10, t=20, b=10),
            xaxis_title=x_title,
            yaxis_title="Active Patients",
            hovermode="x unified"
        )
        st.plotly_chart(fig_active, use_container_width=True)

    with r2_col2:
        st.markdown("##### 🔄 Patient Lifecycle Engagement")
        type_counts = df_clients['patientType'].value_counts().reset_index()
        type_counts.columns = ['Engagement Type', 'Count']

        fig_type = px.pie(
            type_counts,
            names='Engagement Type',
            values='Count',
            hole=0.55,
            color_discrete_map={'Existing Patient': '#7E57C2', 'New Registration': '#26A69A'}
        )
        fig_type.update_traces(textposition='inside', textinfo='percent+label')
        fig_type.update_layout(height=360, showlegend=False, margin=dict(l=10, r=10, t=20, b=10))
        st.plotly_chart(fig_type, use_container_width=True)

    # ---------------------------------------------------------
    # 4. PATIENT DIRECTORY ROSTER
    # ---------------------------------------------------------
    st.markdown("---")
    st.markdown("##### 📋 Patient Master Roster & Contact Directory")

    display_df = df_clients[[
        'regDate', 'patientName', 'gender', 'ageGroup', 'coverageType', 'hmoProvider', 'facilityName', 'phone', 'address'
    ]].copy()

    # Fill NaN age groups for directory listing display
    display_df['ageGroup'] = display_df['ageGroup'].fillna("Unrecorded")

    st.dataframe(
        display_df,
        column_config={
            "regDate": st.column_config.DatetimeColumn("Registration Date", format="DD/MM/YYYY HH:mm"),
            "patientName": "Patient Full Name",
            "gender": "Gender",
            "ageGroup": "Demographic Cohort",
            "coverageType": "Coverage Model",
            "hmoProvider": "HMO / Provider",
            "facilityName": "Registered Facility",
            "phone": "Phone Number",
            "address": "Residential Address"
        },
        use_container_width=True,
        height=380
    )