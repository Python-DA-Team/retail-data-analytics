from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parent
CLEAN_DIR = ROOT / "cleaned_data"
RESULT_DIR = ROOT / "results" / "task_2_02_patero_analysis_80"


def load_transactions() -> pd.DataFrame:
    path = CLEAN_DIR / "transactions_cleaned.csv"
    if not path.exists():
        from cleaning import main as clean_data
        clean_data()
    return pd.read_csv(path, low_memory=False)


def load_products() -> pd.DataFrame:
    path = CLEAN_DIR / "company_data_cleaned.xlsx"
    if not path.exists():
        from cleaning import main as clean_data
        clean_data()
    return pd.read_excel(path, sheet_name="Products")


# 2.2. Pareto Analysis (80/20).
# Pareto Analysis (80/20). Для всіх продуктів (з Products):
# Порахувати частку кожного продукту в загальній виручці (transactions)
# Відсортувати за спаданням, cumsum
# Знайти, скільки продуктів дають 80% виручки
# Візуалізувати: крива Парето (line + bar)

transactions = load_transactions()
products = load_products()

revenue_per_product = (
    transactions.groupby("product_id")["total_amount"]
    .sum()
    .reset_index()
)

revenue_per_product = revenue_per_product.merge(
    products,
    on="product_id",
    how="left"
)

revenue_per_product = revenue_per_product.sort_values(
    "total_amount",
    ascending=False
).reset_index(drop=True)

total_revenue = revenue_per_product["total_amount"].sum()
revenue_per_product["cum_share"] = (
    revenue_per_product["total_amount"].cumsum()
    / total_revenue
    * 100
)


def group(x):
    return "Перші 80% виручки" if x <= 80 else "Останні 20% виручки"


revenue_per_product["80/20"] = revenue_per_product["cum_share"].apply(group)
n_products_80 = (revenue_per_product["cum_share"] <= 80).sum()

print('Quantities of goods in group "Перші 80% виручки": ', n_products_80)

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

plt.title(
    f"Patero Analysis (80/20) by products\n"
    f"Count of products generating 80% of revenue: {n_products_80}",
    fontsize=14,
    fontweight="bold"
)

plt.tight_layout()
plt.show()