from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Heatmap (sns.heatmap): кореляція unit_price, cost_price, margin_pct,
# quantity, total_amount. Використати annot=True та cmap='coolwarm'.

ROOT = Path(__file__).resolve().parent
CLEAN_DIR = ROOT / "cleaned_data"

transactions_path = CLEAN_DIR / "transactions_cleaned.csv"
company_path = CLEAN_DIR / "company_data_cleaned.xlsx"

if not transactions_path.exists() or not company_path.exists():
    from cleaning import main as clean_data
    clean_data()

tx = pd.read_csv(transactions_path, low_memory=False)

tx["quantity"] = pd.to_numeric(tx["quantity"], errors="coerce").abs()
tx["quantity"] = tx["quantity"].replace(0, 1).fillna(1).astype(int)

if "discount" in tx.columns:
    tx["discount"] = pd.to_numeric(tx["discount"], errors="coerce").fillna(0.0)
    tx.loc[tx["discount"] > 1, "discount"] = tx["discount"] / 100.0
else:
    tx["discount"] = 0.0

products = pd.read_excel(company_path, sheet_name="Products")

for col in ["unit_price", "cost_price"]:
    if col in products.columns:
        products[col] = (
            products[col]
            .astype(str)
            .str.replace(r"[$\u20AC\u00A3,]", "", regex=True)
        )
        products[col] = pd.to_numeric(products[col], errors="coerce").fillna(0.0)

products["margin_pct"] = np.where(
    products["unit_price"] > 0,
    (products["unit_price"] - products["cost_price"]) / products["unit_price"],
    0.0,
)

products_clean = products[
    ["product_id", "unit_price", "cost_price", "margin_pct"]
]

merged_df = pd.merge(tx, products_clean, on="product_id", how="left")

merged_df["clean_total_amount"] = (
    merged_df["quantity"]
    * merged_df["unit_price"]
    * (1 - merged_df["discount"])
)

columns_for_corr = [
    "unit_price",
    "cost_price",
    "margin_pct",
    "quantity",
    "clean_total_amount",
]

df_corr_ready = merged_df[columns_for_corr].dropna()

corr_matrix = df_corr_ready.corr()

plt.figure(figsize=(10, 6))

sns.heatmap(
    corr_matrix,
    annot=True,
    cmap="coolwarm",
    fmt=".2f",
    linewidths=0.5,
)

plt.title("Матриця кореляції")
plt.tight_layout()

plt.show()