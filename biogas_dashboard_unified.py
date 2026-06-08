"""
Biogas Plant Analytics Dashboard  ·  Universal Format  ·  Streamlit
=====================================================================
v6 — Bug fixes + full UI overhaul
  FIX 1: tab_raw multiselect crash — 'plant' was in default_show but excluded
          from all_cols options, causing StreamlitAPIException.
  FIX 2: Header-row auto-detection for both Agthala (row offset 0) and
          Data template (row offset 1 with extra blank row).
  FIX 3: load_fertilizer_quality robust coercion with per-column try/except.
  FIX 4: st.session_state["ma_window"] never assigned after slider widget.
  UI:     Full dark industrial redesign — larger charts (480px / 520px),
          richer KPI cards, improved grid density, better typography/colors.
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
# GLOBAL STYLES
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=DM+Sans:wght@300;400;500;600&display=swap');

/* ── Base ─────────────────────────────────────────── */
html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }

/* ── Sidebar ──────────────────────────────────────── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #070d1a 0%, #0b1525 100%);
    border-right: 1px solid #1a2d4a;
}
[data-testid="stSidebar"] * { color: #c8d8f0 !important; }
[data-testid="stSidebar"] h2 {
    font-family: 'Space Mono', monospace;
    font-size: 1.1rem;
    letter-spacing: 0.08em;
    color: #4fc3f7 !important;
}

/* ── Main area background ─────────────────────────── */
.stApp { background: #060c18; }
[data-testid="stMainBlockContainer"] { padding: 1.5rem 2rem; }

/* ── KPI Cards ────────────────────────────────────── */
.kpi-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 12px;
    margin: 1rem 0 1.5rem;
}
.kpi-card {
    background: linear-gradient(135deg, #0d1f3c 0%, #0a1628 100%);
    border: 1px solid #1e3a5f;
    border-top: 2px solid #2979ff;
    border-radius: 10px;
    padding: 18px 20px 14px;
    position: relative;
    overflow: hidden;
}
.kpi-card::before {
    content: '';
    position: absolute;
    top: 0; right: 0;
    width: 60px; height: 60px;
    background: radial-gradient(circle, rgba(79,195,247,0.08) 0%, transparent 70%);
}
.kpi-value {
    font-family: 'Space Mono', monospace;
    font-size: 1.75rem;
    font-weight: 700;
    color: #4fc3f7;
    line-height: 1.1;
    letter-spacing: -0.02em;
}
.kpi-label {
    font-size: 0.72rem;
    font-weight: 500;
    color: #6b8fb5;
    margin-top: 6px;
    text-transform: uppercase;
    letter-spacing: 0.07em;
}
.kpi-icon { font-size: 1.4rem; margin-bottom: 8px; }

/* ── Section headers ──────────────────────────────── */
.sec-hdr {
    background: linear-gradient(90deg, #112240 0%, #0d1b33 100%);
    border-left: 3px solid #2979ff;
    color: #e8f0fe;
    padding: 10px 18px;
    border-radius: 0 8px 8px 0;
    font-family: 'Space Mono', monospace;
    font-size: 0.88rem;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    margin: 20px 0 12px;
}

/* ── Plant badges ─────────────────────────────────── */
.plant-badge {
    display: inline-block;
    background: #0d1f3c;
    border: 1px solid #2979ff;
    border-radius: 20px;
    padding: 4px 14px;
    font-family: 'Space Mono', monospace;
    font-size: 0.78rem;
    color: #4fc3f7;
    margin: 2px 4px;
    letter-spacing: 0.04em;
}

/* ── Tab strip ────────────────────────────────────── */
[data-testid="stTabs"] [data-baseweb="tab-list"] {
    background: #0a1628;
    border-radius: 10px;
    padding: 4px;
    gap: 2px;
}
[data-testid="stTabs"] [data-baseweb="tab"] {
    font-family: 'DM Sans', sans-serif;
    font-size: 0.8rem;
    font-weight: 500;
    padding: 8px 14px;
    border-radius: 8px;
    color: #6b8fb5;
}
[data-testid="stTabs"] [aria-selected="true"] {
    background: #112240 !important;
    color: #4fc3f7 !important;
}

/* ── Plotly chart container ───────────────────────── */
[data-testid="stPlotlyChart"] {
    background: #0a1628;
    border: 1px solid #1a2d4a;
    border-radius: 10px;
    padding: 4px;
}

/* ── Dataframes ───────────────────────────────────── */
[data-testid="stDataFrame"] { border: 1px solid #1a2d4a; border-radius: 8px; }

/* ── Divider ──────────────────────────────────────── */
hr { border-color: #1a2d4a !important; margin: 1rem 0 !important; }

/* ── Info / warning boxes ─────────────────────────── */
.stAlert { border-radius: 8px; }

/* ── Expander ─────────────────────────────────────── */
[data-testid="stExpander"] {
    background: #0a1628;
    border: 1px solid #1a2d4a;
    border-radius: 8px;
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# COLOUR PALETTE
# ─────────────────────────────────────────────────────────────────────────────
PALETTE = [
    "#4fc3f7", "#69f0ae", "#ffab40", "#ea80fc",
    "#ff5252", "#40c4ff", "#b2ff59", "#ffd740",
    "#ff6d00", "#64ffda",
]

# ─────────────────────────────────────────────────────────────────────────────
# SEMANTIC COLUMN DEFINITIONS
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


# ─────────────────────────────────────────────────────────────────────────────
# HEADER ROW DETECTION
# ─────────────────────────────────────────────────────────────────────────────

def _find_header_rows(raw: pd.DataFrame) -> tuple:
    """
    Auto-detect (section_row_idx, header_row_idx) for Daily Operations.
    Agthala: section=0, header=1.
    Data template (extra blank row 0): section=1, header=2.
    Strategy: find the first row whose col-0 == "date" (case-insensitive).
    """
    for r in range(min(6, len(raw))):
        v = str(raw.iloc[r, 0]).replace("\n", " ").strip().lower()
        if v == "date":
            return max(0, r - 1), r
    return 0, 1   # fallback


def _build_col_index(raw: pd.DataFrame) -> dict:
    section_row_idx, header_row_idx = _find_header_rows(raw)

    header = [
        str(v).replace("\n", " ").strip().lower() if pd.notna(v) else ""
        for v in raw.iloc[header_row_idx]
    ]
    section = [
        str(v).replace("\n", " ").strip().lower() if pd.notna(v) else ""
        for v in raw.iloc[section_row_idx]
    ]

    idx: dict = {}
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

def _to_num(s) -> pd.Series:
    if not isinstance(s, pd.Series):
        return pd.Series(dtype=float)
    return pd.to_numeric(s, errors="coerce")


def load_daily_operations(wb_bytes: bytes, plant_name: str) -> pd.DataFrame:
    raw = pd.read_excel(io.BytesIO(wb_bytes),
                        sheet_name="Daily Operations", header=None)
    _, header_row_idx = _find_header_rows(raw)
    data_start = header_row_idx + 2   # skip units row

    # Scan forward for first actual date row
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


def load_lab_analysis(wb_bytes: bytes, plant_name: str) -> pd.DataFrame:
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


def load_dung_quality(wb_bytes: bytes, plant_name: str) -> pd.DataFrame:
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


def load_fertilizer_quality(wb_bytes: bytes, plant_name: str) -> pd.DataFrame:
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
        sr_col, "Sr. No.", "Sr.\nNo.",
        "Sample Date", "Sample\nDate",
        "Material Name", "Material\nName",
        "Batch / Type", "Batch /\nType",
        "Mfg Date / Month", "Mfg Date\n/ Month",
        "Remarks / Sampler", "Remarks /\nSampler",
    }
    for col in data.columns:
        if col in non_numeric:
            continue
        if not isinstance(data[col], pd.Series):
            continue
        if data[col].dtype == object:
            try:
                data[col] = pd.to_numeric(data[col], errors="coerce")
            except Exception:
                pass

    data["plant"] = plant_name
    return data.reset_index(drop=True)


@st.cache_data(show_spinner=False)
def load_plant(file_bytes: bytes, plant_name: str) -> dict:
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
# CHART THEME & HELPERS
# ─────────────────────────────────────────────────────────────────────────────

CHART_BG   = "#07111f"
CHART_GRID = "#112240"
FONT_COLOR = "#c8d8f0"

def _pmap(plants) -> dict:
    return {p: PALETTE[i % len(PALETTE)] for i, p in enumerate(sorted(plants))}

def _ma(s: pd.Series, w: int) -> pd.Series:
    return s.rolling(w, min_periods=1).mean()

def _base(fig, height=480):
    fig.update_layout(
        paper_bgcolor=CHART_BG,
        plot_bgcolor=CHART_BG,
        font=dict(color=FONT_COLOR, family="DM Sans, sans-serif", size=12),
        legend=dict(
            bgcolor="rgba(7,17,31,0.8)",
            bordercolor="#1a2d4a",
            borderwidth=1,
            font=dict(size=11),
        ),
        hovermode="x unified",
        height=height,
        title_x=0,
        title_font=dict(size=14, color="#e8f0fe", family="Space Mono, monospace"),
        margin=dict(l=12, r=12, t=48, b=12),
    )
    fig.update_xaxes(
        showgrid=True, gridcolor=CHART_GRID, gridwidth=1,
        zeroline=False, showline=True, linecolor="#1a2d4a",
        tickfont=dict(size=11),
    )
    fig.update_yaxes(
        showgrid=True, gridcolor=CHART_GRID, gridwidth=1,
        zeroline=False, showline=False,
        tickfont=dict(size=11),
    )
    return fig


def line_fig(df: pd.DataFrame, x: str, ycol: str,
             title: str, ylab: str = "", ma: int = 7,
             height: int = 480) -> go.Figure:
    fig = go.Figure()
    if df.empty or ycol not in df.columns:
        return _base(fig, height)
    cmap = _pmap(df["plant"].unique())
    for p, gdf in df.groupby("plant"):
        c = cmap[p]
        s = gdf[ycol]
        valid = s.notna().sum()
        # Raw data — thinner, more transparent
        fig.add_trace(go.Scatter(
            x=gdf[x], y=s, mode="lines", name=p,
            line=dict(color=c, width=1.4),
            opacity=0.45,
            showlegend=True,
        ))
        # Moving average — thick & bright
        if ma > 1 and valid >= ma:
            fig.add_trace(go.Scatter(
                x=gdf[x], y=_ma(s, ma), mode="lines",
                name=f"{p} ({ma}d avg)",
                line=dict(color=c, width=2.8),
                opacity=1.0,
            ))
        elif valid > 0:
            # If not enough points for MA, show raw boldly
            fig.data[-1].update(opacity=0.9, line=dict(width=2.2))

    fig.update_layout(title=title, yaxis_title=ylab)
    return _base(fig, height)


def dual_line_fig(df: pd.DataFrame, x: str,
                  col_a: str, label_a: str,
                  col_b: str, label_b: str,
                  title: str, height: int = 480) -> go.Figure:
    fig = go.Figure()
    if df.empty:
        return _base(fig, height)
    cmap = _pmap(df["plant"].unique())
    for p, gdf in df.groupby("plant"):
        c = cmap[p]
        if col_a in gdf.columns:
            fig.add_trace(go.Scatter(
                x=gdf[x], y=gdf[col_a], name=f"{p} – {label_a}",
                line=dict(color=c, width=2.4),
            ))
        if col_b in gdf.columns:
            fig.add_trace(go.Scatter(
                x=gdf[x], y=gdf[col_b], name=f"{p} – {label_b}",
                line=dict(color=c, width=2.4, dash="dot"),
            ))
    fig.update_layout(title=title)
    return _base(fig, height)


def bar_fig(df: pd.DataFrame, x: str, y: str, title: str,
            color: str = "plant", barmode: str = "group",
            height: int = 480) -> go.Figure:
    cmap = _pmap(df["plant"].unique()) if "plant" in df.columns else {}
    fig = px.bar(df, x=x, y=y, color=color, barmode=barmode,
                 title=title, color_discrete_map=cmap, template="plotly_dark")
    fig.update_traces(marker_line_width=0)
    fig.update_layout(
        paper_bgcolor=CHART_BG, plot_bgcolor=CHART_BG,
        font=dict(color=FONT_COLOR, family="DM Sans, sans-serif"),
        title_font=dict(size=14, color="#e8f0fe", family="Space Mono, monospace"),
        height=height, title_x=0,
        margin=dict(l=12, r=12, t=48, b=12),
    )
    fig.update_xaxes(showgrid=False, linecolor="#1a2d4a")
    fig.update_yaxes(showgrid=True, gridcolor=CHART_GRID)
    return fig


def scatter_fig(df: pd.DataFrame, x: str, y: str, title: str,
                color: str = "sample_point", height: int = 480) -> go.Figure:
    cmap = _pmap(df[color].unique()) if color in df.columns else {}
    fig = px.scatter(df, x=x, y=y, color=color, trendline="ols",
                     title=title, color_discrete_map=cmap, template="plotly_dark")
    fig.update_traces(marker=dict(size=6, opacity=0.7))
    fig.update_layout(
        paper_bgcolor=CHART_BG, plot_bgcolor=CHART_BG,
        font=dict(color=FONT_COLOR, family="DM Sans, sans-serif"),
        title_font=dict(size=14, color="#e8f0fe", family="Space Mono, monospace"),
        height=height, title_x=0,
        margin=dict(l=12, r=12, t=48, b=12),
    )
    fig.update_xaxes(showgrid=True, gridcolor=CHART_GRID)
    fig.update_yaxes(showgrid=True, gridcolor=CHART_GRID)
    return fig


def sec(text: str):
    st.markdown(f'<div class="sec-hdr">{text}</div>', unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────

def sidebar() -> tuple:
    with st.sidebar:
        st.markdown("## ⚡ BIOGAS ANALYTICS")
        st.markdown("---")

        uploaded = st.file_uploader(
            "📂 Upload plant Excel file(s)",
            type=["xlsx"],
            accept_multiple_files=True,
            help="One file per plant — Unified Daily Report format.",
        )

        all_data: dict = {}
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
            return {}, [], {}

        st.markdown("---")
        st.markdown("### 🏭 Plants")
        plants = list(all_data.keys())
        selected = st.multiselect("Show", plants, default=plants)

        # Date range
        all_ops = [all_data[p]["ops"] for p in selected
                   if p in all_data and not all_data[p]["ops"].empty]
        date_filter: dict = {}
        if all_ops:
            combined = pd.concat(all_ops, ignore_index=True)
            mn = combined["date"].min().date()
            mx = combined["date"].max().date()
            st.markdown("### 📅 Date Range")
            dr = st.date_input("Filter", value=(mn, mx),
                                min_value=mn, max_value=mx)
            date_filter = {
                "start": pd.Timestamp(dr[0]),
                "end":   pd.Timestamp(dr[1] if len(dr) > 1 else dr[0]),
            }

        st.markdown("---")
        st.markdown("### ⚙️ Chart Options")
        # ✅ CORRECT: key= only; value read via session_state.get() later
        st.slider("Moving average (days)", 1, 30, 7, key="ma_window")

        return all_data, selected, date_filter


# ─────────────────────────────────────────────────────────────────────────────
# DATA FILTERS
# ─────────────────────────────────────────────────────────────────────────────

def get_ops(all_data, selected, date_filter) -> pd.DataFrame:
    frames = []
    for p in selected:
        df = all_data[p]["ops"]
        if df.empty:
            continue
        if date_filter:
            df = df[(df["date"] >= date_filter["start"]) &
                    (df["date"] <= date_filter["end"])]
        frames.append(df)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def get_lab(all_data, selected, date_filter) -> pd.DataFrame:
    frames = []
    for p in selected:
        df = all_data[p]["lab"]
        if df.empty:
            continue
        if date_filter:
            df = df[(df["date"] >= date_filter["start"]) &
                    (df["date"] <= date_filter["end"])]
        frames.append(df)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


# ─────────────────────────────────────────────────────────────────────────────
# KPI ROW
# ─────────────────────────────────────────────────────────────────────────────

def render_kpis(ops: pd.DataFrame):
    if ops.empty:
        st.warning("No operational data for the selected range.")
        return

    def sm(col): return ops[col].dropna().mean() if col in ops.columns else float("nan")
    def ss(col): return ops[col].dropna().sum()  if col in ops.columns else float("nan")

    kpis = [
        ("🌿", "Avg Biogas Gen",    f"{sm('total_generated_gas'):.1f}",  "m³ / day"),
        ("🏭", "Total CBG Sales",   f"{ss('cbg_sales_kg'):,.0f}",        "kg total"),
        ("⚗️", "Avg Purif. Eff.",   f"{sm('purif_efficiency'):.1f}",     "% efficiency"),
        ("🔬", "Avg CH₄ Raw",       f"{sm('raw_ch4'):.1f}",              "% purity"),
        ("✨", "Avg CH₄ Pure",      f"{sm('pure_ch4'):.1f}",             "% purity"),
        ("🌡️", "Avg Digester Temp", f"{sm('digester_temp'):.1f}",        "°C"),
        ("⚡", "Avg VPSA Power",    f"{sm('vpsa_kwh_total'):.1f}",       "KWH / day"),
        ("🐄", "Avg Dung Input",    f"{sm('dung_tons'):.1f}",            "tons / day"),
    ]

    # 4 per row × 2 rows
    row1 = st.columns(4)
    row2 = st.columns(4)
    for i, (icon, label, value, unit) in enumerate(kpis):
        col = (row1 if i < 4 else row2)[i % 4]
        with col:
            st.markdown(f"""
