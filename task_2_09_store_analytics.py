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


# задание 2_09
# [Просунуті] Магазинна аналітика
# Магазинна аналітика. З company_data.xlsx (Stores + Employees + Inventory + transactions):
# Revenue per square meter (total_amount / size_sqm) по store_format
# Revenue per employee (total_amount / кількість співробітників) по магазинах
# Найефективніший магазин за обома метриками
def task_2_09_store_analytics() -> None:
    print("\nЗавдання 2_09. Магазинна аналітика")

    result_dir = ROOT / "results" / "task_2_09"

    excel_file = OUT / "company_data_cleaned.xlsx"
    transactions_path = OUT / "transactions_cleaned.csv"

    df_stores = pd.read_excel(excel_file, sheet_name="Stores")
    df_employees = pd.read_excel(excel_file, sheet_name="Employees")

    try:
        df_transactions = pd.read_csv(
            transactions_path,
            low_memory=False
        )

        needed_cols = ["store_id", "total_amount", "is_return"]
        df_transactions = df_transactions[[col for col in needed_cols if col in df_transactions.columns]]

    except Exception as e:
        print(f"ERROR: {e}")
        df_transactions = pd.read_csv(transactions_path, sep=";", on_bad_lines="skip")

    if df_transactions.empty or "total_amount" not in df_transactions.columns:
        print("ERROR")

    df_transactions["is_return"] = pd.to_numeric(df_transactions["is_return"], errors="coerce").fillna(0)
    df_transactions["total_amount"] = pd.to_numeric(df_transactions["total_amount"], errors="coerce").fillna(0)
    df_transactions["store_id"] = pd.to_numeric(df_transactions["store_id"], errors="coerce").fillna(-1)

    df_valid_sales = df_transactions[df_transactions["is_return"] == 0]
    store_revenue = df_valid_sales.groupby("store_id")["total_amount"].sum().reset_index()
    store_revenue.columns = ["store_id", "total_revenue"]

    # співробітники, що реально працюють (зі статусом активно)
    df_employees["status"] = df_employees["status"].astype(str).str.strip().str.lower()
    df_active_emp = df_employees[df_employees["status"] == "active"]
    employee_count = df_active_emp.groupby("store_id")["employee_id"].count().reset_index()
    employee_count.columns = ["store_id", "employee_count"]

    df_analytics = df_stores.merge(store_revenue, on="store_id", how="left").fillna(0)
    df_analytics = df_analytics.merge(employee_count, on="store_id", how="left").fillna(0)

    df_analytics["store_format"] = df_analytics["store_format"].astype(str).str.strip()
    df_analytics["store_format"] = df_analytics["store_format"].replace({"Streett": "Street", "Mal": "Mall"})

    # метрики в розрізі магазинів
    df_analytics["revenue_per_sqm"] = df_analytics.apply(
        lambda r: r["total_revenue"] / r["size_sqm"] if str(r["store_format"]).lower() != "online" and r[
            "size_sqm"] > 0 else 0,
        axis=1
    )

    df_analytics["revenue_per_employee"] = df_analytics.apply(
        lambda r: r["total_revenue"] / r["employee_count"] if r["employee_count"] > 0 else 0,
        axis=1
    )

    # ефективності по формату магазина
    df_offline_only = df_analytics[df_analytics["store_format"].str.lower() != "online"]
    format_grouped = df_offline_only.groupby("store_format").agg(
        total_revenue=("total_revenue", "sum"),
        total_size=("size_sqm", "sum")
    ).reset_index()
    format_grouped["revenue_per_sqm"] = format_grouped["total_revenue"] / format_grouped["total_size"]

    # найефективніший магазин (метод рангів для офлайн магазинів)
    df_rank = df_offline_only[df_offline_only["size_sqm"] > 0].copy()
    if not df_rank.empty:
        df_rank["rank_sqm"] = df_rank["revenue_per_sqm"].rank(ascending=False)
        df_rank["rank_emp"] = df_rank["revenue_per_employee"].rank(ascending=False)
        df_rank["combined_score"] = df_rank["rank_sqm"] + df_rank["rank_emp"]
        best_store = df_rank.sort_values(by="combined_score", ascending=True).iloc[0]
    else:
        best_store = None

    result_dir.mkdir(parents=True, exist_ok=True)
    analytics_path = result_dir / "store_analytics.csv"
    format_path = result_dir / "revenue_per_sqm_by_store_format.csv"
    best_store_path = result_dir / "best_store_by_metrics.csv"
    df_analytics.to_csv(analytics_path, index=False, encoding="utf-8-sig")
    format_grouped.to_csv(format_path, index=False, encoding="utf-8-sig")

    format_print = format_grouped.copy()
    format_print["revenue_per_sqm"] = format_print["revenue_per_sqm"].map("{:,.2f}".format)
    print(f"Revenue per square meter:\n\n{format_print[['store_format', 'revenue_per_sqm']].to_string(index=False)}\n")
    print("-" * 20)

    df_console = df_analytics.copy()
    df_console["total_revenue"] = df_console["total_revenue"].map("{:,.2f}".format)
    df_console["revenue_per_sqm"] = df_console["revenue_per_sqm"].map("{:,.2f}".format)
    df_console["revenue_per_employee"] = df_console["revenue_per_employee"].map("{:,.2f}".format)
    print(f"Загальний звіт по магазинам (перші 20):\n\n"
          f"{df_console[['store_id', 'store_name', 'store_format', 'size_sqm', 'employee_count', 'total_revenue', 'revenue_per_sqm', 'revenue_per_employee']].head(20).to_string(index=False)}\n")
    print("-" * 20)

    if best_store is not None:
        print(f"Найефективніший фізичний магазин за обома показниками:\n\n",
              f"Магазин: {best_store['store_name']} (ID: {best_store['store_id']})\n",
              f"Країна: {best_store['country']}. Формат: {best_store['store_format']}\n",
              f"Площа: {best_store['size_sqm']} кв.м. Штат: {int(best_store['employee_count'])} співробітників\n",
              f"Виручка/кв. метр: {best_store['revenue_per_sqm']:,.2f}\n",
              f"Виручка/одного співробітника: {best_store['revenue_per_employee']:,.2f}")
        best_store.to_frame().T.to_csv(best_store_path, index=False, encoding="utf-8-sig")
        print(f"Таблицю збережено: {best_store_path.relative_to(ROOT)}")

    print(f"Таблицю збережено: {analytics_path.relative_to(ROOT)}")
    print(f"Таблицю збережено: {format_path.relative_to(ROOT)}")


if __name__ == "__main__":
    clean_data()
    task_2_09_store_analytics()
