from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent
CLEAN_DIR = ROOT / "cleaned_data"
RESULT_DIR = ROOT / "results" / "task_1_01"


def load_data():
    transactions_path = CLEAN_DIR / "transactions_cleaned.csv"
    company_path = CLEAN_DIR / "company_data_cleaned.xlsx"

    if not transactions_path.exists() or not company_path.exists():
        from cleaning import main as clean_data
        clean_data()

    transactions = pd.read_csv(transactions_path, low_memory=False)
    products = pd.read_excel(company_path, sheet_name="Products")
    return transactions, products


def calculate_top_products(transactions, products, top_n=10):
    sales = transactions.loc[transactions["is_return"].eq(0)].copy()
    sales["product_id"] = pd.to_numeric(sales["product_id"], errors="coerce")
    sales["total_amount"] = pd.to_numeric(sales["total_amount"], errors="coerce")
    sales = sales.dropna(subset=["product_id", "total_amount"])
    sales = sales.loc[sales["total_amount"].gt(0)]
    sales["product_id"] = sales["product_id"].astype(int)

    revenue = (
        sales.groupby("product_id", as_index=False)["total_amount"]
        .sum()
        .rename(columns={"total_amount": "total_revenue"})
    )

    product_columns = ["product_id", "product_name", "category"]
    product_info = products[product_columns].drop_duplicates(subset="product_id")
    result = revenue.merge(product_info, on="product_id", how="inner")
    result = result.sort_values("total_revenue", ascending=False).head(top_n)
    result["total_revenue"] = result["total_revenue"].round(2)
    return result[
        ["product_id", "product_name", "category", "total_revenue"]
    ].reset_index(drop=True)


def save_results(result):
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = RESULT_DIR / "top_10_products_by_revenue.csv"
    result.to_csv(output_path, index=False, encoding="utf-8-sig")
    return output_path


def main():
    transactions, products = load_data()
    result = calculate_top_products(transactions, products)

    if result.empty:
        raise ValueError("Не знайдено продажів для розрахунку виручки за товарами")

    output_path = save_results(result)
    print("Топ-10 товарів за виручкою:")
    print(result.to_string(index=False))
    print(f"Таблицю збережено: {output_path}")


if __name__ == "__main__":
    main()
