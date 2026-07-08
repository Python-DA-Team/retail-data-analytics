 # Блок 1. Завдання 9.
# Аналіз знижок. Розбити транзакції на: discount_percent == 0 vs >0.
#  Порівняти середню кількість одиниць (quantity) та виручку. Чи працюють знижки?

import pandas as pd
import os



DATA_PATH = "cleaned_data/transactions_cleaned.csv"


def analyze_discounts():

     if not os.path.exists(DATA_PATH):
         print(f"Файл {DATA_PATH} не знайдено!")
         return

     df = pd.read_csv(DATA_PATH)


     no_discount_df = df[df['discount_percent'] == 0]
     with_discount_df = df[df['discount_percent'] > 0]

     print("--- ТАБЛИЦЯ: Транзакції БЕЗ знижок ---")
     print(pd.DataFrame({'Кількість': [no_discount_df['transaction_id'].count()],
                         'Сума': [no_discount_df['total_amount'].sum()]}))

     print("\n--- ТАБЛИЦЯ: Транзакції ЗІ знижкою ---")
     print(pd.DataFrame({'Кількість': [with_discount_df['transaction_id'].count()],
                         'Сума': [with_discount_df['total_amount'].sum()]}))


     df['discount_group'] = ['Без знижки' if d == 0 else 'Зі знижкою' for d in df['discount_percent']]
     analysis = df.groupby('discount_group')[['quantity', 'total_amount']].mean()

     print("СЕРЕДНІ ПОКАЗНИКИ: Без знижки vs Зі знижкою")
     print(analysis.round(2))


     print(" ВИСНОВКИ")
     q_no = analysis.loc['Без знижки', 'quantity']
     q_yes = analysis.loc['Зі знижкою', 'quantity']
     t_no = analysis.loc['Без знижки', 'total_amount']
     t_yes = analysis.loc['Зі знижкою', 'total_amount']

     if q_yes > q_no:
         print(f"- Кількість товарів у кошику зі знижкою вища (+{((q_yes / q_no) - 1) * 100:.1f}%)")
     else:
         print("- Знижки НЕ стимулюють клієнтів купувати більше товарів.")

     if t_yes < t_no:
         print("- Середній чек зі знижкою НИЖЧИЙ: знижки зменшують маржинальність без приросту обсягу.")
     else:
         print("- Середній чек зі знижкою вищий — акції працюють ефективно.")

if __name__ == "__main__":
     analyze_discounts()