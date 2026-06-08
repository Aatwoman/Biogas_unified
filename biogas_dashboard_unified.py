"""
Biogas Plant Analytics Dashboard
==================================
Universal, scalable dashboard that reads any number of plants from the
Unified Daily Report Excel format.  No plant-specific hard-coding.

Sheet layout expected in every uploaded file
----------------------------------------------
• Daily Operations   – rows 0-3 are section / column / unit headers; data from row 4 onward
• Lab & Slurry Analysis – rows 0-2 are title/header; data from row 3 onward (Date ffilled, 7 sample points/day)
• Dung Route Quality – rows 0-2 are headers; data from row 3 onward
• Fertilizer Quality – rows 0-2 are headers; data from row 3 onward

Usage
-----
    streamlit run biogas_dashboard.py
"""

# ──────────────────────────────────────────────
# Imports
# ──────────────────────────────────────────────

!pip install streamlit
import io
import warnings
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

warnings.filterwarnings("ignore")

# ──────────────────────────────────────────────
# Page config
# ──────────────────────────────────────────────
st.set_page_config(
    page_title="Biogas Plant Analytics",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ──────────────────────────────────────────────
# Styling
# ──────────────────────────────────────────────
st.markdown("""
<style>
    .main { background-color: #0e1117; }
    .metric-card {
        background: linear-gradient(135deg, #1e3a5f 0%, #0d2137 100%);
        border: 1px solid #2d5a8e;
        border-radius: 12px;
        padding: 16px 20px;
        text-align: center;
        margin: 4px;
    }
    .metric-value { font-size: 2rem; font-weight: 700; color: #4fc3f7; }
    .metric-label { font-size: 0.78rem; color: #90caf9; margin-top: 4px; }
    .metric-delta { font-size: 0.72rem; color: #a5d6a7; }
    .section-header {
        background: linear-gradient(90deg, #1565c0, #0d47a1);
        color: white; padding: 8px 16px; border-radius: 8px;
        font-size: 1.1rem; font-weight: 600; margin: 16px 0 8px 0;
    }
    .plant-badge {
        display: inline-block;
        background: #1e3a5f; border: 1px solid #4fc3f7;
        border-radius: 20px; padding: 4px 14px;
        font-size: 0.85rem; color: #4fc3f7; margin: 2px;
    }
    .stTabs [data-baseweb="tab"] { font-size: 0.9rem; }
</style>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────
# Constants – column index → semantic name
# (matches the Unified Daily Report format exactly)
# ──────────────────────────────────────────────
COL = {
    # --- Daily Operations sheet (by position index) ---
    "date":               0,
    "dung_tons":          1,
    "waste_potato_tons":  2,
    "feed_init_fm":       3,
    "feed_final_fm":      4,
    "total_feed_m3":      5,
    "filter_water_init":  6,
    "filter_water_final": 7,
    "total_filter_water": 8,
    "raw_ch4":            9,
    "raw_co2":           10,
    "raw_o2":            11,
    "raw_h2s":           12,
    "raw_bal":           13,
    "gen_init_fm":       14,
    "gen_final_fm":      15,
    "total_generated_gas":16,
    "raw_inlet_init":    17,
    "raw_inlet_final":   18,
    "total_raw_gas":     19,
    "gen_inlet_diff":    20,
    "purified_init_fm":  21,
    "purified_final_fm": 22,
    "total_purified_gas":23,
    "expected_gas_kg":   24,
    "cbg_mass_fm_kg":    25,
    "pure_ch4":          26,
    "pure_co2":          27,
    "pure_o2":           28,
    "pure_h2s":          29,
    "pure_bal":          30,
    "pure_gas_purity_fm":31,
    "cbg_sales_kg":      32,
    "num_vehicles":      33,
    "cascade_sales_kg":  34,
    "purif_efficiency":  35,
    "purif_running_hrs": 36,
    "compressor_hrs":    37,
    "vpsa_kwh_init":     38,
    "vpsa_kwh_final":    39,
    "vpsa_kwh_total":    40,
    "bg_mfm_kwh_init":   41,
    "bg_mfm_kwh_final":  42,
    "bg_mfm_kwh_total":  43,
    "screw_press_hrs":   44,
    "vibro_screen_hrs":  45,
    "volute_press_hrs":  46,
    "screw_moisture":    47,
    "volute_moisture":   48,
    "raw_water_m3":      49,
    "digester_ph":       50,
    "digester_temp":     51,
    "flare_m3":          52,
    "poly_kg":           53,
    "dg_hrs":            54,
    "dg_diesel_l":       55,
    "hp_comp_kwh_init":  56,
    "hp_comp_kwh_final": 57,
    "purif_eff_calc":    58,
    "bg_recovery":       59,
    "remarks":           60,
}

# ──────────────────────────────────────────────
# Data loading helpers
# ──────────────────────────────────────────────

def _to_numeric_series(s: pd.Series) -> pd.Series:
    """Coerce a series to numeric; non-parseable become NaN."""
    return pd.to_numeric(s, errors="coerce")


def load_daily_operations(wb_path: str, plant_name: str) -> pd.DataFrame:
    """
    Parse the 'Daily Operations' sheet.
    Rows 0-3 are multi-level headers; data starts at row 4.
    Returns a tidy DataFrame with semantic column names.
    """
    raw = pd.read_excel(wb_path, sheet_name="Daily Operations", header=None)
    data = raw.iloc[4:].reset_index(drop=True)

    # Pick out only the columns we care about
    records = {}
    for name, idx in COL.items():
        if idx < data.shape[1]:
            records[name] = data.iloc[:, idx]
        else:
            records[name] = pd.Series(np.nan, index=data.index)

    df = pd.DataFrame(records)

    # Parse date – strip whitespace, try common formats
    df["date"] = pd.to_datetime(df["date"].astype(str).str.strip(),
                                 dayfirst=True, errors="coerce")
    df = df.dropna(subset=["date"])
    df = df.sort_values("date").reset_index(drop=True)

    # Numeric coercion for all non-date, non-remarks columns
    skip = {"date", "remarks"}
    for col in df.columns:
        if col not in skip:
            df[col] = _to_numeric_series(df[col])

    # Derived convenience columns
    df["total_sales_kg"] = df["cbg_sales_kg"].fillna(0) + df["cascade_sales_kg"].fillna(0)
    df["plant"] = plant_name
    return df


def load_lab_analysis(wb_path: str, plant_name: str) -> pd.DataFrame:
    """
    Parse 'Lab & Slurry Analysis' sheet.
    Row 0-1: title text; Row 2: column headers; Data from row 3.
    Date is in col[0] only for the first sample-point row; forward-fill it.
    """
    raw = pd.read_excel(wb_path, sheet_name="Lab & Slurry Analysis", header=None)
    # Row 2 has real headers
    headers = raw.iloc[2].tolist()
    data    = raw.iloc[3:].reset_index(drop=True).copy()
    data.columns = [str(h).replace("\n", " ").strip() for h in headers]

    # Rename for convenience
    col_map = {
        data.columns[0]: "date_raw",
        data.columns[1]: "sample_point",
        data.columns[2]: "pH",
        data.columns[3]: "EC_mScm",
        data.columns[4]: "TS_pct",
        data.columns[5]: "VS_pct",
        data.columns[6]: "Temp_C",
        data.columns[7]: "Carbon_pct",
    }
    data.rename(columns=col_map, inplace=True)

    # Forward-fill date from the first row of each daily block
    data["date_raw"] = data["date_raw"].ffill()
    data["date"] = pd.to_datetime(data["date_raw"].astype(str).str.strip(),
                                   dayfirst=True, errors="coerce")
    data = data.dropna(subset=["date", "sample_point"])
    data["sample_point"] = data["sample_point"].astype(str).str.strip()

    for col in ["pH", "EC_mScm", "TS_pct", "VS_pct", "Temp_C", "Carbon_pct"]:
        if col in data.columns:
            data[col] = _to_numeric_series(data[col])

    # Validation: drop physiologically impossible rows
    if "TS_pct" in data.columns:
        data = data[~(data["TS_pct"].notna() & ~data["TS_pct"].between(0, 100))]
    if "VS_pct" in data.columns:
        data = data[~(data["VS_pct"].notna() & ~data["VS_pct"].between(0, 100))]

    data["plant"] = plant_name
    return data[["date", "plant", "sample_point", "pH", "EC_mScm",
                 "TS_pct", "VS_pct", "Temp_C", "Carbon_pct"]].reset_index(drop=True)


def load_dung_quality(wb_path: str, plant_name: str) -> pd.DataFrame:
    """
    Parse 'Dung Route Quality' sheet.
    Row 0: route headers; Row 1: sub-column headers (Sand %, pH, EC, TS%); Row 2: units; Data from row 3.
    Pivots into long format: date | route | trip | Sand_pct | pH | EC | TS_pct
    """
    raw = pd.read_excel(wb_path, sheet_name="Dung Route Quality", header=None)
    route_row  = raw.iloc[0]
    subcol_row = raw.iloc[1]
    data       = raw.iloc[3:].reset_index(drop=True)

    records = []
    n_cols = data.shape[1]
    current_route = None
    # Column 0 is always "date"; the rest are route groups of 4 cols each
    for c in range(1, n_cols, 4):
        if c < len(route_row) and pd.notna(route_row.iloc[c]):
            current_route = str(route_row.iloc[c]).strip()
        if current_route is None:
            continue
        # 4 sub-columns: Sand %, pH, EC, TS %
        sub_names = []
        for k in range(4):
            if c + k < len(subcol_row) and pd.notna(subcol_row.iloc[c + k]):
                sub_names.append(str(subcol_row.iloc[c + k]).strip())
            else:
                sub_names.append(f"sub{k}")

        for row_idx, row in data.iterrows():
            date_val = pd.to_datetime(str(row.iloc[0]).strip(), dayfirst=True, errors="coerce")
            if pd.isna(date_val):
                continue
            rec = {"date": date_val, "route": current_route, "plant": plant_name}
            for k, sname in enumerate(sub_names):
                v = row.iloc[c + k] if (c + k) < len(row) else np.nan
                rec[sname] = pd.to_numeric(v, errors="coerce")
            records.append(rec)

    if not records:
        return pd.DataFrame()
    return pd.DataFrame(records).sort_values("date").reset_index(drop=True)


def load_fertilizer_quality(wb_path: str, plant_name: str) -> pd.DataFrame:
    """
    Parse 'Fertilizer Quality' sheet.
    Row 0: title; Row 1: column headers; data alternates section banners and data rows.
    Returns tidy rows with all quality parameters.
    """
    raw = pd.read_excel(wb_path, sheet_name="Fertilizer Quality", header=None)
    headers = raw.iloc[1].tolist()
    clean_headers = [str(h).replace("\n", " ").strip() for h in headers]
    data = raw.iloc[2:].reset_index(drop=True).copy()
    data.columns = clean_headers

    # Drop pure-banner rows (where Sr No is not numeric)
    sr_col = clean_headers[0]
    data = data[pd.to_numeric(data[sr_col], errors="coerce").notna()].copy()

    numeric_cols = [c for c in clean_headers if c not in
                    {"Sr.\nNo.", "Sr. No.", "Sample\nDate", "Sample Date",
                     "Material\nName", "Material Name", "Batch /\nType",
                     "Batch / Type", "Mfg Date\n/ Month", "Mfg Date / Month",
                     "Remarks /\nSampler", "Remarks / Sampler"}]
    for col in numeric_cols:
        if col in data.columns:
            data[col] = _to_numeric_series(data[col])

    data["plant"] = plant_name
    return data.reset_index(drop=True)


@st.cache_data(show_spinner=False)
def load_plant(file_bytes: bytes, plant_name: str) -> dict:
    """Load all sheets for a single plant file.  Cached by file content."""
    wb_path = io.BytesIO(file_bytes)

    def _safe(fn, *args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            st.warning(f"⚠️ [{plant_name}] {fn.__name__}: {e}")
            return pd.DataFrame()

    return {
        "ops":   _safe(load_daily_operations, wb_path, plant_name),
        "lab":   _safe(load_lab_analysis,     wb_path, plant_name),
        "dung":  _safe(load_dung_quality,     wb_path, plant_name),
        "fert":  _safe(load_fertilizer_quality, wb_path, plant_name),
    }


# ──────────────────────────────────────────────
# Chart helpers
# ──────────────────────────────────────────────

PALETTE = px.colors.qualitative.Bold

def _plant_color_map(plants: list) -> dict:
    return {p: PALETTE[i % len(PALETTE)] for i, p in enumerate(sorted(plants))}


def _ma(series: pd.Series, window: int = 7) -> pd.Series:
    return series.rolling(window, min_periods=1).mean()


def line_chart(df: pd.DataFrame, x: str, y: str | list,
               title: str, yaxis: str = "", color: str | None = None,
               ma_window: int = 0) -> go.Figure:
    """Generic multi-series line chart."""
    fig = go.Figure()
    ys = [y] if isinstance(y, str) else y
    colors = PALETTE

    for i, col in enumerate(ys):
        if col not in df.columns:
            continue
        grp_col = color if color else "plant"
        if grp_col in df.columns:
            for j, (grp, gdf) in enumerate(df.groupby(grp_col)):
                c = colors[(i + j) % len(colors)]
                fig.add_trace(go.Scatter(
                    x=gdf[x], y=gdf[col],
                    mode="lines", name=f"{grp} – {col}",
                    line=dict(color=c, width=1.5), opacity=0.85
                ))
                if ma_window > 1:
                    fig.add_trace(go.Scatter(
                        x=gdf[x], y=_ma(gdf[col], ma_window),
                        mode="lines", name=f"{grp} – {col} ({ma_window}d MA)",
                        line=dict(color=c, width=2.5, dash="dash"), showlegend=False
                    ))
        else:
            fig.add_trace(go.Scatter(
                x=df[x], y=df[col], mode="lines", name=col,
                line=dict(color=colors[i % len(colors)], width=2)
            ))

    fig.update_layout(
        title=title, title_x=0,
        xaxis_title=x, yaxis_title=yaxis,
        paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
        font=dict(color="#e0e0e0"),
        legend=dict(bgcolor="rgba(0,0,0,0.5)", bordercolor="#444"),
        hovermode="x unified",
        height=380,
    )
    fig.update_xaxes(showgrid=True, gridcolor="#1e3a5f")
    fig.update_yaxes(showgrid=True, gridcolor="#1e3a5f")
    return fig


def bar_chart(df: pd.DataFrame, x: str, y: str, title: str,
              color: str | None = None, barmode: str = "group") -> go.Figure:
    cmap = _plant_color_map(df["plant"].unique()) if "plant" in df.columns else {}
    fig = px.bar(df, x=x, y=y, color=color,
                 title=title, color_discrete_map=cmap,
                 barmode=barmode, template="plotly_dark")
    fig.update_layout(
        paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
        height=380, title_x=0, hovermode="x unified",
    )
    return fig


def scatter_chart(df: pd.DataFrame, x: str, y: str, title: str,
                  color: str | None = None, trendline: bool = True) -> go.Figure:
    cmap = _plant_color_map(df["plant"].unique()) if "plant" in df.columns else {}
    trend = "ols" if trendline else None
    fig = px.scatter(df, x=x, y=y, color=color, trendline=trend,
                     title=title, color_discrete_map=cmap, template="plotly_dark")
    fig.update_layout(
        paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
        height=400, title_x=0,
    )
    return fig


def gauge_chart(value: float, title: str, min_val: float = 0,
                max_val: float = 100, suffix: str = "%") -> go.Figure:
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        title={"text": title, "font": {"size": 14, "color": "#e0e0e0"}},
        number={"suffix": suffix, "font": {"color": "#4fc3f7"}},
        gauge=dict(
            axis=dict(range=[min_val, max_val], tickcolor="#e0e0e0"),
            bar=dict(color="#1565c0"),
            bgcolor="#0d2137",
            borderwidth=1, bordercolor="#2d5a8e",
            steps=[
                dict(range=[min_val, max_val * 0.5], color="#1a237e"),
                dict(range=[max_val * 0.5, max_val * 0.75], color="#0d47a1"),
                dict(range=[max_val * 0.75, max_val], color="#1565c0"),
            ],
            threshold=dict(line=dict(color="#ef5350", width=3),
                           thickness=0.8, value=max_val * 0.9)
        )
    ))
    fig.update_layout(
        paper_bgcolor="#0e1117", font=dict(color="#e0e0e0"),
        height=260, margin=dict(l=20, r=20, t=40, b=10)
    )
    return fig


# ──────────────────────────────────────────────
# Sidebar – file upload & plant management
# ──────────────────────────────────────────────

def sidebar_uploads() -> tuple[dict, list[str], dict]:
    """Return (all_data, selected_plants, date_filter)."""
    with st.sidebar:
        st.markdown("## ⚡ Biogas Dashboard")
        st.markdown("---")

        uploaded = st.file_uploader(
            "📂 Upload plant Excel file(s)",
            type=["xlsx"],
            accept_multiple_files=True,
            help="Upload one file per plant using the Unified Daily Report format.",
        )

        all_data = {}
        if uploaded:
            for f in uploaded:
                bytes_val = f.read()
                # Use filename (minus extension) as default plant name
                default_name = f.name.replace(".xlsx", "").replace("_", " ").title()
                plant_name = st.text_input(
                    f"Plant name for '{f.name}'",
                    value=default_name,
                    key=f"name_{f.name}",
                )
                with st.spinner(f"Loading {plant_name}…"):
                    all_data[plant_name] = load_plant(bytes_val, plant_name)

        if not all_data:
            st.info("Upload one or more plant Excel files to begin.")
            return {}, [], {}

        st.markdown("---")
        st.markdown("### 🏭 Plant Selection")
        plant_names = list(all_data.keys())
        selected = st.multiselect("Show plants", plant_names, default=plant_names)

        # Date filter using the union of all ops data
        all_ops = [all_data[p]["ops"] for p in selected if not all_data[p]["ops"].empty]
        if all_ops:
            combined = pd.concat(all_ops)
            min_date = combined["date"].min().date()
            max_date = combined["date"].max().date()
            st.markdown("### 📅 Date Range")
            date_range = st.date_input(
                "Filter dates",
                value=(min_date, max_date),
                min_value=min_date,
                max_value=max_date,
            )
            date_filter = {
                "start": pd.Timestamp(date_range[0]),
                "end":   pd.Timestamp(date_range[1] if len(date_range) > 1 else date_range[0]),
            }
        else:
            date_filter = {}

        st.markdown("---")
        st.markdown("### ⚙️ Chart Options")
        ma_win = st.slider("Moving average (days)", 1, 30, 7, key="ma_window")
        st.session_state["ma_window"] = ma_win

        return all_data, selected, date_filter


def _filter_ops(all_data: dict, selected: list, date_filter: dict) -> pd.DataFrame:
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


def _filter_lab(all_data: dict, selected: list, date_filter: dict) -> pd.DataFrame:
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


# ──────────────────────────────────────────────
# KPI row
# ──────────────────────────────────────────────

def render_kpis(ops: pd.DataFrame):
    if ops.empty:
        st.warning("No operational data for the selected range.")
        return

    def safe_mean(col):
        return ops[col].dropna().mean() if col in ops.columns else np.nan

    def safe_sum(col):
        return ops[col].dropna().sum() if col in ops.columns else np.nan

    kpis = {
        "🌿 Avg Biogas Gen (m³/d)": f"{safe_mean('total_generated_gas'):.1f}",
        "🏭 Total CBG Sales (kg)": f"{safe_sum('cbg_sales_kg'):,.0f}",
        "⚗️ Avg Purif. Eff. (%)": f"{safe_mean('purif_efficiency'):.1f}",
        "🔬 Avg CH₄ Raw (%)": f"{safe_mean('raw_ch4'):.1f}",
        "🔬 Avg CH₄ Pure (%)": f"{safe_mean('pure_ch4'):.1f}",
        "🌡️ Avg Digester Temp (°C)": f"{safe_mean('digester_temp'):.1f}",
        "⚡ Avg VPSA KWH/d": f"{safe_mean('vpsa_kwh_total'):.1f}",
        "🐄 Avg Dung (tons/d)": f"{safe_mean('dung_tons'):.1f}",
    }

    cols = st.columns(len(kpis))
    for col_widget, (label, val) in zip(cols, kpis.items()):
        with col_widget:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{val}</div>
                <div class="metric-label">{label}</div>
            </div>""", unsafe_allow_html=True)


# ──────────────────────────────────────────────
# Tab 1 – Gas Production & Quality
# ──────────────────────────────────────────────

def tab_gas(ops: pd.DataFrame):
    st.markdown('<div class="section-header">📊 Gas Production & Quality</div>', unsafe_allow_html=True)
    ma = st.session_state.get("ma_window", 7)

    c1, c2 = st.columns(2)
    with c1:
        if "total_generated_gas" in ops.columns:
            fig = line_chart(ops, "date", "total_generated_gas",
                             "Raw Biogas Generated (m³/day)", "m³/day",
                             color="plant", ma_window=ma)
            st.plotly_chart(fig, use_container_width=True)

    with c2:
        if "total_purified_gas" in ops.columns:
            fig = line_chart(ops, "date", "total_purified_gas",
                             "Purified Gas (m³/day)", "m³/day",
                             color="plant", ma_window=ma)
            st.plotly_chart(fig, use_container_width=True)

    c3, c4 = st.columns(2)
    with c3:
        if all(c in ops.columns for c in ["raw_ch4", "raw_co2"]):
            fig = go.Figure()
            cmap = _plant_color_map(ops["plant"].unique())
            for p, gdf in ops.groupby("plant"):
                c = cmap[p]
                fig.add_trace(go.Scatter(x=gdf["date"], y=gdf["raw_ch4"],
                                          name=f"{p} – CH₄", line=dict(color=c, width=1.5)))
                fig.add_trace(go.Scatter(x=gdf["date"], y=gdf["raw_co2"],
                                          name=f"{p} – CO₂", line=dict(color=c, width=1.5, dash="dot")))
            fig.update_layout(title="Raw Biogas Composition (%)",
                               paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
                               font=dict(color="#e0e0e0"), height=380, hovermode="x unified")
            fig.update_xaxes(showgrid=True, gridcolor="#1e3a5f")
            fig.update_yaxes(showgrid=True, gridcolor="#1e3a5f")
            st.plotly_chart(fig, use_container_width=True)

    with c4:
        if all(c in ops.columns for c in ["pure_ch4", "pure_co2"]):
            fig = go.Figure()
            cmap = _plant_color_map(ops["plant"].unique())
            for p, gdf in ops.groupby("plant"):
                c = cmap[p]
                fig.add_trace(go.Scatter(x=gdf["date"], y=gdf["pure_ch4"],
                                          name=f"{p} – CH₄", line=dict(color=c, width=1.5)))
                fig.add_trace(go.Scatter(x=gdf["date"], y=gdf["pure_co2"],
                                          name=f"{p} – CO₂", line=dict(color=c, width=1.5, dash="dot")))
            fig.update_layout(title="Purified Gas Composition (%)",
                               paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
                               font=dict(color="#e0e0e0"), height=380, hovermode="x unified")
            fig.update_xaxes(showgrid=True, gridcolor="#1e3a5f")
            fig.update_yaxes(showgrid=True, gridcolor="#1e3a5f")
            st.plotly_chart(fig, use_container_width=True)

    # H₂S trend
    st.markdown('<div class="section-header">⚠️ H₂S Levels (PPM)</div>', unsafe_allow_html=True)
    c5, c6 = st.columns(2)
    with c5:
        fig = line_chart(ops, "date", "raw_h2s", "Raw Gas H₂S (PPM)", "PPM",
                         color="plant", ma_window=ma)
        st.plotly_chart(fig, use_container_width=True)
    with c6:
        fig = line_chart(ops, "date", "pure_h2s", "Purified Gas H₂S (PPM)", "PPM",
                         color="plant", ma_window=ma)
        st.plotly_chart(fig, use_container_width=True)


# ──────────────────────────────────────────────
# Tab 2 – Feedstock & Feeding
# ──────────────────────────────────────────────

def tab_feed(ops: pd.DataFrame):
    st.markdown('<div class="section-header">🐄 Feedstock & Feeding</div>', unsafe_allow_html=True)
    ma = st.session_state.get("ma_window", 7)

    c1, c2 = st.columns(2)
    with c1:
        fig = line_chart(ops, "date", "dung_tons", "Dung Collected (tons/day)", "tons",
                         color="plant", ma_window=ma)
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        fig = line_chart(ops, "date", "total_feed_m3", "Total Feed to Reactor (m³/day)", "m³",
                         color="plant", ma_window=ma)
        st.plotly_chart(fig, use_container_width=True)

    c3, c4 = st.columns(2)
    with c3:
        fig = line_chart(ops, "date", "total_filter_water", "Filter Water Consumed (m³/day)", "m³",
                         color="plant", ma_window=ma)
        st.plotly_chart(fig, use_container_width=True)
    with c4:
        if "waste_potato_tons" in ops.columns and ops["waste_potato_tons"].notna().any():
            fig = line_chart(ops, "date", "waste_potato_tons", "Waste Potato Added (tons/day)", "tons",
                             color="plant", ma_window=ma)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No waste-potato data available for selected plants.")

    # Biogas yield per ton of dung
    st.markdown('<div class="section-header">📈 Specific Biogas Yield</div>', unsafe_allow_html=True)
    ops2 = ops.copy()
    ops2["yield_m3_per_ton"] = np.where(
        ops2["dung_tons"] > 0,
        ops2["total_generated_gas"] / ops2["dung_tons"],
        np.nan
    )
    fig = line_chart(ops2, "date", "yield_m3_per_ton",
                     "Biogas Yield (m³ per ton of dung)", "m³/ton",
                     color="plant", ma_window=ma)
    st.plotly_chart(fig, use_container_width=True)


# ──────────────────────────────────────────────
# Tab 3 – Purification & CBG Sales
# ──────────────────────────────────────────────

def tab_purif(ops: pd.DataFrame):
    st.markdown('<div class="section-header">⚗️ Purification & CBG Sales</div>', unsafe_allow_html=True)
    ma = st.session_state.get("ma_window", 7)

    c1, c2 = st.columns(2)
    with c1:
        fig = line_chart(ops, "date", "purif_efficiency", "Purification Efficiency (%)", "%",
                         color="plant", ma_window=ma)
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        fig = line_chart(ops, "date", "bg_recovery", "Biogas Recovery (%)", "%",
                         color="plant", ma_window=ma)
        st.plotly_chart(fig, use_container_width=True)

    c3, c4 = st.columns(2)
    with c3:
        fig = line_chart(ops, "date", "cbg_sales_kg", "CBG Sales – Dispenser (kg/day)", "kg",
                         color="plant", ma_window=ma)
        st.plotly_chart(fig, use_container_width=True)
    with c4:
        fig = line_chart(ops, "date", "total_sales_kg", "Total CBG Sales (kg/day)", "kg",
                         color="plant", ma_window=ma)
        st.plotly_chart(fig, use_container_width=True)

    # Monthly aggregate
    st.markdown('<div class="section-header">📅 Monthly CBG Sales</div>', unsafe_allow_html=True)
    monthly = (ops.copy()
                .assign(month=ops["date"].dt.to_period("M").astype(str))
                .groupby(["month", "plant"], as_index=False)["cbg_sales_kg"]
                .sum())
    fig = bar_chart(monthly, "month", "cbg_sales_kg",
                    "Monthly CBG Sales (kg)", color="plant", barmode="group")
    st.plotly_chart(fig, use_container_width=True)

    # Vehicles served
    c5, c6 = st.columns(2)
    with c5:
        fig = line_chart(ops, "date", "num_vehicles", "Vehicles Served / Day", "count",
                         color="plant", ma_window=ma)
        st.plotly_chart(fig, use_container_width=True)
    with c6:
        fig = line_chart(ops, "date", "purif_running_hrs", "Purification Running Hrs / Day", "hrs",
                         color="plant", ma_window=ma)
        st.plotly_chart(fig, use_container_width=True)


# ──────────────────────────────────────────────
# Tab 4 – Power & Utilities
# ──────────────────────────────────────────────

def tab_power(ops: pd.DataFrame):
    st.markdown('<div class="section-header">⚡ Power & Utility Consumption</div>', unsafe_allow_html=True)
    ma = st.session_state.get("ma_window", 7)

    c1, c2 = st.columns(2)
    with c1:
        fig = line_chart(ops, "date", "vpsa_kwh_total", "VPSA Power Consumed (KWH/day)", "KWH",
                         color="plant", ma_window=ma)
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        fig = line_chart(ops, "date", "bg_mfm_kwh_total", "Biogas MFM Power Consumed (KWH/day)", "KWH",
                         color="plant", ma_window=ma)
        st.plotly_chart(fig, use_container_width=True)

    c3, c4 = st.columns(2)
    with c3:
        fig = line_chart(ops, "date", "raw_water_m3", "Raw Water Consumed (m³/day)", "m³",
                         color="plant", ma_window=ma)
        st.plotly_chart(fig, use_container_width=True)
    with c4:
        fig = line_chart(ops, "date", "poly_kg", "Poly Consumption (kg/day)", "kg",
                         color="plant", ma_window=ma)
        st.plotly_chart(fig, use_container_width=True)

    c5, c6 = st.columns(2)
    with c5:
        fig = line_chart(ops, "date", "dg_hrs", "DG Running Hours / Day", "hrs",
                         color="plant", ma_window=ma)
        st.plotly_chart(fig, use_container_width=True)
    with c6:
        fig = line_chart(ops, "date", "dg_diesel_l", "DG Diesel Consumed (L/day)", "Litres",
                         color="plant", ma_window=ma)
        st.plotly_chart(fig, use_container_width=True)

    # Specific energy: KWH per m³ of purified gas
    st.markdown('<div class="section-header">💡 Specific Energy</div>', unsafe_allow_html=True)
    ops2 = ops.copy()
    ops2["kwh_per_m3"] = np.where(
        ops2["total_purified_gas"] > 0,
        ops2["vpsa_kwh_total"] / ops2["total_purified_gas"],
        np.nan
    )
    fig = line_chart(ops2, "date", "kwh_per_m3",
                     "VPSA Specific Energy (KWH / m³ purified gas)", "KWH/m³",
                     color="plant", ma_window=ma)
    st.plotly_chart(fig, use_container_width=True)


# ──────────────────────────────────────────────
# Tab 5 – Digester & Dewatering
# ──────────────────────────────────────────────

def tab_digester(ops: pd.DataFrame):
    st.markdown('<div class="section-header">🌡️ Digester Conditions</div>', unsafe_allow_html=True)
    ma = st.session_state.get("ma_window", 7)

    c1, c2 = st.columns(2)
    with c1:
        fig = line_chart(ops, "date", "digester_temp", "Digester Temperature (°C, 9-10 AM)", "°C",
                         color="plant", ma_window=ma)
        fig.add_hline(y=37, line_dash="dash", line_color="#ef9a9a",
                       annotation_text="Mesophilic optimum (37°C)")
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        fig = line_chart(ops, "date", "digester_ph", "Digester pH (Mid)", "pH",
                         color="plant", ma_window=ma)
        fig.add_hrect(y0=6.8, y1=7.5, fillcolor="#1b5e20", opacity=0.15,
                       annotation_text="Optimal pH 6.8-7.5")
        st.plotly_chart(fig, use_container_width=True)

    st.markdown('<div class="section-header">💧 Dewatering & Flare</div>', unsafe_allow_html=True)
    c3, c4 = st.columns(2)
    with c3:
        fig = go.Figure()
        cmap = _plant_color_map(ops["plant"].unique())
        for p, gdf in ops.groupby("plant"):
            c = cmap[p]
            fig.add_trace(go.Scatter(x=gdf["date"], y=gdf["screw_moisture"],
                                      name=f"{p} – Screw", line=dict(color=c, width=1.5)))
            fig.add_trace(go.Scatter(x=gdf["date"], y=gdf["volute_moisture"],
                                      name=f"{p} – Volute", line=dict(color=c, width=1.5, dash="dot")))
        fig.update_layout(title="Dewatering Moisture (%)", paper_bgcolor="#0e1117",
                           plot_bgcolor="#0e1117", font=dict(color="#e0e0e0"),
                           height=380, hovermode="x unified")
        st.plotly_chart(fig, use_container_width=True)

    with c4:
        fig = line_chart(ops, "date", "flare_m3", "Flare Gas (m³/day)", "m³",
                         color="plant", ma_window=ma)
        st.plotly_chart(fig, use_container_width=True)

    # Dewatering running hours
    c5, c6, c7 = st.columns(3)
    with c5:
        fig = line_chart(ops, "date", "screw_press_hrs", "Screw Press Running Hrs", "hrs",
                         color="plant", ma_window=1)
        st.plotly_chart(fig, use_container_width=True)
    with c6:
        fig = line_chart(ops, "date", "vibro_screen_hrs", "Vibro Screen Running Hrs", "hrs",
                         color="plant", ma_window=1)
        st.plotly_chart(fig, use_container_width=True)
    with c7:
        fig = line_chart(ops, "date", "volute_press_hrs", "Volute Press Running Hrs", "hrs",
                         color="plant", ma_window=1)
        st.plotly_chart(fig, use_container_width=True)


# ──────────────────────────────────────────────
# Tab 6 – Lab & Slurry Analysis
# ──────────────────────────────────────────────

def tab_lab(all_data: dict, selected: list, date_filter: dict):
    st.markdown('<div class="section-header">🔬 Lab & Slurry Analysis</div>', unsafe_allow_html=True)

    lab = _filter_lab(all_data, selected, date_filter)
    if lab.empty:
        st.info("No lab data available for the selected plants / date range.")
        return

    sample_points = sorted(lab["sample_point"].dropna().unique())
    chosen_pts = st.multiselect(
        "Sample Points", sample_points,
        default=[s for s in ["RCD (Raw Cattle Dung)", "Digester Mid Sampling Point",
                              "Mixing Tank", "Slurry Tank"] if s in sample_points] or sample_points[:3]
    )
    if not chosen_pts:
        st.info("Select at least one sample point above.")
        return

    lab_f = lab[lab["sample_point"].isin(chosen_pts)]

    for param, label in [("pH", "pH"), ("TS_pct", "TS (%)"), ("VS_pct", "VS (%)"),
                          ("EC_mScm", "EC (mS/cm)"), ("Temp_C", "Temperature (°C)"),
                          ("Carbon_pct", "Carbon (%)")]:
        if param not in lab_f.columns or lab_f[param].dropna().empty:
            continue
        fig = px.line(lab_f.dropna(subset=[param]),
                      x="date", y=param, color="sample_point",
                      facet_col="plant" if len(selected) > 1 else None,
                      title=f"{label} by Sample Point",
                      template="plotly_dark")
        fig.update_layout(paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
                           font=dict(color="#e0e0e0"), height=360)
        st.plotly_chart(fig, use_container_width=True)

    # TS vs VS scatter
    st.markdown('<div class="section-header">TS vs VS Correlation</div>', unsafe_allow_html=True)
    valid = lab_f.dropna(subset=["TS_pct", "VS_pct"])
    if not valid.empty:
        fig = scatter_chart(valid, "TS_pct", "VS_pct",
                            "TS (%) vs VS (%)", color="sample_point")
        st.plotly_chart(fig, use_container_width=True)


# ──────────────────────────────────────────────
# Tab 7 – Cross-Plant Comparison
# ──────────────────────────────────────────────

def tab_compare(all_data: dict, selected: list, date_filter: dict):
    st.markdown('<div class="section-header">📊 Cross-Plant Comparison</div>', unsafe_allow_html=True)

    if len(selected) < 2:
        st.info("Select at least 2 plants from the sidebar to use this tab.")
        return

    ops = _filter_ops(all_data, selected, date_filter)
    if ops.empty:
        st.warning("No operational data.")
        return

    # Monthly aggregation
    monthly = (ops.assign(month=ops["date"].dt.to_period("M").astype(str))
               .groupby(["month", "plant"], as_index=False)
               .agg(
                   total_generated_gas=("total_generated_gas", "sum"),
                   total_purified_gas=("total_purified_gas", "sum"),
                   cbg_sales_kg=("cbg_sales_kg", "sum"),
                   avg_purif_eff=("purif_efficiency", "mean"),
                   avg_ch4_raw=("raw_ch4", "mean"),
                   avg_ch4_pure=("pure_ch4", "mean"),
                   avg_digester_temp=("digester_temp", "mean"),
                   dung_tons=("dung_tons", "sum"),
               ))

    params = {
        "total_generated_gas":  "Monthly Raw Biogas (m³)",
        "total_purified_gas":   "Monthly Purified Gas (m³)",
        "cbg_sales_kg":         "Monthly CBG Sales (kg)",
        "avg_purif_eff":        "Avg Purification Efficiency (%)",
        "avg_ch4_raw":          "Avg Raw CH₄ (%)",
        "avg_ch4_pure":         "Avg Pure CH₄ (%)",
        "avg_digester_temp":    "Avg Digester Temp (°C)",
        "dung_tons":            "Total Dung Collected (tons)",
    }

    for col, title in params.items():
        if col in monthly.columns and monthly[col].notna().any():
            fig = bar_chart(monthly, "month", col, title, color="plant", barmode="group")
            st.plotly_chart(fig, use_container_width=True)

    # Radar / spider for latest month averages
    st.markdown('<div class="section-header">🕸️ Plant Profile (Latest Period Average)</div>',
                unsafe_allow_html=True)
    radar_metrics = ["avg_purif_eff", "avg_ch4_raw", "avg_ch4_pure"]
    latest = monthly.groupby("plant")[radar_metrics].mean().reset_index()
    if not latest.empty:
        fig = go.Figure()
        for _, row in latest.iterrows():
            vals = [row[m] for m in radar_metrics] + [row[radar_metrics[0]]]
            labels = ["Purif Eff %", "CH₄ Raw %", "CH₄ Pure %", "Purif Eff %"]
            fig.add_trace(go.Scatterpolar(r=vals, theta=labels,
                                           fill="toself", name=row["plant"]))
        fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
                           showlegend=True,
                           paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
                           font=dict(color="#e0e0e0"), height=420)
        st.plotly_chart(fig, use_container_width=True)


