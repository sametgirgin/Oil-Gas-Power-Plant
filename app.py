from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


st.set_page_config(page_title="Oil & Gas Power Plants", layout="wide")

DATA_PATH = Path(__file__).parent / "Global-Oil-and-Gas-Plant-Tracker-GOGPT-February-2024-v4.xlsx"
GLOSSARY_PATH = Path(__file__).parent / "glossary.md"
TECH_IMAGE_PATH = Path(__file__).parent / "tech.png"
CHP_IMAGE_PATH = Path(__file__).parent / "chp.png"
SHEET_NAME = "Gas & Oil Units"
PARQUET_CACHE = Path(__file__).parent / "gogpt_cache.parquet"

SIDEBAR_FILTER_STYLE = """
<style>
/* Sidebar dropdown styling */
section[data-testid="stSidebar"] .stSelectbox label {
    font-weight: 600;
    color: #0f172a;
}
section[data-testid="stSidebar"] .stSelectbox div[data-baseweb="select"] {
    border: 1.5px solid #0f172a;
    border-radius: 6px;
    box-shadow: 0 1px 2px rgba(0,0,0,0.08);
    background: #ffffff;
}
section[data-testid="stSidebar"] .stSelectbox div[data-baseweb="select"]:hover {
    border-color: #2563eb;
}
</style>
"""


def _read_source_data(data_path: Path) -> pd.DataFrame:
    """Read Excel and write a parquet cache for faster reloads."""
    df = pd.read_excel(data_path, sheet_name=SHEET_NAME)
    try:
        df.to_parquet(PARQUET_CACHE, index=False)
    except Exception:
        # If parquet fails (e.g., missing fastparquet/pyarrow), continue without caching.
        pass
    return df


