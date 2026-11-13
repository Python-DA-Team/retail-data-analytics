# 🛒 Retail Data Analytics

<p align="center"><strong>PYTHON-DA-TEAM · RETAIL DATA ANALYTICS</strong></p>
<p align="center"><em>Sales Performance · Profitability · Data Quality · Financial Analytics</em></p>
<p align="center">
  <img alt="Python" src="https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white">
  <img alt="pandas" src="https://img.shields.io/badge/pandas-150458?style=flat-square&logo=pandas&logoColor=white">
  <img alt="NumPy" src="https://img.shields.io/badge/NumPy-013243?style=flat-square&logo=numpy&logoColor=white">
  <img alt="Matplotlib" src="https://img.shields.io/badge/Matplotlib-0F172A?style=flat-square">
  <img alt="SQLite" src="https://img.shields.io/badge/SQLite-003B57?style=flat-square&logo=sqlite&logoColor=white">
</p>

A comprehensive project for analytical processing, data cleaning, and financial modeling of retail sales (2024–2025).

<!-- Optional: add a verified, repository-hosted team banner here when an actual image is available. -->

---

## 📋 Quick Navigation

| Explore | Work with the project | Reference |
| :-- | :-- | :-- |
| [📌 Overview](#project-overview) | [🧹 Data Cleaning](#data-cleaning-module) | [📐 Methodology](#metric-definitions-methodology) |
| [🛠 Technology Stack](#technology-stack) | [▶️ Running the Project](#running-the-project) | [⚠️ Limitations](#current-analytical-limitations) |
| [📁 Data & Structure](#data-project-structure) | [📊 Analytical Tasks](#analytical-tasks) | [👥 Team Workflow](#team-workflow-submission) |

**Analytical blocks:** [Products, Revenue & Customers](#block-1-products-revenue-and-customers) · [Profitability & Operations](#block-2-profitability-and-operations)

---


<a id="project-overview"></a>

## 📌 Project Overview

**Retail Data Analytics** is a team educational project by **Python-DA-Team**, focused on a comprehensive analysis of retail datasets for 2024–2025. The project covers the full data lifecycle: raw data cleaning, product and category analysis, customer behavior research, store performance evaluation, returns analysis, and simplified financial P&L modeling.

Project Board: [Trello](https://trello.com/b/FnI0Waiu/tima1).

> [!NOTE]
> **Current Repository State:** Analytical work is organized as **22 Python scripts split across two blocks**. During development, tasks are executed as standalone scripts using a shared `cleaning.py` module. The final submission involves combining the code into a single `main.py` file and preparing a 5–7 slide PDF presentation. The root `main.py` file is currently absent in the local repository; tasks are run via individual scripts.

### Primary Analytical Goals

- **Product & Category Analysis:** Identify top-revenue products and categories; compare category revenue between 2024 and 2025.
- **Customer Analytics:** Calculate average check, product revenue concentration, customer retention (Cohort Retention), category pairing analysis, and educational CLV (Customer Lifetime Value) scoring.
- **Operational Profitability:** Assess margin metrics, reported return reasons, retail space efficiency (revenue per m²), and staff productivity (revenue per active employee).
- **Data Quality & Visualization:** Evaluate raw CSV file quality (Data Quality Score), generate output CSV tables, and render PNG visualizations.

---


<a id="technology-stack"></a>

## 🛠 Technology Stack

| **Domain**             | **Tools & Libraries**                         |
| ---------------------- | --------------------------------------------- |
| **Data Processing**    | Python, pandas, NumPy                         |
| **Data Visualization** | Matplotlib, Seaborn                           |
| **Excel Processing**   | openpyxl                                      |
| **Database**           | SQLite (via built-in Python `sqlite3` module) |
| **Development & VCS**  | Python scripts, Git, GitHub                   |
| **Input Formats**      | CSV, TSV, JSON, Excel, SQLite                 |

> [!IMPORTANT]
> **Environment Specification:** Root tasks do not require Jupyter Notebook or Parquet formats. Verified local environment: **Python 3.11.9**, **pandas 3.0.3**, **NumPy 2.4.6**, **Matplotlib 3.11.0**, **Seaborn 0.13.2**, **openpyxl 3.1.5**. A unified dependencies file (`requirements.txt`) is currently absent in the repository root.

---


<a id="data-project-structure"></a>

## 📁 Data & Project Structure

The file and directory hierarchy of the main analytical pipeline is shown below:

```text
retail-data-analytics/
├── cleaning.py                  # Shared data cleaning module
├── task_1_*.py                  # 11 product & customer analysis tasks (Block 1)
├── task_2_*.py                  # 11 profitability & operations tasks (Block 2)
├── company_data.xlsx            # Source Excel file (5 sheets)
├── transactions.csv             # Retail transactions data
├── returns.csv                  # Returns dataset
├── marketing.csv                # Marketing campaigns and budgets
├── salaries.csv                 # Payroll and salary payments
├── customers.csv                # Customer base
├── employees.csv                # Employee records
├── stores.csv                   # Store directory
├── support_tickets.tsv          # Customer support tickets
├── api_logs.json                # API request logs
├── analytics_practice.db        # Local SQLite database
├── cleaned_data/                # Locally generated cleaned datasets
├── results/                     # Locally generated tables and plots
├── .gitignore                   # Git ignore rules
└── README.md                    # Project documentation
```

### Input Files and Description

> [!TIP]
> Source data files must be placed in the same directory as `cleaning.py`. Cloning the repository alone may not include all local datasets.

| **File**                | **Content / Purpose**                                                                                              |
| ----------------------- | ------------------------------------------------------------------------------------------------------------------ |
| `company_data.xlsx`     | 5 sheets: Customers, Products, Stores, Employees, Inventory                                                        |
| `transactions.csv`      | Transaction IDs, dates, customers, products, stores, quantities, discounts, amounts, payment methods, return flags |
| `returns.csv`           | Return records, reasons, refund amounts, purchase dates, and return dates                                          |
| `marketing.csv`         | Campaign dates, budgets, product IDs, campaign performance metrics                                                 |
| `salaries.csv`          | Payroll records (month and `net_pay` for P&L modeling)                                                             |
| `customers.csv`         | Customer records (also represented in the Excel workbook)                                                          |
| `employees.csv`         | Employee records (also represented in the Excel workbook)                                                          |
| `stores.csv`            | Store records (also represented in the Excel workbook)                                                             |
| `support_tickets.tsv`   | Support service tickets                                                                                            |
| `api_logs.json`         | API request logs                                                                                                   |
| `analytics_practice.db` | Local practice DB; cleaned into a separate copy when present                                                       |

### Primary Join Keys

| **Entity**    | **Join Key**  | **Associated Tables & Files**                           |
| ------------- | ------------- | ------------------------------------------------------- |
| **Customers** | `customer_id` | Transactions, support tickets, API logs (via `user_id`) |
| **Products**  | `product_id`  | Transactions, returns, inventory, marketing             |
| **Stores**    | `store_id`    | Transactions, employees, inventory                      |
| **Employees** | `employee_id` | Salaries                                                |

> [!NOTE]
> Python task scripts read table files directly rather than executing SQL queries against the SQLite database. SQLite handling is executed separately inside the cleaning module. Input data may contain missing or invalid IDs; the cleaning module validates key relationships prior to analysis.

---


<a id="data-cleaning-module"></a>

## 🧹 Data Cleaning Module

`cleaning.py` serves as the shared data preparation module. It standardizes missing value representations, normalizes text fields, removes full row duplicates, converts dates and numbers, checks supported ID relationships and value ranges, and repairs supported malformed transaction rows.

Where required fields are present, transaction amounts are validated against the formula:

```text
expected_amount = quantity * unit_price * (1 - discount_percent / 100)
```

For rows flagged as returns, a negative transaction amount is expected. Invalid values may be replaced with `NaN`; cleaning does not guarantee full imputation of all missing cells.

### Output Cleaned Files (`cleaned_data/`)

- Cleaned CSV files appended with `_cleaned.csv`.
- `company_data_cleaned.xlsx` (preserves 5 source sheets; products are extracted from the *Products* sheet).
- `support_tickets_cleaned.tsv` from the required support tickets input, and `api_logs_cleaned.json` when the JSON source exists.
- `cleaning_report.json` containing metrics on row counts, missing values, and parsing errors.
- `analytics_practice_cleaned.db` (when the source DB is present and cleaning runs; the original DB remains untouched). SQLite cleanup uses a limited set of SQL corrections, separate from the tabular cleaning rules.

<details>
<summary>⚠️ Data cleaning cache behavior & regeneration notes</summary>

**Caching Logic:** The cleaning module skips re-processing if all files in `CLEANED_FILES` exist on disk. Task wrapper functions check a reduced subset of required files. Cache checks do not compare source file modification timestamps or validate cache integrity; the cleaned database is not included in these checks. To regenerate outputs after changing the source data, first ensure the original inputs are available, then rename the existing `cleaned_data/` folder to keep a backup and run `cleaning.py` again. A missing JSON source is skipped, but its cleaned output remains in the cleaner's cache checklist, so later direct cleaning runs will not consider the cache complete. Most tasks process `cleaned_data/`. **Task 2_03 intentionally evaluates 5 raw CSV files** (`customers.csv`, `employees.csv`, `marketing.csv`, `stores.csv`, and `returns.csv`) to measure baseline data quality.

</details>

---


<a id="running-the-project"></a>

## ▶️ Running the Project

Run the following commands from the repository root directory in **Windows PowerShell**. If `.venv` is already configured, use it directly and skip environment setup.

### 1. Virtual Environment Setup

```powershell
# Create Python 3.11 virtual environment
py -3.11 -m venv .venv

# Install dependencies using the virtual environment's Python
.\.venv\Scripts\python.exe -m pip install pandas numpy matplotlib seaborn openpyxl

```

### 2. Executing Data Cleaning and Analytical Scripts

```powershell
# 1. Run the shared data cleaning pipeline
.\.venv\Scripts\python.exe cleaning.py

# 2. Examples of executing individual analytical tasks
.\.venv\Scripts\python.exe task_1_01_top_products_by_revenue.py
.\.venv\Scripts\python.exe task_1_03_average_check_by_store.py
.\.venv\Scripts\python.exe "task_2_10_P&L_Financial_Modeling.py"
.\.venv\Scripts\python.exe task_2_11_dynamic_executive_dashboard.py

```

> [!TIP]
> Task scripts call a shared cleaning wrapper before analysis; actual cleaning runs when the required outputs are missing. Script filenames containing special characters (`&` or parentheses `()`) must be enclosed in quotes in CLI commands.

### Results Output Directory (`results/`)

Outputs are written to `results/` subdirectories as CSV tables and PNG visualizations where a task creates charts. Most folders follow `results/task_1_01` or `results/task_2_03`. Existing naming exceptions include `results/task_1_3`, `results/task_1_02_patero_analysis`, and `results/task_2_02_patero_analysis_80`.

---


<a id="analytical-tasks"></a>

## 📊 Analytical Tasks


### Block 1: Products, Revenue, and Customers

| **#**    | **Script**                                 | **Analytical Focus**                                                      |
| -------- | ------------------------------------------ | ------------------------------------------------------------------------- |
| **1_01** | `task_1_01_top_products_by_revenue.py`     | Top 10 products by total revenue                                          |
| **1_02** | `task_1_02_revenue_pivot_by_category.py`   | Revenue pivot by category and calendar month number; category leaders     |
| **1_03** | `task_1_03_average_check_by_store.py`      | Revenue per unique transaction ID across retail stores                    |
| **1_04** | `task_1_04_barplot_revenue_by_category.py` | Category revenue comparison between 2024 and 2025                         |
| **1_05** | `task_1_05_correlation_heatmap.py`         | Correlation matrix: price, margin, quantity, and total transaction amount |
| **1_06** | `task_1_06_sales_distribution_plots.py`    | Sales distribution analysis (Boxplot, Violin plot, Density plot)          |
| **1_07** | `task_1_07_abc_analysis_of_products.py`    | Product ABC classification at 70% and 90% cumulative revenue thresholds   |
| **1_08** | `task_1_08_market_basket_analysis.py`      | Top 5 category pairs by customer and ISO week number                      |
| **1_09** | `task_1_09_discount_analysis.py`           | Observed quantities and amounts with and without discounts                |
| **1_10** | `task_1_10_cohort_retention.py`            | Monthly customer cohorts and repeat purchases in initial category         |
| **1_11** | `task_1_11_clv_estimation.py`              | Educational CLV scoring and four segments based on ranked-score quartiles |

---


### Block 2: Profitability and Operations

| **#**    | **Script**                                 | **Analytical Focus**                                                                                           |
| -------- | ------------------------------------------ | -------------------------------------------------------------------------------------------------------------- |
| **2_01** | `task_2_01_profit_analysis.py`             | Monthly profit on non-return sales after COGS and a 5% revenue-based expense allowance                         |
| **2_02** | `task_2_02_patero_analysis_80.py`          | Pareto analysis: revenue concentration around 80% cumulative threshold                                         |
| **2_03** | `task_2_03_data_quality_score.py`          | Data Quality Score across 4 metrics for 5 raw CSV files                                                        |
| **2_04** | `task_2_04_monthly_revenue_stacked_bar.py` | 2025 revenue table and stacked costs plus gross profit chart                                                   |
| **2_05** | `task_2_05_pareto_curve.py`                | Pareto chart: product revenue ranking and cumulative percentage curve                                          |
| **2_06** | `task_2_06_Dashboard_(multi-plot).py`      | Multi-panel dashboard: revenue trend, store margin, returns, transactions                                      |
| **2_07** | `task_2_07_time_series_analysis.py`        | Daily amounts, 7- and 30-observation rolling means, and anomaly flags                                          |
| **2_08** | `task_2_08_returns_analysis.py`            | Return rates by category and payment method, mean refunds by reason, discount relationships, and return timing |
| **2_09** | `task_2_09_store_analytics.py`             | Revenue per m² and per active employee, brick-and-mortar store rankings                                        |
| **2_10** | `task_2_10_P&L_Financial_Modeling.py`      | Monthly P&L: revenue, COGS, marketing, payroll, 5% expense allowance, operating profit                         |
| **2_11** | `task_2_11_dynamic_executive_dashboard.py` | Executive dashboard: 6 KPI cards, 2 charts, 3-month comparative view                                           |

---


<a id="metric-definitions-methodology"></a>

## 📐 Metric Definitions & Methodology

> [!IMPORTANT]
> **Discrepancies in Profit Calculation:** Profit definitions vary across tasks. **Task 2_01** subtracts product cost (COGS) and a 5% revenue overhead. **Task 2_11** calculates gross profit (Revenue minus COGS) before deducting marketing, payroll, and administrative expenses. These figures must not be presented as identical metrics.

### 1. Monthly P&L Model in Task 2_10

```text
Revenue = sum(total_amount)
COGS = sum(quantity * cost_price)
Gross Profit = Revenue - COGS
Operating Profit = Gross Profit - Marketing Cost - Salary Cost - 0.05 * Revenue
Net Margin % = Operating Profit / Revenue * 100
```

- **Marketing:** Campaign budgets are split evenly across campaign duration months.
- **Payroll:** Extracted from the `net_pay` column in `salaries_cleaned.csv`.
- *Note:* The metric is labeled `Net Margin %`, but its numerator is operating profit; interest and taxes are not modeled separately. The task includes return rows in revenue and does not reverse their product costs in COGS. This treatment needs review before interpreting the output as a financial statement.

### 2. Data Quality Score in Task 2_03

The overall score is the arithmetic mean of four metrics calculated for each of the five source CSV files:

- **Completeness:** Proportion of non-null cells.
- **Uniqueness:** One minus the proportion of exact duplicate rows.
- **Validity:** Proportion of rows passing task-specific anomaly checks.
- **Consistency:** Proportion of rows passing selected value and range checks.

These checks do not constitute a complete schema, primary-key, or cross-table referential-integrity audit.

### 3. Executive Dashboard in Task 2_11

Generates static dashboards `dashboard_2025-01.png`, `dashboard_2025-06.png`, `dashboard_2025-12.png`, and a summary table `dashboard_month_comparison.csv`. Each image displays 6 KPI cards, a daily revenue trend, and a category breakdown plot. The function accepts a month parameter; it is not an interactive application and does not calculate MoM or YoY percentage changes.

---


<a id="current-analytical-limitations"></a>

## ⚠️ Current Analytical Limitations

1. **Date Period Aggregation:** Task 1_02 groups by calendar month number without year. Task 1_08 groups by customer and ISO week number without ISO year. Both can combine periods from 2024 and 2025. Category pairs reflect grouped customer activity, not verified items from a single order.
2. **Revenue Calculation Variance:** Return filtering logic varies: some scripts exclude returns, others process all transaction amounts, while tasks 2_04 and 2_05 re-derive revenue totals. Cross-task revenue numbers require normalization before comparison.
3. **Educational Nature of CLV (Task 1_11):** The formula `clv = arpu_month * purchase_frequency_month * lifetime_months` is a historical educational score, not a validated forecast of future customer profit. ARPU already includes purchase frequency. The four segments are based on quartiles of ranked scores, not a clustering algorithm.
4. **Discount Analysis Interpretation (Task 1_09):** Group comparisons between discounted and non-discounted transactions highlight observed correlations but do not establish causality.
5. **Anomaly Detection (Task 2_07):** A row is flagged when the absolute daily amount difference exceeds twice the standard deviation of daily differences. The rule does not subtract the mean difference. Rolling windows contain 7 or 30 daily observations; missing calendar dates are not filled before calculation.

---


<a id="team-workflow-submission"></a>

## 👥 Team Workflow & Submission

### Team Members (Python-DA-Team)

`Serhii` · `Dmytro` · `Svitlana` · `Yuliia` · `Oksana`

```text
[ Personal Branches ] ──► [ Integration: Serhii ] ──► [ Review & QA ] ──► [ Explicit Approval ] ──► [ main ]
```

### Pre-Submission Checklist

1. **Validation:** Verify input datasets, mathematical formulas, output tables, charts, and generated artifacts on live data.
2. **Syntax Check:** After Python edits, run `python -m py_compile` with the edited filenames, then run each affected task on the source data.
3. **Calculation Review:** Resolve the documented analytical limitations before using the results in final conclusions.
4. **Final Assembly:** Put the cleaning code first in one self-contained `main.py`, followed by all 22 tasks. The submitted file must not depend on a separate `cleaning.py`.
5. **Final Validation:** Add tests for cleaning, key formulas, and expected output files. Run the complete `main.py` on the original inputs before submission.
6. **Deliverables:** Submit one `main.py` file and a PDF presentation of 5-7 slides.

> [!IMPORTANT]
> **Git Workflow:** Use `Serhii` for integration work. Commits, pushes, pull requests, and merging into `main` require explicit approval. Generated `cleaned_data/`, `results/`, database files, large source datasets, and local instruction files such as `AGENTS.md` must not be added to commits. Review `git status` before committing.