# ──────────────────────────────────────────────
# Tab 8 – Dung Route Quality
# ──────────────────────────────────────────────

def tab_dung_routes(all_data: dict, selected: list, date_filter: dict):
    st.markdown('<div class="section-header">🚛 Dung Route Quality</div>', unsafe_allow_html=True)

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
        st.info("No dung route quality data for selected plants.")
        return

    dung = pd.concat(frames, ignore_index=True)
    routes = sorted(dung["route"].dropna().unique())
    chosen = st.multiselect("Routes", routes, default=routes[:6] if len(routes) > 6 else routes)
    dung_f = dung[dung["route"].isin(chosen)]

    for col, label in [("Sand (%)", "Sand (%)"), ("pH", "pH"), ("EC", "EC"), ("TS (%)", "TS (%)")]:
        matching = [c for c in dung_f.columns if c.strip().lower() == col.strip().lower()]
        if not matching:
            continue
        real_col = matching[0]
        if dung_f[real_col].dropna().empty:
            continue
        fig = px.box(dung_f.dropna(subset=[real_col]),
                     x="route", y=real_col, color="plant",
                     title=f"Dung Route – {label} Distribution",
                     template="plotly_dark")
        fig.update_layout(paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
                           font=dict(color="#e0e0e0"), height=360)
        st.plotly_chart(fig, use_container_width=True)


