import streamlit as st

def get_sidebar_filters(df_logins, df_appointments, df_consults, df_financials=None, df_inventory=None, df_sales=None, df_lab=None, df_clients=None):
    all_facilities = set()
    
    if not df_logins.empty and 'facility' in df_logins.columns:
        all_facilities.update([f for f in df_logins['facility'].dropna().unique() if not str(f).startswith("602") and not str(f).startswith("605")])
    if not df_appointments.empty and 'facility' in df_appointments.columns:
        all_facilities.update([f for f in df_appointments['facility'].dropna().unique() if not str(f).startswith("602") and not str(f).startswith("605")])
    if not df_consults.empty and 'facilityName' in df_consults.columns:
        all_facilities.update([f for f in df_consults['facilityName'].dropna().unique() if not str(f).startswith("602") and not str(f).startswith("605")])
    if df_financials is not None and not df_financials.empty and 'facilityName' in df_financials.columns:
        all_facilities.update([f for f in df_financials['facilityName'].dropna().unique() if not str(f).startswith("602") and not str(f).startswith("605")])
    if df_inventory is not None and not df_inventory.empty and 'facilityName' in df_inventory.columns:
        all_facilities.update([f for f in df_inventory['facilityName'].dropna().unique() if not str(f).startswith("602") and not str(f).startswith("605")])
    if df_sales is not None and not df_sales.empty and 'facilityName' in df_sales.columns:
        all_facilities.update([f for f in df_sales['facilityName'].dropna().unique() if not str(f).startswith("602") and not str(f).startswith("605")])
    if df_lab is not None and not df_lab.empty and 'facilityName' in df_lab.columns:
        all_facilities.update([f for f in df_lab['facilityName'].dropna().unique() if not str(f).startswith("602") and not str(f).startswith("605")])
    if df_clients is not None and not df_clients.empty and 'facilityName' in df_clients.columns:
        all_facilities.update([f for f in df_clients['facilityName'].dropna().unique() if not str(f).startswith("602") and not str(f).startswith("605")])

    # Extract all unique facility names from the raw DataFrame
    facility_list = sorted([str(f) for f in all_facilities if str(f).strip() != ""])

    # Ensure "All Facilities" is always the first option and always defined.
    options = ["All Facilities"] + facility_list if facility_list else ["All Facilities"]

    # Adding index=0 forces Streamlit to default to "All Facilities"
    selected_facility = st.sidebar.selectbox(
        "Select Target Facility",
        options=options,
        index=0,
        key="facility_filter_v2"  # Changing key forces Streamlit to discard old session memory
    )

    return selected_facility
