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


# задание 1_03
CLEAN_DIR = OUT
RESULT_DIR = ROOT / "results" / "task_1_3"


def load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    transactions_path = CLEAN_DIR / "transactions_cleaned.csv"
    company_path = CLEAN_DIR / "company_data_cleaned.xlsx"

    transactions = pd.read_csv(transactions_path, low_memory=False)
    stores = pd.read_excel(company_path, sheet_name="Stores")
    return transactions, stores


def calculate_average_check(
    transactions: pd.DataFrame,
    stores: pd.DataFrame,
) -> pd.DataFrame:
    sales = transactions.loc[transactions["is_return"].eq(0)].copy()
    sales["store_id"] = pd.to_numeric(sales["store_id"], errors="coerce")
    sales["total_amount"] = pd.to_numeric(sales["total_amount"], errors="coerce")
    sales = sales.dropna(subset=["transaction_id", "store_id", "total_amount"])
    sales = sales.loc[sales["total_amount"].gt(0)]
    sales["store_id"] = sales["store_id"].astype("int64")

    checks = (
        sales.groupby(["store_id", "transaction_id"], as_index=False)
        .agg(check_amount=("total_amount", "sum"))
    )

    store_metrics = (
        checks.groupby("store_id", as_index=False)
        .agg(
            transactions_count=("transaction_id", "nunique"),
            total_revenue=("check_amount", "sum"),
            average_check=("check_amount", "mean"),
        )
    )

    store_columns = [
        "store_id",
        "store_name",
        "country",
        "region",
        "store_format",
    ]
    result = store_metrics.merge(
        stores[store_columns],
        on="store_id",
        how="left",
        validate="one_to_one",
    )

    result = result[
        [
            "store_id",
            "store_name",
            "country",
            "region",
            "store_format",
            "transactions_count",
            "total_revenue",
            "average_check",
        ]
    ]
    result[["total_revenue", "average_check"]] = result[
        ["total_revenue", "average_check"]
    ].round(2)
    return result.sort_values("average_check", ascending=False).reset_index(drop=True)


def save_results(result: pd.DataFrame) -> Path:
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = RESULT_DIR / "average_check_by_store.csv"
    result.to_csv(output_path, index=False, encoding="utf-8-sig")
    return output_path


def print_store(label: str, store: pd.Series) -> None:
    print(
        f"{label}: {store['store_name']} (store_id={store['store_id']}), "
        f"середній чек = {store['average_check']:.2f}"
    )


def task_1_03_average_check_by_store() -> None:
    print("\nЗавдання 1_03. Середній чек по магазинах")

    transactions, stores = load_data()
    result = calculate_average_check(transactions, stores)

    if result.empty:
        raise ValueError("Не знайдено продажів для розрахунку середнього чека")

    output_path = save_results(result)
    print_store("Найвищий середній чек", result.iloc[0])
    print_store("Найнижчий середній чек", result.iloc[-1])
    print(f"Таблицю збережено: {output_path.relative_to(ROOT)}")


if __name__ == "__main__":
    clean_data()
    task_1_03_average_check_by_store()
