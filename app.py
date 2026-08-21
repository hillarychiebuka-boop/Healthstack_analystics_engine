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
from db import (
    load_inventory_data, load_pharmacy_sales, load_laboratory_data, 
    load_client_engagement_data, apply_date_filter
)
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

# 5. Sidebar Filter Execution (Facility + Time Horizon)
selected_facility, selected_duration = get_sidebar_filters(
    df_logins, df_appointments, df_consults, df_financials, df_inventory, df_sales, df_lab, df_clients
)

# 6. Global Facility Filtering Application
def filter_by_facility(df, selected_fac, col_name='facilityName'):
    if df.empty or selected_fac == "All Facilities":
        return df.copy()
    
    target_col = col_name if col_name in df.columns else ('facility' if 'facility' in df.columns else None)
    if not target_col:
        return df.copy()
        
    return df[df[target_col].astype(str).str.strip().str.lower() == selected_fac.strip().lower()].copy()

filtered_logins = filter_by_facility(df_logins, selected_facility, 'facility')
filtered_appts = filter_by_facility(df_appointments, selected_facility, 'facility')
filtered_types = filter_by_facility(df_appt_types, selected_facility, 'facility')
filtered_consults = filter_by_facility(df_consults, selected_facility, 'facilityName')
filtered_anomalies = filter_by_facility(df_anomalies, selected_facility, 'facility')
filtered_financials = filter_by_facility(df_financials, selected_facility, 'facilityName')
filtered_inventory = filter_by_facility(df_inventory, selected_facility, 'facilityName')
filtered_sales = filter_by_facility(df_sales, selected_facility, 'facilityName')
filtered_lab = filter_by_facility(df_lab, selected_facility, 'facilityName')
filtered_clients = filter_by_facility(df_clients, selected_facility, 'facilityName')

# 7. Global Time Horizon / Duration Filtering Application
filtered_logins = apply_date_filter(filtered_logins, selected_duration, 'createdAt')
filtered_appts = apply_date_filter(filtered_appts, selected_duration, 'createdAt')
filtered_consults = apply_date_filter(filtered_consults, selected_duration, 'createdAt')
filtered_anomalies = apply_date_filter(filtered_anomalies, selected_duration, 'createdAt')
filtered_financials = apply_date_filter(filtered_financials, selected_duration, 'createdAt')
filtered_sales = apply_date_filter(filtered_sales, selected_duration, 'transactionDate')
filtered_lab = apply_date_filter(filtered_lab, selected_duration, 'orderDate')
filtered_clients = apply_date_filter(filtered_clients, selected_duration, 'regDate')

df_hourly = load_hourly_data(selected_facility)

# 8. Dashboard Tabs Orchestration
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
