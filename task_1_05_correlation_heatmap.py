from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns


ROOT = Path(__file__).resolve().parent
CLEAN_DIR = ROOT / "cleaned_data"
RESULT_DIR = ROOT / "results" / "task_1_05"


def load_data():
    transactions_path = CLEAN_DIR / "transactions_cleaned.csv"
    company_path = CLEAN_DIR / "company_data_cleaned.xlsx"

    if not transactions_path.exists() or not company_path.exists():
        from cleaning import main as clean_data

        clean_data()

    transactions = pd.read_csv(transactions_path, low_memory=False)
    products = pd.read_excel(company_path, sheet_name="Products")
    return transactions, products


def calculate_correlation(transactions, products):
    sales = transactions.query("is_return == 0").copy()

    for column in ["product_id", "quantity", "total_amount"]:
        sales[column] = pd.to_numeric(sales[column], errors="coerce")

    sales = sales.dropna(
        subset=["product_id", "quantity", "total_amount"]
    )
    sales = sales.loc[
        sales["quantity"].gt(0) & sales["total_amount"].gt(0)
    ]
    sales["product_id"] = sales["product_id"].astype(int)

    product_columns = [
        "product_id",
        "unit_price",
        "cost_price",
        "margin_pct",
    ]
    product_data = products[product_columns].drop_duplicates("product_id")

    for column in ["unit_price", "cost_price", "margin_pct"]:
        product_data[column] = pd.to_numeric(
            product_data[column], errors="coerce"
        )

    merged = sales.merge(product_data, on="product_id", how="inner")
    correlation_columns = [
        "unit_price",
        "cost_price",
        "margin_pct",
        "quantity",
        "total_amount",
    ]
    correlation_data = merged[correlation_columns].dropna()

    if len(correlation_data) < 2:
        raise ValueError("Недостатньо даних для розрахунку кореляції")

    return correlation_data.corr().round(2)


def save_results(correlation):
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    table_path = RESULT_DIR / "correlation_matrix.csv"
    chart_path = RESULT_DIR / "correlation_heatmap.png"
    correlation.to_csv(table_path, encoding="utf-8-sig")

    sns.set_theme(style="white")
    plt.figure(figsize=(9, 6))
    sns.heatmap(
        correlation,
        annot=True,
        cmap="coolwarm",
        fmt=".2f",
        vmin=-1,
        vmax=1,
        linewidths=0.5,
    )
    plt.title("Матриця кореляції показників продажів")
    plt.tight_layout()
    plt.savefig(chart_path, dpi=300, bbox_inches="tight")
    plt.close()
    return table_path, chart_path


def main():
    transactions, products = load_data()
    correlation = calculate_correlation(transactions, products)
    table_path, chart_path = save_results(correlation)

    print("Матриця кореляції:")
    print(correlation.to_string())
    print(f"Таблицю збережено: {table_path}")
    print(f"Графік збережено: {chart_path}")


if __name__ == "__main__":
    main()
