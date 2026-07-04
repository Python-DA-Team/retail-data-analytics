# 2. Розподіл виручки по категоріях. pivot_table:
# category по рядках, місяць по стовпцях, сума total_amount.
# Яка категорія лідирує щомісяця?

ROOT = Path(__file__).resolve().parent
CLEAN_DIR = ROOT / "cleaned_data"
RESULT_DIR = ROOT / "results" / "task_1_02_pivot_table"

def load_table(filename: str, sep: str = ",") -> pd.DataFrame:
    """Універсальне завантаження очищених таблиць з cleaned_data"""
    path = CLEAN_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Файл {path} не знайдено")
    return pd.read_csv(path, low_memory=False, sep=sep)

# 1. Завантаження очищених таблиць
transactions = load_table("transactions_cleaned.csv")
products = load_table("products_cleaned.csv")

# 2. Перетворення дати у datetime та витяг місяця
transactions["transaction_date"] = pd.to_datetime(transactions["transaction_date"], errors="coerce")
transactions["month"] = transactions["transaction_date"].dt.month

# 3. Об’єднання транзакцій з продуктами по product_id
df = transactions.merge(products, on="product_id", how="left")

# 4. Побудова pivot_table: категорії по рядках, місяці по стовпцях, сума total_amount
pivot = pd.pivot_table(
    df,    
    values="total_amount",
    index="category",
    columns="month",
    aggfunc="sum",
    fill_value=0
)

print("Pivot table 'Revenue breakdown by category and month':\n", pivot)

# 5. Знаходження категорії-лідера щомісяця
leaders = pivot.idxmax()
leaders_table = pd.DataFrame({
    "month": leaders.index,
    "leader_category": leaders.values
})
print("\nLeaderboard:\n", leaders_table)
