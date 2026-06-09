
"""
Biogas Plant Analytics Dashboard  ·  Universal Format  ·  Streamlit v8
=======================================================================
FIXES in this version:
  1. Raw Data tab — fully working: safe column list (no 'plant' in options),
     proper show_cols construction, Excel + CSV download, summary stats.
  2. Graphs wider — use_container_width=True + height=500 default;
     legend moved BELOW chart (orientation='h') to free horizontal space.
  3. X-axis locked to full selected date range with 1-day padding on each end.
  4. Full light mode — all CSS uses !important, Streamlit theme vars overridden.
  5. Legend orientation=horizontal below each chart — no more crowded top-right.
  6. All parameter columns verified against actual Excel structure.
  7. purif_eff_calc / bg_recovery empty columns hidden from chart list
     (legitimately empty in this dataset — calculated columns not filled).
"""

import io
import warnings
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

warnings.filterwarnings("ignore")

# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Biogas Plant Analytics",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
# LIGHT MODE STYLES
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Inter:wght@300;400;500;600&display=swap');

/* Force light mode everywhere */
html, body, [class*="css"], .stApp,
[data-testid="stAppViewContainer"],
[data-testid="stMainBlockContainer"],
[data-testid="block-container"],
section[data-testid="stMain"],
div[data-testid="stVerticalBlock"] {
    background-color: #f0f4f8 !important;
    color: #1a2740 !important;
    font-family: 'Inter', sans-serif !important;
}

/* Override Streamlit's own dark-mode injection */
:root {
    --background-color: #f0f4f8 !important;
    --secondary-background-color: #e4ecf5 !important;
    --text-color: #1a2740 !important;
    --primary-color: #1565c0 !important;
}