<div class="kpi-card">
  <div class="kpi-icon">{icon}</div>
  <div class="kpi-value">{value}</div>
  <div class="kpi-label">{label} &nbsp;·&nbsp; {unit}</div>
</div>""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# TABS
# ─────────────────────────────────────────────────────────────────────────────

def tab_gas(ops: pd.DataFrame, ma: int):
    sec("📊 GAS PRODUCTION & QUALITY")
    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(line_fig(ops, "date", "total_generated_gas",
                                  "Raw Biogas Generated", "m³/day", ma=ma),
                        use_container_width=True, key="chart_001")
    with c2:
        st.plotly_chart(line_fig(ops, "date", "total_purified_gas",
                                  "Purified Gas Output", "m³/day", ma=ma),
                        use_container_width=True, key="chart_002")

    c3, c4 = st.columns(2)
    with c3:
        st.plotly_chart(dual_line_fig(ops, "date",
                                       "raw_ch4", "CH₄", "raw_co2", "CO₂",
                                       "Raw Biogas Composition (%)"),
                        use_container_width=True, key="chart_003")
    with c4:
        st.plotly_chart(dual_line_fig(ops, "date",
                                       "pure_ch4", "CH₄", "pure_co2", "CO₂",
                                       "Purified Gas Composition (%)"),
                        use_container_width=True, key="chart_004")

    sec("⚠️ H₂S CONTAMINATION (PPM)")
    c5, c6 = st.columns(2)
    with c5:
        fig = line_fig(ops, "date", "raw_h2s", "Raw Gas H₂S", "PPM", ma=ma)
        fig.add_hline(y=500, line_dash="dash", line_color="#ff5252",
                       annotation_text="Alert 500 PPM", annotation_font_color="#ff5252")
        st.plotly_chart(fig, use_container_width=True, key="chart_005")
    with c6:
        fig = line_fig(ops, "date", "pure_h2s", "Purified Gas H₂S", "PPM", ma=ma)
        fig.add_hline(y=50, line_dash="dash", line_color="#ffab40",
                       annotation_text="Target <50 PPM", annotation_font_color="#ffab40")
        st.plotly_chart(fig, use_container_width=True, key="chart_006")

    sec("📉 GAS BALANCE")
    c7, c8 = st.columns(2)
    with c7:
        st.plotly_chart(line_fig(ops, "date", "flare_m3",
                                  "Flare Gas (m³/day)", "m³", ma=ma),
                        use_container_width=True, key="chart_007")
    with c8:
        st.plotly_chart(line_fig(ops, "date", "gen_inlet_diff",
                                  "Gen–Inlet Differential (m³)", "m³", ma=ma),
                        use_container_width=True, key="chart_008")


