from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns


ROOT = Path(__file__).resolve().parent
CLEAN_DIR = ROOT / "cleaned_data"
RESULT_DIR = ROOT / "results" / "task_1_06"


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

    product_data = products[["product_id", "category"]].drop_duplicates(
        "product_id"
    )
    sales = sales.merge(product_data, on="product_id", how="inner")
    sales = sales.dropna(subset=["category"])
    return sales


def calculate_summary(sales):
    summary = (
        sales.groupby("category", as_index=False)
        .agg(
            sales_count=("total_amount", "count"),
            average_amount=("total_amount", "mean"),
            median_amount=("total_amount", "median"),
            minimum_amount=("total_amount", "min"),
            maximum_amount=("total_amount", "max"),
        )
        .sort_values("median_amount", ascending=False)
    )
    numeric_columns = [
        "average_amount",
        "median_amount",
        "minimum_amount",
        "maximum_amount",
    ]
    summary[numeric_columns] = summary[numeric_columns].round(2)
    return summary


def save_results(sales, summary):
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    table_path = RESULT_DIR / "sales_distribution_by_category.csv"
    boxplot_path = RESULT_DIR / "sales_boxplot.png"
    violinplot_path = RESULT_DIR / "sales_violinplot.png"
    kdeplot_path = RESULT_DIR / "sales_kdeplot.png"
    summary.to_csv(table_path, index=False, encoding="utf-8-sig")

    sns.set_theme(style="whitegrid")

    plt.figure(figsize=(11, 6))
    sns.boxplot(
        data=sales,
        x="category",
        y="total_amount",
        hue="category",
        legend=False,
        palette="Set3",
        showfliers=True,
    )
    plt.title("Розподіл суми продажів за категоріями: boxplot")
    plt.xlabel("Категорія")
    plt.ylabel("Сума продажу")
    plt.xticks(rotation=30, ha="right")
    plt.tight_layout()
    plt.savefig(boxplot_path, dpi=300, bbox_inches="tight")
    plt.close()

    plt.figure(figsize=(11, 6))
    sns.violinplot(
        data=sales,
        x="category",
        y="total_amount",
        hue="category",
        legend=False,
        palette="Set3",
        cut=0,
    )
    plt.title("Розподіл суми продажів за категоріями: violinplot")
    plt.xlabel("Категорія")
    plt.ylabel("Сума продажу")
    plt.xticks(rotation=30, ha="right")
    plt.tight_layout()
    plt.savefig(violinplot_path, dpi=300, bbox_inches="tight")
    plt.close()

    plt.figure(figsize=(11, 6))
    sns.kdeplot(
        data=sales,
        x="total_amount",
        hue="category",
        fill=True,
        alpha=0.3,
        common_norm=False,
        palette="Set1",
    )
    plt.title("Щільність розподілу суми продажів за категоріями")
    plt.xlabel("Сума продажу")
    plt.ylabel("Щільність")
    plt.tight_layout()
    plt.savefig(kdeplot_path, dpi=300, bbox_inches="tight")
    plt.close()

    return table_path, boxplot_path, violinplot_path, kdeplot_path


def main():
    transactions, products = load_data()
    sales = prepare_sales(transactions, products)

    if sales.empty:
        raise ValueError("Не знайдено продажів для побудови графіків")

    summary = calculate_summary(sales)
    output_paths = save_results(sales, summary)

    print("Розподіл суми продажів за категоріями:")
    print(summary.to_string(index=False))
    for path in output_paths:
        print(f"Збережено: {path}")


if __name__ == "__main__":
    main()
