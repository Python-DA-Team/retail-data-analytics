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


# задание 2_11
# [Додаткова] Динамічний executive dashboard
# Динамічний екзек'ютів-дашборд. Створити функцію generate_dashboard(data_path, month),
# яка приймає шлях до даних та місяць (напр. '2025-06') і будує 6 графіків:
# - KPI cards: Revenue, Profit, Margin %, Customers Count, Avg Order Value, Return Rate
# - Плюс 2 графіки на вибір (тренд, розподіл, Pareto тощо)
# - Функція має зберігати PNG з ім'ям dashboard_{month}.png
# - Викликати для трьох різних місяців: '2025-01', '2025-06', '2025-12'
# - Порівняльний аналіз: який місяць найкращий? Чому?
def generate_dashboard(data_path, month: str) -> dict[str, float]:
    data_path = Path(data_path)
    result_dir = ROOT / "results" / "task_2_11"
    result_dir.mkdir(parents=True, exist_ok=True)

    transactions = pd.read_csv(data_path / "transactions_cleaned.csv", low_memory=False)
    products = pd.read_excel(data_path / "company_data_cleaned.xlsx", sheet_name="Products")

    transactions["transaction_date"] = pd.to_datetime(transactions["transaction_date"], errors="coerce")
    transactions["month"] = transactions["transaction_date"].dt.to_period("M").astype(str)
    transactions["day"] = transactions["transaction_date"].dt.date

    df = transactions[transactions["month"] == month].copy()
    if df.empty:
        raise ValueError(f"Немає даних за місяць {month}")

    products_small = products[["product_id", "category", "cost_price"]].copy()
    products_small["cost_price"] = pd.to_numeric(products_small["cost_price"], errors="coerce").fillna(0)
    df = df.merge(products_small, on="product_id", how="left")

    df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce").fillna(0)
    df["total_amount"] = pd.to_numeric(df["total_amount"], errors="coerce").fillna(0)
    df["is_return"] = pd.to_numeric(df["is_return"], errors="coerce").fillna(0)

    sales = df[df["is_return"] == 0].copy()
    revenue = sales["total_amount"].sum()
    cost = (sales["quantity"] * sales["cost_price"]).sum()
    profit = revenue - cost
    margin = profit / revenue * 100 if revenue != 0 else 0
    customers_count = sales["customer_id"].nunique()
    avg_order_value = revenue / len(sales) if len(sales) > 0 else 0
    return_rate = df["is_return"].mean() * 100

    daily_revenue = sales.groupby("day")["total_amount"].sum().reset_index()
    category_revenue = (
        sales.groupby("category")["total_amount"]
        .sum()
        .sort_values(ascending=False)
        .head(8)
        .reset_index()
    )

    kpis = [
        ("Revenue", revenue, "{:,.2f}"),
        ("Profit", profit, "{:,.2f}"),
        ("Margin %", margin, "{:.2f}%"),
        ("Customers Count", customers_count, "{:,.0f}"),
        ("Avg Order Value", avg_order_value, "{:,.2f}"),
        ("Return Rate", return_rate, "{:.2f}%"),
    ]

    fig = plt.figure(figsize=(18, 11))
    grid = fig.add_gridspec(3, 4)
    fig.suptitle(f"Executive Dashboard - {month}", fontsize=18, fontweight="bold")

    for i, (title, value, template) in enumerate(kpis):
        ax = fig.add_subplot(grid[i // 3, i % 3])
        ax.set_facecolor("#f5f5f5")
        ax.text(0.5, 0.62, template.format(value), ha="center", va="center", fontsize=20, fontweight="bold")
        ax.text(0.5, 0.28, title, ha="center", va="center", fontsize=11)
        ax.set_xticks([])
        ax.set_yticks([])
        for spine in ax.spines.values():
            spine.set_visible(False)

    ax_info = fig.add_subplot(grid[0:2, 3])
    ax_info.axis("off")
    ax_info.text(
        0.02,
        0.85,
        f"Transactions: {len(df):,}\n"
        f"Sales: {len(sales):,}\n"
        f"Returns: {int(df['is_return'].sum()):,}\n"
        f"Categories: {sales['category'].nunique():,}",
        fontsize=13,
        va="top",
    )

    ax_trend = fig.add_subplot(grid[2, 0:2])
    ax_trend.plot(daily_revenue["day"], daily_revenue["total_amount"], marker="o", color="#4f81bd")
    ax_trend.set_title("Daily Revenue Trend")
    ax_trend.set_xlabel("Day")
    ax_trend.set_ylabel("Revenue")
    ax_trend.tick_params(axis="x", rotation=45)
    ax_trend.grid(True, alpha=0.3)

    ax_category = fig.add_subplot(grid[2, 2:4])
    sns.barplot(data=category_revenue, x="total_amount", y="category", ax=ax_category, color="#66c2a5")
    ax_category.set_title("Revenue by Category")
    ax_category.set_xlabel("Revenue")
    ax_category.set_ylabel("Category")

    plt.tight_layout()
    dashboard_path = result_dir / f"dashboard_{month}.png"
    plt.savefig(dashboard_path, dpi=300, bbox_inches="tight")
    plt.close(fig)

    print(f"Графік збережено: {dashboard_path.relative_to(ROOT)}")

    return {
        "month": month,
        "revenue": revenue,
        "profit": profit,
        "margin_percent": margin,
        "customers_count": customers_count,
        "avg_order_value": avg_order_value,
        "return_rate": return_rate,
    }


def task_2_11_dynamic_executive_dashboard() -> None:
    print("\nЗавдання 2_11. Динамічний executive dashboard")

    result_dir = ROOT / "results" / "task_2_11"
    months = ["2025-01", "2025-06", "2025-12"]

    comparison = []
    for month in months:
        comparison.append(generate_dashboard(OUT, month))

    comparison_df = pd.DataFrame(comparison)
    comparison_path = result_dir / "dashboard_month_comparison.csv"
    comparison_df.to_csv(comparison_path, index=False, encoding="utf-8-sig")

    best_month = comparison_df.sort_values(
        by=["profit", "margin_percent", "revenue"],
        ascending=False,
    ).iloc[0]

    print("\nПорівняльний аналіз")
    print(comparison_df.round(2).to_string(index=False))
    print(
        f"Найкращий місяць: {best_month['month']}. "
        f"Причина: найбільший profit = {best_month['profit']:.2f}, "
        f"margin = {best_month['margin_percent']:.2f}%, "
        f"revenue = {best_month['revenue']:.2f}, "
        f"return rate = {best_month['return_rate']:.2f}%."
    )
    print(f"Таблицю збережено: {comparison_path.relative_to(ROOT)}")


if __name__ == "__main__":
    clean_data()
    task_2_11_dynamic_executive_dashboard()