def tab_feed(ops: pd.DataFrame, ma: int):
    sec("🐄 FEEDSTOCK & FEEDING")
    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(line_fig(ops, "date", "dung_tons",
                                  "Dung Collected (tons/day)", "tons", ma=ma),
                        use_container_width=True, key="chart_009")
    with c2:
        st.plotly_chart(line_fig(ops, "date", "total_feed_m3",
                                  "Total Feed to Reactor (m³/day)", "m³", ma=ma),
                        use_container_width=True, key="chart_010")

    c3, c4 = st.columns(2)
    with c3:
        st.plotly_chart(line_fig(ops, "date", "total_filter_water",
                                  "Filter Water Consumed (m³/day)", "m³", ma=ma),
                        use_container_width=True, key="chart_011")
    with c4:
        has_potato = ("waste_potato_tons" in ops.columns and
                      ops["waste_potato_tons"].notna().any())
        if has_potato:
            st.plotly_chart(line_fig(ops, "date", "waste_potato_tons",
                                      "Waste Potato Added (tons/day)", "tons", ma=ma),
                            use_container_width=True, key="chart_012")
        else:
            st.info("No waste-potato data for selected plants / date range.")

    sec("📈 SPECIFIC BIOGAS YIELD")
    ops2 = ops.copy()
    ops2["yield_m3_per_ton"] = np.where(
        ops2["dung_tons"] > 0,
        ops2["total_generated_gas"] / ops2["dung_tons"],
        np.nan,
    )
    st.plotly_chart(line_fig(ops2, "date", "yield_m3_per_ton",
                              "Biogas Yield (m³ per ton of dung)",
                              "m³/ton", ma=ma, height=400),
                    use_container_width=True, key="chart_013")


