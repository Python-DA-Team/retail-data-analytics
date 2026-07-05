import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from pathlib import Path

sns.set_theme(style='whitegrid')
plt.rcParams['figure.figsize'] = (10, 5)

BASE_DIR = Path(__file__).resolve().parent
CLEAN_DIR = BASE_DIR / "cleaned_data"

files_to_check = {
   'Customers': CLEAN_DIR / 'customers_cleaned.csv',
   'Employees': CLEAN_DIR / 'employees_cleaned.csv',
   'Marketing': CLEAN_DIR / 'marketing_cleaned.csv',
   'Stores': CLEAN_DIR / 'stores_cleaned.csv',
   'Returns': CLEAN_DIR / 'returns_cleaned.csv'
}

if not all(path.exists() for path in files_to_check.values()):
   from cleaning import main as clean_data
   clean_data()

dq_results = []

for name, path in files_to_check.items():
   if not path.exists():
      print(f'Не знайдено файл {name} за шляхом {path}.')
      continue

   df = pd.read_csv(path)
   total_rows = len(df)

   if total_rows == 0:
      continue

# перевіряю заповненість файлів даними
   total_cells = df.size
   missing_cells = df.isna().sum().sum()
   completeness = 1.0 - (missing_cells / total_cells) if total_cells > 0 else 1.0

# перевіряю на наявність дублікатів
   duplicate_rows = df.duplicated().sum()
   uniqueness = 1.0 - (duplicate_rows / total_rows)

# перевіряю рядки на наявність аномалій та коректність типів даних
   valid_rows_count = total_rows
   consistent_rows_count = total_rows

   if name == 'Customers':
      df['age'] = pd.to_numeric(df['age'], errors='coerce')
      df['total_orders'] = pd.to_numeric(df['total_orders'], errors='coerce')

      anomalies = df[(df['age'] > 100) | (df['customer_id'].isna()) | (df['age'].isna())]
      valid_rows_count = total_rows - len(anomalies)

      consistent = df[(df['age'] > 0) & (df['age'] <= 100) & (df['total_orders'] >= 0)]
      consistent_rows_count = len(consistent)

   elif name == 'Employees':
      if df['salary'].dtype == 'object':
         df['salary'] = df['salary'].astype(str).str.replace(r'[₴\$€£]|(?:USD|UAH|EUR|GBP)|\s|', "", regex=True)
      df['salary'] = pd.to_numeric(df['salary'], errors='coerce')
      df['performance_score'] = pd.to_numeric(df['performance_score'], errors='coerce')

      anomalies = df[df['employee_id'].isna() | df['department'].isna() | df['salary'].isna()]
      valid_rows_count = total_rows - len(anomalies)
      consistent = df[(df['performance_score'] >= 0) & (df['performance_score'] <= 100) & (df['salary'] > 0)]
      consistent_rows_count = len(consistent)

   elif name == 'Marketing':
      if df['budget'].dtype == 'object':
         df['budget'] = df['budget'].astype(str).str.replace(r'[₴\$€£]|(?:USD|UAH|EUR|GBP)|\s|', "", regex=True)
      df['budget'] = pd.to_numeric(df['budget'], errors='coerce')

      if df['clicks'].dtype == 'object':
         df['clicks'] = df['clicks'].astype(str).str.replace(r'[₴\$€£]|(?:USD|UAH|EUR|GBP)|\s|', "", regex=True)
      df['clicks'] = pd.to_numeric(df['clicks'], errors='coerce')

      anomalies = df[(df['budget'] < 0) | (df['clicks'] < 0) | (df['budget'].isna()) | (df['clicks'].isna())]
      valid_rows_count = total_rows - len(anomalies)
      consistent = df[(df['ctr_pct'] >= 0) & (df['ctr_pct'] <= 100) &
                      (df['conversion_rate_pct'] >= 0) & (df['conversion_rate_pct'] <= 100)]
      consistent_rows_count = len(consistent)

   elif name == 'Stores':
      df['size_sqm'] = pd.to_numeric(df['size_sqm'], errors='coerce')
      anomalies = df[(df['size_sqm'] <= 0) | (df['size_sqm'].isna())]
      valid_rows_count = total_rows - len(anomalies)

      consistent = df[df['has_cafe'].astype(str).str.lower().isin(['true', 'false', '1', '0', 'yes', 'no']) &
                      df['has_parking'].astype(str).str.lower().isin(['true', 'false', '1', '0', 'yes', 'no'])]
      consistent_rows_count = len(consistent)

   elif name == 'Returns':
      df['refund_amount'] = pd.to_numeric(df['refund_amount'], errors='coerce')
      df['total_amount'] = pd.to_numeric(df['total_amount'], errors='coerce')
      df['quantity'] = pd.to_numeric(df['quantity'], errors='coerce')

      anomalies = df[(df['refund_amount'].abs() > df['total_amount'].abs()) | df['refund_amount'].isna()]
      valid_rows_count = total_rows - len(anomalies)
      consistent = df[df['quantity'] >= 1]
      consistent_rows_count = len(consistent)

   validity = valid_rows_count / total_rows
   consistency = consistent_rows_count / total_rows
   overall_score = (completeness + uniqueness + validity + consistency) / 4.0

   dq_results.append({
      'File Name': name,
      'Повнота (%)': round(completeness * 100, 2),
      'Унікальність (%)': round(uniqueness * 100, 2),
      'Валідність (%)': round(validity * 100, 2),
      'Узгодженість (%)': round(consistency * 100, 2),
      'Загальна оцінка (%)': round(overall_score * 100, 2)
   })

df_dq_report = pd.DataFrame(dq_results)

print(f'\nЗвіт про якість даних(DATA QUALITY REPORT)\n\n{df_dq_report.to_string(index=False)}')
print('-' * 20)

best_file = df_dq_report.loc[df_dq_report['Загальна оцінка (%)'].idxmax()]
worst_file = df_dq_report.loc[df_dq_report['Загальна оцінка (%)'].idxmin()]

print(f"\nНайвищий DQ Score: файл '{best_file['File Name']}' з показником {best_file['Загальна оцінка (%)']}%")
print(f"Найнижчий DQ Score: файл '{worst_file['File Name']}' з показником {worst_file['Загальна оцінка (%)']}%")

df_melted = df_dq_report.melt(id_vars='File Name',
                              value_vars=['Повнота (%)', 'Унікальність (%)', 'Валідність (%)', 'Узгодженість (%)'],
                              var_name='Metric', value_name='Percentage')

plt.figure(figsize=(10, 5))
ax = sns.barplot(x='File Name', y='Percentage', hue='Metric', data=df_melted, palette='viridis')

for i, name in enumerate(df_dq_report['File Name']):
   score = df_dq_report.loc[df_dq_report['File Name'] == name, 'Загальна оцінка (%)'].values[0]
   plt.plot([i - 0.3, i + 0.3], [score, score], color='red', linestyle='--', linewidth=1.5)
   plt.text(i, score + 2, f'{score}%')

plt.title('Порівняльний аналіз метрик Data Quality Score')
plt.xlabel('Назва файлу / Датасету')
plt.ylabel('Показник якості (%)')
plt.ylim(0, 115)
plt.legend(title="Метрики оцінки", bbox_to_anchor=(1.02, 1), loc='upper left')
plt.tight_layout()
#
# plot_path = os.path.join(BASE_DIR, 'data_quality_report.png')
# plt.savefig(plot_path, dpi=300)
plt.show()