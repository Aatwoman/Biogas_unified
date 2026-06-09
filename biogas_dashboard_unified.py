"""
Biogas Plant Analytics Dashboard  ·  Universal Format  ·  Streamlit
=====================================================================
v7 — Full overhaul
  1. x-axis locked to selected date range (no auto-compress)
  2. Flexible date filter: month picker + custom range
  3. Plant selection: individual view or compare mode
  4. Full light mode
  5. Cross-plant compare tab fixed
  6. Raw data tab fixed
  7. Individual vs compare toggle
  8. All tabs work correctly regardless of plant count
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

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
    background-color: #f5f7fa !important;
    color: #1a2740 !important;
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #1a2d4a 0%, #0f1f38 100%) !important;
    border-right: 1px solid #2a4a7a;
}
[data-testid="stSidebar"] * { color: #c8d8f0 !important; }
[data-testid="stSidebar"] h2 {
    font-family: 'Space Mono', monospace;
    font-size: 1rem;
    letter-spacing: 0.06em;
    color: #4fc3f7 !important;
}
[data-testid="stSidebar"] label { color: #a0bcd8 !important; }
[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] .stMultiSelect label,
[data-testid="stSidebar"] .stSlider label { color: #a0bcd8 !important; }

/* ── Main area ── */
.stApp { background-color: #f0f4f8 !important; }
[data-testid="stMainBlockContainer"] { padding: 1.5rem 2rem; }

/* ── KPI Cards ── */
.kpi-card {
    background: #ffffff;
    border: 1px solid #d1dce8;
    border-top: 3px solid #2979ff;
    border-radius: 10px;
    padding: 16px 18px 12px;
    box-shadow: 0 2px 8px rgba(26,45,74,0.07);
}
.kpi-value {
    font-family: 'Space Mono', monospace;
    font-size: 1.65rem;
    font-weight: 700;
    color: #1565c0;
    line-height: 1.1;
    letter-spacing: -0.02em;
}
.kpi-label {
    font-size: 0.70rem;
    font-weight: 600;
    color: #5a7a9a;
    margin-top: 5px;
    text-transform: uppercase;
    letter-spacing: 0.07em;
}
.kpi-icon { font-size: 1.3rem; margin-bottom: 6px; }

/* ── Section headers ── */
.sec-hdr {
    background: #e8f0fe;
    border-left: 3px solid #2979ff;
    color: #1a2d4a;
    padding: 9px 16px;
    border-radius: 0 8px 8px 0;
    font-family: 'Space Mono', monospace;
    font-size: 0.82rem;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    margin: 18px 0 10px;
}

/* ── Plant badges ── */
.plant-badge {
    display: inline-block;
    background: #e3f2fd;
    border: 1px solid #90caf9;
    border-radius: 20px;
    padding: 3px 12px;
    font-family: 'Space Mono', monospace;
    font-size: 0.76rem;
    color: #1565c0;
    margin: 2px 3px;
}
.compare-badge {
    display: inline-block;
    background: #fff3e0;
    border: 1px solid #ffb74d;
    border-radius: 20px;
    padding: 3px 12px;
    font-family: 'Space Mono', monospace;
    font-size: 0.76rem;
    color: #e65100;
    margin: 2px 3px;
}

/* ── Tabs ── */
[data-testid="stTabs"] [data-baseweb="tab-list"] {
    background: #e8eef5;
    border-radius: 10px;
    padding: 3px;
    gap: 2px;
}
[data-testid="stTabs"] [data-baseweb="tab"] {
    font-family: 'Inter', sans-serif;
    font-size: 0.78rem;
    font-weight: 500;
    padding: 7px 13px;
    border-radius: 7px;
    color: #5a7a9a;
}
[data-testid="stTabs"] [aria-selected="true"] {
    background: #ffffff !important;
    color: #1565c0 !important;
    box-shadow: 0 1px 4px rgba(26,45,74,0.12);
}

/* ── Chart containers ── */
[data-testid="stPlotlyChart"] {
    background: #ffffff;
    border: 1px solid #d8e4f0;
    border-radius: 10px;
    padding: 4px;
    box-shadow: 0 1px 4px rgba(26,45,74,0.06);
}

/* ── Dataframe ── */
[data-testid="stDataFrame"] {
    border: 1px solid #d8e4f0;
    border-radius: 8px;
    box-shadow: 0 1px 4px rgba(26,45,74,0.04);
}

/* ── Info / warning ── */
.stAlert { border-radius: 8px; }

/* ── Expander ── */
[data-testid="stExpander"] {
    background: #ffffff;
    border: 1px solid #d8e4f0;
    border-radius: 8px;
}

/* ── Mode toggle banner ── */
.mode-banner {
    background: linear-gradient(90deg, #e3f2fd 0%, #f3e5f5 100%);
    border: 1px solid #90caf9;
    border-radius: 8px;
    padding: 8px 16px;
    margin-bottom: 12px;
    font-size: 0.82rem;
    color: #1a2d4a;
    font-weight: 500;
}

hr { border-color: #d1dce8 !important; margin: 1rem 0 !important; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# COLOUR PALETTE  (works on white background)
# ─────────────────────────────────────────────────────────────────────────────
PALETTE = [
    "#1565c0", "#2e7d32", "#e65100", "#6a1b9a",
    "#00838f", "#c62828", "#4527a0", "#558b2f",
    "#ad1457", "#00695c",
]

# Chart theme — light
CHART_BG   = "#ffffff"
CHART_GRID = "#e8eef5"
FONT_COLOR = "#1a2740"

# ─────────────────────────────────────────────────────────────────────────────
# COLUMN DEFINITIONS (unchanged)
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
# HEADER DETECTION + LOADERS  (unchanged logic)
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
# CHART HELPERS  (light mode, xrange support)
# ─────────────────────────────────────────────────────────────────────────────

def _pmap(plants):
    return {p: PALETTE[i % len(PALETTE)] for i, p in enumerate(sorted(plants))}

def _hex_to_rgba(hex_color, alpha=0.15):
    """Convert '#rrggbb' to 'rgba(r,g,b,alpha)' for Plotly fill colors."""
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"

def _ma(s, w):
    return s.rolling(w, min_periods=1).mean()

def _base(fig, height=480, xrange=None):
    fig.update_layout(
        paper_bgcolor=CHART_BG,
        plot_bgcolor=CHART_BG,
        font=dict(color=FONT_COLOR, family="Inter, sans-serif", size=12),
        legend=dict(
            bgcolor="rgba(255,255,255,0.9)",
            bordercolor="#d1dce8",
            borderwidth=1,
            font=dict(size=11, color=FONT_COLOR),
        ),
        hovermode="x unified",
        height=height,
        title_x=0,
        title_font=dict(size=14, color="#1a2d4a", family="Space Mono, monospace"),
        margin=dict(l=12, r=12, t=48, b=12),
    )
    xaxis_kw = dict(
        showgrid=True, gridcolor=CHART_GRID, gridwidth=1,
        zeroline=False, showline=True, linecolor="#d1dce8",
        tickfont=dict(size=11, color=FONT_COLOR),
        tickcolor=FONT_COLOR,
        type="date",
        rangemode="normal",
        autorange=False if xrange is not None else True,
    )
    if xrange is not None:
        xaxis_kw["range"] = xrange
    fig.update_xaxes(**xaxis_kw)
    fig.update_yaxes(
        showgrid=True, gridcolor=CHART_GRID, gridwidth=1,
        zeroline=False, showline=False,
        tickfont=dict(size=11, color=FONT_COLOR),
    )
    return fig


def _xrange_from_filter(date_filter):
    """Return [start, end] list for Plotly xaxis range, or None.
    Pads start by -1 day and end by +1 day so edge points are not clipped.
    """
    if not date_filter:
        return None
    s = date_filter.get("start")
    e = date_filter.get("end")
    if s is None or e is None:
        return None
    import pandas as _pd
    s_pad = (s - _pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    e_pad = (e + _pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    return [s_pad, e_pad]


def line_fig(df, x, ycol, title, ylab="", ma=7, height=480, xrange=None):
    fig = go.Figure()
    if df.empty or ycol not in df.columns:
        return _base(fig, height, xrange=xrange)
    cmap = _pmap(df["plant"].unique())
    for p, gdf in df.groupby("plant"):
        c = cmap[p]
        s = gdf[ycol]
        valid = s.notna().sum()
        fig.add_trace(go.Scatter(
            x=gdf[x], y=s, mode="lines", name=p,
            line=dict(color=c, width=1.4),
            opacity=0.35, showlegend=True,
        ))
        if ma > 1 and valid >= ma:
            fig.add_trace(go.Scatter(
                x=gdf[x], y=_ma(s, ma), mode="lines",
                name=f"{p} ({ma}d avg)",
                line=dict(color=c, width=2.6),
                opacity=1.0,
            ))
        elif valid > 0:
            fig.data[-1].update(opacity=0.9, line=dict(width=2.2))
    fig.update_layout(title=title, yaxis_title=ylab)
    return _base(fig, height, xrange=xrange)


def dual_line_fig(df, x, col_a, label_a, col_b, label_b, title,
                  height=480, xrange=None):
    fig = go.Figure()
    if df.empty:
        return _base(fig, height, xrange=xrange)
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
    return _base(fig, height, xrange=xrange)


def bar_fig(df, x, y, title, color="plant", barmode="group", height=480):
    cmap = _pmap(df["plant"].unique()) if "plant" in df.columns else {}
    fig = px.bar(df, x=x, y=y, color=color, barmode=barmode,
                 title=title, color_discrete_map=cmap)
    fig.update_traces(marker_line_width=0)
    fig.update_layout(
        paper_bgcolor=CHART_BG, plot_bgcolor=CHART_BG,
        font=dict(color=FONT_COLOR, family="Inter, sans-serif"),
        title_font=dict(size=14, color="#1a2d4a", family="Space Mono, monospace"),
        legend=dict(bgcolor="rgba(255,255,255,0.9)", bordercolor="#d1dce8",
                    borderwidth=1, font=dict(color=FONT_COLOR)),
        height=height, title_x=0,
        margin=dict(l=12, r=12, t=48, b=12),
    )
    fig.update_xaxes(showgrid=False, linecolor="#d1dce8",
                     tickfont=dict(color=FONT_COLOR))
    fig.update_yaxes(showgrid=True, gridcolor=CHART_GRID,
                     tickfont=dict(color=FONT_COLOR))
    return fig


def scatter_fig(df, x, y, title, color="sample_point", height=480):
    cmap = _pmap(df[color].unique()) if color in df.columns else {}
    fig = px.scatter(df, x=x, y=y, color=color, trendline="ols",
                     title=title, color_discrete_map=cmap)
    fig.update_traces(marker=dict(size=6, opacity=0.7))
    fig.update_layout(
        paper_bgcolor=CHART_BG, plot_bgcolor=CHART_BG,
        font=dict(color=FONT_COLOR, family="Inter, sans-serif"),
        title_font=dict(size=14, color="#1a2d4a", family="Space Mono, monospace"),
        legend=dict(bgcolor="rgba(255,255,255,0.9)", bordercolor="#d1dce8",
                    borderwidth=1, font=dict(color=FONT_COLOR)),
        height=height, title_x=0,
        margin=dict(l=12, r=12, t=48, b=12),
    )
    fig.update_xaxes(showgrid=True, gridcolor=CHART_GRID,
                     tickfont=dict(color=FONT_COLOR))
    fig.update_yaxes(showgrid=True, gridcolor=CHART_GRID,
                     tickfont=dict(color=FONT_COLOR))
    return fig


def sec(text):
    st.markdown(f'<div class="sec-hdr">{text}</div>', unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR — file upload, plant selection, date filter, mode
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

        # ── View mode ──
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

        # ── Plant selection ──
        if view_mode == "individual":
            selected_plant = st.selectbox("Plant to view", plants, key="sel_plant_ind")
            selected = [selected_plant]
            compare_plants = []
        else:
            st.markdown("**Select plants to compare:**")
            compare_plants = st.multiselect(
                "Plants", plants, default=plants, key="sel_plant_cmp"
            )
            selected = compare_plants if compare_plants else plants

        # ── Date filter ──
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
                horizontal=False,
            )

            if filter_type == "Month / Year":
                # Build list of available year-months
                all_months = pd.period_range(
                    pd.Period(data_min, "M"),
                    pd.Period(data_max, "M"),
                    freq="M"
                )
                month_strs = [str(m) for m in all_months]
                # Multi-select months
                chosen_months = st.multiselect(
                    "Select months",
                    month_strs,
                    default=month_strs,  # all months by default
                    key="month_picker",
                )
                if chosen_months:
                    periods = [pd.Period(m, "M") for m in chosen_months]
                    start_ts = periods[0].start_time
                    end_ts   = periods[-1].end_time
                    # Use actual min/max across all chosen months
                    start_ts = min(p.start_time for p in periods)
                    end_ts   = max(p.end_time   for p in periods)
                    date_filter = {
                        "start": start_ts,
                        "end":   end_ts,
                        "months": chosen_months,
                    }
                else:
                    date_filter = {}

            elif filter_type == "Custom Range":
                dr = st.date_input(
                    "Date range",
                    value=(data_min, data_max),
                    min_value=data_min,
                    max_value=data_max,
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

            else:  # All Data
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
    # Month-based: filter to exact months if 'months' key present
    if "months" in date_filter:
        periods = [pd.Period(m, "M") for m in date_filter["months"]]
        mask = df["date"].apply(lambda d: pd.Period(d, "M") in periods)
        return df[mask]
    return df[
        (df["date"] >= date_filter["start"]) &
        (df["date"] <= date_filter["end"])
    ]


def get_ops(all_data, selected, date_filter):
    frames = []
    for p in selected:
        if p not in all_data:
            continue
        df = all_data[p]["ops"]
        if df.empty:
            continue
        frames.append(_apply_date_filter(df, date_filter))
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def get_lab(all_data, selected, date_filter):
    frames = []
    for p in selected:
        if p not in all_data:
            continue
        df = all_data[p]["lab"]
        if df.empty:
            continue
        frames.append(_apply_date_filter(df, date_filter))
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
        ("🌿", "Avg Biogas Gen",    f"{sm('total_generated_gas'):.1f}",  "m³ / day"),
        ("🏭", "Total CBG Sales",   f"{ss('cbg_sales_kg'):,.0f}",        "kg total"),
        ("⚗️", "Avg Purif. Eff.",   f"{sm('purif_efficiency'):.1f}",     "% efficiency"),
        ("🔬", "Avg CH₄ Raw",       f"{sm('raw_ch4'):.1f}",              "% purity"),
        ("✨", "Avg CH₄ Pure",      f"{sm('pure_ch4'):.1f}",             "% purity"),
        ("🌡️", "Avg Digester Temp", f"{sm('digester_temp'):.1f}",        "°C"),
        ("⚡", "Avg VPSA Power",    f"{sm('vpsa_kwh_total'):.1f}",       "KWH / day"),
        ("🐄", "Avg Dung Input",    f"{sm('dung_tons'):.1f}",            "tons / day"),
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
  <div class="kpi-label">{label} &nbsp;·&nbsp; {unit}</div>
</div>""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# TABS
# ─────────────────────────────────────────────────────────────────────────────

def tab_gas(ops, ma, xr):
    sec("📊 GAS PRODUCTION & QUALITY")
    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(line_fig(ops, "date", "total_generated_gas",
                                  "Raw Biogas Generated", "m³/day", ma=ma, xrange=xr),
                        use_container_width=True, key="chart_001")
    with c2:
        st.plotly_chart(line_fig(ops, "date", "total_purified_gas",
                                  "Purified Gas Output", "m³/day", ma=ma, xrange=xr),
                        use_container_width=True, key="chart_002")

    c3, c4 = st.columns(2)
    with c3:
        st.plotly_chart(dual_line_fig(ops, "date",
                                       "raw_ch4", "CH₄", "raw_co2", "CO₂",
                                       "Raw Biogas Composition (%)", xrange=xr),
                        use_container_width=True, key="chart_003")
    with c4:
        st.plotly_chart(dual_line_fig(ops, "date",
                                       "pure_ch4", "CH₄", "pure_co2", "CO₂",
                                       "Purified Gas Composition (%)", xrange=xr),
                        use_container_width=True, key="chart_004")

    sec("⚠️ H₂S CONTAMINATION (PPM)")
    c5, c6 = st.columns(2)
    with c5:
        fig = line_fig(ops, "date", "raw_h2s", "Raw Gas H₂S", "PPM", ma=ma, xrange=xr)
        fig.add_hline(y=500, line_dash="dash", line_color="#c62828",
                       annotation_text="Alert 500 PPM", annotation_font_color="#c62828")
        st.plotly_chart(fig, use_container_width=True, key="chart_005")
    with c6:
        fig = line_fig(ops, "date", "pure_h2s", "Purified Gas H₂S", "PPM", ma=ma, xrange=xr)
        fig.add_hline(y=50, line_dash="dash", line_color="#e65100",
                       annotation_text="Target <50 PPM", annotation_font_color="#e65100")
        st.plotly_chart(fig, use_container_width=True, key="chart_006")

    sec("📉 GAS BALANCE")
    c7, c8 = st.columns(2)
    with c7:
        st.plotly_chart(line_fig(ops, "date", "flare_m3",
                                  "Flare Gas (m³/day)", "m³", ma=ma, xrange=xr),
                        use_container_width=True, key="chart_007")
    with c8:
        st.plotly_chart(line_fig(ops, "date", "gen_inlet_diff",
                                  "Gen–Inlet Differential (m³)", "m³", ma=ma, xrange=xr),
                        use_container_width=True, key="chart_008")


def tab_feed(ops, ma, xr):
    sec("🐄 FEEDSTOCK & FEEDING")
    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(line_fig(ops, "date", "dung_tons",
                                  "Dung Collected (tons/day)", "tons", ma=ma, xrange=xr),
                        use_container_width=True, key="chart_009")
    with c2:
        st.plotly_chart(line_fig(ops, "date", "total_feed_m3",
                                  "Total Feed to Reactor (m³/day)", "m³", ma=ma, xrange=xr),
                        use_container_width=True, key="chart_010")

    c3, c4 = st.columns(2)
    with c3:
        st.plotly_chart(line_fig(ops, "date", "total_filter_water",
                                  "Filter Water Consumed (m³/day)", "m³", ma=ma, xrange=xr),
                        use_container_width=True, key="chart_011")
    with c4:
        has_potato = ("waste_potato_tons" in ops.columns and
                      ops["waste_potato_tons"].notna().any())
        if has_potato:
            st.plotly_chart(line_fig(ops, "date", "waste_potato_tons",
                                      "Waste Potato Added (tons/day)", "tons",
                                      ma=ma, xrange=xr),
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
                              "m³/ton", ma=ma, height=400, xrange=xr),
                    use_container_width=True, key="chart_013")


def tab_purif(ops, ma, xr):
    sec("⚗️ PURIFICATION & CBG SALES")
    c1, c2 = st.columns(2)
    with c1:
        fig = line_fig(ops, "date", "purif_efficiency",
                       "Purification Efficiency (%)", "%", ma=ma, xrange=xr)
        fig.add_hline(y=95, line_dash="dot", line_color="#2e7d32",
                       annotation_text="Target 95%", annotation_font_color="#2e7d32")
        st.plotly_chart(fig, use_container_width=True, key="chart_014")
    with c2:
        st.plotly_chart(line_fig(ops, "date", "bg_recovery",
                                  "Biogas Recovery (%)", "%", ma=ma, xrange=xr),
                        use_container_width=True, key="chart_015")

    c3, c4 = st.columns(2)
    with c3:
        st.plotly_chart(line_fig(ops, "date", "cbg_sales_kg",
                                  "CBG Sales – Dispenser (kg/day)", "kg", ma=ma, xrange=xr),
                        use_container_width=True, key="chart_016")
    with c4:
        st.plotly_chart(line_fig(ops, "date", "total_sales_kg",
                                  "Total CBG Sales incl. Cascade (kg/day)", "kg",
                                  ma=ma, xrange=xr),
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
                                  "Vehicles Served / Day", "count", ma=1, xrange=xr),
                        use_container_width=True, key="chart_019")
    with c6:
        st.plotly_chart(line_fig(ops, "date", "purif_running_hrs",
                                  "Purification Running Hrs / Day", "hrs", ma=1, xrange=xr),
                        use_container_width=True, key="chart_020")


def tab_power(ops, ma, xr):
    sec("⚡ POWER & UTILITY CONSUMPTION")
    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(line_fig(ops, "date", "vpsa_kwh_total",
                                  "VPSA Power Consumed (KWH/day)", "KWH", ma=ma, xrange=xr),
                        use_container_width=True, key="chart_021")
    with c2:
        st.plotly_chart(line_fig(ops, "date", "bg_mfm_kwh_total",
                                  "Biogas MFM Power (KWH/day)", "KWH", ma=ma, xrange=xr),
                        use_container_width=True, key="chart_022")

    c3, c4 = st.columns(2)
    with c3:
        st.plotly_chart(line_fig(ops, "date", "raw_water_m3",
                                  "Raw Water Consumed (m³/day)", "m³", ma=ma, xrange=xr),
                        use_container_width=True, key="chart_023")
    with c4:
        st.plotly_chart(line_fig(ops, "date", "poly_kg",
                                  "Poly Consumption (kg/day)", "kg", ma=ma, xrange=xr),
                        use_container_width=True, key="chart_024")

    c5, c6 = st.columns(2)
    with c5:
        st.plotly_chart(line_fig(ops, "date", "dg_hrs",
                                  "DG Running Hours / Day", "hrs", ma=1, xrange=xr),
                        use_container_width=True, key="chart_025")
    with c6:
        st.plotly_chart(line_fig(ops, "date", "dg_diesel_l",
                                  "DG Diesel Consumed (L/day)", "L", ma=ma, xrange=xr),
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
                              "KWH/m³", ma=ma, height=400, xrange=xr),
                    use_container_width=True, key="chart_027")


def tab_digester(ops, ma, xr):
    sec("🌡️ DIGESTER CONDITIONS")
    c1, c2 = st.columns(2)
    with c1:
        fig = line_fig(ops, "date", "digester_temp",
                       "Digester Temperature (°C)", "°C", ma=ma, xrange=xr)
        fig.add_hline(y=37, line_dash="dash", line_color="#e65100",
                       annotation_text="Mesophilic 37°C",
                       annotation_font_color="#e65100")
        fig.add_hrect(y0=35, y1=40, fillcolor="#e65100", opacity=0.05)
        st.plotly_chart(fig, use_container_width=True, key="chart_028")
    with c2:
        fig = line_fig(ops, "date", "digester_ph",
                       "Digester pH (Mid)", "pH", ma=ma, xrange=xr)
        fig.add_hrect(y0=6.8, y1=7.5, fillcolor="#2e7d32", opacity=0.08,
                       annotation_text="Optimal 6.8–7.5",
                       annotation_font_color="#2e7d32")
        st.plotly_chart(fig, use_container_width=True, key="chart_029")

    sec("💧 DEWATERING & SCREW PRESS")
    c3, c4 = st.columns(2)
    with c3:
        st.plotly_chart(dual_line_fig(ops, "date",
                                       "screw_moisture", "Screw Press",
                                       "volute_moisture", "Volute Press",
                                       "Dewatering Moisture (%)", xrange=xr),
                        use_container_width=True, key="chart_030")
    with c4:
        st.plotly_chart(line_fig(ops, "date", "flare_m3",
                                  "Flare Gas (m³/day)", "m³", ma=ma, xrange=xr),
                        use_container_width=True, key="chart_031")

    c5, c6, c7 = st.columns(3)
    for col_w, col, title in zip(
        [c5, c6, c7],
        ["screw_press_hrs", "vibro_screen_hrs", "volute_press_hrs"],
        ["Screw Press Hrs/Day", "Vibro Screen Hrs/Day", "Volute Press Hrs/Day"],
    ):
        with col_w:
            st.plotly_chart(line_fig(ops, "date", col, title, "hrs",
                                      ma=1, height=380, xrange=xr),
                            use_container_width=True, key=f"chart_digester_{col}")


def tab_lab(all_data, selected, date_filter):
    sec("🔬 LAB & SLURRY ANALYSIS")
    lab = get_lab(all_data, selected, date_filter)
    if lab.empty:
        st.info("No lab data for the selected range.")
        return

    xr = _xrange_from_filter(date_filter)

    pts = sorted(lab["sample_point"].dropna().unique())
    defaults = ([s for s in ["RCD (Raw Cattle Dung)",
                              "Digester Mid Sampling Point",
                              "Mixing Tank", "Slurry Tank"]
                 if s in pts] or pts[:3])
    chosen = st.multiselect("Sample Points", pts, default=defaults, key="lab_pts")
    if not chosen:
        st.info("Select at least one sample point.")
        return

    lab_f = lab[lab["sample_point"].isin(chosen)]
    params = [
        ("pH",         "pH"),
        ("TS_pct",     "TS (%)"),
        ("VS_pct",     "VS (%)"),
        ("EC_mScm",    "EC (mS/cm)"),
        ("Temp_C",     "Temperature (°C)"),
        ("Carbon_pct", "Carbon (%)"),
    ]
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
            )
            fig.update_layout(
                paper_bgcolor=CHART_BG, plot_bgcolor=CHART_BG,
                font=dict(color=FONT_COLOR, family="Inter, sans-serif"),
                title_font=dict(size=14, color="#1a2d4a",
                                family="Space Mono, monospace"),
                legend=dict(bgcolor="rgba(255,255,255,0.9)", bordercolor="#d1dce8",
                            borderwidth=1, font=dict(color=FONT_COLOR)),
                height=420, margin=dict(l=12, r=12, t=48, b=12),
            )
            xax_kw = dict(
                showgrid=True, gridcolor=CHART_GRID,
                tickfont=dict(color=FONT_COLOR),
                type="date",
                rangemode="normal",
                autorange=False if xr else True,
            )
            if xr:
                xax_kw["range"] = xr
            fig.update_xaxes(**xax_kw)
            fig.update_yaxes(showgrid=True, gridcolor=CHART_GRID,
                             tickfont=dict(color=FONT_COLOR))
            with col_w:
                st.plotly_chart(fig, use_container_width=True,
                                key=f"chart_lab_{param}")

    sec("📊 TS vs VS CORRELATION")
    valid = lab_f.dropna(subset=["TS_pct", "VS_pct"])
    if not valid.empty:
        st.plotly_chart(scatter_fig(valid, "TS_pct", "VS_pct",
                                     "TS (%) vs VS (%) — by Sample Point",
                                     height=460),
                        use_container_width=True, key="chart_034")


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
        st.info("Select **Compare** mode and choose at least 2 plants from the sidebar.")
        return

    ops = get_ops(all_data, selected, date_filter)

    # Show per-plant data availability so user can diagnose missing data
    st.markdown("**Data availability per plant:**")
    diag_cols = st.columns(len(selected))
    plants_with_data = []
    for i, p in enumerate(selected):
        pdata = all_data.get(p, {}).get("ops", pd.DataFrame())
        filtered = _apply_date_filter(pdata, date_filter) if not pdata.empty else pdata
        row_count = len(filtered)
        if row_count > 0:
            plants_with_data.append(p)
            date_min = filtered["date"].min().strftime("%d %b %Y")
            date_max = filtered["date"].max().strftime("%d %b %Y")
            diag_cols[i].success(f"**{p}**  \n{row_count} rows  \n{date_min} → {date_max}")
        else:
            diag_cols[i].warning(f"**{p}**  \nNo data in selected range")

    if len(plants_with_data) < 2:
        st.warning(
            f"Only **{len(plants_with_data)}** plant(s) have data in the selected range. "
            "Adjust the date filter to include dates present in both plants."
        )
        if len(plants_with_data) == 0:
            return
        ops = get_ops(all_data, plants_with_data, date_filter)

    if ops.empty:
        st.warning("No operational data for the selected plants and date range.")
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

    if monthly.empty:
        st.warning("No monthly data to compare.")
        return

    metrics = [
        ("total_generated_gas", "Monthly Raw Biogas (m³)"),
        ("total_purified_gas",  "Monthly Purified Gas (m³)"),
        ("cbg_sales_kg",        "Monthly CBG Sales (kg)"),
        ("avg_purif_eff",       "Avg Purification Efficiency (%)"),
        ("avg_ch4_raw",         "Avg Raw CH₄ (%)"),
        ("avg_digester_temp",   "Avg Digester Temp (°C)"),
        ("dung_tons",           "Total Dung Collected (tons)"),
    ]

    rendered = 0
    for col, title in metrics:
        if col not in monthly.columns:
            continue
        subset = monthly[["month", "plant", col]].dropna(subset=[col])
        if subset.empty:
            continue
        st.plotly_chart(
            bar_fig(subset, "month", col, title, color="plant", height=380),
            use_container_width=True,
            key=f"chart_compare_{col}",
        )
        rendered += 1

    if rendered == 0:
        st.info("No comparable metrics found for the selected range.")
        return

    sec("📈 DAILY OVERLAY COMPARISON")
    xr = _xrange_from_filter(date_filter)
    overlay_metrics = [
        ("total_generated_gas", "Raw Biogas Generated (m³/day)", "m³/day"),
        ("total_purified_gas",  "Purified Gas (m³/day)", "m³/day"),
        ("purif_efficiency",    "Purification Efficiency (%)", "%"),
        ("cbg_sales_kg",        "CBG Sales (kg/day)", "kg"),
    ]
    ma = st.session_state.get("ma_window", 7)
    for col, title, ylab in overlay_metrics:
        if col in ops.columns and ops[col].notna().any():
            st.plotly_chart(
                line_fig(ops, "date", col, title, ylab, ma=ma, height=380, xrange=xr),
                use_container_width=True,
                key=f"chart_overlay_{col}",
            )

    sec("🕸️ PLANT PROFILE RADAR (PERIOD AVERAGES)")
    radar_m = ["avg_purif_eff", "avg_ch4_raw", "avg_ch4_pure"]
    latest  = monthly.groupby("plant")[
        [c for c in radar_m if c in monthly.columns]
    ].mean().reset_index()
    available_radar = [c for c in radar_m if c in latest.columns]

    if not latest.empty and len(available_radar) >= 2:
        fig = go.Figure()
        cmap = _pmap(latest["plant"].tolist())
        labels_map = {
            "avg_purif_eff": "Purif Eff %",
            "avg_ch4_raw":   "CH₄ Raw %",
            "avg_ch4_pure":  "CH₄ Pure %",
        }
        theta = [labels_map.get(m, m) for m in available_radar] + \
                [labels_map.get(available_radar[0], available_radar[0])]
        for _, row in latest.iterrows():
            pname = row["plant"]
            vals  = [row.get(m, 0) for m in available_radar] + \
                    [row.get(available_radar[0], 0)]
            c = cmap.get(pname, PALETTE[0])
            fig.add_trace(go.Scatterpolar(
                r=vals, theta=theta, fill="toself", name=pname,
                line=dict(color=c, width=2),
                fillcolor=_hex_to_rgba(c, alpha=0.15),
            ))
        fig.update_layout(
            polar=dict(
                radialaxis=dict(visible=True, range=[0, 100],
                                tickfont=dict(size=10, color="#5a7a9a"),
                                gridcolor="#d1dce8"),
                angularaxis=dict(tickfont=dict(size=12, color="#1a2d4a"),
                                 gridcolor="#d1dce8"),
                bgcolor="#f5f7fa",
            ),
            paper_bgcolor=CHART_BG,
            font=dict(color=FONT_COLOR, family="Inter, sans-serif"),
            height=500,
            legend=dict(bgcolor="rgba(255,255,255,0.9)", bordercolor="#d1dce8",
                        borderwidth=1, font=dict(color=FONT_COLOR)),
        )
        st.plotly_chart(fig, use_container_width=True, key="chart_035")


def tab_dung_routes(all_data, selected, date_filter):
    sec("🚛 DUNG ROUTE QUALITY")
    frames = []
    for p in selected:
        if p not in all_data:
            continue
        df = all_data[p]["dung"]
        if df.empty:
            continue
        frames.append(_apply_date_filter(df, date_filter))

    if not frames:
        st.info("No dung route quality data for this selection.")
        return

    dung = pd.concat(frames, ignore_index=True)
    routes = sorted(dung["route"].dropna().unique())
    if not routes:
        st.info("No routes found.")
        return

    chosen = st.multiselect("Routes", routes,
                             default=routes[:6] if len(routes) > 6 else routes,
                             key="dung_routes")
    if not chosen:
        return
    dung_f = dung[dung["route"].isin(chosen)]

    metrics = ["Sand (%)", "pH", "EC", "TS (%)"]
    pairs = [(metrics[i], metrics[i+1] if i+1 < len(metrics) else None)
             for i in range(0, len(metrics), 2)]
    rendered = 0
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
                         color="plant", title=f"Dung Route – {needle}")
            fig.update_layout(
                paper_bgcolor=CHART_BG, plot_bgcolor=CHART_BG,
                font=dict(color=FONT_COLOR, family="Inter, sans-serif"),
                title_font=dict(size=14, color="#1a2d4a",
                                family="Space Mono, monospace"),
                legend=dict(bgcolor="rgba(255,255,255,0.9)", bordercolor="#d1dce8",
                            borderwidth=1, font=dict(color=FONT_COLOR)),
                height=440, margin=dict(l=12, r=12, t=48, b=12),
            )
            fig.update_xaxes(showgrid=False, tickfont=dict(color=FONT_COLOR))
            fig.update_yaxes(showgrid=True, gridcolor=CHART_GRID,
                             tickfont=dict(color=FONT_COLOR))
            with col_w:
                st.plotly_chart(fig, use_container_width=True,
                                key=f"chart_dung_{rc}")
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

    c1, c2 = st.columns([1, 3])
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
        title_font=dict(size=14, color="#1a2d4a", family="Space Mono, monospace"),
        legend=dict(bgcolor="rgba(255,255,255,0.9)", bordercolor="#d1dce8",
                    borderwidth=1, font=dict(color=FONT_COLOR)),
        height=500, margin=dict(l=12, r=12, t=48, b=12),
    )
    fig.update_xaxes(showgrid=False, tickfont=dict(color=FONT_COLOR))
    fig.update_yaxes(showgrid=True, gridcolor=CHART_GRID,
                     tickfont=dict(color=FONT_COLOR))
    st.plotly_chart(fig, use_container_width=True, key="chart_037")

    with st.expander("📋 Raw fertilizer data"):
        st.dataframe(fert, use_container_width=True)


def tab_raw(ops, all_data, selected, date_filter):
    sec("🗄️ RAW DATA EXPLORER")
    if ops.empty:
        st.info("No data loaded.")
        return

    # Plant selector within raw tab
    plants_available = [p for p in selected if p in all_data
                        and not all_data[p]["ops"].empty]
    if not plants_available:
        st.info("No plant data available.")
        return

    if len(plants_available) > 1:
        raw_plant_sel = st.multiselect(
            "Plants to include in raw view",
            plants_available,
            default=plants_available,
            key="raw_plant_sel",
        )
    else:
        raw_plant_sel = plants_available

    if not raw_plant_sel:
        st.info("Select at least one plant.")
        return

    # Re-filter for selected plants + date range
    raw_frames = []
    for p in raw_plant_sel:
        df = all_data[p]["ops"]
        if not df.empty:
            raw_frames.append(_apply_date_filter(df, date_filter))
    if not raw_frames:
        st.info("No data for selected plants in this date range.")
        return

    ops_raw = pd.concat(raw_frames, ignore_index=True).sort_values("date", ascending=False)

    # Column selector — plant always shown, date always first
    meta_cols  = ["date", "plant"]
    data_cols  = [c for c in ops_raw.columns if c not in meta_cols]
    preferred  = ["dung_tons", "total_generated_gas", "total_purified_gas",
                  "cbg_sales_kg", "purif_efficiency", "raw_ch4", "pure_ch4",
                  "digester_temp"]
    default_show = [c for c in preferred if c in data_cols]

    sel_cols = st.multiselect("Columns to display", data_cols,
                               default=default_show, key="raw_col_sel")
    show_cols = meta_cols + [c for c in sel_cols if c in ops_raw.columns]

    st.dataframe(
        ops_raw[show_cols],
        use_container_width=True,
        height=520,
    )

    col_dl1, col_dl2 = st.columns(2)
    with col_dl1:
        st.download_button(
            "⬇️ Download as CSV",
            ops_raw.to_csv(index=False).encode("utf-8"),
            "biogas_filtered_data.csv",
            "text/csv",
            key="dl_csv",
        )
    with col_dl2:
        buf = io.BytesIO()
        ops_raw.to_excel(buf, index=False, engine="openpyxl")
        st.download_button(
            "⬇️ Download as Excel",
            buf.getvalue(),
            "biogas_filtered_data.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="dl_xlsx",
        )

    with st.expander("📊 Summary Statistics"):
        num_c = ops_raw.select_dtypes(include=[np.number]).columns
        st.dataframe(ops_raw[num_c].describe().T.round(2), use_container_width=True)


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    all_data, selected, date_filter, view_mode, compare_plants = sidebar()

    if not all_data or not selected:
        st.markdown("## ⚡ Biogas Plant Analytics Dashboard")
        st.markdown("""
