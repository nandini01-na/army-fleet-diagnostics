import streamlit as st

# ---------------------------------------------------------
# 1. PAGE CONFIG — MUST BE THE VERY FIRST STREAMLIT COMMAND
# ---------------------------------------------------------
st.set_page_config(
    page_title="Army Fleet Diagnostics",
    page_icon="🎖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state keys safely
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime
import re
import sqlite3
import hashlib
import sys
import os

# Set proper directory path
if getattr(sys, 'frozen', False):
    APP_DIR = os.path.dirname(sys.executable)
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))

DB_PATH = os.path.join(APP_DIR, "fleet_data.db")

# ---------------------------------------------------------
# 2. CUSTOM LOGIN SYSTEM
# ---------------------------------------------------------
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

USER_DB = {
    "commander1": {
        "name": "Unit Commander",
        "password_hash": hash_password("changeme123"),
        "role": "editor"
    },
    "tech1": {
        "name": "Field Technician",
        "password_hash": hash_password("changeme123"),
        "role": "viewer"
    }
}

def login_screen():
    st.title("🎖️ Army Fleet Diagnostics — Login")
    with st.form("login_form"):
        username_input = st.text_input("Username")
        password_input = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")

        if submitted:
            user = USER_DB.get(username_input)
            if user and user["password_hash"] == hash_password(password_input):
                st.session_state["logged_in"] = True
                st.session_state["username"] = username_input
                st.session_state["name"] = user["name"]
                st.session_state["role"] = user["role"]
                st.rerun()
            else:
                st.error("Username or password is incorrect")

def logout_button():
    if st.sidebar.button("🚪 Logout"):
        for key in ["logged_in", "username", "name", "role"]:
            st.session_state.pop(key, None)
        st.session_state["logged_in"] = False
        st.rerun()

if not st.session_state.get("logged_in", False):
    login_screen()
    st.stop()

username = st.session_state.get("username", "Officer")
name = st.session_state.get("name", "Commanding Officer")
user_role = st.session_state.get("role", "editor")

