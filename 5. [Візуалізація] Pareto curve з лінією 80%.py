import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


with open('transactions.csv', 'r', encoding='utf-8') as f_in, \
     open('transactions_clean_pareto.csv', 'w', encoding='utf-8') as f_out:
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

tx = pd.read_csv('transactions_clean_pareto.csv')


tx['quantity'] = pd.to_numeric(tx['quantity'], errors='coerce').abs().replace(0, 1).fillna(1).astype(int)
tx['discount_percent'] = pd.to_numeric(tx['discount_percent'], errors='coerce').fillna(0.0)
tx.loc[tx['discount_percent'] > 1, 'discount_percent'] = tx['discount_percent'] / 100.0

products = pd.read_excel('company_data.xlsx', sheet_name='Products')
products['unit_price'] = products['unit_price'].astype(str).str.replace(r'[$\u20AC\u00A3,]', '', regex=True)
products['unit_price'] = pd.to_numeric(products['unit_price'], errors='coerce').fillna(0.0)
products_clean = products[['product_id', 'unit_price']]

df = pd.merge(tx, products_clean, on='product_id', how='left')

df['revenue'] = df['quantity'] * df['unit_price'] * (1 - df['discount_percent'])


product_revenue = df.groupby('product_id')['revenue'].sum().reset_index()


product_revenue = product_revenue.sort_values(by='revenue', ascending=False).reset_index(drop=True)


product_revenue['cum_revenue'] = product_revenue['revenue'].cumsum()


total_revenue = product_revenue['revenue'].sum()
product_revenue['cum_percentage'] = (product_revenue['cum_revenue'] / total_revenue) * 100


product_revenue['product_id'] = product_revenue['product_id'].astype(str)


fig, ax1 = plt.subplots(figsize=(14, 7))


color_bar = '#4f81bd'
ax1.bar(product_revenue['product_id'], product_revenue['revenue'], color=color_bar, alpha=0.85, label='Виручка продукту')
ax1.set_xlabel('ID Продукту', fontsize=12, labelpad=10)
ax1.set_ylabel('Виручка', color=color_bar, fontsize=12)
ax1.tick_params(axis='y', labelcolor=color_bar)

clean_labels = [str(int(float(x))) for x in product_revenue['product_id']]

ax1.set_xticks(range(len(product_revenue)))
ax1.set_xticklabels(clean_labels, rotation=90, fontsize=5)

ax1.yaxis.get_major_formatter().set_scientific(False)



ax2 = ax1.twinx()
color_line = '#c00000'
ax2.plot(product_revenue['product_id'], product_revenue['cum_percentage'], color=color_line, marker='o', ms=4, lw=2, label='Кумулятивний %')
ax2.set_ylabel('Кумулятивний відсоток', color=color_line, fontsize=12)
ax2.tick_params(axis='y', labelcolor=color_line)
ax2.set_ylim(0, 105)


ax2.axhline(y=80, color='gray', linestyle='--', linewidth=1.5, label='Межа Парето (80%)')


plt.title('Аналіз Парето', fontsize=16, pad=20)


lines1, labels1 = ax1.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax1.legend(lines1 + lines2, labels1 + labels2, loc='center right', frameon=True)

ax1.grid(True, axis='y', linestyle=':', alpha=0.6)

plt.tight_layout()
plt.show()

