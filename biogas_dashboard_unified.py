"""
Biogas Plant Analytics Dashboard  ·  Universal Format  ·  Streamlit
=====================================================================
Reads any number of plants from the Unified Daily Report Excel format.
Columns are located by NAME (dynamic scan), so extra or reordered
columns in any plant file are handled automatically.

Sheets expected
  • Daily Operations
  • Lab & Slurry Analysis
  • Dung Route Quality
  • Fertilizer Quality

Usage
  streamlit run biogas_dashboard.py
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

st.markdown("""
<style>
.metric-card{background:linear-gradient(135deg,#1e3a5f,#0d2137);border:1px solid #2d5a8e;
 border-radius:12px;padding:16px 20px;text-align:center;margin:4px}
.metric-value{font-size:2rem;font-weight:700;color:#4fc3f7}
.metric-label{font-size:.78rem;color:#90caf9;margin-top:4px}
.sec-hdr{background:linear-gradient(90deg,#1565c0,#0d47a1);color:white;padding:8px 16px;
 border-radius:8px;font-size:1.1rem;font-weight:600;margin:16px 0 8px}
.plant-badge{display:inline-block;background:#1e3a5f;border:1px solid #4fc3f7;
 border-radius:20px;padding:4px 14px;font-size:.85rem;color:#4fc3f7;margin:2px}
</style>
""", unsafe_allow_html=True)

PALETTE = px.colors.qualitative.Bold

# ─────────────────────────────────────────────────────────────────────────────
# SEMANTIC COLUMN DEFINITIONS
# Maps internal key → substrings to search in header row (first match wins).
# Special keys starting with __ are handled by dedicated multi-occurrence logic.
# ─────────────────────────────────────────────────────────────────────────────
SEEK = {
    "date":                ["date"],
    "dung_tons":           ["dung (tons)", "dung\n(tons)", "dung"],
    "waste_potato_tons":   ["waste potato"],
    "total_feed_m3":       ["total feed to reactor"],
    "total_filter_water":  ["total filter water consumed"],
    # raw analyser = first occurrence of these
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
    # pure analyser = second occurrence — handled in _build_col_index
    "pure_gas_purity_fm":  ["pure gas purity in fm", "pure gas purity"],
    "cbg_sales_kg":        ["total cbg sales dispenser", "total cbg sales"],
    "num_vehicles":        ["no. of vehicles", "no of vehicles"],
    "cascade_sales_kg":    ["cascade vehicle sales"],
    "purif_efficiency":    ["purification efficiency (%)"],
    "purif_running_hrs":   ["purification running hrs"],
    "compressor_hrs":      ["compressor running hrs"],
    # vpsa/bgmfm kwh totals = handled by multi-occurrence logic
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

# Keys that need the SECOND occurrence of a shared substring
_SECOND_OCCURRENCE = {
    "pure_ch4": ["ch₄", "ch4"],
    "pure_co2": ["co₂", "co2"],
    "pure_h2s": ["h₂s", "h2s"],
}


def _build_col_index(raw: pd.DataFrame) -> dict:
    """
    Dynamically scan header row (row 1) of a Daily Operations sheet.
    Returns {semantic_key: column_index}.
    Handles repeated column names (ch4/co2/h2s appear twice: raw then pure).
    """
    # Normalise header row
    header = [
        str(v).replace("\n", " ").strip().lower() if pd.notna(v) else ""
        for v in raw.iloc[1]
    ]
    section = [
        str(v).replace("\n", " ").strip().lower() if pd.notna(v) else ""
        for v in raw.iloc[0]
    ]

    idx: dict = {}

    # ── Simple single-occurrence columns ────────────────────────────────────
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

    # ── Second-occurrence columns (raw → pure) ───────────────────────────────
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

    # ── "Total KWH Consumed" appears multiple times ──────────────────────────
    kwh_cols = [c for c, h in enumerate(header) if "total kwh consumed" in h]
    if len(kwh_cols) >= 1:
        idx["vpsa_kwh_total"] = kwh_cols[0]
    if len(kwh_cols) >= 2:
        idx["bg_mfm_kwh_total"] = kwh_cols[1]

    # ── HP Compressor KWH ────────────────────────────────────────────────────
    hp_cols = [c for c, s in enumerate(section) if "hp compressor" in s]
    for c in hp_cols:
        h = header[c]
        if "initial" in h:
            idx["hp_comp_kwh_init"] = c
        elif "final" in h:
            idx["hp_comp_kwh_final"] = c

    return idx


# ─────────────────────────────────────────────────────────────────────────────
# LOADERS
# ─────────────────────────────────────────────────────────────────────────────

def _to_num(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s, errors="coerce")


def load_daily_operations(wb_bytes: bytes, plant_name: str) -> pd.DataFrame:
    raw = pd.read_excel(io.BytesIO(wb_bytes),
                        sheet_name="Daily Operations", header=None)

    # Auto-detect data start row (first row where col-0 parses as a date)
    data_start = 3
    for r in range(2, min(10, len(raw))):
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

    records = {}
    all_keys = list(SEEK.keys()) + list(_SECOND_OCCURRENCE.keys()) + [
        "vpsa_kwh_total", "bg_mfm_kwh_total",
        "hp_comp_kwh_init", "hp_comp_kwh_final",
    ]
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
    # Row 2 is always the column-header row; data starts row 3
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

    # Drop physiologically impossible values
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

    # Dynamically find the header row: first row where col-0 looks like "Sr" / "Sr. No."
    header_row_idx = 2  # default
    for r in range(min(5, len(raw))):
        v = str(raw.iloc[r, 0]).replace("\n", " ").strip().lower()
        if v.startswith("sr"):
            header_row_idx = r
            break

    headers = [str(h).replace("\n", " ").strip()
               for h in raw.iloc[header_row_idx]]
    data = raw.iloc[header_row_idx + 1:].reset_index(drop=True).copy()
    data.columns = headers

    # Drop section-banner rows (where the first column is not numeric)
    sr_col = headers[0]
    data = data[pd.to_numeric(data[sr_col], errors="coerce").notna()].copy()

    # Coerce numeric columns
    non_numeric = {"Sr. No.", "Sr.\nNo.", sr_col,
                   "Sample Date", "Sample\nDate",
                   "Material Name", "Material\nName",
                   "Batch / Type", "Batch /\nType",
                   "Mfg Date / Month", "Mfg Date\n/ Month",
                   "Remarks / Sampler", "Remarks /\nSampler"}
    for col in data.columns:
        if col not in non_numeric and data[col].dtype == object:
            data[col] = _to_num(data[col])

    data["plant"] = plant_name
    return data.reset_index(drop=True)


@st.cache_data(show_spinner=False)
def load_plant(file_bytes: bytes, plant_name: str) -> dict:
    """Load all sheets for one plant file. Cached by file content hash."""
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

def _pmap(plants) -> dict:
    return {p: PALETTE[i % len(PALETTE)] for i, p in enumerate(sorted(plants))}


def _ma(s: pd.Series, w: int) -> pd.Series:
    return s.rolling(w, min_periods=1).mean()


def _base(fig, height=380):
    fig.update_layout(
        paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
        font=dict(color="#e0e0e0"),
        legend=dict(bgcolor="rgba(0,0,0,0.5)", bordercolor="#444"),
        hovermode="x unified", height=height, title_x=0,
    )
    fig.update_xaxes(showgrid=True, gridcolor="#1e3a5f")
    fig.update_yaxes(showgrid=True, gridcolor="#1e3a5f")
    return fig


def line_fig(df: pd.DataFrame, x: str, ycol: str,
             title: str, ylab: str = "", ma: int = 7) -> go.Figure:
    """Single-metric multi-plant line chart."""
    fig = go.Figure()
    if df.empty or ycol not in df.columns:
        return _base(fig)
    cmap = _pmap(df["plant"].unique())
    for p, gdf in df.groupby("plant"):
        c = cmap[p]
        s = gdf[ycol]
        fig.add_trace(go.Scatter(x=gdf[x], y=s, mode="lines", name=p,
                                  line=dict(color=c, width=1.6), opacity=0.85))
        if ma > 1 and s.notna().sum() >= ma:
            fig.add_trace(go.Scatter(
                x=gdf[x], y=_ma(s, ma), mode="lines",
                name=f"{p} {ma}d MA",
                line=dict(color=c, width=2.5, dash="dash"), showlegend=False))
    fig.update_layout(title=title, yaxis_title=ylab)
    return _base(fig)


def dual_line_fig(df: pd.DataFrame, x: str,
                  col_a: str, label_a: str,
                  col_b: str, label_b: str,
                  title: str) -> go.Figure:
    """Two metrics per plant (solid / dotted)."""
    fig = go.Figure()
    if df.empty:
        return _base(fig)
    cmap = _pmap(df["plant"].unique())
    for p, gdf in df.groupby("plant"):
        c = cmap[p]
        if col_a in gdf.columns:
            fig.add_trace(go.Scatter(x=gdf[x], y=gdf[col_a],
                                      name=f"{p} – {label_a}",
                                      line=dict(color=c, width=1.6)))
        if col_b in gdf.columns:
            fig.add_trace(go.Scatter(x=gdf[x], y=gdf[col_b],
                                      name=f"{p} – {label_b}",
                                      line=dict(color=c, width=1.6, dash="dot")))
    fig.update_layout(title=title)
    return _base(fig)


def bar_fig(df: pd.DataFrame, x: str, y: str, title: str,
            color: str = "plant", barmode: str = "group") -> go.Figure:
    cmap = _pmap(df["plant"].unique()) if "plant" in df.columns else {}
    fig = px.bar(df, x=x, y=y, color=color, barmode=barmode,
                 title=title, color_discrete_map=cmap, template="plotly_dark")
    fig.update_layout(paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
                      font=dict(color="#e0e0e0"), height=380, title_x=0)
    return fig


def scatter_fig(df: pd.DataFrame, x: str, y: str, title: str,
                color: str = "sample_point") -> go.Figure:
    cmap = _pmap(df[color].unique()) if color in df.columns else {}
    fig = px.scatter(df, x=x, y=y, color=color, trendline="ols",
                     title=title, color_discrete_map=cmap, template="plotly_dark")
    fig.update_layout(paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
                      font=dict(color="#e0e0e0"), height=400, title_x=0)
    return fig


def sec(text: str):
    st.markdown(f'<div class="sec-hdr">{text}</div>', unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR
# FIX: st.slider uses key="ma_window" — NEVER manually assign session_state
#      for a widget-managed key. Just read it with .get() after the slider.
# ─────────────────────────────────────────────────────────────────────────────

def sidebar() -> tuple:
    """Returns (all_data, selected_plants, date_filter)."""
    with st.sidebar:
        st.markdown("## ⚡ Biogas Dashboard")
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
        st.markdown("### ⚙️ Options")
        # ✅ CORRECT: declare the slider with key — do NOT write to session_state manually
        st.slider("Moving average (days)", 1, 30, 7, key="ma_window")

        return all_data, selected, date_filter


# ─────────────────────────────────────────────────────────────────────────────
# DATA FILTERS
# ─────────────────────────────────────────────────────────────────────────────

def get_ops(all_data: dict, selected: list, date_filter: dict) -> pd.DataFrame:
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


def get_lab(all_data: dict, selected: list, date_filter: dict) -> pd.DataFrame:
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

    def sm(col): return ops[col].dropna().mean() if col in ops.columns else np.nan
    def ss(col): return ops[col].dropna().sum()  if col in ops.columns else np.nan

    kpis = {
        "🌿 Avg Biogas Gen (m³/d)": f"{sm('total_generated_gas'):.1f}",
        "🏭 Total CBG Sales (kg)":   f"{ss('cbg_sales_kg'):,.0f}",
        "⚗️ Avg Purif. Eff. (%)":   f"{sm('purif_efficiency'):.1f}",
        "🔬 Avg CH₄ Raw (%)":        f"{sm('raw_ch4'):.1f}",
        "🔬 Avg CH₄ Pure (%)":       f"{sm('pure_ch4'):.1f}",
        "🌡️ Avg Digester Temp (°C)": f"{sm('digester_temp'):.1f}",
        "⚡ Avg VPSA KWH/d":         f"{sm('vpsa_kwh_total'):.1f}",
        "🐄 Avg Dung (tons/d)":      f"{sm('dung_tons'):.1f}",
    }
    cols = st.columns(len(kpis))
    for col_w, (label, val) in zip(cols, kpis.items()):
        with col_w:
            st.markdown(f"""<div class="metric-card">
                <div class="metric-value">{val}</div>
                <div class="metric-label">{label}</div>
            </div>""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# TABS
# ─────────────────────────────────────────────────────────────────────────────

def tab_gas(ops: pd.DataFrame, ma: int):
    sec("📊 Gas Production & Quality")
    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(line_fig(ops, "date", "total_generated_gas",
                                  "Raw Biogas Generated (m³/day)", "m³/day", ma=ma),
                        use_container_width=True)
    with c2:
        st.plotly_chart(line_fig(ops, "date", "total_purified_gas",
                                  "Purified Gas (m³/day)", "m³/day", ma=ma),
                        use_container_width=True)

    c3, c4 = st.columns(2)
    with c3:
        st.plotly_chart(dual_line_fig(ops, "date",
                                       "raw_ch4", "CH₄", "raw_co2", "CO₂",
                                       "Raw Biogas Composition (%)"),
                        use_container_width=True)
    with c4:
        st.plotly_chart(dual_line_fig(ops, "date",
                                       "pure_ch4", "CH₄", "pure_co2", "CO₂",
                                       "Purified Gas Composition (%)"),
                        use_container_width=True)

    sec("⚠️ H₂S Levels (PPM)")
    c5, c6 = st.columns(2)
    with c5:
        st.plotly_chart(line_fig(ops, "date", "raw_h2s",
                                  "Raw Gas H₂S (PPM)", "PPM", ma=ma),
                        use_container_width=True)
    with c6:
        st.plotly_chart(line_fig(ops, "date", "pure_h2s",
                                  "Purified Gas H₂S (PPM)", "PPM", ma=ma),
                        use_container_width=True)


def tab_feed(ops: pd.DataFrame, ma: int):
    sec("🐄 Feedstock & Feeding")
    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(line_fig(ops, "date", "dung_tons",
                                  "Dung Collected (tons/day)", "tons", ma=ma),
                        use_container_width=True)
    with c2:
        st.plotly_chart(line_fig(ops, "date", "total_feed_m3",
                                  "Total Feed to Reactor (m³/day)", "m³", ma=ma),
                        use_container_width=True)

    c3, c4 = st.columns(2)
    with c3:
        st.plotly_chart(line_fig(ops, "date", "total_filter_water",
                                  "Filter Water Consumed (m³/day)", "m³", ma=ma),
                        use_container_width=True)
    with c4:
        has_potato = ("waste_potato_tons" in ops.columns and
                      ops["waste_potato_tons"].notna().any())
        if has_potato:
            st.plotly_chart(line_fig(ops, "date", "waste_potato_tons",
                                      "Waste Potato Added (tons/day)", "tons", ma=ma),
                            use_container_width=True)
        else:
            st.info("No waste-potato data for selected plants.")

    sec("📈 Specific Biogas Yield")
    ops2 = ops.copy()
    ops2["yield_m3_per_ton"] = np.where(ops2["dung_tons"] > 0,
                                         ops2["total_generated_gas"] / ops2["dung_tons"],
                                         np.nan)
    st.plotly_chart(line_fig(ops2, "date", "yield_m3_per_ton",
                              "Biogas Yield (m³ per ton of dung)", "m³/ton", ma=ma),
                    use_container_width=True)


def tab_purif(ops: pd.DataFrame, ma: int):
    sec("⚗️ Purification & CBG Sales")
    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(line_fig(ops, "date", "purif_efficiency",
                                  "Purification Efficiency (%)", "%", ma=ma),
                        use_container_width=True)
    with c2:
        st.plotly_chart(line_fig(ops, "date", "bg_recovery",
                                  "Biogas Recovery (%)", "%", ma=ma),
                        use_container_width=True)

    c3, c4 = st.columns(2)
    with c3:
        st.plotly_chart(line_fig(ops, "date", "cbg_sales_kg",
                                  "CBG Sales – Dispenser (kg/day)", "kg", ma=ma),
                        use_container_width=True)
    with c4:
        st.plotly_chart(line_fig(ops, "date", "total_sales_kg",
                                  "Total CBG Sales (kg/day)", "kg", ma=ma),
                        use_container_width=True)

    sec("📅 Monthly CBG Sales")
    monthly = (ops.assign(month=ops["date"].dt.to_period("M").astype(str))
                  .groupby(["month", "plant"], as_index=False)["cbg_sales_kg"].sum())
    if not monthly.empty:
        st.plotly_chart(bar_fig(monthly, "month", "cbg_sales_kg",
                                 "Monthly CBG Sales (kg)", color="plant"),
                        use_container_width=True)

    c5, c6 = st.columns(2)
    with c5:
        st.plotly_chart(line_fig(ops, "date", "num_vehicles",
                                  "Vehicles Served / Day", "count", ma=1),
                        use_container_width=True)
    with c6:
        st.plotly_chart(line_fig(ops, "date", "purif_running_hrs",
                                  "Purification Running Hrs / Day", "hrs", ma=1),
                        use_container_width=True)


def tab_power(ops: pd.DataFrame, ma: int):
    sec("⚡ Power & Utility Consumption")
    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(line_fig(ops, "date", "vpsa_kwh_total",
                                  "VPSA Power Consumed (KWH/day)", "KWH", ma=ma),
                        use_container_width=True)
    with c2:
        st.plotly_chart(line_fig(ops, "date", "bg_mfm_kwh_total",
                                  "Biogas MFM Power (KWH/day)", "KWH", ma=ma),
                        use_container_width=True)

    c3, c4 = st.columns(2)
    with c3:
        st.plotly_chart(line_fig(ops, "date", "raw_water_m3",
                                  "Raw Water Consumed (m³/day)", "m³", ma=ma),
                        use_container_width=True)
    with c4:
        st.plotly_chart(line_fig(ops, "date", "poly_kg",
                                  "Poly Consumption (kg/day)", "kg", ma=ma),
                        use_container_width=True)

    c5, c6 = st.columns(2)
    with c5:
        st.plotly_chart(line_fig(ops, "date", "dg_hrs",
                                  "DG Running Hours / Day", "hrs", ma=1),
                        use_container_width=True)
    with c6:
        st.plotly_chart(line_fig(ops, "date", "dg_diesel_l",
                                  "DG Diesel Consumed (L/day)", "L", ma=ma),
                        use_container_width=True)

    sec("💡 Specific Energy")
    ops2 = ops.copy()
    ops2["kwh_per_m3"] = np.where(ops2["total_purified_gas"] > 0,
                                   ops2["vpsa_kwh_total"] / ops2["total_purified_gas"],
                                   np.nan)
    st.plotly_chart(line_fig(ops2, "date", "kwh_per_m3",
                              "VPSA Specific Energy (KWH / m³ purified gas)",
                              "KWH/m³", ma=ma),
                    use_container_width=True)


def tab_digester(ops: pd.DataFrame, ma: int):
    sec("🌡️ Digester Conditions")
    c1, c2 = st.columns(2)
    with c1:
        fig = line_fig(ops, "date", "digester_temp",
                       "Digester Temperature (°C, 9-10 AM)", "°C", ma=ma)
        fig.add_hline(y=37, line_dash="dash", line_color="#ef9a9a",
                       annotation_text="Mesophilic 37°C")
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        fig = line_fig(ops, "date", "digester_ph",
                       "Digester pH (Mid)", "pH", ma=ma)
        fig.add_hrect(y0=6.8, y1=7.5, fillcolor="#1b5e20", opacity=0.12,
                       annotation_text="Optimal 6.8–7.5")
        st.plotly_chart(fig, use_container_width=True)

    sec("💧 Dewatering & Flare")
    c3, c4 = st.columns(2)
    with c3:
        st.plotly_chart(dual_line_fig(ops, "date",
                                       "screw_moisture", "Screw",
                                       "volute_moisture", "Volute",
                                       "Dewatering Moisture (%)"),
                        use_container_width=True)
    with c4:
        st.plotly_chart(line_fig(ops, "date", "flare_m3",
                                  "Flare Gas (m³/day)", "m³", ma=ma),
                        use_container_width=True)

    c5, c6, c7 = st.columns(3)
    for col_w, col, title in zip(
        [c5, c6, c7],
        ["screw_press_hrs", "vibro_screen_hrs", "volute_press_hrs"],
        ["Screw Press Hrs", "Vibro Screen Hrs", "Volute Press Hrs"],
    ):
        with col_w:
            st.plotly_chart(line_fig(ops, "date", col, title, "hrs", ma=1),
                            use_container_width=True)


def tab_lab(all_data: dict, selected: list, date_filter: dict):
    sec("🔬 Lab & Slurry Analysis")
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

    for param, label in [
        ("pH",       "pH"),
        ("TS_pct",   "TS (%)"),
        ("VS_pct",   "VS (%)"),
        ("EC_mScm",  "EC (mS/cm)"),
        ("Temp_C",   "Temperature (°C)"),
        ("Carbon_pct","Carbon (%)"),
    ]:
        if param not in lab_f.columns or lab_f[param].dropna().empty:
            continue
        sub = lab_f.dropna(subset=[param])
        fig = px.line(
            sub, x="date", y=param, color="sample_point",
            facet_col="plant" if len(selected) > 1 else None,
            title=f"{label} by Sample Point",
            template="plotly_dark",
        )
        fig.update_layout(paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
                           font=dict(color="#e0e0e0"), height=360)
        st.plotly_chart(fig, use_container_width=True)

    sec("TS vs VS Correlation")
    valid = lab_f.dropna(subset=["TS_pct", "VS_pct"])
    if not valid.empty:
        st.plotly_chart(scatter_fig(valid, "TS_pct", "VS_pct",
                                     "TS (%) vs VS (%)"),
                        use_container_width=True)


def tab_compare(all_data: dict, selected: list, date_filter: dict):
    sec("📊 Cross-Plant Comparison")
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

    for col, title in [
        ("total_generated_gas", "Monthly Raw Biogas (m³)"),
        ("total_purified_gas",  "Monthly Purified Gas (m³)"),
        ("cbg_sales_kg",        "Monthly CBG Sales (kg)"),
        ("avg_purif_eff",       "Avg Purification Efficiency (%)"),
        ("avg_ch4_raw",         "Avg Raw CH₄ (%)"),
        ("avg_digester_temp",   "Avg Digester Temp (°C)"),
        ("dung_tons",           "Total Dung Collected (tons)"),
    ]:
        if col in monthly.columns and monthly[col].notna().any():
            st.plotly_chart(bar_fig(monthly, "month", col, title, color="plant"),
                            use_container_width=True)

    sec("🕸️ Plant Profile (Period Averages)")
    radar_m = ["avg_purif_eff", "avg_ch4_raw", "avg_ch4_pure"]
    latest  = monthly.groupby("plant")[radar_m].mean().reset_index()
    if not latest.empty:
        fig = go.Figure()
        for _, row in latest.iterrows():
            vals   = [row.get(m, 0) for m in radar_m] + [row.get(radar_m[0], 0)]
            labels = ["Purif Eff %", "CH₄ Raw %", "CH₄ Pure %", "Purif Eff %"]
            fig.add_trace(go.Scatterpolar(r=vals, theta=labels,
                                          fill="toself", name=row["plant"]))
        fig.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
            paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
            font=dict(color="#e0e0e0"), height=420,
        )
        st.plotly_chart(fig, use_container_width=True)


def tab_dung_routes(all_data: dict, selected: list, date_filter: dict):
    sec("🚛 Dung Route Quality")
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
        st.info("No dung route quality data.")
        return

    dung = pd.concat(frames, ignore_index=True)
    routes = sorted(dung["route"].dropna().unique())
    chosen = st.multiselect("Routes", routes,
                             default=routes[:6] if len(routes) > 6 else routes)
    dung_f = dung[dung["route"].isin(chosen)]

    for needle in ["Sand (%)", "pH", "EC", "TS (%)"]:
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
        fig.update_layout(paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
                           font=dict(color="#e0e0e0"), height=360)
        st.plotly_chart(fig, use_container_width=True)


def tab_fertilizer(all_data: dict, selected: list):
    sec("🌱 Organic Fertilizer Quality")
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

    param = st.selectbox("Parameter", num_cols)
    mat_col = next((c for c in fert.columns
                    if "material" in str(c).lower()), None)

    if mat_col:
        fig = px.box(fert.dropna(subset=[param]), x=mat_col, y=param,
                     color="plant", title=f"Fertilizer {param} by Material",
                     template="plotly_dark")
    else:
        fig = px.box(fert.dropna(subset=[param]), y=param,
                     color="plant", title=f"Fertilizer {param}",
                     template="plotly_dark")
    fig.update_layout(paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
                       font=dict(color="#e0e0e0"), height=420)
    st.plotly_chart(fig, use_container_width=True)

    with st.expander("View raw fertilizer data"):
        st.dataframe(fert, use_container_width=True)


def tab_raw(ops: pd.DataFrame):
    sec("🗄️ Raw Data Explorer")
    if ops.empty:
        st.info("No data loaded.")
        return

    all_cols = [c for c in ops.columns if c != "plant"]
    default_show = [c for c in ["date", "plant", "dung_tons",
                                 "total_generated_gas", "total_purified_gas",
                                 "cbg_sales_kg", "purif_efficiency",
                                 "raw_ch4", "pure_ch4", "digester_temp"]
                    if c in ops.columns]
    sel = st.multiselect("Columns", all_cols, default=default_show)
    show = [c for c in sel if c in ops.columns]
    if show:
        st.dataframe(ops[show].sort_values("date", ascending=False),
                     use_container_width=True, height=600)

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
**How to use:**
1. Upload one `.xlsx` file per plant in the sidebar (Unified Daily Report format).
2. Rename each plant if needed.
3. Filter by date range.
4. Navigate the tabs below.

**Scalable:** add any number of plant files — no plant-specific code required.
Extra or reordered columns are handled automatically.
        """)
        return

    # Header badges
    badges = " ".join(
        f'<span class="plant-badge">🏭 {p}</span>' for p in selected
    )
    st.markdown(f"## ⚡ Biogas Analytics &nbsp;&nbsp; {badges}",
                unsafe_allow_html=True)

    # ✅ Read the slider value — do NOT assign to session_state
    ma = st.session_state.get("ma_window", 7)

    # Combined ops for selected plants + date range
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