/* ── Sidebar ─────────────────────────────────────── */
[data-testid="stSidebar"],
[data-testid="stSidebar"] > div:first-child {
    background: linear-gradient(180deg, #1a2d4a 0%, #0f1f38 100%) !important;
    border-right: 1px solid #2a4a7a !important;
}
[data-testid="stSidebar"] *,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span { color: #c8d8f0 !important; }
[data-testid="stSidebar"] h2 {
    font-family: 'Space Mono', monospace !important;
    font-size: 1rem !important;
    letter-spacing: 0.06em !important;
    color: #4fc3f7 !important;
}
[data-testid="stSidebar"] .stRadio label,
[data-testid="stSidebar"] .stSlider label,
[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] .stMultiSelect label {
    color: #a0bcd8 !important;
}
[data-testid="stSidebar"] .stRadio span { color: #c8d8f0 !important; }

/* ── Main content ────────────────────────────────── */
.stApp { background-color: #f0f4f8 !important; }
[data-testid="stMainBlockContainer"] {
    padding: 1.5rem 2rem !important;
    background-color: #f0f4f8 !important;
}

/* Fix text colors in main area */
.stMarkdown, .stMarkdown p, .stMarkdown li,
p, label, span, div { color: #1a2740 !important; }

/* ── KPI Cards ───────────────────────────────────── */
.kpi-card {
    background: #ffffff !important;
    border: 1px solid #ccd9e8 !important;
    border-top: 3px solid #1565c0 !important;
    border-radius: 10px !important;
    padding: 14px 16px 12px !important;
    box-shadow: 0 2px 6px rgba(21,101,192,0.08) !important;
    margin-bottom: 8px !important;
}
.kpi-value {
    font-family: 'Space Mono', monospace !important;
    font-size: 1.55rem !important;
    font-weight: 700 !important;
    color: #1565c0 !important;
    line-height: 1.1 !important;
}
.kpi-label {
    font-size: 0.68rem !important;
    font-weight: 600 !important;
    color: #5a7a9a !important;
    margin-top: 4px !important;
    text-transform: uppercase !important;
    letter-spacing: 0.07em !important;
}
.kpi-icon { font-size: 1.2rem !important; margin-bottom: 5px !important; }

/* ── Section headers ─────────────────────────────── */
.sec-hdr {
    background: #e3ecf8 !important;
    border-left: 3px solid #1565c0 !important;
    color: #1a2d4a !important;
    padding: 9px 16px !important;
    border-radius: 0 8px 8px 0 !important;
    font-family: 'Space Mono', monospace !important;
    font-size: 0.80rem !important;
    font-weight: 700 !important;
    letter-spacing: 0.06em !important;
    text-transform: uppercase !important;
    margin: 18px 0 8px !important;
}

/* ── Plant badges ────────────────────────────────── */
.plant-badge {
    display: inline-block !important;
    background: #ddeeff !important;
    border: 1px solid #90caf9 !important;
    border-radius: 20px !important;
    padding: 3px 12px !important;
    font-family: 'Space Mono', monospace !important;
    font-size: 0.75rem !important;
    color: #1565c0 !important;
    margin: 2px 3px !important;
}
.compare-badge {
    display: inline-block !important;
    background: #fff3e0 !important;
    border: 1px solid #ffb74d !important;
    border-radius: 20px !important;
    padding: 3px 12px !important;
    font-family: 'Space Mono', monospace !important;
    font-size: 0.75rem !important;
    color: #bf360c !important;
    margin: 2px 3px !important;
}

/* ── Tabs ────────────────────────────────────────── */
[data-testid="stTabs"] [data-baseweb="tab-list"] {
    background: #dde8f5 !important;
    border-radius: 10px !important;
    padding: 3px !important;
    gap: 2px !important;
}
[data-testid="stTabs"] [data-baseweb="tab"] {
    font-family: 'Inter', sans-serif !important;
    font-size: 0.77rem !important;
    font-weight: 500 !important;
    padding: 7px 12px !important;
    border-radius: 7px !important;
    color: #4a6a8a !important;
    background: transparent !important;
}
[data-testid="stTabs"] [aria-selected="true"] {
    background: #ffffff !important;
    color: #1565c0 !important;
    box-shadow: 0 1px 4px rgba(21,101,192,0.12) !important;
}

/* ── Chart wrappers ──────────────────────────────── */
[data-testid="stPlotlyChart"] {
    background: #ffffff !important;
    border: 1px solid #cdd9e8 !important;
    border-radius: 10px !important;
    box-shadow: 0 1px 4px rgba(21,101,192,0.05) !important;
    overflow: hidden !important;
}

/* ── Dataframes ──────────────────────────────────── */
[data-testid="stDataFrame"] {
    border: 1px solid #cdd9e8 !important;
    border-radius: 8px !important;
}
/* Fix dataframe text color */
.dvn-scroller, [data-testid="stDataFrame"] * {
    color: #1a2740 !important;
    background-color: #ffffff !important;
}

/* ── Expander ────────────────────────────────────── */
[data-testid="stExpander"],
[data-testid="stExpander"] > div {
    background: #ffffff !important;
    border: 1px solid #cdd9e8 !important;
    border-radius: 8px !important;
}

/* ── Info/warning/success ────────────────────────── */
.stAlert { border-radius: 8px !important; }
[data-testid="stInfo"] { background: #e8f4fd !important; }
[data-testid="stWarning"] { background: #fff8e1 !important; }

/* ── Download buttons ────────────────────────────── */
.stDownloadButton button {
    background: #1565c0 !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 6px !important;
}

/* ── Mode banner ─────────────────────────────────── */
.mode-banner {
    background: linear-gradient(90deg, #e3f0ff 0%, #eef4fd 100%) !important;
    border: 1px solid #90c0f0 !important;
    border-radius: 8px !important;
    padding: 7px 14px !important;
    margin-bottom: 10px !important;
    font-size: 0.82rem !important;
    color: #1a2d4a !important;
    font-weight: 500 !important;
}

hr { border-color: #cdd9e8 !important; margin: 1rem 0 !important; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────
PALETTE = [
    "#1565c0", "#2e7d32", "#c84b00", "#6a1b9a",
    "#00838f", "#b71c1c", "#4527a0", "#558b2f",
    "#ad1457", "#00695c",
]
CHART_BG   = "#ffffff"
CHART_GRID = "#eaf0f8"
FONT_COLOR = "#1a2740"
AXIS_COLOR = "#7a96b2"

# ─────────────────────────────────────────────────────────────────────────────
# COLUMN DEFINITIONS
# ─────────────────────────────────────────────────────────────────────────────
SEEK = {
    "date":                ["date"],
    "dung_tons":           ["dung (tons)", "dung\n(tons)", "dung"],
    "waste_potato_tons":   ["waste potato"],
    "total_feed_m3":       ["total feed to reactor"],
    "total_filter_water":  ["total filter water consumed"],
    "raw_ch4":             ["ch₄", "ch4"],
    "raw_co2":             ["co₂", "co2"],
    "raw_o2":              ["o₂", "o2"],
    "raw_h2s":             ["h₂s", "h2s"],
    "raw_bal":             ["bal (%)"],
    "total_generated_gas": ["total generated gas"],
    "total_raw_gas":       ["total raw gas"],
    "gen_inlet_diff":      ["gen-inlet"],
    "total_purified_gas":  ["total purified gas"],
    "expected_gas_kg":     ["expected gas"],
    "cbg_mass_fm_kg":      ["cbg mass fm"],
    "pure_gas_purity_fm":  ["pure gas purity in fm", "pure gas purity"],
    "cbg_sales_kg":        ["total cbg sales dispenser", "total cbg sales"],
    "num_vehicles":        ["no. of vehicles", "no of vehicles"],
    "cascade_sales_kg":    ["cascade vehicle sales"],
    "purif_efficiency":    ["purification efficiency (%)"],
    "purif_running_hrs":   ["purification running hrs"],
    "compressor_hrs":      ["compressor running hrs"],
    "screw_press_hrs":     ["screw press running hrs"],
    "vibro_screen_hrs":    ["vibro screen running hrs"],
    "volute_press_hrs":    ["volute press running hrs"],
    "screw_moisture":      ["screw press moisture"],
    "volute_moisture":     ["volute press moisture"],
    "raw_water_m3":        ["raw water"],
    "digester_ph":         ["mid ph"],
    "digester_temp":       ["digester temp"],
    "flare_m3":            ["flare"],
    "poly_kg":             ["poly consumption"],
    "dg_hrs":              ["dg running hrs"],
    "dg_diesel_l":         ["dg diesel consumed"],
    "purif_eff_calc":      ["purif. eff."],
    "bg_recovery":         ["bg recovery"],
    "remarks":             ["remarks"],
}

_SECOND_OCCURRENCE = {
    "pure_ch4": ["ch₄", "ch4"],
    "pure_co2": ["co₂", "co2"],
    "pure_h2s": ["h₂s", "h2s"],
}

# Human-friendly display names for raw data tab
COL_LABELS = {
    "dung_tons":           "Dung Collected (tons)",
    "waste_potato_tons":   "Waste Potato (tons)",
    "total_feed_m3":       "Total Feed to Reactor (m³)",
    "total_filter_water":  "Filter Water (m³)",
    "raw_ch4":             "Raw CH₄ (%)",
    "raw_co2":             "Raw CO₂ (%)",
    "raw_o2":              "Raw O₂ (%)",
    "raw_h2s":             "Raw H₂S (PPM)",
    "raw_bal":             "Raw Balance (%)",
    "total_generated_gas": "Total Generated Gas (m³)",
    "total_raw_gas":       "Total Raw Gas (m³)",
    "gen_inlet_diff":      "Gen–Inlet Diff (m³)",
    "total_purified_gas":  "Total Purified Gas (m³)",
    "expected_gas_kg":     "Expected Gas (kg)",
    "cbg_mass_fm_kg":      "CBG Mass FM (kg)",
    "pure_gas_purity_fm":  "Pure Gas Purity FM (%)",
    "cbg_sales_kg":        "CBG Sales Dispenser (kg)",
    "num_vehicles":        "No. of Vehicles",
    "cascade_sales_kg":    "Cascade Sales (kg)",
    "total_sales_kg":      "Total CBG Sales (kg)",
    "purif_efficiency":    "Purification Efficiency (%)",
    "purif_running_hrs":   "Purification Running Hrs",
    "compressor_hrs":      "Compressor Running Hrs",
    "screw_press_hrs":     "Screw Press Running Hrs",
    "vibro_screen_hrs":    "Vibro Screen Running Hrs",
    "volute_press_hrs":    "Volute Press Running Hrs",
    "screw_moisture":      "Screw Press Moisture (%)",
    "volute_moisture":     "Volute Press Moisture (%)",
    "raw_water_m3":        "Raw Water (m³)",
    "digester_ph":         "Digester pH",
    "digester_temp":       "Digester Temp (°C)",
    "flare_m3":            "Flare Gas (m³)",
    "poly_kg":             "Poly Consumption (kg)",
    "dg_hrs":              "DG Running Hrs",
    "dg_diesel_l":         "DG Diesel Consumed (L)",
    "purif_eff_calc":      "Purif. Eff. Calc (%)",
    "bg_recovery":         "BG Recovery (%)",
    "pure_ch4":            "Pure CH₄ (%)",
    "pure_co2":            "Pure CO₂ (%)",
    "pure_h2s":            "Pure H₂S (PPM)",
    "vpsa_kwh_total":      "VPSA KWH Total",
    "bg_mfm_kwh_total":    "BG MFM KWH Total",
    "hp_comp_kwh_init":    "HP Compressor KWH Init",
    "hp_comp_kwh_final":   "HP Compressor KWH Final",
    "remarks":             "Remarks",
}


# ─────────────────────────────────────────────────────────────────────────────
# HEADER DETECTION
# ─────────────────────────────────────────────────────────────────────────────
def _find_header_rows(raw):
    for r in range(min(6, len(raw))):
        v = str(raw.iloc[r, 0]).replace("\n", " ").strip().lower()
        if v == "date":
            return max(0, r - 1), r
    return 0, 1


def _build_col_index(raw):
    section_row_idx, header_row_idx = _find_header_rows(raw)
    header = [
        str(v).replace("\n", " ").strip().lower() if pd.notna(v) else ""
        for v in raw.iloc[header_row_idx]
    ]
    section = [
        str(v).replace("\n", " ").strip().lower() if pd.notna(v) else ""
        for v in raw.iloc[section_row_idx]
    ]
    idx = {}
    skip_keys = set(_SECOND_OCCURRENCE.keys()) | {
        "vpsa_kwh_total", "bg_mfm_kwh_total",
        "hp_comp_kwh_init", "hp_comp_kwh_final",
    }
    for key, needles in SEEK.items():
        if key in skip_keys:
            continue
        for needle in needles:
            nl = needle.lower()
            for c, h in enumerate(header):
                if nl in h:
                    idx[key] = c
                    break
            if key in idx:
                break
    for pure_key, needles in _SECOND_OCCURRENCE.items():
        raw_key = pure_key.replace("pure_", "raw_")
        for needle in needles:
            nl = needle.lower()
            matches = [c for c, h in enumerate(header) if nl in h]
            if len(matches) >= 1 and raw_key not in idx:
                idx[raw_key] = matches[0]
            if len(matches) >= 2:
                idx[pure_key] = matches[1]
            if raw_key in idx and pure_key in idx:
                break
    kwh_cols = [c for c, h in enumerate(header) if "total kwh consumed" in h]
    if len(kwh_cols) >= 1:
        idx["vpsa_kwh_total"] = kwh_cols[0]
    if len(kwh_cols) >= 2:
        idx["bg_mfm_kwh_total"] = kwh_cols[1]
    hp_cols = [c for c, s in enumerate(section) if "hp compressor" in s]
    for c in hp_cols:
        h = header[c] if c < len(header) else ""
        if "initial" in h:
            idx["hp_comp_kwh_init"] = c
        elif "final" in h:
            idx["hp_comp_kwh_final"] = c
    return idx


# ─────────────────────────────────────────────────────────────────────────────
# LOADERS
# ─────────────────────────────────────────────────────────────────────────────
def _to_num(s):
    if not isinstance(s, pd.Series):
        return pd.Series(dtype=float)
    return pd.to_numeric(s, errors="coerce")


def load_daily_operations(wb_bytes, plant_name):
    raw = pd.read_excel(io.BytesIO(wb_bytes),
                        sheet_name="Daily Operations", header=None)
    _, header_row_idx = _find_header_rows(raw)
    data_start = header_row_idx + 2
    for r in range(data_start, min(data_start + 5, len(raw))):
        try:
            v = raw.iloc[r, 0]
            if pd.notna(v):
                pd.Timestamp(v)
                data_start = r
                break
        except Exception:
            pass
    col_idx = _build_col_index(raw)
    data = raw.iloc[data_start:].reset_index(drop=True)
    all_keys = (list(SEEK.keys()) + list(_SECOND_OCCURRENCE.keys()) +
                ["vpsa_kwh_total", "bg_mfm_kwh_total",
                 "hp_comp_kwh_init", "hp_comp_kwh_final"])
    records = {}
    for key in all_keys:
        c = col_idx.get(key)
        if c is not None and c < data.shape[1]:
            records[key] = data.iloc[:, c].values
        else:
            records[key] = np.full(len(data), np.nan, dtype=object)
    df = pd.DataFrame(records)
    df["date"] = pd.to_datetime(df["date"], dayfirst=True, errors="coerce")
    df = df.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)
    for col in df.columns:
        if col not in ("date", "remarks"):
            df[col] = _to_num(df[col])
    df["total_sales_kg"] = (df["cbg_sales_kg"].fillna(0) +
                             df["cascade_sales_kg"].fillna(0))
    df["plant"] = plant_name
    return df


def load_lab_analysis(wb_bytes, plant_name):
    raw = pd.read_excel(io.BytesIO(wb_bytes),
                        sheet_name="Lab & Slurry Analysis", header=None)
    data = raw.iloc[3:].reset_index(drop=True).copy()
    data.columns = range(data.shape[1])
    data.rename(columns={0: "date", 1: "sample_point", 2: "pH",
                          3: "EC_mScm", 4: "TS_pct", 5: "VS_pct",
                          6: "Temp_C", 7: "Carbon_pct"}, inplace=True)
    data["date"] = data["date"].ffill()
    data["date"] = pd.to_datetime(data["date"], dayfirst=True, errors="coerce")
    data = data.dropna(subset=["date", "sample_point"])
    data["sample_point"] = data["sample_point"].astype(str).str.strip()
    data = data[~data["sample_point"].str.lower().str.contains(
        "sample point|notes|nan", na=False)]
    for col in ["pH", "EC_mScm", "TS_pct", "VS_pct", "Temp_C", "Carbon_pct"]:
        if col in data.columns:
            data[col] = _to_num(data[col])
    for col, lo, hi in [("TS_pct", 0, 100), ("VS_pct", 0, 100), ("pH", 0, 14)]:
        if col in data.columns:
            data = data[~(data[col].notna() & ~data[col].between(lo, hi))]
    data["plant"] = plant_name
    return data[["date", "plant", "sample_point", "pH", "EC_mScm",
                 "TS_pct", "VS_pct", "Temp_C", "Carbon_pct"]].reset_index(drop=True)


def load_dung_quality(wb_bytes, plant_name):
    raw = pd.read_excel(io.BytesIO(wb_bytes),
                        sheet_name="Dung Route Quality", header=None)
    route_row  = raw.iloc[0]
    subcol_row = raw.iloc[1]
    data       = raw.iloc[3:].reset_index(drop=True)
    records, current_route = [], None
    for c in range(1, data.shape[1], 4):
        if c < len(route_row) and pd.notna(route_row.iloc[c]):
            current_route = str(route_row.iloc[c]).strip()
        if current_route is None:
            continue
        sub_names = []
        for k in range(4):
            ci = c + k
            sub_names.append(
                str(subcol_row.iloc[ci]).strip()
                if ci < len(subcol_row) and pd.notna(subcol_row.iloc[ci])
                else f"sub{k}"
            )
        for _, row in data.iterrows():
            date_val = pd.to_datetime(row.iloc[0], dayfirst=True, errors="coerce")
            if pd.isna(date_val):
                continue
            rec = {"date": date_val, "route": current_route, "plant": plant_name}
            for k, sname in enumerate(sub_names):
                v = row.iloc[c + k] if (c + k) < len(row) else np.nan
                rec[sname] = pd.to_numeric(v, errors="coerce")
            records.append(rec)
    return (pd.DataFrame(records).sort_values("date").reset_index(drop=True)
            if records else pd.DataFrame())


def load_fertilizer_quality(wb_bytes, plant_name):
    raw = pd.read_excel(io.BytesIO(wb_bytes),
                        sheet_name="Fertilizer Quality", header=None)
    header_row_idx = 2
    for r in range(min(6, len(raw))):
        v = str(raw.iloc[r, 0]).replace("\n", " ").strip().lower()
        if v.startswith("sr"):
            header_row_idx = r
            break
    headers = [str(h).replace("\n", " ").strip() for h in raw.iloc[header_row_idx]]
    data = raw.iloc[header_row_idx + 1:].reset_index(drop=True).copy()
    data.columns = headers
    sr_col = headers[0]
    data = data[pd.to_numeric(data[sr_col], errors="coerce").notna()].copy()
    non_numeric = {
        sr_col, "Sr. No.", "Sr.\nNo.", "Sample Date", "Sample\nDate",
        "Material Name", "Material\nName", "Batch / Type", "Batch /\nType",
        "Mfg Date / Month", "Mfg Date\n/ Month",
        "Remarks / Sampler", "Remarks /\nSampler",
    }
    for col in data.columns:
        if col in non_numeric:
            continue
        if isinstance(data[col], pd.Series) and data[col].dtype == object:
            try:
                data[col] = pd.to_numeric(data[col], errors="coerce")
            except Exception:
                pass
    data["plant"] = plant_name
    return data.reset_index(drop=True)


@st.cache_data(show_spinner=False)
def load_plant(file_bytes, plant_name):
    def _safe(fn, label):
        try:
            return fn(file_bytes, plant_name)
        except Exception as e:
            st.warning(f"⚠️ [{plant_name}] {label}: {e}")
            return pd.DataFrame()
    return {
        "ops":  _safe(load_daily_operations,  "Daily Operations"),
        "lab":  _safe(load_lab_analysis,      "Lab & Slurry Analysis"),
        "dung": _safe(load_dung_quality,      "Dung Route Quality"),
        "fert": _safe(load_fertilizer_quality, "Fertilizer Quality"),
    }


# ─────────────────────────────────────────────────────────────────────────────
# CHART HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def _pmap(plants):
    return {p: PALETTE[i % len(PALETTE)] for i, p in enumerate(sorted(plants))}


def _hex_to_rgba(hex_color, alpha=0.15):
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


def _ma(s, w):
    return s.rolling(w, min_periods=1).mean()


def _xrange_from_filter(date_filter):
    """Return padded [start, end] for Plotly x-axis, or None."""
    if not date_filter:
        return None
    s = date_filter.get("start")
    e = date_filter.get("end")
    if s is None or e is None:
        return None
    return [
        (s - pd.Timedelta(days=1)).strftime("%Y-%m-%d"),
        (e + pd.Timedelta(days=1)).strftime("%Y-%m-%d"),
    ]


def _base(fig, height=500, xrange=None):
    """Apply light-mode theme, legend below chart, full x-axis extent."""
    legend_cfg = dict(
        orientation="h",          # horizontal legend
        yanchor="top",
        y=-0.18,                   # below the chart
        xanchor="center",
        x=0.5,
        bgcolor="rgba(255,255,255,0.9)",
        bordercolor="#cdd9e8",
        borderwidth=1,
        font=dict(size=11, color=FONT_COLOR),
    )
    xaxis_kw = dict(
        showgrid=True, gridcolor=CHART_GRID, gridwidth=1,
        zeroline=False, showline=True, linecolor="#cdd9e8",
        tickfont=dict(size=11, color=AXIS_COLOR),
        tickcolor=AXIS_COLOR,
        title_font=dict(color=AXIS_COLOR),
        type="date",
        autorange=xrange is None,
    )
    if xrange is not None:
        xaxis_kw["range"] = xrange
    fig.update_layout(
        paper_bgcolor=CHART_BG,
        plot_bgcolor=CHART_BG,
        font=dict(color=FONT_COLOR, family="Inter, sans-serif", size=12),
        legend=legend_cfg,
        hovermode="x unified",
        height=height,
        title_x=0,
        title_font=dict(size=13, color="#1a2d4a", family="Space Mono, monospace"),
        margin=dict(l=10, r=10, t=44, b=80),  # b=80 to give room for bottom legend
    )
    fig.update_xaxes(**xaxis_kw)
    fig.update_yaxes(
        showgrid=True, gridcolor=CHART_GRID, gridwidth=1,
        zeroline=False, showline=False,
        tickfont=dict(size=11, color=AXIS_COLOR),
        title_font=dict(color=AXIS_COLOR),
    )
    return fig


def line_fig(df, x, ycol, title, ylab="", ma=7, height=500, xrange=None):
    fig = go.Figure()
    if df.empty or ycol not in df.columns:
        return _base(fig, height, xrange)
    cmap = _pmap(df["plant"].unique())
    for p, gdf in df.groupby("plant"):
        c = cmap[p]
        s = gdf[ycol]
        valid = s.notna().sum()
        # Raw data line — thin and faded
        fig.add_trace(go.Scatter(
            x=gdf[x], y=s, mode="lines", name=p,
            line=dict(color=c, width=1.2),
            opacity=0.3,
            showlegend=(ma <= 1),  # only show in legend if no MA
        ))
        if ma > 1 and valid >= ma:
            # MA line — thick, bold, in legend
            fig.add_trace(go.Scatter(
                x=gdf[x], y=_ma(s, ma), mode="lines",
                name=f"{p}  ({ma}d avg)",
                line=dict(color=c, width=2.8),
                opacity=1.0,
                showlegend=True,
            ))
        elif valid > 0 and ma <= 1:
            # No MA: make raw line more visible
            fig.data[-1].update(opacity=0.85, line=dict(width=2.2))
    fig.update_layout(title=title, yaxis_title=ylab)
    return _base(fig, height, xrange)


def dual_line_fig(df, x, col_a, label_a, col_b, label_b, title,
                  height=500, xrange=None):
    fig = go.Figure()
    if df.empty:
        return _base(fig, height, xrange)
    cmap = _pmap(df["plant"].unique())
    for p, gdf in df.groupby("plant"):
        c = cmap[p]
        if col_a in gdf.columns and gdf[col_a].notna().any():
            fig.add_trace(go.Scatter(
                x=gdf[x], y=gdf[col_a], name=f"{p} – {label_a}",
                line=dict(color=c, width=2.4),
            ))
        if col_b in gdf.columns and gdf[col_b].notna().any():
            fig.add_trace(go.Scatter(
                x=gdf[x], y=gdf[col_b], name=f"{p} – {label_b}",
                line=dict(color=c, width=2.4, dash="dot"),
            ))
    fig.update_layout(title=title)
    return _base(fig, height, xrange)


def bar_fig(df, x, y, title, color="plant", barmode="group", height=460):
    cmap = _pmap(df["plant"].unique()) if "plant" in df.columns else {}
    fig = px.bar(df, x=x, y=y, color=color, barmode=barmode,
                 title=title, color_discrete_map=cmap)
    fig.update_traces(marker_line_width=0)
    fig.update_layout(
        paper_bgcolor=CHART_BG, plot_bgcolor=CHART_BG,
        font=dict(color=FONT_COLOR, family="Inter, sans-serif"),
        title_font=dict(size=13, color="#1a2d4a", family="Space Mono, monospace"),
        legend=dict(
            orientation="h", yanchor="top", y=-0.18, xanchor="center", x=0.5,
            bgcolor="rgba(255,255,255,0.9)", bordercolor="#cdd9e8",
            borderwidth=1, font=dict(color=FONT_COLOR),
        ),
        height=height, title_x=0,
        margin=dict(l=10, r=10, t=44, b=80),
    )
    fig.update_xaxes(showgrid=False, linecolor="#cdd9e8",
                     tickfont=dict(color=AXIS_COLOR))
    fig.update_yaxes(showgrid=True, gridcolor=CHART_GRID,
                     tickfont=dict(color=AXIS_COLOR))
    return fig


def scatter_fig(df, x, y, title, color="sample_point", height=480):
    cmap = _pmap(df[color].unique()) if color in df.columns else {}
    fig = px.scatter(df, x=x, y=y, color=color, trendline="ols",
                     title=title, color_discrete_map=cmap)
    fig.update_traces(marker=dict(size=6, opacity=0.7))
    fig.update_layout(
        paper_bgcolor=CHART_BG, plot_bgcolor=CHART_BG,
        font=dict(color=FONT_COLOR, family="Inter, sans-serif"),
        title_font=dict(size=13, color="#1a2d4a", family="Space Mono, monospace"),
        legend=dict(
            orientation="h", yanchor="top", y=-0.18, xanchor="center", x=0.5,
            bgcolor="rgba(255,255,255,0.9)", bordercolor="#cdd9e8",
            borderwidth=1, font=dict(color=FONT_COLOR),
        ),
        height=height, title_x=0,
        margin=dict(l=10, r=10, t=44, b=80),
    )
    fig.update_xaxes(showgrid=True, gridcolor=CHART_GRID,
                     tickfont=dict(color=AXIS_COLOR))
    fig.update_yaxes(showgrid=True, gridcolor=CHART_GRID,
                     tickfont=dict(color=AXIS_COLOR))
    return fig


def sec(text):
    st.markdown(f'<div class="sec-hdr">{text}</div>', unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────
def sidebar():
    with st.sidebar:
        st.markdown("## ⚡ BIOGAS ANALYTICS")
        st.markdown("---")

        uploaded = st.file_uploader(
            "📂 Upload plant Excel file(s)",
            type=["xlsx"],
            accept_multiple_files=True,
            help="One file per plant — Unified Daily Report format.",
        )

        all_data = {}
        if uploaded:
            for f in uploaded:
                raw_bytes = f.read()
                default = f.name.replace(".xlsx", "").replace("_", " ").title()
                pname = st.text_input(
                    f"Name for '{f.name}'",
                    value=default,
                    key=f"pname_{f.name}",
                )
                with st.spinner(f"Loading {pname}…"):
                    all_data[pname] = load_plant(raw_bytes, pname)

        if not all_data:
            st.info("Upload one or more plant Excel files to begin.")
            return {}, [], {}, "individual", []

        st.markdown("---")
        st.markdown("### 🏭 Plants")
        plants = list(all_data.keys())

        if len(plants) > 1:
            view_mode = st.radio(
                "View mode",
                ["individual", "compare"],
                format_func=lambda x: "📋 Individual" if x == "individual" else "📊 Compare",
                key="view_mode",
                horizontal=True,
            )
        else:
            view_mode = "individual"

        if view_mode == "individual":
            selected_plant = st.selectbox("Plant to view", plants, key="sel_plant_ind")
            selected = [selected_plant]
            compare_plants = []
        else:
            compare_plants = st.multiselect(
                "Plants to compare", plants, default=plants, key="sel_plant_cmp"
            )
            selected = compare_plants if compare_plants else plants

        # Date filter
        all_ops = [all_data[p]["ops"] for p in selected
                   if p in all_data and not all_data[p]["ops"].empty]
        date_filter = {}

        if all_ops:
            combined = pd.concat(all_ops, ignore_index=True)
            data_min = combined["date"].min().date()
            data_max = combined["date"].max().date()

            st.markdown("---")
            st.markdown("### 📅 Date Filter")
            filter_type = st.radio(
                "Filter by",
                ["Month / Year", "Custom Range", "All Data"],
                key="date_filter_type",
            )

            if filter_type == "Month / Year":
                all_months = pd.period_range(
                    pd.Period(data_min, "M"),
                    pd.Period(data_max, "M"),
                    freq="M",
                )
                month_strs = [str(m) for m in all_months]
                chosen_months = st.multiselect(
                    "Select months", month_strs,
                    default=month_strs, key="month_picker",
                )
                if chosen_months:
                    periods = [pd.Period(m, "M") for m in chosen_months]
                    date_filter = {
                        "start":  min(p.start_time for p in periods),
                        "end":    max(p.end_time   for p in periods),
                        "months": chosen_months,
                    }
            elif filter_type == "Custom Range":
                dr = st.date_input(
                    "Date range", value=(data_min, data_max),
                    min_value=data_min, max_value=data_max,
                    key="custom_dr",
                )
                if isinstance(dr, (list, tuple)) and len(dr) == 2:
                    date_filter = {
                        "start": pd.Timestamp(dr[0]),
                        "end":   pd.Timestamp(dr[1]),
                    }
                elif isinstance(dr, (list, tuple)) and len(dr) == 1:
                    date_filter = {
                        "start": pd.Timestamp(dr[0]),
                        "end":   pd.Timestamp(dr[0]),
                    }
            else:
                date_filter = {
                    "start": pd.Timestamp(data_min),
                    "end":   pd.Timestamp(data_max),
                }

        st.markdown("---")
        st.markdown("### ⚙️ Chart Options")
        st.slider("Moving average (days)", 1, 30, 7, key="ma_window")

        return all_data, selected, date_filter, view_mode, compare_plants


# ─────────────────────────────────────────────────────────────────────────────
# DATA FILTERS
# ─────────────────────────────────────────────────────────────────────────────
def _apply_date_filter(df, date_filter):
    if df.empty or not date_filter:
        return df
    if "months" in date_filter:
        periods = [pd.Period(m, "M") for m in date_filter["months"]]
        mask = df["date"].apply(lambda d: pd.Period(d, "M") in periods)
        return df[mask]
    return df[
        (df["date"] >= date_filter["start"]) &
        (df["date"] <= date_filter["end"])
    ]


def get_ops(all_data, selected, date_filter):
    frames = [
        _apply_date_filter(all_data[p]["ops"], date_filter)
        for p in selected
        if p in all_data and not all_data[p]["ops"].empty
    ]
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def get_lab(all_data, selected, date_filter):
    frames = [
        _apply_date_filter(all_data[p]["lab"], date_filter)
        for p in selected
        if p in all_data and not all_data[p]["lab"].empty
    ]
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


# ─────────────────────────────────────────────────────────────────────────────
# KPI ROW
# ─────────────────────────────────────────────────────────────────────────────
def render_kpis(ops):
    if ops.empty:
        st.warning("No operational data for the selected range.")
        return

    def sm(col): return ops[col].dropna().mean() if col in ops.columns else float("nan")
    def ss(col): return ops[col].dropna().sum()  if col in ops.columns else float("nan")

    kpis = [
        ("🌿", "Avg Biogas Gen",    f"{sm('total_generated_gas'):.0f}", "m³ / day"),
        ("🏭", "Total CBG Sales",   f"{ss('cbg_sales_kg'):,.0f}",       "kg total"),
        ("⚗️", "Avg Purif. Eff.",   f"{sm('purif_efficiency'):.1f}",    "%"),
        ("🔬", "Avg CH₄ Raw",       f"{sm('raw_ch4'):.1f}",             "% purity"),
        ("✨", "Avg CH₄ Pure",      f"{sm('pure_ch4'):.1f}",            "% purity"),
        ("🌡️", "Avg Digester Temp", f"{sm('digester_temp'):.1f}",       "°C"),
        ("⚡", "Avg VPSA Power",    f"{sm('vpsa_kwh_total'):.0f}",      "KWH / day"),
        ("🐄", "Avg Dung Input",    f"{sm('dung_tons'):.1f}",           "tons / day"),
    ]
    row1 = st.columns(4)
    row2 = st.columns(4)
    for i, (icon, label, value, unit) in enumerate(kpis):
        col = (row1 if i < 4 else row2)[i % 4]
        with col:
            st.markdown(f"""
<div class="kpi-card">
  <div class="kpi-icon">{icon}</div>
  <div class="kpi-value">{value}</div>
  <div class="kpi-label">{label}&nbsp;·&nbsp;{unit}</div>
</div>""", unsafe_allow_html=True)
    st.markdown("")  # spacing after KPI row


# ─────────────────────────────────────────────────────────────────────────────
# TABS
# ─────────────────────────────────────────────────────────────────────────────
def _pc(fig, key):
    """Shorthand: plotly_chart with use_container_width=True."""
    st.plotly_chart(fig, use_container_width=True, key=key)


def tab_gas(ops, ma, xr):
    sec("📊 GAS PRODUCTION & QUALITY")
    c1, c2 = st.columns(2)
    with c1:
        _pc(line_fig(ops,"date","total_generated_gas","Raw Biogas Generated","m³/day",ma,xrange=xr),"g1")
    with c2:
        _pc(line_fig(ops,"date","total_purified_gas","Purified Gas Output","m³/day",ma,xrange=xr),"g2")

    c3, c4 = st.columns(2)
    with c3:
        _pc(dual_line_fig(ops,"date","raw_ch4","CH₄","raw_co2","CO₂","Raw Gas Composition (%)",xrange=xr),"g3")
    with c4:
        _pc(dual_line_fig(ops,"date","pure_ch4","CH₄","pure_co2","CO₂","Purified Gas Composition (%)",xrange=xr),"g4")

    sec("⚠️ H₂S LEVELS (PPM)")
    c5, c6 = st.columns(2)
    with c5:
        fig = line_fig(ops,"date","raw_h2s","Raw Gas H₂S","PPM",ma,xrange=xr)
        fig.add_hline(y=500, line_dash="dash", line_color="#c62828",
                       annotation_text="Alert 500 PPM", annotation_font_color="#c62828")
        _pc(fig,"g5")
    with c6:
        fig = line_fig(ops,"date","pure_h2s","Purified Gas H₂S","PPM",ma,xrange=xr)
        fig.add_hline(y=50, line_dash="dash", line_color="#e65100",
                       annotation_text="Target <50 PPM", annotation_font_color="#e65100")
        _pc(fig,"g6")

    sec("📉 GAS BALANCE")
    c7, c8 = st.columns(2)
    with c7:
        _pc(line_fig(ops,"date","flare_m3","Flare Gas","m³",ma,xrange=xr),"g7")
    with c8:
        _pc(line_fig(ops,"date","gen_inlet_diff","Gen–Inlet Differential","m³",ma,xrange=xr),"g8")


def tab_feed(ops, ma, xr):
    sec("🐄 FEEDSTOCK & FEEDING")
    c1, c2 = st.columns(2)
    with c1:
        _pc(line_fig(ops,"date","dung_tons","Dung Collected","tons/day",ma,xrange=xr),"f1")
    with c2:
        _pc(line_fig(ops,"date","total_feed_m3","Total Feed to Reactor","m³/day",ma,xrange=xr),"f2")

    c3, c4 = st.columns(2)
    with c3:
        _pc(line_fig(ops,"date","total_filter_water","Filter Water Consumed","m³/day",ma,xrange=xr),"f3")
    with c4:
        if "waste_potato_tons" in ops.columns and ops["waste_potato_tons"].notna().any():
            _pc(line_fig(ops,"date","waste_potato_tons","Waste Potato Added","tons/day",ma,xrange=xr),"f4")
        else:
            st.info("No waste-potato data for selected range.")

    sec("📈 SPECIFIC BIOGAS YIELD")
    o2 = ops.copy()
    o2["yield_m3_per_ton"] = np.where(o2["dung_tons"]>0,
                                       o2["total_generated_gas"]/o2["dung_tons"],np.nan)
    _pc(line_fig(o2,"date","yield_m3_per_ton","Biogas Yield (m³ per ton of dung)","m³/ton",ma,xrange=xr),"f5")


def tab_purif(ops, ma, xr):
    sec("⚗️ PURIFICATION & CBG SALES")
    c1, c2 = st.columns(2)
    with c1:
        fig = line_fig(ops,"date","purif_efficiency","Purification Efficiency","%",ma,xrange=xr)
        fig.add_hline(y=95, line_dash="dot", line_color="#2e7d32",
                       annotation_text="Target 95%", annotation_font_color="#2e7d32")
        _pc(fig,"p1")
    with c2:
        _pc(line_fig(ops,"date","bg_recovery","Biogas Recovery","%",ma,xrange=xr),"p2")

    c3, c4 = st.columns(2)
    with c3:
        _pc(line_fig(ops,"date","cbg_sales_kg","CBG Sales – Dispenser","kg/day",ma,xrange=xr),"p3")
    with c4:
        _pc(line_fig(ops,"date","total_sales_kg","Total CBG Sales incl. Cascade","kg/day",ma,xrange=xr),"p4")

    sec("📅 MONTHLY CBG SALES")
    monthly = (ops.assign(month=ops["date"].dt.to_period("M").astype(str))
                  .groupby(["month","plant"],as_index=False)["cbg_sales_kg"].sum())
    if not monthly.empty:
        _pc(bar_fig(monthly,"month","cbg_sales_kg","Monthly CBG Sales (kg)",color="plant",height=440),"p5")

    c5, c6 = st.columns(2)
    with c5:
        _pc(line_fig(ops,"date","num_vehicles","Vehicles Served / Day","count",1,xrange=xr),"p6")
    with c6:
        _pc(line_fig(ops,"date","purif_running_hrs","Purification Running Hrs","hrs",1,xrange=xr),"p7")


def tab_power(ops, ma, xr):
    sec("⚡ POWER & UTILITY CONSUMPTION")
    c1, c2 = st.columns(2)
    with c1:
        _pc(line_fig(ops,"date","vpsa_kwh_total","VPSA Power Consumed","KWH/day",ma,xrange=xr),"pw1")
    with c2:
        _pc(line_fig(ops,"date","bg_mfm_kwh_total","Biogas MFM Power","KWH/day",ma,xrange=xr),"pw2")

    c3, c4 = st.columns(2)
    with c3:
        _pc(line_fig(ops,"date","raw_water_m3","Raw Water Consumed","m³/day",ma,xrange=xr),"pw3")
    with c4:
        _pc(line_fig(ops,"date","poly_kg","Poly Consumption","kg/day",ma,xrange=xr),"pw4")

    c5, c6 = st.columns(2)
    with c5:
        _pc(line_fig(ops,"date","dg_hrs","DG Running Hours","hrs",1,xrange=xr),"pw5")
    with c6:
        _pc(line_fig(ops,"date","dg_diesel_l","DG Diesel Consumed","L/day",ma,xrange=xr),"pw6")

    sec("💡 SPECIFIC ENERGY INTENSITY")
    o2 = ops.copy()
    o2["kwh_per_m3"] = np.where(o2["total_purified_gas"]>0,
                                  o2["vpsa_kwh_total"]/o2["total_purified_gas"],np.nan)
    _pc(line_fig(o2,"date","kwh_per_m3","VPSA Specific Energy (KWH / m³ purified gas)","KWH/m³",ma,xrange=xr),"pw7")


def tab_digester(ops, ma, xr):
    sec("🌡️ DIGESTER CONDITIONS")
    c1, c2 = st.columns(2)
    with c1:
        fig = line_fig(ops,"date","digester_temp","Digester Temperature","°C",ma,xrange=xr)
        fig.add_hline(y=37, line_dash="dash", line_color="#e65100",
                       annotation_text="Mesophilic 37°C", annotation_font_color="#e65100")
        fig.add_hrect(y0=35, y1=40, fillcolor="#e65100", opacity=0.05)
        _pc(fig,"d1")
    with c2:
        fig = line_fig(ops,"date","digester_ph","Digester pH","pH",ma,xrange=xr)
        fig.add_hrect(y0=6.8, y1=7.5, fillcolor="#2e7d32", opacity=0.07,
                       annotation_text="Optimal 6.8–7.5", annotation_font_color="#2e7d32")
        _pc(fig,"d2")

    sec("💧 DEWATERING")
    c3, c4 = st.columns(2)
    with c3:
        _pc(dual_line_fig(ops,"date","screw_moisture","Screw Press","volute_moisture","Volute Press","Dewatering Moisture (%)",xrange=xr),"d3")
    with c4:
        _pc(line_fig(ops,"date","flare_m3","Flare Gas","m³",ma,xrange=xr),"d4")

    c5, c6, c7 = st.columns(3)
    for col_w, col, title, key in zip(
        [c5,c6,c7],
        ["screw_press_hrs","vibro_screen_hrs","volute_press_hrs"],
        ["Screw Press Hrs","Vibro Screen Hrs","Volute Press Hrs"],
        ["d5","d6","d7"],
    ):
        with col_w:
            _pc(line_fig(ops,"date",col,title,"hrs",1,height=440,xrange=xr),key)


def tab_lab(all_data, selected, date_filter):
    sec("🔬 LAB & SLURRY ANALYSIS")
    lab = get_lab(all_data, selected, date_filter)
    if lab.empty:
        st.info("No lab data for the selected range.")
        return

    xr = _xrange_from_filter(date_filter)
    pts = sorted(lab["sample_point"].dropna().unique())
    defaults = ([s for s in ["RCD (Raw Cattle Dung)","Digester Mid Sampling Point",
                              "Mixing Tank","Slurry Tank"] if s in pts] or pts[:3])
    chosen = st.multiselect("Sample Points", pts, default=defaults, key="lab_pts")
    if not chosen:
        st.info("Select at least one sample point.")
        return

    lab_f = lab[lab["sample_point"].isin(chosen)]
    params = [
        ("pH","pH"), ("TS_pct","TS (%)"), ("VS_pct","VS (%)"),
        ("EC_mScm","EC (mS/cm)"), ("Temp_C","Temperature (°C)"), ("Carbon_pct","Carbon (%)"),
    ]
    for i in range(0, len(params), 2):
        c1, c2 = st.columns(2)
        for col_w, (param, label) in zip([c1,c2], params[i:i+2]):
            if param not in lab_f.columns or lab_f[param].dropna().empty:
                continue
            sub = lab_f.dropna(subset=[param])
            fig = px.line(sub, x="date", y=param, color="sample_point",
                          facet_col="plant" if len(selected)>1 else None,
                          title=f"{label} by Sample Point")
            fig.update_layout(
                paper_bgcolor=CHART_BG, plot_bgcolor=CHART_BG,
                font=dict(color=FONT_COLOR, family="Inter, sans-serif"),
                title_font=dict(size=13, color="#1a2d4a", family="Space Mono, monospace"),
                legend=dict(orientation="h", yanchor="top", y=-0.18,
                            xanchor="center", x=0.5,
                            bgcolor="rgba(255,255,255,0.9)", bordercolor="#cdd9e8",
                            borderwidth=1, font=dict(color=FONT_COLOR)),
                height=480, margin=dict(l=10, r=10, t=44, b=80),
            )
            xkw = dict(showgrid=True, gridcolor=CHART_GRID, tickfont=dict(color=AXIS_COLOR),
                       type="date", autorange=xr is None)
            if xr: xkw["range"] = xr
            fig.update_xaxes(**xkw)
            fig.update_yaxes(showgrid=True, gridcolor=CHART_GRID, tickfont=dict(color=AXIS_COLOR))
            with col_w:
                _pc(fig, f"lab_{param}")

    sec("📊 TS vs VS CORRELATION")
    valid = lab_f.dropna(subset=["TS_pct","VS_pct"])
    if not valid.empty:
        _pc(scatter_fig(valid,"TS_pct","VS_pct","TS (%) vs VS (%)"),"lab_scatter")


def tab_compare(all_data, selected, date_filter):
    sec("📊 CROSS-PLANT COMPARISON")
    try:
        _tab_compare_inner(all_data, selected, date_filter)
    except Exception as e:
        st.error(f"Compare tab error: {e}")
        import traceback
        with st.expander("Error details"):
            st.code(traceback.format_exc())


def _tab_compare_inner(all_data, selected, date_filter):
    if len(selected) < 2:
        st.info("Select **Compare** mode and choose at least 2 plants.")
        return

    ops = get_ops(all_data, selected, date_filter)

    st.markdown("**Data availability:**")
    diag_cols = st.columns(len(selected))
    plants_with_data = []
    for i, p in enumerate(selected):
        pdata = all_data.get(p, {}).get("ops", pd.DataFrame())
        filtered = _apply_date_filter(pdata, date_filter) if not pdata.empty else pdata
        if len(filtered) > 0:
            plants_with_data.append(p)
            diag_cols[i].success(
                f"**{p}**\n{len(filtered)} rows  \n"
                f"{filtered['date'].min().strftime('%d %b %Y')} → "
                f"{filtered['date'].max().strftime('%d %b %Y')}"
            )
        else:
            diag_cols[i].warning(f"**{p}**\nNo data in range")

    if len(plants_with_data) < 2:
        st.warning("Need ≥2 plants with data. Adjust the date filter.")
        return

    monthly = (
        ops.assign(month=ops["date"].dt.to_period("M").astype(str))
           .groupby(["month","plant"],as_index=False)
           .agg(
               total_generated_gas=("total_generated_gas","sum"),
               total_purified_gas =("total_purified_gas", "sum"),
               cbg_sales_kg       =("cbg_sales_kg",       "sum"),
               avg_purif_eff      =("purif_efficiency",   "mean"),
               avg_ch4_raw        =("raw_ch4",            "mean"),
               avg_ch4_pure       =("pure_ch4",           "mean"),
               avg_digester_temp  =("digester_temp",      "mean"),
               dung_tons          =("dung_tons",          "sum"),
           )
    )

    for col, title in [
        ("total_generated_gas","Monthly Raw Biogas (m³)"),
        ("total_purified_gas", "Monthly Purified Gas (m³)"),
        ("cbg_sales_kg",       "Monthly CBG Sales (kg)"),
        ("avg_purif_eff",      "Avg Purification Efficiency (%)"),
        ("avg_ch4_raw",        "Avg Raw CH₄ (%)"),
        ("avg_digester_temp",  "Avg Digester Temp (°C)"),
        ("dung_tons",          "Total Dung Collected (tons)"),
    ]:
        if col in monthly.columns and monthly[col].notna().any():
            _pc(bar_fig(monthly,"month",col,title,color="plant"),f"cmp_{col}")

    sec("📈 DAILY OVERLAY")
    xr = _xrange_from_filter(date_filter)
    ma = st.session_state.get("ma_window", 7)
    for col, title, ylab in [
        ("total_generated_gas","Raw Biogas Generated (m³/day)","m³/day"),
        ("total_purified_gas", "Purified Gas (m³/day)","m³/day"),
        ("purif_efficiency",   "Purification Efficiency (%)","% "),
        ("cbg_sales_kg",       "CBG Sales (kg/day)","kg"),
    ]:
        if col in ops.columns and ops[col].notna().any():
            _pc(line_fig(ops,"date",col,title,ylab,ma,xrange=xr),f"cmp_overlay_{col}")

    sec("🕸️ PLANT PROFILE RADAR")
    radar_m = ["avg_purif_eff","avg_ch4_raw","avg_ch4_pure"]
    latest = monthly.groupby("plant")[[c for c in radar_m if c in monthly.columns]].mean().reset_index()
    avail = [c for c in radar_m if c in latest.columns]
    if not latest.empty and len(avail) >= 2:
        labels_map = {"avg_purif_eff":"Purif Eff %","avg_ch4_raw":"CH₄ Raw %","avg_ch4_pure":"CH₄ Pure %"}
        theta = [labels_map.get(m,m) for m in avail] + [labels_map.get(avail[0],avail[0])]
        fig = go.Figure()
        cmap = _pmap(latest["plant"].tolist())
        for _, row in latest.iterrows():
            pname = row["plant"]
            vals  = [row.get(m,0) for m in avail] + [row.get(avail[0],0)]
            c = cmap.get(pname, PALETTE[0])
            fig.add_trace(go.Scatterpolar(
                r=vals, theta=theta, fill="toself", name=pname,
                line=dict(color=c,width=2), fillcolor=_hex_to_rgba(c,0.15),
            ))
        fig.update_layout(
            polar=dict(
                radialaxis=dict(visible=True, range=[0,100],
                                tickfont=dict(size=10,color="#5a7a9a"),
                                gridcolor="#d1dce8"),
                angularaxis=dict(tickfont=dict(size=12,color="#1a2d4a"),gridcolor="#d1dce8"),
                bgcolor="#f5f7fa",
            ),
            paper_bgcolor=CHART_BG,
            font=dict(color=FONT_COLOR,family="Inter, sans-serif"),
            height=480,
            legend=dict(orientation="h",yanchor="top",y=-0.1,xanchor="center",x=0.5,
                        bgcolor="rgba(255,255,255,0.9)",bordercolor="#cdd9e8",
                        borderwidth=1,font=dict(color=FONT_COLOR)),
        )
        _pc(fig,"cmp_radar")


def tab_dung_routes(all_data, selected, date_filter):
    sec("🚛 DUNG ROUTE QUALITY")
    frames = [
        _apply_date_filter(all_data[p]["dung"], date_filter)
        for p in selected
        if p in all_data and not all_data[p]["dung"].empty
    ]
    if not frames:
        st.info("No dung route quality data for this selection.")
        return

    dung = pd.concat(frames, ignore_index=True)
    routes = sorted(dung["route"].dropna().unique())
    chosen = st.multiselect("Routes", routes,
                             default=routes[:6] if len(routes)>6 else routes,
                             key="dung_routes")
    if not chosen:
        return
    dung_f = dung[dung["route"].isin(chosen)]

    rendered = 0
    for i in range(0, 4, 2):
        c1, c2 = st.columns(2)
        for col_w, needle in zip([c1,c2], ["Sand (%)","pH","EC","TS (%)"][i:i+2]):
            matching = [c for c in dung_f.columns if c.strip().lower()==needle.strip().lower()]
            if not matching:
                continue
            rc = matching[0]
            if dung_f[rc].dropna().empty:
                continue
            fig = px.box(dung_f.dropna(subset=[rc]), x="route", y=rc,
                         color="plant", title=f"Dung Route – {needle}")
            fig.update_layout(
                paper_bgcolor=CHART_BG, plot_bgcolor=CHART_BG,
                font=dict(color=FONT_COLOR, family="Inter, sans-serif"),
                title_font=dict(size=13,color="#1a2d4a",family="Space Mono, monospace"),
                legend=dict(orientation="h",yanchor="top",y=-0.18,xanchor="center",x=0.5,
                            bgcolor="rgba(255,255,255,0.9)",bordercolor="#cdd9e8",
                            borderwidth=1,font=dict(color=FONT_COLOR)),
                height=460, margin=dict(l=10,r=10,t=44,b=80),
            )
            fig.update_xaxes(showgrid=False, tickfont=dict(color=AXIS_COLOR))
            fig.update_yaxes(showgrid=True, gridcolor=CHART_GRID, tickfont=dict(color=AXIS_COLOR))
            with col_w:
                _pc(fig, f"dung_{rc}")
            rendered += 1
    if rendered == 0:
        st.info("No matching metric columns found in dung route data.")


def tab_fertilizer(all_data, selected):
    sec("🌱 ORGANIC FERTILIZER QUALITY")
    frames = [all_data[p]["fert"] for p in selected
              if p in all_data and not all_data[p]["fert"].empty]
    if not frames:
        st.info("No fertilizer quality data.")
        return

    fert = pd.concat(frames, ignore_index=True)
    num_cols = fert.select_dtypes(include=[np.number]).columns.tolist()
    if not num_cols:
        st.dataframe(fert.head(30), use_container_width=True)
        return

    c1, _ = st.columns([1, 3])
    with c1:
        param = st.selectbox("Parameter", num_cols, key="fert_param")

    mat_col = next((c for c in fert.columns if "material" in str(c).lower()), None)
    fert_plot = fert.dropna(subset=[param])
    if fert_plot.empty:
        st.info(f"No data for {param}.")
        return

    if mat_col:
        fig = px.box(fert_plot, x=mat_col, y=param, color="plant",
                     title=f"{param} by Material Type", points="all")
    else:
        fig = px.box(fert_plot, y=param, color="plant",
                     title=f"{param}", points="all")
    fig.update_traces(marker=dict(size=4, opacity=0.6))
    fig.update_layout(
        paper_bgcolor=CHART_BG, plot_bgcolor=CHART_BG,
        font=dict(color=FONT_COLOR, family="Inter, sans-serif"),
        title_font=dict(size=13,color="#1a2d4a",family="Space Mono, monospace"),
        legend=dict(orientation="h",yanchor="top",y=-0.18,xanchor="center",x=0.5,
                    bgcolor="rgba(255,255,255,0.9)",bordercolor="#cdd9e8",
                    borderwidth=1,font=dict(color=FONT_COLOR)),
        height=500, margin=dict(l=10,r=10,t=44,b=80),
    )
    fig.update_xaxes(showgrid=False, tickfont=dict(color=AXIS_COLOR))
    fig.update_yaxes(showgrid=True, gridcolor=CHART_GRID, tickfont=dict(color=AXIS_COLOR))
    _pc(fig,"fert_chart")

    with st.expander("📋 Raw fertilizer data"):
        st.dataframe(fert, use_container_width=True)


# ─────────────────────────────────────────────────────────────────────────────
# RAW DATA TAB  — fully fixed
# ─────────────────────────────────────────────────────────────────────────────
def tab_raw(ops, all_data, selected, date_filter):
    sec("🗄️ RAW DATA EXPLORER")
    if ops.empty:
        st.info("No data loaded for the selected range.")
        return

    # ── Plant selector within this tab ──────────────────────────
    plants_avail = [p for p in selected
                    if p in all_data and not all_data[p]["ops"].empty]
    if not plants_avail:
        st.info("No plant data available.")
        return

    if len(plants_avail) > 1:
        raw_plant_sel = st.multiselect(
            "Plants to include", plants_avail,
            default=plants_avail, key="raw_plant_sel",
        )
    else:
        raw_plant_sel = plants_avail

    if not raw_plant_sel:
        st.info("Select at least one plant.")
        return

    # ── Rebuild filtered dataframe for chosen plants ─────────────
    raw_frames = []
    for p in raw_plant_sel:
        df = all_data[p]["ops"]
        if not df.empty:
            raw_frames.append(_apply_date_filter(df, date_filter))
    if not raw_frames:
        st.info("No data for selected plants in this date range.")
        return

    ops_raw = pd.concat(raw_frames, ignore_index=True).sort_values(
        "date", ascending=False
    ).reset_index(drop=True)

    # ── Column selector ──────────────────────────────────────────
    # date and plant are ALWAYS shown; the multiselect controls DATA columns only
    ALWAYS_SHOW = ["date", "plant"]
    # data_cols: everything except date and plant, with human labels
    data_cols = [c for c in ops_raw.columns if c not in ALWAYS_SHOW]

    # Filter out columns that are entirely empty (all NaN) — they add noise
    non_empty_data_cols = [c for c in data_cols if ops_raw[c].notna().any()]

    # Build display labels for the multiselect
    col_display = {c: COL_LABELS.get(c, c) for c in non_empty_data_cols}
    display_to_col = {v: k for k, v in col_display.items()}

    # Preferred defaults (only from non-empty cols)
    preferred_keys = ["dung_tons","total_generated_gas","total_purified_gas",
                      "cbg_sales_kg","purif_efficiency","raw_ch4","pure_ch4",
                      "digester_temp","digester_ph","raw_h2s","pure_h2s",
                      "vpsa_kwh_total"]
    default_labels = [col_display[c] for c in preferred_keys
                      if c in col_display]

    st.markdown(f"**{len(ops_raw):,} rows** · {len(non_empty_data_cols)} data columns available")

    sel_labels = st.multiselect(
        "Select columns to display",
        options=list(col_display.values()),  # options = display labels
        default=default_labels,              # default = display labels (all in options ✓)
        key="raw_col_sel",
    )

    # Map display labels back to column names
    sel_cols = [display_to_col[lbl] for lbl in sel_labels if lbl in display_to_col]
    show_cols = ALWAYS_SHOW + [c for c in sel_cols if c in ops_raw.columns]

    # Build a display copy with renamed columns for readability
    display_df = ops_raw[show_cols].copy()
    rename_map = {c: COL_LABELS.get(c, c) for c in show_cols if c not in ALWAYS_SHOW}
    display_df = display_df.rename(columns=rename_map)
    # Format date nicely
    display_df["date"] = display_df["date"].dt.strftime("%Y-%m-%d")

    st.dataframe(display_df, use_container_width=True, height=520)

    # ── Downloads ────────────────────────────────────────────────
    dl1, dl2 = st.columns(2)
    with dl1:
        st.download_button(
            "⬇️ Download as CSV",
            ops_raw[show_cols].to_csv(index=False).encode("utf-8"),
            "biogas_data.csv", "text/csv", key="dl_csv",
        )
    with dl2:
        buf = io.BytesIO()
        ops_raw[show_cols].to_excel(buf, index=False, engine="openpyxl")
        st.download_button(
            "⬇️ Download as Excel",
            buf.getvalue(),
            "biogas_data.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="dl_xlsx",
        )

    # ── Summary stats ────────────────────────────────────────────
    with st.expander("📊 Summary Statistics"):
        num_cols_show = [c for c in sel_cols if ops_raw[c].dtype in [float, np.float64]]
        if num_cols_show:
            stats = ops_raw[num_cols_show].describe().T.round(2)
            stats.index = [COL_LABELS.get(c, c) for c in stats.index]
            st.dataframe(stats, use_container_width=True)
        else:
            st.info("No numeric columns selected.")


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────
def main():
    all_data, selected, date_filter, view_mode, compare_plants = sidebar()

    if not all_data or not selected:
        st.markdown("## ⚡ Biogas Plant Analytics Dashboard")
        st.markdown("""
**Getting started:**
1. Upload one `.xlsx` per plant (Unified Daily Report format) via the sidebar.
2. Rename each plant if needed.
3. Choose **Individual** view or **Compare** mode (2+ plants).
4. Pick a date filter — specific months, custom range, or all data.
5. Explore the analysis tabs.
        """)
        return

    # ── Header ──────────────────────────────────────────────────
    if view_mode == "compare" and len(selected) >= 2:
        badges = " ".join(f'<span class="compare-badge">⚖️ {p}</span>' for p in selected)
        mode_label, mode_color = "COMPARE MODE", "#c84b00"
    else:
        badges = " ".join(f'<span class="plant-badge">🏭 {p}</span>' for p in selected)
        mode_label, mode_color = "INDIVIDUAL VIEW", "#1565c0"

    st.markdown(
        f"<h2 style='font-family:Space Mono,monospace;color:#1a2d4a;"
        f"font-size:1.25rem;letter-spacing:0.04em;margin-bottom:4px'>"
        f"⚡ BIOGAS ANALYTICS &nbsp;"
        f"<span style='font-size:0.68rem;color:{mode_color}'>[{mode_label}]</span>"
        f"&nbsp;{badges}</h2>",
        unsafe_allow_html=True,
    )

    if date_filter:
        if "months" in date_filter:
            st.markdown(
                f'<div class="mode-banner">📅 Showing: <strong>'
                f'{", ".join(date_filter["months"])}</strong></div>',
                unsafe_allow_html=True,
            )
        else:
            s = date_filter["start"].strftime("%d %b %Y")
            e = date_filter["end"].strftime("%d %b %Y")
            st.markdown(
                f'<div class="mode-banner">📅 Range: <strong>{s}</strong>'
                f' → <strong>{e}</strong></div>',
                unsafe_allow_html=True,
            )

    ma  = st.session_state.get("ma_window", 7)
    ops = get_ops(all_data, selected, date_filter)
    xr  = _xrange_from_filter(date_filter)

    render_kpis(ops)
    st.markdown("---")

    # ── Tab layout ───────────────────────────────────────────────
    if view_mode == "compare" and len(selected) >= 2:
        tab_names = [
            "📊 Compare","📊 Gas Production","🐄 Feedstock",
            "⚗️ Purification","⚡ Power","🌡️ Digester",
            "🔬 Lab","🚛 Dung Routes","🌱 Fertilizer","🗄️ Raw Data",
        ]
        tabs = st.tabs(tab_names)
        with tabs[0]: tab_compare(all_data, selected, date_filter)
        with tabs[1]: tab_gas(ops, ma, xr)
        with tabs[2]: tab_feed(ops, ma, xr)
        with tabs[3]: tab_purif(ops, ma, xr)
        with tabs[4]: tab_power(ops, ma, xr)
        with tabs[5]: tab_digester(ops, ma, xr)
        with tabs[6]: tab_lab(all_data, selected, date_filter)
        with tabs[7]: tab_dung_routes(all_data, selected, date_filter)
        with tabs[8]: tab_fertilizer(all_data, selected)
        with tabs[9]: tab_raw(ops, all_data, selected, date_filter)
    else:
        tab_names = [
            "📊 Gas Production","🐄 Feedstock","⚗️ Purification",
            "⚡ Power","🌡️ Digester","🔬 Lab",
            "🚛 Dung Routes","🌱 Fertilizer","🗄️ Raw Data",
        ]
        tabs = st.tabs(tab_names)
        with tabs[0]: tab_gas(ops, ma, xr)
        with tabs[1]: tab_feed(ops, ma, xr)
        with tabs[2]: tab_purif(ops, ma, xr)
        with tabs[3]: tab_power(ops, ma, xr)
        with tabs[4]: tab_digester(ops, ma, xr)
        with tabs[5]: tab_lab(all_data, selected, date_filter)
        with tabs[6]: tab_dung_routes(all_data, selected, date_filter)
        with tabs[7]: tab_fertilizer(all_data, selected)
        with tabs[8]: tab_raw(ops, all_data, selected, date_filter)


if __name__ == "__main__":
    main()

