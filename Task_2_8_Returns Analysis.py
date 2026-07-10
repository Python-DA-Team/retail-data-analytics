# Завдання 8. Блок 2.
# Returns Analysis. З returns.csv (окремий файл з деталями повернень) та transactions.csv (де is_return == 1):
# Rate of returns by category (returns / total transactions) — використайте merge з Products для отримання категорії
# Average refund amount by reason (return_reason з returns.csv). Яка причина найдорожча?
# Чи корелює discount_percent із ймовірністю повернення? Порівняти середній discount для returns vs non-returns
# Чи відрізняється return rate по payment_method?
# Який середній час між покупкою та поверненням (return_date - transaction_date)?


import pandas as pd
from pathlib import Path

# Конфігурація відображення
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 1000)


DATA_DIR = Path("cleaned_data")
FILES = {
    "transactions": DATA_DIR / "transactions_cleaned.csv",
    "returns": DATA_DIR / "returns_cleaned.csv",
    "products": DATA_DIR / "company_data_cleaned.xlsx"
}

def analyze_return_rate_by_category(transactions, returns, products):

    for name, path in FILES.items():
        if not path.exists():
            print(f"Помилка: Файл {path} не знайдено!")
            return None


    transactions = pd.read_csv(FILES["transactions"])
    returns = pd.read_csv(FILES["returns"])
    products = pd.read_excel(FILES["products"], sheet_name="Products")


    total_tx = transactions.groupby('product_id').size().reset_index(name='total_transactions')
    total_returns = returns.groupby('product_id').size().reset_index(name='total_returns')

    data = pd.merge(total_tx, total_returns, on='product_id', how='left').fillna(0)
    data = pd.merge(data, products[['product_id', 'category']], on='product_id', how='left')

    cat_stats = data.groupby('category').agg({'total_transactions': 'sum', 'total_returns': 'sum'})
    cat_stats['return_rate_pct'] = (cat_stats['total_returns'] / cat_stats['total_transactions']) * 100
    return cat_stats.sort_values('return_rate_pct', ascending=False)


def analyze_refunds_by_reason(returns):

    reason_stats = returns.groupby('return_reason')['refund_amount'].mean().sort_values(ascending=False)
    return reason_stats


def analyze_discount_vs_return(transactions):

    discount_stats = transactions.groupby('is_return')['discount_percent'].mean()


    correlation = transactions['discount_percent'].corr(transactions['is_return'])

    return discount_stats, correlation

def analyze_return_rate_by_payment(transactions):

    payment_stats = transactions.groupby('payment_method')['is_return'].mean() * 100
    return payment_stats.sort_values(ascending=False)


def analyze_return_time(returns):

    returns['transaction_date'] = pd.to_datetime(returns['transaction_date'])
    returns['return_date'] = pd.to_datetime(returns['return_date'])


    returns['days_to_return'] = (returns['return_date'] - returns['transaction_date']).dt.days

    return returns['days_to_return'].mean()


def run_all_analysis():

    if not all(f.exists() for f in FILES.values()):
        print("Помилка: Не всі файли знайдено в папці cleaned_data!")
        return

    transactions = pd.read_csv(FILES["transactions"])
    returns = pd.read_csv(FILES["returns"])
    products = pd.read_excel(FILES["products"], sheet_name="Products")


    category_results = analyze_return_rate_by_category(transactions, returns, products)
    print("Return Rate по категоріях")
    print(category_results)
    print("\n" + "=" * 50 + "\n")


    reason_results = analyze_refunds_by_reason(returns)
    print("Середня сума повернення за причиною")
    print(reason_results)
    print("\n" + "=" * 50 + "\n")

    discount_stats, correlation = analyze_discount_vs_return(transactions)

    print("Вплив знижки на повернення")

    print("Середній discount_percent:")

    print(f"Non-returns (is_return=0): {discount_stats[0]:.2f}%")

    print(f"Returns (is_return=1): {discount_stats[1]:.2f}%")

    print(f"Коефіцієнт кореляції між знижкою та поверненням: {correlation:.4f}")

    if abs(correlation) < 0.1:
        print("Висновок: Зв'язок між знижкою та ймовірністю повернення майже відсутній.")
    else:
        print("Висновок: Існує помітний статистичний зв'язок між розміром знижки та поверненнями.")
    print("\n" + "=" * 50 + "\n")

    print("Return Rate за методом оплати (%)")
    print(analyze_return_rate_by_payment(transactions))
    print("\n" + "=" * 50 + "\n")

    avg_days = analyze_return_time(returns)
    print(f"Середній час між покупкою та поверненням")
    print(f"Клієнти повертають товар в середньому через {avg_days:.1f} днів.")

if __name__ == "__main__":
    run_all_analysis()