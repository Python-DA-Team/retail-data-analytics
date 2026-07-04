from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


ROOT = Path(__file__).resolve().parent
CLEAN_DIR = ROOT / "cleaned_data"
RESULT_DIR = ROOT / "results" / "task_2_04"


def load_data():
    transactions_path = CLEAN_DIR / "transactions_cleaned.csv"
    company_path = CLEAN_DIR / "company_data_cleaned.xlsx"

    if not transactions_path.exists() or not company_path.exists():
        from cleaning import main as clean_data

        clean_data()

    transactions = pd.read_csv(transactions_path, low_memory=False)
    products = pd.read_excel(company_path, sheet_name="Products")
    return transactions, products


def calculate_monthly_results(transactions, products):
    sales = transactions.query("is_return == 0").copy()

    for column in ["product_id", "quantity", "total_amount"]:
        sales[column] = pd.to_numeric(sales[column], errors="coerce")

    sales["transaction_date"] = pd.to_datetime(
        sales["transaction_date"], errors="coerce"
    )
    sales = sales.dropna(
        subset=["product_id", "quantity", "total_amount", "transaction_date"]
    )
    sales = sales.loc[
        sales["quantity"].gt(0) & sales["total_amount"].gt(0)
    ]
    sales = sales.loc[sales["transaction_date"].dt.year.eq(2025)]
    sales["product_id"] = sales["product_id"].astype(int)
    sales["month"] = sales["transaction_date"].dt.month

    product_data = products[["product_id", "cost_price"]].drop_duplicates(
        "product_id"
    )
    product_data["cost_price"] = pd.to_numeric(
        product_data["cost_price"], errors="coerce"
    )
    product_data = product_data.dropna(subset=["cost_price"])
    product_data = product_data.loc[product_data["cost_price"].ge(0)]

    sales = sales.merge(product_data, on="product_id", how="inner")
    sales["revenue"] = sales["total_amount"]
    sales["cost"] = sales["quantity"] * sales["cost_price"]
    sales["profit"] = sales["revenue"] - sales["cost"]

    monthly = (
        sales.groupby("month", as_index=False)
        .agg(
            revenue=("revenue", "sum"),
            cost=("cost", "sum"),
            profit=("profit", "sum"),
        )
        .set_index("month")
        .reindex(range(1, 13), fill_value=0)
        .rename_axis("month")
        .reset_index()
    )
    monthly[["revenue", "cost", "profit"]] = monthly[
        ["revenue", "cost", "profit"]
    ].round(2)
    return monthly


def save_results(monthly):
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    table_path = RESULT_DIR / "monthly_revenue_cost_profit_2025.csv"
    chart_path = RESULT_DIR / "monthly_revenue_stacked_bar_2025.png"
    monthly.to_csv(table_path, index=False, encoding="utf-8-sig")

    month_names = [
        "Січ",
        "Лют",
        "Бер",
        "Квіт",
        "Трав",
        "Черв",
        "Лип",
        "Серп",
        "Вер",
        "Жовт",
        "Лист",
        "Груд",
    ]

    plt.figure(figsize=(11, 6))
    plt.bar(
        monthly["month"],
        monthly["cost"],
        label="Собівартість",
        color="#fc8d62",
    )
    plt.bar(
        monthly["month"],
        monthly["profit"],
        bottom=monthly["cost"],
        label="Валовий прибуток",
        color="#66c2a5",
    )
    plt.title("Структура виручки за місяцями 2025 року")
    plt.xlabel("Місяць")
    plt.ylabel("Сума")
    plt.xticks(range(1, 13), month_names)
    plt.ticklabel_format(style="plain", axis="y")
    plt.grid(axis="y", linestyle="--", alpha=0.4)
    plt.legend(title="Виручка = собівартість + прибуток")
    plt.tight_layout()
    plt.savefig(chart_path, dpi=300, bbox_inches="tight")
    plt.close()
    return table_path, chart_path


def main():
    transactions, products = load_data()
    monthly = calculate_monthly_results(transactions, products)

    if monthly["revenue"].sum() == 0:
        raise ValueError("Не знайдено продажів за 2025 рік")

    table_path, chart_path = save_results(monthly)
    print("Виручка, собівартість і валовий прибуток за 2025 рік:")
    print(monthly.to_string(index=False))
    print(f"Таблицю збережено: {table_path}")
    print(f"Графік збережено: {chart_path}")


if __name__ == "__main__":
    main()
