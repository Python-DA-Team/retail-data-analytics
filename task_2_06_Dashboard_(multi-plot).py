from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns


ROOT = Path(__file__).resolve().parent
CLEAN_DIR = ROOT / "cleaned_data"
RESULT_DIR = ROOT / "results" / "task_2_06"


def load_table(filename: str, sep: str = ",") -> pd.DataFrame:
    """Універсальне завантаження очищених таблиць з cleaned_data"""
    if filename == "products_cleaned.csv":
        path = CLEAN_DIR / "company_data_cleaned.xlsx"
        if not path.exists():
            from cleaning import main as clean_data
            clean_data()
        return pd.read_excel(path, sheet_name="Products")

    path = CLEAN_DIR / filename
    if not path.exists():
        from cleaning import main as clean_data
        clean_data()
    return pd.read_csv(path, low_memory=False, sep=sep)


# 6. [Візуалізація] Dashboard (multi-plot):
# Dashboard (multi-plot): 4 графіки на одному полотні (subplots(2,2)):
# Revenue trend (line)
# Profit margin by store format (sns.barplot)
# Returns rate by category (pie — plt.pie)
# Monthly transaction count (sns.lineplot з marker='o')

transactions = load_table("transactions_cleaned.csv")
products = load_table("products_cleaned.csv")
returns = load_table("returns_cleaned.csv")
stores = load_table("stores_cleaned.csv")

transactions["transaction_date"] = pd.to_datetime(
    transactions["transaction_date"],
    errors="coerce"
)

transactions["month"] = transactions["transaction_date"].dt.month

revenue_trend = (
    transactions
    .groupby("transaction_date", as_index=False)["total_amount"]
    .sum()
)

fig, axes = plt.subplots(2, 2, figsize=(14, 10))
fig.suptitle('Total Revenue')

# 1. Revenue trend (line)
sns.lineplot(
    data=revenue_trend,
    x='transaction_date',
    y='total_amount',
    color='royalblue',
    ax=axes[0,0]
)
axes[0,0].set_title('Revenue Trend')
axes[0,0].set_xlabel('Date')
axes[0,0].set_ylabel('Total Amount')

# 2. Profit margin by store format (barplot)
df = transactions.merge(products[['product_id', 'margin_pct']], on='product_id', how="left")
df = df.merge(stores[['store_id', 'store_format']], on='store_id', how="left")
df['profit'] = df['total_amount'] * df['margin_pct'] / 100

df_clean = df.dropna(subset=["margin_pct"])
df_clean = df_clean[df_clean["total_amount"] > 0]

share_unknown = (df_clean["store_format"].isna().sum() / len(df_clean)) * 100
print(f"Частка Unknown: {share_unknown:.1f}%")

# враховуючи кількість транзакцій з магазином з форматом NaN та id NaN -5002 строки (5%), переназвемо формат
# у 'Uknow' та зробимо умовні 'id'

df_clean["store_format"] = df_clean["store_format"].fillna("Unknown")
df_clean["store_id"] = df_clean["store_id"].fillna(-1)  # умовний ID

profit_margin_format = (
    df_clean.groupby('store_format').apply(
    lambda g: g['profit'].sum()/ g['total_amount'].sum() * 100).
    reset_index(name='profit_margin')
)

sns.barplot(
    data=profit_margin_format,
    x='store_format',
    y='profit_margin',
    color='green',
    ax=axes[0,1]
)
axes[0,1].set_title("Profit Margin by Store Format")
axes[0,1].set_xlabel('Store Format')
axes[0,1].set_ylabel('Profit Margin')

# 3. Returns rate by category (pie chart)
returns = transactions[transactions["is_return"]==True]
returns_rate = returns.merge(products[["product_id","category"]], on="product_id", how="left")
returns_rate = returns_rate.groupby("category")["transaction_id"].count()

axes[1,0].pie(
    returns_rate,
    labels=returns_rate.index,
    colors =sns.color_palette('pastel'),
    autopct="%1.1f%%"
)
axes[1,0].set_title("Returns Rate by Category")

# 4. Monthly transaction count (lineplot з marker='o')

monthly_counts = transactions.groupby("month")["transaction_id"].count().reset_index()

sns.lineplot(
    data=monthly_counts,
    x="month",
    y="transaction_id",
    marker="o",
    ax=axes[1,1]
)
axes[1,1].set_title("Monthly Transaction Count")
axes[1,1].set_xlabel('Month')
axes[1,1].set_ylabel('Transaction Count')

plt.tight_layout()

RESULT_DIR.mkdir(parents=True, exist_ok=True)
output_path = RESULT_DIR / "dashboard_multi_plot.png"
plt.savefig(output_path, dpi=300, bbox_inches="tight")
print(f"Графік збережено: {output_path}")

plt.close()