**Getting started:**
1. Upload one `.xlsx` file per plant using the sidebar (Unified Daily Report format).
2. Rename each plant if needed.
3. Choose **Individual** to view one plant, or **Compare** to overlay multiple.
4. Set the date filter — pick specific months or a custom range.
5. Explore all tabs below.
        """)
        return

    # ── Header ──
    if view_mode == "compare" and len(selected) >= 2:
        badges = " ".join(
            f'<span class="compare-badge">⚖️ {p}</span>' for p in selected
        )
        mode_label = "COMPARE MODE"
        mode_color = "#e65100"
    else:
        badges = " ".join(
            f'<span class="plant-badge">🏭 {p}</span>' for p in selected
        )
        mode_label = "INDIVIDUAL VIEW"
        mode_color = "#1565c0"

    st.markdown(
        f"<h2 style='font-family:Space Mono,monospace;color:#1a2d4a;"
        f"font-size:1.3rem;letter-spacing:0.04em;margin-bottom:4px'>"
        f"⚡ BIOGAS ANALYTICS &nbsp;"
        f"<span style='font-size:0.7rem;color:{mode_color};'>[{mode_label}]</span>"
        f"&nbsp; {badges}</h2>",
        unsafe_allow_html=True,
    )

    # Date range display
    if date_filter:
        if "months" in date_filter:
            months_str = ", ".join(date_filter["months"])
            st.markdown(
                f'<div class="mode-banner">📅 Showing: <strong>{months_str}</strong></div>',
                unsafe_allow_html=True,
            )
        else:
            s = date_filter["start"].strftime("%d %b %Y")
            e = date_filter["end"].strftime("%d %b %Y")
            st.markdown(
                f'<div class="mode-banner">📅 Range: <strong>{s}</strong> → <strong>{e}</strong></div>',
                unsafe_allow_html=True,
            )

    ma = st.session_state.get("ma_window", 7)
    ops = get_ops(all_data, selected, date_filter)
    xr  = _xrange_from_filter(date_filter)

    render_kpis(ops)
    st.markdown("---")

    # ── Tab layout ──
    if view_mode == "compare" and len(selected) >= 2:
        # Compare mode: show compare tab first, then optionally individual tabs
        tabs = st.tabs([
            "📊 Compare", "📊 Gas Production", "🐄 Feedstock",
            "⚗️ Purification & Sales", "⚡ Power & Utilities",
            "🌡️ Digester & Dewatering", "🔬 Lab Analysis",
            "🚛 Dung Routes", "🌱 Fertilizer", "🗄️ Raw Data",
        ])
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
        # Individual mode
        tabs = st.tabs([
            "📊 Gas Production", "🐄 Feedstock", "⚗️ Purification & Sales",
            "⚡ Power & Utilities", "🌡️ Digester & Dewatering", "🔬 Lab Analysis",
            "🚛 Dung Routes", "🌱 Fertilizer", "🗄️ Raw Data",
        ])
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
