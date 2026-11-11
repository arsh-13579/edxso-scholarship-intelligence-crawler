import streamlit as st
import pandas as pd
import sqlite3
import json
import os
from src.config import Config
from main import execute_crawler_run

st.set_page_config(page_title="Atlas Funding — Scholarship Intelligence Engine", layout="wide")

st.title("🎓 Atlas Funding — Autonomous Scholarship Intelligence Crawler")
st.caption("Continuous Discovery • Primary-Source Verification • Explainable Confidence Scoring • Anti-Hallucination Evidence Tracing • Change Detection")

if not os.path.exists(Config.DB_PATH):
    execute_crawler_run(1)
    execute_crawler_run(2)

# Top Action Bar for Live Re-Crawling
col_btn1, col_btn2, col_spacer = st.columns([2, 2, 6])
with col_btn1:
    if st.button("🔄 Trigger Crawl Run #1 (Baseline Discovery)"):
        execute_crawler_run(1)
        st.rerun()
with col_btn2:
    if st.button("⚡ Trigger Crawl Run #2 (Simulate Change Detection)"):
        execute_crawler_run(2)
        st.rerun()

conn = sqlite3.connect(Config.DB_PATH)
df = pd.read_sql_query("SELECT * FROM scholarships ORDER BY confidence_score DESC", conn)
changes_df = pd.read_sql_query("SELECT * FROM change_history ORDER BY id DESC", conn)
runs_df = pd.read_sql_query("SELECT * FROM crawl_runs ORDER BY run_id DESC", conn)
conn.close()

# Section 10 Metrics Bar
m1, m2, m3, m4, m5, m6, m7 = st.columns(7)
m1.metric("Total Discovered", len(df))
m2.metric("Verified (≥95%)", len(df[df["verification_label"] == "VERIFIED"]))
m3.metric("Review Required", len(df[df["verification_label"] == "REVIEW_REQUIRED"]))
m4.metric("Active / Expiring Soon", len(df[df["status"].isin(["ACTIVE", "EXPIRING_SOON"])]))
m5.metric("Expired / Discontinued", len(df[df["status"].isin(["EXPIRED", "NO_LONGER_VERIFIABLE"])]))
m6.metric("Changes Detected", len(changes_df))
m7.metric("Avg Confidence", f"{df['confidence_score'].mean():.1f}%")

st.divider()

tab1, tab2, tab3 = st.tabs([
    "🔍 Searchable Scholarship Repository & Deep Inspector",
    "⚡ Change Detection & Audit History",
    "🤖 Crawler Run Logs & Source Distribution"
])

