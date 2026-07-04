from pathlib import Path

import pandas as pd

from cleaning import main as clean_data


ROOT = Path(__file__).resolve().parent
CLEAN_DIR = ROOT / "cleaned_data"
RESULT_DIR = ROOT / "results" / "task_1_02"


def load_data():
    clean_data()

    transactions_path = CLEAN_DIR / "transactions_cleaned.csv"
    company_path = CLEAN_DIR / "company_data_cleaned.xlsx"

    transactions = pd.read_csv(transactions_path, low_memory=False)
    products = pd.read_excel(company_path, sheet_name="Products")
    return transactions, products


def calculate_revenue_pivot(transactions, products):
    sales = transactions.loc[transactions["is_return"].eq(0)].copy()
    sales["transaction_date"] = pd.to_datetime(
        sales["transaction_date"], errors="coerce"
    )
    sales["product_id"] = pd.to_numeric(sales["product_id"], errors="coerce")
    sales["total_amount"] = pd.to_numeric(sales["total_amount"], errors="coerce")
    sales = sales.dropna(
        subset=["transaction_date", "product_id", "total_amount"]
    )
    sales = sales.loc[sales["total_amount"].gt(0)]
    sales["product_id"] = sales["product_id"].astype(int)
    sales["month"] = sales["transaction_date"].dt.to_period("M").astype(str)

    products_clean = products[["product_id", "category"]].drop_duplicates()
    merged = sales.merge(products_clean, on="product_id", how="inner")
    merged = merged.dropna(subset=["category"])

    pivot = pd.pivot_table(
        merged,
        values="total_amount",
        index="category",
        columns="month",
        aggfunc="sum",
        fill_value=0,
    )
    pivot = pivot.sort_index(axis=1).round(2)
    return pivot


def calculate_monthly_leaders(pivot):
    leaders = pivot.idxmax()
    leaders_table = pd.DataFrame(
        {
            "month": leaders.index,
            "leader_category": leaders.values,
            "revenue": pivot.max().values,
        }
    )
    leaders_table["revenue"] = leaders_table["revenue"].round(2)
    return leaders_table


def save_results(pivot, leaders_table):
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    pivot_path = RESULT_DIR / "revenue_pivot_by_category.csv"
    leaders_path = RESULT_DIR / "monthly_category_leaders.csv"

    pivot.to_csv(pivot_path, encoding="utf-8-sig")
    leaders_table.to_csv(leaders_path, index=False, encoding="utf-8-sig")
    return pivot_path, leaders_path


def main():
    transactions, products = load_data()
    pivot = calculate_revenue_pivot(transactions, products)

    if pivot.empty:
        raise ValueError("Не знайдено продажів для розрахунку виручки")

    leaders_table = calculate_monthly_leaders(pivot)
    pivot_path, leaders_path = save_results(pivot, leaders_table)

    print("Виручка по категоріях і місяцях:")
    print(pivot.to_string())
    print("\nКатегорія-лідер за кожен місяць:")
    print(leaders_table.to_string(index=False))
    print(f"Pivot-таблицю збережено: {pivot_path}")
    print(f"Таблицю лідерів збережено: {leaders_path}")


if __name__ == "__main__":
    main()
