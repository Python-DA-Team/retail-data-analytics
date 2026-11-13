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


# задание 1_04
# Візуалізація (matplotlib/seaborn)
# 4. Barplot: виручка по категоріях за 2024 vs 2025 (поруч).
def task_1_04_barplot_revenue_by_category() -> None:
    print("\nЗавдання 1_04. Barplot: виручка по категоріях за 2024 vs 2025")

    transactions_path = OUT / 'transactions_cleaned.csv'
    company_path = OUT / 'company_data_cleaned.xlsx'
    result_dir = ROOT / "results" / "task_1_04"

    tx = pd.read_csv(transactions_path, low_memory=False)

    tx['transaction_date'] = pd.to_datetime(tx['transaction_date'], errors='coerce', format='mixed')
    tx['year'] = tx['transaction_date'].dt.year

    tx = tx[tx['is_return'] == 0].copy()

    tx['quantity'] = pd.to_numeric(tx['quantity'], errors='coerce').abs()
    tx['quantity'] = tx['quantity'].replace(0, 1).fillna(1).astype(int)

    if 'discount_percent' in tx.columns:
        tx['discount'] = pd.to_numeric(tx['discount_percent'], errors='coerce').fillna(0.0).astype(float)
        tx.loc[tx['discount'] > 1, 'discount'] = tx.loc[tx['discount'] > 1, 'discount'] / 100.0
    else:
        tx['discount'] = 0.0

    products = pd.read_excel(company_path, sheet_name='Products')

    products['unit_price'] = products['unit_price'].astype(str).str.replace(r'[$\u20AC\u00A3,]', '', regex=True)
    products['unit_price'] = pd.to_numeric(products['unit_price'], errors='coerce').fillna(0.0)

    products_clean = products[['product_id', 'category', 'unit_price']]

    print("Об'єднання таблиць та розрахунок виручки...")
    merged_df = pd.merge(tx, products_clean, on='product_id', how='left')

    df_filtered = merged_df[merged_df['year'].isin([2024, 2025])]

    df_filtered['clean_total_amount'] = df_filtered['quantity'] * df_filtered['unit_price'] * (1 - df_filtered['discount'])

    revenue_data = df_filtered.groupby(['category', 'year'])['clean_total_amount'].sum().reset_index()

    result_dir.mkdir(parents=True, exist_ok=True)
    table_path = result_dir / "revenue_by_category_2024_2025.csv"
    chart_path = result_dir / "revenue_by_category_2024_2025.png"
    revenue_data.to_csv(table_path, index=False, encoding="utf-8-sig")

    plt.figure(figsize=(12, 6))
    sns.set_theme(style="whitegrid")

    ax = sns.barplot(
        data=revenue_data,
        x='category',
        y='clean_total_amount',
        hue='year',
        palette='Set2'
    )

    plt.title('Виручка по категоріях за 2024 vs 2025 роки ', fontsize=16, pad=15)
    plt.xlabel('Категорія товару', fontsize=12, labelpad=10)
    plt.ylabel('Загальна виручка', fontsize=12, labelpad=10)

    plt.ticklabel_format(style='plain', axis='y')
    plt.xticks(rotation=30, ha='right')
    plt.legend(title='Рік', loc='upper right')
    plt.tight_layout()

    plt.savefig(chart_path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"Таблицю збережено: {table_path.relative_to(ROOT)}")
    print(f"Графік збережено: {chart_path.relative_to(ROOT)}")


if __name__ == "__main__":
    clean_data()
    task_1_04_barplot_revenue_by_category()
