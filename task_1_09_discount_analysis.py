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


# задание 1_09
# Блок 1. Завдання 9.
# Аналіз знижок. Розбити транзакції на: discount_percent == 0 vs >0.
#  Порівняти середню кількість одиниць (quantity) та виручку. Чи працюють знижки?
DATA_PATH = OUT / "transactions_cleaned.csv"


def task_1_09_discount_analysis() -> None:
    print("\nЗавдання 1_09. Аналіз знижок")

    result_dir = ROOT / "results" / "task_1_09"

    if not os.path.exists(DATA_PATH):
        print(f"Файл {DATA_PATH} не знайдено!")
        return

    df = pd.read_csv(DATA_PATH)

    no_discount_df = df[df["discount_percent"] == 0]
    with_discount_df = df[df["discount_percent"] > 0]

    no_discount_table = pd.DataFrame({"Кількість": [no_discount_df["transaction_id"].count()],
                                      "Сума": [no_discount_df["total_amount"].sum()]})
    with_discount_table = pd.DataFrame({"Кількість": [with_discount_df["transaction_id"].count()],
                                        "Сума": [with_discount_df["total_amount"].sum()]})

    print("ТАБЛИЦЯ: Транзакції БЕЗ знижок")
    print(no_discount_table)
    print("\n" + "=" * 50 + "\n")

    print("ТАБЛИЦЯ: Транзакції ЗІ знижкою")
    print(with_discount_table)
    print("\n" + "=" * 50 + "\n")

    df["discount_group"] = ["Без знижки" if d == 0 else "Зі знижкою" for d in df["discount_percent"]]
    analysis = df.groupby("discount_group")[["quantity", "total_amount"]].mean()

    print("СЕРЕДНІ ПОКАЗНИКИ: Без знижки vs Зі знижкою")
    print(analysis.round(2))

    print(" ВИСНОВКИ")
    q_no = analysis.loc["Без знижки", "quantity"]
    q_yes = analysis.loc["Зі знижкою", "quantity"]
    t_no = analysis.loc["Без знижки", "total_amount"]
    t_yes = analysis.loc["Зі знижкою", "total_amount"]

    if q_yes > q_no:
        print(f"- Кількість товарів у кошику зі знижкою вища (+{((q_yes / q_no) - 1) * 100:.1f}%)")
    else:
        print("- Знижки НЕ стимулюють клієнтів купувати більше товарів.")

    if t_yes < t_no:
        print("- Середній чек зі знижкою НИЖЧИЙ: знижки зменшують маржинальність без приросту обсягу.")
    else:
        print("- Середній чек зі знижкою вищий — акції працюють ефективно.")

    result_dir.mkdir(parents=True, exist_ok=True)
    no_discount_path = result_dir / "transactions_without_discount.csv"
    with_discount_path = result_dir / "transactions_with_discount.csv"
    analysis_path = result_dir / "discount_analysis.csv"
    no_discount_table.to_csv(no_discount_path, index=False, encoding="utf-8-sig")
    with_discount_table.to_csv(with_discount_path, index=False, encoding="utf-8-sig")
    analysis.round(2).to_csv(analysis_path, encoding="utf-8-sig")
    print(f"Таблицю збережено: {no_discount_path.relative_to(ROOT)}")
    print(f"Таблицю збережено: {with_discount_path.relative_to(ROOT)}")
    print(f"Таблицю збережено: {analysis_path.relative_to(ROOT)}")


if __name__ == "__main__":
    clean_data()
    task_1_09_discount_analysis()