def tab_purif(ops: pd.DataFrame, ma: int):
    sec("⚗️ PURIFICATION & CBG SALES")
    c1, c2 = st.columns(2)
    with c1:
        fig = line_fig(ops, "date", "purif_efficiency",
                       "Purification Efficiency (%)", "%", ma=ma)
        fig.add_hline(y=95, line_dash="dot", line_color="#69f0ae",
                       annotation_text="Target 95%", annotation_font_color="#69f0ae")
        st.plotly_chart(fig, use_container_width=True, key="chart_014")
    with c2:
        st.plotly_chart(line_fig(ops, "date", "bg_recovery",
                                  "Biogas Recovery (%)", "%", ma=ma),
                        use_container_width=True, key="chart_015")

    c3, c4 = st.columns(2)
    with c3:
        st.plotly_chart(line_fig(ops, "date", "cbg_sales_kg",
                                  "CBG Sales – Dispenser (kg/day)", "kg", ma=ma),
                        use_container_width=True, key="chart_016")
    with c4:
        st.plotly_chart(line_fig(ops, "date", "total_sales_kg",
                                  "Total CBG Sales incl. Cascade (kg/day)", "kg", ma=ma),
                        use_container_width=True, key="chart_017")

    sec("📅 MONTHLY CBG SALES")
    monthly = (ops.assign(month=ops["date"].dt.to_period("M").astype(str))
                  .groupby(["month", "plant"], as_index=False)["cbg_sales_kg"].sum())
    if not monthly.empty:
        st.plotly_chart(bar_fig(monthly, "month", "cbg_sales_kg",
                                 "Monthly CBG Sales (kg)", color="plant", height=420),
                        use_container_width=True, key="chart_018")

    c5, c6 = st.columns(2)
    with c5:
        st.plotly_chart(line_fig(ops, "date", "num_vehicles",
                                  "Vehicles Served / Day", "count", ma=1),
                        use_container_width=True, key="chart_019")
    with c6:
        st.plotly_chart(line_fig(ops, "date", "purif_running_hrs",
                                  "Purification Running Hrs / Day", "hrs", ma=1),
                        use_container_width=True, key="chart_020")


