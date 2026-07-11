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


# задание 1_01
# Базові (pandas)
# 1. Топ-10 товарів за виручкою.
# Згрупувати transactions.csv по product_id (лише продажі, не returns), порахувати sum(total_amount).
# Об'єднати з Products через company_data.xlsx. Вивести таблицю.
def task_1_01_top_products_by_revenue() -> None:
    print("\nЗавдання 1_01. Топ-10 товарів за виручкою")

    transactions_path = OUT / 'transactions_cleaned.csv'
    excel_path = OUT / 'company_data_cleaned.xlsx'

    df_transactions = pd.read_csv(transactions_path, low_memory=False)
    df_products = pd.read_excel(excel_path, sheet_name='Products')

    df_transactions = df_transactions[df_transactions['is_return'] == 0].copy()
    if df_transactions['total_amount'].dtype == 'object':
        df_transactions['total_amount'] = df_transactions['total_amount'].astype(str).str.replace("", regex=True)
    df_transactions['total_amount'] = pd.to_numeric(df_transactions['total_amount'], errors='coerce')

    # групую товари та обчислюю загальну виручку
    revenue_per_product = (
        df_transactions.groupby('product_id')['total_amount']
        .sum()
        .reset_index()
    )
    revenue_per_product.columns = ['product_id', 'total_amount']

    final_table = pd.merge(revenue_per_product, df_products, on='product_id', how='inner')

    # сортую товари з топ-10 за спаданням
    top_10_products = (
        final_table.sort_values(by='total_amount', ascending=False)
        .head(10)
        .reset_index(drop=True)
    )

    top_10_products['total_amount'] = top_10_products['total_amount'].map('{:,.2f}'.format)
    output_columns = ['product_name', 'category', 'total_amount']
    available_columns = [col for col in output_columns if col in top_10_products.columns]

    print(f'\nТОП-10 товарів за виручкою:\n\n{top_10_products[available_columns].to_string(index=False)}')
    result_dir = ROOT / "results" / "task_1_01"
    result_dir.mkdir(parents=True, exist_ok=True)
    output_path = result_dir / "top_10_products_by_revenue.csv"
    top_10_products[available_columns].to_csv(output_path, index=False, encoding="utf-8-sig")
    print(f"Таблицю збережено: {output_path.relative_to(ROOT)}")
    print('-' * 20)


if __name__ == "__main__":
    clean_data()
    task_1_01_top_products_by_revenue()
