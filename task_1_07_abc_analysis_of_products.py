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


# задание 1_07
# 7. [Просунуті] ABC-аналіз товарів. Порахувати суму виручки на товарі 10%.
# ABC-аналіз товарів. Порахувати суму виручки на товар, відсортувати за спаданням,
# додати cumsum() частки (кумулятивна сума). A = перші 70% виручки, B = 70–90%, C = останні 10%.
# Скільки товарів у A, B, C?
def task_1_07_abc_analysis_of_products() -> None:
    print("\nЗавдання 1_07. ABC-аналіз товарів")

    RESULT_DIR = ROOT / "results" / "task_1_07"

    transactions = pd.read_csv(OUT / "transactions_cleaned.csv", low_memory=False)
    products = pd.read_excel(OUT / "company_data_cleaned.xlsx", sheet_name="Products")

    # 1. Сума виручки на товар
    revenue_per_product = transactions.groupby("product_id")["total_amount"].sum().reset_index()

    # 2. Об’єднання з products для категорій/назв
    revenue_per_product = revenue_per_product.merge(products, on="product_id", how="left")

    # 3. Сортування за спаданням
    revenue_per_product = revenue_per_product.sort_values("total_amount", ascending=False)

    # 4. Кумулятивна частка
    total_revenue = revenue_per_product["total_amount"].sum()
    revenue_per_product["cum_share"] = revenue_per_product["total_amount"].cumsum() / total_revenue * 100

    # 5. Присвоєння груп A/B/C та Підрахунок кількості товарів у кожній групі
    def abc_group(x):
        if x <= 70:
            return "A (перші 70% виручки)"
        elif x <= 90:
            return "B (70–90%)"
        else:
            return "C (останні 10%)"

    revenue_per_product["ABC"] = revenue_per_product["cum_share"].apply(abc_group)

    abc_counts = revenue_per_product["ABC"].value_counts()

    # 7. Підрахунок суми виручки на товарі групи C (10%)
    sum_c = revenue_per_product[revenue_per_product["ABC"] == "C (останні 10%)"]["total_amount"].sum()

    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    table_path = RESULT_DIR / "abc_analysis_of_products.csv"
    counts_path = RESULT_DIR / "abc_counts.csv"
    revenue_per_product.to_csv(table_path, index=False, encoding="utf-8-sig")
    abc_counts.rename_axis("ABC").reset_index(name="product_count").to_csv(
        counts_path,
        index=False,
        encoding="utf-8-sig",
    )

    print("Quantities of goods in each group:\n", abc_counts)
    print(
        "Sorting by sum in descending order\n",
        revenue_per_product[["product_id", "product_name", "total_amount", "category", "ABC"]].head(10)
    )
    print("Revenue from Group C products (10%):", sum_c)
    print(f"Таблицю збережено: {table_path.relative_to(ROOT)}")
    print(f"Таблицю збережено: {counts_path.relative_to(ROOT)}")


if __name__ == "__main__":
    clean_data()
    task_1_07_abc_analysis_of_products()
