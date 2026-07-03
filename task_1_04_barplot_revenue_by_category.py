from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns


ROOT = Path(__file__).resolve().parent
CLEAN_DIR = ROOT / "cleaned_data"
RESULT_DIR = ROOT / "results" / "task_1_04"


def load_data():
    transactions_path = CLEAN_DIR / "transactions_cleaned.csv"
    company_path = CLEAN_DIR / "company_data_cleaned.xlsx"

    if not transactions_path.exists() or not company_path.exists():
        from cleaning import main as clean_data
        clean_data()

    transactions = pd.read_csv(transactions_path, low_memory=False)
    products = pd.read_excel(company_path, sheet_name="Products")
    return transactions, products


def calculate_revenue(transactions, products):
    sales = transactions.query("is_return == 0").copy()
    sales["transaction_date"] = pd.to_datetime(
        sales["transaction_date"], errors="coerce"
    )
    sales["total_amount"] = pd.to_numeric(
        sales["total_amount"], errors="coerce"
    )
    sales["product_id"] = pd.to_numeric(
        sales["product_id"], errors="coerce"
    )
    sales = sales.dropna(
        subset=["transaction_date", "total_amount", "product_id"]
    )
    sales = sales[sales["total_amount"] > 0]
    sales["product_id"] = sales["product_id"].astype(int)
    sales["year"] = sales["transaction_date"].dt.year
    sales = sales[sales["year"].isin([2024, 2025])]

    products_clean = products[["product_id", "category"]].drop_duplicates()
    merged = sales.merge(products_clean, on="product_id", how="left")
    merged = merged.dropna(subset=["category"])

    revenue = (
        merged.groupby(["category", "year"], as_index=False)["total_amount"]
        .sum()
        .rename(columns={"total_amount": "revenue"})
    )
    revenue["revenue"] = revenue["revenue"].round(2)
    return revenue


def save_results(revenue):
    RESULT_DIR.mkdir(parents=True, exist_ok=True)

    table_path = RESULT_DIR / "revenue_by_category_2024_2025.csv"
    chart_path = RESULT_DIR / "revenue_by_category_2024_2025.png"
    revenue.to_csv(table_path, index=False, encoding="utf-8-sig")

    sns.set_theme(style="whitegrid")
    plt.figure(figsize=(12, 6))
    sns.barplot(
        data=revenue,
        x="category",
        y="revenue",
        hue="year",
        hue_order=[2024, 2025],
        palette="Set2",
    )
    plt.title("Виручка по категоріях за 2024 та 2025 роки", fontsize=16)
    plt.xlabel("Категорія товару", fontsize=12)
    plt.ylabel("Загальна виручка", fontsize=12)
    plt.ticklabel_format(style="plain", axis="y")
    plt.xticks(rotation=30, ha="right")
    plt.legend(title="Рік")
    plt.tight_layout()
    plt.savefig(chart_path, dpi=300, bbox_inches="tight")
    plt.close()

    return table_path, chart_path


def main():
    transactions, products = load_data()
    revenue = calculate_revenue(transactions, products)

    if revenue.empty:
        raise ValueError("Не знайдено даних для побудови графіка")

    table_path, chart_path = save_results(revenue)
    print(revenue.to_string(index=False))
    print(f"Таблицю збережено: {table_path}")
    print(f"Графік збережено: {chart_path}")


if __name__ == "__main__":
    main()
