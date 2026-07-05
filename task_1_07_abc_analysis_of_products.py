from pathlib import Path

import pandas as pd

from cleaning import main as clean_data


ROOT = Path(__file__).resolve().parent
CLEAN_DIR = ROOT / "cleaned_data"
RESULT_DIR = ROOT / "results" / "task_1_07"


def load_data():
    clean_data()

    transactions_path = CLEAN_DIR / "transactions_cleaned.csv"
    company_path = CLEAN_DIR / "company_data_cleaned.xlsx"

    transactions = pd.read_csv(transactions_path, low_memory=False)
    products = pd.read_excel(company_path, sheet_name="Products")
    return transactions, products


def assign_abc_group(cum_share_pct):
    if cum_share_pct <= 70:
        return "A"
    if cum_share_pct <= 90:
        return "B"
    return "C"


def calculate_abc_analysis(transactions, products):
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
    result = result.sort_values("total_revenue", ascending=False).reset_index(drop=True)

    total_revenue = result["total_revenue"].sum()
    result["revenue_share_pct"] = result["total_revenue"] / total_revenue * 100
    result["cum_share_pct"] = result["revenue_share_pct"].cumsum()
    result["abc_group"] = result["cum_share_pct"].apply(assign_abc_group)

    value_columns = ["total_revenue", "revenue_share_pct", "cum_share_pct"]
    result[value_columns] = result[value_columns].round(2)
    return result


def calculate_group_summary(abc_result):
    summary = (
        abc_result.groupby("abc_group", as_index=False)
        .agg(
            products_count=("product_id", "count"),
            total_revenue=("total_revenue", "sum"),
            revenue_share_pct=("revenue_share_pct", "sum"),
        )
        .sort_values("abc_group")
    )
    summary[["total_revenue", "revenue_share_pct"]] = summary[
        ["total_revenue", "revenue_share_pct"]
    ].round(2)
    return summary


def save_results(abc_result, summary):
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    products_path = RESULT_DIR / "abc_analysis_of_products.csv"
    summary_path = RESULT_DIR / "abc_group_summary.csv"

    abc_result.to_csv(products_path, index=False, encoding="utf-8-sig")
    summary.to_csv(summary_path, index=False, encoding="utf-8-sig")
    return products_path, summary_path


def main():
    transactions, products = load_data()
    abc_result = calculate_abc_analysis(transactions, products)

    if abc_result.empty:
        raise ValueError("Не знайдено продажів для ABC-аналізу товарів")

    summary = calculate_group_summary(abc_result)
    products_path, summary_path = save_results(abc_result, summary)

    print("Кількість товарів у групах ABC:")
    print(summary.to_string(index=False))
    print("\nТоп-10 товарів за виручкою:")
    print(
        abc_result[
            [
                "product_id",
                "product_name",
                "category",
                "total_revenue",
                "cum_share_pct",
                "abc_group",
            ]
        ]
        .head(10)
        .to_string(index=False)
    )
    print(f"Таблицю ABC-аналізу збережено: {products_path}")
    print(f"Зведену таблицю збережено: {summary_path}")


if __name__ == "__main__":
    main()
