"""
Baseline subset analysis: melanoma / miraclib / PBMC / time_from_treatment_start=0
Outputs:
  outputs/tables/part4_by_project.csv
  outputs/tables/part4_by_response.csv
  outputs/tables/part4_by_gender.csv
"""

import os
import sqlite3
import pandas as pd

# Paths 
ROOT    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(ROOT, "immune_cells.db")
OUT_DIR = os.path.join(ROOT, "outputs", "tables")
os.makedirs(OUT_DIR, exist_ok=True)

# Filter constants (mirrors part3_stats.py + baseline time point)
INDICATION   = "melanoma"
TREATMENT    = "miraclib"
SAMPLE_TYPE  = "PBMC"
TIME_POINT   = 0


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# Baseline filter 

def load_baseline(conn: sqlite3.Connection) -> pd.DataFrame:
    query = """
        SELECT
            s.sample_id,
            s.subject_id,
            s.project,
            s.response,
            s.time_from_treatment_start
        FROM samples s
        WHERE s.indication                = :indication
          AND s.treatment                 = :treatment
          AND s.sample_type               = :sample_type
          AND s.time_from_treatment_start = :time_point
    """
    df = pd.read_sql_query(
        query, conn,
        params={
            "indication":  INDICATION,
            "treatment":   TREATMENT,
            "sample_type": SAMPLE_TYPE,
            "time_point":  TIME_POINT,
        },
    )
    print(f"1. Baseline samples found: {len(df)}")
    return df


# Count by project 

def count_by_project(baseline_df: pd.DataFrame) -> pd.DataFrame:
    result = (
        baseline_df.groupby("project")["sample_id"]
        .nunique()
        .reset_index()
        .rename(columns={"sample_id": "sample_count"})
        .sort_values("project")
    )
    out = os.path.join(OUT_DIR, "part4_by_project.csv")
    result.to_csv(out, index=False)
    print(f"\n2. By project (saved → {os.path.basename(out)}):")
    print(result.to_string(index=False))
    return result


# Count by response

def count_by_response(baseline_df: pd.DataFrame) -> pd.DataFrame:
    result = (
        baseline_df.groupby("response")["subject_id"]
        .nunique()
        .reset_index()
        .rename(columns={"subject_id": "subject_count"})
        .sort_values("response")
    )
    out = os.path.join(OUT_DIR, "part4_by_response.csv")
    result.to_csv(out, index=False)
    print(f"\n3. By response (saved → {os.path.basename(out)}):")
    print(result.to_string(index=False))
    return result


# Count by gender 

def count_by_gender(baseline_df: pd.DataFrame, conn: sqlite3.Connection) -> pd.DataFrame:
    # Pull gender for each subject from the patients table
    subject_ids = tuple(baseline_df["subject_id"].unique())
    placeholders = ",".join("?" * len(subject_ids))
    patients = pd.read_sql_query(
        f"SELECT subject_id, gender FROM patients WHERE subject_id IN ({placeholders})",
        conn,
        params=subject_ids,
    )
    merged = baseline_df.merge(patients, on="subject_id", how="left")
    result = (
        merged.groupby("gender")["subject_id"]
        .nunique()
        .reset_index()
        .rename(columns={"subject_id": "subject_count"})
        .sort_values("gender")
    )
    out = os.path.join(OUT_DIR, "part4_by_gender.csv")
    result.to_csv(out, index=False)
    print(f"\n4. By gender (saved → {os.path.basename(out)}):")
    print(result.to_string(index=False))
    return result


# Plain-English summary 

def print_summary(
    baseline_df: pd.DataFrame,
    by_project: pd.DataFrame,
    by_response: pd.DataFrame,
    by_gender: pd.DataFrame,
) -> None:
    proj_parts = [
        f"{row['project']}={row['sample_count']}"
        for _, row in by_project.iterrows()
    ]

    resp_dict  = dict(zip(by_response["response"], by_response["subject_count"]))
    gender_dict = dict(zip(by_gender["gender"], by_gender["subject_count"]))

    responders     = resp_dict.get("yes", 0)
    non_responders = resp_dict.get("no",  0)
    male           = gender_dict.get("M", 0)
    female         = gender_dict.get("F", 0)

    print("\n" + "=" * 52)
    print(
        f"Baseline melanoma PBMC miraclib samples: {len(baseline_df)}\n"
        f"By project: {', '.join(proj_parts)}\n"
        f"Responders: {responders} | Non-responders: {non_responders}\n"
        f"Male: {male} | Female: {female}"
    )
    print("=" * 52)


# Main

def main() -> None:
    conn = get_connection()
    try:
        baseline_df  = load_baseline(conn)
        by_project   = count_by_project(baseline_df)
        by_response  = count_by_response(baseline_df)
        by_gender    = count_by_gender(baseline_df, conn)
        print_summary(baseline_df, by_project, by_response, by_gender)
    finally:
        conn.close()


if __name__ == "__main__":
    main()