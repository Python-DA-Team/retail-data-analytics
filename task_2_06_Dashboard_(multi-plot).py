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


# задание 2_06
# 6. [Візуалізація] Dashboard (multi-plot):
# Dashboard (multi-plot): 4 графіки на одному полотні (subplots(2,2)):
# Revenue trend (line)
# Profit margin by store format (sns.barplot)
# Returns rate by category (pie — plt.pie)
# Monthly transaction count (sns.lineplot з marker='o')
def task_2_06_dashboard_multi_plot() -> None:
    print("\nЗавдання 2_06. Dashboard (multi-plot)")

    RESULT_DIR = ROOT / "results" / "task_2_06"

    transactions = pd.read_csv(OUT / "transactions_cleaned.csv", low_memory=False)
    products = pd.read_excel(OUT / "company_data_cleaned.xlsx", sheet_name="Products")
    returns = pd.read_csv(OUT / "returns_cleaned.csv", low_memory=False)
    stores = pd.read_excel(OUT / "company_data_cleaned.xlsx", sheet_name="Stores")

    transactions["transaction_date"] = pd.to_datetime(transactions["transaction_date"], errors="coerce")
    transactions["month"] = transactions["transaction_date"].dt.to_period("M").astype(str)

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle("Total Revenue")

    # 1. Revenue trend (line)
    revenue_trend = transactions.groupby("month", as_index=False)["total_amount"].sum()

    sns.lineplot(
        data=revenue_trend,
        x="month",
        y="total_amount",
        color="royalblue",
        marker="o",
        ax=axes[0, 0]
    )
    axes[0, 0].set_title("Revenue Trend")
    axes[0, 0].set_xlabel("Month")
    axes[0, 0].set_ylabel("Total Amount")
    axes[0, 0].tick_params(axis="x", rotation=90)

    # 2. Profit margin by store format (barplot)
    df = transactions.merge(products[["product_id", "margin_pct"]], on="product_id", how="left")
    df = df.merge(stores[["store_id", "store_format"]], on="store_id", how="left")
    df["profit"] = df["total_amount"] * df["margin_pct"] / 100

    df_clean = df.dropna(subset=["margin_pct"])
    df_clean = df_clean[df_clean["total_amount"] > 0]

    share_unknown = (df_clean["store_format"].isna().sum() / len(df_clean)) * 100
    print(f"Частка Unknown: {share_unknown:.1f}%")

    # враховуючи кількість транзакцій з магазином з форматом NaN та id NaN -5002 строки (5%), переназвемо формат
    # у 'Uknow' та зробимо умовні 'id'

    df_clean["store_format"] = df_clean["store_format"].fillna("Unknown")
    df_clean["store_id"] = df_clean["store_id"].fillna(-1)  # умовний ID

    profit_margin_format = (
        df_clean.groupby("store_format").apply(
        lambda g: g["profit"].sum()/ g["total_amount"].sum() * 100).
        reset_index(name="profit_margin")
    )

    sns.barplot(
        data=profit_margin_format,
        x="store_format",
        y="profit_margin",
        color="green",
        ax=axes[0, 1]
    )
    axes[0, 1].set_title("Profit Margin by Store Format")
    axes[0, 1].set_xlabel("Store Format")
    axes[0, 1].set_ylabel("Profit Margin")

    # 3. Returns rate by category (pie chart)
    returns = transactions[transactions["is_return"] == True]
    returns_rate = returns.merge(products[["product_id", "category"]], on="product_id", how="left")
    returns_rate = returns_rate.groupby("category")["transaction_id"].count()

    axes[1, 0].pie(
        returns_rate,
        labels=returns_rate.index,
        colors=sns.color_palette("pastel"),
        autopct="%1.1f%%"
    )
    axes[1, 0].set_title("Returns Rate by Category")

    # 4. Monthly transaction count (lineplot з marker='o')

    monthly_counts = transactions.groupby("month")["transaction_id"].count().reset_index()

    sns.lineplot(
        data=monthly_counts,
        x="month",
        y="transaction_id",
        marker="o",
        ax=axes[1, 1]
    )
    axes[1, 1].set_title("Monthly Transaction Count")
    axes[1, 1].set_xlabel("Month")
    axes[1, 1].set_ylabel("Transaction Count")
    axes[1, 1].tick_params(axis="x", rotation=90)

    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    dashboard_path = RESULT_DIR / "dashboard_multi_plot.png"
    revenue_trend_path = RESULT_DIR / "revenue_trend.csv"
    profit_margin_path = RESULT_DIR / "profit_margin_by_store_format.csv"
    returns_rate_path = RESULT_DIR / "returns_rate_by_category.csv"
    monthly_counts_path = RESULT_DIR / "monthly_transaction_count.csv"
    revenue_trend.to_csv(revenue_trend_path, index=False, encoding="utf-8-sig")
    profit_margin_format.to_csv(profit_margin_path, index=False, encoding="utf-8-sig")
    returns_rate.to_csv(returns_rate_path, encoding="utf-8-sig")
    monthly_counts.to_csv(monthly_counts_path, index=False, encoding="utf-8-sig")

    plt.tight_layout()
    plt.savefig(dashboard_path, dpi=300, bbox_inches="tight")
    plt.close()

    print(f"Таблицю збережено: {revenue_trend_path.relative_to(ROOT)}")
    print(f"Таблицю збережено: {profit_margin_path.relative_to(ROOT)}")
    print(f"Таблицю збережено: {returns_rate_path.relative_to(ROOT)}")
    print(f"Таблицю збережено: {monthly_counts_path.relative_to(ROOT)}")
    print(f"Графік збережено: {dashboard_path.relative_to(ROOT)}")


if __name__ == "__main__":
    clean_data()
    task_2_06_dashboard_multi_plot()
