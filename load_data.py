import sqlite3
import pandas as pd
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "immune_cells.db")
CSV_PATH = os.path.join(os.path.dirname(__file__), "data", "cell-count.csv")

CSV_COLUMNS = [
    "project", "subject_id", "indication", "age", "gender",
    "treatment", "response", "sample_id", "sample_type",
    "time_from_treatment_start",
    "b_cell", "cd8_t_cell", "cd4_t_cell", "nk_cell", "monocyte",
]

CELL_POPULATIONS = ["b_cell", "cd8_t_cell", "cd4_t_cell", "nk_cell", "monocyte"]


def create_schema(conn: sqlite3.Connection) -> None:
    """Create all three tables with FK constraints."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS patients (
            subject_id  TEXT PRIMARY KEY,
            gender      TEXT,
            age         INTEGER
        );

        CREATE TABLE IF NOT EXISTS samples (
            sample_id                   TEXT PRIMARY KEY,
            subject_id                  TEXT NOT NULL,
            project                     TEXT,
            indication                  TEXT,
            treatment                   TEXT,
            time_from_treatment_start   INTEGER,
            response                    TEXT,
            sample_type                 TEXT,
            FOREIGN KEY (subject_id) REFERENCES patients (subject_id)
        );

        CREATE TABLE IF NOT EXISTS cell_counts (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            sample_id   TEXT NOT NULL,
            population  TEXT NOT NULL,
            count       INTEGER,
            FOREIGN KEY (sample_id) REFERENCES samples (sample_id)
        );
    """)
    conn.commit()

def load_csv(conn: sqlite3.Connection, csv_path: str) -> None:
    """Read cell-count.csv (no header) and populate all three tables."""
    df = pd.read_csv(csv_path, header=None, names=CSV_COLUMNS)

    # Pulls patient information columns and drops duplicates.
    patients_df = (
        df[["subject_id", "gender", "age"]]
        .drop_duplicates(subset="subject_id")
        .reset_index(drop=True)
    )
    patients_df["age"] = pd.to_numeric(patients_df["age"], errors="coerce").astype(
        "Int64"
    )

    patients_df.to_sql(
        "patients",
        conn,
        if_exists="append",
        index=False,
        method="multi",
    )

    # Pulls sample-level columns 
    sample_cols = [
        "sample_id", "subject_id", "project", "indication",
        "treatment", "time_from_treatment_start", "response", "sample_type",
    ]
    samples_df = df[sample_cols].copy()
    samples_df["time_from_treatment_start"] = pd.to_numeric(
        samples_df["time_from_treatment_start"], errors="coerce"
    ).astype("Int64")

    samples_df.to_sql(
        "samples",
        conn,
        if_exists="append",
        index=False,
        method="multi",
    )

    # Pulls the 5 cell count colums and rotates them into population & count columns.
    cell_long = df[["sample_id"] + CELL_POPULATIONS].melt(
        id_vars="sample_id",
        value_vars=CELL_POPULATIONS,
        var_name="population",
        value_name="count",
    )
    cell_long["count"] = pd.to_numeric(cell_long["count"], errors="coerce").astype(
        "Int64"
    )

    cell_long[["sample_id", "population", "count"]].to_sql(
        "cell_counts",
        conn,
        if_exists="append",
        index=False,
        method="multi",
    )


if __name__ == "__main__":
    # Remove stale database if present
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")

    try:
        create_schema(conn)
        load_csv(conn, CSV_PATH)
    except Exception as exc:
        conn.rollback()
        raise
    finally:
        conn.close()