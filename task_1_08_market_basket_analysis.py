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


# задание 1_08
# Блок 1. Завдання 8.
# Market Basket Analysis. Для кожного customer_id зібрати всі category куплених товарів за один день.
# Знайти найчастіші пари категорій, що купують разом (комбінації 2 категорій).
# Які топ-5 пар?
# > Підказка: якщо same-day покупок мало — спробуйте згрупувати по customer_id + тиждень через .dt.isocalendar().week.
# Використайте itertools.combinations() для генерації пар категорій.
# Для підрахунку пар зручно застосувати value_counts() на серії пар або nunique() для перевірки кількості унікальних пар.
def task_1_08_market_basket_analysis() -> None:
    print("\nЗавдання 1_08. Market Basket Analysis")

    CLEAN_DIR = OUT
    result_dir = ROOT / "results" / "task_1_08"

    transactions_path = CLEAN_DIR / "transactions_cleaned.csv"
    excel_path = CLEAN_DIR / "company_data_cleaned.xlsx"

    if not transactions_path.exists() or not excel_path.exists():
        clean_data()

    df_trans = pd.read_csv(transactions_path)
    df_prod = pd.read_excel(excel_path, sheet_name="Products")

    df = pd.merge(df_trans, df_prod[["product_id", "category"]], on="product_id", how="left")

    df = df.dropna(subset=["customer_id", "transaction_date", "category"])

    df["transaction_date"] = pd.to_datetime(df["transaction_date"])
    df["week"] = df["transaction_date"].dt.isocalendar().week

    basket = df.groupby(["customer_id", "week"])["category"].apply(set)

    pairs = []
    for cats in basket:
        if len(cats) > 1:
            pairs.extend(combinations(sorted(list(cats)), 2))

    top_5 = pd.Series(pairs).value_counts().head(5)

    result_dir.mkdir(parents=True, exist_ok=True)
    table_path = result_dir / "top_5_category_pairs.csv"
    top_5.rename_axis("category_pair").reset_index(name="count").to_csv(
        table_path,
        index=False,
        encoding="utf-8-sig",
    )

    print(" Топ-5 пар категорій, що купують разом")
    print(top_5)
    print(f"Таблицю збережено: {table_path.relative_to(ROOT)}")


if __name__ == "__main__":
    clean_data()
    task_1_08_market_basket_analysis()