def tab_power(ops: pd.DataFrame, ma: int):
    sec("⚡ POWER & UTILITY CONSUMPTION")
    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(line_fig(ops, "date", "vpsa_kwh_total",
                                  "VPSA Power Consumed (KWH/day)", "KWH", ma=ma),
                        use_container_width=True, key="chart_021")
    with c2:
        st.plotly_chart(line_fig(ops, "date", "bg_mfm_kwh_total",
                                  "Biogas MFM Power (KWH/day)", "KWH", ma=ma),
                        use_container_width=True, key="chart_022")

    c3, c4 = st.columns(2)
    with c3:
        st.plotly_chart(line_fig(ops, "date", "raw_water_m3",
                                  "Raw Water Consumed (m³/day)", "m³", ma=ma),
                        use_container_width=True, key="chart_023")
    with c4:
        st.plotly_chart(line_fig(ops, "date", "poly_kg",
                                  "Poly Consumption (kg/day)", "kg", ma=ma),
                        use_container_width=True, key="chart_024")

    c5, c6 = st.columns(2)
    with c5:
        st.plotly_chart(line_fig(ops, "date", "dg_hrs",
                                  "DG Running Hours / Day", "hrs", ma=1),
                        use_container_width=True, key="chart_025")
    with c6:
        st.plotly_chart(line_fig(ops, "date", "dg_diesel_l",
                                  "DG Diesel Consumed (L/day)", "L", ma=ma),
                        use_container_width=True, key="chart_026")

    sec("💡 SPECIFIC ENERGY INTENSITY")
    ops2 = ops.copy()
    ops2["kwh_per_m3"] = np.where(
        ops2["total_purified_gas"] > 0,
        ops2["vpsa_kwh_total"] / ops2["total_purified_gas"],
        np.nan,
    )
    st.plotly_chart(line_fig(ops2, "date", "kwh_per_m3",
                              "VPSA Specific Energy (KWH / m³ purified gas)",
                              "KWH/m³", ma=ma, height=400),
                    use_container_width=True, key="chart_027")


