# Sales Analytics Dashboard

End-to-end analytical product: from raw CSV files to a deployed web application.

**[▶ Live Demo](https://sales-dashboard-analytics.streamlit.app)** &nbsp;|&nbsp; Python &nbsp;|&nbsp; Streamlit &nbsp;|&nbsp; Pandas &nbsp;|&nbsp; Plotly &nbsp;|&nbsp; SQLite

---

## About

Interactive dashboard analyzing **1,330 sales transactions** from 2010–2017 across 45 countries.
The goal is **actionable insights** for business decisions:
automatic anomaly detection, portfolio Pareto analysis, and SLA monitoring for operational efficiency.

![Overview](screenshots/01_overview_main.png)

---

---

## Tech Stack

| | | | | |
|---|---|---|---|---|
| ![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white) | ![Streamlit](https://img.shields.io/badge/Streamlit-1.35-FF4B4B?logo=streamlit&logoColor=white) | ![Pandas](https://img.shields.io/badge/Pandas-2.2.2-150458?logo=pandas&logoColor=white) | ![Plotly](https://img.shields.io/badge/Plotly-5.22-3F4F75?logo=plotly&logoColor=white) | ![SQLite](https://img.shields.io/badge/SQLite-3-003B57?logo=sqlite&logoColor=white) |

*Also used:* `streamlit-option-menu>=0.3.6` (for building custom intuitive navigation between analytical pages).

---

---

## Analytical Pages

### Overview — Executive Summary
![Overview Trend](screenshots/02_overview_trend_yoy.png)

KPIs with YoY delta, automatic alert on declining trends, 6-month moving average to smooth seasonal noise. YoY metrics are calculated on the full dataset — delta remains stable regardless of active filters.

---

### Product — Portfolio Analysis
![Product](screenshots/03_product_analysis.png)

Weighted margin `SUM(profit)/SUM(revenue)` instead of `AVG(margin)` — a methodologically correct aggregation that accounts for the size of each deal.

![Pareto](screenshots/04_product_pareto.png)

**Pareto result:** 7 out of 12 categories (58%) generate 80% of profit. Automatic identification of the core portfolio and the "long tail".

---

### Geography — Geographic Distribution
![Geography](screenshots/05_geography_map.png)

Choropleth map with sub-regional breakdown. **88.5% of revenue from Europe** — critical concentration that requires diversification. 82 records without `country_code` are displayed explicitly as a data gap.

---

### Operations — Operational Efficiency
![Operations](screenshots/06_operations_sla.png)

Automatic SLA check: Critical orders are processed in 23.7 days, Low — 25.1 days. The difference is only 1.4 days (~6%) — **the priority system is effectively not working**. Seasonality heatmap identifies peak load periods by category and month.

---

### Data Dictionary — Data Documentation
![Data Dictionary](screenshots/07_data_dictionary.png)

Description of all 22 fields, data quality after cleaning (0 missing values, 0 duplicates), and methodological decisions. Live documentation — updates automatically with the data.

---

### Interactive Filters

| All data · $1704.6M · 1,330 orders | Filter 2015–2017 · $556.1M · 441 orders |
|:---:|:---:|
| ![Before](screenshots/08_filters_before.png) | ![After](screenshots/09_filters_after.png) |

Filters by year, channel, category, and region. State is preserved in `session_state` — does not reset on UI interaction.

---

## Key Insights

- **$1.7B** total revenue over 8 years · portfolio margin **29.4%**
- **88.5%** of revenue from Europe — critical geographic dependency
- **Clothes 67.2%** margin vs **Meat 13.6%** — a spread of 53.6 p.p. within the same portfolio
- **7 out of 12** categories generate 80% of profit (Pareto principle confirmed)
- **SLA paradox:** difference between Critical and Low priority processing — only 1.4 days

---

## Architecture

```text
sales-dashboard/
├── main.py                    # entry point, routing
├── app/
│   ├── components/            # reusable UI (filters, header)
│   ├── pages/                 # 5 analytical views
│   └── services/
│       ├── data_loader.py     # ETL pipeline: extract → transform → load
│       ├── database.py        # SQLite layer
│       └── metrics.py         # business metrics (pandas + SQL)
├── data/
│   ├── raw/                   # immutable source files
│   └── processed/             # generated SQLite DB
└── tests/                     # pytest unit + integration tests
```

**Key decisions:**
- `@st.cache_data` — ETL pipeline runs once at startup
- pandas for dynamic KPIs + SQL for static aggregations
- `df.copy()` everywhere — protection against original data mutation
- Defensive programming — edge case handling at every level

---

## Data Quality

| Rows | Missing Values | Duplicates | Columns |
|:---:|:---:|:---:|:---:|
| 1,330 | 0 | 0 | 22 |

**Non-trivial data cleaning cases:**
- Namibia ISO code `NA` → pandas reads as `NaN` → restored via `.loc`
- 82 records without `country_code` → saved as `unknown`, not removed
- `units_sold` missing values → median imputation (robust to outliers)

---

## Getting Started

```bash
git clone https://github.com/husak-alla/sales-dashboard.git
cd sales-dashboard
pip install -r requirements.txt
streamlit run main.py
```

## Tests

```bash
pytest tests/ -v
```