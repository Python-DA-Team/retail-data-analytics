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


# задание 1_02
# 2. Розподіл виручки по категоріях. pivot_table:
# category по рядках, місяць по стовпцях, сума total_amount.
# Яка категорія лідирує щомісяця?
def task_1_02_pivot_table() -> None:
    print("\nЗавдання 1_02. Розподіл виручки по категоріях")

    CLEAN_DIR = OUT
    RESULT_DIR = ROOT / "results" / "task_1_02_patero_analysis"

    def load_table(filename: str, sep: str = ",") -> pd.DataFrame:
        """Універсальне завантаження очищених таблиць з cleaned_data"""
        if filename == "products_cleaned.csv":
            path = CLEAN_DIR / "company_data_cleaned.xlsx"
            if not path.exists():
                raise FileNotFoundError(f"Файл {path} не знайдено")
            return pd.read_excel(path, sheet_name="Products")

        path = CLEAN_DIR / filename
        if not path.exists():
            raise FileNotFoundError(f"Файл {path} не знайдено")
        return pd.read_csv(path, low_memory=False, sep=sep)

    # 1. Завантаження очищених таблиць
    transactions = load_table("transactions_cleaned.csv")
    products = load_table("products_cleaned.csv")

    # 2. Перетворення дати у datetime та витяг місяця
    transactions["transaction_date"] = pd.to_datetime(transactions["transaction_date"], errors="coerce")
    transactions["month"] = transactions["transaction_date"].dt.month

    # 3. Об’єднання транзакцій з продуктами по product_id
    df = transactions.merge(products, on="product_id", how="left")

    # 4. Побудова pivot_table: категорії по рядках, місяці по стовпцях, сума total_amount
    pivot = pd.pivot_table(
        df,
        values="total_amount",
        index="category",
        columns="month",
        aggfunc="sum",
        fill_value=0
    )

    print("Pivot table 'Revenue breakdown by category and month':\n", pivot)

    # 5. Знаходження категорії-лідера щомісяця
    leaders = pivot.idxmax()
    leaders_table = pd.DataFrame({
        "month": leaders.index,
        "leader_category": leaders.values
    })
    print("\nLeaderboard:\n", leaders_table)
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    pivot_path = RESULT_DIR / "revenue_pivot_by_category.csv"
    leaders_path = RESULT_DIR / "monthly_category_leaders.csv"
    pivot.to_csv(pivot_path, encoding="utf-8-sig")
    leaders_table.to_csv(leaders_path, index=False, encoding="utf-8-sig")
    print(f"Pivot-таблицю збережено: {pivot_path.relative_to(ROOT)}")
    print(f"Таблицю лідерів збережено: {leaders_path.relative_to(ROOT)}")


if __name__ == "__main__":
    clean_data()
    task_1_02_pivot_table()
