import re
import pandas as pd

# Canonical Master Department Definitions
CANONICAL_DEPARTMENTS = [
    "General Outpatient (GOPD)",
    "Pharmacy Services",
    "Laboratory & Diagnostics",
    "Radiology & Imaging",
    "Inpatient & Nursing Wards",
    "Surgical Services / OT",
    "Obstetrics & Gynecology (O&G)",
    "Pediatrics & Child Health",
    "Cardiology",
    "Emergency & Casualty",
    "Intensive Care Unit (ICU)",
    "Front Desk & Administration",
    "Ophthalmology",
    "Dental Clinic",
    "ENT Medicine",
    "Orthopaedics",
    "Family Medicine",
    "Physiotherapy",
    "Urology",
    "Specialized / Presidential Wing",
    "Unassigned / Other"
]

def map_department(raw_dept: str) -> str:
    """
    Maps raw database department/location strings into standardized canonical departments.
    Unmatched or empty records fall cleanly under 'Unassigned / Other'.
    """
    if not raw_dept or pd.isna(raw_dept):
        return "Unassigned / Other"

    s = str(raw_dept).strip().lower()

    if s in ["undefined", "unknown", "none", "", "null"]:
        return "Unassigned / Other"

    # 1. Emergency & Casualty (ER, Casualty, Triage variants)
    if any(k in s for k in ["emergency", "er", "casualty", "casuality"]):
        return "Emergency & Casualty"

    # 2. Cardiology & Cardiac Care
    if any(k in s for k in ["cardiology", "cardiac"]):
        return "Cardiology"

    # 3. Intensive Care Unit (ICU)
    if any(k in s for k in ["icu", "intensive care"]):
        return "Intensive Care Unit (ICU)"

    # 4. Pediatrics & Child Health
    if any(k in s for k in ["pediatric", "paediatric", "child health", "neonatal", "room 3"]):
        return "Pediatrics & Child Health"

    # 5. Surgical Services / Operating Theatre
    if any(k in s for k in ["surgery", "surgical", "ot", "operating theatre", "theatre", "theater"]):
        return "Surgical Services / OT"

    # 6. Obstetrics & Gynecology / ANC
    if any(k in s for k in ["obstetrics", "gynecology", "gynaecology", "gyn", "o&g", "maternity", "antenatal", "anc"]):
        return "Obstetrics & Gynecology (O&G)"

    # 7. Front Desk & Administration
    if any(k in s for k in ["frontdesk", "front desk", "reception", "intake"]):
        return "Front Desk & Administration"

    # 8. Ophthalmology & Eye Care
    if any(k in s for k in ["ophthalmology", "eye", "optometry"]):
        return "Ophthalmology"

    # 9. Dental Care
    if any(k in s for k in ["dental", "oral"]):
        return "Dental Clinic"

    # 10. ENT Medicine
    if any(k in s for k in ["ent", "ear nose", "otorhinolaryngology"]):
        return "ENT Medicine"

    # 11. Orthopaedics
    if any(k in s for k in ["orthopaedic", "orthopedic", "bone"]):
        return "Orthopaedics"

    # 12. Family Medicine & General Outpatient
    if "family medicine" in s:
        return "Family Medicine"

    if any(k in s for k in ["gopd", "outpatient", "out-patient", "general outpatient", "opd", "clinic"]):
        return "General Outpatient (GOPD)"

    # 13. Pharmacy
    if any(k in s for k in ["pharmacy", "dispensing", "drugs"]):
        return "Pharmacy Services"

    # 14. Laboratory & Diagnostics
    if any(k in s for k in ["lab", "laboratory", "diagnostics", "pathology"]):
        return "Laboratory & Diagnostics"

    # 15. Radiology & Imaging
    if any(k in s for k in ["radiology", "imaging", "x-ray", "mri", "ct scan", "ultrasound"]):
        return "Radiology & Imaging"

    # 16. Inpatient & Wards
    if any(k in s for k in ["inpatient", "ward", "nursing", "admission", "nurse"]):
        return "Inpatient & Nursing Wards"

    # 17. Physiotherapy
    if any(k in s for k in ["physiotherapy", "physical therapy", "rehab"]):
        return "Physiotherapy"

    # 18. Urology
    if "urology" in s:
        return "Urology"

    # 19. Specialized Facilities / Outposts
    if any(k in s for k in ["presidential", "purelife", "tristate", "wing"]):
        return "Specialized / Presidential Wing"

    return "Unassigned / Other"

# Function Alias for Backwards Compatibility
map_raw_to_canonical_department = map_department


def standardize_department_dataframe(df: pd.DataFrame, dept_column: str = "department") -> pd.DataFrame:
    """
    Enriches a dataframe with 'canonical_department' while preserving 'raw_department'.
    """
    if df is None or df.empty:
        return df

    if dept_column in df.columns:
        df['raw_department'] = df[dept_column].fillna("Undefined").astype(str)
        df['canonical_department'] = df['raw_department'].apply(map_department)
    else:
        df['raw_department'] = "Undefined"
        df['canonical_department'] = "Unassigned / Other"

    return df


def extract_unique_departments(*dfs) -> list:
    """
    Extracts all unique canonical departments present across any provided DataFrames.
    Returns a deduplicated, sorted list starting with 'All Departments'.
    """
    unique_depts = set()
    dept_cols = [
        "canonical_department", "rawdepartment", "department", "dept_name", 
        "clinic", "unit", "specialty", "department_name", "location", 
        "locationname", "departmentname"
    ]

    for df in dfs:
        if df is not None and not df.empty:
            target_col = next((c for c in df.columns if str(c).lower().strip() in dept_cols), None)
            if target_col:
                if target_col == "canonical_department":
                    mapped = df[target_col].dropna().unique()
                else:
                    mapped = df[target_col].dropna().apply(map_department).unique()
                unique_depts.update(mapped)

    # Remove 'All Departments' if present in data values to avoid duplicate prepending
    cleaned_depts = [d for d in unique_depts if d != "All Departments"]
    sorted_departments = sorted(cleaned_depts)
    
    return ["All Departments"] + sorted_departments
