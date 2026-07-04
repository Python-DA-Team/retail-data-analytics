from itertools import combinations
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent
CLEAN_DIR = ROOT / "cleaned_data"
RESULT_DIR = ROOT / "results" / "task_1_08"


def load_data():
    transactions_path = CLEAN_DIR / "transactions_cleaned.csv"
    company_path = CLEAN_DIR / "company_data_cleaned.xlsx"

    if not transactions_path.exists() or not company_path.exists():
        from cleaning import main as clean_data
        clean_data()

    transactions = pd.read_csv(transactions_path, low_memory=False)
    products = pd.read_excel(company_path, sheet_name="Products")
    return transactions, products


def prepare_sales(transactions, products):
    sales = transactions.loc[transactions["is_return"].eq(0)].copy()
    sales["transaction_date"] = pd.to_datetime(
        sales["transaction_date"], errors="coerce"
    )
    sales["customer_id"] = pd.to_numeric(sales["customer_id"], errors="coerce")
    sales["product_id"] = pd.to_numeric(sales["product_id"], errors="coerce")
    sales = sales.dropna(subset=["customer_id", "product_id", "transaction_date"])
    sales["customer_id"] = sales["customer_id"].astype(int)
    sales["product_id"] = sales["product_id"].astype(int)
    sales["purchase_date"] = sales["transaction_date"].dt.normalize()

    product_categories = products[["product_id", "category"]].drop_duplicates()
    sales = sales.merge(product_categories, on="product_id", how="inner")
    return sales.dropna(subset=["category"])


def calculate_top_pairs(sales, top_n=5):
    baskets = sales.groupby(["customer_id", "purchase_date"])["category"].apply(set)

    all_pairs = []
    for categories in baskets:
        if len(categories) >= 2:
            sorted_categories = sorted(categories)
            all_pairs.extend(combinations(sorted_categories, 2))

    if not all_pairs:
        return pd.DataFrame(columns=["category_1", "category_2", "basket_count"])

    pair_counts = pd.Series(all_pairs).value_counts().head(top_n).reset_index()
    pair_counts.columns = ["category_pair", "basket_count"]
    pair_counts["category_1"] = pair_counts["category_pair"].str[0]
    pair_counts["category_2"] = pair_counts["category_pair"].str[1]
    return pair_counts[["category_1", "category_2", "basket_count"]]


def save_results(result):
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = RESULT_DIR / "top_5_category_pairs.csv"
    result.to_csv(output_path, index=False, encoding="utf-8-sig")
    return output_path


def main():
    transactions, products = load_data()
    sales = prepare_sales(transactions, products)
    result = calculate_top_pairs(sales)

    if result.empty:
        raise ValueError("Не знайдено покупок з двома або більше категоріями за день")

    output_path = save_results(result)
    print("Топ-5 пар категорій, які купують разом за один день:")
    print(result.to_string(index=False))
    print(f"Таблицю збережено: {output_path}")


if __name__ == "__main__":
    main()