# ──────────────────────────────────────────────
# Tab 9 – Fertilizer Quality
# ──────────────────────────────────────────────

def tab_fertilizer(all_data: dict, selected: list):
    st.markdown('<div class="section-header">🌱 Organic Fertilizer Quality</div>', unsafe_allow_html=True)

    frames = []
    for p in selected:
        df = all_data[p]["fert"]
        if df.empty:
            continue
        frames.append(df)

    if not frames:
        st.info("No fertilizer quality data for selected plants.")
        return

    fert = pd.concat(frames, ignore_index=True)

    numeric_cols = fert.select_dtypes(include=[np.number]).columns.tolist()
    if not numeric_cols:
        st.dataframe(fert.head(30), use_container_width=True)
        return

    # Box plots for each numeric parameter
    param_col = st.selectbox("Parameter", numeric_cols)
    material_col = None
    for c in fert.columns:
        if "material" in str(c).lower() or "name" in str(c).lower():
            material_col = c
            break

    if material_col and material_col in fert.columns:
        fig = px.box(fert.dropna(subset=[param_col]),
                     x=material_col, y=param_col, color="plant",
                     title=f"Fertilizer {param_col} by Material",
                     template="plotly_dark")
    else:
        fig = px.box(fert.dropna(subset=[param_col]),
                     y=param_col, color="plant",
                     title=f"Fertilizer {param_col}",
                     template="plotly_dark")

    fig.update_layout(paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
                       font=dict(color="#e0e0e0"), height=420)
    st.plotly_chart(fig, use_container_width=True)

    with st.expander("View raw fertilizer data"):
        st.dataframe(fert, use_container_width=True)


