import streamlit as st
from pymongo import MongoClient
import pandas as pd
import numpy as np
import os

MONGO_URI = st.secrets.get("MONGO_URI", os.getenv("MONGO_URI"))

# =========================================================
# CENTRALIZED TARGET FACILITY WHITELIST & MAPPING
# =========================================================
TARGET_FACILITIES_RAW = [
    "foremost base hospital",
    "TRISTATE HEALTHCARE SYSTEM",
    "FIRST HEALTH DSIL",
    "GENERAL HOSPITAL CALABAR",
    "VBFC",
    "Purelife Health",
    "RAINBOW SCANS",
    "COMPASS HEALTH-LARRYKEN",
    "COMPASS HEALTH-THE NEST MONT.",
    "COMPASS HEALTH-THE BRIDGE",
    "STATE HOUSE MEDICAL CENTER",
    "OBUDU GERMAN HOSPITAL"
]

# Case-insensitive lookup dict mapping lowercase -> exact target casing
TARGET_FACILITIES_CLEAN = {f.strip().lower(): f for f in TARGET_FACILITIES_RAW}

def sanitize_and_filter_facilities(df, facility_col='facilityName'):
    """
    Filters DataFrame to retain only target whitelist facilities,
    normalizing name casing for standard reporting.
    """
    if df.empty or facility_col not in df.columns:
        return df

    # Normalize column for matching
    temp_series = df[facility_col].astype(str).str.strip().str.lower()
    
    # Filter dataframe against whitelist keys
    df_filtered = df[temp_series.isin(TARGET_FACILITIES_CLEAN.keys())].copy()

    # Apply standardized display casing
    df_filtered[facility_col] = temp_series[temp_series.isin(TARGET_FACILITIES_CLEAN.keys())].map(
        lambda x: TARGET_FACILITIES_CLEAN.get(x, x)
    )

    return df_filtered


def apply_date_filter(df, duration_option, date_col='createdAt'):
    """
    Filters DataFrame dynamically based on time horizon selection.
    """
    if df.empty or date_col not in df.columns or duration_option == "All Time":
        return df

    now = pd.Timestamp.now(tz='UTC')
    df[date_col] = pd.to_datetime(df[date_col], errors='coerce', utc=True)
    
    if duration_option == "Last 7 Days":
        cutoff = now - pd.Timedelta(days=7)
    elif duration_option == "Last 30 Days":
        cutoff = now - pd.Timedelta(days=30)
    elif duration_option == "Quarterly (Last 90 Days)":
        cutoff = now - pd.Timedelta(days=90)
    elif duration_option == "Yearly (Last 365 Days)":
        cutoff = now - pd.Timedelta(days=365)
    else:
        return df

    return df[df[date_col] >= cutoff]


@st.cache_resource
def get_mongo_client():
    return MongoClient(
        MONGO_URI,
        datetime_conversion="DATETIME_AUTO",
        socketTimeoutMS=600000,
        connectTimeoutMS=60000,
        maxIdleTimeMS=120000
    )

client = get_mongo_client()
db = client['healthstackv2']

@st.cache_data(ttl=600)
def load_inventory_data():
    pipeline = [
        {"$match": {"facility": {"$ne": None}}},
        {"$lookup": {"from": "facilities", "localField": "facility", "foreignField": "_id", "as": "facilityDetails"}},
        {"$unwind": {"path": "$facilityDetails", "preserveNullAndEmptyArrays": True}},
        {"$project": {
            "_id": 1,
            "itemName": {"$ifNull": ["$name", "Unspecified Medication"]},
            "facilityId": "$facility",
            "facilityName": {
                "$ifNull": ["$facilityDetails.name", "$facilityDetails.facilityName", "$facilityName", "Unknown Facility"]
            },
            "baseUnit": {"$ifNull": ["$baseunit", "Unit"]},
            "quantity": {"$convert": {"input": "$quantity", "to": "double", "onError": 0, "onNull": 0}},
            "reorderLevel": {"$convert": {"input": "$reorder_level", "to": "double", "onError": 10, "onNull": 10}},
            "costPrice": {"$convert": {"input": "$costprice", "to": "double", "onError": 0, "onNull": 0}},
            "sellingPrice": {"$convert": {"input": "$sellingprice", "to": "double", "onError": 0, "onNull": 0}},
            "rawStockValue": {"$convert": {"input": "$stockvalue", "to": "double", "onError": 0, "onNull": 0}}
        }}
    ]
    raw_df = pd.DataFrame(list(db.inventories.aggregate(pipeline)))
    if raw_df.empty:
        return pd.DataFrame()
    
    cleaned = raw_df.copy()
    cleaned['quantity'] = cleaned['quantity'].apply(lambda x: max(0, x))
    cleaned['isLowStock'] = cleaned['quantity'] <= cleaned['reorderLevel']
    cleaned['facilityName'] = cleaned['facilityName'].astype(str).str.strip()
    
    cleaned['computedStockValue'] = cleaned.apply(
        lambda r: r['rawStockValue'] if r['rawStockValue'] > 0 else (r['quantity'] * r['sellingPrice']), 
        axis=1
    )
    return sanitize_and_filter_facilities(cleaned, 'facilityName')

