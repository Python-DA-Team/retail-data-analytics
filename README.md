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
├── tasks/                  # файли із завданнями учасників
├── cleaned_data/           # створюється автоматично, у Git не додається
├── README.md
└── images/
```

## 🗄 Основні таблиці

| Таблиця | Призначення |
|---|---|
| customers | Клієнти |
| customer_pii | Контактні дані |
| orders | Замовлення |
| order_items | Позиції замовлень |
| products | Товари |
| categories | Категорії |
| suppliers | Постачальники |
| payments | Оплати |
| returns | Повернення |
| reviews | Відгуки |
| employees | Співробітники |
| employee_salaries | Зарплати |
| promotions | Акції |
| shipments | Доставки |
| shippers | Служби доставки |
| inventory | Склад |
| warehouses | Склади |

## 🔗 Схема зв'язків

```text
customers ── customer_pii
      │
      └──── orders ───── payments
              │
              ├──── returns
              ├──── shipments ── shippers
              ├──── employees ── employee_salaries
              └──── order_items ── products ── categories
                                 ├──────────── suppliers
                                 └──────────── promotions

products ── inventory ── warehouses
customers ── reviews
```

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
