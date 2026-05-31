"""
For melanoma / miraclib / PBMC samples, produces:
  • outputs/plots/boxplot_response.png  — side-by-side boxplots per population
  • outputs/tables/stats_results.csv    — Mann-Whitney U results per population
"""

import os
import sqlite3

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from scipy import stats

# Paths
ROOT     = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH  = os.path.join(ROOT, "immune_cells.db")
FREQ_CSV = os.path.join(ROOT, "outputs", "tables", "cell_freq_summary.csv")
PLOT_DIR = os.path.join(ROOT, "outputs", "plots")
TBL_DIR  = os.path.join(ROOT, "outputs", "tables")
PLOT_OUT = os.path.join(PLOT_DIR, "boxplot_response.png")
STAT_OUT = os.path.join(TBL_DIR, "stats_results.csv")

os.makedirs(PLOT_DIR, exist_ok=True)
os.makedirs(TBL_DIR,  exist_ok=True)

# Filter constants
INDICATION  = "melanoma"
TREATMENT   = "miraclib"
SAMPLE_TYPE = "PBMC"

POPULATIONS = ["b_cell", "cd8_t_cell", "cd4_t_cell", "nk_cell", "monocyte"]

RESPONSE_YES = "yes"
RESPONSE_NO  = "no"
PALETTE      = {RESPONSE_YES: "#2ecc71", RESPONSE_NO: "#e74c3c"}


# Build analysis dataframe 
def load_data() -> pd.DataFrame:
    """
    Joins samples + cell_counts (filtered) with the pre-computed frequency
    summary to attach the 'percentage' column.
    """
    conn = sqlite3.connect(DB_PATH)
    query = """
        SELECT
            s.sample_id   AS sample,
            s.response    AS response,
            cc.population AS population,
            cc.count      AS count
        FROM samples s
        JOIN cell_counts cc ON s.sample_id = cc.sample_id
        WHERE s.indication  = :indication
          AND s.treatment   = :treatment
          AND s.sample_type = :sample_type
    """
    db_df = pd.read_sql_query(
        query, conn,
        params={"indication": INDICATION, "treatment": TREATMENT,
                "sample_type": SAMPLE_TYPE},
    )
    conn.close()

    if db_df.empty:
        raise ValueError(
            f"No rows returned for indication={INDICATION!r}, "
            f"treatment={TREATMENT!r}, sample_type={SAMPLE_TYPE!r}.\n"
            "Check that the DB contains matching records."
        )

    # Merge pre-computed percentages from part2
    freq = pd.read_csv(FREQ_CSV)[["sample", "population", "percentage"]]
    df = db_df.merge(freq, on=["sample", "population"], how="left")

    # Normalise response labels to lower-case for reliable comparison
    df["response"] = df["response"].str.strip().str.lower()
    return df


# Boxplot 
def make_boxplot(df: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 5, figsize=(18, 5), sharey=False)
    fig.suptitle(
        f"Cell population frequency by response\n"
        f"({INDICATION} · {TREATMENT} · {SAMPLE_TYPE})",
        fontsize=13, fontweight="bold", y=1.02,
    )

    for ax, pop in zip(axes, POPULATIONS):
        pop_df = df[df["population"] == pop].copy()

        # Ensure both groups present
        present = set(pop_df["response"].unique())
        order = [r for r in [RESPONSE_YES, RESPONSE_NO] if r in present]

        sns.boxplot(
            data=pop_df,
            x="response", y="percentage",
            hue="response",
            order=order,
            hue_order=order,
            palette=PALETTE,
            width=0.5,
            linewidth=1.2,
            fliersize=0,
            legend=False,
            ax=ax,
        )
        sns.stripplot(
            data=pop_df,
            x="response", y="percentage",
            order=order,
            color="black",
            alpha=0.6,
            jitter=True,
            size=5,
            ax=ax,
        )

        ax.set_title(pop, fontsize=11, fontweight="bold")
        ax.set_xlabel("Response", fontsize=9)
        ax.set_ylabel("Percentage (%)", fontsize=9)
        ax.tick_params(labelsize=8)

    plt.tight_layout()
    plt.savefig(PLOT_OUT, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved plot: {PLOT_OUT}")


# Mann-Whitney U tests 
def run_stats(df: pd.DataFrame) -> pd.DataFrame:
    records = []
    for pop in POPULATIONS:
        pop_df = df[df["population"] == pop]
        yes_vals = pop_df.loc[pop_df["response"] == RESPONSE_YES, "percentage"].dropna()
        no_vals  = pop_df.loc[pop_df["response"] == RESPONSE_NO,  "percentage"].dropna()

        if len(yes_vals) < 2 or len(no_vals) < 2:
            # Not enough data for a meaningful test
            u_stat, p_val = float("nan"), float("nan")
        else:
            u_stat, p_val = stats.mannwhitneyu(
                yes_vals, no_vals, alternative="two-sided"
            )

        records.append({
            "population":        pop,
            "n_responders":      len(yes_vals),
            "n_non_responders":  len(no_vals),
            "median_responders": round(yes_vals.median(), 4) if len(yes_vals) else float("nan"),
            "median_non_responders": round(no_vals.median(), 4) if len(no_vals) else float("nan"),
            "U_statistic":       round(u_stat, 4) if not pd.isna(u_stat) else float("nan"),
            "p_value":           round(p_val,  6) if not pd.isna(p_val)  else float("nan"),
            "significant":       bool(p_val < 0.05) if not pd.isna(p_val) else False,
        })

    return pd.DataFrame(records)


# Plain-English summary 
def print_summary(results: pd.DataFrame) -> None:
    sig = results[results["significant"] == True]
    if sig.empty:
        print("\nNo significant differences found.")
    else:
        parts = [f"{row.population} (p={row.p_value:.3f})"
                 for _, row in sig.iterrows()]
        print(f"\nSignificant difference found in: {', '.join(parts)}")


# Main 
def main() -> None:
    df = load_data()
    print(f"Filtered dataset: {len(df)} rows, "
          f"{df['sample'].nunique()} samples, "
          f"{df['response'].value_counts().to_dict()}")

    make_boxplot(df)

    results = run_stats(df)
    print("\nStatistical results:")
    print(results.to_string(index=False))

    results.to_csv(STAT_OUT, index=False)
    print(f"\nSaved stats: {STAT_OUT}")

    print_summary(results)


if __name__ == "__main__":
    main()