# ──────────────────────────────────────────────
# Tab 10 – Raw Data Explorer
# ──────────────────────────────────────────────

def tab_raw(ops: pd.DataFrame):
    st.markdown('<div class="section-header">🗄️ Raw Data Explorer</div>', unsafe_allow_html=True)

    if ops.empty:
        st.info("No data loaded.")
        return

    col_choices = [c for c in ops.columns if c not in ("plant",)]
    selected_cols = st.multiselect("Columns to display",
                                   col_choices,
                                   default=["date", "plant", "dung_tons",
                                            "total_generated_gas", "total_purified_gas",
                                            "cbg_sales_kg", "purif_efficiency",
                                            "raw_ch4", "pure_ch4", "digester_temp"])
    display_cols = [c for c in selected_cols if c in ops.columns]
    if display_cols:
        st.dataframe(ops[display_cols].sort_values("date", ascending=False),
                     use_container_width=True, height=600)

    # CSV download
    csv = ops.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="⬇️ Download filtered data as CSV",
        data=csv,
        file_name="biogas_filtered_data.csv",
        mime="text/csv",
    )

    # Summary statistics
    with st.expander("📊 Summary Statistics"):
        num_cols = ops.select_dtypes(include=[np.number]).columns.tolist()
        st.dataframe(ops[num_cols].describe().T.round(2), use_container_width=True)


