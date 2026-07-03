import os
import sqlite3
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
# Візуалізація (matplotlib/seaborn)
# 4. Barplot: виручка по категоріях за 2024 vs 2025 (поруч).


with open('transactions.csv', 'r', encoding='utf-8') as f_in, \
        open('transactions_fixed.csv', 'w', encoding='utf-8') as f_out:
    header = f_in.readline().strip()
    f_out.write(header + '\n')
    expected_cols_count = len(header.split(','))

    for line in f_in:
        line_clean = line.strip()
        if not line_clean:
            continue

        parts = line_clean.split(',')
        if len(parts) > expected_cols_count:
            excess = len(parts) - expected_cols_count
            text_idx = 4
            fixed_text = "_".join(parts[text_idx: text_idx + excess + 1])
            fixed_parts = parts[:text_idx] + [fixed_text] + parts[text_idx + excess + 1:]

            f_out.write(",".join(fixed_parts) + '\n')
        else:
            f_out.write(line_clean + '\n')

tx = pd.read_csv('transactions_fixed.csv')


tx['transaction_date'] = pd.to_datetime(tx['transaction_date'], errors='coerce', format='mixed')
tx['year'] = tx['transaction_date'].dt.year


tx['quantity'] = pd.to_numeric(tx['quantity'], errors='coerce').abs()
tx['quantity'] = tx['quantity'].replace(0, 1).fillna(1).astype(int)


if 'discount' in tx.columns:
    tx['discount'] = pd.to_numeric(tx['discount'], errors='coerce').fillna(0.0)
    tx.loc[tx['discount'] > 1, 'discount'] = tx['discount'] / 100.0
else:
    tx['discount'] = 0.0

products = pd.read_excel('company_data.xlsx', sheet_name='Products')


products['unit_price'] = products['unit_price'].astype(str).str.replace(r'[$\u20AC\u00A3,]', '', regex=True)
products['unit_price'] = pd.to_numeric(products['unit_price'], errors='coerce').fillna(0.0)

products_clean = products[['product_id', 'category', 'unit_price']]

print("Об'єднання таблиць та розрахунок виручки...")
merged_df = pd.merge(tx, products_clean, on='product_id', how='left')


df_filtered = merged_df[merged_df['year'].isin([2024, 2025])]


df_filtered['clean_total_amount'] = df_filtered['quantity'] * df_filtered['unit_price'] * (1 - df_filtered['discount'])

revenue_data = df_filtered.groupby(['category', 'year'])['clean_total_amount'].sum().reset_index()


plt.figure(figsize=(12, 6))
sns.set_theme(style="whitegrid")

ax = sns.barplot(
    data=revenue_data,
    x='category',
    y='clean_total_amount',
    hue='year',
    palette='Set2'
)

plt.title('Виручка по категоріях за 2024 vs 2025 роки ', fontsize=16, pad=15)
plt.xlabel('Категорія товару', fontsize=12, labelpad=10)
plt.ylabel('Загальна виручка', fontsize=12, labelpad=10)

plt.ticklabel_format(style='plain', axis='y')
plt.xticks(rotation=30, ha='right')
plt.legend(title='Рік', loc='upper right')
plt.tight_layout()

plt.show()
