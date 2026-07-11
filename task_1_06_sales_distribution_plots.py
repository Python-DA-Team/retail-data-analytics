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


# задание 1_06
# 6. Boxplot / Violinplot (seaborn) + KDE: розподіл total_amount по категоріях (тільки продажі > 0). Показати викиди. Спробуйте обидва типи:
#    - sns.boxplot() — медіана, квартилі, викиди
#    - sns.violinplot() — boxplot + KDE (щільність розподілу)
#    - Додатково: sns.kdeplot(data=df, x='total_amount', hue='category', fill=True) — порівняння розподілів категорій на одному графіку
def task_1_06_sales_distribution_plots() -> None:
    print("\nЗавдання 1_06. Sales distribution plots")

    result_dir = ROOT / "results" / "task_1_06"

    tx = pd.read_csv(OUT / "transactions_cleaned.csv", low_memory=False)

    tx = tx[tx["is_return"] == 0].copy()
    tx["quantity"] = pd.to_numeric(tx["quantity"], errors="coerce").abs()
    tx["quantity"] = tx["quantity"].replace(0, 1).fillna(1).astype(int)

    if "discount" in tx.columns:
        tx["discount"] = pd.to_numeric(tx["discount"], errors="coerce").fillna(0.0)
        tx.loc[tx["discount"] > 1, "discount"] = tx["discount"] / 100.0
    else:
        tx["discount"] = 0.0

    products = pd.read_excel(OUT / "company_data_cleaned.xlsx", sheet_name="Products")
    products["unit_price"] = pd.to_numeric(products["unit_price"], errors="coerce").fillna(0.0)
    products["category"] = products["category"].astype(str).str.strip()
    products["category"] = products["category"].str.capitalize()
    products_clean = products[["product_id", "category", "unit_price"]]

    merged_df = pd.merge(tx, products_clean, on="product_id", how="left")

    merged_df["clean_total_amount"] = merged_df["quantity"] * merged_df["unit_price"] * (1 - merged_df["discount"])

    df_filtered = merged_df[merged_df["clean_total_amount"] > 0]

    result_dir.mkdir(parents=True, exist_ok=True)
    table_path = result_dir / "sales_distribution_data.csv"
    boxplot_path = result_dir / "boxplot_total_amount_by_category.png"
    violinplot_path = result_dir / "violinplot_total_amount_by_category.png"
    kdeplot_path = result_dir / "kdeplot_total_amount_by_category.png"
    df_filtered.to_csv(table_path, index=False, encoding="utf-8-sig")

    sns.set_theme(style="whitegrid")

    plt.figure(figsize=(10, 6))
    sns.boxplot(
        data=df_filtered,
        x="category",
        y="clean_total_amount",
        hue="category",
        legend=False,
        palette="Set3"
    )
    plt.title("1. Boxplot")
    plt.xlabel("Категорія товару")
    plt.ylabel("Сума")
    plt.xticks(rotation=30, ha="right")
    plt.ticklabel_format(style="plain", axis="y")
    plt.tight_layout()
    plt.savefig(boxplot_path, dpi=300, bbox_inches="tight")
    plt.close()

    plt.figure(figsize=(10, 6))
    sns.violinplot(
        data=df_filtered,
        x="category",
        y="clean_total_amount",
        hue="category",
        legend=False,
        palette="Set3"
    )
    plt.title("2. Violinplot")
    plt.xlabel("Категорія товару")
    plt.ylabel("Сума транзакції")
    plt.xticks(rotation=30, ha="right")
    plt.ticklabel_format(style="plain", axis="y")
    plt.tight_layout()
    plt.savefig(violinplot_path, dpi=300, bbox_inches="tight")
    plt.close()

    plt.figure(figsize=(10, 6))
    sns.kdeplot(
        data=df_filtered,
        x="clean_total_amount",
        hue="category",
        fill=True,
        alpha=0.35,
        palette="Set1"
    )
    plt.title("3. KDEplot")
    plt.xlabel("Сума транзакції")
    plt.ylabel("Щільність розподілу")
    plt.ticklabel_format(style="plain", axis="x")
    plt.tight_layout()
    plt.savefig(kdeplot_path, dpi=300, bbox_inches="tight")
    plt.close()

    print(f"Побудовано графіки для {df_filtered['category'].nunique()} категорій.")
    print(f"Таблицю збережено: {table_path.relative_to(ROOT)}")
    print(f"Графік збережено: {boxplot_path.relative_to(ROOT)}")
    print(f"Графік збережено: {violinplot_path.relative_to(ROOT)}")
    print(f"Графік збережено: {kdeplot_path.relative_to(ROOT)}")


if __name__ == "__main__":
    clean_data()
    task_1_06_sales_distribution_plots()