# ---------------------------------------------------------
# 3. DATABASE LAYER
# ---------------------------------------------------------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS defect_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            Unit TEXT, Nomenclature TEXT, Veh_BA_No TEXT,
            Dt_Induction TEXT, Dt_In TEXT, Dt_Out TEXT,
            KM_In INTEGER, KM_Out INTEGER,
            Defect TEXT, Repair_Activity TEXT,
            created_by TEXT, created_at TEXT
        )
    """)
    conn.commit()
    conn.close()

def load_all_records():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM defect_logs", conn)
    conn.close()
    return df

def insert_record(record: dict, created_by_user: str):
    conn = sqlite3.connect(DB_PATH)
    record = dict(record)
    record["created_by"] = created_by_user
    record["created_at"] = datetime.now().strftime("%d-%b-%Y %H:%M")
    cols = ", ".join(record.keys())
    placeholders = ", ".join(["?"] * len(record))
    conn.execute(f"INSERT INTO defect_logs ({cols}) VALUES ({placeholders})", list(record.values()))
    conn.commit()
    conn.close()

def seed_db_if_empty():
    existing = load_all_records()
    if len(existing) > 0:
        return
    baseline = get_base_fleet()
    conn = sqlite3.connect(DB_PATH)
    for _, row in baseline.iterrows():
        rec = row.to_dict()
        rec["created_by"] = "system_seed"
        rec["created_at"] = datetime.now().strftime("%d-%b-%Y %H:%M")
        cols = ", ".join(rec.keys())
        placeholders = ", ".join(["?"] * len(rec))
        conn.execute(f"INSERT INTO defect_logs ({cols}) VALUES ({placeholders})", list(rec.values()))
    conn.commit()
    conn.close()

# ---------------------------------------------------------
# 4. BASE FLEET DATASET
# ---------------------------------------------------------
@st.cache_data
def get_base_fleet():
    raw_data = [
        {"Unit": "Unit A", "Nomenclature": "2.5 TON", "Veh_BA_No": "19C-107753W", "Dt_Induction": "09-Jun-2021", "Dt_In": "26-Oct-2023", "Dt_Out": "28-Jan-2024", "KM_In": 22131, "KM_Out": 22137, "Defect": "AXLE NOISY, AIR FILTER DIRTY, RADIATOR LEAKING, HUB SEAL WORN OUT", "Repair_Activity": "REPAIRED, AIR FILTER NEW FITTED, RADIATOR ASSY NEW FITTED, HUB SEAL NEW FITTED"},
        {"Unit": "Unit A", "Nomenclature": "2.5 TON", "Veh_BA_No": "19C-107753W", "Dt_Induction": "09-Jun-2021", "Dt_In": "13-Nov-2023", "Dt_Out": "22-Feb-2024", "KM_In": 22238, "KM_Out": 22243, "Defect": "ROTARY SWITCH NOT WORK, ISOLETOR SWITCH NOT WORK, AIR FILTER DIRTY, CLUTCH HARD", "Repair_Activity": "ROTARY SWITCH REPAIRED, ISOLETOR SWITCH NEW FITTED, AIR FILTER NEW FITTED, CLUTCH ADJUSTED"},
        {"Unit": "Unit B", "Nomenclature": "2.5 TON", "Veh_BA_No": "19C-107906X", "Dt_Induction": "09-Jun-2021", "Dt_In": "06-Mar-2025", "Dt_Out": "08-Mar-2025", "KM_In": 30502, "KM_Out": 30509, "Defect": "AIR COMPRESSURE LEAK, BRAKE POOR", "Repair_Activity": "AIR COMPRESSOR CANEBLIZED FROM CL-V VEH, REAR BRAKE BOOSTER FITTED, BRAKE ADJUSTED"},
        {"Unit": "Unit B", "Nomenclature": "2.5 TON", "Veh_BA_No": "19C-107906X", "Dt_Induction": "09-Jun-2021", "Dt_In": "21-May-2025", "Dt_Out": "28-Jul-2025", "KM_In": 30732, "KM_Out": 30739, "Defect": "VEH PULLING POWER WEAK, SOLENOID SWITCH NOT WORK", "Repair_Activity": "CLUTCH PLATE & MASTER CYLINDER NEW FITTED, SOLENOID SWITCH NEW FITTED"},
        {"Unit": "Unit C", "Nomenclature": "2.5 TON", "Veh_BA_No": "19C-107906X", "Dt_Induction": "09-Jun-2021", "Dt_In": "15-Sep-2025", "Dt_Out": "15-Sep-2025", "KM_In": 31022, "KM_Out": 31028, "Defect": "DOOR GLASS MECHANISM NOT WORK, MAIN SWITCH NOT WORK, STEERING GEAR BOX OIL LEAKING", "Repair_Activity": "DOOR GLASS REPAIRED, CHANGE OVER SWITCH NEW FITTED, STEERING SEAL KIT ZF NEW FITTED"},
        {"Unit": "Unit D", "Nomenclature": "2.5 TON", "Veh_BA_No": "19C-107906X", "Dt_Induction": "09-Jun-2021", "Dt_In": "09-Jul-2026", "Dt_Out": "12-Jul-2026", "KM_In": 32237, "KM_Out": 32243, "Defect": "AXLE NOISY, PROPELLER SHAFT NOISY, DOOR LOCK NOT WORK", "Repair_Activity": "AXLE REPAIRED, PROPELLER SHAFT NUT FITTED, DOOR LOCK REPAIRED"},
        {"Unit": "Unit E", "Nomenclature": "2.5 TON", "Veh_BA_No": "22C-109902P", "Dt_Induction": "24-Feb-2022", "Dt_In": "13-Nov-2025", "Dt_Out": "16-Nov-2025", "KM_In": 10847, "KM_Out": 10849, "Defect": "ISOLATOR SWITCH NOT WORK, BRAKE POOR", "Repair_Activity": "ISOLATOR SWITCH REPAIRED, BRAKE ADJUSTED"},
        {"Unit": "Unit F", "Nomenclature": "ALS", "Veh_BA_No": "13D-192836W", "Dt_Induction": "20-Aug-2014", "Dt_In": "05-Sep-2023", "Dt_Out": "27-Oct-2023", "KM_In": 60740, "KM_Out": 60742, "Defect": "STARTING TROUBLE", "Repair_Activity": "INJECTOR OVERHAUL & FUEL FEED PUMP REPAIRED"},
        {"Unit": "Unit G", "Nomenclature": "ALS", "Veh_BA_No": "13D-192836W", "Dt_Induction": "20-Aug-2014", "Dt_In": "10-Feb-2025", "Dt_Out": "14-Feb-2025", "KM_In": 66343, "KM_Out": 66348, "Defect": "MAIN GEAR BOX NOISY, RADIATOR LEKING, BRAKE POOR, CABIN LIFTING PUMP NOT WORK", "Repair_Activity": "MAIN GEAR BOX SHAFT REPLACED, GAS WELDING, BRAKE ADJUSTED, RAM HYDRAULIC FITTED"},
        {"Unit": "Unit H", "Nomenclature": "ALS", "Veh_BA_No": "13D-192836W", "Dt_Induction": "20-Aug-2014", "Dt_In": "17-Apr-2025", "Dt_Out": "18-Aug-2025", "KM_In": 66487, "KM_Out": 66490, "Defect": "ENGINE OVERHEATING, HAND BRAKE AIR PRESSURE LEAKING", "Repair_Activity": "WATER PUMP MAJOR SERVICE KIT FITTED, PRESSURE LEAKING RECTIFIED"},
        {"Unit": "Unit I", "Nomenclature": "ALS", "Veh_BA_No": "13D-192836W", "Dt_Induction": "20-Aug-2014", "Dt_In": "18-Nov-2025", "Dt_Out": "24-Feb-2026", "KM_In": 68064, "KM_Out": 68068, "Defect": "GEAR SHIFTING HARD, STARTING TROUBLE", "Repair_Activity": "GEAR BOX SERVICING, FUEL TANK & PIPE LINE CLEANED"},
        {"Unit": "Unit J", "Nomenclature": "ALS", "Veh_BA_No": "13D-192836W", "Dt_Induction": "20-Aug-2014", "Dt_In": "19-Mar-2026", "Dt_Out": "20-Mar-2026", "KM_In": 68221, "KM_Out": 68229, "Defect": "BRAKE POOR", "Repair_Activity": "BRAKE ADJUSTED"},
        {"Unit": "Unit K", "Nomenclature": "ALS", "Veh_BA_No": "19D-208745N", "Dt_Induction": "29-May-2019", "Dt_In": "26-Oct-2023", "Dt_Out": "26-Oct-2023", "KM_In": 27321, "KM_Out": 27329, "Defect": "BRAKE POOR", "Repair_Activity": "BRAKE ADJUSTED"},
        {"Unit": "Unit L", "Nomenclature": "ALS", "Veh_BA_No": "19D-208745N", "Dt_Induction": "29-May-2019", "Dt_In": "14-Jan-2025", "Dt_Out": "18-Jan-2025", "KM_In": 29103, "KM_Out": 29109, "Defect": "ROAD SPRING BROCKEN, SUSPENSION NOISY", "Repair_Activity": "ROAD SPRING LEAF & U BOLT FITTED, SUSPENSION REPAIR"},
        {"Unit": "Unit M", "Nomenclature": "ALS", "Veh_BA_No": "19D-202808W", "Dt_Induction": "29-May-2019", "Dt_In": "06-Aug-2023", "Dt_Out": "07-Aug-2023", "KM_In": 25562, "KM_Out": 25670, "Defect": "BRAKE POOR, HEAD LIGHT NOT WORK", "Repair_Activity": "BRAKE ADJUSTED, HEAD LIGHT REPAIRED"},
        {"Unit": "Unit N", "Nomenclature": "ALS", "Veh_BA_No": "19D-202808W", "Dt_Induction": "29-May-2019", "Dt_In": "24-Aug-2023", "Dt_Out": "24-Aug-2023", "KM_In": 26020, "KM_Out": 26025, "Defect": "ROAD SPRING BROCKEN", "Repair_Activity": "ROAD SPRING NO.6 LEAF NEW FITTED"},
        {"Unit": "Unit O", "Nomenclature": "5 KL W/B", "Veh_BA_No": "14P-029330Y", "Dt_Induction": "16-Jun-2014", "Dt_In": "01-Jul-2025", "Dt_Out": "01-Jul-2025", "KM_In": 21800, "KM_Out": 21809, "Defect": "FAN BELT BROCKEN, WATER PUMP NOT WORK", "Repair_Activity": "FAN BELT NEW FITTED, WATER PUMP REPAIRED"}
    ]
    return pd.DataFrame(raw_data)

# ---------------------------------------------------------
# 5. STYLING
# ---------------------------------------------------------
st.markdown("""
<style>
    .stApp { background-color: #0e1117 !important; color: #f8fafc !important; }
    .metric-card-box {
        background-color: #1e293b !important; border: 1px solid #334155 !important;
        border-left: 4px solid #38bdf8 !important; padding: 16px 20px !important;
        border-radius: 8px !important; margin-bottom: 12px !important;
    }
    .metric-card-title { color: #94a3b8 !important; font-size: 13px !important; font-weight: 500 !important; margin-bottom: 4px !important; }
    .metric-card-val { color: #f8fafc !important; font-size: 22px !important; font-weight: 700 !important; margin-bottom: 4px !important; }
    .action-directive-box {
        background-color: #1e293b !important; border: 1px solid #475569 !important;
        padding: 16px 20px !important; border-radius: 8px !important; margin-bottom: 12px !important;
    }
    .stTabs [data-baseweb="tab"] { color: #cbd5e1 !important; font-weight: 600 !important; }
    .stTabs [data-baseweb="tab"][aria-selected="true"] { color: #38bdf8 !important; border-bottom-color: #38bdf8 !important; }
</style>
""", unsafe_allow_html=True)

init_db()
seed_db_if_empty()

st.sidebar.title("🎖️ Command Controls")
st.sidebar.write(f"Logged in as: **{name}**")
st.sidebar.caption(f"Role: **{user_role}**")
logout_button()

# ---------------------------------------------------------
# 6. FEATURE PARSER & RISK SCORING ENGINE
# ---------------------------------------------------------
def parse_features(raw_df):
    df = raw_df.copy()
    if df.empty:
        return df
    norm_cols = {str(c).strip().lower(): c for c in df.columns}

    def get_col(patterns):
        for pat in patterns:
            for clean_c, orig_c in norm_cols.items():
                if re.search(pat, clean_c):
                    return orig_c
        return None

    c_unit = get_col([r'unit', r'regiment'])
    c_nom = get_col([r'nom', r'type', r'variant', r'make'])
    c_ba = get_col([r'ba.*no', r'veh.*no', r'number'])
    c_ind = get_col([r'induct', r'vintage', r'yom', r'dt.*induct'])
    c_km = get_col([r'km.*in', r'odometer', r'mileage'])
    c_def = get_col([r'defect', r'fault', r'complaint'])
    c_rep = get_col([r'repair', r'activity', r'action'])
    c_dt_in = get_col([r'dt.*in', r'date.*in'])
    c_dt_out = get_col([r'dt.*out', r'date.*out'])

    clean_dict = {
        'Unit': df[c_unit].astype(str) if c_unit else [f"Unit {chr(65 + i % 15)}" for i in range(len(df))],
        'Nomenclature': df[c_nom].astype(str) if c_nom else "2.5 TON",
        'Veh_BA_No': df[c_ba].astype(str) if c_ba else [f"IA-{2001+i}" for i in range(len(df))],
        'Dt_Induction': df[c_ind].astype(str) if c_ind else "01-Jan-2020",
        'KM_In': pd.to_numeric(df[c_km], errors='coerce').fillna(25000) if c_km else 25000,
        'Defect': df[c_def].astype(str) if c_def else "Routine Checkup",
        'Repair_Activity': df[c_rep].astype(str) if c_rep else "Servicing & Adjustments",
        'Dt_In': df[c_dt_in].astype(str) if c_dt_in else "01-Jan-2024",
        'Dt_Out': df[c_dt_out].astype(str) if c_dt_out else "05-Jan-2024"
    }
    res_df = pd.DataFrame(clean_dict)

    current_year = datetime.now().year

    def extract_vintage(val):
        try:
            years = re.findall(r'\b(19\d\d|20\d\d)\b', str(val))
            if years:
                return max(1.0, float(current_year - int(years[-1])))
            dt = pd.to_datetime(val, errors='coerce')
            if pd.notnull(dt):
                return max(1.0, float(current_year - dt.year))
        except Exception:
            pass
        return 5.0

    res_df['Vintage_Years'] = res_df['Dt_Induction'].apply(extract_vintage)
    res_df['Vintage_Category'] = res_df['Vintage_Years'].apply(
        lambda v: "0-5 Years" if v <= 5 else ("5-10 Years" if v <= 10 else ("10-15 Years" if v <= 15 else "15+ Years"))
    )

    res_df['KM_In_Num'] = pd.to_numeric(res_df['KM_In'], errors='coerce').fillna(25000)
    res_df['Mileage_Category'] = res_df['KM_In_Num'].apply(
        lambda k: "0-25k KM" if k <= 25000 else ("25k-50k KM" if k <= 50000 else ("50k-75k KM" if k <= 75000 else ("75k-1 Lakh KM" if k <= 100000 else "Beyond 1 Lakh KM")))
    )

    subsystems, actions, risk_scores = [], [], []
    for _, row in res_df.iterrows():
        d = str(row['Defect']).upper()
        r = str(row['Repair_Activity']).upper()

        if any(w in d for w in ['ENGINE', 'RADIATOR', 'WATER PUMP', 'FAN BELT', 'OVERHEAT', 'COOLANT']):
            sub, sub_severity = "Thermal & Cooling", 30
        elif any(w in d for w in ['BRAKE', 'AIR PRESSURE', 'COMPRESS', 'BOOSTER']):
            sub, sub_severity = "Braking & Pneumatics", 30
        elif any(w in d for w in ['GEAR', 'CLUTCH', 'AXLE', 'PROPELLER', 'DRIVE']):
            sub, sub_severity = "Transmission & Drivetrain", 25
        elif any(w in d for w in ['SPRING', 'SUSPENSION', 'HUB SEAL', 'LEAF']):
            sub, sub_severity = "Suspension & Running Gear", 20
        elif any(w in d for w in ['SWITCH', 'LIGHT', 'WIPER', 'BATTERY', 'SOLENOID', 'DOOR']):
            sub, sub_severity = "Electrical & Body", 15
        else:
            sub, sub_severity = "General Chassis", 10

        if any(w in r for w in ['NEW FITTED', 'REPLACED', 'CANNIBALIZED', 'FITTED', 'OVERHAUL', 'KIT']):
            act, action_severity = "⚙️ Spare Part Replaced", 20
        else:
            act, action_severity = "🔧 Servicing & Adjustment", 5

        vintage_stress = min(row['Vintage_Years'] * 2.0, 20.0)
        mileage_stress = min((row['KM_In_Num'] / 10000.0) * 2.5, 20.0)

        calculated_risk = round(min(95.0, max(12.0, 10.0 + sub_severity + action_severity + vintage_stress + mileage_stress)), 1)

        subsystems.append(sub)
        actions.append(act)
        risk_scores.append(calculated_risk)

    res_df['Subsystem'] = subsystems
    res_df['Action_Type'] = actions
    res_df['AI_Failure_Risk_%'] = risk_scores
    res_df['Tactical_Status'] = res_df['AI_Failure_Risk_%'].apply(
        lambda r: "🟢 Mission Ready (P1)" if r < 60 else ("🟡 Field Limit (P2)" if r < 80 else "🔴 Critical Workshop Grounded (P3)")
    )
    return res_df

# ---------------------------------------------------------
# 7. INGESTION & DATA FLOW (PRIORITIZES UPLOADED FILE)
# ---------------------------------------------------------
units_15 = [f"Unit {chr(65 + i)}" for i in range(15)]

uploaded_file = None
if user_role in ["editor", "Admin"]:
    uploaded_file = st.sidebar.file_uploader("📂 Ingest Unit Workshop File (.xlsx / .csv)", type=["xlsx", "csv"])

# DYNAMIC DATA BINDING: Use uploaded file directly if present
if uploaded_file is not None:
    try:
        new_df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
        df_full = parse_features(new_df)
        st.sidebar.success(f"✅ Active: {uploaded_file.name} ({len(df_full)} Logs)")
    except Exception as e:
        st.sidebar.error(f"Error parsing file: {e}")
        raw_store = load_all_records()
        df_full = parse_features(raw_store)
else:
    raw_store = load_all_records()
    df_full = parse_features(raw_store)

st.sidebar.markdown("---")
st.sidebar.subheader("🔍 Filters")

unit_list = sorted(list(df_full['Unit'].astype(str).unique())) if not df_full.empty else []
sel_unit = st.sidebar.selectbox("Filter Unit", ["All Units"] + unit_list)

var_list = sorted(list(df_full['Nomenclature'].astype(str).unique())) if not df_full.empty else []
sel_variant = st.sidebar.selectbox("Filter Vehicle Type", ["All Vehicles"] + var_list)

sub_list = sorted(list(df_full['Subsystem'].astype(str).unique())) if not df_full.empty else []
sel_sub = st.sidebar.selectbox("Filter Subsystem Defect", ["All Subsystems"] + sub_list)

sel_vin = st.sidebar.selectbox("Filter Vintage (Age)", ["All Vintage", "0-5 Years", "5-10 Years", "10-15 Years", "15+ Years"])
sel_mil = st.sidebar.selectbox("Filter Mileage Range", ["All Mileage", "0-25k KM", "25k-50k KM", "50k-75k KM", "75k-1 Lakh KM", "Beyond 1 Lakh KM"])

if user_role in ["editor", "Admin"] and uploaded_file is None:
    st.sidebar.markdown("---")
    st.sidebar.subheader("➕ Add Single Defect Record (DB)")
    with st.sidebar.form("add_new_defect_form", clear_on_submit=True):
        in_unit = st.selectbox("Assigned Unit", units_15)
        in_nom = st.selectbox("Vehicle Platform", ["2.5 TON", "ALS", "5 KL W/B", "Specialist Veh"])
        in_ba = st.text_input("BA No", "22C-998811K")
        in_ind = st.text_input("Induction Date", "10-Jan-2022")
        in_km = st.number_input("Odometer (KM In)", value=28000, step=500)
        in_def = st.text_input("Defect Description", "BRAKE POOR, RADIATOR LEAKING")
        in_rep = st.text_input("Repair Activity Carried Out", "RADIATOR NEW FITTED, BRAKE ADJUSTED")
        if st.form_submit_button("Submit Record"):
            insert_record({
                "Unit": in_unit, "Nomenclature": in_nom, "Veh_BA_No": in_ba,
                "Dt_Induction": in_ind, "Dt_In": datetime.now().strftime("%d-%b-%Y"),
                "Dt_Out": datetime.now().strftime("%d-%b-%Y"), "KM_In": in_km,
                "KM_Out": in_km + 5, "Defect": in_def, "Repair_Activity": in_rep
            }, username)
            st.rerun()

# Apply Filters
dff = df_full.copy()
if not dff.empty:
    if sel_unit != "All Units": dff = dff[dff['Unit'] == sel_unit]
    if sel_variant != "All Vehicles": dff = dff[dff['Nomenclature'] == sel_variant]
    if sel_sub != "All Subsystems": dff = dff[dff['Subsystem'] == sel_sub]
    if sel_vin != "All Vintage": dff = dff[dff['Vintage_Category'] == sel_vin]
    if sel_mil != "All Mileage": dff = dff[dff['Mileage_Category'] == sel_mil]

# ---------------------------------------------------------
# 8. EXECUTIVE HEADER & TOP METRICS
# ---------------------------------------------------------
st.title("🪖 Army Fleet Predictive Maintenance Dashboard")
st.caption(f"Active Filter: **{sel_unit}** | Platform: **{sel_variant}** | Subsystem: **{sel_sub}**")

k1, k2, k3, k4, k5 = st.columns(5)
tot_v = len(dff['Veh_BA_No'].unique()) if not dff.empty else 0
ready_v = len(dff[dff['Tactical_Status'].str.contains("🟢")]) if not dff.empty else 0
lim_v = len(dff[dff['Tactical_Status'].str.contains("🟡")]) if not dff.empty else 0
gnd_v = len(dff[dff['Tactical_Status'].str.contains("🔴")]) if not dff.empty else 0
avg_risk = round(dff['AI_Failure_Risk_%'].mean(), 1) if not dff.empty else 0

with k1:
    st.markdown(f"""<div class="metric-card-box"><div class="metric-card-title">Monitored Vehicles</div><div class="metric-card-val">{tot_v} Vehs</div><div style="color:#38bdf8; font-size:12px; font-weight:600;">{len(dff)} Defect Logs</div></div>""", unsafe_allow_html=True)
with k2:
    st.markdown(f"""<div class="metric-card-box" style="border-left-color:#f59e0b !important;"><div class="metric-card-title">Avg Failure Risk</div><div class="metric-card-val">{avg_risk}%</div><div style="color:#f59e0b; font-size:12px; font-weight:600;">Statistical Estimate</div></div>""", unsafe_allow_html=True)
with k3:
    st.markdown(f"""<div class="metric-card-box" style="border-left-color:#10b981 !important;"><div class="metric-card-title">🟢 Mission Ready</div><div class="metric-card-val">{ready_v}</div><div style="color:#10b981; font-size:12px; font-weight:600;">{(ready_v/max(1, len(dff))*100):.0f}% Fleet</div></div>""", unsafe_allow_html=True)
with k4:
    st.markdown(f"""<div class="metric-card-box" style="border-left-color:#38bdf8 !important;"><div class="metric-card-title">🟡 Minor Adjustments</div><div class="metric-card-val">{lim_v}</div><div style="color:#38bdf8; font-size:12px; font-weight:600;">Field Fixes</div></div>""", unsafe_allow_html=True)
with k5:
    st.markdown(f"""<div class="metric-card-box" style="border-left-color:#ef4444 !important;"><div class="metric-card-title">🔴 Workshop Grounded</div><div class="metric-card-val">{gnd_v}</div><div style="color:#ef4444; font-size:12px; font-weight:600;">Awaiting Spares</div></div>""", unsafe_allow_html=True)

st.markdown("---")

# ---------------------------------------------------------
# 9. TABS
# ---------------------------------------------------------
tab_analytics, tab_vm, tab_diag, tab_docket = st.tabs([
    "📊 Subsystem Defect Analytics",
    "📈 Vintage & Mileage Analysis",
    "🔮 AI Vehicle Diagnostics",
    "📋 Digital Maintenance Docket (Editable)"
])

with tab_analytics:
    g1, g2 = st.columns(2)
    with g1:
        st.subheader("Subsystem Defects (By Repair Nature)")
        if not dff.empty:
            fig_sub = px.histogram(
                dff, x='Subsystem', color='Action_Type', barmode='group',
                color_discrete_map={'⚙️ Spare Part Replaced': '#ef4444', '🔧 Servicing & Adjustment': '#38bdf8'},
                title=f"Defects by Mechanical Assembly ({sel_unit} | {sel_variant})"
            )
            fig_sub.update_layout(plot_bgcolor='#1e293b', paper_bgcolor='#1e293b', font=dict(color='#f8fafc'),
                                   xaxis=dict(color='#cbd5e1', gridcolor='#334155'), yaxis=dict(color='#cbd5e1', gridcolor='#334155'),
                                   legend=dict(font=dict(color='#f8fafc')), xaxis_tickangle=-20)
            st.plotly_chart(fig_sub, use_container_width=True)
        else:
            st.info("No records matching active filters.")
    with g2:
        st.subheader("Vehicle Variant Defect Load")
        if not dff.empty:
            fig_var = px.histogram(dff, x='Nomenclature', color='Subsystem', title="Breakdown Distribution by Vehicle Platform")
            fig_var.update_layout(plot_bgcolor='#1e293b', paper_bgcolor='#1e293b', font=dict(color='#f8fafc'),
                                   xaxis=dict(color='#cbd5e1', gridcolor='#334155'), yaxis=dict(color='#cbd5e1', gridcolor='#334155'),
                                   legend=dict(font=dict(color='#f8fafc')))
            st.plotly_chart(fig_var, use_container_width=True)
        else:
            st.info("No records matching active filters.")

with tab_vm:
    v1, v2 = st.columns(2)
    with v1:
        st.subheader("Mileage Range vs Defect Frequency")
        if not dff.empty:
            fig_mil = px.histogram(dff, x='Mileage_Category', color='Action_Type',
                                    category_orders={'Mileage_Category': ["0-25k KM", "25k-50k KM", "50k-75k KM", "75k-1 Lakh KM", "Beyond 1 Lakh KM"]},
                                    color_discrete_map={'⚙️ Spare Part Replaced': '#ef4444', '🔧 Servicing & Adjustment': '#38bdf8'},
                                    title="Odometer Mileage Stress Bands")
            fig_mil.update_layout(plot_bgcolor='#1e293b', paper_bgcolor='#1e293b', font=dict(color='#f8fafc'),
                                   xaxis=dict(color='#cbd5e1', gridcolor='#334155'), yaxis=dict(color='#cbd5e1', gridcolor='#334155'),
                                   legend=dict(font=dict(color='#f8fafc')))
            st.plotly_chart(fig_mil, use_container_width=True)
        else:
            st.info("No records available.")
    with v2:
        st.subheader("Vintage (Age) vs Subsystem Breakdowns")
        if not dff.empty:
            fig_vin = px.histogram(dff, x='Vintage_Category', color='Subsystem',
                                    category_orders={'Vintage_Category': ["0-5 Years", "5-10 Years", "10-15 Years", "15+ Years"]},
                                    title="Age-Induced Degradation Curve")
            fig_vin.update_layout(plot_bgcolor='#1e293b', paper_bgcolor='#1e293b', font=dict(color='#f8fafc'),
                                   xaxis=dict(color='#cbd5e1', gridcolor='#334155'), yaxis=dict(color='#cbd5e1', gridcolor='#334155'),
                                   legend=dict(font=dict(color='#f8fafc')))
            st.plotly_chart(fig_vin, use_container_width=True)
        else:
            st.info("No records available.")

with tab_diag:
    st.subheader("🔮 Individual Vehicle Audit & Failure Diagnostic")
    vehs = sorted(dff['Veh_BA_No'].unique()) if not dff.empty else []
    if vehs:
        c_v1, c_v2 = st.columns([1, 2])
        t_veh = c_v1.selectbox("Select Target BA Number", vehs)
        v_data = dff[dff['Veh_BA_No'] == t_veh]

        with c_v1:
            st.markdown(f"""
            <div class="metric-card-box">
                <div style="color:#38bdf8; font-size:16px; font-weight:700; margin-bottom:8px;">🪖 Vehicle Identity Profile</div>
                <p style="color:#cbd5e1; margin:4px 0;"><b>BA Number:</b> <code style="color:#38bdf8;">{t_veh}</code></p>
                <p style="color:#cbd5e1; margin:4px 0;"><b>Platform:</b> {v_data['Nomenclature'].iloc[0]}</p>
                <p style="color:#cbd5e1; margin:4px 0;"><b>Unit:</b> {v_data['Unit'].iloc[0]}</p>
                <p style="color:#cbd5e1; margin:4px 0;"><b>Vintage:</b> {v_data['Vintage_Years'].iloc[0]} Years</p>
                <p style="color:#cbd5e1; margin:4px 0;"><b>Cumulative Mileage:</b> {int(v_data['KM_In_Num'].max()):,} KM</p>
                <p style="color:#cbd5e1; margin:4px 0;"><b>Risk Score:</b> <b style="color:#ef4444;">{v_data['AI_Failure_Risk_%'].iloc[-1]}%</b> <span style="color:#94a3b8; font-size:11px;">(rule-based estimate)</span></p>
                <p style="color:#cbd5e1; margin:4px 0;"><b>Tactical Status:</b> {v_data['Tactical_Status'].iloc[-1]}</p>
            </div>
            """, unsafe_allow_html=True)

        with c_v2:
            st.markdown("#### 🛠️ Prescriptive Action Directives")
            text = " ".join(v_data['Defect'].tolist()).upper()
            recs = []
            if "BRAKE" in text or "PRESSURE" in text:
                recs.append({"title": "Braking Circuit Deterioration", "cause": "Repeat brake adjustment and pneumatic leakage recorded.",
                             "action": "Conduct immediate pressure bench test on booster & unloader valve before next deployment.",
                             "urgency": "🔴 High Priority (Immediate Workshop Check)"})
            if "SPRING" in text or "SUSPENSION" in text:
                recs.append({"title": "Suspension Leaf Stress", "cause": "Terrain fatigue on road spring leaves and loose U-bolts.",
                             "action": "Re-torque U-bolts to factory specs and inspect rubber bump stops.",
                             "urgency": "🟡 Medium Priority (Field Inspection)"})
            if "RADIATOR" in text or "ENGINE" in text or "WATER PUMP" in text:
                recs.append({"title": "Thermal Cooling Vulnerability", "cause": "Temperature anomalies and coolant leakage logged.",
                             "action": "Conduct cooling circuit flush and replace water pump service kit.",
                             "urgency": "🔴 High Priority (Component Overhaul)"})
            if not recs:
                recs.append({"title": "Nominal Fleet Operation", "cause": "No chronic wear patterns detected in recent logs.",
                             "action": "Proceed with standard 5,000 KM lubrication and routine check schedule.",
                             "urgency": "🟢 Nominal Operation"})

            for r in recs:
                st.markdown(f"""
                <div class="action-directive-box">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
                        <div style="color:#f8fafc; font-size:15px; font-weight:700;">{r['title']}</div>
                        <span style="font-weight:700; font-size:12px;">{r['urgency']}</span>
                    </div>
                    <div style="color:#cbd5e1; font-size:13px; margin:3px 0;"><b>⚠️ Root Cause:</b> {r['cause']}</div>
                    <div style="color:#38bdf8; font-size:13px; font-weight:600; margin:3px 0;"><b>✅ Required Workshop Action:</b> {r['action']}</div>
                </div>
                """, unsafe_allow_html=True)

            st.markdown("#### 📜 Chronological Workshop Defect History")
            st.dataframe(v_data[['Dt_In', 'KM_In', 'Defect', 'Repair_Activity', 'Subsystem', 'Action_Type']], use_container_width=True)
    else:
        st.info("No vehicles match current filters.")
with tab_docket:
    st.subheader("📋 Digital Maintenance Docket")
    cols = ['Veh_BA_No', 'Unit', 'Nomenclature', 'Vintage_Category', 'Mileage_Category', 'KM_In',
            'Defect', 'Repair_Activity', 'Subsystem', 'Action_Type', 'AI_Failure_Risk_%', 'Tactical_Status']

    if dff.empty:
        st.info("No records to display for active filters.")
    else:
        if user_role in ["editor", "Admin"]:
            st.caption("Double click any cell to edit details directly, or add new rows at the bottom.")
            edited_df = st.data_editor(dff[cols], num_rows="dynamic", use_container_width=True)
        else:
            st.caption("🔒 Read-only view — your role does not permit editing.")
            st.dataframe(dff[cols], use_container_width=True)
            edited_df = dff[cols]

        csv_bytes = edited_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Maintenance Docket (CSV)",
            data=csv_bytes,
            file_name=f"Army_Fleet_Docket_{datetime.now().strftime('%d_%b_%Y')}.csv",
            mime="text/csv"
        )

            

    