with tab1:
    f_col1, f_col2, f_col3 = st.columns([4, 3, 3])
    search_q = f_col1.text_input("🔎 Search by Scholarship Name, Provider, Course, or Keyword", "")
    source_filter = f_col2.multiselect(
        "Filter by Source Type",
        options=sorted(df["source_type"].unique()),
        default=sorted(df["source_type"].unique())
    )
    status_filter = f_col3.multiselect(
        "Filter by Lifecycle Status",
        options=sorted(df["status"].unique()),
        default=sorted(df["status"].unique())
    )

    filtered_df = df[
        df["source_type"].isin(source_filter) &
        df["status"].isin(status_filter)
    ]
    if search_q:
        mask = (
            filtered_df["name"].str.contains(search_q, case=False, na=False) |
            filtered_df["provider"].str.contains(search_q, case=False, na=False) |
            filtered_df["eligibility_summary"].str.contains(search_q, case=False, na=False)
        )
        filtered_df = filtered_df[mask]

    st.dataframe(
        filtered_df[[
            "scholarship_id", "name", "provider", "source_type", "amount_benefit",
            "closing_date", "status", "verification_label", "confidence_score", "last_verified"
        ]].rename(columns={
            "scholarship_id": "ID", "name": "Scholarship", "provider": "Provider",
            "source_type": "Source Type", "amount_benefit": "Amount / Benefit",
            "closing_date": "Deadline", "status": "Status",
            "verification_label": "Verification", "confidence_score": "Confidence (%)",
            "last_verified": "Last Verified"
        }),
        use_container_width=True
    )

    st.subheader("📋 Deep Scholarship Inspector (Click Any Scholarship Below)")
    selected_name = st.selectbox("Select a Scholarship to Inspect Evidence, Schema & Score Breakdown:", filtered_df["name"].tolist())

    if selected_name:
        row = filtered_df[filtered_df["name"] == selected_name].iloc[0]
        score_breakdown = json.loads(row["score_breakdown_json"])
        evidence_map = json.loads(row["evidence_json"])

        c1, c2 = st.columns([3, 2])
        with c1:
            st.markdown(f"### {row['name']}")
            st.markdown(f"**Provider:** {row['provider']} (`{row['source_type']}`)")
            st.markdown(f"**🔗 Official Primary Source:** [{row['official_source_url']}]({row['official_source_url']})")
            st.markdown(f"**📝 Official Application Link:** [{row['application_url']}]({row['application_url']})")
            st.markdown(f"**💰 Scholarship Amount / Benefit:** {row['amount_benefit']}")
            st.markdown(f"**📅 Opening Date:** `{row['opening_date']}` | **Closing Date (Deadline):** `{row['closing_date']}`")

            st.markdown("#### Structured Eligibility & Atlas Schema Fields")
            schema_table = pd.DataFrame([
                {"Field": "Eligibility Summary", "Extracted Value (Anti-Hallucination Enforced)": row["eligibility_summary"]},
                {"Field": "Education Level / Course", "Extracted Value (Anti-Hallucination Enforced)": row["education_level"]},
                {"Field": "Academic Requirements", "Extracted Value (Anti-Hallucination Enforced)": row["academic_requirements"]},
                {"Field": "Income Criteria", "Extracted Value (Anti-Hallucination Enforced)": row["income_criteria"]},
                {"Field": "Age Criteria", "Extracted Value (Anti-Hallucination Enforced)": row["age_criteria"]},
                {"Field": "Gender Criteria", "Extracted Value (Anti-Hallucination Enforced)": row["gender_criteria"]},
                {"Field": "Category Criteria", "Extracted Value (Anti-Hallucination Enforced)": row["category_criteria"]},
                {"Field": "Domicile / State", "Extracted Value (Anti-Hallucination Enforced)": row["domicile_requirements"]},
                {"Field": "Institution Requirements", "Extracted Value (Anti-Hallucination Enforced)": row["institution_requirements"]},
                {"Field": "Documents Required", "Extracted Value (Anti-Hallucination Enforced)": row["documents_required"]},
                {"Field": "Selection Process", "Extracted Value (Anti-Hallucination Enforced)": row["selection_process"]},
                {"Field": "Renewal Requirements", "Extracted Value (Anti-Hallucination Enforced)": row["renewal_requirements"]}
            ])
            st.table(schema_table)

        with c2:
            st.markdown("#### 🛡️ Verification & Confidence Engine")
            st.metric("Confidence Score", f"{row['confidence_score']}%", delta=row["verification_label"])
            st.markdown(f"**Lifecycle Status:** `{row['status']}` | **Last Verified:** `{row['last_verified']}`")
            st.markdown(f"**Content Hash (SHA-256):** `{row['raw_content_hash'][:24]}...`")

            st.markdown("##### Why This Score? (Deterministic Breakdown)")
            for criterion, explanation in score_breakdown.items():
                st.write(f"- **{criterion}:** {explanation}")

            st.markdown("##### 🔎 Verbatim Source Evidence Trace (`DB ➔ Official Source ➔ Quote`)")
            for field_k, quote_v in evidence_map.items():
                st.info(f"**{field_k.upper()}:** '{quote_v}'")

            sch_changes = changes_df[changes_df["scholarship_id"] == row["scholarship_id"]]
            st.markdown("##### 🕒 Change History for This Scholarship")
            if len(sch_changes) > 0:
                st.dataframe(sch_changes[["field_changed", "old_value", "new_value", "date_detected", "evidence_quote"]], use_container_width=True)
            else:
                st.caption("No field mutations detected across crawl runs for this record.")

with tab2:
    st.subheader("⚡ Multi-Run Change Detection Audit Log")
    st.markdown("Demonstrates non-destructive updates: retains `Old Value`, `New Value`, `Date Detected`, `Official Source`, and `Verbatim Evidence`.")
    st.dataframe(changes_df, use_container_width=True)

with tab3:
    st.subheader("🤖 Autonomous Crawler Execution History")
    st.dataframe(runs_df, use_container_width=True)
    st.subheader("📊 Repository Breakdown by Source Category")
    st.bar_chart(df["source_type"].value_counts())