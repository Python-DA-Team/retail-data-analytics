from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns


ROOT = Path(__file__).resolve().parent
CLEAN_DIR = ROOT / "cleaned_data"
RESULT_DIR = ROOT / "results" / "task_2_03"


def load_data() -> dict[str, pd.DataFrame]:
    paths = {
        "Customers": CLEAN_DIR / "customers_cleaned.csv",
        "Employees": CLEAN_DIR / "employees_cleaned.csv",
        "Marketing": CLEAN_DIR / "marketing_cleaned.csv",
        "Stores": CLEAN_DIR / "stores_cleaned.csv",
        "Returns": CLEAN_DIR / "returns_cleaned.csv",
    }

    if any(not path.exists() for path in paths.values()):
        from cleaning import main as clean_data

        clean_data()

    return {
        name: pd.read_csv(path, low_memory=False)
        for name, path in paths.items()
    }


def calculate_score(
    name: str,
    data: pd.DataFrame,
) -> dict[str, str | float]:
    if data.empty:
        raise ValueError(f"Файл {name} не містить даних")

    total_rows = len(data)
    completeness = data.notna().sum().sum() / data.size
    uniqueness = 1 - data.duplicated().sum() / total_rows

    if name == "Customers":
        age = pd.to_numeric(data["age"], errors="coerce")
        orders = pd.to_numeric(data["total_orders"], errors="coerce")
        lifetime_value = pd.to_numeric(data["lifetime_value"], errors="coerce")
        registration_date = pd.to_datetime(
            data["registration_date"], errors="coerce"
        )
        valid = data["customer_id"].notna() & age.between(0, 100)
        consistent = (
            orders.ge(0)
            & lifetime_value.ge(0)
            & registration_date.le(pd.Timestamp("2025-12-31"))
        )

    elif name == "Employees":
        salary = pd.to_numeric(data["salary"], errors="coerce")
        performance = pd.to_numeric(
            data["performance_score"], errors="coerce"
        )
        hire_date = pd.to_datetime(data["hire_date"], errors="coerce")
        valid = (
            data["employee_id"].notna()
            & data["store_id"].notna()
            & salary.gt(0)
        )
        consistent = (
            performance.between(0, 100)
            & hire_date.le(pd.Timestamp("2025-12-31"))
        )

    elif name == "Marketing":
        budget = pd.to_numeric(data["budget"], errors="coerce")
        impressions = pd.to_numeric(data["impressions"], errors="coerce")
        clicks = pd.to_numeric(data["clicks"], errors="coerce")
        conversions = pd.to_numeric(data["conversions"], errors="coerce")
        ctr = pd.to_numeric(data["ctr_pct"], errors="coerce")
        conversion_rate = pd.to_numeric(
            data["conversion_rate_pct"], errors="coerce"
        )
        start_date = pd.to_datetime(data["start_date"], errors="coerce")
        end_date = pd.to_datetime(data["end_date"], errors="coerce")
        valid = (
            data["campaign_id"].notna()
            & budget.ge(0)
            & impressions.ge(0)
            & clicks.ge(0)
            & conversions.ge(0)
        )
        consistent = (
            clicks.le(impressions)
            & conversions.le(clicks)
            & ctr.between(0, 100)
            & conversion_rate.between(0, 100)
            & end_date.ge(start_date)
        )

    elif name == "Stores":
        size = pd.to_numeric(data["size_sqm"], errors="coerce")
        open_date = pd.to_datetime(data["open_date"], errors="coerce")
        boolean_values = ["true", "false"]
        valid = data["store_id"].notna() & size.gt(0)
        consistent = (
            data["has_cafe"].astype(str).str.lower().isin(boolean_values)
            & data["has_parking"].astype(str).str.lower().isin(boolean_values)
            & open_date.le(pd.Timestamp("2025-12-31"))
        )

    else:
        quantity = pd.to_numeric(data["quantity"], errors="coerce")
        total_amount = pd.to_numeric(data["total_amount"], errors="coerce")
        refund_amount = pd.to_numeric(data["refund_amount"], errors="coerce")
        transaction_date = pd.to_datetime(
            data["transaction_date"], errors="coerce"
        )
        return_date = pd.to_datetime(data["return_date"], errors="coerce")
        valid = (
            data["transaction_id"].notna()
            & quantity.gt(0)
            & total_amount.lt(0)
            & refund_amount.ge(0)
        )
        consistent = (
            data["is_return"].eq(1)
            & refund_amount.le(total_amount.abs())
            & return_date.ge(transaction_date)
        )

    validity = valid.fillna(False).mean()
    consistency = consistent.fillna(False).mean()
    overall_score = (
        completeness + uniqueness + validity + consistency
    ) / 4

    return {
        "Файл": name,
        "Повнота (%)": round(completeness * 100, 2),
        "Унікальність (%)": round(uniqueness * 100, 2),
        "Валідність (%)": round(validity * 100, 2),
        "Узгодженість (%)": round(consistency * 100, 2),
        "Загальна оцінка (%)": round(overall_score * 100, 2),
    }


def save_results(report: pd.DataFrame) -> tuple[Path, Path]:
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    table_path = RESULT_DIR / "data_quality_score.csv"
    chart_path = RESULT_DIR / "data_quality_score.png"
    report.to_csv(table_path, index=False, encoding="utf-8-sig")

    metrics = [
        "Повнота (%)",
        "Унікальність (%)",
        "Валідність (%)",
        "Узгодженість (%)",
    ]
    chart_data = report.melt(
        id_vars="Файл",
        value_vars=metrics,
        var_name="Метрика",
        value_name="Оцінка",
    )

    sns.set_theme(style="whitegrid")
    plt.figure(figsize=(11, 6))
    sns.barplot(
        data=chart_data,
        x="Файл",
        y="Оцінка",
        hue="Метрика",
        palette="viridis",
    )
    plt.title("Data Quality Score очищених даних")
    plt.xlabel("Набір даних")
    plt.ylabel("Оцінка, %")
    plt.ylim(0, 105)
    plt.legend(title="Метрика", bbox_to_anchor=(1.02, 1), loc="upper left")
    plt.tight_layout()
    plt.savefig(chart_path, dpi=300)
    plt.close()
    return table_path, chart_path


def main() -> None:
    datasets = load_data()
    report = pd.DataFrame(
        [calculate_score(name, data) for name, data in datasets.items()]
    )

    best = report.loc[report["Загальна оцінка (%)"].idxmax()]
    worst = report.loc[report["Загальна оцінка (%)"].idxmin()]
    table_path, chart_path = save_results(report)

    print(report.to_string(index=False))
    print(
        f"\nНайвищий DQ Score: {best['Файл']} "
        f"({best['Загальна оцінка (%)']:.2f}%)"
    )
    print(
        f"Найнижчий DQ Score: {worst['Файл']} "
        f"({worst['Загальна оцінка (%)']:.2f}%)"
    )
    print(f"Таблицю збережено: {table_path}")
    print(f"Графік збережено: {chart_path}")


if __name__ == "__main__":
    main()
