# Блок 1. Завдання 8.
# Market Basket Analysis. Для кожного customer_id зібрати всі category куплених товарів за один день.
# Знайти найчастіші пари категорій, що купують разом (комбінації 2 категорій).
# Які топ-5 пар?
# > Підказка: якщо same-day покупок мало — спробуйте згрупувати по customer_id + тиждень через .dt.isocalendar().week.
# Використайте itertools.combinations() для генерації пар категорій.
# Для підрахунку пар зручно застосувати value_counts() на серії пар або nunique() для перевірки кількості унікальних пар.

from itertools import combinations
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent
CLEAN_DIR = ROOT / "cleaned_data"


def solve_market_basket():

    transactions_path = CLEAN_DIR / "transactions_cleaned.csv"
    excel_path = CLEAN_DIR / "company_data_cleaned.xlsx"

    if not transactions_path.exists() or not excel_path.exists():
        from cleaning import main as clean_data
        clean_data()

    df_trans = pd.read_csv(transactions_path)
    df_prod = pd.read_excel(excel_path, sheet_name="Products")

    df = pd.merge(df_trans, df_prod[['product_id', 'category']], on='product_id', how='left')

    df = df.dropna(subset=['customer_id', 'transaction_date', 'category'])

    df['transaction_date'] = pd.to_datetime(df['transaction_date'])
    df['week'] = df['transaction_date'].dt.isocalendar().week

    basket = df.groupby(['customer_id', 'week'])['category'].apply(set)

    pairs = []
    for cats in basket:
        if len(cats) > 1:
            pairs.extend(combinations(sorted(list(cats)), 2))

    top_5 = pd.Series(pairs).value_counts().head(5)

    print(" Топ-5 пар категорій, що купують разом")
    print(top_5)


if __name__ == "__main__":
    solve_market_basket()