from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent
CLEAN_DIR = ROOT / "cleaned_data"
RESULT_DIR = ROOT / "results" / "task_2_01"


def load_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    transactions_path = CLEAN_DIR / "transactions_cleaned.csv"
    company_path = CLEAN_DIR / "company_data_cleaned.xlsx"

    if not transactions_path.exists() or not company_path.exists():
        from cleaning import main as clean_data
        clean_data()

    transactions = pd.read_csv(transactions_path, low_memory=False)
    products = pd.read_excel(company_path, sheet_name="Products")
    stores = pd.read_excel(company_path, sheet_name="Stores")
    return transactions, products, stores


def prepare_sales(
    transactions: pd.DataFrame,
    products: pd.DataFrame,
    stores: pd.DataFrame,
) -> pd.DataFrame:
    sales = transactions.query("is_return == 0").copy()

    numeric_columns = ["product_id", "store_id", "quantity", "total_amount"]
    for column in numeric_columns:
        sales[column] = pd.to_numeric(sales[column], errors="coerce")

    sales["transaction_date"] = pd.to_datetime(
        sales["transaction_date"], errors="coerce"
    )
    sales = sales.dropna(
        subset=[
            "product_id",
            "store_id",
            "quantity",
            "total_amount",
            "transaction_date",
        ]
    )
    sales = sales.loc[sales["quantity"].gt(0) & sales["total_amount"].gt(0)]
    sales[["product_id", "store_id"]] = sales[["product_id", "store_id"]].astype(
        "int64"
    )

    sales = sales.merge(
        products[["product_id", "product_name", "category", "cost_price"]],
        on="product_id",
        how="inner",
        validate="many_to_one",
    )
    sales = sales.merge(
        stores[["store_id", "store_name", "store_format"]],
        on="store_id",
        how="inner",
        validate="many_to_one",
    )

    sales["cost_price"] = pd.to_numeric(sales["cost_price"], errors="coerce")
    sales = sales.dropna(subset=["cost_price"])
    sales = sales.loc[sales["cost_price"].ge(0)]

    sales["revenue"] = sales["total_amount"]
    sales["total_cost"] = sales["quantity"] * sales["cost_price"]
    sales["operating_expenses"] = sales["revenue"] * 0.05
    sales["profit"] = (
        sales["revenue"] - sales["total_cost"] - sales["operating_expenses"]
    )
    sales["month"] = sales["transaction_date"].dt.to_period("M")
    return sales


def calculate_monthly_profit(sales: pd.DataFrame) -> pd.DataFrame:
    monthly = (
        sales.groupby("month", as_index=False)
        .agg(
            total_revenue=("revenue", "sum"),
            total_cost=("total_cost", "sum"),
            operating_expenses=("operating_expenses", "sum"),
            total_profit=("profit", "sum"),
        )
        .sort_values("month")
    )
    monthly["margin_pct"] = (
        monthly["total_profit"] / monthly["total_revenue"] * 100
    )
    monthly["month"] = monthly["month"].astype(str)

    value_columns = [
        "total_revenue",
        "total_cost",
        "operating_expenses",
        "total_profit",
        "margin_pct",
    ]
    monthly[value_columns] = monthly[value_columns].round(2)
    return monthly


def save_results(monthly: pd.DataFrame) -> Path:
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = RESULT_DIR / "monthly_profit_analysis.csv"
    monthly.to_csv(output_path, index=False, encoding="utf-8-sig")
    return output_path


def main() -> None:
    transactions, products, stores = load_data()
    sales = prepare_sales(transactions, products, stores)
    monthly = calculate_monthly_profit(sales)

    if monthly.empty:
        raise ValueError("Не знайдено даних для розрахунку прибутку")

    best_month = monthly.loc[monthly["total_profit"].idxmax()]
    worst_month = monthly.loc[monthly["total_profit"].idxmin()]
    output_path = save_results(monthly)

    print(
        f"Найприбутковіший місяць: {best_month['month']}, "
        f"прибуток = {best_month['total_profit']:.2f}"
    )
    print(
        f"Місяць з найнижчим прибутком: {worst_month['month']}, "
        f"прибуток = {worst_month['total_profit']:.2f}"
    )
    if worst_month["total_profit"] < 0:
        print("Цей місяць був збитковим.")
    else:
        print("Збиткових місяців немає.")
    print(f"Таблицю збережено: {output_path}")


if __name__ == "__main__":
    main()
