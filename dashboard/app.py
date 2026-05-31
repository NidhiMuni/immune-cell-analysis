import os
import sqlite3
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Immune Cell Analysis Dashboard", layout="wide")

ROOT    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(ROOT, "immune_cells.db")

@st.cache_resource
def get_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def qdf(sql, params=()):
    return pd.read_sql_query(sql, get_conn(), params=params)

def csv(name):
    return pd.read_csv(os.path.join(ROOT, "outputs", "tables", name))

tab1, tab2, tab3, tab4 = st.tabs([
    "Data Overview", "Cell Frequencies", "Responder Analysis", "Baseline Subset"
])

# Tab 1 
with tab1:
    st.header("Data Overview")

    c1, c2, c3 = st.columns(3)
    c1.metric("Patients", qdf("SELECT COUNT(*) AS n FROM patients").iloc[0,0])
    c2.metric("Samples",  qdf("SELECT COUNT(*) AS n FROM samples").iloc[0,0])
    c3.metric("Cell Count Records", qdf("SELECT COUNT(*) AS n FROM cell_counts").iloc[0,0])

    samples = qdf("""
        SELECT s.sample_id, s.subject_id, p.gender, p.age, s.indication,
               s.treatment, s.response, s.sample_type, s.time_from_treatment_start
        FROM samples s JOIN patients p ON s.subject_id = p.subject_id
    """)

    with st.sidebar:
        ind = st.multiselect("Indication",   sorted(samples.indication.unique()),   default=sorted(samples.indication.unique()))
        trt = st.multiselect("Treatment",    sorted(samples.treatment.unique()),    default=sorted(samples.treatment.unique()))
        sty = st.multiselect("Sample Type",  sorted(samples.sample_type.unique()), default=sorted(samples.sample_type.unique()))

    mask = samples.indication.isin(ind) & samples.treatment.isin(trt) & samples.sample_type.isin(sty)
    st.dataframe(samples[mask], use_container_width=True)

# Tab 2 
with tab2:
    st.header("Cell Population Frequencies")

    freq = csv("cell_freq_summary.csv")
    search = st.text_input("Filter by sample ID")
    df = freq[freq["sample"].str.contains(search, case=False)] if search else freq
    st.dataframe(df, use_container_width=True)

    st.subheader("Average % per population")
    st.bar_chart(freq.groupby("population")["percentage"].mean())

# Tab 3 
with tab3:
    st.header("Responder vs Non-Responder Analysis")
    st.caption("melanoma · miraclib · PBMC only")

    boxplot = os.path.join(ROOT, "outputs", "plots", "boxplot_response.png")
    if os.path.exists(boxplot):
        st.image(boxplot, use_column_width=True)

    stats = csv("stats_results.csv")
    st.dataframe(stats, use_container_width=True)

    for _, row in stats.iterrows():
        msg = f"**{row.population}**: p = {row.p_value:.3f}"
        if row.significant:
            st.success(f"✓ {msg} — significant")
        else:
            st.info(f"– {msg} — not significant")

# Tab 4 
with tab4:
    st.header("Baseline Subset Analysis")

    by_proj = csv("part4_by_project.csv")
    by_resp = csv("part4_by_response.csv")
    by_gend = csv("part4_by_gender.csv")

    c1, c2, c3 = st.columns(3)
    for col, df, idx, val in [
        (c1, by_proj, "project",  "sample_count"),
        (c2, by_resp, "response", "subject_count"),
        (c3, by_gend, "gender",   "subject_count"),
    ]:
        with col:
            st.dataframe(df, use_container_width=True, hide_index=True)
            st.bar_chart(df.set_index(idx)[val])

    with st.expander("View raw baseline samples"):
        st.dataframe(qdf("""
            SELECT s.sample_id, s.subject_id, p.gender, s.project,
                   s.response, s.time_from_treatment_start
            FROM samples s JOIN patients p ON s.subject_id = p.subject_id
            WHERE s.indication='melanoma' AND s.treatment='miraclib'
              AND s.sample_type='PBMC' AND s.time_from_treatment_start=0
        """), use_container_width=True)