@st.cache_data(show_spinner=False)
def load_data(data_path: Path, last_modified: float, cache_last_modified: float) -> pd.DataFrame:
    if not data_path.exists():
        st.error(f"Data file not found: {data_path.name}")
        st.stop()

    use_parquet = (
        PARQUET_CACHE.exists() and cache_last_modified >= last_modified
    )

    if use_parquet:
        df = pd.read_parquet(PARQUET_CACHE)
    else:
        df = _read_source_data(data_path)

    # Normalize text columns so filters behave consistently.
    text_cols = ["Country", "Status", "Fuel", "Region", "Hydrogen capable?", "Technology", "CHP"]
    for col in text_cols:
        df[col] = df[col].fillna("Unknown")

    # Standardize CHP values to a small, consistent set.
    if "CHP" in df.columns:
        chp_map = {"yes": "Yes", "y": "Yes", "no": "No", "n": "No", "not found": "Not found"}
        df["CHP"] = (
            df["CHP"]
            .astype(str)
            .str.strip()
            .str.lower()
            .map(chp_map)
            .fillna("Unknown")
        )

    # Coerce numeric columns to numeric for calculations/visuals.
    numeric_cols = ["Capacity (MW)", "Latitude", "Longitude", "Start year"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


@st.cache_data(show_spinner=False)
def load_glossary_text(path: Path, last_modified: float) -> str:
    if not path.exists():
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def build_filters(df: pd.DataFrame) -> Dict[str, List[str]]:
    st.sidebar.markdown(SIDEBAR_FILTER_STYLE, unsafe_allow_html=True)
    st.sidebar.header("Filters")
    filters = {}
    options: Dict[str, str] = {
        "Country": "Country",
        "Status": "Status",
        "Fuel": "Fuel",
        "Hydrogen capable?": "Hydrogen capable?",
        "Region": "Region",
        "Technology": "Technology",
        "CHP": "CHP",
    }

    for col, label in options.items():
        values = ["All"] + sorted(df[col].dropna().unique())
        choice = st.sidebar.selectbox(label=label, options=values, index=0)
        filters[col] = [choice] if choice != "All" else values[1:]

    return filters


def apply_filters(df: pd.DataFrame, selections: Dict[str, List[str]]) -> pd.DataFrame:
    for col, chosen in selections.items():
        if chosen:
            df = df[df[col].isin(chosen)]
    return df


def make_map(df: pd.DataFrame) -> Optional[go.Figure]:
    plot_df = df.dropna(subset=["Latitude", "Longitude", "Capacity (MW)"])
    if plot_df.empty:
        st.warning("No plants match the current filters.")
        return None

    fig = px.scatter_mapbox(
        plot_df,
        lat="Latitude",
        lon="Longitude",
        size="Capacity (MW)",
        size_max=40,
        color="Status",
        hover_name="Plant name",
        hover_data={
            "Unit name": True,
            "Country": True,
            "City": True,
            "Fuel": True,
            "Capacity (MW)": ":.1f",
            "Technology": True,
            "Hydrogen capable?": True,
            "Status": True,
            "Start year": True,
            "Owner": True,
            "Latitude": ":.4f",
            "Longitude": ":.4f",
        },
        zoom=1,
        height=650,
        mapbox_style="carto-positron",
    )
    fig.update_layout(margin=dict(l=0, r=0, t=0, b=0))
    return fig


def main() -> None:
    logo_path = Path(__file__).parent / "logo.png"
    title_col, logo_col = st.columns([3, 1])
    with title_col:
        st.title("Global Oil & Gas Power Plants")
    with logo_col:
        if logo_path.exists():
            st.image(str(logo_path), use_column_width=True)

    st.caption(
        "Bubble size represents capacity (MW). Use the sidebar to filter by country, status, fuel, hydrogen capability, region, technology, and CHP."
    )

    data_mtime = DATA_PATH.stat().st_mtime if DATA_PATH.exists() else 0
    glossary_mtime = GLOSSARY_PATH.stat().st_mtime if GLOSSARY_PATH.exists() else 0
    parquet_mtime = PARQUET_CACHE.stat().st_mtime if PARQUET_CACHE.exists() else 0

    df = load_data(DATA_PATH, data_mtime, parquet_mtime)
    glossary_text = load_glossary_text(GLOSSARY_PATH, glossary_mtime)

    selections = build_filters(df)
    filtered = apply_filters(df, selections)

    tab_map, tab_glossary = st.tabs(["Map & Plants", "Glossary"])

    with tab_map:
        col1, col2, col3 = st.columns(3)
        col1.metric("Plants shown", f"{filtered['Plant name'].nunique():,}")
        col2.metric("Units shown", f"{len(filtered):,}")
        total_capacity = filtered["Capacity (MW)"].sum(skipna=True)
        col3.metric("Total capacity (MW)", f"{total_capacity:,.1f}")

        fig = make_map(filtered)
        if fig:
            st.plotly_chart(fig, use_container_width=True)

        st.subheader("Plant details for your selection")
        display_cols = [
            "Plant name",
            "Unit name",
            "Country",
            "Region",
            "City",
            "Fuel",
            "Capacity (MW)",
            "Status",
            "Technology",
            "Hydrogen capable?",
            "Start year",
            "Owner",
        ]
        missing_cols = [c for c in display_cols if c not in filtered.columns]
        if missing_cols:
            st.warning(f"Missing columns in dataset: {', '.join(missing_cols)}")
        else:
            st.dataframe(filtered[display_cols].reset_index(drop=True))

    with tab_glossary:
        st.subheader("Glossary")
        if glossary_text.strip():
            st.markdown(glossary_text)
        else:
            st.info("No glossary content found in glossary.md.")

        # Show supporting tech image at the bottom of the glossary tab.
        if TECH_IMAGE_PATH.exists():
            st.divider()
            st.image(str(TECH_IMAGE_PATH), use_column_width=True)

        # Show CHP visual beneath the glossary section if available.
        if CHP_IMAGE_PATH.exists():
            if not TECH_IMAGE_PATH.exists():
                st.divider()
            st.image(str(CHP_IMAGE_PATH), use_column_width=True)


if __name__ == "__main__":
    main()
