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


# задание 2_02
# 2.2. Pareto Analysis (80/20).
# Pareto Analysis (80/20). Для всіх продуктів (з Products):
# Порахувати частку кожного продукту в загальній виручці (transactions)
# Відсортувати за спаданням, cumsum
# Знайти, скільки продуктів дають 80% виручки
# Візуалізувати: крива Парето (line + bar)
def task_2_02_patero_analysis_80() -> None:
    print("\nЗавдання 2_02. Patero Analysis (80/20)")

    CLEAN_DIR = OUT
    RESULT_DIR = ROOT / "results" / "task_2_02_patero_analysis_80"

    def load_table(filename: str, sep: str = ",") -> pd.DataFrame:
        """Універсальне завантаження очищених таблиць з cleaned_data"""
        path = CLEAN_DIR / filename
        if not path.exists():
            raise FileNotFoundError(f"Файл {path} не знайдено")
        return pd.read_csv(path, low_memory=False, sep=sep)

    transactions = load_table("transactions_cleaned.csv")
    products = pd.read_excel(CLEAN_DIR / "company_data_cleaned.xlsx", sheet_name="Products")

    revenue_per_product = transactions.groupby("product_id")["total_amount"].sum().reset_index()
    revenue_per_product = revenue_per_product.merge(products, on="product_id", how="left")
    revenue_per_product = revenue_per_product.sort_values("total_amount", ascending=False).reset_index(drop=True)

    total_revenue = revenue_per_product["total_amount"].sum()
    revenue_per_product["cum_share"] = revenue_per_product["total_amount"].cumsum() / total_revenue * 100

    n_products_80 = int(revenue_per_product[revenue_per_product["cum_share"] >= 80].index[0] + 1)

    def group(x):
        return "Перші 80% виручки" if x < n_products_80 else "Останні 20% виручки"

    revenue_per_product["80/20"] = [group(i) for i in range(len(revenue_per_product))]

    print('Quantities of goods in group "Перші 80% виручки": ', n_products_80)

    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    table_path = RESULT_DIR / "patero_analysis_80.csv"
    chart_path = RESULT_DIR / "patero_analysis_80.png"
    revenue_per_product.to_csv(table_path, index=False, encoding="utf-8-sig")

    # графік та лінія
    fig, ax1 = plt.subplots(figsize=(15, 7))

    colors = revenue_per_product["80/20"].map({
        "Перші 80% виручки": "skyblue",
        "Останні 20% виручки": "lightgreen"
    })

    ax1.bar(revenue_per_product["product_name"], revenue_per_product["total_amount"], color=colors, alpha=0.8)
    ax1.set_ylabel("Total Amount", fontsize=15)
    ax1.set_xticks(range(len(revenue_per_product["product_name"])))
    ax1.set_xticklabels(revenue_per_product["product_name"], rotation=90)

    ax2 = ax1.twinx()
    ax2.plot(revenue_per_product["product_name"], revenue_per_product["cum_share"], color="red", alpha=0.8)
    ax2.set_ylabel("Cum_share (%)", fontsize=15)

    ax2.axhline(80, color="k", linestyle="--", label="80% поріг")

    ax1.axvline(n_products_80 - 1, color="purple", linestyle="--", label=f"{n_products_80} продуктів = 80%")

    plt.title("Patero Analysis (80/20) by products", fontsize=15, fontweight="bold")
    ax2.legend(loc="lower right")

    plt.title(f"Patero Analysis (80/20) by products\n"
              f"Count of products generating 80% of revenue: {n_products_80}",
              fontsize=14, fontweight="bold")

    plt.tight_layout()
    plt.savefig(chart_path, dpi=300, bbox_inches="tight")
    plt.close(fig)

    print(f"Таблицю збережено: {table_path.relative_to(ROOT)}")
    print(f"Графік збережено: {chart_path.relative_to(ROOT)}")


if __name__ == "__main__":
    clean_data()
    task_2_02_patero_analysis_80()
