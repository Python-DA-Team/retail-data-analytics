# Retail Data Analytics

Team learning project focused on retail sales analysis for 2024-2025. The project covers product performance, revenue, profitability, returns, time series, financial modeling, data quality, and dashboard development.

## Technologies

- Python 3
- pandas and NumPy
- matplotlib and seaborn
- Jupyter Notebook
- Git and GitHub

## Data

The analysis uses transaction, returns, marketing, salary, product, store, employee, and inventory data. The main source files are:

- `transactions.csv`
- `returns.csv`
- `marketing.csv`
- `salaries.parquet`
- `company_data.xlsx`

Files containing personal data, secrets, or large raw datasets should not be committed without approval.

## Project scope

### 1. Product, revenue, finance, and strategy analysis

The first block covers:

- Top products by revenue and revenue by category.
- Average order value by store.
- Category comparisons for 2024 and 2025.
- Correlation heatmaps and distribution analysis with boxplots, violin plots, and KDE curves.
- ABC analysis and cumulative revenue contribution.
- Market basket analysis for frequently purchased category pairs.
- Discount effectiveness and cohort retention.
- Customer lifetime value estimation and customer segmentation.

### 2. Profitability, Pareto analysis, time series, dashboards, and data quality

The second block covers:

- Revenue, cost, profit, and margin analysis for completed sales.
- Pareto analysis using cumulative revenue contribution.
- Data quality scoring based on completeness, uniqueness, validity, and consistency.
- Stacked monthly revenue, cost, and profit charts.
- Time series features, rolling averages, growth and decline analysis, and anomaly detection.
- Returns analysis by category, reason, discount, and payment method.
- Store efficiency using revenue per square meter and revenue per employee.
- Monthly P&L modeling with revenue, COGS, gross profit, marketing costs, salary costs, operating profit, and net margin.
- An executive dashboard with KPI cards and monthly comparisons.

## Recommended structure

```text
retail-data-analytics/
├── data/                 # local data, when permitted
├── notebooks/            # exploratory notebooks
├── src/                  # Python scripts
├── outputs/
│   ├── figures/          # PNG/JPG charts
│   └── tables/           # CSV/XLSX summaries
├── requirements.txt
└── README.md
```

Task files should include the block number, task number, and a short descriptive name, for example:

```text
src/block_1/task_04_category_revenue.py
outputs/figures/block_1_task_04_category_revenue.png
```

## Team workflow

1. Update the local `main` branch with `git switch main` and `git pull origin main`.
2. Create a task branch, for example `git switch -c username/block-1-task-04`.
3. Add the code, short conclusions, and required outputs.
4. Commit and push the task branch.
5. Open a pull request from the task branch to `main`.
6. Keep one logical result per pull request.
7. Update `main` after review and merge before starting the next task.

Do not commit directly to `main` or modify another contributor's files without agreement.

## Pull request checklist

- Block and task number.
- Source code or notebook.
- Required chart or table outputs.
- Short description of the method.
- Two to five key findings.
- No accidental changes or deletions of other contributors' files.

## Team

Repository organization: **Python-DA-Team**  
Working team: **data-analysts**

Українська версія опису збережена у файлі [`README_UA.md`](README_UA.md).
