# Блок 1. Завдання 9.
# Аналіз знижок. Розбити транзакції на: discount_percent == 0 vs >0.
# Порівняти середню кількість одиниць (quantity) та виручку. Чи працюють знижки?

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent
CLEAN_DIR = ROOT / "cleaned_data"


def load_data():
    transactions_path = CLEAN_DIR / "transactions_cleaned.csv"
    company_path = CLEAN_DIR / "company_data_cleaned.xlsx"

    if not transactions_path.exists() or not company_path.exists():
        from cleaning import main as clean_data
        clean_data()

    df_trans = pd.read_csv(transactions_path, low_memory=False)
    df_prod = pd.read_excel(company_path, sheet_name="Products")

    return df_trans, df_prod


def run_discount_analysis():
    df_trans, df_prod = load_data()

    df_trans = df_trans[["quantity", "total_amount", "discount_percent", "product_id"]]
    df_prod = df_prod[["product_id", "category"]]

    df = pd.merge(df_trans, df_prod, on="product_id", how="left")

    df["discount_percent"] = df["discount_percent"].fillna(0)
    df["Groups_name"] = df["discount_percent"] > 0

    comparison = df.groupby("Groups_name").agg({
        "quantity": "mean",
        "total_amount": "mean"
    }).rename(columns={"quantity": "Avg_Quantity", "total_amount": "Avg_Revenue"})

    comparison = comparison.rename(index={False: "Без знижки", True: "Зі знижкою"})

    print("Результати аналізу ефективності знижок")
    print(comparison)

    if comparison.loc["Зі знижкою", "Avg_Revenue"] > comparison.loc["Без знижки", "Avg_Revenue"]:
        print("Висновок: Знижки стимулюють вищий середній чек.")
    else:
        print("Висновок: Середній чек без знижок вищий (знижки зменшують маржинальність).")


if __name__ == "__main__":
    run_discount_analysis()