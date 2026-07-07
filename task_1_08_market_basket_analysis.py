# Блок 1. Завдання 8.
# Market Basket Analysis.
# Для кожного customer_id зібрати всі category куплених товарів за один день.
# Знайти найчастіші пари категорій, що купують разом (комбінації 2 категорій).
# Які топ-5 пар?
# Підказка: якщо same-day покупок мало — спробуйте згрупувати по customer_id + тиждень через .dt.isocalendar().week.
# Використайте itertools.combinations() для генерації пар категорій.
# Для підрахунку пар зручно застосувати value_counts() на серії пар або nunique() для перевірки кількості унікальних пар.

import pandas as pd
from itertools import combinations
from pathlib import Path

from cleaning import main as clean_data


ROOT = Path(__file__).resolve().parent
CLEAN_DIR = ROOT / "cleaned_data"


def run_market_basket_analysis():
    transactions_path = CLEAN_DIR / "transactions_cleaned.csv"
    excel_path = CLEAN_DIR / "company_data_cleaned.xlsx"

    if not transactions_path.exists() or not excel_path.exists():
        clean_data()

    df_trans = pd.read_csv(transactions_path)[['customer_id', 'transaction_date', 'product_id']]
    df_prod = pd.read_excel(excel_path, sheet_name="Products", usecols=['product_id', 'category'])

    df = pd.merge(df_trans, df_prod, on='product_id', how='inner')

    df['transaction_date'] = pd.to_datetime(df['transaction_date'])
    df['week'] = df['transaction_date'].dt.isocalendar().week

    grouped = df.groupby(['customer_id', 'week'])['category'].apply(set)

    all_pairs = []
    for categories in grouped:
        if len(categories) >= 2:
            sorted_cats = sorted(list(categories))
            all_pairs.extend(list(combinations(sorted_cats, 2)))

    pairs_series = pd.Series(all_pairs)
    top_5 = pairs_series.value_counts().head(5)

    print("Топ-5 пар категорій, що купують разом")
    print(top_5)


if __name__ == "__main__":
    run_market_basket_analysis()