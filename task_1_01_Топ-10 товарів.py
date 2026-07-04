import os
import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
marketing_path = os.path.join(BASE_DIR, 'marketing.csv')
excel_path = os.path.join(BASE_DIR, 'company_data.xlsx')

df_marketing = pd.read_csv(marketing_path)
df_products = pd.read_excel(excel_path, sheet_name='Products')

if df_marketing['revenue_generated'].dtype == 'object':
    df_marketing['revenue_generated'] = df_marketing['revenue_generated'].astype(str).str.replace("", regex=True)
df_marketing['revenue_generated'] = pd.to_numeric(df_marketing['revenue_generated'], errors='coerce')

# групую товари та обчислюю загальну виручку
revenue_per_product = (
    df_marketing.groupby('product_id')['revenue_generated']
    .sum()
    .reset_index()
)
revenue_per_product.columns = ['product_id', 'total_amount']

final_table = pd.merge(revenue_per_product, df_products, on='product_id', how='inner')

# сортую товари з топ-10 за спаданням
top_10_products = (
    final_table.sort_values(by='total_amount', ascending=False)
    .head(10)
    .reset_index(drop=True)
)

top_10_products['total_amount'] = top_10_products['total_amount'].map('{:,.2f}'.format)
output_columns = ['product_name', 'category', 'total_amount']
available_columns = [col for col in output_columns if col in top_10_products.columns]

print(f'\nТОП-10 товарів за виручкою:\n\n{top_10_products[available_columns].to_string(index=False)}')
print('-' * 20)