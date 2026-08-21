import streamlit as st
import pandas as pd
import os
import sys

# Append project root path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 1. Page Config Setup
st.set_page_config(
    page_title="HealthStack Solutions | Executive Analytics Engine",
    page_icon="🛡️",
    layout="wide"
)

# 2. Database & Module Imports
from db import load_inventory_data, load_pharmacy_sales, load_laboratory_data, load_client_engagement_data
from modules.filters import get_sidebar_filters
from modules.logins import load_engagement_data, load_hourly_data, render_engagement_tab
from modules.appointments import load_appointments_data, load_appointment_types, render_queue_tab
from modules.clinical import load_clinical_consultations, render_clinical_tab
from modules.security import load_security_anomalies, render_security_tab
from modules.financials import load_financial_data, render_financials_tab
from modules.pharmacy import render_pharmacy_tab
from modules.laboratory import render_laboratory_tab
from modules.patients_engagement import render_patient_engagement_tab

# 3. Header Setup
st.title("🛡️ HealthStack Solutions — Executive Analytics Engine")
st.markdown("Real-time operational metrics across engagement, appointments, clinicals, security, financials, pharmacy, laboratory diagnostics, and patient registrations.")

# 4. Data Preloading Across Modules
df_logins = load_engagement_data()
df_appointments = load_appointments_data()
df_appt_types = load_appointment_types()
df_consults = load_clinical_consultations()
df_anomalies = load_security_anomalies()
df_financials = load_financial_data()
df_inventory = load_inventory_data()
df_sales = load_pharmacy_sales()
df_lab = load_laboratory_data()
df_clients = load_client_engagement_data()

# 5. Sidebar Filter Execution
selected_facility = get_sidebar_filters(
    df_logins, df_appointments, df_consults, df_financials, df_inventory, df_sales, df_lab, df_clients
)

# 6. Global Filtering Application
if selected_facility != "All Facilities":
    filtered_logins = df_logins[df_logins['facility'] == selected_facility] if not df_logins.empty and 'facility' in df_logins.columns else pd.DataFrame()
    filtered_appts = df_appointments[df_appointments['facility'] == selected_facility] if not df_appointments.empty and 'facility' in df_appointments.columns else pd.DataFrame()
    filtered_types = df_appt_types[df_appt_types['facility'] == selected_facility] if not df_appt_types.empty and 'facility' in df_appt_types.columns else pd.DataFrame()
    filtered_consults = df_consults[df_consults['facilityName'] == selected_facility] if not df_consults.empty and 'facilityName' in df_consults.columns else pd.DataFrame()
    filtered_anomalies = df_anomalies[df_anomalies['facility'] == selected_facility] if not df_anomalies.empty and 'facility' in df_anomalies.columns else pd.DataFrame()
    filtered_financials = df_financials[df_financials['facilityName'] == selected_facility] if not df_financials.empty and 'facilityName' in df_financials.columns else pd.DataFrame()
    filtered_inventory = df_inventory[df_inventory['facilityName'] == selected_facility] if not df_inventory.empty and 'facilityName' in df_inventory.columns else pd.DataFrame()
    filtered_sales = df_sales[df_sales['facilityName'] == selected_facility] if not df_sales.empty and 'facilityName' in df_sales.columns else pd.DataFrame()
    filtered_lab = df_lab[df_lab['facilityName'] == selected_facility] if not df_lab.empty and 'facilityName' in df_lab.columns else pd.DataFrame()
    filtered_clients = df_clients[df_clients['facilityName'] == selected_facility] if not df_clients.empty and 'facilityName' in df_clients.columns else pd.DataFrame()
else:
    filtered_logins = df_logins.copy()
    filtered_appts = df_appointments.copy()
    filtered_types = df_appt_types.copy()
    filtered_consults = df_consults.copy()
    filtered_anomalies = df_anomalies.copy()
    filtered_financials = df_financials.copy()
    filtered_inventory = df_inventory.copy()
    filtered_sales = df_sales.copy()
    filtered_lab = df_lab.copy()
    filtered_clients = df_clients.copy()

df_hourly = load_hourly_data(selected_facility)

# 7. Dashboard Tabs Orchestration
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
    "📊 Logins & User Engagement", 
    "📅 Appointments & Queue Engine", 
    "🩺 Outpatients & Clinical Encounters",
    "🛡️ Security & Anomaly Center",
    "💳 Financial & Revenue Insights",
    "💊 Pharmacy & Inventory Engine",
    "🔬 Laboratory & Diagnostics Engine",
    "👥 Patient Engagement & Registrations"
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

with tab6:
    render_pharmacy_tab(filtered_inventory, filtered_sales, selected_facility)

with tab7:
    render_laboratory_tab(filtered_lab, selected_facility)

with tab8:
    render_patient_engagement_tab(filtered_clients, selected_facility)
