from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent
CLEAN_DIR = ROOT / "cleaned_data"
RESULT_DIR = ROOT / "results" / "task_1_09"


def load_data():
    transactions_path = CLEAN_DIR / "transactions_cleaned.csv"

    if not transactions_path.exists():
        from cleaning import main as clean_data
        clean_data()

    return pd.read_csv(transactions_path, low_memory=False)


def calculate_discount_metrics(transactions):
    sales = transactions.loc[transactions["is_return"].eq(0)].copy()

    numeric_columns = ["quantity", "total_amount", "discount_percent"]
    for column in numeric_columns:
        sales[column] = pd.to_numeric(sales[column], errors="coerce")

    sales = sales.dropna(subset=numeric_columns)
    sales = sales.loc[
        sales["quantity"].gt(0)
        & sales["total_amount"].gt(0)
        & sales["discount_percent"].between(0, 100)
    ].copy()

    sales["discount_group"] = "Без знижки"
    sales.loc[sales["discount_percent"].gt(0), "discount_group"] = "Зі знижкою"

    result = (
        sales.groupby("discount_group", as_index=False)
        .agg(
            sales_count=("transaction_id", "count"),
            average_quantity=("quantity", "mean"),
            average_revenue=("total_amount", "mean"),
            total_revenue=("total_amount", "sum"),
        )
    )

    group_order = ["Без знижки", "Зі знижкою"]
    result["discount_group"] = pd.Categorical(
        result["discount_group"], categories=group_order, ordered=True
    )
    result = result.sort_values("discount_group").reset_index(drop=True)
    result["discount_group"] = result["discount_group"].astype("string")
    result[["average_quantity", "average_revenue", "total_revenue"]] = result[
        ["average_quantity", "average_revenue", "total_revenue"]
    ].round(2)
    return result


def save_results(result):
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = RESULT_DIR / "discount_comparison.csv"
    result.to_csv(output_path, index=False, encoding="utf-8-sig")
    return output_path


def print_conclusion(result):
    comparison = result.set_index("discount_group")
    no_discount = comparison.loc["Без знижки"]
    with_discount = comparison.loc["Зі знижкою"]

    quantity_change = (
        with_discount["average_quantity"] / no_discount["average_quantity"] - 1
    ) * 100
    revenue_change = (
        with_discount["average_revenue"] / no_discount["average_revenue"] - 1
    ) * 100

    print(
        f"Зміна середньої кількості товарів зі знижкою: "
        f"{quantity_change:+.2f}%"
    )
    print(f"Зміна середньої виручки зі знижкою: {revenue_change:+.2f}%")

    if quantity_change > 0 and revenue_change > 0:
        print("Висновок: продажі зі знижкою мають вищі середні показники.")
    elif quantity_change > 0:
        print(
            "Висновок: знижки пов'язані з більшою кількістю товарів, "
            "але не з вищою середньою виручкою."
        )
    else:
        print("Висновок: знижки не підвищують середню кількість товарів у продажу.")


def main():
    transactions = load_data()
    result = calculate_discount_metrics(transactions)

    required_groups = {"Без знижки", "Зі знижкою"}
    if set(result["discount_group"]) != required_groups:
        raise ValueError("Недостатньо даних для порівняння груп зі знижкою та без неї")

    output_path = save_results(result)
    print(result.to_string(index=False))
    print_conclusion(result)
    print(f"Таблицю збережено: {output_path}")


if __name__ == "__main__":
    main()
