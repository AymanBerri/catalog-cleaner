"""
Streamlit dashboard for the catalog-cleaner results.

Run:
    pip install streamlit
    streamlit run app.py
"""

from pathlib import Path

import pandas as pd
import streamlit as st

# ---------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "output" / "resultats.parquet"

# ---------------------------------------------------------------------
# Page setup
# ---------------------------------------------------------------------
st.set_page_config(
    page_title="Catalog Cleaner",
    page_icon="🧹",
    layout="wide",
)

st.title("Catalog Cleaner — Results")
st.caption("525,034 sales lines · Task 1 (mis-categorization) + Task 2 (extraction)")

# ---------------------------------------------------------------------
# Load data (cached — Streamlit re-runs the script on every interaction)
# ---------------------------------------------------------------------
@st.cache_data(show_spinner="Loading results...")
def load_data() -> pd.DataFrame:
    return pd.read_parquet(RESULTS)


df = load_data()

# ---------------------------------------------------------------------
# Top metrics
# ---------------------------------------------------------------------
col1, col2, col3, col4, col5 = st.columns(5)

col1.metric("Total rows", f"{len(df):,}")

n_ok = (df["status"] == "ok").sum()
col2.metric("Task 1 — auto-resolved", f"{100 * n_ok / len(df):.1f}%")

n_review = df["status"].isin(["to_review_rule", "to_review_ml"]).sum()
col3.metric("Flagged for review", f"{n_review:,}", f"{100 * n_review / len(df):.1f}%")

dim_pct = 100 * df["dimension"].notna().mean()
col4.metric("Dimension found", f"{dim_pct:.1f}%")

col_pct = 100 * df["couleur"].apply(len).gt(0).mean()
col5.metric("Color found", f"{col_pct:.1f}%")

st.divider()

# ---------------------------------------------------------------------
# Charts — status breakdown + top colors
# ---------------------------------------------------------------------
left, right = st.columns(2)

with left:
    st.subheader("Task 1 — status breakdown")
    status_counts = df["status"].value_counts().sort_values(ascending=True)
    st.bar_chart(status_counts)

with right:
    st.subheader("Task 2 — top 20 colors")
    all_colors = [c for lst in df["couleur"] for c in lst]
    top_colors = pd.Series(all_colors).value_counts().head(20)
    st.bar_chart(top_colors)

st.divider()

# ---------------------------------------------------------------------
# Filters
# ---------------------------------------------------------------------
st.subheader("Filters")

f1, f2, f3, f4 = st.columns(4)

with f1:
    status_options = ["(all)"] + sorted(df["status"].unique().tolist())
    selected_status = st.selectbox("Status", status_options)

with f2:
    univers_options = ["(all)"] + sorted(df["Univers"].dropna().unique().tolist())
    selected_univers = st.selectbox("Univers", univers_options)

with f3:
    has_dim = st.checkbox("Has dimension")
    has_col = st.checkbox("Has color")
    has_mat = st.checkbox("Has material")

with f4:
    row_limit = st.slider("Max rows to show", 10, 500, 50, step=10)

# Apply filters
filtered = df.copy()
if selected_status != "(all)":
    filtered = filtered[filtered["status"] == selected_status]
if selected_univers != "(all)":
    filtered = filtered[filtered["Univers"] == selected_univers]
if has_dim:
    filtered = filtered[filtered["dimension"].notna()]
if has_col:
    filtered = filtered[filtered["couleur"].apply(len).gt(0)]
if has_mat:
    filtered = filtered[filtered["materiau"].apply(len).gt(0)]

st.caption(f"Filtered: {len(filtered):,} rows")

# ---------------------------------------------------------------------
# Title search
# ---------------------------------------------------------------------
st.subheader("Search a title")

query = st.text_input("Type any keyword (e.g., 'matelas', 'table basse', 'lit'):")

if query:
    search_mask = filtered["Libellé produit"].str.contains(query, case=False, na=False)
    filtered = filtered[search_mask]
    st.caption(f"Matches: {len(filtered):,}")

# ---------------------------------------------------------------------
# Display table
# ---------------------------------------------------------------------
display_cols = [
    "Libellé produit",
    "Nature",
    "nature_predicted",
    "status",
    "confidence",
    "dimension",
    "dimension_unit",
    "couleur",
    "materiau",
]

st.dataframe(
    filtered[display_cols].head(row_limit),
    use_container_width=True,
    hide_index=True,
)

# ---------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------
st.divider()
st.caption(
    "Task 2 findings: `docs/task2_findings.md` · "
    "Task 1 findings: `docs/task1_findings.md`"
)