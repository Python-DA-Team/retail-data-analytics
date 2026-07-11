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


# задание 2_04
# Побудувати stacked bar у matplotlib: revenue + cost + profit по місяцях (12 місяців 2025 року). Використати plt.bar() з параметром bottom.
def task_2_04_monthly_revenue_stacked_bar() -> None:
    print("\nЗавдання 2_04. Stacked bar: revenue, cost, profit")

    result_dir = ROOT / "results" / "task_2_04"

    tx = pd.read_csv(OUT / "transactions_cleaned.csv", low_memory=False)

    tx["transaction_date"] = pd.to_datetime(tx["transaction_date"], errors="coerce", format="mixed")
    tx["year"] = tx["transaction_date"].dt.year
    tx["month"] = tx["transaction_date"].dt.month

    tx_2025 = tx[tx["year"] == 2025].copy()

    tx_2025["quantity"] = pd.to_numeric(tx_2025["quantity"], errors="coerce").abs().replace(0, 1).fillna(1).astype(int)

    tx_2025["discount_percent"] = pd.to_numeric(tx_2025["discount_percent"], errors="coerce").fillna(0.0).astype(float)
    tx_2025.loc[tx_2025["discount_percent"] > 1, "discount_percent"] = tx_2025.loc[tx_2025["discount_percent"] > 1, "discount_percent"] / 100.0

    products = pd.read_excel(OUT / "company_data_cleaned.xlsx", sheet_name="Products")

    for col in ["unit_price", "cost_price"]:
        products[col] = pd.to_numeric(products[col], errors="coerce").fillna(0.0)

    products["category"] = products["category"].astype(str).str.strip().str.capitalize()
    products_clean = products[["product_id", "unit_price", "cost_price"]]

    df_2025 = pd.merge(tx_2025, products_clean, on="product_id", how="left")

    df_2025["revenue"] = df_2025["quantity"] * df_2025["unit_price"] * (1 - df_2025["discount_percent"])
    df_2025["cost"] = df_2025["quantity"] * df_2025["cost_price"]
    df_2025["profit"] = df_2025["revenue"] - df_2025["cost"]

    monthly_data = df_2025.groupby("month")[["revenue", "cost", "profit"]].sum().reset_index()

    monthly_data = monthly_data.set_index("month").reindex(range(1, 13), fill_value=0).reset_index()

    result_dir.mkdir(parents=True, exist_ok=True)
    table_path = result_dir / "monthly_revenue_cost_profit_2025.csv"
    chart_path = result_dir / "monthly_revenue_stacked_bar_2025.png"
    monthly_data.to_csv(table_path, index=False, encoding="utf-8-sig")

    plt.figure(figsize=(10, 6))

    months = monthly_data["month"]
    costs = monthly_data["cost"]
    profits = monthly_data["profit"]

    month_names = ["Січ", "Лют", "Бер", "Квіт", "Трав", "Черв", "Лип", "Серп", "Врес", "Жовт", "Лист", "Груд"]

    plt.bar(months, costs, label="Собівартість (Cost)", color="#fc8d62", alpha=0.85)

    plt.bar(months, profits, bottom=costs, label="Чистий прибуток (Profit)", color="#66c2a5", alpha=0.85)

    plt.title("Структура виручки за 2025 рік")
    plt.xlabel("Місяць")
    plt.ylabel("Сума")

    plt.xticks(range(1, 13), month_names)

    plt.ticklabel_format(style="plain", axis="y")

    plt.grid(axis="y", linestyle="--", alpha=0.5)
    plt.legend(loc="upper left", frameon=True)

    plt.tight_layout()
    plt.savefig(chart_path, dpi=300, bbox_inches="tight")
    plt.close()

    print("Stacked bar за 2025 рік побудовано.")
    print(f"Таблицю збережено: {table_path.relative_to(ROOT)}")
    print(f"Графік збережено: {chart_path.relative_to(ROOT)}")


if __name__ == "__main__":
    clean_data()
    task_2_04_monthly_revenue_stacked_bar()
