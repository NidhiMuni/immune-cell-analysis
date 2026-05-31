# immune-cell-analysis

Analysis pipeline and dashboard for exploring immune cell population frequencies across clinical trial samples, with a focus on predicting treatment response to miraclib in melanoma patients.

---

## How to Run

```bash
pip install -r requirements.txt
make load        
make analysis    
make dashboard   
```

Open dashboard at http://localhost:8501
All outputs are written to `outputs/tables/` and `outputs/plots/`.

---

## Database Schema

```
patients
  subject_id  TEXT  PRIMARY KEY
  gender      TEXT
  age         INTEGER

samples
  sample_id                  TEXT  PRIMARY KEY
  subject_id                 TEXT  FK → patients.subject_id
  project                    TEXT
  indication                 TEXT
  treatment                  TEXT
  time_from_treatment_start  INTEGER
  response                   TEXT
  sample_type                TEXT

cell_counts
  id          INTEGER  PRIMARY KEY AUTOINCREMENT
  sample_id   TEXT     FK → samples.sample_id
  population  TEXT
  count       INTEGER
```

### Design rationale
The raw CSV is normalized into three tables — one per real-world entity: the person, the sample, and the measurement. Patient demographics live on `patients` so they aren't repeated across every timepoint; clinical metadata lives on `samples` since it describes a collection event, not a person. Cell counts are stored in long format (one row per population per sample) rather than as five columns, so adding a new population requires no schema change and population-level queries need no unpivoting.


### How this scales
Adding projects or samples requires no schema changes — `project` is just a filter on `samples`, and `cell_counts` grows linearly at 5 rows per sample with indexes keeping queries fast. For very large datasets the schema can work with more powerful database architectures with minimal changes.

---

## Code Structure

```
├── load_data.py                  # build immune_cells.db from CSV
├── pipeline/
│   ├── initial_analysis.py         # per-sample cell frequencies → cell_freq_summary.csv
│   ├── statistical_analysis.py            # responder analysis → boxplot + stats_results.csv
│   └── data_subset_analysis.py           # baseline cohort breakdown → 3 summary CSVs
├── dashboard/
│   └── app.py                    # Streamlit dashboard
├── data/
│   └── cell-count.csv            # raw input (not committed)
├── outputs/
│   ├── plots/                    # generated figures
│   └── tables/                   # generated CSVs
├── Makefile                      
└── requirements.txt
```

### Why it's structured this way

**Separation of concerns.** `load_data.py` owns the database; `analysis/` scripts own the outputs; the dashboard only reads. No script writes to the database except `load_data.py`, so the pipeline is safe to re-run in any order after the initial load.

**Scripts over notebooks.** Each analysis step is a plain Python file with a `main()` function. This makes them easy to run in CI, call from the Makefile, and read without a Jupyter environment.

**Analysis feeds the dashboard.** The dashboard reads CSVs that the analysis scripts produce rather than recomputing everything on each page load. Expensive computations (Mann-Whitney tests, melt/pivot operations) happen once at analysis time; the dashboard stays fast and stateless.

**Long-format data throughout.** The database stores cell counts in long format, and the frequency CSV follows the same convention. This makes filtering and grouping by population consistent whether you're writing SQL or pandas.

---
