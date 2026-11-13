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


# задание 2_10
# 10. [Просунуті] Фінансове моделювання P&L.
# Фінансове моделювання. Створити P&L по місяцях:
# - Revenue: sum(total_amount)
# - COGS: sum(quantity * cost_price)
# - Gross Profit = Revenue - COGS
# - Marketing Cost: sum(budget) з marketing.csv по місяцях кампаній
# - Salary Cost: sum(net_pay) з salaries.parquet по місяцях
# - Operating Profit = Gross Profit - Marketing - Salaries - 5% операційні
# - Net Margin % = Operating Profit / Revenue * 100
def task_2_10_load_table(filename: str, sep: str = ",") -> pd.DataFrame:
    path = OUT / filename
    if not path.exists():
        raise FileNotFoundError(f"Файл {path} не знайдено")
    return pd.read_csv(path, low_memory=False, sep=sep)


def task_2_10_pnl_financial_modeling() -> None:
    print("\nЗавдання 2_10. P&L Financial Modeling")

    RESULT_DIR = ROOT / "results" / "task_2_10"

    transactions = task_2_10_load_table("transactions_cleaned.csv")
    products = pd.read_excel(OUT / "company_data_cleaned.xlsx", sheet_name="Products")
    marketing = task_2_10_load_table("marketing_cleaned.csv")
    salaries = task_2_10_load_table("salaries_cleaned.csv")

    # Transactions
    transactions["transaction_date"] = pd.to_datetime(transactions["transaction_date"], errors="coerce")
    transactions["month"] = transactions["transaction_date"].dt.to_period("M")

    # - Revenue: sum(total_amount). Revenue: сума total_amount по місяцях
    revenue = transactions.groupby("month")["total_amount"].sum().reset_index(name="Revenue")

    # - COGS: sum(quantity * cost_price). COGS: сума quantity * cost_price по місяцях
    transactions = transactions.merge(products[["product_id", "product_name", "cost_price"]], on="product_id", how="left")
    transactions["COGS"] = transactions["quantity"] * transactions["cost_price"]
    cogs = transactions.groupby("month")["COGS"].sum().reset_index()

    # - Gross Profit = Revenue - COGS.
    pnl = revenue.merge(cogs, on="month")
    pnl["Gross Profit"] = pnl["Revenue"] - pnl["COGS"]

    # - Marketing Cost: sum(budget) з marketing.csv по місяцях кампаній

    # Точний варіант (розподіл бюджету по всіх місяцях кампанії), як кaмпанія триває декілька місяців - більш точний
    marketing["start_date"] = pd.to_datetime(marketing["start_date"], errors="coerce")
    marketing["end_date"] = pd.to_datetime(marketing["end_date"], errors="coerce")

    rows = []
    for _, row in marketing.iterrows():
        if pd.notnull(row["start_date"]) and pd.notnull(row["end_date"]):
            # список місяців між start_date і end_date
            months = pd.period_range(row["start_date"], row["end_date"], freq="M")
            # рівномірний розподіл бюджету
            monthly_budget = row["budget"] / len(months) if len(months) > 0 else row["budget"]
            for m in months:
                rows.append({"month": m, "Marketing Cost": monthly_budget})

    marketing_cost = pd.DataFrame(rows).groupby("month")["Marketing Cost"].sum().reset_index()

    pnl = pnl.merge(marketing_cost, on="month", how="left").fillna({"Marketing Cost": 0})

    # - Salary Cost: sum(net_pay) з salaries.parquet по місяцях
    # сума net_pay по місяцях - беремо готову колонку month
    salaries["month"] = salaries["month"].astype("period[M]")
    salary_cost = salaries.groupby("month")["net_pay"].sum().reset_index(name="Salary Cost")

    pnl = pnl.merge(salary_cost, on="month", how="left").fillna({"Salary Cost": 0})

    # - Operating Profit = Gross Profit - Marketing - Salaries - 5% операційні
    pnl["Operating Profit"] = pnl["Gross Profit"] - pnl["Marketing Cost"] - pnl["Salary Cost"] - (pnl["Revenue"] * 0.05)

    # - Net Margin % = Operating Profit / Revenue * 100
    pnl["Net Margin %"] = pnl["Operating Profit"] / pnl["Revenue"] * 100

    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    table_path = RESULT_DIR / "pnl_financial_modeling.csv"
    net_margin_chart_path = RESULT_DIR / "net_margin_by_month.png"
    revenue_profit_chart_path = RESULT_DIR / "revenue_vs_operating_profit.png"
    pnl.to_csv(table_path, index=False, encoding="utf-8-sig")

    print(pnl.head())
    print(f"Таблицю збережено: {table_path.relative_to(ROOT)}")

    # Net Margin % — негативний, показує збитковість.
    # Висновок: вийшла таблиця P&L по місяцях — і видно, що витрати на зарплати та маркетинг значно перевищують
    # валовий прибуток, тому Operating Profit виходить від’ємним, а Net Margin % негативний (наприклад, −58% у січні).
    # Це тестові дані, то: модель правильно працює, просто фінансові показники показують збитковість

    # графіки для візуалізації:
    # Лінійний графік Net Margin %
    plt.figure(figsize=(10, 4))
    plt.plot(pnl["month"].astype(str), pnl["Net Margin %"], marker="o", color="red")
    plt.xticks(rotation=90)
    plt.title("Net Margin % по місяцях", fontsize=14, fontweight="bold")
    plt.xlabel("Місяць")
    plt.ylabel("Net Margin %")
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(net_margin_chart_path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"Графік збережено: {net_margin_chart_path.relative_to(ROOT)}")

    # Барплот Revenue vs Operating Profit
    plt.figure(figsize=(10, 5))
    width = 0.35
    x = range(len(pnl["month"]))

    plt.bar(x, pnl["Revenue"], width=width, label="Revenue", color="skyblue")
    plt.bar([i + width for i in x], pnl["Operating Profit"], width=width, label="Operating Profit", color="green")

    plt.xticks([i + width / 2 for i in x], pnl["month"].astype(str), rotation=90)
    plt.title("Revenue vs Operating Profit по місяцях", fontsize=14, fontweight="bold")
    plt.xlabel("Місяць", fontsize=14)
    plt.ylabel("Сума")
    plt.legend()
    plt.tight_layout()
    plt.savefig(revenue_profit_chart_path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"Графік збережено: {revenue_profit_chart_path.relative_to(ROOT)}")


if __name__ == "__main__":
    clean_data()
    task_2_10_pnl_financial_modeling()
