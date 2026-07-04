# 🛒 Retail Data Analytics

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![SQLite](https://img.shields.io/badge/Database-SQLite-003B57?logo=sqlite&logoColor=white)](#)
[![Pandas](https://img.shields.io/badge/Pandas-Data%20Analysis-150458?logo=pandas&logoColor=white)](https://pandas.pydata.org/)
[![GitHub](https://img.shields.io/badge/Git-GitHub-black?logo=github)](https://github.com/)

**Командний навчальний проєкт з Data Analytics на базі SQLite**

---

## 📌 Опис

Проєкт присвячений аналізу даних інтернет-магазину. Використовуються SQL, SQLite та Python для отримання, очищення, аналізу та візуалізації даних. У роботі реалізовано повний цикл Data Analytics: завантаження даних, Data Cleaning, SQL-запити, побудова бізнес-метрик, аналітичних звітів і графіків.

## 🛠 Технологічний стек

- Python 3
- SQLite
- Pandas
- NumPy
- Matplotlib
- Seaborn
- Git & GitHub

## 📁 Структура проєкту

```text
.
├── main.py                 # головна точка запуску
├── cleaning.py             # централізоване очищення всіх джерел даних
├── task_*.py               # перевірені файли окремих завдань
├── cleaned_data/           # створюється автоматично, у Git не додається
├── results/                # створюється автоматично, у Git не додається
└── README.md
```

## 🗄 Файли даних

Усі завдання працюють з одними й тими самими вхідними файлами, але виконують різні види аналізу.

| Файл | Формат | Обсяг | Записів | Опис |
|---|---|---:|---:|---|
| `analytics_practice.db` | SQLite | ~473 MB | 17 таблиць | Навчальна реляційна база для SQL-завдань |
| `company_data.xlsx` | Excel, 5 аркушів | ~350 KB | 5050+128+120+505+572 | Customers, Products, Stores, Employees, Inventory |
| `transactions.csv` | CSV | ~7.5 MB | 101 000 | Транзакції за 2024–2025 роки |
| `support_tickets.tsv` | TSV | ~1 MB | 15 150 | Звернення в підтримку |
| `api_logs.json` | JSON | ~13 MB | 50 000 | Логи API-запитів |
| `marketing.csv` | CSV | ~7 KB | 60 | Маркетингові кампанії з метриками |
| `salaries.csv` | CSV | ~660 KB | 10 157 | Помісячні зарплати |
| `returns.csv` | CSV | ~580 KB | 5 000 | Повернення товарів |
| `customers.csv` | CSV | ~490 KB | 5 050 | Клієнти, окремий файл для зручності |
| `employees.csv` | CSV | ~57 KB | 505 | Співробітники, окремий файл |
| `stores.csv` | CSV | ~6 KB | 120 | Магазини, окремий файл |

Усього використовується 11 вхідних файлів. `analytics_practice.db` очищається в окрему копію `cleaned_data/analytics_practice_cleaned.db`; оригінальна база не змінюється.

## 🔗 Схема зв'язків між файлами

```text
customers.customer_id -> transactions.customer_id -> support_tickets.customer_id
customers.customer_id -> api_logs.user_id
products.product_id   -> transactions.product_id -> inventory.product_id
products.product_id   -> marketing.product_id
stores.store_id       -> transactions.store_id -> employees.store_id
stores.store_id       -> inventory.store_id
employees.employee_id -> salaries.employee_id
```

## ⚠️ Навмисно забруднені дані

Набір даних містить навмисні помилки, що імітують реальну роботу дата-аналітика.

| Тип помилки | Де зустрічається |
|---|---|
| Дати у форматах `YYYY-MM-DD`, `DD/MM/YYYY`, `DD.MM.YYYY` | `transactions.csv` |
| Різний регістр: male, Male, MALE, M | `gender`, Customers |
| Описка Femail замість Female | `gender`, Customers |
| Коди UA, PL, DE замість назв країн | `customers.csv` |
| Ціни як рядки: `$49.99`, `€120.00` | `unit_price`, Products |
| Пропуски: NaN, None, N/A, NULL, порожній рядок, ? | Усі файли |
| Зайві коми та зсув колонок | `transactions.csv`, ~1% |
| Сторонні ID: customer_id=999999, store_id=-1 | Transactions, Employees |
| Дублікати рядків | Усі файли, ~1% |
| `total_amount` не відповідає `qty × price × discount` | Transactions, ~3% |
| CTR понад 100% | Marketing |
| Кількість дорівнює 0 або є від'ємною | Transactions |
| Дата в майбутньому | Customers, Stores, Employees |
| Статус-код як рядок `"200"` | `api_logs.json` |
| `has_cafe` як yes/no | Stores |
| Зарплата як рядок `"$3500"` | Employees |
| JSON з зайвими або відсутніми полями | `api_logs.json`, ~1% |

## 📦 Формат здачі

Команда здає:

- один Python-файл `.py` з очищенням даних і всіма виконаними завданнями;
- презентацію у форматі PDF на 5–7 слайдів.

Під час розробки очищення та 22 завдання зберігаються в окремих файлах. Перед здачею вони об'єднуються в один `main.py`.

## 🧹 Data Cleaning

Файл `cleaning.py` містить єдиний для всієї команди процес очищення даних:

- перевірка пропущених значень і дублікатів;
- приведення дат, чисел та інших типів;
- уніфікація текстових значень;
- нормалізація назв країн;
- виправлення зміщених рядків у транзакціях;
- перевірка зовнішніх ID та бізнес-логіки;
- створення очищених CSV, TSV, JSON, Excel і копії SQLite;
- формування звіту `cleaning_report.json`.

Оригінальні файли не змінюються. Результати записуються до папки `cleaned_data`.

### Порядок роботи команди

1. Під час командної розробки `cleaning.py` зберігається в репозиторії як окремий спільний модуль, щоб не дублювати очищення у файлах завдань.
2. Учасники завантажують у свої гілки лише власні файли завдань `.py`.
3. Перед фінальною здачею код із `cleaning.py` та код усіх 22 завдань об'єднуються в один файл `main.py`. Окремий файл `cleaning.py` до комплекту здачі не входить.
4. Під час запуску фінальний `main.py` спочатку виконує очищення, автоматично створює папку `cleaned_data`, а потім запускає всі завдання.
5. Код усіх завдань використовує дані з `cleaned_data`, щоб розрахунки виконувалися на однаковому наборі очищених даних.
6. Папку `cleaned_data` і великі файли `.db` не потрібно додавати до GitHub, оскільки вони створюються локально під час запуску.

Запуск:

```bash
python main.py
```

## 📊 Реалізовані завдання

### SQL

- SELECT
- JOIN
- GROUP BY
- ORDER BY
- Aggregate Functions

### Аналіз

- Revenue Analysis
- Profitability Analysis
- Returns Analysis
- Payment Method Analysis
- Customer Analysis
- Churn Risk Scoring

### Візуалізації

- Lineplot
- Barplot
- Scatterplot
- Boxplot
- Violinplot
- Heatmap
- Dashboard
- Stacked Bar Chart

### Результати завдань

Кожне з 22 завдань виконується з одного підсумкового Python-файлу. Під час запуску основні таблиці та висновки виводяться у консоль, а створені графіки й додаткові таблиці автоматично зберігаються у папці `results`.

Для кожного завдання використовується окрема папка `results/task_N`, де `N` є номером завдання. Файли результатів повторно створюються під час запуску коду, тому їх не потрібно готувати вручну.

## 📈 Основні метрики

- Revenue
- Profit
- Refund Amount
- Return Rate
- Average Rating
- Days Since Last Order
- Frequency Decline
- Churn Risk

## 🌿 Git Flow

```bash
git switch main
git pull origin main

git switch -c username/task-name

git add .
git commit -m "Complete task"
git push origin username/task-name
```

Після завершення роботи створюється Pull Request до `main`.

## 👥 Команда

- Сергій
- Дмитро
- Світлана
- Юлія
- Оксана

## ✅ Висновок

Проєкт демонструє повний цикл роботи дата-аналітика: від очищення та підготовки даних до створення аналітичних звітів, бізнес-метрик і візуалізацій для підтримки прийняття рішень.