def tab_digester(ops: pd.DataFrame, ma: int):
    sec("🌡️ DIGESTER CONDITIONS")
    c1, c2 = st.columns(2)
    with c1:
        fig = line_fig(ops, "date", "digester_temp",
                       "Digester Temperature (°C)", "°C", ma=ma)
        fig.add_hline(y=37, line_dash="dash", line_color="#ffab40",
                       annotation_text="Mesophilic 37°C",
                       annotation_font_color="#ffab40")
        fig.add_hrect(y0=35, y1=40, fillcolor="#ffab40", opacity=0.06)
        st.plotly_chart(fig, use_container_width=True, key="chart_028")
    with c2:
        fig = line_fig(ops, "date", "digester_ph",
                       "Digester pH (Mid)", "pH", ma=ma)
        fig.add_hrect(y0=6.8, y1=7.5, fillcolor="#69f0ae", opacity=0.08,
                       annotation_text="Optimal 6.8–7.5",
                       annotation_font_color="#69f0ae")
        st.plotly_chart(fig, use_container_width=True, key="chart_029")

    sec("💧 DEWATERING & SCREW PRESS")
    c3, c4 = st.columns(2)
    with c3:
        st.plotly_chart(dual_line_fig(ops, "date",
                                       "screw_moisture", "Screw Press",
                                       "volute_moisture", "Volute Press",
                                       "Dewatering Moisture (%)"),
                        use_container_width=True, key="chart_030")
    with c4:
        st.plotly_chart(line_fig(ops, "date", "flare_m3",
                                  "Flare Gas (m³/day)", "m³", ma=ma),
                        use_container_width=True, key="chart_031")

    c5, c6, c7 = st.columns(3)
    for col_w, col, title in zip(
        [c5, c6, c7],
        ["screw_press_hrs", "vibro_screen_hrs", "volute_press_hrs"],
        ["Screw Press Hrs/Day", "Vibro Screen Hrs/Day", "Volute Press Hrs/Day"],
    ):
        with col_w:
            st.plotly_chart(line_fig(ops, "date", col, title, "hrs",
                                      ma=1, height=380),
                            use_container_width=True, key=f"chart_digester_{col}")


def tab_lab(all_data: dict, selected: list, date_filter: dict):
    sec("🔬 LAB & SLURRY ANALYSIS")
    lab = get_lab(all_data, selected, date_filter)
    if lab.empty:
        st.info("No lab data for the selected range.")
        return

    pts = sorted(lab["sample_point"].dropna().unique())
    defaults = ([s for s in ["RCD (Raw Cattle Dung)",
                              "Digester Mid Sampling Point",
                              "Mixing Tank", "Slurry Tank"]
                 if s in pts] or pts[:3])
    chosen = st.multiselect("Sample Points", pts, default=defaults)
    if not chosen:
        st.info("Select at least one sample point.")
        return

    lab_f = lab[lab["sample_point"].isin(chosen)]

    params = [
        ("pH",        "pH"),
        ("TS_pct",    "TS (%)"),
        ("VS_pct",    "VS (%)"),
        ("EC_mScm",   "EC (mS/cm)"),
        ("Temp_C",    "Temperature (°C)"),
        ("Carbon_pct","Carbon (%)"),
    ]
    # Two columns layout for lab charts
    param_pairs = [(params[i], params[i+1] if i+1 < len(params) else None)
                   for i in range(0, len(params), 2)]
    for left, right in param_pairs:
        c1, c2 = st.columns(2)
        for col_w, item in zip([c1, c2], [left, right]):
            if item is None:
                continue
            param, label = item
            if param not in lab_f.columns or lab_f[param].dropna().empty:
                continue
            sub = lab_f.dropna(subset=[param])
            fig = px.line(
                sub, x="date", y=param, color="sample_point",
                facet_col="plant" if len(selected) > 1 else None,
                title=f"{label} by Sample Point",
                template="plotly_dark",
            )
            fig.update_layout(
                paper_bgcolor=CHART_BG, plot_bgcolor=CHART_BG,
                font=dict(color=FONT_COLOR, family="DM Sans, sans-serif"),
                title_font=dict(size=14, color="#e8f0fe",
                                family="Space Mono, monospace"),
                height=420, margin=dict(l=12, r=12, t=48, b=12),
            )
            fig.update_xaxes(showgrid=True, gridcolor=CHART_GRID)
            fig.update_yaxes(showgrid=True, gridcolor=CHART_GRID)
            with col_w:
                st.plotly_chart(fig, use_container_width=True, key=f"chart_lab_{param}")

    sec("📊 TS vs VS CORRELATION")
    valid = lab_f.dropna(subset=["TS_pct", "VS_pct"])
    if not valid.empty:
        st.plotly_chart(scatter_fig(valid, "TS_pct", "VS_pct",
                                     "TS (%) vs VS (%) — by Sample Point",
                                     height=460),
                        use_container_width=True, key="chart_034")


