# 🛒 Retail Data Analytics

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![SQLite](https://img.shields.io/badge/Database-SQLite-003B57?logo=sqlite&logoColor=white)](#)
[![Pandas](https://img.shields.io/badge/Pandas-Data%20Analysis-150458?logo=pandas&logoColor=white)](https://pandas.pydata.org/)
[![GitHub](https://img.shields.io/badge/Git-GitHub-black?logo=github)](https://github.com/)

**Командний навчальний проєкт з Data Analytics на базі SQLite**
:::

------------------------------------------------------------------------

## 📌 Опис

Проєкт присвячений аналізу даних інтернет-магазину. Використовуються
SQL, SQLite та Python для отримання, очищення, аналізу та візуалізації
даних. У роботі реалізовано повний цикл Data Analytics: завантаження
даних, Data Cleaning, SQL-запити, побудова бізнес-метрик, аналітичних
звітів і графіків.

## 🛠 Технологічний стек

-   Python 3
-   SQLite
-   Pandas
-   NumPy
-   Matplotlib
-   Seaborn
-   Git & GitHub

## 📁 Структура проєкту

``` text
.
├── online_store.db
├── main.py
├── README.md
└── images/
```

## 🗄 Основні таблиці

  Таблиця             Призначення
  ------------------- -------------------
  customers           Клієнти
  customer_pii        Контактні дані
  orders              Замовлення
  order_items         Позиції замовлень
  products            Товари
  categories          Категорії
  suppliers           Постачальники
  payments            Оплати
  returns             Повернення
  reviews             Відгуки
  employees           Співробітники
  employee_salaries   Зарплати
  promotions          Акції
  shipments           Доставки
  shippers            Служби доставки
  inventory           Склад
  warehouses          Склади

## 🔗 Схема зв'язків

``` text
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

-   Перевірка пропущених значень
-   Видалення дублікатів
-   Перетворення типів даних
-   Уніфікація текстових полів
-   Нормалізація назв країн
-   Перевірка бізнес-логіки

## 📊 Реалізовані завдання

### SQL

-   SELECT
-   JOIN
-   GROUP BY
-   ORDER BY
-   Aggregate Functions

### Аналіз

-   Revenue Analysis
-   Profitability Analysis
-   Returns Analysis
-   Payment Method Analysis
-   Customer Analysis
-   Churn Risk Scoring

### Візуалізації

-   Lineplot
-   Barplot
-   Scatterplot
-   Boxplot
-   Violinplot
-   Heatmap
-   Dashboard
-   Stacked Bar Chart

## 📈 Основні метрики

-   Revenue
-   Profit
-   Refund Amount
-   Return Rate
-   Average Rating
-   Days Since Last Order
-   Frequency Decline
-   Churn Risk

## 🌿 Git Flow

``` bash
git switch main
git pull origin main

git switch -c username/task-name

git add .
git commit -m "Complete task"
git push origin username/task-name
```

Після завершення роботи створюється Pull Request до `main`.

## 👥 Команда

-   Сергій
-   Дмитро
-   Світлана
-   Юлія
-   Оксана

## ✅ Висновок

Проєкт демонструє повний цикл роботи дата-аналітика: від роботи з
реляційною базою даних SQLite до створення аналітичних звітів,
бізнес-метрик і візуалізацій для підтримки прийняття рішень.
