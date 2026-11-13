from __future__ import annotations

import os
from itertools import combinations
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from cleaning import main as run_cleaning


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "cleaned_data"
CLEANED_FILES = [
    "company_data_cleaned.xlsx",
    "customers_cleaned.csv",
    "employees_cleaned.csv",
    "stores_cleaned.csv",
    "marketing_cleaned.csv",
    "returns_cleaned.csv",
    "salaries_cleaned.csv",
    "transactions_cleaned.csv",
    "support_tickets_cleaned.tsv",
]


def cleaned_data_exists() -> bool:
    return OUT.exists() and all((OUT / filename).exists() for filename in CLEANED_FILES)


def clean_data() -> None:
    if not cleaned_data_exists():
        run_cleaning()


# задание 1_10
def task_1_10_cohort_retention() -> None:
    print("\nЗавдання 1_10. Cohort Retention")

    result_dir = ROOT / "results" / "task_1_10"
    transactions_path = OUT / "transactions_cleaned.csv"
    products_path = OUT / "company_data_cleaned.xlsx"

    transactions = pd.read_csv(transactions_path, low_memory=False)
    products = pd.read_excel(products_path, sheet_name="Products")

    sales = transactions.loc[transactions["is_return"].eq(0)].copy()
    sales["transaction_date"] = pd.to_datetime(sales["transaction_date"], errors="coerce")
    sales = sales.dropna(subset=["customer_id", "product_id", "transaction_date"])

    sales["customer_id"] = sales["customer_id"].astype("int64")
    sales["product_id"] = sales["product_id"].astype("int64")
    sales = sales.merge(
        products[["product_id", "category"]],
        on="product_id",
        how="inner",
        validate="many_to_one",
    )

    sales = sales.sort_values(["customer_id", "transaction_date", "transaction_id"])
    first_purchase = (
        sales.groupby("customer_id", as_index=False)
        .first()[["customer_id", "transaction_date", "category"]]
        .rename(
            columns={
                "transaction_date": "first_purchase_date",
                "category": "first_category",
            }
        )
    )

    sales = sales.merge(first_purchase, on="customer_id", how="inner")
    sales["purchase_month"] = sales["transaction_date"].dt.to_period("M")
    sales["cohort_month"] = sales["first_purchase_date"].dt.to_period("M")
    sales["month_number"] = (
        (sales["purchase_month"].dt.year - sales["cohort_month"].dt.year) * 12
        + sales["purchase_month"].dt.month
        - sales["cohort_month"].dt.month
    )

    same_category = sales.loc[sales["category"].eq(sales["first_category"])]
    active = (
        same_category[["cohort_month", "month_number", "customer_id"]]
        .drop_duplicates()
        .groupby(["cohort_month", "month_number"])["customer_id"]
        .nunique()
        .unstack(fill_value=0)
    )

    cohort_size = (
        first_purchase.assign(
            cohort_month=first_purchase["first_purchase_date"].dt.to_period("M")
        )
        .groupby("cohort_month")["customer_id"]
        .nunique()
    )

    retention = active.div(cohort_size, axis=0).mul(100)
    last_month = sales["purchase_month"].max()
    for cohort_month in retention.index:
        months_available = last_month.ordinal - cohort_month.ordinal
        unavailable = retention.columns > months_available
        retention.loc[cohort_month, unavailable] = float("nan")

    retention.index = retention.index.astype(str)
    retention.columns = [f"M{int(col)}" for col in retention.columns]
    retention = retention.round(2)

    details = first_purchase.copy()
    details["cohort_month"] = details["first_purchase_date"].dt.to_period("M").astype(str)

    result_dir.mkdir(parents=True, exist_ok=True)
    retention_path = result_dir / "cohort_retention.csv"
    details_path = result_dir / "customer_first_category.csv"
    chart_path = result_dir / "cohort_retention.png"
    retention.to_csv(retention_path, encoding="utf-8-sig")
    details.to_csv(details_path, index=False, encoding="utf-8-sig")

    plt.figure(figsize=(16, 9))
    sns.heatmap(
        retention,
        annot=True,
        fmt=".1f",
        cmap="YlGnBu",
        vmin=0,
        vmax=100,
        cbar_kws={"label": "Retention, %"},
    )
    plt.title("Cohort Retention за категорією першої покупки")
    plt.xlabel("Місяць після першої покупки")
    plt.ylabel("Місяць першої покупки")
    plt.tight_layout()
    plt.savefig(chart_path, dpi=180, bbox_inches="tight")
    plt.close()

    print(
        f"Cohort Retention: {len(retention)} когорт, "
        f"{retention.columns[0]}-{retention.columns[-1]}"
    )
    print(f"Таблицю збережено: {retention_path.relative_to(ROOT)}")
    print(f"Таблицю збережено: {details_path.relative_to(ROOT)}")
    print(f"Графік збережено: {chart_path.relative_to(ROOT)}")


if __name__ == "__main__":
    clean_data()
    task_1_10_cohort_retention()