def tab_compare(all_data: dict, selected: list, date_filter: dict):
    sec("📊 CROSS-PLANT COMPARISON")
    if len(selected) < 2:
        st.info("Select at least 2 plants from the sidebar.")
        return

    ops = get_ops(all_data, selected, date_filter)
    if ops.empty:
        st.warning("No operational data.")
        return

    monthly = (
        ops.assign(month=ops["date"].dt.to_period("M").astype(str))
           .groupby(["month", "plant"], as_index=False)
           .agg(
               total_generated_gas=("total_generated_gas", "sum"),
               total_purified_gas =("total_purified_gas",  "sum"),
               cbg_sales_kg       =("cbg_sales_kg",        "sum"),
               avg_purif_eff      =("purif_efficiency",     "mean"),
               avg_ch4_raw        =("raw_ch4",              "mean"),
               avg_ch4_pure       =("pure_ch4",             "mean"),
               avg_digester_temp  =("digester_temp",        "mean"),
               dung_tons          =("dung_tons",            "sum"),
           )
    )

    metrics = [
        ("total_generated_gas", "Monthly Raw Biogas (m³)"),
        ("total_purified_gas",  "Monthly Purified Gas (m³)"),
        ("cbg_sales_kg",        "Monthly CBG Sales (kg)"),
        ("avg_purif_eff",       "Avg Purification Efficiency (%)"),
        ("avg_ch4_raw",         "Avg Raw CH₄ (%)"),
        ("avg_digester_temp",   "Avg Digester Temp (°C)"),
        ("dung_tons",           "Total Dung Collected (tons)"),
    ]
    for col, title in metrics:
        if col in monthly.columns and monthly[col].notna().any():
            st.plotly_chart(
                bar_fig(monthly, "month", col, title, color="plant", height=400),
                use_container_width=True,
                key=f"chart_compare_{col}",
            )

    sec("🕸️ PLANT PROFILE RADAR (PERIOD AVERAGES)")
    radar_m = ["avg_purif_eff", "avg_ch4_raw", "avg_ch4_pure"]
    latest  = monthly.groupby("plant")[radar_m].mean().reset_index()
    if not latest.empty:
        fig = go.Figure()
        cmap = _pmap(latest["plant"].tolist())
        for _, row in latest.iterrows():
            pname = row["plant"]
            vals  = [row.get(m, 0) for m in radar_m] + [row.get(radar_m[0], 0)]
            labels = ["Purif Eff %", "CH₄ Raw %", "CH₄ Pure %", "Purif Eff %"]
            fig.add_trace(go.Scatterpolar(
                r=vals, theta=labels, fill="toself", name=pname,
                line=dict(color=cmap.get(pname, PALETTE[0]), width=2),
                fillcolor=cmap.get(pname, PALETTE[0]).replace(")", ",0.15)").replace("rgb(", "rgba("),
            ))
        fig.update_layout(
            polar=dict(
                radialaxis=dict(visible=True, range=[0, 100],
                                tickfont=dict(size=10, color="#6b8fb5"),
                                gridcolor="#1a2d4a"),
                angularaxis=dict(tickfont=dict(size=12, color="#c8d8f0"),
                                 gridcolor="#1a2d4a"),
                bgcolor="#07111f",
            ),
            paper_bgcolor=CHART_BG,
            font=dict(color=FONT_COLOR, family="DM Sans, sans-serif"),
            height=500,
            legend=dict(bgcolor="rgba(7,17,31,0.8)", bordercolor="#1a2d4a",
                        borderwidth=1),
        )
        st.plotly_chart(fig, use_container_width=True, key="chart_035")


def tab_dung_routes(all_data: dict, selected: list, date_filter: dict):
    sec("🚛 DUNG ROUTE QUALITY")
    frames = []
    for p in selected:
        df = all_data[p]["dung"]
        if df.empty:
            continue
        if date_filter:
            df = df[(df["date"] >= date_filter["start"]) &
                    (df["date"] <= date_filter["end"])]
        frames.append(df)

    if not frames:
        st.info("No dung route quality data for this selection.")
        return

    dung = pd.concat(frames, ignore_index=True)
    routes = sorted(dung["route"].dropna().unique())
    chosen = st.multiselect("Routes", routes,
                             default=routes[:6] if len(routes) > 6 else routes)
    if not chosen:
        return
    dung_f = dung[dung["route"].isin(chosen)]

    metrics = ["Sand (%)", "pH", "EC", "TS (%)"]
    pairs   = [(metrics[i], metrics[i+1] if i+1 < len(metrics) else None)
               for i in range(0, len(metrics), 2)]
    for left, right in pairs:
        c1, c2 = st.columns(2)
        for col_w, needle in zip([c1, c2], [left, right]):
            if needle is None:
                continue
            matching = [c for c in dung_f.columns
                        if c.strip().lower() == needle.strip().lower()]
            if not matching:
                continue
            rc = matching[0]
            if dung_f[rc].dropna().empty:
                continue
            fig = px.box(dung_f.dropna(subset=[rc]), x="route", y=rc,
                         color="plant", title=f"Dung Route – {needle}",
                         template="plotly_dark")
            fig.update_layout(
                paper_bgcolor=CHART_BG, plot_bgcolor=CHART_BG,
                font=dict(color=FONT_COLOR, family="DM Sans, sans-serif"),
                title_font=dict(size=14, color="#e8f0fe",
                                family="Space Mono, monospace"),
                height=440, margin=dict(l=12, r=12, t=48, b=12),
            )
            fig.update_xaxes(showgrid=False)
            fig.update_yaxes(showgrid=True, gridcolor=CHART_GRID)
            with col_w:
                st.plotly_chart(fig, use_container_width=True, key=f"chart_dung_{rc}")


