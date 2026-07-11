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


# задание 1_05
# Heatmap (sns.heatmap): кореляція unit_price, cost_price, margin_pct, quantity, total_amount.
# Використати annot=True та cmap='coolwarm'.
def task_1_05_correlation_heatmap() -> None:
    print("\nЗавдання 1_05. Heatmap: кореляція числових показників")

    transactions_path = OUT / "transactions_cleaned.csv"
    company_path = OUT / "company_data_cleaned.xlsx"
    result_dir = ROOT / "results" / "task_1_05"

    tx = pd.read_csv(transactions_path, low_memory=False)
    products = pd.read_excel(company_path, sheet_name="Products")

    tx = tx[tx["is_return"] == 0].copy()
    tx["quantity"] = pd.to_numeric(tx["quantity"], errors="coerce").abs()
    tx["quantity"] = tx["quantity"].replace(0, 1).fillna(1).astype(int)
    tx["total_amount"] = pd.to_numeric(tx["total_amount"], errors="coerce")

    for col in ["unit_price", "cost_price", "margin_pct"]:
        if col in products.columns:
            products[col] = pd.to_numeric(products[col], errors="coerce")

    products_clean = products[["product_id", "unit_price", "cost_price", "margin_pct"]]

    merged_df = pd.merge(tx, products_clean, on="product_id", how="left")

    columns_for_corr = ["unit_price", "cost_price", "margin_pct", "quantity", "total_amount"]
    df_corr_ready = merged_df[columns_for_corr].dropna()

    corr_matrix = df_corr_ready.corr()

    result_dir.mkdir(parents=True, exist_ok=True)
    table_path = result_dir / "correlation_matrix.csv"
    chart_path = result_dir / "correlation_heatmap.png"
    corr_matrix.to_csv(table_path, encoding="utf-8-sig")

    plt.figure(figsize=(10, 6))
    sns.heatmap(
        corr_matrix,
        annot=True,
        cmap="coolwarm",
        fmt=".2f",
        linewidths=0.5,
    )

    plt.title("Матриця кореляції")
    plt.tight_layout()
    plt.savefig(chart_path, dpi=300, bbox_inches="tight")
    plt.close()

    print("Матрицю кореляції побудовано.")
    print(f"Таблицю збережено: {table_path.relative_to(ROOT)}")
    print(f"Графік збережено: {chart_path.relative_to(ROOT)}")


if __name__ == "__main__":
    clean_data()
    task_1_05_correlation_heatmap()
