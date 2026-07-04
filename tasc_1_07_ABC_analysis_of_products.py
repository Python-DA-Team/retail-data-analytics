# 7. [Просунуті] ABC-аналіз товарів. Порахувати суму виручки на товарі 10%.
# ABC-аналіз товарів. Порахувати суму виручки на товар, відсортувати за спаданням,
# додати cumsum() частки (кумулятивна сума). A = перші 70% виручки, B = 70–90%, C = останні 10%.
# Скільки товарів у A, B, C?

ROOT = Path(__file__).resolve().parent
CLEAN_DIR = ROOT / "cleaned_data"
RESULT_DIR = ROOT / "results" / "task_1_07_ABC_analysis_of_products"

def load_table(filename: str, sep: str = ",") -> pd.DataFrame:
    """Універсальне завантаження очищених таблиць з cleaned_data"""
    path = CLEAN_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Файл {path} не знайдено")
    return pd.read_csv(path, low_memory=False, sep=sep)


transactions = load_table("transactions_cleaned.csv")
products = load_table("products_cleaned.csv")

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
sum_c = revenue_per_product[revenue_per_product['ABC']=="C (останні 10%)"]['total_amount'].sum()

print('Quantities of goods in each group:\n', abc_counts)
print('Sorting by sum in descending order\n', revenue_per_product[["product_id", "product_name", "total_amount", "category", "ABC"]].head(10))
print('Revenue from Group C products (10%):' , sum_c)