def tab_fertilizer(all_data: dict, selected: list):
    sec("🌱 ORGANIC FERTILIZER QUALITY")
    frames = [all_data[p]["fert"] for p in selected
              if not all_data[p]["fert"].empty]
    if not frames:
        st.info("No fertilizer quality data.")
        return

    fert = pd.concat(frames, ignore_index=True)
    num_cols = fert.select_dtypes(include=[np.number]).columns.tolist()
    if not num_cols:
        st.dataframe(fert.head(30), use_container_width=True)
        return

    c1, c2 = st.columns([1, 3])
    with c1:
        param = st.selectbox("Parameter", num_cols)
    mat_col = next((c for c in fert.columns if "material" in str(c).lower()), None)

    fert_plot = fert.dropna(subset=[param])
    if fert_plot.empty:
        st.info(f"No data for {param}.")
        return

    if mat_col:
        fig = px.box(fert_plot, x=mat_col, y=param,
                     color="plant", title=f"{param} by Material Type",
                     template="plotly_dark",
                     points="all")
    else:
        fig = px.box(fert_plot, y=param,
                     color="plant", title=f"{param}",
                     template="plotly_dark",
                     points="all")

    fig.update_traces(marker=dict(size=4, opacity=0.6))
    fig.update_layout(
        paper_bgcolor=CHART_BG, plot_bgcolor=CHART_BG,
        font=dict(color=FONT_COLOR, family="DM Sans, sans-serif"),
        title_font=dict(size=14, color="#e8f0fe", family="Space Mono, monospace"),
        height=500, margin=dict(l=12, r=12, t=48, b=12),
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=True, gridcolor=CHART_GRID)
    st.plotly_chart(fig, use_container_width=True, key="chart_037")

    with st.expander("📋 Raw fertilizer data"):
        st.dataframe(fert, use_container_width=True)


def tab_raw(ops: pd.DataFrame):
    sec("🗄️ RAW DATA EXPLORER")
    if ops.empty:
        st.info("No data loaded.")
        return

    # ✅ FIX: all_cols excludes 'plant'; default_show must ONLY use cols in all_cols
    all_cols = [c for c in ops.columns if c != "plant"]
    preferred = ["date", "dung_tons", "total_generated_gas", "total_purified_gas",
                 "cbg_sales_kg", "purif_efficiency", "raw_ch4", "pure_ch4",
                 "digester_temp"]
    # Only keep preferred cols that actually exist in all_cols (not ops.columns!)
    default_show = [c for c in preferred if c in all_cols]

    sel  = st.multiselect("Columns to display", all_cols, default=default_show)
    # Always prepend plant + date for readability if present
    show_cols = []
    for must in ["date", "plant"]:
        if must in ops.columns and must not in sel:
            show_cols.append(must)
    show_cols += [c for c in sel if c in ops.columns]

    if show_cols:
        st.dataframe(
            ops[show_cols].sort_values("date", ascending=False),
            use_container_width=True,
            height=560,
        )

    st.download_button(
        "⬇️ Download filtered data as CSV",
        ops.to_csv(index=False).encode("utf-8"),
        "biogas_filtered_data.csv",
        "text/csv",
    )

    with st.expander("📊 Summary Statistics"):
        num_c = ops.select_dtypes(include=[np.number]).columns
        st.dataframe(ops[num_c].describe().T.round(2), use_container_width=True)


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    all_data, selected, date_filter = sidebar()

    if not all_data or not selected:
        st.markdown("## ⚡ Biogas Plant Analytics Dashboard")
        st.markdown("""
**Getting started:**
1. Upload one `.xlsx` file per plant using the sidebar (Unified Daily Report format).
2. Rename each plant if needed.
3. Set the date range filter.
4. Explore all 10 analysis tabs below.

**Notes:** Any number of plant files can be loaded simultaneously.
Columns are detected by name — extra or reordered columns are handled automatically.
        """)
        return

    badges = " ".join(
        f'<span class="plant-badge">🏭 {p}</span>' for p in selected
    )
    st.markdown(f"<h2 style='font-family:Space Mono,monospace;color:#e8f0fe;"
                f"font-size:1.4rem;letter-spacing:0.04em;margin-bottom:4px'>"
                f"⚡ BIOGAS ANALYTICS &nbsp; {badges}</h2>",
                unsafe_allow_html=True)

    # ✅ CORRECT: read slider value from session_state — never assign to it
    ma = st.session_state.get("ma_window", 7)

    ops = get_ops(all_data, selected, date_filter)

    render_kpis(ops)
    st.markdown("---")

    tabs = st.tabs([
        "📊 Gas Production", "🐄 Feedstock", "⚗️ Purification & Sales",
        "⚡ Power & Utilities", "🌡️ Digester & Dewatering", "🔬 Lab Analysis",
        "📊 Cross-Plant Compare", "🚛 Dung Routes", "🌱 Fertilizer", "🗄️ Raw Data",
    ])

    with tabs[0]: tab_gas(ops, ma)
    with tabs[1]: tab_feed(ops, ma)
    with tabs[2]: tab_purif(ops, ma)
    with tabs[3]: tab_power(ops, ma)
    with tabs[4]: tab_digester(ops, ma)
    with tabs[5]: tab_lab(all_data, selected, date_filter)
    with tabs[6]: tab_compare(all_data, selected, date_filter)
    with tabs[7]: tab_dung_routes(all_data, selected, date_filter)
    with tabs[8]: tab_fertilizer(all_data, selected)
    with tabs[9]: tab_raw(ops)


if __name__ == "__main__":
    main()
