# Блок 1. Завдання 8.
# Market Basket Analysis. Для кожного customer_id зібрати всі category куплених товарів за один день.
# Знайти найчастіші пари категорій, що купують разом (комбінації 2 категорій).
# Які топ-5 пар?

from itertools import combinations
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent
CLEAN_DIR = ROOT / "cleaned_data"
RESULT_DIR = ROOT / "results" / "task_1_08_market_basket_analysis"


def load_data():
    transactions_path = CLEAN_DIR / "transactions_cleaned.csv"
    company_path = CLEAN_DIR / "company_data_cleaned.xlsx"

    if not transactions_path.exists() or not company_path.exists():
        from cleaning import main as clean_data
        clean_data()

    df_trans = pd.read_csv(transactions_path, low_memory=False)
    df_prod = pd.read_excel(company_path, sheet_name="Products")

    return df_trans, df_prod


def run_market_basket_analysis():
    df_trans, df_prod = load_data()

    df_trans = df_trans[["customer_id", "transaction_date", "product_id"]].copy()
    df_prod = df_prod[["product_id", "category"]].copy()

    df = pd.merge(df_trans, df_prod, on="product_id", how="inner")

    df["transaction_date"] = pd.to_datetime(df["transaction_date"])
    df["week"] = df["transaction_date"].dt.isocalendar().week

    grouped = df.groupby(["customer_id", "week"])["category"].apply(set)

    all_pairs = []

    for categories in grouped:
        if len(categories) >= 2:
            sorted_cats = sorted(list(categories))
            all_pairs.extend(list(combinations(sorted_cats, 2)))

    pairs_series = pd.Series(all_pairs)
    top_5 = pairs_series.value_counts().head(5)

    result = top_5.reset_index()
    result.columns = ["category_pair", "basket_count"]
    result["category_1"] = result["category_pair"].str[0]
    result["category_2"] = result["category_pair"].str[1]
    result = result[["category_1", "category_2", "basket_count"]]

    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = RESULT_DIR / "top_5_category_pairs.csv"
    result.to_csv(output_path, index=False, encoding="utf-8-sig")

    print("Топ-5 пар категорій, що купують разом")
    print(result.to_string(index=False))
    print(f"Таблицю збережено: {output_path}")


if __name__ == "__main__":
    run_market_basket_analysis()