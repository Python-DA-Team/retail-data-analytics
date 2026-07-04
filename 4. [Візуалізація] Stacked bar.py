# Побудувати stacked bar у matplotlib: revenue + cost + profit по місяцях (12 місяців 2025 року). Використати plt.bar() з параметром bottom.
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


with open('transactions.csv', 'r', encoding='utf-8') as f_in, \
     open('transactions_clean_stacked.csv', 'w', encoding='utf-8') as f_out:
    header = f_in.readline().strip()
    f_out.write(header + '\n')
    expected_cols_count = len(header.split(','))
    for line in f_in:
        line_clean = line.strip()
        if not line_clean: continue
        parts = line_clean.split(',')
        if len(parts) > expected_cols_count:
            excess = len(parts) - expected_cols_count
            text_idx = 4
            fixed_text = "_".join(parts[text_idx : text_idx + excess + 1])
            fixed_parts = parts[:text_idx] + [fixed_text] + parts[text_idx + excess + 1:]
            f_out.write(",".join(fixed_parts) + '\n')
        else:
            f_out.write(line_clean + '\n')

tx = pd.read_csv('transactions_clean_stacked.csv')

tx['transaction_date'] = pd.to_datetime(tx['transaction_date'], errors='coerce', format='mixed')
tx['year'] = tx['transaction_date'].dt.year
tx['month'] = tx['transaction_date'].dt.month

tx_2025 = tx[tx['year'] == 2025].copy()

tx_2025['quantity'] = pd.to_numeric(tx_2025['quantity'], errors='coerce').abs().replace(0, 1).fillna(1).astype(int)

tx_2025['discount_percent'] = pd.to_numeric(tx_2025['discount_percent'], errors='coerce').fillna(0.0)
tx_2025.loc[tx_2025['discount_percent'] > 1, 'discount_percent'] = tx_2025['discount_percent'] / 100.0


products = pd.read_excel('company_data.xlsx', sheet_name='Products')

for col in ['unit_price', 'cost_price']:
    products[col] = products[col].astype(str).str.replace(r'[$\u20AC\u00A3,]', '', regex=True)
    products[col] = pd.to_numeric(products[col], errors='coerce').fillna(0.0)

products['category'] = products['category'].astype(str).str.strip().str.capitalize()
products_clean = products[['product_id', 'unit_price', 'cost_price']]


df_2025 = pd.merge(tx_2025, products_clean, on='product_id', how='left')


df_2025['revenue'] = df_2025['quantity'] * df_2025['unit_price'] * (1 - df_2025['discount_percent'])
df_2025['cost'] = df_2025['quantity'] * df_2025['cost_price']
df_2025['profit'] = df_2025['revenue'] - df_2025['cost']

monthly_data = df_2025.groupby('month')[['revenue', 'cost', 'profit']].sum().reset_index()

monthly_data = monthly_data.set_index('month').reindex(range(1, 13), fill_value=0).reset_index()



plt.figure(figsize=(10, 6))

months = monthly_data['month']
costs = monthly_data['cost']
profits = monthly_data['profit']

month_names = ['Січ', 'Лют', 'Бер', 'Квіт', 'Трав', 'Черв', 'Лип', 'Серп', 'Врес', 'Жовт', 'Лист', 'Груд']


plt.bar(months, costs, label='Собівартість (Cost)', color='#fc8d62', alpha=0.85)

plt.bar(months, profits, bottom=costs, label='Чистий прибуток (Profit)', color='#66c2a5', alpha=0.85)


plt.title('Структура виручки за 2025 рік')
plt.xlabel('Місяць')
plt.ylabel('Сума')

plt.xticks(range(1, 13), month_names)

plt.ticklabel_format(style='plain', axis='y')

plt.grid(axis='y', linestyle='--', alpha=0.5)
plt.legend(loc='upper left', frameon=True)

plt.tight_layout()
plt.show()