# ──────────────────────────────────────────────
# Main app
# ──────────────────────────────────────────────

def main():
    all_data, selected, date_filter = sidebar_uploads()

    if not all_data or not selected:
        # Landing / welcome screen
        st.markdown("## ⚡ Biogas Plant Analytics Dashboard")
        st.markdown("""
        Welcome! This dashboard works with the **Unified Daily Report Excel format**.

        **How to use:**
        1. Upload one `.xlsx` file per plant in the sidebar (use the Unified Daily Report template).
        2. Optionally rename each plant in the sidebar.
        3. Filter by date range.
        4. Navigate the tabs to explore gas production, purification, lab data, and more.

        **Scalable:** Add as many plants as you like — the code reads any number of files
        without plant-specific hard-coding.  Columns missing in a given plant's file will
        simply show as unavailable for that plant.
        """)
        return

    # Header with active plant badges
    badges = " ".join(f'<span class="plant-badge">🏭 {p}</span>' for p in selected)
    st.markdown(f"## ⚡ Biogas Plant Analytics &nbsp;&nbsp; {badges}", unsafe_allow_html=True)

    # Build combined ops DataFrame for the selected plants + date range
    ops = _filter_ops(all_data, selected, date_filter)

    # KPI row
    render_kpis(ops)
    st.markdown("---")

    # Tabs
    tabs = st.tabs([
        "📊 Gas Production",
        "🐄 Feedstock",
        "⚗️ Purification & Sales",
        "⚡ Power & Utilities",
        "🌡️ Digester & Dewatering",
        "🔬 Lab Analysis",
        "📊 Cross-Plant Compare",
        "🚛 Dung Routes",
        "🌱 Fertilizer",
        "🗄️ Raw Data",
    ])

    with tabs[0]:
        tab_gas(ops)
    with tabs[1]:
        tab_feed(ops)
    with tabs[2]:
        tab_purif(ops)
    with tabs[3]:
        tab_power(ops)
    with tabs[4]:
        tab_digester(ops)
    with tabs[5]:
        tab_lab(all_data, selected, date_filter)
    with tabs[6]:
        tab_compare(all_data, selected, date_filter)
    with tabs[7]:
        tab_dung_routes(all_data, selected, date_filter)
    with tabs[8]:
        tab_fertilizer(all_data, selected)
    with tabs[9]:
        tab_raw(ops)


if __name__ == "__main__":
    main()
