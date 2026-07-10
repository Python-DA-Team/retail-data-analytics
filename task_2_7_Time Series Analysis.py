# Завдання 7. Блок 2.
# Time Series Analysis. З transactions.csv:
# Згрупувати по днях: sum(total_amount)
# Додати змінні: dayofweek, month, is_weekend, is_holiday_season (Nov-Dec)
# Порахувати 7-денне та 30-денне ковзне середнє (rolling()) — зверніть увагу, як rolling() згладжує шум.
# Використати shift() для визначення днів з різким зростанням/падінням виручки відносно попереднього дня
# (day-over-day change). Знайти топ-5 днів з найбільшим приростом та падінням.
# Визначити дні з аномальним падінням/зростанням (>2 std від середнього)

import pandas as pd
import os
from pathlib import Path

pd.set_option('display.max_columns', None)

pd.set_option('display.width', 1000)

DATA_PATH = Path("cleaned_data/transactions_cleaned.csv")


def group_transactions_by_day():
    if not DATA_PATH.exists():
        print(f"Файл {DATA_PATH} не знайдено!")
        return None


    df = pd.read_csv(DATA_PATH)


    df['transaction_date'] = pd.to_datetime(df['transaction_date'])


    df['dayofweek'] = df['transaction_date'].dt.dayofweek
    df['month'] = df['transaction_date'].dt.month
    df['is_weekend'] = df['dayofweek'].isin([5, 6]).astype(int)
    df['is_holiday_season'] = df['month'].isin([11, 12]).astype(int)


    daily_stats = df.groupby(df['transaction_date'].dt.date).agg({
        'total_amount': 'sum',
        'dayofweek': 'first',
        'month': 'first',
        'is_weekend': 'max',
        'is_holiday_season': 'max'
    }).reset_index()


    daily_stats.columns = ['date', 'total_daily_amount', 'dayofweek', 'month', 'is_weekend', 'is_holiday_season']

    return daily_stats

def analyze_revenue_trends(df: pd.DataFrame) -> pd.DataFrame:

    df = df.sort_values('date')

    df['rolling_7d'] = df['total_daily_amount'].rolling(window=7).mean()
    df['rolling_30d'] = df['total_daily_amount'].rolling(window=30).mean()


    df['dod_change'] = df['total_daily_amount'] - df['total_daily_amount'].shift(1)

    mean_change = df['dod_change'].mean()
    std_change = df['dod_change'].std()

    df['is_anomaly'] = (df['dod_change'].abs() > 2 * std_change).astype(int)

    return df

def run_all_analysis():

    df = group_transactions_by_day()

    if df is not None:

        print("Етап 1: Результат групування по днях")
        print(df)
        print("\n" + "=" * 50 + "\n")

        result = analyze_revenue_trends(df)

        print("Результати з ковзними середніми (перші 40 днів):")
        print(result[['date','dayofweek', 'month', 'total_daily_amount', 'is_weekend', 'is_holiday_season',
                      'rolling_7d', 'rolling_30d']].head(40))
        print("\n" + "=" * 50 + "\n")

        print("Результати з ковзними середніми (кінець періоду):")
        print(result[['date', 'dayofweek', 'month', 'total_daily_amount', 'is_weekend', 'is_holiday_season',
                      'rolling_7d', 'rolling_30d']].tail())
        print("\n" + "=" * 50 + "\n")

        top_growth = result.nlargest(5, 'dod_change')
        top_drop = result.nsmallest(5, 'dod_change')

        print("Топ-5 днів з найбільшим приростом:")
        print(top_growth[['date','dayofweek', 'month', 'total_daily_amount', 'is_weekend', 'is_holiday_season' ,
                          'dod_change']])
        print("\n" + "=" * 50 + "\n")

        print("Топ-5 днів з найбільшим падінням:")
        print(top_drop[['date', 'dayofweek', 'month', 'total_daily_amount', 'is_weekend', 'is_holiday_season' ,
                        'dod_change']])
        print("\n" + "=" * 50 + "\n")

        print("Дні з аномальними змінами (> 2 std)")
        print(result[result['is_anomaly'] == 1][['date','dayofweek', 'month', 'total_daily_amount', 'is_weekend',
                                                 'is_holiday_season' , 'dod_change']])

if __name__ == "__main__":
    run_all_analysis()