@st.cache_data(ttl=600)
def load_pharmacy_sales():
    pipeline = [
        {"$match": {"productitems": {"$exists": True, "$type": "array", "$ne": []}, "facility": {"$ne": None}}},
        {"$unwind": {"path": "$productitems", "preserveNullAndEmptyArrays": False}},
        {"$lookup": {"from": "facilities", "localField": "facility", "foreignField": "_id", "as": "facilityDetails"}},
        {"$unwind": {"path": "$facilityDetails", "preserveNullAndEmptyArrays": True}},
        {"$project": {
            "_id": 1,
            "rawDate": "$createdAt",
            "altDate": "$date",
            "documentNo": {"$ifNull": ["$documentNo", "N/A"]},
            "facilityId": "$facility",
            "facilityName": {
                "$ifNull": ["$facilityDetails.name", "$facilityDetails.facilityName", "$facilityName", "Unknown Facility"]
            },
            "sourceClient": {"$ifNull": ["$source", "Walk-in Patient"]},
            "itemName": {"$ifNull": ["$productitems.name", "Unspecified Drug"]},
            "qtySold": {"$convert": {"input": "$productitems.quantity", "to": "double", "onError": 1, "onNull": 1}},
            "costPrice": {"$convert": {"input": "$productitems.costprice", "to": "double", "onError": 0, "onNull": 0}},
            "sellingPrice": {"$convert": {"input": "$productitems.sellingprice", "to": "double", "onError": 0, "onNull": 0}},
            "amount": {"$convert": {"input": "$productitems.amount", "to": "double", "onError": 0, "onNull": 0}}
        }}
    ]
    raw_df = pd.DataFrame(list(db.productentries.aggregate(pipeline)))
    if raw_df.empty:
        return pd.DataFrame()
    
    cleaned = raw_df.copy()
    cleaned['transactionDate'] = pd.to_datetime(cleaned['rawDate'].fillna(cleaned['altDate']), errors='coerce', utc=True)
    
    max_now = pd.Timestamp.now(tz='UTC')
    cleaned = cleaned[cleaned['transactionDate'] <= max_now]
    
    cleaned['unitPrice'] = cleaned.apply(
        lambda r: r['sellingPrice'] if r['sellingPrice'] > 0 else (r['amount'] / r['qtySold'] if r['qtySold'] > 0 else 0),
        axis=1
    )
    cleaned['lineRevenue'] = cleaned.apply(
        lambda r: r['amount'] if r['amount'] > 0 else (r['qtySold'] * r['unitPrice']),
        axis=1
    )
    cleaned['lineProfit'] = cleaned['lineRevenue'] - (cleaned['qtySold'] * cleaned['costPrice'])
    cleaned['facilityName'] = cleaned['facilityName'].astype(str).str.strip()
    cleaned = cleaned.sort_values('transactionDate', ascending=False)
    
    return sanitize_and_filter_facilities(cleaned, 'facilityName')

