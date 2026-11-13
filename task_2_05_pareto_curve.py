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


# задание 2_05
# [Візуалізація] Pareto curve з лінією 80%
# Побудувати Pareto curve: cumulative revenue vs products (bar + line). Додати пунктирну лінію 80% для наочності.
def task_2_05_pareto_curve() -> None:
    print("\nЗавдання 2_05. Pareto curve з лінією 80%")

    result_dir = ROOT / "results" / "task_2_05"

    tx = pd.read_csv(OUT / "transactions_cleaned.csv", low_memory=False)

    tx["quantity"] = pd.to_numeric(tx["quantity"], errors="coerce").abs().replace(0, 1).fillna(1).astype(int)
    tx["discount_percent"] = pd.to_numeric(tx["discount_percent"], errors="coerce").fillna(0.0).astype(float)
    tx.loc[tx["discount_percent"] > 1, "discount_percent"] = tx.loc[tx["discount_percent"] > 1, "discount_percent"] / 100.0

    products = pd.read_excel(OUT / "company_data_cleaned.xlsx", sheet_name="Products")
    products["unit_price"] = pd.to_numeric(products["unit_price"], errors="coerce").fillna(0.0)
    products_clean = products[["product_id", "unit_price"]]

    df = pd.merge(tx, products_clean, on="product_id", how="left")

    df["revenue"] = df["quantity"] * df["unit_price"] * (1 - df["discount_percent"])

    product_revenue = df.groupby("product_id")["revenue"].sum().reset_index()

    product_revenue = product_revenue.sort_values(by="revenue", ascending=False).reset_index(drop=True)

    product_revenue["cum_revenue"] = product_revenue["revenue"].cumsum()

    total_revenue = product_revenue["revenue"].sum()
    product_revenue["cum_percentage"] = (product_revenue["cum_revenue"] / total_revenue) * 100

    product_revenue["product_id"] = product_revenue["product_id"].astype(str)

    result_dir.mkdir(parents=True, exist_ok=True)
    table_path = result_dir / "pareto_product_revenue.csv"
    chart_path = result_dir / "pareto_curve_80_percent.png"
    product_revenue.to_csv(table_path, index=False, encoding="utf-8-sig")

    fig, ax1 = plt.subplots(figsize=(14, 7))

    color_bar = "#4f81bd"
    ax1.bar(product_revenue["product_id"], product_revenue["revenue"], color=color_bar, alpha=0.85, label="Виручка продукту")
    ax1.set_xlabel("ID Продукту", fontsize=12, labelpad=10)
    ax1.set_ylabel("Виручка", color=color_bar, fontsize=12)
    ax1.tick_params(axis="y", labelcolor=color_bar)

    clean_labels = [str(int(float(x))) for x in product_revenue["product_id"]]

    ax1.set_xticks(range(len(product_revenue)))
    ax1.set_xticklabels(clean_labels, rotation=90, fontsize=5)

    ax1.yaxis.get_major_formatter().set_scientific(False)

    ax2 = ax1.twinx()
    color_line = "#c00000"
    ax2.plot(product_revenue["product_id"], product_revenue["cum_percentage"], color=color_line, marker="o", ms=4, lw=2, label="Кумулятивний %")
    ax2.set_ylabel("Кумулятивний відсоток", color=color_line, fontsize=12)
    ax2.tick_params(axis="y", labelcolor=color_line)
    ax2.set_ylim(0, 105)

    ax2.axhline(y=80, color="gray", linestyle="--", linewidth=1.5, label="Межа Парето (80%)")

    plt.title("Аналіз Парето", fontsize=16, pad=20)

    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="center right", frameon=True)

    ax1.grid(True, axis="y", linestyle=":", alpha=0.6)

    plt.tight_layout()
    plt.savefig(chart_path, dpi=300, bbox_inches="tight")
    plt.close()

    print("Pareto curve побудовано.")
    print(f"Таблицю збережено: {table_path.relative_to(ROOT)}")
    print(f"Графік збережено: {chart_path.relative_to(ROOT)}")


if __name__ == "__main__":
    clean_data()
    task_2_05_pareto_curve()
