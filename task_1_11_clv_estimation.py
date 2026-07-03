from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns


ROOT = Path(__file__).resolve().parent
CLEAN_DIR = ROOT / "cleaned_data"
RESULT_DIR = ROOT / "results" / "task_11"


def load_transactions() -> pd.DataFrame:
    path = CLEAN_DIR / "transactions_cleaned.csv"
    if not path.exists():
        from cleaning import main as clean_data
        clean_data()

    transactions = pd.read_csv(path, low_memory=False)
    transactions["transaction_date"] = pd.to_datetime(
        transactions["transaction_date"], errors="coerce"
    )
    return transactions


def prepare_sales(transactions: pd.DataFrame) -> pd.DataFrame:
    sales = transactions.loc[
        transactions["is_return"].eq(0)
        & transactions["transaction_date"].between("2024-01-01", "2025-12-31 23:59:59")
    ].copy()

    sales["customer_id"] = pd.to_numeric(sales["customer_id"], errors="coerce")
    sales["total_amount"] = pd.to_numeric(sales["total_amount"], errors="coerce")
    sales = sales.dropna(subset=["customer_id", "transaction_id", "transaction_date", "total_amount"])
    sales = sales.loc[sales["total_amount"].gt(0)]
    sales["customer_id"] = sales["customer_id"].astype("int64")
    sales["month"] = sales["transaction_date"].dt.to_period("M")
    return sales


def calculate_monthly_metrics(sales: pd.DataFrame) -> pd.DataFrame:
    monthly = sales.groupby("month").agg(
        revenue=("total_amount", "sum"),
        customers=("customer_id", "nunique"),
        purchases=("transaction_id", "nunique"),
    )
    monthly["arpu"] = monthly["revenue"] / monthly["customers"]
    monthly["purchase_frequency"] = monthly["purchases"] / monthly["customers"]
    monthly.index = monthly.index.astype(str)
    return monthly.round(2)


def calculate_customer_clv(sales: pd.DataFrame) -> pd.DataFrame:
    customers = sales.groupby("customer_id").agg(
        first_purchase=("transaction_date", "min"),
        last_purchase=("transaction_date", "max"),
        total_revenue=("total_amount", "sum"),
        purchases=("transaction_id", "nunique"),
        active_months=("month", "nunique"),
    )

    first_month = customers["first_purchase"].dt.to_period("M")
    last_month = customers["last_purchase"].dt.to_period("M")
    customers["lifetime_months"] = (
        (last_month.dt.year - first_month.dt.year) * 12
        + last_month.dt.month
        - first_month.dt.month
        + 1
    )

    customers["arpu_month"] = customers["total_revenue"] / customers["lifetime_months"]
    customers["purchase_frequency_month"] = customers["purchases"] / customers["lifetime_months"]
    customers["clv"] = (
        customers["arpu_month"]
        * customers["purchase_frequency_month"]
        * customers["lifetime_months"]
    )

    labels = ["Low", "Medium", "High", "Premium"]
    customers["clv_segment"] = pd.qcut(
        customers["clv"].rank(method="first"),
        q=4,
        labels=labels,
    )
    return customers.reset_index().round({
        "total_revenue": 2,
        "arpu_month": 2,
        "purchase_frequency_month": 2,
        "clv": 2,
    })


def build_summary(
    monthly: pd.DataFrame,
    customers: pd.DataFrame,
) -> pd.DataFrame:
    return pd.DataFrame({
        "metric": [
            "Average monthly ARPU",
            "Average monthly purchase frequency",
            "Average customer lifetime, months",
            "Average estimated CLV",
            "Median estimated CLV",
        ],
        "value": [
            monthly["arpu"].mean(),
            monthly["purchase_frequency"].mean(),
            customers["lifetime_months"].mean(),
            customers["clv"].mean(),
            customers["clv"].median(),
        ],
    }).round(2)


def save_results(
    monthly: pd.DataFrame,
    customers: pd.DataFrame,
    summary: pd.DataFrame,
) -> None:
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    monthly.to_csv(RESULT_DIR / "monthly_clv_metrics.csv", encoding="utf-8-sig")
    customers.to_csv(RESULT_DIR / "customer_clv_segments.csv", index=False, encoding="utf-8-sig")
    summary.to_csv(RESULT_DIR / "clv_summary.csv", index=False, encoding="utf-8-sig")

    order = ["Low", "Medium", "High", "Premium"]
    segment_stats = customers.groupby("clv_segment", observed=False).agg(
        customers=("customer_id", "count"),
        average_clv=("clv", "mean"),
    ).reindex(order)

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    sns.barplot(
        data=segment_stats.reset_index(),
        x="clv_segment",
        y="customers",
        hue="clv_segment",
        order=order,
        palette="Blues_d",
        legend=False,
        ax=axes[0],
    )
    axes[0].set_title("Кількість клієнтів за CLV-сегментами")
    axes[0].set_xlabel("CLV-сегмент")
    axes[0].set_ylabel("Кількість клієнтів")

    sns.barplot(
        data=segment_stats.reset_index(),
        x="clv_segment",
        y="average_clv",
        hue="clv_segment",
        order=order,
        palette="YlGnBu",
        legend=False,
        ax=axes[1],
    )
    axes[1].set_title("Середній CLV за сегментами")
    axes[1].set_xlabel("CLV-сегмент")
    axes[1].set_ylabel("CLV")

    plt.tight_layout()
    plt.savefig(RESULT_DIR / "clv_segments.png", dpi=180, bbox_inches="tight")
    plt.close()


def main() -> None:
    transactions = load_transactions()
    sales = prepare_sales(transactions)
    monthly = calculate_monthly_metrics(sales)
    customers = calculate_customer_clv(sales)
    summary = build_summary(monthly, customers)
    save_results(monthly, customers, summary)

    print("Monthly metrics")
    print(monthly.to_string())
    print("\nCLV summary")
    print(summary.to_string(index=False))
    print("\nCLV segments")
    print(customers["clv_segment"].value_counts().reindex(
        ["Low", "Medium", "High", "Premium"]
    ).to_string())
    print(f"\nРезультати збережено у: {RESULT_DIR}")


if __name__ == "__main__":
    main()