@st.cache_data(ttl=600)
def load_laboratory_data():
    pipeline = [
        {
            "$match": {
                "$and": [
                    {
                        "$or": [
                            { "documentType": { "$regex": "lab|diagnostic|investigation|test|result", "$options": "i" } },
                            { "documentname": { "$regex": "lab|diagnostic|investigation|test|result|malaria|pcv|widal|urinalysis|chemistry|hematology|spirometry", "$options": "i" } }
                        ]
                    },
                    { "documentname": { "$not": { "$regex": "doctor note|clinical note|nursing note|admission note|discharge note", "$options": "i" } } }
                ]
            }
        },
        {"$lookup": {"from": "facilities", "localField": "facility", "foreignField": "_id", "as": "facilityDetails"}},
        {"$unwind": {"path": "$facilityDetails", "preserveNullAndEmptyArrays": True}},
        {"$project": {
            "_id": 1,
            "documentName": "$documentname",
            "documentType": "$documentType",
            "facilityName": {
                "$ifNull": ["$facilityDetails.name", "$facilityDetails.facilityName", "$facilityname", "Unknown Facility"]
            },
            "status": { "$ifNull": ["$status", "pending"] },
            "orderDate": "$createdAt",
            "resultDate": "$updatedAt",
            "testName": {
                "$ifNull": ["$documentdetail.Investigation", "$documentname", "Unspecified Diagnostic Test"]
            },
            "rawDiagnosis": {
                "$ifNull": ["$documentdetail.Diagnosis", "$documentdetail.Finding", "Unspecified Condition"]
            },
            "doctor": {"$ifNull": ["$createdByname", "Unassigned Clinician"]}
        }}
    ]
    raw_df = pd.DataFrame(list(db.clinicaldocuments.aggregate(pipeline)))
    if raw_df.empty:
        return pd.DataFrame()

    cleaned = raw_df.copy()
    cleaned['orderDate'] = pd.to_datetime(cleaned['orderDate'], errors='coerce', utc=True)
    cleaned['resultDate'] = pd.to_datetime(cleaned['resultDate'], errors='coerce', utc=True)
    max_now = pd.Timestamp.now(tz='UTC')
    cleaned = cleaned[cleaned['orderDate'] <= max_now]

    cleaned['tat_hours'] = (cleaned['resultDate'] - cleaned['orderDate']).dt.total_seconds() / 3600.0
    cleaned['tat_hours'] = cleaned['tat_hours'].apply(lambda x: x if (pd.notnull(x) and x >= 0) else np.nan)
    cleaned['valid_tat_hours'] = cleaned['tat_hours'].apply(lambda x: x if (pd.notnull(x) and x > 0.01) else np.nan)
    
    cleaned['isFulfilled'] = cleaned['status'].str.lower().isin(['completed', 'fulfilled', 'verified', 'closed'])
    cleaned['testName'] = cleaned['testName'].astype(str).str.replace(r"[\[\]']", "", regex=True).str.strip().str.title()
    cleaned['facilityName'] = cleaned['facilityName'].astype(str).str.strip()
    
    patterns = [
        (r'(?i).*fbc.*mp.*|.*mp.*fbc.*', 'FBC & Malaria Parasite'),
        (r'(?i)^mp$|^mp result$', 'Malaria Parasite Result'),
        (r'(?i)^fbc$|^fbc result$', 'Full Blood Count'),
        (r'(?i)^pcv$|^pcv result$', 'Packed Cell Volume (PCV)'),
        (r'(?i).*spt.*', 'Sputum Test Result'),
        (r'(?i).*rvs.*hbsag.*', 'RVS / HBsAg / Anti-HCV / VDRL Panel')
    ]

    for pattern, replacement in patterns:
        cleaned['testName'] = cleaned['testName'].str.replace(pattern, replacement, regex=True)
    
    cleaned = cleaned[~cleaned['testName'].isin(['', 'Nan', 'None', 'Doctor Note', 'Clinical Note', 'Nursing Note'])]
    cleaned = cleaned.sort_values('orderDate', ascending=False)
    
    return sanitize_and_filter_facilities(cleaned, 'facilityName')

