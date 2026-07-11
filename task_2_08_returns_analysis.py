from __future__ import annotations

import os
from itertools import combinations
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from cleaning import main as run_cleaning


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "cleaned_data"
CLEANED_FILES = [
    "company_data_cleaned.xlsx",
    "customers_cleaned.csv",
    "employees_cleaned.csv",
    "stores_cleaned.csv",
    "marketing_cleaned.csv",
    "returns_cleaned.csv",
    "salaries_cleaned.csv",
    "transactions_cleaned.csv",
    "support_tickets_cleaned.tsv",
]


def cleaned_data_exists() -> bool:
    return OUT.exists() and all((OUT / filename).exists() for filename in CLEANED_FILES)


def clean_data() -> None:
    if not cleaned_data_exists():
        run_cleaning()


# задание 2_08
# Завдання 8. Блок 2.
# Returns Analysis. З returns.csv (окремий файл з деталями повернень) та transactions.csv (де is_return == 1):
# Rate of returns by category (returns / total transactions) — використайте merge з Products для отримання категорії
# Average refund amount by reason (return_reason з returns.csv). Яка причина найдорожча?
# Чи корелює discount_percent із ймовірністю повернення? Порівняти середній discount для returns vs non-returns
# Чи відрізняється return rate по payment_method?
# Який середній час між покупкою та поверненням (return_date - transaction_date)?
# Конфігурація відображення
pd.set_option("display.max_columns", None)
pd.set_option("display.width", 1000)

DATA_DIR = OUT
FILES = {
    "transactions": DATA_DIR / "transactions_cleaned.csv",
    "returns": DATA_DIR / "returns_cleaned.csv",
    "products": DATA_DIR / "company_data_cleaned.xlsx"
}


def analyze_return_rate_by_category(transactions, returns, products):

    for name, path in FILES.items():
        if not path.exists():
            print(f"Помилка: Файл {path} не знайдено!")
            return None

    transactions = pd.read_csv(FILES["transactions"])
    returns = pd.read_csv(FILES["returns"])
    products = pd.read_excel(FILES["products"], sheet_name="Products")

    total_tx = transactions.groupby("product_id").size().reset_index(name="total_transactions")
    total_returns = returns.groupby("product_id").size().reset_index(name="total_returns")

    data = pd.merge(total_tx, total_returns, on="product_id", how="left").fillna(0)
    data = pd.merge(data, products[["product_id", "category"]], on="product_id", how="left")

    cat_stats = data.groupby("category").agg({"total_transactions": "sum", "total_returns": "sum"})
    cat_stats["return_rate_pct"] = (cat_stats["total_returns"] / cat_stats["total_transactions"]) * 100
    return cat_stats.sort_values("return_rate_pct", ascending=False)


def analyze_refunds_by_reason(returns):

    reason_stats = returns.groupby("return_reason")["refund_amount"].mean().sort_values(ascending=False)
    return reason_stats


def analyze_discount_vs_return(transactions):

    discount_stats = transactions.groupby("is_return")["discount_percent"].mean()

    correlation = transactions["discount_percent"].corr(transactions["is_return"])

    return discount_stats, correlation


def analyze_return_rate_by_payment(transactions):

    payment_stats = transactions.groupby("payment_method")["is_return"].mean() * 100
    return payment_stats.sort_values(ascending=False)


def analyze_return_time(returns):

    returns["transaction_date"] = pd.to_datetime(returns["transaction_date"])
    returns["return_date"] = pd.to_datetime(returns["return_date"])

    returns["days_to_return"] = (returns["return_date"] - returns["transaction_date"]).dt.days

    return returns["days_to_return"].mean()


def task_2_08_returns_analysis() -> None:
    print("\nЗавдання 2_08. Returns Analysis")

    result_dir = ROOT / "results" / "task_2_08"

    if not all(f.exists() for f in FILES.values()):
        print("Помилка: Не всі файли знайдено в папці cleaned_data!")
        return

    transactions = pd.read_csv(FILES["transactions"])
    returns = pd.read_csv(FILES["returns"])
    products = pd.read_excel(FILES["products"], sheet_name="Products")

    result_dir.mkdir(parents=True, exist_ok=True)

    category_results = analyze_return_rate_by_category(transactions, returns, products)
    print("Return Rate по категоріях")
    print(category_results)
    category_path = result_dir / "return_rate_by_category.csv"
    category_results.to_csv(category_path, encoding="utf-8-sig")
    print(f"Таблицю збережено: {category_path.relative_to(ROOT)}")
    print("\n" + "=" * 50 + "\n")

    reason_results = analyze_refunds_by_reason(returns)
    print("Середня сума повернення за причиною")
    print(reason_results)
    reason_path = result_dir / "average_refund_by_reason.csv"
    reason_results.to_csv(reason_path, encoding="utf-8-sig")
    print(f"Таблицю збережено: {reason_path.relative_to(ROOT)}")
    print("\n" + "=" * 50 + "\n")

    discount_stats, correlation = analyze_discount_vs_return(transactions)

    print("Вплив знижки на повернення")

    print("Середній discount_percent:")

    print(f"Non-returns (is_return=0): {discount_stats[0]:.2f}%")

    print(f"Returns (is_return=1): {discount_stats[1]:.2f}%")

    print(f"Коефіцієнт кореляції між знижкою та поверненням: {correlation:.4f}")

    if abs(correlation) < 0.1:
        print("Висновок: Зв'язок між знижкою та ймовірністю повернення майже відсутній.")
    else:
        print("Висновок: Існує помітний статистичний зв'язок між розміром знижки та поверненнями.")

    discount_path = result_dir / "discount_vs_return.csv"
    pd.DataFrame(
        {
            "is_return": discount_stats.index,
            "average_discount_percent": discount_stats.values,
            "correlation": correlation,
        }
    ).to_csv(discount_path, index=False, encoding="utf-8-sig")
    print(f"Таблицю збережено: {discount_path.relative_to(ROOT)}")
    print("\n" + "=" * 50 + "\n")

    print("Return Rate за методом оплати (%)")
    payment_results = analyze_return_rate_by_payment(transactions)
    print(payment_results)
    payment_path = result_dir / "return_rate_by_payment_method.csv"
    payment_results.to_csv(payment_path, encoding="utf-8-sig")
    print(f"Таблицю збережено: {payment_path.relative_to(ROOT)}")
    print("\n" + "=" * 50 + "\n")

    avg_days = analyze_return_time(returns)
    print(f"Середній час між покупкою та поверненням")
    print(f"Клієнти повертають товар в середньому через {avg_days:.1f} днів.")
    time_path = result_dir / "average_return_time.csv"
    pd.DataFrame(
        {
            "metric": ["average_days_to_return"],
            "value": [avg_days],
        }
    ).to_csv(time_path, index=False, encoding="utf-8-sig")
    print(f"Таблицю збережено: {time_path.relative_to(ROOT)}")


if __name__ == "__main__":
    clean_data()
    task_2_08_returns_analysis()
