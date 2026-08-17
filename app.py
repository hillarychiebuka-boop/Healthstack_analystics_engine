import streamlit as st
import pandas as pd
import os
import sys

# Append the project root path so modules are found consistently
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 1. Page Config Setup
st.set_page_config(
    page_title="HealthStack Solutions | Executive Analytics Engine",
    page_icon="🛡️",
    layout="wide"
)

# 2. Module Imports (Single, Clean Route)
from modules.filters import get_sidebar_filters
from modules.logins import load_engagement_data, load_hourly_data, render_engagement_tab
from modules.appointments import load_appointments_data, load_appointment_types, render_queue_tab
from modules.clinical import load_clinical_consultations, render_clinical_tab
from modules.security import load_security_anomalies, render_security_tab
from modules.financials import load_financial_data, render_financials_tab

# 3. Header Setup
st.title("🛡️ HealthStack Solutions — Executive Analytics Engine")
st.markdown("Real-time operational metrics across User Engagement, Patient Queue Operations, Clinical Consultations, Security Governance, and Executive Financials.")

# 4. Data Preloading Across Modules
df_logins = load_engagement_data()
df_appointments = load_appointments_data()
df_appt_types = load_appointment_types()
df_consults = load_clinical_consultations()
df_anomalies = load_security_anomalies()
df_financials = load_financial_data()

# 5. Sidebar Filter Execution
selected_facility = get_sidebar_filters(df_logins, df_appointments, df_consults, df_financials)

# 6. Global Filtering Application
if selected_facility != "All Facilities":
    filtered_logins = df_logins[df_logins['facility'] == selected_facility] if not df_logins.empty and 'facility' in df_logins.columns else pd.DataFrame()
    filtered_appts = df_appointments[df_appointments['facility'] == selected_facility] if not df_appointments.empty and 'facility' in df_appointments.columns else pd.DataFrame()
    filtered_types = df_appt_types[df_appt_types['facility'] == selected_facility] if not df_appt_types.empty and 'facility' in df_appt_types.columns else pd.DataFrame()
    filtered_consults = df_consults[df_consults['facilityName'] == selected_facility] if not df_consults.empty and 'facilityName' in df_consults.columns else pd.DataFrame()
    filtered_anomalies = df_anomalies[df_anomalies['facility'] == selected_facility] if not df_anomalies.empty and 'facility' in df_anomalies.columns else pd.DataFrame()
    filtered_financials = df_financials[df_financials['facilityName'] == selected_facility] if not df_financials.empty and 'facilityName' in df_financials.columns else pd.DataFrame()
else:
    filtered_logins = df_logins.copy()
    filtered_appts = df_appointments.copy()
    filtered_types = df_appt_types.copy()
    filtered_consults = df_consults.copy()
    filtered_anomalies = df_anomalies.copy()
    filtered_financials = df_financials.copy()

df_hourly = load_hourly_data(selected_facility)

# 7. Dashboard Tabs Orchestration
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Logins & User Engagement", 
    "📅 Appointments & Queue Engine", 
    "🩺 Outpatients & Clinical Encounters",
    "🛡️ Security & Anomaly Center",
    "💳 Financial & Revenue Insights"
])

with tab1:
    render_engagement_tab(filtered_logins, df_hourly, filtered_anomalies, selected_facility)

with tab2:
    render_queue_tab(filtered_appts, filtered_types, selected_facility)

with tab3:
    render_clinical_tab(filtered_consults, selected_facility)

with tab4:
    render_security_tab(filtered_anomalies, selected_facility)

with tab5:
    render_financials_tab(filtered_financials, selected_facility)