# Retail Data Analytics

Командний навчальний проєкт з аналізу даних роздрібної торгівлі за 2024–2025 роки. Проєкт охоплює продуктовий портфель, виручку, прибутковість, повернення, часові ряди, фінансове моделювання, якість даних і побудову дашбордів.

## Технології

- Python 3
- pandas, NumPy
- matplotlib, seaborn
- Jupyter Notebook
- Git і GitHub

## Дані

У завданнях використовуються `transactions.csv`, `returns.csv`, `marketing.csv`, `salaries.parquet` і таблиці `Products`, `Stores`, `Employees`, `Inventory` з `company_data.xlsx`.

> Файли з персональними даними, секретами або великими наборами даних не додавайте до репозиторію без узгодження.

## Блок 1 — Product & Revenue Analysis / Finance & Strategy Analysis

Фокус: аналіз продуктового портфеля, ціноутворення, виручка та кошики.

### Базові завдання (pandas)

1. **Топ-10 товарів за виручкою.** Згрупувати `transactions.csv` за `product_id` (лише продажі, без повернень), порахувати `sum(total_amount)`, об'єднати з `Products` із `company_data.xlsx` та вивести таблицю.
2. **Розподіл виручки за категоріями.** Побудувати `pivot_table`: категорії у рядках, місяці у стовпцях, значення — сума `total_amount`. Визначити категорію-лідера кожного місяця.
3. **Середній чек за магазинами.** Згрупувати транзакції за `store_id`, об'єднати зі `Stores` і визначити магазини з найвищим та найнижчим середнім чеком.

### Візуалізація (matplotlib / seaborn)

4. **Barplot:** порівняти виручку за категоріями у 2024 та 2025 роках.
5. **Heatmap:** показати кореляції `unit_price`, `cost_price`, `margin_pct`, `quantity`, `total_amount`; використати `annot=True` і `cmap='coolwarm'`.
6. **Boxplot / Violinplot + KDE:** дослідити розподіл додатного `total_amount` за категоріями, показати медіану, квартилі, щільність і викиди. Додатково побудувати `sns.kdeplot(..., hue='category', fill=True)`.

### Просунуті завдання

7. **ABC-аналіз товарів.** Порахувати виручку на товар, відсортувати за спаданням і додати кумулятивну частку через `cumsum()`: A — перші 70% виручки, B — 70–90%, C — останні 10%. Визначити кількість товарів у кожній групі.
8. **Market Basket Analysis.** Для кожного `customer_id` зібрати категорії товарів, придбаних за один день, і знайти топ-5 пар категорій. Якщо спільних денних покупок мало — групувати за клієнтом і ISO-тижнем. Для пар використати `itertools.combinations()`.
9. **Аналіз знижок.** Розділити транзакції на `discount_percent == 0` і `discount_percent > 0`, порівняти середню кількість одиниць та виручку й оцінити ефективність знижок.
10. **Cohort Retention.** Визначити місяць першої покупки кожного клієнта і перевірити повторні покупки в тій самій категорії в наступні місяці. Побудувати cohort table з відсотком утримання.

### Додаткове завдання

11. **Естимація CLV.** Розрахувати місячні ARPU та Average Purchase Frequency, середній життєвий цикл клієнта і `CLV = ARPU × frequency × lifetime`. Сегментувати клієнтів на Low, Medium, High і Premium.

## Блок 2 — Profitability, Pareto, Time Series, Dashboards & Data Quality

Фокус: прибутковість, Pareto-аналіз, часові ряди, дашборди та якість даних.

### Базові завдання (pandas)

1. **Profit-аналіз.** Об'єднати `transactions.csv` із Products і Stores. Для продажів (`is_return == 0`) розрахувати виручку, собівартість `quantity × cost_price`, прибуток з урахуванням 5% операційних витрат і місячні revenue, cost, profit та margin %. Визначити найприбутковіший і найзбитковіший місяці.
2. **Pareto Analysis (80/20).** Розрахувати частку кожного продукту у виручці, відсортувати, застосувати `cumsum()` і визначити кількість продуктів, які формують 80% виручки. Побудувати bar + line.
3. **Data Quality Score.** Для кожного датафрейму розрахувати completeness, uniqueness, validity, consistency та середній `overall_score`. Визначити найкращий і найгірший файли.

### Візуалізація (matplotlib / seaborn)

4. **Stacked bar:** показати revenue, cost і profit за 12 місяців 2025 року через `plt.bar(..., bottom=...)`.
5. **Pareto curve:** показати cumulative revenue за продуктами (bar + line) і додати пунктирну лінію 80%.
6. **Dashboard 2×2:** revenue trend, profit margin by store format, returns rate by category і monthly transaction count.

### Просунуті завдання

7. **Time Series Analysis.** Агрегувати денну виручку, додати `dayofweek`, `month`, `is_weekend`, `is_holiday_season`, 7- і 30-денні rolling averages. Через `shift()` знайти топ-5 денних зростань і падінь та аномалії понад 2 стандартні відхилення.
8. **Returns Analysis.** Розрахувати return rate за категоріями, середню суму повернення за причинами, зв'язок знижки з поверненнями, return rate за способом оплати та середній час між покупкою і поверненням.
9. **Магазинна аналітика.** Розрахувати revenue per square meter за форматом магазину та revenue per employee за магазинами. Визначити найефективніший магазин за обома метриками.
10. **Фінансове моделювання.** Побудувати місячний P&L: Revenue, COGS, Gross Profit, Marketing Cost, Salary Cost, Operating Profit з 5% операційних витрат і Net Margin %.

### Додаткове завдання

11. **Динамічний executive dashboard.** Реалізувати `generate_dashboard(data_path, month)` з KPI Revenue, Profit, Margin %, Customers Count, Avg Order Value і Return Rate та двома додатковими графіками. Зберегти `dashboard_{month}.png` для `2025-01`, `2025-06`, `2025-12` і порівняти місяці.

## Рекомендована структура

```text
retail-data-analytics/
├── data/                 # локальні дані, якщо дозволено
├── notebooks/            # дослідницькі ноутбуки
├── src/                  # Python-скрипти
├── outputs/
│   ├── figures/          # PNG/JPG графіки
│   └── tables/           # підсумкові CSV/XLSX
├── requirements.txt
└── README.md
```

Назви файлів мають містити номер блоку, номер завдання та коротку назву, наприклад:

```text
src/block_1/task_04_category_revenue.py
outputs/figures/block_1_task_04_category_revenue.png
```

## Командний процес

1. Оновити локальний `main`: `git switch main` і `git pull origin main`.
2. Створити окрему гілку для завдання: `git switch -c username/block-1-task-04`.
3. Додати код, короткі висновки й результат виконання.
4. Зробити commit і push у свою гілку.
5. Створити Pull Request: `base: main` ← `compare: робоча гілка`.
6. Один завершений логічний результат — один Pull Request.
7. Після перевірки та merge оновити `main` перед наступним завданням.

Не завантажуйте робочі файли безпосередньо в `main` і не змінюйте файли інших учасників без узгодження.

## Що має бути в Pull Request

- номер блоку та завдання;
- вихідний код або notebook;
- збережений графік/таблиця, якщо він передбачений;
- короткий опис методу;
- 2–5 основних висновків;
- відсутність випадкових змін або видалень чужих файлів.

## Команда

Репозиторій належить організації **Python-DA-Team**. Робоча команда — **data-analysts**.
