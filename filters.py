import streamlit as st

def get_sidebar_filters(df_logins, df_appointments, df_consults, df_financials=None):
    all_facilities = set()
    
    if not df_logins.empty and 'facility' in df_logins.columns:
        all_facilities.update([f for f in df_logins['facility'].dropna().unique() if not str(f).startswith("602") and not str(f).startswith("605")])
    if not df_appointments.empty and 'facility' in df_appointments.columns:
        all_facilities.update([f for f in df_appointments['facility'].dropna().unique() if not str(f).startswith("602") and not str(f).startswith("605")])
    if not df_consults.empty and 'facilityName' in df_consults.columns:
        all_facilities.update([f for f in df_consults['facilityName'].dropna().unique() if not str(f).startswith("602") and not str(f).startswith("605")])
    if df_financials is not None and not df_financials.empty and 'facilityName' in df_financials.columns:
        all_facilities.update([f for f in df_financials['facilityName'].dropna().unique() if not str(f).startswith("602") and not str(f).startswith("605")])

    facility_list = ["All Facilities"] + sorted(list(all_facilities))

    st.sidebar.header("🕹️ Filter & Global Settings")
    selected_facility = st.sidebar.selectbox(
        "Select Target Facility", 
        options=facility_list, 
        key="global_facility_selector"
    )
    return selected_facility