@st.cache_data(ttl=600)
def load_client_engagement_data():
    pipeline = [
        {"$match": {"facility": {"$ne": None}}},
        {"$lookup": {"from": "facilities", "localField": "facility", "foreignField": "_id", "as": "facilityDetails"}},
        {"$unwind": {"path": "$facilityDetails", "preserveNullAndEmptyArrays": True}},
        {"$project": {
            "_id": 1,
            "firstName": {"$ifNull": ["$firstname", ""]},
            "lastName": {"$ifNull": ["$lastname", ""]},
            "gender": {
                "$cond": [
                    {"$in": ["$gender", ["", None]]},
                    "Unspecified",
                    "$gender"
                ]
            },
            "maritalStatus": {
                "$cond": [
                    {"$in": ["$maritalstatus", ["", None]]},
                    "Unspecified",
                    "$maritalstatus"
                ]
            },
            "facilityName": {
                "$ifNull": ["$facilityDetails.name", "$facilityDetails.facilityName", "$facilityName", "Unknown Facility"]
            },
            "dob": "$dob",
            "phone": {"$ifNull": ["$phone", "N/A"]},
            "address": {"$ifNull": ["$address", "Unspecified"]},
            "createdAt": "$createdAt",
            "paymentInfo": "$paymentinfo"
        }}
    ]

    raw_docs = list(db.clients.aggregate(pipeline))
    if not raw_docs:
        return pd.DataFrame()

    df = pd.DataFrame(raw_docs)

    # Clean Names & Facility Formatting
    df['patientName'] = (df['firstName'].astype(str).str.strip() + " " + df['lastName'].astype(str).str.strip()).str.title()
    df.loc[df['patientName'].str.strip() == "", 'patientName'] = "Anonymous Patient"
    df['facilityName'] = df['facilityName'].astype(str).str.strip()

    # Gender Normalization
    df['gender'] = df['gender'].astype(str).str.upper().str.strip()
    df.loc[~df['gender'].isin(['MALE', 'FEMALE']), 'gender'] = 'UNSPECIFIED'

    # Registration Date & Timeline Features
    ref_date = pd.Timestamp.now(tz='UTC')
    df['regDate'] = pd.to_datetime(df['createdAt'], errors='coerce', utc=True)
    
    # Age Calculation & Cleaning
    df['dob_clean'] = pd.to_datetime(df['dob'], errors='coerce', utc=True)
    valid_dob = (df['dob_clean'].dt.year >= 1900) & (df['dob_clean'].dt.year <= ref_date.year)
    df['dob_clean'] = df['dob_clean'].where(valid_dob, pd.NaT)
    
    df['age'] = (ref_date - df['dob_clean']).dt.days / 365.25
    df.loc[(df['age'] < 0) | (df['age'] > 115), 'age'] = np.nan

    def assign_cohort(age):
        if pd.isna(age):
            return np.nan
        elif age < 2:
            return "Infant (0-1)"
        elif age <= 12:
            return "Pediatric (2-12)"
        elif age <= 24:
            return "Youth (13-24)"
        elif age <= 59:
            return "Adult (25-59)"
        else:
            return "Senior (60+)"

    df['ageGroup'] = df['age'].apply(assign_cohort)

    # New vs Returning Patient Flag (Registered in Last 30 Days)
    thirty_days_ago = ref_date - pd.Timedelta(days=30)
    df['patientType'] = df['regDate'].apply(lambda x: 'New Registration' if pd.notnull(x) and x >= thirty_days_ago else 'Existing Patient')

    # Payer Coverage Profile
    def extract_coverage(pay_list):
        if isinstance(pay_list, list) and len(pay_list) > 0:
            modes = [str(p.get('paymentmode', '')).upper() for p in pay_list if isinstance(p, dict)]
            orgs = [str(p.get('organizationName', '')).strip() for p in pay_list if isinstance(p, dict) and p.get('organizationName')]
            
            hmo_name = orgs[0] if len(orgs) > 0 and orgs[0] not in ['None', ''] else 'Direct HMO'
            
            if 'HMO' in modes or 'INSURANCE' in modes:
                return pd.Series(['HMO Covered', hmo_name])
            elif 'CASH' in modes:
                return pd.Series(['Cash Out-of-Pocket', 'Self-Pay'])
        return pd.Series(['Cash Out-of-Pocket', 'Self-Pay'])

    df[['coverageType', 'hmoProvider']] = df['paymentInfo'].apply(extract_coverage)
    df['facilityName'] = df['facilityName'].fillna('Unspecified Facility').astype(str).str.strip()

    df = df.sort_values('regDate', ascending=False)
    return sanitize_and_filter_facilities(df, 'facilityName')
