from __future__ import annotations

import csv
import json
import os
import re
import shutil
import sqlite3
from itertools import combinations
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "cleaned_data"
DATA_END = pd.Timestamp("2025-12-31 23:59:59")
NA_PATTERN = re.compile(r"^\s*(?:|nan|none|n/?a|null|\?)\s*$", re.I)
CLEANED_FILES = [
    "company_data_cleaned.xlsx",
    "customers_cleaned.csv",
    "employees_cleaned.csv",
    "stores_cleaned.csv",
    "marketing_cleaned.csv",
    "returns_cleaned.csv",
    "salaries_cleaned.csv",
    "transactions_cleaned.csv",
    "support_tickets_cleaned.tsv",
    "api_logs_cleaned.json",
    "cleaning_report.json",
]


def cleaned_data_exists() -> bool:
    return OUT.exists() and all((OUT / filename).exists() for filename in CLEANED_FILES)


def base_clean(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for col in df.select_dtypes(include=["object", "string"]).columns:
        text = df[col].astype("string").str.strip()
        df[col] = text.mask(text.str.match(NA_PATTERN, na=False), pd.NA)
    return df.drop_duplicates().reset_index(drop=True)


def number(series: pd.Series) -> pd.Series:
    text = series.astype("string")
    for symbol in ["$", "€", "₴", "%", ",", " units"]:
        text = text.str.replace(symbol, "", regex=False)
    return pd.to_numeric(text, errors="coerce")


def mixed_date(series: pd.Series) -> pd.Series:
    return pd.to_datetime(
        series.astype("string").str.strip(),
        format="mixed",
        dayfirst=True,
        errors="coerce",
    )


def dates(df: pd.DataFrame, columns: list[str], reject_future: bool = False) -> None:
    for col in columns:
        if col in df:
            parsed = mixed_date(df[col])
            df[col] = parsed.mask(parsed > DATA_END) if reject_future else parsed


def boolean(series: pd.Series) -> pd.Series:
    values = {"true": True, "yes": True, "1": True, "y": True,
              "false": False, "no": False, "0": False, "n": False}
    return series.astype("string").str.lower().str.strip().map(values).astype("boolean")


def valid_id(df: pd.DataFrame, col: str, allowed: set[int]) -> None:
    if col in df:
        values = pd.to_numeric(df[col], errors="coerce").round().astype("Int64")
        df[col] = values.where(values.isin(allowed))


def clean_customers(df: pd.DataFrame) -> pd.DataFrame:
    df = base_clean(df)
    gender = {"male": "Male", "m": "Male", "mle": "Male",
              "female": "Female", "f": "Female", "femail": "Female",
              "femal": "Female", "other": "Other", "rather": "Rather not to say"}
    countries = {"UA": "Ukraine", "PL": "Poland", "DE": "Germany",
                 "FR": "France", "IT": "Italy", "ES": "Spain", "GB": "UK"}
    if "gender" in df:
        original = df["gender"]
        df["gender"] = original.astype("string").str.lower().map(gender).fillna(original)
    if "country" in df:
        df["country"] = df["country"].replace(countries)
    dates(df, ["registration_date"], reject_future=True)
    if "age" in df:
        age = pd.to_numeric(df["age"], errors="coerce")
        df["age"] = age.where(age.between(14, 100))
    return df


def clean_products(df: pd.DataFrame) -> pd.DataFrame:
    df = base_clean(df)
    for col in ["category", "subcategory"]:
        if col in df:
            df[col] = df[col].astype("string").str.title()
    for col in ["unit_price", "cost_price", "margin_pct", "weight_kg"]:
        if col in df:
            df[col] = number(df[col])
    valid = df["unit_price"].gt(0) & df["cost_price"].ge(0)
    df.loc[~valid, ["unit_price", "cost_price"]] = np.nan
    df["margin_pct"] = np.where(
        valid, (df["unit_price"] - df["cost_price"]) / df["unit_price"] * 100, np.nan
    )
    return df


def clean_stores(df: pd.DataFrame) -> pd.DataFrame:
    df = base_clean(df)
    if "store_format" in df:
        df["store_format"] = df["store_format"].replace({"Streett": "Street", "Mal": "Mall"})
    for col in ["has_cafe", "has_parking"]:
        if col in df:
            df[col] = boolean(df[col])
    dates(df, ["open_date"], reject_future=True)
    if "size_sqm" in df:
        size = pd.to_numeric(df["size_sqm"], errors="coerce")
        df["size_sqm"] = size.where(size.gt(0))
    return df


def clean_employees(df: pd.DataFrame, store_ids: set[int]) -> pd.DataFrame:
    df = base_clean(df)
    if "department" in df:
        df["department"] = df["department"].astype("string").str.title().replace({"It": "IT", "Hr": "HR"})
    if "salary" in df:
        salary = number(df["salary"])
        df["salary"] = salary.where(salary.gt(0))
    dates(df, ["hire_date"], reject_future=True)
    valid_id(df, "store_id", store_ids)
    return df


def clean_inventory(df: pd.DataFrame, store_ids: set[int], product_ids: set[int]) -> pd.DataFrame:
    df = base_clean(df)
    valid_id(df, "store_id", store_ids)
    valid_id(df, "product_id", product_ids)
    stock = number(df["stock_quantity"])
    df["stock_quantity"] = stock.where(stock.ge(0)).astype("Int64")
    dates(df, ["last_restock_date"])
    return df


def read_broken_transactions(path: Path) -> tuple[pd.DataFrame, dict[str, int]]:
    fixed, tabs, shifted, rejected = [], 0, 0, 0
    with path.open(encoding="utf-8-sig", newline="") as source:
        header = next(csv.reader([source.readline()]))
        for raw in source:
            if "\t" in raw:
                raw, tabs = raw.replace("\t", ","), tabs + 1
            row = next(csv.reader([raw]))
            if len(row) == len(header) + 1 and row[4].strip() == "":
                row.pop(4)
                shifted += 1
            if len(row) != len(header):
                rejected += 1
                continue
            fixed.append(row)
    return pd.DataFrame(fixed, columns=header), {
        "rows_repaired": len(fixed), "tab_rows": tabs,
        "shifted_rows": shifted, "rejected_rows": rejected,
    }


def clean_transactions(df: pd.DataFrame, ids: dict[str, set[int]], prices: pd.Series) -> pd.DataFrame:
    df = base_clean(df)
    for col in ["transaction_id", "customer_id", "store_id", "product_id", "quantity", "is_return"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").round().astype("Int64")
    df["discount_percent"] = number(df["discount_percent"])
    df["total_amount"] = number(df["total_amount"])
    valid_id(df, "customer_id", ids["customer"])
    valid_id(df, "store_id", ids["store"])
    valid_id(df, "product_id", ids["product"])
    df["quantity"] = df["quantity"].where(df["quantity"].gt(0))
    df["is_return"] = df["is_return"].where(df["is_return"].isin([0, 1]))
    df["discount_percent"] = df["discount_percent"].where(df["discount_percent"].between(0, 100))
    dates(df, ["transaction_date"])
    df["payment_method"] = df["payment_method"].astype("string").str.title()
    df["currency"] = df["currency"].astype("string").str.upper().replace({"$": "USD", "€": "EUR", "₴": "UAH"})

    expected = (df["quantity"].astype("Float64") * df["product_id"].map(prices)
                * (1 - df["discount_percent"] / 100))
    expected = expected.where(df["is_return"].notna())
    return_rows = df["is_return"].eq(1).fillna(False)
    expected = expected.where(~return_rows, -expected.abs()).round(2)
    mismatch = expected.notna() & (df["total_amount"].sub(expected).abs() > 0.01)
    df.loc[mismatch, "total_amount"] = expected.loc[mismatch]
    return df


def clean_returns(df: pd.DataFrame, ids: dict[str, set[int]]) -> pd.DataFrame:
    df = base_clean(df)
    for kind in ["customer", "store", "product"]:
        valid_id(df, f"{kind}_id", ids[kind])
    quantity = pd.to_numeric(df["quantity"], errors="coerce").round().astype("Int64")
    df["quantity"] = quantity.where(quantity.gt(0))
    df["payment_method"] = df["payment_method"].astype("string").str.title()
    df["currency"] = df["currency"].astype("string").str.upper().replace({"$": "USD", "€": "EUR", "₴": "UAH"})
    df["return_reason"] = df["return_reason"].replace({"??": "Other", "OTHER": "Other", "other": "Other"})
    dates(df, ["transaction_date", "return_date"])
    df.loc[df["return_date"] < df["transaction_date"], "return_date"] = pd.NaT
    refund = number(df["refund_amount"])
    df["refund_amount"] = refund.where(refund.ge(0))
    return df


def clean_marketing(df: pd.DataFrame, product_ids: set[int]) -> pd.DataFrame:
    df = base_clean(df)
    valid_id(df, "product_id", product_ids)
    dates(df, ["start_date", "end_date"])
    for col in ["budget", "impressions", "clicks", "conversions", "revenue_generated"]:
        df[col] = number(df[col])
    df["target_category"] = df["target_category"].astype("string").str.title()
    impressions = df["impressions"].where(df["impressions"] > 0)
    clicks = df["clicks"].where(df["clicks"] >= 0).clip(upper=impressions)
    conversions = df["conversions"].where(df["conversions"] >= 0).clip(upper=clicks)
    df["clicks"], df["conversions"] = clicks, conversions
    df["ctr_pct"] = (clicks / impressions * 100).round(2).clip(0, 100)
    df["conversion_rate_pct"] = (conversions / clicks.replace(0, np.nan) * 100).round(2).clip(0, 100)
    df["roi_pct"] = ((df["revenue_generated"] - df["budget"])
                     / df["budget"].replace(0, np.nan) * 100).round(2)
    return df


def clean_salaries(df: pd.DataFrame, employee_ids: set[int]) -> pd.DataFrame:
    df = base_clean(df)
    valid_id(df, "employee_id", employee_ids)
    dates(df, ["month"])
    df["department"] = df["department"].astype("string").str.title().replace({"It": "IT", "Hr": "HR"})
    for col in ["base_salary", "bonus", "deductions", "hours_worked", "overtime_hours", "net_pay"]:
        df[col] = number(df[col])
    complete = df[["base_salary", "bonus", "deductions"]].notna().all(axis=1)
    df.loc[complete, "net_pay"] = (df.loc[complete, "base_salary"]
                                    + df.loc[complete, "bonus"]
                                    - df.loc[complete, "deductions"]).round(2)
    return df


def clean_support(df: pd.DataFrame, ids: dict[str, set[int]]) -> pd.DataFrame:
    df = base_clean(df)
    valid_id(df, "customer_id", ids["customer"])
    valid_id(df, "product_id", ids["product"])
    dates(df, ["ticket_date"])
    df["category"] = df["category"].astype("string").str.title()
    df["priority"] = df["priority"].replace({"1": "Low", "2": "Medium", "3": "High", "4": "Critical"})
    status = {"done": "Closed", "resolved": "Closed", "closed": "Closed",
              "in_progress": "InProgress", "in progress": "InProgress"}
    normalized = df["status"].astype("string").str.lower().str.strip()
    df["status"] = normalized.map(status).fillna(df["status"])
    score = pd.to_numeric(df["satisfaction_score"], errors="coerce")
    df["satisfaction_score"] = score.where(score.between(1, 5))
    return df


def clean_json(path: Path, customer_ids: set[int]) -> pd.DataFrame:
    try:
        df = pd.read_json(path, lines=True)
    except ValueError:
        df = pd.read_json(path)
    expected_columns = [
        "log_id", "timestamp", "endpoint", "method", "status_code",
        "response_time_ms", "user_id", "device_type", "ip_address",
        "user_agent", "error_message",
    ]
    df = base_clean(df).reindex(columns=expected_columns)
    valid_id(df, "user_id", customer_ids)
    dates(df, ["timestamp"])
    code = pd.to_numeric(df["status_code"], errors="coerce").round().astype("Int64")
    df["status_code"] = code.where(code.between(100, 599))
    response = pd.to_numeric(df["response_time_ms"], errors="coerce")
    df["response_time_ms"] = response.where(response.ge(0))
    return df


# PyCharm cannot infer the schema of a SQLite file selected at runtime.
# noinspection SqlNoDataSourceInspection,SqlResolve
def clean_database(source: Path, destination: Path) -> None:
    shutil.copy2(source, destination)
    with sqlite3.connect(destination) as con:
        con.execute("UPDATE customers SET gender='Male' WHERE lower(trim(gender)) IN ('m','male','mle')")
        con.execute("UPDATE customers SET gender='Female' WHERE lower(trim(gender)) IN ('f','female','femail','femal')")
        con.execute("UPDATE employees SET store_id=NULL WHERE store_id NOT IN (SELECT store_id FROM stores)")
        con.execute("UPDATE transactions SET customer_id=NULL WHERE customer_id NOT IN (SELECT customer_id FROM customers)")
        con.execute("UPDATE transactions SET store_id=NULL WHERE store_id NOT IN (SELECT store_id FROM stores)")
        tables = {
            row[0]
            for row in con.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        if "order_items" in tables:
            con.execute("UPDATE order_items SET quantity=NULL WHERE quantity<=0")
        con.execute("UPDATE api_logs SET status_code=NULL WHERE status_code<100 OR status_code>599")
        con.commit()


def save(frame: pd.DataFrame, filename: str, sep: str = ",") -> dict[str, int]:
    frame.to_csv(OUT / filename, index=False, sep=sep, encoding="utf-8-sig",
                 date_format="%Y-%m-%d %H:%M:%S")
    return {"rows": len(frame), "missing": int(frame.isna().sum().sum())}


def clean_data() -> None:
    if cleaned_data_exists():
        return

    OUT.mkdir(exist_ok=True)
    report: dict[str, object] = {}

    sheets = pd.read_excel(ROOT / "company_data.xlsx", sheet_name=None)
    customers_xlsx = clean_customers(sheets["Customers"])
    products = clean_products(sheets["Products"])
    stores_xlsx = clean_stores(sheets["Stores"])
    ids = {
        "customer": set(customers_xlsx["customer_id"].dropna().astype(int)),
        "product": set(products["product_id"].dropna().astype(int)),
        "store": set(stores_xlsx["store_id"].dropna().astype(int)),
    }
    employees_xlsx = clean_employees(sheets["Employees"], ids["store"])
    employee_ids = set(employees_xlsx["employee_id"].dropna().astype(int))
    inventory = clean_inventory(sheets["Inventory"], ids["store"], ids["product"])
    cleaned_sheets = {"Customers": customers_xlsx, "Products": products,
                      "Stores": stores_xlsx, "Employees": employees_xlsx,
                      "Inventory": inventory}
    with pd.ExcelWriter(OUT / "company_data_cleaned.xlsx", engine="openpyxl") as writer:
        for name, frame in cleaned_sheets.items():
            frame.to_excel(writer, sheet_name=name, index=False)
            report[f"company_data.xlsx::{name}"] = {"rows": len(frame), "missing": int(frame.isna().sum().sum())}

    customers = clean_customers(pd.read_csv(ROOT / "customers.csv", low_memory=False))
    employees = clean_employees(pd.read_csv(ROOT / "employees.csv", low_memory=False), ids["store"])
    stores = clean_stores(pd.read_csv(ROOT / "stores.csv", low_memory=False))
    marketing = clean_marketing(pd.read_csv(ROOT / "marketing.csv", low_memory=False), ids["product"])
    returns = clean_returns(pd.read_csv(ROOT / "returns.csv", low_memory=False), ids)
    salaries = clean_salaries(pd.read_csv(ROOT / "salaries.csv", low_memory=False), employee_ids)
    support = clean_support(pd.read_csv(ROOT / "support_tickets.tsv", sep="\t", low_memory=False), ids)
    raw_transactions, parser_report = read_broken_transactions(ROOT / "transactions.csv")
    transactions = clean_transactions(
        raw_transactions, ids, products.set_index("product_id")["unit_price"]
    )
    report["transactions_parser"] = parser_report

    for filename, frame in {
        "customers_cleaned.csv": customers, "employees_cleaned.csv": employees,
        "stores_cleaned.csv": stores, "marketing_cleaned.csv": marketing,
        "returns_cleaned.csv": returns, "salaries_cleaned.csv": salaries,
        "transactions_cleaned.csv": transactions,
    }.items():
        report[filename] = save(frame, filename)
    report["support_tickets_cleaned.tsv"] = save(support, "support_tickets_cleaned.tsv", "\t")

    json_path = ROOT / "api_logs.json"
    if json_path.exists():
        api = clean_json(json_path, ids["customer"])
        api.to_json(OUT / "api_logs_cleaned.json", orient="records", lines=True,
                    force_ascii=False, date_format="iso")
        report["api_logs_cleaned.json"] = {"rows": len(api), "missing": int(api.isna().sum().sum())}
    else:
        report["api_logs.json"] = "Файл відсутній у папці проєкту"

    database = ROOT / "analytics_practice.db"
    if database.exists():
        clean_database(database, OUT / "analytics_practice_cleaned.db")
        report["analytics_practice_cleaned.db"] = "Очищену копію створено"

    with (OUT / "cleaning_report.json").open("w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2, default=str)
    print(f"Готово: {OUT}")
    print(json.dumps(report, ensure_ascii=False, indent=2, default=str))


# задание 1_01
# Базові (pandas)
# 1. Топ-10 товарів за виручкою.
# Згрупувати transactions.csv по product_id (лише продажі, не returns), порахувати sum(total_amount).
# Об'єднати з Products через company_data.xlsx. Вивести таблицю.
def task_1_01_top_products_by_revenue() -> None:
    print("\nЗавдання 1_01. Топ-10 товарів за виручкою")

    transactions_path = OUT / 'transactions_cleaned.csv'
    excel_path = OUT / 'company_data_cleaned.xlsx'

    df_transactions = pd.read_csv(transactions_path, low_memory=False)
    df_products = pd.read_excel(excel_path, sheet_name='Products')

    df_transactions = df_transactions[df_transactions['is_return'] == 0].copy()
    if df_transactions['total_amount'].dtype == 'object':
        df_transactions['total_amount'] = df_transactions['total_amount'].astype(str).str.replace("", regex=True)
    df_transactions['total_amount'] = pd.to_numeric(df_transactions['total_amount'], errors='coerce')

    # групую товари та обчислюю загальну виручку
    revenue_per_product = (
        df_transactions.groupby('product_id')['total_amount']
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
    result_dir = ROOT / "results" / "task_1_01"
    result_dir.mkdir(parents=True, exist_ok=True)
    output_path = result_dir / "top_10_products_by_revenue.csv"
    top_10_products[available_columns].to_csv(output_path, index=False, encoding="utf-8-sig")
    print(f"Таблицю збережено: {output_path.relative_to(ROOT)}")
    print('-' * 20)


# задание 1_02
# 2. Розподіл виручки по категоріях. pivot_table:
# category по рядках, місяць по стовпцях, сума total_amount.
# Яка категорія лідирує щомісяця?
def task_1_02_pivot_table() -> None:
    print("\nЗавдання 1_02. Розподіл виручки по категоріях")

    CLEAN_DIR = OUT
    RESULT_DIR = ROOT / "results" / "task_1_02_patero_analysis"

    def load_table(filename: str, sep: str = ",") -> pd.DataFrame:
        """Універсальне завантаження очищених таблиць з cleaned_data"""
        if filename == "products_cleaned.csv":
            path = CLEAN_DIR / "company_data_cleaned.xlsx"
            if not path.exists():
                raise FileNotFoundError(f"Файл {path} не знайдено")
            return pd.read_excel(path, sheet_name="Products")

        path = CLEAN_DIR / filename
        if not path.exists():
            raise FileNotFoundError(f"Файл {path} не знайдено")
        return pd.read_csv(path, low_memory=False, sep=sep)

    # 1. Завантаження очищених таблиць
    transactions = load_table("transactions_cleaned.csv")
    products = load_table("products_cleaned.csv")

    # 2. Перетворення дати у datetime та витяг місяця
    transactions["transaction_date"] = pd.to_datetime(transactions["transaction_date"], errors="coerce")
    transactions["month"] = transactions["transaction_date"].dt.month

    # 3. Об’єднання транзакцій з продуктами по product_id
    df = transactions.merge(products, on="product_id", how="left")

    # 4. Побудова pivot_table: категорії по рядках, місяці по стовпцях, сума total_amount
    pivot = pd.pivot_table(
        df,
        values="total_amount",
        index="category",
        columns="month",
        aggfunc="sum",
        fill_value=0
    )

    print("Pivot table 'Revenue breakdown by category and month':\n", pivot)

    # 5. Знаходження категорії-лідера щомісяця
    leaders = pivot.idxmax()
    leaders_table = pd.DataFrame({
        "month": leaders.index,
        "leader_category": leaders.values
    })
    print("\nLeaderboard:\n", leaders_table)
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    pivot_path = RESULT_DIR / "revenue_pivot_by_category.csv"
    leaders_path = RESULT_DIR / "monthly_category_leaders.csv"
    pivot.to_csv(pivot_path, encoding="utf-8-sig")
    leaders_table.to_csv(leaders_path, index=False, encoding="utf-8-sig")
    print(f"Pivot-таблицю збережено: {pivot_path.relative_to(ROOT)}")
    print(f"Таблицю лідерів збережено: {leaders_path.relative_to(ROOT)}")


# задание 1_03
CLEAN_DIR = OUT
RESULT_DIR = ROOT / "results" / "task_1_3"


def load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    transactions_path = CLEAN_DIR / "transactions_cleaned.csv"
    company_path = CLEAN_DIR / "company_data_cleaned.xlsx"

    transactions = pd.read_csv(transactions_path, low_memory=False)
    stores = pd.read_excel(company_path, sheet_name="Stores")
    return transactions, stores


def calculate_average_check(
    transactions: pd.DataFrame,
    stores: pd.DataFrame,
) -> pd.DataFrame:
    sales = transactions.loc[transactions["is_return"].eq(0)].copy()
    sales["store_id"] = pd.to_numeric(sales["store_id"], errors="coerce")
    sales["total_amount"] = pd.to_numeric(sales["total_amount"], errors="coerce")
    sales = sales.dropna(subset=["transaction_id", "store_id", "total_amount"])
    sales = sales.loc[sales["total_amount"].gt(0)]
    sales["store_id"] = sales["store_id"].astype("int64")

    checks = (
        sales.groupby(["store_id", "transaction_id"], as_index=False)
        .agg(check_amount=("total_amount", "sum"))
    )

    store_metrics = (
        checks.groupby("store_id", as_index=False)
        .agg(
            transactions_count=("transaction_id", "nunique"),
            total_revenue=("check_amount", "sum"),
            average_check=("check_amount", "mean"),
        )
    )

    store_columns = [
        "store_id",
        "store_name",
        "country",
        "region",
        "store_format",
    ]
    result = store_metrics.merge(
        stores[store_columns],
        on="store_id",
        how="left",
        validate="one_to_one",
    )

    result = result[
        [
            "store_id",
            "store_name",
            "country",
            "region",
            "store_format",
            "transactions_count",
            "total_revenue",
            "average_check",
        ]
    ]
    result[["total_revenue", "average_check"]] = result[
        ["total_revenue", "average_check"]
    ].round(2)
    return result.sort_values("average_check", ascending=False).reset_index(drop=True)


def save_results(result: pd.DataFrame) -> Path:
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = RESULT_DIR / "average_check_by_store.csv"
    result.to_csv(output_path, index=False, encoding="utf-8-sig")
    return output_path


def print_store(label: str, store: pd.Series) -> None:
    print(
        f"{label}: {store['store_name']} (store_id={store['store_id']}), "
        f"середній чек = {store['average_check']:.2f}"
    )


def task_1_03_average_check_by_store() -> None:
    print("\nЗавдання 1_03. Середній чек по магазинах")

    transactions, stores = load_data()
    result = calculate_average_check(transactions, stores)

    if result.empty:
        raise ValueError("Не знайдено продажів для розрахунку середнього чека")

    output_path = save_results(result)
    print_store("Найвищий середній чек", result.iloc[0])
    print_store("Найнижчий середній чек", result.iloc[-1])
    print(f"Таблицю збережено: {output_path.relative_to(ROOT)}")


# задание 1_04
# Візуалізація (matplotlib/seaborn)
# 4. Barplot: виручка по категоріях за 2024 vs 2025 (поруч).
def task_1_04_barplot_revenue_by_category() -> None:
    print("\nЗавдання 1_04. Barplot: виручка по категоріях за 2024 vs 2025")

    transactions_path = OUT / 'transactions_cleaned.csv'
    company_path = OUT / 'company_data_cleaned.xlsx'
    result_dir = ROOT / "results" / "task_1_04"

    tx = pd.read_csv(transactions_path, low_memory=False)

    tx['transaction_date'] = pd.to_datetime(tx['transaction_date'], errors='coerce', format='mixed')
    tx['year'] = tx['transaction_date'].dt.year

    tx = tx[tx['is_return'] == 0].copy()

    tx['quantity'] = pd.to_numeric(tx['quantity'], errors='coerce').abs()
    tx['quantity'] = tx['quantity'].replace(0, 1).fillna(1).astype(int)

    if 'discount_percent' in tx.columns:
        tx['discount'] = pd.to_numeric(tx['discount_percent'], errors='coerce').fillna(0.0).astype(float)
        tx.loc[tx['discount'] > 1, 'discount'] = tx.loc[tx['discount'] > 1, 'discount'] / 100.0
    else:
        tx['discount'] = 0.0

    products = pd.read_excel(company_path, sheet_name='Products')

    products['unit_price'] = products['unit_price'].astype(str).str.replace(r'[$\u20AC\u00A3,]', '', regex=True)
    products['unit_price'] = pd.to_numeric(products['unit_price'], errors='coerce').fillna(0.0)

    products_clean = products[['product_id', 'category', 'unit_price']]

    print("Об'єднання таблиць та розрахунок виручки...")
    merged_df = pd.merge(tx, products_clean, on='product_id', how='left')

    df_filtered = merged_df[merged_df['year'].isin([2024, 2025])]

    df_filtered['clean_total_amount'] = df_filtered['quantity'] * df_filtered['unit_price'] * (1 - df_filtered['discount'])

    revenue_data = df_filtered.groupby(['category', 'year'])['clean_total_amount'].sum().reset_index()

    result_dir.mkdir(parents=True, exist_ok=True)
    table_path = result_dir / "revenue_by_category_2024_2025.csv"
    chart_path = result_dir / "revenue_by_category_2024_2025.png"
    revenue_data.to_csv(table_path, index=False, encoding="utf-8-sig")

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

    plt.savefig(chart_path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"Таблицю збережено: {table_path.relative_to(ROOT)}")
    print(f"Графік збережено: {chart_path.relative_to(ROOT)}")


# задание 1_05
# Heatmap (sns.heatmap): кореляція unit_price, cost_price, margin_pct, quantity, total_amount.
# Використати annot=True та cmap='coolwarm'.
def task_1_05_correlation_heatmap() -> None:
    print("\nЗавдання 1_05. Heatmap: кореляція числових показників")

    transactions_path = OUT / "transactions_cleaned.csv"
    company_path = OUT / "company_data_cleaned.xlsx"
    result_dir = ROOT / "results" / "task_1_05"

    tx = pd.read_csv(transactions_path, low_memory=False)
    products = pd.read_excel(company_path, sheet_name="Products")

    tx = tx[tx["is_return"] == 0].copy()
    tx["quantity"] = pd.to_numeric(tx["quantity"], errors="coerce").abs()
    tx["quantity"] = tx["quantity"].replace(0, 1).fillna(1).astype(int)
    tx["total_amount"] = pd.to_numeric(tx["total_amount"], errors="coerce")

    for col in ["unit_price", "cost_price", "margin_pct"]:
        if col in products.columns:
            products[col] = pd.to_numeric(products[col], errors="coerce")

    products_clean = products[["product_id", "unit_price", "cost_price", "margin_pct"]]

    merged_df = pd.merge(tx, products_clean, on="product_id", how="left")

    columns_for_corr = ["unit_price", "cost_price", "margin_pct", "quantity", "total_amount"]
    df_corr_ready = merged_df[columns_for_corr].dropna()

    corr_matrix = df_corr_ready.corr()

    result_dir.mkdir(parents=True, exist_ok=True)
    table_path = result_dir / "correlation_matrix.csv"
    chart_path = result_dir / "correlation_heatmap.png"
    corr_matrix.to_csv(table_path, encoding="utf-8-sig")

    plt.figure(figsize=(10, 6))
    sns.heatmap(
        corr_matrix,
        annot=True,
        cmap="coolwarm",
        fmt=".2f",
        linewidths=0.5,
    )

    plt.title("Матриця кореляції")
    plt.tight_layout()
    plt.savefig(chart_path, dpi=300, bbox_inches="tight")
    plt.close()

    print("Матрицю кореляції побудовано.")
    print(f"Таблицю збережено: {table_path.relative_to(ROOT)}")
    print(f"Графік збережено: {chart_path.relative_to(ROOT)}")


# задание 1_06
# 6. Boxplot / Violinplot (seaborn) + KDE: розподіл total_amount по категоріях (тільки продажі > 0). Показати викиди. Спробуйте обидва типи:
#    - sns.boxplot() — медіана, квартилі, викиди
#    - sns.violinplot() — boxplot + KDE (щільність розподілу)
#    - Додатково: sns.kdeplot(data=df, x='total_amount', hue='category', fill=True) — порівняння розподілів категорій на одному графіку
def task_1_06_sales_distribution_plots() -> None:
    print("\nЗавдання 1_06. Sales distribution plots")

    result_dir = ROOT / "results" / "task_1_06"

    tx = pd.read_csv(OUT / "transactions_cleaned.csv", low_memory=False)

    tx = tx[tx["is_return"] == 0].copy()
    tx["quantity"] = pd.to_numeric(tx["quantity"], errors="coerce").abs()
    tx["quantity"] = tx["quantity"].replace(0, 1).fillna(1).astype(int)

    if "discount" in tx.columns:
        tx["discount"] = pd.to_numeric(tx["discount"], errors="coerce").fillna(0.0)
        tx.loc[tx["discount"] > 1, "discount"] = tx["discount"] / 100.0
    else:
        tx["discount"] = 0.0

    products = pd.read_excel(OUT / "company_data_cleaned.xlsx", sheet_name="Products")
    products["unit_price"] = pd.to_numeric(products["unit_price"], errors="coerce").fillna(0.0)
    products["category"] = products["category"].astype(str).str.strip()
    products["category"] = products["category"].str.capitalize()
    products_clean = products[["product_id", "category", "unit_price"]]

    merged_df = pd.merge(tx, products_clean, on="product_id", how="left")

    merged_df["clean_total_amount"] = merged_df["quantity"] * merged_df["unit_price"] * (1 - merged_df["discount"])

    df_filtered = merged_df[merged_df["clean_total_amount"] > 0]

    result_dir.mkdir(parents=True, exist_ok=True)
    table_path = result_dir / "sales_distribution_data.csv"
    boxplot_path = result_dir / "boxplot_total_amount_by_category.png"
    violinplot_path = result_dir / "violinplot_total_amount_by_category.png"
    kdeplot_path = result_dir / "kdeplot_total_amount_by_category.png"
    df_filtered.to_csv(table_path, index=False, encoding="utf-8-sig")

    sns.set_theme(style="whitegrid")

    plt.figure(figsize=(10, 6))
    sns.boxplot(
        data=df_filtered,
        x="category",
        y="clean_total_amount",
        hue="category",
        legend=False,
        palette="Set3"
    )
    plt.title("1. Boxplot")
    plt.xlabel("Категорія товару")
    plt.ylabel("Сума")
    plt.xticks(rotation=30, ha="right")
    plt.ticklabel_format(style="plain", axis="y")
    plt.tight_layout()
    plt.savefig(boxplot_path, dpi=300, bbox_inches="tight")
    plt.close()

    plt.figure(figsize=(10, 6))
    sns.violinplot(
        data=df_filtered,
        x="category",
        y="clean_total_amount",
        hue="category",
        legend=False,
        palette="Set3"
    )
    plt.title("2. Violinplot")
    plt.xlabel("Категорія товару")
    plt.ylabel("Сума транзакції")
    plt.xticks(rotation=30, ha="right")
    plt.ticklabel_format(style="plain", axis="y")
    plt.tight_layout()
    plt.savefig(violinplot_path, dpi=300, bbox_inches="tight")
    plt.close()

    plt.figure(figsize=(10, 6))
    sns.kdeplot(
        data=df_filtered,
        x="clean_total_amount",
        hue="category",
        fill=True,
        alpha=0.35,
        palette="Set1"
    )
    plt.title("3. KDEplot")
    plt.xlabel("Сума транзакції")
    plt.ylabel("Щільність розподілу")
    plt.ticklabel_format(style="plain", axis="x")
    plt.tight_layout()
    plt.savefig(kdeplot_path, dpi=300, bbox_inches="tight")
    plt.close()

    print(f"Побудовано графіки для {df_filtered['category'].nunique()} категорій.")
    print(f"Таблицю збережено: {table_path.relative_to(ROOT)}")
    print(f"Графік збережено: {boxplot_path.relative_to(ROOT)}")
    print(f"Графік збережено: {violinplot_path.relative_to(ROOT)}")
    print(f"Графік збережено: {kdeplot_path.relative_to(ROOT)}")


# задание 1_07
# 7. [Просунуті] ABC-аналіз товарів. Порахувати суму виручки на товарі 10%.
# ABC-аналіз товарів. Порахувати суму виручки на товар, відсортувати за спаданням,
# додати cumsum() частки (кумулятивна сума). A = перші 70% виручки, B = 70–90%, C = останні 10%.
# Скільки товарів у A, B, C?
def task_1_07_abc_analysis_of_products() -> None:
    print("\nЗавдання 1_07. ABC-аналіз товарів")

    RESULT_DIR = ROOT / "results" / "task_1_07"

    transactions = pd.read_csv(OUT / "transactions_cleaned.csv", low_memory=False)
    products = pd.read_excel(OUT / "company_data_cleaned.xlsx", sheet_name="Products")

    # 1. Сума виручки на товар
    revenue_per_product = transactions.groupby("product_id")["total_amount"].sum().reset_index()

    # 2. Об’єднання з products для категорій/назв
    revenue_per_product = revenue_per_product.merge(products, on="product_id", how="left")

    # 3. Сортування за спаданням
    revenue_per_product = revenue_per_product.sort_values("total_amount", ascending=False)

    # 4. Кумулятивна частка
    total_revenue = revenue_per_product["total_amount"].sum()
    revenue_per_product["cum_share"] = revenue_per_product["total_amount"].cumsum() / total_revenue * 100

    # 5. Присвоєння груп A/B/C та Підрахунок кількості товарів у кожній групі
    def abc_group(x):
        if x <= 70:
            return "A (перші 70% виручки)"
        elif x <= 90:
            return "B (70–90%)"
        else:
            return "C (останні 10%)"

    revenue_per_product["ABC"] = revenue_per_product["cum_share"].apply(abc_group)

    abc_counts = revenue_per_product["ABC"].value_counts()

    # 7. Підрахунок суми виручки на товарі групи C (10%)
    sum_c = revenue_per_product[revenue_per_product["ABC"] == "C (останні 10%)"]["total_amount"].sum()

    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    table_path = RESULT_DIR / "abc_analysis_of_products.csv"
    counts_path = RESULT_DIR / "abc_counts.csv"
    revenue_per_product.to_csv(table_path, index=False, encoding="utf-8-sig")
    abc_counts.rename_axis("ABC").reset_index(name="product_count").to_csv(
        counts_path,
        index=False,
        encoding="utf-8-sig",
    )

    print("Quantities of goods in each group:\n", abc_counts)
    print(
        "Sorting by sum in descending order\n",
        revenue_per_product[["product_id", "product_name", "total_amount", "category", "ABC"]].head(10)
    )
    print("Revenue from Group C products (10%):", sum_c)
    print(f"Таблицю збережено: {table_path.relative_to(ROOT)}")
    print(f"Таблицю збережено: {counts_path.relative_to(ROOT)}")


# задание 1_08
# Блок 1. Завдання 8.
# Market Basket Analysis. Для кожного customer_id зібрати всі category куплених товарів за один день.
# Знайти найчастіші пари категорій, що купують разом (комбінації 2 категорій).
# Які топ-5 пар?
# > Підказка: якщо same-day покупок мало — спробуйте згрупувати по customer_id + тиждень через .dt.isocalendar().week.
# Використайте itertools.combinations() для генерації пар категорій.
# Для підрахунку пар зручно застосувати value_counts() на серії пар або nunique() для перевірки кількості унікальних пар.
def task_1_08_market_basket_analysis() -> None:
    print("\nЗавдання 1_08. Market Basket Analysis")

    CLEAN_DIR = OUT
    result_dir = ROOT / "results" / "task_1_08"

    transactions_path = CLEAN_DIR / "transactions_cleaned.csv"
    excel_path = CLEAN_DIR / "company_data_cleaned.xlsx"

    if not transactions_path.exists() or not excel_path.exists():
        clean_data()

    df_trans = pd.read_csv(transactions_path)
    df_prod = pd.read_excel(excel_path, sheet_name="Products")

    df = pd.merge(df_trans, df_prod[["product_id", "category"]], on="product_id", how="left")

    df = df.dropna(subset=["customer_id", "transaction_date", "category"])

    df["transaction_date"] = pd.to_datetime(df["transaction_date"])
    df["week"] = df["transaction_date"].dt.isocalendar().week

    basket = df.groupby(["customer_id", "week"])["category"].apply(set)

    pairs = []
    for cats in basket:
        if len(cats) > 1:
            pairs.extend(combinations(sorted(list(cats)), 2))

    top_5 = pd.Series(pairs).value_counts().head(5)

    result_dir.mkdir(parents=True, exist_ok=True)
    table_path = result_dir / "top_5_category_pairs.csv"
    top_5.rename_axis("category_pair").reset_index(name="count").to_csv(
        table_path,
        index=False,
        encoding="utf-8-sig",
    )

    print(" Топ-5 пар категорій, що купують разом")
    print(top_5)
    print(f"Таблицю збережено: {table_path.relative_to(ROOT)}")


# задание 1_09
# Блок 1. Завдання 9.
# Аналіз знижок. Розбити транзакції на: discount_percent == 0 vs >0.
#  Порівняти середню кількість одиниць (quantity) та виручку. Чи працюють знижки?
DATA_PATH = OUT / "transactions_cleaned.csv"


def task_1_09_discount_analysis() -> None:
    print("\nЗавдання 1_09. Аналіз знижок")

    result_dir = ROOT / "results" / "task_1_09"

    if not os.path.exists(DATA_PATH):
        print(f"Файл {DATA_PATH} не знайдено!")
        return

    df = pd.read_csv(DATA_PATH)

    no_discount_df = df[df["discount_percent"] == 0]
    with_discount_df = df[df["discount_percent"] > 0]

    no_discount_table = pd.DataFrame({"Кількість": [no_discount_df["transaction_id"].count()],
                                      "Сума": [no_discount_df["total_amount"].sum()]})
    with_discount_table = pd.DataFrame({"Кількість": [with_discount_df["transaction_id"].count()],
                                        "Сума": [with_discount_df["total_amount"].sum()]})

    print("ТАБЛИЦЯ: Транзакції БЕЗ знижок")
    print(no_discount_table)
    print("\n" + "=" * 50 + "\n")

    print("ТАБЛИЦЯ: Транзакції ЗІ знижкою")
    print(with_discount_table)
    print("\n" + "=" * 50 + "\n")

    df["discount_group"] = ["Без знижки" if d == 0 else "Зі знижкою" for d in df["discount_percent"]]
    analysis = df.groupby("discount_group")[["quantity", "total_amount"]].mean()

    print("СЕРЕДНІ ПОКАЗНИКИ: Без знижки vs Зі знижкою")
    print(analysis.round(2))

    print(" ВИСНОВКИ")
    q_no = analysis.loc["Без знижки", "quantity"]
    q_yes = analysis.loc["Зі знижкою", "quantity"]
    t_no = analysis.loc["Без знижки", "total_amount"]
    t_yes = analysis.loc["Зі знижкою", "total_amount"]

    if q_yes > q_no:
        print(f"- Кількість товарів у кошику зі знижкою вища (+{((q_yes / q_no) - 1) * 100:.1f}%)")
    else:
        print("- Знижки НЕ стимулюють клієнтів купувати більше товарів.")

    if t_yes < t_no:
        print("- Середній чек зі знижкою НИЖЧИЙ: знижки зменшують маржинальність без приросту обсягу.")
    else:
        print("- Середній чек зі знижкою вищий — акції працюють ефективно.")

    result_dir.mkdir(parents=True, exist_ok=True)
    no_discount_path = result_dir / "transactions_without_discount.csv"
    with_discount_path = result_dir / "transactions_with_discount.csv"
    analysis_path = result_dir / "discount_analysis.csv"
    no_discount_table.to_csv(no_discount_path, index=False, encoding="utf-8-sig")
    with_discount_table.to_csv(with_discount_path, index=False, encoding="utf-8-sig")
    analysis.round(2).to_csv(analysis_path, encoding="utf-8-sig")
    print(f"Таблицю збережено: {no_discount_path.relative_to(ROOT)}")
    print(f"Таблицю збережено: {with_discount_path.relative_to(ROOT)}")
    print(f"Таблицю збережено: {analysis_path.relative_to(ROOT)}")


# задание 1_10
def task_1_10_cohort_retention() -> None:
    print("\nЗавдання 1_10. Cohort Retention")

    result_dir = ROOT / "results" / "task_1_10"
    transactions_path = OUT / "transactions_cleaned.csv"
    products_path = OUT / "company_data_cleaned.xlsx"

    transactions = pd.read_csv(transactions_path, low_memory=False)
    products = pd.read_excel(products_path, sheet_name="Products")

    sales = transactions.loc[transactions["is_return"].eq(0)].copy()
    sales["transaction_date"] = pd.to_datetime(sales["transaction_date"], errors="coerce")
    sales = sales.dropna(subset=["customer_id", "product_id", "transaction_date"])

    sales["customer_id"] = sales["customer_id"].astype("int64")
    sales["product_id"] = sales["product_id"].astype("int64")
    sales = sales.merge(
        products[["product_id", "category"]],
        on="product_id",
        how="inner",
        validate="many_to_one",
    )

    sales = sales.sort_values(["customer_id", "transaction_date", "transaction_id"])
    first_purchase = (
        sales.groupby("customer_id", as_index=False)
        .first()[["customer_id", "transaction_date", "category"]]
        .rename(
            columns={
                "transaction_date": "first_purchase_date",
                "category": "first_category",
            }
        )
    )

    sales = sales.merge(first_purchase, on="customer_id", how="inner")
    sales["purchase_month"] = sales["transaction_date"].dt.to_period("M")
    sales["cohort_month"] = sales["first_purchase_date"].dt.to_period("M")
    sales["month_number"] = (
        (sales["purchase_month"].dt.year - sales["cohort_month"].dt.year) * 12
        + sales["purchase_month"].dt.month
        - sales["cohort_month"].dt.month
    )

    same_category = sales.loc[sales["category"].eq(sales["first_category"])]
    active = (
        same_category[["cohort_month", "month_number", "customer_id"]]
        .drop_duplicates()
        .groupby(["cohort_month", "month_number"])["customer_id"]
        .nunique()
        .unstack(fill_value=0)
    )

    cohort_size = (
        first_purchase.assign(
            cohort_month=first_purchase["first_purchase_date"].dt.to_period("M")
        )
        .groupby("cohort_month")["customer_id"]
        .nunique()
    )

    retention = active.div(cohort_size, axis=0).mul(100)
    last_month = sales["purchase_month"].max()
    for cohort_month in retention.index:
        months_available = last_month.ordinal - cohort_month.ordinal
        unavailable = retention.columns > months_available
        retention.loc[cohort_month, unavailable] = float("nan")

    retention.index = retention.index.astype(str)
    retention.columns = [f"M{int(col)}" for col in retention.columns]
    retention = retention.round(2)

    details = first_purchase.copy()
    details["cohort_month"] = details["first_purchase_date"].dt.to_period("M").astype(str)

    result_dir.mkdir(parents=True, exist_ok=True)
    retention_path = result_dir / "cohort_retention.csv"
    details_path = result_dir / "customer_first_category.csv"
    chart_path = result_dir / "cohort_retention.png"
    retention.to_csv(retention_path, encoding="utf-8-sig")
    details.to_csv(details_path, index=False, encoding="utf-8-sig")

    plt.figure(figsize=(16, 9))
    sns.heatmap(
        retention,
        annot=True,
        fmt=".1f",
        cmap="YlGnBu",
        vmin=0,
        vmax=100,
        cbar_kws={"label": "Retention, %"},
    )
    plt.title("Cohort Retention за категорією першої покупки")
    plt.xlabel("Місяць після першої покупки")
    plt.ylabel("Місяць першої покупки")
    plt.tight_layout()
    plt.savefig(chart_path, dpi=180, bbox_inches="tight")
    plt.close()

    print(
        f"Cohort Retention: {len(retention)} когорт, "
        f"{retention.columns[0]}-{retention.columns[-1]}"
    )
    print(f"Таблицю збережено: {retention_path.relative_to(ROOT)}")
    print(f"Таблицю збережено: {details_path.relative_to(ROOT)}")
    print(f"Графік збережено: {chart_path.relative_to(ROOT)}")


# задание 1_11
def task_1_11_clv_estimation() -> None:
    print("\nЗавдання 1_11. CLV Estimation")

    result_dir = ROOT / "results" / "task_1_11"
    transactions_path = OUT / "transactions_cleaned.csv"

    transactions = pd.read_csv(transactions_path, low_memory=False)
    transactions["transaction_date"] = pd.to_datetime(
        transactions["transaction_date"], errors="coerce"
    )

    sales = transactions.loc[
        transactions["is_return"].eq(0)
        & transactions["transaction_date"].between("2024-01-01", "2025-12-31 23:59:59")
    ].copy()

    sales["customer_id"] = pd.to_numeric(sales["customer_id"], errors="coerce")
    sales["total_amount"] = pd.to_numeric(sales["total_amount"], errors="coerce")
    sales = sales.dropna(
        subset=["customer_id", "transaction_id", "transaction_date", "total_amount"]
    )
    sales = sales.loc[sales["total_amount"].gt(0)]
    sales["customer_id"] = sales["customer_id"].astype("int64")
    sales["month"] = sales["transaction_date"].dt.to_period("M")

    monthly = sales.groupby("month").agg(
        revenue=("total_amount", "sum"),
        customers=("customer_id", "nunique"),
        purchases=("transaction_id", "nunique"),
    )
    monthly["arpu"] = monthly["revenue"] / monthly["customers"]
    monthly["purchase_frequency"] = monthly["purchases"] / monthly["customers"]
    monthly.index = monthly.index.astype(str)
    monthly = monthly.round(2)

    customers = sales.groupby("customer_id").agg(
        first_purchase=("transaction_date", "min"),
        last_purchase=("transaction_date", "max"),
        total_revenue=("total_amount", "sum"),
        purchases=("transaction_id", "nunique"),
        active_months=("month", "nunique"),
    )

    first_month = customers["first_purchase"].dt.to_period("M")
    last_month = customers["last_purchase"].dt.to_period("M")
    customers["lifetime_months"] = (
        (last_month.dt.year - first_month.dt.year) * 12
        + last_month.dt.month
        - first_month.dt.month
        + 1
    )

    customers["arpu_month"] = customers["total_revenue"] / customers["lifetime_months"]
    customers["purchase_frequency_month"] = (
        customers["purchases"] / customers["lifetime_months"]
    )
    customers["clv"] = (
        customers["arpu_month"]
        * customers["purchase_frequency_month"]
        * customers["lifetime_months"]
    )

    labels = ["Low", "Medium", "High", "Premium"]
    customers["clv_segment"] = pd.qcut(
        customers["clv"].rank(method="first"),
        q=4,
        labels=labels,
    )
    customers = customers.reset_index().round(
        {
            "total_revenue": 2,
            "arpu_month": 2,
            "purchase_frequency_month": 2,
            "clv": 2,
        }
    )

    summary = pd.DataFrame(
        {
            "metric": [
                "Average monthly ARPU",
                "Average monthly purchase frequency",
                "Average customer lifetime, months",
                "Average estimated CLV",
                "Median estimated CLV",
            ],
            "value": [
                monthly["arpu"].mean(),
                monthly["purchase_frequency"].mean(),
                customers["lifetime_months"].mean(),
                customers["clv"].mean(),
                customers["clv"].median(),
            ],
        }
    ).round(2)

    result_dir.mkdir(parents=True, exist_ok=True)
    monthly_path = result_dir / "monthly_clv_metrics.csv"
    customers_path = result_dir / "customer_clv_segments.csv"
    summary_path = result_dir / "clv_summary.csv"
    chart_path = result_dir / "clv_segments.png"
    monthly.to_csv(monthly_path, encoding="utf-8-sig")
    customers.to_csv(customers_path, index=False, encoding="utf-8-sig")
    summary.to_csv(summary_path, index=False, encoding="utf-8-sig")

    order = ["Low", "Medium", "High", "Premium"]
    segment_stats = (
        customers.groupby("clv_segment", observed=False)
        .agg(
            customers=("customer_id", "count"),
            average_clv=("clv", "mean"),
        )
        .reindex(order)
    )

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    sns.barplot(
        data=segment_stats.reset_index(),
        x="clv_segment",
        y="customers",
        hue="clv_segment",
        order=order,
        palette="Blues_d",
        legend=False,
        ax=axes[0],
    )
    axes[0].set_title("Кількість клієнтів за CLV-сегментами")
    axes[0].set_xlabel("CLV-сегмент")
    axes[0].set_ylabel("Кількість клієнтів")

    sns.barplot(
        data=segment_stats.reset_index(),
        x="clv_segment",
        y="average_clv",
        hue="clv_segment",
        order=order,
        palette="YlGnBu",
        legend=False,
        ax=axes[1],
    )
    axes[1].set_title("Середній CLV за сегментами")
    axes[1].set_xlabel("CLV-сегмент")
    axes[1].set_ylabel("CLV")

    plt.tight_layout()
    plt.savefig(chart_path, dpi=180, bbox_inches="tight")
    plt.close()

    print("Monthly metrics")
    print(monthly.to_string())
    print("\nCLV summary")
    print(summary.to_string(index=False))
    print("\nCLV segments")
    print(
        customers["clv_segment"]
        .value_counts()
        .reindex(["Low", "Medium", "High", "Premium"])
        .to_string()
    )
    print(f"Таблицю збережено: {monthly_path.relative_to(ROOT)}")
    print(f"Таблицю збережено: {customers_path.relative_to(ROOT)}")
    print(f"Таблицю збережено: {summary_path.relative_to(ROOT)}")
    print(f"Графік збережено: {chart_path.relative_to(ROOT)}")


# задание 2_01
def task_2_01_load_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    transactions_path = OUT / "transactions_cleaned.csv"
    company_path = OUT / "company_data_cleaned.xlsx"

    transactions = pd.read_csv(transactions_path, low_memory=False)
    products = pd.read_excel(company_path, sheet_name="Products")
    stores = pd.read_excel(company_path, sheet_name="Stores")
    return transactions, products, stores


def task_2_01_prepare_sales(
    transactions: pd.DataFrame,
    products: pd.DataFrame,
    stores: pd.DataFrame,
) -> pd.DataFrame:
    sales = transactions.query("is_return == 0").copy()

    numeric_columns = ["product_id", "store_id", "quantity", "total_amount"]
    for column in numeric_columns:
        sales[column] = pd.to_numeric(sales[column], errors="coerce")

    sales["transaction_date"] = pd.to_datetime(
        sales["transaction_date"], errors="coerce"
    )
    sales = sales.dropna(
        subset=[
            "product_id",
            "store_id",
            "quantity",
            "total_amount",
            "transaction_date",
        ]
    )
    sales = sales.loc[sales["quantity"].gt(0) & sales["total_amount"].gt(0)]
    sales[["product_id", "store_id"]] = sales[["product_id", "store_id"]].astype(
        "int64"
    )

    sales = sales.merge(
        products[["product_id", "product_name", "category", "cost_price"]],
        on="product_id",
        how="inner",
        validate="many_to_one",
    )
    sales = sales.merge(
        stores[["store_id", "store_name", "store_format"]],
        on="store_id",
        how="inner",
        validate="many_to_one",
    )

    sales["cost_price"] = pd.to_numeric(sales["cost_price"], errors="coerce")
    sales = sales.dropna(subset=["cost_price"])
    sales = sales.loc[sales["cost_price"].ge(0)]

    sales["revenue"] = sales["total_amount"]
    sales["total_cost"] = sales["quantity"] * sales["cost_price"]
    sales["operating_expenses"] = sales["revenue"] * 0.05
    sales["profit"] = (
        sales["revenue"] - sales["total_cost"] - sales["operating_expenses"]
    )
    sales["month"] = sales["transaction_date"].dt.to_period("M")
    return sales


def task_2_01_calculate_monthly_profit(sales: pd.DataFrame) -> pd.DataFrame:
    monthly = (
        sales.groupby("month", as_index=False)
        .agg(
            total_revenue=("revenue", "sum"),
            total_cost=("total_cost", "sum"),
            operating_expenses=("operating_expenses", "sum"),
            total_profit=("profit", "sum"),
        )
        .sort_values("month")
    )
    monthly["margin_pct"] = (
        monthly["total_profit"] / monthly["total_revenue"] * 100
    )
    monthly["month"] = monthly["month"].astype(str)

    value_columns = [
        "total_revenue",
        "total_cost",
        "operating_expenses",
        "total_profit",
        "margin_pct",
    ]
    monthly[value_columns] = monthly[value_columns].round(2)
    return monthly


def task_2_01_save_results(monthly: pd.DataFrame) -> Path:
    RESULT_DIR = ROOT / "results" / "task_2_01"
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = RESULT_DIR / "monthly_profit_analysis.csv"
    monthly.to_csv(output_path, index=False, encoding="utf-8-sig")
    return output_path


def task_2_01_profit_analysis() -> None:
    print("\nЗавдання 2_01. Profit Analysis")

    transactions, products, stores = task_2_01_load_data()
    sales = task_2_01_prepare_sales(transactions, products, stores)
    monthly = task_2_01_calculate_monthly_profit(sales)

    if monthly.empty:
        raise ValueError("Не знайдено даних для розрахунку прибутку")

    best_month = monthly.loc[monthly["total_profit"].idxmax()]
    worst_month = monthly.loc[monthly["total_profit"].idxmin()]
    output_path = task_2_01_save_results(monthly)

    print(
        f"Найприбутковіший місяць: {best_month['month']}, "
        f"прибуток = {best_month['total_profit']:.2f}"
    )
    print(
        f"Місяць з найнижчим прибутком: {worst_month['month']}, "
        f"прибуток = {worst_month['total_profit']:.2f}"
    )
    if worst_month["total_profit"] < 0:
        print("Цей місяць був збитковим.")
    else:
        print("Збиткових місяців немає.")
    print(f"Таблицю збережено: {output_path.relative_to(ROOT)}")


# задание 2_02
# 2.2. Pareto Analysis (80/20).
# Pareto Analysis (80/20). Для всіх продуктів (з Products):
# Порахувати частку кожного продукту в загальній виручці (transactions)
# Відсортувати за спаданням, cumsum
# Знайти, скільки продуктів дають 80% виручки
# Візуалізувати: крива Парето (line + bar)
def task_2_02_patero_analysis_80() -> None:
    print("\nЗавдання 2_02. Patero Analysis (80/20)")

    CLEAN_DIR = OUT
    RESULT_DIR = ROOT / "results" / "task_2_02_patero_analysis_80"

    def load_table(filename: str, sep: str = ",") -> pd.DataFrame:
        """Універсальне завантаження очищених таблиць з cleaned_data"""
        path = CLEAN_DIR / filename
        if not path.exists():
            raise FileNotFoundError(f"Файл {path} не знайдено")
        return pd.read_csv(path, low_memory=False, sep=sep)

    transactions = load_table("transactions_cleaned.csv")
    products = pd.read_excel(CLEAN_DIR / "company_data_cleaned.xlsx", sheet_name="Products")

    revenue_per_product = transactions.groupby("product_id")["total_amount"].sum().reset_index()
    revenue_per_product = revenue_per_product.merge(products, on="product_id", how="left")
    revenue_per_product = revenue_per_product.sort_values("total_amount", ascending=False).reset_index(drop=True)

    total_revenue = revenue_per_product["total_amount"].sum()
    revenue_per_product["cum_share"] = revenue_per_product["total_amount"].cumsum() / total_revenue * 100

    n_products_80 = int(revenue_per_product[revenue_per_product["cum_share"] >= 80].index[0] + 1)

    def group(x):
        return "Перші 80% виручки" if x < n_products_80 else "Останні 20% виручки"

    revenue_per_product["80/20"] = [group(i) for i in range(len(revenue_per_product))]

    print('Quantities of goods in group "Перші 80% виручки": ', n_products_80)

    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    table_path = RESULT_DIR / "patero_analysis_80.csv"
    chart_path = RESULT_DIR / "patero_analysis_80.png"
    revenue_per_product.to_csv(table_path, index=False, encoding="utf-8-sig")

    # графік та лінія
    fig, ax1 = plt.subplots(figsize=(15, 7))

    colors = revenue_per_product["80/20"].map({
        "Перші 80% виручки": "skyblue",
        "Останні 20% виручки": "lightgreen"
    })

    ax1.bar(revenue_per_product["product_name"], revenue_per_product["total_amount"], color=colors, alpha=0.8)
    ax1.set_ylabel("Total Amount", fontsize=15)
    ax1.set_xticks(range(len(revenue_per_product["product_name"])))
    ax1.set_xticklabels(revenue_per_product["product_name"], rotation=90)

    ax2 = ax1.twinx()
    ax2.plot(revenue_per_product["product_name"], revenue_per_product["cum_share"], color="red", alpha=0.8)
    ax2.set_ylabel("Cum_share (%)", fontsize=15)

    ax2.axhline(80, color="k", linestyle="--", label="80% поріг")

    ax1.axvline(n_products_80 - 1, color="purple", linestyle="--", label=f"{n_products_80} продуктів = 80%")

    plt.title("Patero Analysis (80/20) by products", fontsize=15, fontweight="bold")
    ax2.legend(loc="lower right")

    plt.title(f"Patero Analysis (80/20) by products\n"
              f"Count of products generating 80% of revenue: {n_products_80}",
              fontsize=14, fontweight="bold")

    plt.tight_layout()
    plt.savefig(chart_path, dpi=300, bbox_inches="tight")
    plt.close(fig)

    print(f"Таблицю збережено: {table_path.relative_to(ROOT)}")
    print(f"Графік збережено: {chart_path.relative_to(ROOT)}")


# задание 2_03
# [Базові] Data Quality Score
# Оцінити кожен датафрейм за метриками якості:
# completeness = 1 - % missing;
# uniqueness = 1 - % дублікатів;
# validity = % рядків без аномалій;
# consistency = % рядків з коректними типами та діапазонами;
# overall_score = average чотирьох метрик.
# Визначити файл із найвищим та найнижчим DQ Score.
def task_2_03_data_quality_score() -> None:
    print("\nЗавдання 2_03. Data Quality Score")

    sns.set_theme(style="whitegrid")
    plt.rcParams["figure.figsize"] = (10, 5)

    BASE_DIR = ROOT
    result_dir = ROOT / "results" / "task_2_03"

    files_to_check = {
        "Customers": os.path.join(BASE_DIR, "customers.csv"),
        "Employees": os.path.join(BASE_DIR, "employees.csv"),
        "Marketing": os.path.join(BASE_DIR, "marketing.csv"),
        "Stores": os.path.join(BASE_DIR, "stores.csv"),
        "Returns": os.path.join(BASE_DIR, "returns.csv")
    }

    dq_results = []

    for name, path in files_to_check.items():
        if not os.path.exists(path):
            print(f"Не знайдено файл {name} за шляхом {path}.")
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

        if name == "Customers":
            df["age"] = pd.to_numeric(df["age"], errors="coerce")
            df["total_orders"] = pd.to_numeric(df["total_orders"], errors="coerce")

            anomalies = df[(df["age"] > 100) | (df["customer_id"].isna()) | (df["age"].isna())]
            valid_rows_count = total_rows - len(anomalies)

            consistent = df[(df["age"] > 0) & (df["age"] <= 100) & (df["total_orders"] >= 0)]
            consistent_rows_count = len(consistent)

        elif name == "Employees":
            if df["salary"].dtype == "object":
                df["salary"] = df["salary"].astype(str).str.replace(r"[₴\$€£]|(?:USD|UAH|EUR|GBP)|\s|", "", regex=True)
            df["salary"] = pd.to_numeric(df["salary"], errors="coerce")
            df["performance_score"] = pd.to_numeric(df["performance_score"], errors="coerce")

            anomalies = df[df["employee_id"].isna() | df["department"].isna() | df["salary"].isna()]
            valid_rows_count = total_rows - len(anomalies)
            consistent = df[(df["performance_score"] >= 0) & (df["performance_score"] <= 100) & (df["salary"] > 0)]
            consistent_rows_count = len(consistent)

        elif name == "Marketing":
            if df["budget"].dtype == "object":
                df["budget"] = df["budget"].astype(str).str.replace(r"[₴\$€£]|(?:USD|UAH|EUR|GBP)|\s|", "", regex=True)
            df["budget"] = pd.to_numeric(df["budget"], errors="coerce")

            if df["clicks"].dtype == "object":
                df["clicks"] = df["clicks"].astype(str).str.replace(r"[₴\$€£]|(?:USD|UAH|EUR|GBP)|\s|", "", regex=True)
            df["clicks"] = pd.to_numeric(df["clicks"], errors="coerce")

            anomalies = df[(df["budget"] < 0) | (df["clicks"] < 0) | (df["budget"].isna()) | (df["clicks"].isna())]
            valid_rows_count = total_rows - len(anomalies)
            consistent = df[(df["ctr_pct"] >= 0) & (df["ctr_pct"] <= 100) &
                            (df["conversion_rate_pct"] >= 0) & (df["conversion_rate_pct"] <= 100)]
            consistent_rows_count = len(consistent)

        elif name == "Stores":
            df["size_sqm"] = pd.to_numeric(df["size_sqm"], errors="coerce")
            anomalies = df[(df["size_sqm"] <= 0) | (df["size_sqm"].isna())]
            valid_rows_count = total_rows - len(anomalies)

            consistent = df[df["has_cafe"].astype(str).str.lower().isin(["true", "false", "1", "0", "yes", "no"]) &
                            df["has_parking"].astype(str).str.lower().isin(["true", "false", "1", "0", "yes", "no"])]
            consistent_rows_count = len(consistent)

        elif name == "Returns":
            df["refund_amount"] = pd.to_numeric(df["refund_amount"], errors="coerce")
            df["total_amount"] = pd.to_numeric(df["total_amount"], errors="coerce")
            df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce")

            anomalies = df[(df["refund_amount"].abs() > df["total_amount"].abs()) | df["refund_amount"].isna()]
            valid_rows_count = total_rows - len(anomalies)
            consistent = df[df["quantity"] >= 1]
            consistent_rows_count = len(consistent)

        validity = valid_rows_count / total_rows
        consistency = consistent_rows_count / total_rows
        overall_score = (completeness + uniqueness + validity + consistency) / 4.0

        dq_results.append({
            "File Name": name,
            "Повнота (%)": round(completeness * 100, 2),
            "Унікальність (%)": round(uniqueness * 100, 2),
            "Валідність (%)": round(validity * 100, 2),
            "Узгодженість (%)": round(consistency * 100, 2),
            "Загальна оцінка (%)": round(overall_score * 100, 2)
        })

    df_dq_report = pd.DataFrame(dq_results)

    print(f"\nЗвіт про якість даних(DATA QUALITY REPORT)\n\n{df_dq_report.to_string(index=False)}")
    print("-" * 20)

    best_file = df_dq_report.loc[df_dq_report["Загальна оцінка (%)"].idxmax()]
    worst_file = df_dq_report.loc[df_dq_report["Загальна оцінка (%)"].idxmin()]

    print(f"\nНайвищий DQ Score: файл '{best_file['File Name']}' з показником {best_file['Загальна оцінка (%)']}%")
    print(f"Найнижчий DQ Score: файл '{worst_file['File Name']}' з показником {worst_file['Загальна оцінка (%)']}%")

    result_dir.mkdir(parents=True, exist_ok=True)
    table_path = result_dir / "data_quality_score.csv"
    chart_path = result_dir / "data_quality_score.png"
    df_dq_report.to_csv(table_path, index=False, encoding="utf-8-sig")

    df_melted = df_dq_report.melt(id_vars="File Name",
                                  value_vars=["Повнота (%)", "Унікальність (%)", "Валідність (%)", "Узгодженість (%)"],
                                  var_name="Metric", value_name="Percentage")

    plt.figure(figsize=(10, 5))
    sns.barplot(x="File Name", y="Percentage", hue="Metric", data=df_melted, palette="viridis")

    for i, name in enumerate(df_dq_report["File Name"]):
        score = df_dq_report.loc[df_dq_report["File Name"] == name, "Загальна оцінка (%)"].values[0]
        plt.plot([i - 0.3, i + 0.3], [score, score], color="red", linestyle="--", linewidth=1.5)
        plt.text(i, score + 2, f"{score}%")

    plt.title("Порівняльний аналіз метрик Data Quality Score")
    plt.xlabel("Назва файлу / Датасету")
    plt.ylabel("Показник якості (%)")
    plt.ylim(0, 115)
    plt.legend(title="Метрики оцінки", bbox_to_anchor=(1.02, 1), loc="upper left")
    plt.tight_layout()
    plt.savefig(chart_path, dpi=300, bbox_inches="tight")
    plt.close()

    print(f"Таблицю збережено: {table_path.relative_to(ROOT)}")
    print(f"Графік збережено: {chart_path.relative_to(ROOT)}")


# задание 2_04
# Побудувати stacked bar у matplotlib: revenue + cost + profit по місяцях (12 місяців 2025 року). Використати plt.bar() з параметром bottom.
def task_2_04_monthly_revenue_stacked_bar() -> None:
    print("\nЗавдання 2_04. Stacked bar: revenue, cost, profit")

    result_dir = ROOT / "results" / "task_2_04"

    tx = pd.read_csv(OUT / "transactions_cleaned.csv", low_memory=False)

    tx["transaction_date"] = pd.to_datetime(tx["transaction_date"], errors="coerce", format="mixed")
    tx["year"] = tx["transaction_date"].dt.year
    tx["month"] = tx["transaction_date"].dt.month

    tx_2025 = tx[tx["year"] == 2025].copy()

    tx_2025["quantity"] = pd.to_numeric(tx_2025["quantity"], errors="coerce").abs().replace(0, 1).fillna(1).astype(int)

    tx_2025["discount_percent"] = pd.to_numeric(tx_2025["discount_percent"], errors="coerce").fillna(0.0).astype(float)
    tx_2025.loc[tx_2025["discount_percent"] > 1, "discount_percent"] = tx_2025.loc[tx_2025["discount_percent"] > 1, "discount_percent"] / 100.0

    products = pd.read_excel(OUT / "company_data_cleaned.xlsx", sheet_name="Products")

    for col in ["unit_price", "cost_price"]:
        products[col] = pd.to_numeric(products[col], errors="coerce").fillna(0.0)

    products["category"] = products["category"].astype(str).str.strip().str.capitalize()
    products_clean = products[["product_id", "unit_price", "cost_price"]]

    df_2025 = pd.merge(tx_2025, products_clean, on="product_id", how="left")

    df_2025["revenue"] = df_2025["quantity"] * df_2025["unit_price"] * (1 - df_2025["discount_percent"])
    df_2025["cost"] = df_2025["quantity"] * df_2025["cost_price"]
    df_2025["profit"] = df_2025["revenue"] - df_2025["cost"]

    monthly_data = df_2025.groupby("month")[["revenue", "cost", "profit"]].sum().reset_index()

    monthly_data = monthly_data.set_index("month").reindex(range(1, 13), fill_value=0).reset_index()

    result_dir.mkdir(parents=True, exist_ok=True)
    table_path = result_dir / "monthly_revenue_cost_profit_2025.csv"
    chart_path = result_dir / "monthly_revenue_stacked_bar_2025.png"
    monthly_data.to_csv(table_path, index=False, encoding="utf-8-sig")

    plt.figure(figsize=(10, 6))

    months = monthly_data["month"]
    costs = monthly_data["cost"]
    profits = monthly_data["profit"]

    month_names = ["Січ", "Лют", "Бер", "Квіт", "Трав", "Черв", "Лип", "Серп", "Врес", "Жовт", "Лист", "Груд"]

    plt.bar(months, costs, label="Собівартість (Cost)", color="#fc8d62", alpha=0.85)

    plt.bar(months, profits, bottom=costs, label="Чистий прибуток (Profit)", color="#66c2a5", alpha=0.85)

    plt.title("Структура виручки за 2025 рік")
    plt.xlabel("Місяць")
    plt.ylabel("Сума")

    plt.xticks(range(1, 13), month_names)

    plt.ticklabel_format(style="plain", axis="y")

    plt.grid(axis="y", linestyle="--", alpha=0.5)
    plt.legend(loc="upper left", frameon=True)

    plt.tight_layout()
    plt.savefig(chart_path, dpi=300, bbox_inches="tight")
    plt.close()

    print("Stacked bar за 2025 рік побудовано.")
    print(f"Таблицю збережено: {table_path.relative_to(ROOT)}")
    print(f"Графік збережено: {chart_path.relative_to(ROOT)}")


# задание 2_05
# [Візуалізація] Pareto curve з лінією 80%
# Побудувати Pareto curve: cumulative revenue vs products (bar + line). Додати пунктирну лінію 80% для наочності.
def task_2_05_pareto_curve() -> None:
    print("\nЗавдання 2_05. Pareto curve з лінією 80%")

    result_dir = ROOT / "results" / "task_2_05"

    tx = pd.read_csv(OUT / "transactions_cleaned.csv", low_memory=False)

    tx["quantity"] = pd.to_numeric(tx["quantity"], errors="coerce").abs().replace(0, 1).fillna(1).astype(int)
    tx["discount_percent"] = pd.to_numeric(tx["discount_percent"], errors="coerce").fillna(0.0).astype(float)
    tx.loc[tx["discount_percent"] > 1, "discount_percent"] = tx.loc[tx["discount_percent"] > 1, "discount_percent"] / 100.0

    products = pd.read_excel(OUT / "company_data_cleaned.xlsx", sheet_name="Products")
    products["unit_price"] = pd.to_numeric(products["unit_price"], errors="coerce").fillna(0.0)
    products_clean = products[["product_id", "unit_price"]]

    df = pd.merge(tx, products_clean, on="product_id", how="left")

    df["revenue"] = df["quantity"] * df["unit_price"] * (1 - df["discount_percent"])

    product_revenue = df.groupby("product_id")["revenue"].sum().reset_index()

    product_revenue = product_revenue.sort_values(by="revenue", ascending=False).reset_index(drop=True)

    product_revenue["cum_revenue"] = product_revenue["revenue"].cumsum()

    total_revenue = product_revenue["revenue"].sum()
    product_revenue["cum_percentage"] = (product_revenue["cum_revenue"] / total_revenue) * 100

    product_revenue["product_id"] = product_revenue["product_id"].astype(str)

    result_dir.mkdir(parents=True, exist_ok=True)
    table_path = result_dir / "pareto_product_revenue.csv"
    chart_path = result_dir / "pareto_curve_80_percent.png"
    product_revenue.to_csv(table_path, index=False, encoding="utf-8-sig")

    fig, ax1 = plt.subplots(figsize=(14, 7))

    color_bar = "#4f81bd"
    ax1.bar(product_revenue["product_id"], product_revenue["revenue"], color=color_bar, alpha=0.85, label="Виручка продукту")
    ax1.set_xlabel("ID Продукту", fontsize=12, labelpad=10)
    ax1.set_ylabel("Виручка", color=color_bar, fontsize=12)
    ax1.tick_params(axis="y", labelcolor=color_bar)

    clean_labels = [str(int(float(x))) for x in product_revenue["product_id"]]

    ax1.set_xticks(range(len(product_revenue)))
    ax1.set_xticklabels(clean_labels, rotation=90, fontsize=5)

    ax1.yaxis.get_major_formatter().set_scientific(False)

    ax2 = ax1.twinx()
    color_line = "#c00000"
    ax2.plot(product_revenue["product_id"], product_revenue["cum_percentage"], color=color_line, marker="o", ms=4, lw=2, label="Кумулятивний %")
    ax2.set_ylabel("Кумулятивний відсоток", color=color_line, fontsize=12)
    ax2.tick_params(axis="y", labelcolor=color_line)
    ax2.set_ylim(0, 105)

    ax2.axhline(y=80, color="gray", linestyle="--", linewidth=1.5, label="Межа Парето (80%)")

    plt.title("Аналіз Парето", fontsize=16, pad=20)

    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="center right", frameon=True)

    ax1.grid(True, axis="y", linestyle=":", alpha=0.6)

    plt.tight_layout()
    plt.savefig(chart_path, dpi=300, bbox_inches="tight")
    plt.close()

    print("Pareto curve побудовано.")
    print(f"Таблицю збережено: {table_path.relative_to(ROOT)}")
    print(f"Графік збережено: {chart_path.relative_to(ROOT)}")


# задание 2_06
# 6. [Візуалізація] Dashboard (multi-plot):
# Dashboard (multi-plot): 4 графіки на одному полотні (subplots(2,2)):
# Revenue trend (line)
# Profit margin by store format (sns.barplot)
# Returns rate by category (pie — plt.pie)
# Monthly transaction count (sns.lineplot з marker='o')
def task_2_06_dashboard_multi_plot() -> None:
    print("\nЗавдання 2_06. Dashboard (multi-plot)")

    RESULT_DIR = ROOT / "results" / "task_2_06"

    transactions = pd.read_csv(OUT / "transactions_cleaned.csv", low_memory=False)
    products = pd.read_excel(OUT / "company_data_cleaned.xlsx", sheet_name="Products")
    returns = pd.read_csv(OUT / "returns_cleaned.csv", low_memory=False)
    stores = pd.read_excel(OUT / "company_data_cleaned.xlsx", sheet_name="Stores")

    transactions["transaction_date"] = pd.to_datetime(transactions["transaction_date"], errors="coerce")
    transactions["month"] = transactions["transaction_date"].dt.to_period("M").astype(str)

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle("Total Revenue")

    # 1. Revenue trend (line)
    revenue_trend = transactions.groupby("month", as_index=False)["total_amount"].sum()

    sns.lineplot(
        data=revenue_trend,
        x="month",
        y="total_amount",
        color="royalblue",
        marker="o",
        ax=axes[0, 0]
    )
    axes[0, 0].set_title("Revenue Trend")
    axes[0, 0].set_xlabel("Month")
    axes[0, 0].set_ylabel("Total Amount")
    axes[0, 0].tick_params(axis="x", rotation=90)

    # 2. Profit margin by store format (barplot)
    df = transactions.merge(products[["product_id", "margin_pct"]], on="product_id", how="left")
    df = df.merge(stores[["store_id", "store_format"]], on="store_id", how="left")
    df["profit"] = df["total_amount"] * df["margin_pct"] / 100

    df_clean = df.dropna(subset=["margin_pct"])
    df_clean = df_clean[df_clean["total_amount"] > 0]

    share_unknown = (df_clean["store_format"].isna().sum() / len(df_clean)) * 100
    print(f"Частка Unknown: {share_unknown:.1f}%")

    # враховуючи кількість транзакцій з магазином з форматом NaN та id NaN -5002 строки (5%), переназвемо формат
    # у 'Uknow' та зробимо умовні 'id'

    df_clean["store_format"] = df_clean["store_format"].fillna("Unknown")
    df_clean["store_id"] = df_clean["store_id"].fillna(-1)  # умовний ID

    profit_margin_format = (
        df_clean.groupby("store_format").apply(
        lambda g: g["profit"].sum()/ g["total_amount"].sum() * 100).
        reset_index(name="profit_margin")
    )

    sns.barplot(
        data=profit_margin_format,
        x="store_format",
        y="profit_margin",
        color="green",
        ax=axes[0, 1]
    )
    axes[0, 1].set_title("Profit Margin by Store Format")
    axes[0, 1].set_xlabel("Store Format")
    axes[0, 1].set_ylabel("Profit Margin")

    # 3. Returns rate by category (pie chart)
    returns = transactions[transactions["is_return"] == True]
    returns_rate = returns.merge(products[["product_id", "category"]], on="product_id", how="left")
    returns_rate = returns_rate.groupby("category")["transaction_id"].count()

    axes[1, 0].pie(
        returns_rate,
        labels=returns_rate.index,
        colors=sns.color_palette("pastel"),
        autopct="%1.1f%%"
    )
    axes[1, 0].set_title("Returns Rate by Category")

    # 4. Monthly transaction count (lineplot з marker='o')

    monthly_counts = transactions.groupby("month")["transaction_id"].count().reset_index()

    sns.lineplot(
        data=monthly_counts,
        x="month",
        y="transaction_id",
        marker="o",
        ax=axes[1, 1]
    )
    axes[1, 1].set_title("Monthly Transaction Count")
    axes[1, 1].set_xlabel("Month")
    axes[1, 1].set_ylabel("Transaction Count")
    axes[1, 1].tick_params(axis="x", rotation=90)

    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    dashboard_path = RESULT_DIR / "dashboard_multi_plot.png"
    revenue_trend_path = RESULT_DIR / "revenue_trend.csv"
    profit_margin_path = RESULT_DIR / "profit_margin_by_store_format.csv"
    returns_rate_path = RESULT_DIR / "returns_rate_by_category.csv"
    monthly_counts_path = RESULT_DIR / "monthly_transaction_count.csv"
    revenue_trend.to_csv(revenue_trend_path, index=False, encoding="utf-8-sig")
    profit_margin_format.to_csv(profit_margin_path, index=False, encoding="utf-8-sig")
    returns_rate.to_csv(returns_rate_path, encoding="utf-8-sig")
    monthly_counts.to_csv(monthly_counts_path, index=False, encoding="utf-8-sig")

    plt.tight_layout()
    plt.savefig(dashboard_path, dpi=300, bbox_inches="tight")
    plt.close()

    print(f"Таблицю збережено: {revenue_trend_path.relative_to(ROOT)}")
    print(f"Таблицю збережено: {profit_margin_path.relative_to(ROOT)}")
    print(f"Таблицю збережено: {returns_rate_path.relative_to(ROOT)}")
    print(f"Таблицю збережено: {monthly_counts_path.relative_to(ROOT)}")
    print(f"Графік збережено: {dashboard_path.relative_to(ROOT)}")


# задание 2_07
# Завдання 7. Блок 2.
# Time Series Analysis. З transactions.csv:
# Згрупувати по днях: sum(total_amount)
# Додати змінні: dayofweek, month, is_weekend, is_holiday_season (Nov-Dec)
# Порахувати 7-денне та 30-денне ковзне середнє (rolling()) — зверніть увагу, як rolling() згладжує шум.
# Використати shift() для визначення днів з різким зростанням/падінням виручки відносно попереднього дня
# (day-over-day change). Знайти топ-5 днів з найбільшим приростом та падінням.
# Визначити дні з аномальним падінням/зростанням (>2 std від середнього)
pd.set_option("display.max_columns", None)
pd.set_option("display.width", 1000)

DATA_PATH_TIME_SERIES = OUT / "transactions_cleaned.csv"


def group_transactions_by_day():
    if not DATA_PATH_TIME_SERIES.exists():
        print(f"Файл {DATA_PATH_TIME_SERIES} не знайдено!")
        return None

    df = pd.read_csv(DATA_PATH_TIME_SERIES)

    df["transaction_date"] = pd.to_datetime(df["transaction_date"])

    df["dayofweek"] = df["transaction_date"].dt.dayofweek
    df["month"] = df["transaction_date"].dt.month
    df["is_weekend"] = df["dayofweek"].isin([5, 6]).astype(int)
    df["is_holiday_season"] = df["month"].isin([11, 12]).astype(int)

    daily_stats = df.groupby(df["transaction_date"].dt.date).agg({
        "total_amount": "sum",
        "dayofweek": "first",
        "month": "first",
        "is_weekend": "max",
        "is_holiday_season": "max"
    }).reset_index()

    daily_stats.columns = ["date", "total_daily_amount", "dayofweek", "month", "is_weekend", "is_holiday_season"]

    return daily_stats


def analyze_revenue_trends(df: pd.DataFrame) -> pd.DataFrame:

    df = df.sort_values("date")

    df["rolling_7d"] = df["total_daily_amount"].rolling(window=7).mean()
    df["rolling_30d"] = df["total_daily_amount"].rolling(window=30).mean()

    df["dod_change"] = df["total_daily_amount"] - df["total_daily_amount"].shift(1)

    mean_change = df["dod_change"].mean()
    std_change = df["dod_change"].std()

    df["is_anomaly"] = (df["dod_change"].abs() > 2 * std_change).astype(int)

    return df


def task_2_07_time_series_analysis() -> None:
    print("\nЗавдання 2_07. Time Series Analysis")

    result_dir = ROOT / "results" / "task_2_07"

    df = group_transactions_by_day()

    if df is not None:

        print("Етап 1: Результат групування по днях")
        print(df)
        print("\n" + "=" * 50 + "\n")

        result = analyze_revenue_trends(df)

        print("Результати з ковзними середніми (перші 40 днів):")
        print(result[["date", "dayofweek", "month", "total_daily_amount", "is_weekend", "is_holiday_season",
                      "rolling_7d", "rolling_30d"]].head(40))
        print("\n" + "=" * 50 + "\n")

        print("Результати з ковзними середніми (кінець періоду):")
        print(result[["date", "dayofweek", "month", "total_daily_amount", "is_weekend", "is_holiday_season",
                      "rolling_7d", "rolling_30d"]].tail())
        print("\n" + "=" * 50 + "\n")

        top_growth = result.nlargest(5, "dod_change")
        top_drop = result.nsmallest(5, "dod_change")

        print("Топ-5 днів з найбільшим приростом:")
        print(top_growth[["date", "dayofweek", "month", "total_daily_amount", "is_weekend", "is_holiday_season",
                          "dod_change"]])
        print("\n" + "=" * 50 + "\n")

        print("Топ-5 днів з найбільшим падінням:")
        print(top_drop[["date", "dayofweek", "month", "total_daily_amount", "is_weekend", "is_holiday_season",
                        "dod_change"]])
        print("\n" + "=" * 50 + "\n")

        print("Дні з аномальними змінами (> 2 std)")
        anomalies = result[result["is_anomaly"] == 1][["date", "dayofweek", "month", "total_daily_amount", "is_weekend",
                                                       "is_holiday_season", "dod_change"]]
        print(anomalies)

        result_dir.mkdir(parents=True, exist_ok=True)
        daily_path = result_dir / "daily_revenue_time_series.csv"
        top_growth_path = result_dir / "top_5_growth_days.csv"
        top_drop_path = result_dir / "top_5_drop_days.csv"
        anomalies_path = result_dir / "anomaly_days.csv"
        result.to_csv(daily_path, index=False, encoding="utf-8-sig")
        top_growth.to_csv(top_growth_path, index=False, encoding="utf-8-sig")
        top_drop.to_csv(top_drop_path, index=False, encoding="utf-8-sig")
        anomalies.to_csv(anomalies_path, index=False, encoding="utf-8-sig")
        print(f"Таблицю збережено: {daily_path.relative_to(ROOT)}")
        print(f"Таблицю збережено: {top_growth_path.relative_to(ROOT)}")
        print(f"Таблицю збережено: {top_drop_path.relative_to(ROOT)}")
        print(f"Таблицю збережено: {anomalies_path.relative_to(ROOT)}")


# задание 2_08
# Завдання 8. Блок 2.
# Returns Analysis. З returns.csv (окремий файл з деталями повернень) та transactions.csv (де is_return == 1):
# Rate of returns by category (returns / total transactions) — використайте merge з Products для отримання категорії
# Average refund amount by reason (return_reason з returns.csv). Яка причина найдорожча?
# Чи корелює discount_percent із ймовірністю повернення? Порівняти середній discount для returns vs non-returns
# Чи відрізняється return rate по payment_method?
# Який середній час між покупкою та поверненням (return_date - transaction_date)?
# Конфігурація відображення
pd.set_option("display.max_columns", None)
pd.set_option("display.width", 1000)

DATA_DIR = OUT
FILES = {
    "transactions": DATA_DIR / "transactions_cleaned.csv",
    "returns": DATA_DIR / "returns_cleaned.csv",
    "products": DATA_DIR / "company_data_cleaned.xlsx"
}


def analyze_return_rate_by_category(transactions, returns, products):

    for name, path in FILES.items():
        if not path.exists():
            print(f"Помилка: Файл {path} не знайдено!")
            return None

    transactions = pd.read_csv(FILES["transactions"])
    returns = pd.read_csv(FILES["returns"])
    products = pd.read_excel(FILES["products"], sheet_name="Products")

    total_tx = transactions.groupby("product_id").size().reset_index(name="total_transactions")
    total_returns = returns.groupby("product_id").size().reset_index(name="total_returns")

    data = pd.merge(total_tx, total_returns, on="product_id", how="left").fillna(0)
    data = pd.merge(data, products[["product_id", "category"]], on="product_id", how="left")

    cat_stats = data.groupby("category").agg({"total_transactions": "sum", "total_returns": "sum"})
    cat_stats["return_rate_pct"] = (cat_stats["total_returns"] / cat_stats["total_transactions"]) * 100
    return cat_stats.sort_values("return_rate_pct", ascending=False)


def analyze_refunds_by_reason(returns):

    reason_stats = returns.groupby("return_reason")["refund_amount"].mean().sort_values(ascending=False)
    return reason_stats


def analyze_discount_vs_return(transactions):

    discount_stats = transactions.groupby("is_return")["discount_percent"].mean()

    correlation = transactions["discount_percent"].corr(transactions["is_return"])

    return discount_stats, correlation


def analyze_return_rate_by_payment(transactions):

    payment_stats = transactions.groupby("payment_method")["is_return"].mean() * 100
    return payment_stats.sort_values(ascending=False)


def analyze_return_time(returns):

    returns["transaction_date"] = pd.to_datetime(returns["transaction_date"])
    returns["return_date"] = pd.to_datetime(returns["return_date"])

    returns["days_to_return"] = (returns["return_date"] - returns["transaction_date"]).dt.days

    return returns["days_to_return"].mean()


def task_2_08_returns_analysis() -> None:
    print("\nЗавдання 2_08. Returns Analysis")

    result_dir = ROOT / "results" / "task_2_08"

    if not all(f.exists() for f in FILES.values()):
        print("Помилка: Не всі файли знайдено в папці cleaned_data!")
        return

    transactions = pd.read_csv(FILES["transactions"])
    returns = pd.read_csv(FILES["returns"])
    products = pd.read_excel(FILES["products"], sheet_name="Products")

    result_dir.mkdir(parents=True, exist_ok=True)

    category_results = analyze_return_rate_by_category(transactions, returns, products)
    print("Return Rate по категоріях")
    print(category_results)
    category_path = result_dir / "return_rate_by_category.csv"
    category_results.to_csv(category_path, encoding="utf-8-sig")
    print(f"Таблицю збережено: {category_path.relative_to(ROOT)}")
    print("\n" + "=" * 50 + "\n")

    reason_results = analyze_refunds_by_reason(returns)
    print("Середня сума повернення за причиною")
    print(reason_results)
    reason_path = result_dir / "average_refund_by_reason.csv"
    reason_results.to_csv(reason_path, encoding="utf-8-sig")
    print(f"Таблицю збережено: {reason_path.relative_to(ROOT)}")
    print("\n" + "=" * 50 + "\n")

    discount_stats, correlation = analyze_discount_vs_return(transactions)

    print("Вплив знижки на повернення")

    print("Середній discount_percent:")

    print(f"Non-returns (is_return=0): {discount_stats[0]:.2f}%")

    print(f"Returns (is_return=1): {discount_stats[1]:.2f}%")

    print(f"Коефіцієнт кореляції між знижкою та поверненням: {correlation:.4f}")

    if abs(correlation) < 0.1:
        print("Висновок: Зв'язок між знижкою та ймовірністю повернення майже відсутній.")
    else:
        print("Висновок: Існує помітний статистичний зв'язок між розміром знижки та поверненнями.")

    discount_path = result_dir / "discount_vs_return.csv"
    pd.DataFrame(
        {
            "is_return": discount_stats.index,
            "average_discount_percent": discount_stats.values,
            "correlation": correlation,
        }
    ).to_csv(discount_path, index=False, encoding="utf-8-sig")
    print(f"Таблицю збережено: {discount_path.relative_to(ROOT)}")
    print("\n" + "=" * 50 + "\n")

    print("Return Rate за методом оплати (%)")
    payment_results = analyze_return_rate_by_payment(transactions)
    print(payment_results)
    payment_path = result_dir / "return_rate_by_payment_method.csv"
    payment_results.to_csv(payment_path, encoding="utf-8-sig")
    print(f"Таблицю збережено: {payment_path.relative_to(ROOT)}")
    print("\n" + "=" * 50 + "\n")

    avg_days = analyze_return_time(returns)
    print(f"Середній час між покупкою та поверненням")
    print(f"Клієнти повертають товар в середньому через {avg_days:.1f} днів.")
    time_path = result_dir / "average_return_time.csv"
    pd.DataFrame(
        {
            "metric": ["average_days_to_return"],
            "value": [avg_days],
        }
    ).to_csv(time_path, index=False, encoding="utf-8-sig")
    print(f"Таблицю збережено: {time_path.relative_to(ROOT)}")


# задание 2_09
# [Просунуті] Магазинна аналітика
# Магазинна аналітика. З company_data.xlsx (Stores + Employees + Inventory + transactions):
# Revenue per square meter (total_amount / size_sqm) по store_format
# Revenue per employee (total_amount / кількість співробітників) по магазинах
# Найефективніший магазин за обома метриками
def task_2_09_store_analytics() -> None:
    print("\nЗавдання 2_09. Магазинна аналітика")

    result_dir = ROOT / "results" / "task_2_09"

    excel_file = OUT / "company_data_cleaned.xlsx"
    transactions_path = OUT / "transactions_cleaned.csv"

    df_stores = pd.read_excel(excel_file, sheet_name="Stores")
    df_employees = pd.read_excel(excel_file, sheet_name="Employees")

    try:
        df_transactions = pd.read_csv(
            transactions_path,
            low_memory=False
        )

        needed_cols = ["store_id", "total_amount", "is_return"]
        df_transactions = df_transactions[[col for col in needed_cols if col in df_transactions.columns]]

    except Exception as e:
        print(f"ERROR: {e}")
        df_transactions = pd.read_csv(transactions_path, sep=";", on_bad_lines="skip")

    if df_transactions.empty or "total_amount" not in df_transactions.columns:
        print("ERROR")

    df_transactions["is_return"] = pd.to_numeric(df_transactions["is_return"], errors="coerce").fillna(0)
    df_transactions["total_amount"] = pd.to_numeric(df_transactions["total_amount"], errors="coerce").fillna(0)
    df_transactions["store_id"] = pd.to_numeric(df_transactions["store_id"], errors="coerce").fillna(-1)

    df_valid_sales = df_transactions[df_transactions["is_return"] == 0]
    store_revenue = df_valid_sales.groupby("store_id")["total_amount"].sum().reset_index()
    store_revenue.columns = ["store_id", "total_revenue"]

    # співробітники, що реально працюють (зі статусом активно)
    df_employees["status"] = df_employees["status"].astype(str).str.strip().str.lower()
    df_active_emp = df_employees[df_employees["status"] == "active"]
    employee_count = df_active_emp.groupby("store_id")["employee_id"].count().reset_index()
    employee_count.columns = ["store_id", "employee_count"]

    df_analytics = df_stores.merge(store_revenue, on="store_id", how="left").fillna(0)
    df_analytics = df_analytics.merge(employee_count, on="store_id", how="left").fillna(0)

    df_analytics["store_format"] = df_analytics["store_format"].astype(str).str.strip()
    df_analytics["store_format"] = df_analytics["store_format"].replace({"Streett": "Street", "Mal": "Mall"})

    # метрики в розрізі магазинів
    df_analytics["revenue_per_sqm"] = df_analytics.apply(
        lambda r: r["total_revenue"] / r["size_sqm"] if str(r["store_format"]).lower() != "online" and r[
            "size_sqm"] > 0 else 0,
        axis=1
    )

    df_analytics["revenue_per_employee"] = df_analytics.apply(
        lambda r: r["total_revenue"] / r["employee_count"] if r["employee_count"] > 0 else 0,
        axis=1
    )

    # ефективності по формату магазина
    df_offline_only = df_analytics[df_analytics["store_format"].str.lower() != "online"]
    format_grouped = df_offline_only.groupby("store_format").agg(
        total_revenue=("total_revenue", "sum"),
        total_size=("size_sqm", "sum")
    ).reset_index()
    format_grouped["revenue_per_sqm"] = format_grouped["total_revenue"] / format_grouped["total_size"]

    # найефективніший магазин (метод рангів для офлайн магазинів)
    df_rank = df_offline_only[df_offline_only["size_sqm"] > 0].copy()
    if not df_rank.empty:
        df_rank["rank_sqm"] = df_rank["revenue_per_sqm"].rank(ascending=False)
        df_rank["rank_emp"] = df_rank["revenue_per_employee"].rank(ascending=False)
        df_rank["combined_score"] = df_rank["rank_sqm"] + df_rank["rank_emp"]
        best_store = df_rank.sort_values(by="combined_score", ascending=True).iloc[0]
    else:
        best_store = None

    result_dir.mkdir(parents=True, exist_ok=True)
    analytics_path = result_dir / "store_analytics.csv"
    format_path = result_dir / "revenue_per_sqm_by_store_format.csv"
    best_store_path = result_dir / "best_store_by_metrics.csv"
    df_analytics.to_csv(analytics_path, index=False, encoding="utf-8-sig")
    format_grouped.to_csv(format_path, index=False, encoding="utf-8-sig")

    format_print = format_grouped.copy()
    format_print["revenue_per_sqm"] = format_print["revenue_per_sqm"].map("{:,.2f}".format)
    print(f"Revenue per square meter:\n\n{format_print[['store_format', 'revenue_per_sqm']].to_string(index=False)}\n")
    print("-" * 20)

    df_console = df_analytics.copy()
    df_console["total_revenue"] = df_console["total_revenue"].map("{:,.2f}".format)
    df_console["revenue_per_sqm"] = df_console["revenue_per_sqm"].map("{:,.2f}".format)
    df_console["revenue_per_employee"] = df_console["revenue_per_employee"].map("{:,.2f}".format)
    print(f"Загальний звіт по магазинам (перші 20):\n\n"
          f"{df_console[['store_id', 'store_name', 'store_format', 'size_sqm', 'employee_count', 'total_revenue', 'revenue_per_sqm', 'revenue_per_employee']].head(20).to_string(index=False)}\n")
    print("-" * 20)

    if best_store is not None:
        print(f"Найефективніший фізичний магазин за обома показниками:\n\n",
              f"Магазин: {best_store['store_name']} (ID: {best_store['store_id']})\n",
              f"Країна: {best_store['country']}. Формат: {best_store['store_format']}\n",
              f"Площа: {best_store['size_sqm']} кв.м. Штат: {int(best_store['employee_count'])} співробітників\n",
              f"Виручка/кв. метр: {best_store['revenue_per_sqm']:,.2f}\n",
              f"Виручка/одного співробітника: {best_store['revenue_per_employee']:,.2f}")
        best_store.to_frame().T.to_csv(best_store_path, index=False, encoding="utf-8-sig")
        print(f"Таблицю збережено: {best_store_path.relative_to(ROOT)}")

    print(f"Таблицю збережено: {analytics_path.relative_to(ROOT)}")
    print(f"Таблицю збережено: {format_path.relative_to(ROOT)}")


# задание 2_10
# 10. [Просунуті] Фінансове моделювання P&L.
# Фінансове моделювання. Створити P&L по місяцях:
# - Revenue: sum(total_amount)
# - COGS: sum(quantity * cost_price)
# - Gross Profit = Revenue - COGS
# - Marketing Cost: sum(budget) з marketing.csv по місяцях кампаній
# - Salary Cost: sum(net_pay) з salaries.parquet по місяцях
# - Operating Profit = Gross Profit - Marketing - Salaries - 5% операційні
# - Net Margin % = Operating Profit / Revenue * 100
def task_2_10_load_table(filename: str, sep: str = ",") -> pd.DataFrame:
    path = OUT / filename
    if not path.exists():
        raise FileNotFoundError(f"Файл {path} не знайдено")
    return pd.read_csv(path, low_memory=False, sep=sep)


def task_2_10_pnl_financial_modeling() -> None:
    print("\nЗавдання 2_10. P&L Financial Modeling")

    RESULT_DIR = ROOT / "results" / "task_2_10"

    transactions = task_2_10_load_table("transactions_cleaned.csv")
    products = pd.read_excel(OUT / "company_data_cleaned.xlsx", sheet_name="Products")
    marketing = task_2_10_load_table("marketing_cleaned.csv")
    salaries = task_2_10_load_table("salaries_cleaned.csv")

    # Transactions
    transactions["transaction_date"] = pd.to_datetime(transactions["transaction_date"], errors="coerce")
    transactions["month"] = transactions["transaction_date"].dt.to_period("M")

    # - Revenue: sum(total_amount). Revenue: сума total_amount по місяцях
    revenue = transactions.groupby("month")["total_amount"].sum().reset_index(name="Revenue")

    # - COGS: sum(quantity * cost_price). COGS: сума quantity * cost_price по місяцях
    transactions = transactions.merge(products[["product_id", "product_name", "cost_price"]], on="product_id", how="left")
    transactions["COGS"] = transactions["quantity"] * transactions["cost_price"]
    cogs = transactions.groupby("month")["COGS"].sum().reset_index()

    # - Gross Profit = Revenue - COGS.
    pnl = revenue.merge(cogs, on="month")
    pnl["Gross Profit"] = pnl["Revenue"] - pnl["COGS"]

    # - Marketing Cost: sum(budget) з marketing.csv по місяцях кампаній

    # Точний варіант (розподіл бюджету по всіх місяцях кампанії), як кaмпанія триває декілька місяців - більш точний
    marketing["start_date"] = pd.to_datetime(marketing["start_date"], errors="coerce")
    marketing["end_date"] = pd.to_datetime(marketing["end_date"], errors="coerce")

    rows = []
    for _, row in marketing.iterrows():
        if pd.notnull(row["start_date"]) and pd.notnull(row["end_date"]):
            # список місяців між start_date і end_date
            months = pd.period_range(row["start_date"], row["end_date"], freq="M")
            # рівномірний розподіл бюджету
            monthly_budget = row["budget"] / len(months) if len(months) > 0 else row["budget"]
            for m in months:
                rows.append({"month": m, "Marketing Cost": monthly_budget})

    marketing_cost = pd.DataFrame(rows).groupby("month")["Marketing Cost"].sum().reset_index()

    pnl = pnl.merge(marketing_cost, on="month", how="left").fillna({"Marketing Cost": 0})

    # - Salary Cost: sum(net_pay) з salaries.parquet по місяцях
    # сума net_pay по місяцях - беремо готову колонку month
    salaries["month"] = salaries["month"].astype("period[M]")
    salary_cost = salaries.groupby("month")["net_pay"].sum().reset_index(name="Salary Cost")

    pnl = pnl.merge(salary_cost, on="month", how="left").fillna({"Salary Cost": 0})

    # - Operating Profit = Gross Profit - Marketing - Salaries - 5% операційні
    pnl["Operating Profit"] = pnl["Gross Profit"] - pnl["Marketing Cost"] - pnl["Salary Cost"] - (pnl["Revenue"] * 0.05)

    # - Net Margin % = Operating Profit / Revenue * 100
    pnl["Net Margin %"] = pnl["Operating Profit"] / pnl["Revenue"] * 100

    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    table_path = RESULT_DIR / "pnl_financial_modeling.csv"
    net_margin_chart_path = RESULT_DIR / "net_margin_by_month.png"
    revenue_profit_chart_path = RESULT_DIR / "revenue_vs_operating_profit.png"
    pnl.to_csv(table_path, index=False, encoding="utf-8-sig")

    print(pnl.head())
    print(f"Таблицю збережено: {table_path.relative_to(ROOT)}")

    # Net Margin % — негативний, показує збитковість.
    # Висновок: вийшла таблиця P&L по місяцях — і видно, що витрати на зарплати та маркетинг значно перевищують
    # валовий прибуток, тому Operating Profit виходить від’ємним, а Net Margin % негативний (наприклад, −58% у січні).
    # Це тестові дані, то: модель правильно працює, просто фінансові показники показують збитковість

    # графіки для візуалізації:
    # Лінійний графік Net Margin %
    plt.figure(figsize=(10, 4))
    plt.plot(pnl["month"].astype(str), pnl["Net Margin %"], marker="o", color="red")
    plt.xticks(rotation=90)
    plt.title("Net Margin % по місяцях", fontsize=14, fontweight="bold")
    plt.xlabel("Місяць")
    plt.ylabel("Net Margin %")
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(net_margin_chart_path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"Графік збережено: {net_margin_chart_path.relative_to(ROOT)}")

    # Барплот Revenue vs Operating Profit
    plt.figure(figsize=(10, 5))
    width = 0.35
    x = range(len(pnl["month"]))

    plt.bar(x, pnl["Revenue"], width=width, label="Revenue", color="skyblue")
    plt.bar([i + width for i in x], pnl["Operating Profit"], width=width, label="Operating Profit", color="green")

    plt.xticks([i + width / 2 for i in x], pnl["month"].astype(str), rotation=90)
    plt.title("Revenue vs Operating Profit по місяцях", fontsize=14, fontweight="bold")
    plt.xlabel("Місяць", fontsize=14)
    plt.ylabel("Сума")
    plt.legend()
    plt.tight_layout()
    plt.savefig(revenue_profit_chart_path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"Графік збережено: {revenue_profit_chart_path.relative_to(ROOT)}")


def main() -> None:
    clean_data()
    task_1_01_top_products_by_revenue()
    task_1_02_pivot_table()
    task_1_03_average_check_by_store()
    task_1_04_barplot_revenue_by_category()
    task_1_05_correlation_heatmap()
    task_1_06_sales_distribution_plots()
    task_1_07_abc_analysis_of_products()
    task_1_08_market_basket_analysis()
    task_1_09_discount_analysis()
    task_1_10_cohort_retention()
    task_1_11_clv_estimation()
    task_2_01_profit_analysis()
    task_2_02_patero_analysis_80()
    task_2_03_data_quality_score()
    task_2_04_monthly_revenue_stacked_bar()
    task_2_05_pareto_curve()
    task_2_06_dashboard_multi_plot()
    task_2_07_time_series_analysis()
    task_2_08_returns_analysis()
    task_2_09_store_analytics()
    task_2_10_pnl_financial_modeling()


if __name__ == "__main__":
    main()
