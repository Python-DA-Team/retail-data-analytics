import pandas as pd

excel_file = 'company_data.xlsx'
transactions_path = 'transactions.csv'

df_stores = pd.read_excel(excel_file, sheet_name='Stores')
df_employees = pd.read_excel(excel_file, sheet_name='Employees')

try:
    df_transactions = pd.read_csv(
        transactions_path,
        sep=None,
        engine='python',
        on_bad_lines='skip'
    )

    needed_cols = ['store_id', 'total_amount', 'is_return']
    df_transactions = df_transactions[[col for col in needed_cols if col in df_transactions.columns]]

except Exception as e:
    print(f'ERROR: {e}')
    df_transactions = pd.read_csv(transactions_path, sep=';', on_bad_lines='skip')

if df_transactions.empty or 'total_amount' not in df_transactions.columns:
    print('ERROR')

df_transactions['is_return'] = pd.to_numeric(df_transactions['is_return'], errors='coerce').fillna(0)
df_transactions['total_amount'] = pd.to_numeric(df_transactions['total_amount'], errors='coerce').fillna(0)
df_transactions['store_id'] = pd.to_numeric(df_transactions['store_id'], errors='coerce').fillna(-1)

df_valid_sales = df_transactions[df_transactions['is_return'] == 0]
store_revenue = df_valid_sales.groupby('store_id')['total_amount'].sum().reset_index()
store_revenue.columns = ['store_id', 'total_revenue']

# співробітники, що реально працюють (зі статусом активно)
df_employees['status'] = df_employees['status'].astype(str).str.strip().str.lower()
df_active_emp = df_employees[df_employees['status'] == 'active']
employee_count = df_active_emp.groupby('store_id')['employee_id'].count().reset_index()
employee_count.columns = ['store_id', 'employee_count']

df_analytics = df_stores.merge(store_revenue, on='store_id', how='left').fillna(0)
df_analytics = df_analytics.merge(employee_count, on='store_id', how='left').fillna(0)

df_analytics['store_format'] = df_analytics['store_format'].astype(str).str.strip()
df_analytics['store_format'] = df_analytics['store_format'].replace({'Streett': 'Street', 'Mal': 'Mall'})

# метрики в розрізі магазинів
df_analytics['revenue_per_sqm'] = df_analytics.apply(
    lambda r: r['total_revenue'] / r['size_sqm'] if str(r['store_format']).lower() != 'online' and r[
        'size_sqm'] > 0 else 0,
    axis=1
)

df_analytics['revenue_per_employee'] = df_analytics.apply(
    lambda r: r['total_revenue'] / r['employee_count'] if r['employee_count'] > 0 else 0,
    axis=1
)

# ефективності по формату магазина
df_offline_only = df_analytics[df_analytics['store_format'].str.lower() != 'online']
format_grouped = df_offline_only.groupby('store_format').agg(
    total_revenue=('total_revenue', 'sum'),
    total_size=('size_sqm', 'sum')
).reset_index()
format_grouped['revenue_per_sqm'] = format_grouped['total_revenue'] / format_grouped['total_size']

# найефективніший магазин (метод рангів для офлайн магазинів)
df_rank = df_offline_only[df_offline_only['size_sqm'] > 0].copy()
if not df_rank.empty:
    df_rank['rank_sqm'] = df_rank['revenue_per_sqm'].rank(ascending=False)
    df_rank['rank_emp'] = df_rank['revenue_per_employee'].rank(ascending=False)
    df_rank['combined_score'] = df_rank['rank_sqm'] + df_rank['rank_emp']
    best_store = df_rank.sort_values(by='combined_score', ascending=True).iloc[0]
else:
    best_store = None

format_print = format_grouped.copy()
format_print['revenue_per_sqm'] = format_print['revenue_per_sqm'].map('{:,.2f}'.format)
print(f'Revenue per square meter:\n\n{format_print[["store_format", "revenue_per_sqm"]].to_string(index=False)}\n')
print('-' * 20)

df_console = df_analytics.copy()
df_console['total_revenue'] = df_console['total_revenue'].map('{:,.2f}'.format)
df_console['revenue_per_sqm'] = df_console['revenue_per_sqm'].map('{:,.2f}'.format)
df_console['revenue_per_employee'] = df_console['revenue_per_employee'].map('{:,.2f}'.format)
print(f'Загальний звіт по магазинам (перші 20):\n\n'
      f'{df_console[["store_id", "store_name", "store_format", "size_sqm", "employee_count", "total_revenue", "revenue_per_sqm", "revenue_per_employee"]].head(20).to_string(index=False)}\n')
print('-' * 20)


if best_store is not None:
    print(f'Найефективніший фізичний магазин за обома показниками:\n\n',
          f'Магазин: {best_store["store_name"]} (ID: {best_store["store_id"]})\n',
          f'Країна: {best_store["country"]}. Формат: {best_store["store_format"]}\n',
          f'Площа: {best_store["size_sqm"]} кв.м. Штат: {int(best_store["employee_count"])} співробітників\n',
          f'Виручка/кв. метр: {best_store["revenue_per_sqm"]:,.2f}\n',
          f'Виручка/одного співробітника: {best_store["revenue_per_employee"]:,.2f}')
