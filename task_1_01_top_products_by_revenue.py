# Базові (pandas)
# 1. Топ-10 товарів за виручкою.
# Згрупувати transactions.csv по product_id (лише продажі, не returns), порахувати sum(total_amount).
# Об'єднати з Products через company_data.xlsx. Вивести таблицю.

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent
CLEAN_DIR = ROOT / "cleaned_data"

marketing_path = CLEAN_DIR / "marketing_cleaned.csv"
excel_path = CLEAN_DIR / "company_data_cleaned.xlsx"

if not marketing_path.exists() or not excel_path.exists():
    from cleaning import main as clean_data
    clean_data()

df_marketing = pd.read_csv(marketing_path)
df_products = pd.read_excel(excel_path, sheet_name="Products")

if df_marketing["revenue_generated"].dtype == "object":
    df_marketing["revenue_generated"] = (
        df_marketing["revenue_generated"]
        .astype(str)
        .str.replace("", "", regex=True)
    )

df_marketing["revenue_generated"] = pd.to_numeric(
    df_marketing["revenue_generated"], errors="coerce"
)

# групую товари та обчислюю загальну виручку
revenue_per_product = (
    df_marketing.groupby("product_id")["revenue_generated"]
    .sum()
    .reset_index()
)

revenue_per_product.columns = ["product_id", "total_amount"]

final_table = pd.merge(revenue_per_product, df_products, on="product_id", how="inner")

# сортую товари з топ-10 за спаданням
top_10_products = (
    final_table.sort_values(by="total_amount", ascending=False)
    .head(10)
    .reset_index(drop=True)
)

top_10_products["total_amount"] = top_10_products["total_amount"].map("{:,.2f}".format)

output_columns = ["product_name", "category", "total_amount"]
available_columns = [col for col in output_columns if col in top_10_products.columns]

print(f"\nТОП-10 товарів за виручкою:\n\n{top_10_products[available_columns].to_string(index=False)}")
print("-" * 20)