"""
Computes per-sample cell population frequencies from immune_cells.db and 
saves a summary CSV to outputs/tables/cell_freq_summary.csv.
"""

import os
import sqlite3
import pandas as pd

ROOT    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(ROOT, "immune_cells.db")
OUT_DIR = os.path.join(ROOT, "outputs", "tables")
OUT_CSV = os.path.join(OUT_DIR, "cell_freq_summary.csv")

os.makedirs(OUT_DIR, exist_ok=True)


def main() -> None:
    # Load every (sample_id, population, count) row 
    conn = sqlite3.connect(DB_PATH)
    query = """
        SELECT
            s.sample_id   AS sample,
            cc.population AS population,
            cc.count      AS count
        FROM samples s
        JOIN cell_counts cc ON s.sample_id = cc.sample_id
        ORDER BY s.sample_id, cc.population
    """
    df = pd.read_sql_query(query, conn)
    conn.close()

    # Per-sample total count 
    totals = df.groupby("sample")["count"].sum().rename("total_count")
    df = df.join(totals, on="sample")

    # Percentage per population per sample 
    df["percentage"] = (df["count"] / df["total_count"]) * 100

    # Reorder columns and save
    df = df[["sample", "total_count", "population", "count", "percentage"]]
    df.to_csv(OUT_CSV, index=False)
    


if __name__ == "__main__":
    main()