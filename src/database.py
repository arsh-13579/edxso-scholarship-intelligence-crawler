import sqlite3
import json
import os
import pandas as pd
from datetime import datetime, timezone
from src.config import Config

def init_db():
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(Config.DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS scholarships (
        scholarship_id TEXT PRIMARY KEY,
        name TEXT,
        provider TEXT,
        source_type TEXT,
        official_source_url TEXT,
        application_url TEXT,
        amount_benefit TEXT,
        eligibility_summary TEXT,
        academic_requirements TEXT,
        education_level TEXT,
        income_criteria TEXT,
        age_criteria TEXT,
        gender_criteria TEXT,
        category_criteria TEXT,
        domicile_requirements TEXT,
        institution_requirements TEXT,
        opening_date TEXT,
        closing_date TEXT,
        documents_required TEXT,
        selection_process TEXT,
        renewal_requirements TEXT,
        status TEXT,
        verification_label TEXT,
        confidence_score REAL,
        score_breakdown_json TEXT,
        evidence_json TEXT,
        raw_content_hash TEXT,
        last_verified TEXT,
        crawl_run_count INTEGER DEFAULT 1
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS change_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        scholarship_id TEXT,
        scholarship_name TEXT,
        field_changed TEXT,
        old_value TEXT,
        new_value TEXT,
        date_detected TEXT,
        official_source_url TEXT,
        evidence_quote TEXT,
        crawl_run INTEGER
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS crawl_runs (
        run_id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_number INTEGER,
        timestamp TEXT,
        discovered_count INTEGER,
        verified_count INTEGER,
        changes_detected INTEGER,
        new_added INTEGER
    )
    """)

    conn.commit()
    conn.close()

def upsert_scholarship_with_change_detection(record: dict, run_number: int) -> list[dict]:
    conn = sqlite3.connect(Config.DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    existing = cursor.execute(
        "SELECT * FROM scholarships WHERE scholarship_id = ?",
        (record["scholarship_id"],)
    ).fetchone()

    now_str = datetime.now(timezone.utc).strftime("%d %b %Y %H:%M UTC")
    detected_changes = []

    if existing:
        existing_dict = dict(existing)
        tracked_fields = [
            "closing_date", "opening_date", "amount_benefit",
            "income_criteria", "academic_requirements", "status", "verification_label"
        ]
        evidence_map = json.loads(record.get("evidence_json", "{}"))

        for field in tracked_fields:
            old_val = str(existing_dict.get(field, "Not specified")).strip()
            new_val = str(record.get(field, "Not specified")).strip()
            if old_val != new_val:
                ev_quote = evidence_map.get(field, evidence_map.get("closing_date", "Updated official notification on primary portal."))
                cursor.execute("""
                INSERT INTO change_history (
                    scholarship_id, scholarship_name, field_changed,
                    old_value, new_value, date_detected,
                    official_source_url, evidence_quote, crawl_run
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    record["scholarship_id"], record["name"], field,
                    old_val, new_val, now_str,
                    record["official_source_url"], ev_quote, run_number
                ))
                detected_changes.append({
                    "scholarship_name": record["name"],
                    "field": field,
                    "old": old_val,
                    "new": new_val,
                    "evidence": ev_quote
                })

        record["crawl_run_count"] = int(existing_dict.get("crawl_run_count", 1)) + 1
    else:
        record["crawl_run_count"] = 1

    record["last_verified"] = now_str

    cursor.execute("""
    INSERT INTO scholarships (
        scholarship_id, name, provider, source_type, official_source_url, application_url,
        amount_benefit, eligibility_summary, academic_requirements, education_level,
        income_criteria, age_criteria, gender_criteria, category_criteria,
        domicile_requirements, institution_requirements, opening_date, closing_date,
        documents_required, selection_process, renewal_requirements,
        status, verification_label, confidence_score, score_breakdown_json,
        evidence_json, raw_content_hash, last_verified, crawl_run_count
    ) VALUES (
        :scholarship_id, :name, :provider, :source_type, :official_source_url, :application_url,
        :amount_benefit, :eligibility_summary, :academic_requirements, :education_level,
        :income_criteria, :age_criteria, :gender_criteria, :category_criteria,
        :domicile_requirements, :institution_requirements, :opening_date, :closing_date,
        :documents_required, :selection_process, :renewal_requirements,
        :status, :verification_label, :confidence_score, :score_breakdown_json,
        :evidence_json, :raw_content_hash, :last_verified, :crawl_run_count
    )
    ON CONFLICT(scholarship_id) DO UPDATE SET
        amount_benefit=excluded.amount_benefit,
        eligibility_summary=excluded.eligibility_summary,
        academic_requirements=excluded.academic_requirements,
        income_criteria=excluded.income_criteria,
        opening_date=excluded.opening_date,
        closing_date=excluded.closing_date,
        status=excluded.status,
        verification_label=excluded.verification_label,
        confidence_score=excluded.confidence_score,
        score_breakdown_json=excluded.score_breakdown_json,
        evidence_json=excluded.evidence_json,
        raw_content_hash=excluded.raw_content_hash,
        last_verified=excluded.last_verified,
        crawl_run_count=excluded.crawl_run_count
    """, record)

    conn.commit()
    conn.close()
    return detected_changes

def log_crawl_run(run_number: int, discovered: int, verified: int, changes: int, new_added: int):
    conn = sqlite3.connect(Config.DB_PATH)
    now_str = datetime.now(timezone.utc).strftime("%d %b %Y %H:%M UTC")
    conn.execute("""
    INSERT INTO crawl_runs (run_number, timestamp, discovered_count, verified_count, changes_detected, new_added)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (run_number, now_str, discovered, verified, changes, new_added))
    conn.commit()
    conn.close()

def export_csv_reports():
    conn = sqlite3.connect(Config.DB_PATH)
    df_sch = pd.read_sql_query("SELECT * FROM scholarships ORDER BY confidence_score DESC", conn)
    df_chg = pd.read_sql_query("SELECT * FROM change_history ORDER BY id DESC", conn)
    conn.close()

    df_sch.to_csv("data/scholarships_repository.csv", index=False)
    df_chg.to_csv("data/change_detection_log.csv", index=False)
