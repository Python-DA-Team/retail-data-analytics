# 6. Boxplot / Violinplot (seaborn) + KDE: розподіл total_amount по категоріях (тільки продажі > 0). Показати викиди. Спробуйте обидва типи:
#    - sns.boxplot() — медіана, квартилі, викиди
#    - sns.violinplot() — boxplot + KDE (щільність розподілу)
#    - Додатково: sns.kdeplot(data=df, x='total_amount', hue='category', fill=True) — порівняння розподілів категорій на одному графіку

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

with open('transactions.csv', 'r', encoding='utf-8') as f_in, \
        open('transactions_clean_for_plots.csv', 'w', encoding='utf-8') as f_out:
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


tx = pd.read_csv('transactions_clean_for_plots.csv')


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
products['category'] = products['category'].astype(str).str.strip()
products['category'] = products['category'].str.capitalize()
products_clean = products[['product_id', 'category', 'unit_price']]


merged_df = pd.merge(tx, products_clean, on='product_id', how='left')


merged_df['clean_total_amount'] = merged_df['quantity'] * merged_df['unit_price'] * (1 - merged_df['discount'])

df_filtered = merged_df[merged_df['clean_total_amount'] > 0]


sns.set_theme(style="whitegrid")

plt.figure(figsize=(10, 6))
sns.boxplot(
    data=df_filtered,
    x='category',
    y='clean_total_amount',
    hue='category',
    legend=False,
    palette='Set3'
)
plt.title('1. Boxplot')
plt.xlabel('Категорія товару')
plt.ylabel('Сума')
plt.xticks(rotation=30, ha='right')
plt.ticklabel_format(style='plain', axis='y')
plt.tight_layout()
plt.show()


plt.figure(figsize=(10, 6))
sns.violinplot(
    data=df_filtered,
    x='category',
    y='clean_total_amount',
    hue='category',
    legend=False,
    palette='Set3'
)
plt.title('2. Violinplot')
plt.xlabel('Категорія товару')
plt.ylabel('Сума транзакції')
plt.xticks(rotation=30, ha='right')
plt.ticklabel_format(style='plain', axis='y')
plt.tight_layout()
plt.show()

plt.figure(figsize=(10, 6))
sns.kdeplot(
    data=df_filtered,
    x='clean_total_amount',
    hue='category',
    fill=True,
    alpha=0.35,
    palette='Set1'
)
plt.title('3. KDEplot')
plt.xlabel('Сума транзакції')
plt.ylabel('Щільність розподілу')
plt.ticklabel_format(style='plain', axis='x')
plt.tight_layout()
plt.show()
