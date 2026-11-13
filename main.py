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
        report["api_logs.json"] = "Datei im Projektordner nicht gefunden"

    database = ROOT / "analytics_practice.db"
    if database.exists():
        clean_database(database, OUT / "analytics_practice_cleaned.db")
        report["analytics_practice_cleaned.db"] = "Bereinigte Kopie erstellt"

    with (OUT / "cleaning_report.json").open("w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2, default=str)
    print(f"Fertig: {OUT}")
    print(json.dumps(report, ensure_ascii=False, indent=2, default=str))


# Aufgabe 1_01
# Grundlagen (pandas)
# 1. Top-10-Produkte nach Umsatz.
# transactions.csv nach product_id gruppieren (nur Verkäufe, keine Retouren) und sum(total_amount) berechnen.
# Mit Products aus company_data.xlsx zusammenführen und die Tabelle ausgeben.
def task_1_01_top_products_by_revenue() -> None:
    print("\nAufgabe 1_01. Top-10-Produkte nach Umsatz")

    transactions_path = OUT / 'transactions_cleaned.csv'
    excel_path = OUT / 'company_data_cleaned.xlsx'

    df_transactions = pd.read_csv(transactions_path, low_memory=False)
    df_products = pd.read_excel(excel_path, sheet_name='Products')

    df_transactions = df_transactions[df_transactions['is_return'] == 0].copy()
    if df_transactions['total_amount'].dtype == 'object':
        df_transactions['total_amount'] = df_transactions['total_amount'].astype(str).str.replace("", regex=True)
    df_transactions['total_amount'] = pd.to_numeric(df_transactions['total_amount'], errors='coerce')

    # Produkte gruppieren und Gesamtumsatz berechnen
    revenue_per_product = (
        df_transactions.groupby('product_id')['total_amount']
        .sum()
        .reset_index()
    )
    revenue_per_product.columns = ['product_id', 'total_amount']

    final_table = pd.merge(revenue_per_product, df_products, on='product_id', how='inner')

    # Top-10-Produkte absteigend sortieren
    top_10_products = (
        final_table.sort_values(by='total_amount', ascending=False)
        .head(10)
        .reset_index(drop=True)
    )

    top_10_products['total_amount'] = top_10_products['total_amount'].map('{:,.2f}'.format)
    output_columns = ['product_name', 'category', 'total_amount']
    available_columns = [col for col in output_columns if col in top_10_products.columns]

    print(f'\nTop-10-Produkte nach Umsatz:\n\n{top_10_products[available_columns].to_string(index=False)}')
    result_dir = ROOT / "results" / "task_1_01"
    result_dir.mkdir(parents=True, exist_ok=True)
    output_path = result_dir / "top_10_products_by_revenue.csv"
    top_10_products[available_columns].to_csv(output_path, index=False, encoding="utf-8-sig")
    print(f"Tabelle gespeichert: {output_path.relative_to(ROOT)}")
    print('-' * 20)


# Aufgabe 1_02
# 2. Umsatzverteilung nach Kategorien mit pivot_table:
# category als Zeilen, Monat als Spalten, Summe von total_amount.
# Welche Kategorie führt jeden Monat?
def task_1_02_pivot_table() -> None:
    print("\nAufgabe 1_02. Umsatzverteilung nach Kategorien")

    CLEAN_DIR = OUT
    RESULT_DIR = ROOT / "results" / "task_1_02_patero_analysis"

    def load_table(filename: str, sep: str = ",") -> pd.DataFrame:
        """Universelles Laden bereinigter Tabellen aus cleaned_data"""
        if filename == "products_cleaned.csv":
            path = CLEAN_DIR / "company_data_cleaned.xlsx"
            if not path.exists():
                raise FileNotFoundError(f"Datei {path} nicht gefunden")
            return pd.read_excel(path, sheet_name="Products")

        path = CLEAN_DIR / filename
        if not path.exists():
            raise FileNotFoundError(f"Datei {path} nicht gefunden")
        return pd.read_csv(path, low_memory=False, sep=sep)

    # 1. Bereinigte Tabellen laden
    transactions = load_table("transactions_cleaned.csv")
    products = load_table("products_cleaned.csv")

    # 2. Datum in datetime umwandeln und Monat extrahieren
    transactions["transaction_date"] = pd.to_datetime(transactions["transaction_date"], errors="coerce")
    transactions["month"] = transactions["transaction_date"].dt.month

    # 3. Transaktionen und Produkte über product_id zusammenführen
    df = transactions.merge(products, on="product_id", how="left")

    # 4. pivot_table erstellen: Kategorien als Zeilen, Monate als Spalten, Summe von total_amount
    pivot = pd.pivot_table(
        df,
        values="total_amount",
        index="category",
        columns="month",
        aggfunc="sum",
        fill_value=0
    )

    print("Pivot table 'Revenue breakdown by category and month':\n", pivot)

    # 5. Führende Kategorie für jeden Monat bestimmen
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
    print(f"Pivot-Tabelle gespeichert: {pivot_path.relative_to(ROOT)}")
    print(f"Leaderboard-Tabelle gespeichert: {leaders_path.relative_to(ROOT)}")


# Aufgabe 1_03
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
        f"durchschnittlicher Bonwert = {store['average_check']:.2f}"
    )


def task_1_03_average_check_by_store() -> None:
    print("\nAufgabe 1_03. Durchschnittlicher Bonwert pro Filiale")

    transactions, stores = load_data()
    result = calculate_average_check(transactions, stores)

    if result.empty:
        raise ValueError("Keine Verkäufe für die Berechnung des durchschnittlichen Bonwerts gefunden")

    output_path = save_results(result)
    print_store("Höchster durchschnittlicher Bonwert", result.iloc[0])
    print_store("Niedrigster durchschnittlicher Bonwert", result.iloc[-1])
    print(f"Tabelle gespeichert: {output_path.relative_to(ROOT)}")


# Aufgabe 1_04
# Visualisierung (matplotlib/seaborn)
# 4. Balkendiagramm: Umsatz nach Kategorien für 2024 und 2025 (nebeneinander).
def task_1_04_barplot_revenue_by_category() -> None:
    print("\nAufgabe 1_04. Balkendiagramm: Umsatz nach Kategorien für 2024 und 2025")

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

    print("Tabellen zusammenführen und Umsatz berechnen...")
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

    plt.title('Umsatz nach Kategorien für 2024 und 2025 ', fontsize=16, pad=15)
    plt.xlabel('Produktkategorie', fontsize=12, labelpad=10)
    plt.ylabel('Gesamtumsatz', fontsize=12, labelpad=10)

    plt.ticklabel_format(style='plain', axis='y')
    plt.xticks(rotation=30, ha='right')
    plt.legend(title='Jahr', loc='upper right')
    plt.tight_layout()

    plt.savefig(chart_path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"Tabelle gespeichert: {table_path.relative_to(ROOT)}")
    print(f"Diagramm gespeichert: {chart_path.relative_to(ROOT)}")


# Aufgabe 1_05
# Heatmap (sns.heatmap): Korrelation von unit_price, cost_price, margin_pct, quantity und total_amount.
# annot=True und cmap='coolwarm' verwenden.
def task_1_05_correlation_heatmap() -> None:
    print("\nAufgabe 1_05. Heatmap: Korrelation numerischer Kennzahlen")

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

    plt.title("Korrelationsmatrix")
    plt.tight_layout()
    plt.savefig(chart_path, dpi=300, bbox_inches="tight")
    plt.close()

    print("Korrelationsmatrix erstellt.")
    print(f"Tabelle gespeichert: {table_path.relative_to(ROOT)}")
    print(f"Diagramm gespeichert: {chart_path.relative_to(ROOT)}")


# Aufgabe 1_06
# 6. Boxplot / Violinplot (seaborn) + KDE: Verteilung von total_amount nach Kategorien (nur Verkäufe > 0). Ausreißer anzeigen. Beide Varianten testen:
#    - sns.boxplot() — Median, Quartile und Ausreißer
#    - sns.violinplot() — Boxplot + KDE (Verteilungsdichte)
#    - Zusätzlich: sns.kdeplot(data=df, x='total_amount', hue='category', fill=True) — Verteilungen der Kategorien in einem Diagramm vergleichen
def task_1_06_sales_distribution_plots() -> None:
    print("\nAufgabe 1_06. Sales distribution plots")

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
    plt.xlabel("Produktkategorie")
    plt.ylabel("Summe")
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
    plt.xlabel("Produktkategorie")
    plt.ylabel("Transaktionsbetrag")
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
    plt.xlabel("Transaktionsbetrag")
    plt.ylabel("Verteilungsdichte")
    plt.ticklabel_format(style="plain", axis="x")
    plt.tight_layout()
    plt.savefig(kdeplot_path, dpi=300, bbox_inches="tight")
    plt.close()

    print(f"Diagramme erstellt für {df_filtered['category'].nunique()} Kategorien.")
    print(f"Tabelle gespeichert: {table_path.relative_to(ROOT)}")
    print(f"Diagramm gespeichert: {boxplot_path.relative_to(ROOT)}")
    print(f"Diagramm gespeichert: {violinplot_path.relative_to(ROOT)}")
    print(f"Diagramm gespeichert: {kdeplot_path.relative_to(ROOT)}")


# Aufgabe 1_07
# 7. [Fortgeschritten] ABC-Analyse der Produkte. Umsatz je Produkt berechnen.
# ABC-Analyse der Produkte. Umsatz je Produkt berechnen und absteigend sortieren,
# cumsum() für den kumulierten Anteil hinzufügen. A = erste 70 % des Umsatzes, B = 70–90 %, C = letzte 10 %.
# Wie viele Produkte gehören zu A, B und C?
def task_1_07_abc_analysis_of_products() -> None:
    print("\nAufgabe 1_07. ABC-Analyse der Produkte")

    RESULT_DIR = ROOT / "results" / "task_1_07"

    transactions = pd.read_csv(OUT / "transactions_cleaned.csv", low_memory=False)
    products = pd.read_excel(OUT / "company_data_cleaned.xlsx", sheet_name="Products")

    # 1. Summe виручки на товар
    revenue_per_product = transactions.groupby("product_id")["total_amount"].sum().reset_index()

    # 2. Mit products für Kategorien und Namen zusammenführen
    revenue_per_product = revenue_per_product.merge(products, on="product_id", how="left")

    # 3. Absteigend sortieren
    revenue_per_product = revenue_per_product.sort_values("total_amount", ascending=False)

    # 4. Kumulierten Anteil berechnen
    total_revenue = revenue_per_product["total_amount"].sum()
    revenue_per_product["cum_share"] = revenue_per_product["total_amount"].cumsum() / total_revenue * 100

    # 5. Gruppen A/B/C zuweisen und die Anzahl der Produkte je Gruppe zählen
    def abc_group(x):
        if x <= 70:
            return "A (erste 70 % des Umsatzes)"
        elif x <= 90:
            return "B (70–90%)"
        else:
            return "C (letzte 10 %)"

    revenue_per_product["ABC"] = revenue_per_product["cum_share"].apply(abc_group)

    abc_counts = revenue_per_product["ABC"].value_counts()

    # 7. Umsatzsumme der Produkte in Gruppe C (10 %) berechnen
    sum_c = revenue_per_product[revenue_per_product["ABC"] == "C (letzte 10 %)"]["total_amount"].sum()

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
    print(f"Tabelle gespeichert: {table_path.relative_to(ROOT)}")
    print(f"Tabelle gespeichert: {counts_path.relative_to(ROOT)}")


# Aufgabe 1_08
# Block 1. Aufgabe 8.
# Market-Basket-Analyse. Für jede customer_id alle Kategorien der an einem Tag gekauften Produkte sammeln.
# Die häufigsten gemeinsam gekauften Kategoriepaare finden (Kombinationen aus 2 Kategorien).
# Welche 5 Paare sind am häufigsten?
# > Hinweis: Wenn es zu wenige Same-Day-Käufe gibt, nach customer_id + Woche über .dt.isocalendar().week gruppieren.
# itertools.combinations() zur Erzeugung der Kategoriepaare verwenden.
# Für die Zählung value_counts() auf der Paar-Serie oder nunique() für die Anzahl eindeutiger Paare verwenden.
def task_1_08_market_basket_analysis() -> None:
    print("\nAufgabe 1_08. Market Basket Analysis")

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

    print(" Top-5 gemeinsam gekaufter Kategoriepaare")
    print(top_5)
    print(f"Tabelle gespeichert: {table_path.relative_to(ROOT)}")


# Aufgabe 1_09
# Block 1. Aufgabe 9.
# Rabattanalyse. Transaktionen aufteilen: discount_percent == 0 gegenüber >0.
#  Durchschnittliche Stückzahl (quantity) und Umsatz vergleichen. Wirken die Rabatte?
DATA_PATH = OUT / "transactions_cleaned.csv"


def task_1_09_discount_analysis() -> None:
    print("\nAufgabe 1_09. Rabattanalyse")

    result_dir = ROOT / "results" / "task_1_09"

    if not os.path.exists(DATA_PATH):
        print(f"Datei {DATA_PATH} nicht gefunden!")
        return

    df = pd.read_csv(DATA_PATH)

    no_discount_df = df[df["discount_percent"] == 0]
    with_discount_df = df[df["discount_percent"] > 0]

    no_discount_table = pd.DataFrame({"Кількість": [no_discount_df["transaction_id"].count()],
                                      "Summe": [no_discount_df["total_amount"].sum()]})
    with_discount_table = pd.DataFrame({"Кількість": [with_discount_df["transaction_id"].count()],
                                        "Summe": [with_discount_df["total_amount"].sum()]})

    print("TABELLE: Transaktionen OHNE Rabatt")
    print(no_discount_table)
    print("\n" + "=" * 50 + "\n")

    print("TABELLE: Transaktionen MIT Rabatt")
    print(with_discount_table)
    print("\n" + "=" * 50 + "\n")

    df["discount_group"] = ["Без знижки" if d == 0 else "Зі знижкою" for d in df["discount_percent"]]
    analysis = df.groupby("discount_group")[["quantity", "total_amount"]].mean()

    print("DURCHSCHNITTSWERTE: Ohne Rabatt vs. Mit Rabatt")
    print(analysis.round(2))

    print(" FAZIT")
    q_no = analysis.loc["Без знижки", "quantity"]
    q_yes = analysis.loc["Зі знижкою", "quantity"]
    t_no = analysis.loc["Без знижки", "total_amount"]
    t_yes = analysis.loc["Зі знижкою", "total_amount"]

    if q_yes > q_no:
        print(f"- Die Anzahl der Produkte im Warenkorb ist mit Rabatt höher (+{((q_yes / q_no) - 1) * 100:.1f}%)")
    else:
        print("- Rabatte motivieren Kunden NICHT, mehr Produkte zu kaufen.")

    if t_yes < t_no:
        print("- Der durchschnittliche Bonwert ist mit Rabatt NIEDRIGER: Rabatte senken die Marge ohne zusätzliches Volumen.")
    else:
        print("- Der durchschnittliche Bonwert ist mit Rabatt höher — die Aktionen wirken effektiv.")

    result_dir.mkdir(parents=True, exist_ok=True)
    no_discount_path = result_dir / "transactions_without_discount.csv"
    with_discount_path = result_dir / "transactions_with_discount.csv"
    analysis_path = result_dir / "discount_analysis.csv"
    no_discount_table.to_csv(no_discount_path, index=False, encoding="utf-8-sig")
    with_discount_table.to_csv(with_discount_path, index=False, encoding="utf-8-sig")
    analysis.round(2).to_csv(analysis_path, encoding="utf-8-sig")
    print(f"Tabelle gespeichert: {no_discount_path.relative_to(ROOT)}")
    print(f"Tabelle gespeichert: {with_discount_path.relative_to(ROOT)}")
    print(f"Tabelle gespeichert: {analysis_path.relative_to(ROOT)}")


# Aufgabe 1_10
def task_1_10_cohort_retention() -> None:
    print("\nAufgabe 1_10. Cohort Retention")

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
    plt.title("Cohort Retention nach Kategorie des Erstkaufs")
    plt.xlabel("Monat nach dem Erstkauf")
    plt.ylabel("Monat des Erstkaufs")
    plt.tight_layout()
    plt.savefig(chart_path, dpi=180, bbox_inches="tight")
    plt.close()

    print(
        f"Cohort Retention: {len(retention)} Kohorten, "
        f"{retention.columns[0]}-{retention.columns[-1]}"
    )
    print(f"Tabelle gespeichert: {retention_path.relative_to(ROOT)}")
    print(f"Tabelle gespeichert: {details_path.relative_to(ROOT)}")
    print(f"Diagramm gespeichert: {chart_path.relative_to(ROOT)}")


# Aufgabe 1_11
def task_1_11_clv_estimation() -> None:
    print("\nAufgabe 1_11. CLV Estimation")

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
    axes[0].set_title("Anzahl der Kunden nach CLV-Segment")
    axes[0].set_xlabel("CLV-сегмент")
    axes[0].set_ylabel("Anzahl der Kunden")

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
    axes[1].set_title("Durchschnittlicher CLV nach Segment")
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
    print(f"Tabelle gespeichert: {monthly_path.relative_to(ROOT)}")
    print(f"Tabelle gespeichert: {customers_path.relative_to(ROOT)}")
    print(f"Tabelle gespeichert: {summary_path.relative_to(ROOT)}")
    print(f"Diagramm gespeichert: {chart_path.relative_to(ROOT)}")


# Aufgabe 2_01
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
    print("\nAufgabe 2_01. Profit Analysis")

    transactions, products, stores = task_2_01_load_data()
    sales = task_2_01_prepare_sales(transactions, products, stores)
    monthly = task_2_01_calculate_monthly_profit(sales)

    if monthly.empty:
        raise ValueError("Keine Daten zur Gewinnberechnung gefunden")

    best_month = monthly.loc[monthly["total_profit"].idxmax()]
    worst_month = monthly.loc[monthly["total_profit"].idxmin()]
    output_path = task_2_01_save_results(monthly)

    print(
        f"Profitabelster Monat: {best_month['month']}, "
        f"Gewinn = {best_month['total_profit']:.2f}"
    )
    print(
        f"Monat mit dem niedrigsten Gewinn: {worst_month['month']}, "
        f"Gewinn = {worst_month['total_profit']:.2f}"
    )
    if worst_month["total_profit"] < 0:
        print("Dieser Monat war defizitär.")
    else:
        print("Es gibt keine defizitären Monate.")
    print(f"Tabelle gespeichert: {output_path.relative_to(ROOT)}")


# Aufgabe 2_02
# 2.2. Pareto-Analyse (80/20).
# Pareto-Analyse (80/20). Für alle Produkte aus Products:
# Anteil jedes Produkts am Gesamtumsatz (transactions) berechnen
# Absteigend sortieren und cumsum berechnen
# Ermitteln, wie viele Produkte 80 % des Umsatzes erzeugen
# Visualisieren: Pareto-Kurve (Linie + Balken)
def task_2_02_patero_analysis_80() -> None:
    print("\nAufgabe 2_02. Patero Analysis (80/20)")

    CLEAN_DIR = OUT
    RESULT_DIR = ROOT / "results" / "task_2_02_patero_analysis_80"

    def load_table(filename: str, sep: str = ",") -> pd.DataFrame:
        """Universelles Laden bereinigter Tabellen aus cleaned_data"""
        path = CLEAN_DIR / filename
        if not path.exists():
            raise FileNotFoundError(f"Datei {path} nicht gefunden")
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
        return "Erste 80 % des Umsatzes" if x < n_products_80 else "Letzte 20 % des Umsatzes"

    revenue_per_product["80/20"] = [group(i) for i in range(len(revenue_per_product))]

    print('Produktanzahl in der Gruppe "Erste 80 % des Umsatzes": ', n_products_80)

    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    table_path = RESULT_DIR / "patero_analysis_80.csv"
    chart_path = RESULT_DIR / "patero_analysis_80.png"
    revenue_per_product.to_csv(table_path, index=False, encoding="utf-8-sig")

    # графік та лінія
    fig, ax1 = plt.subplots(figsize=(15, 7))

    colors = revenue_per_product["80/20"].map({
        "Erste 80 % des Umsatzes": "skyblue",
        "Letzte 20 % des Umsatzes": "lightgreen"
    })

    ax1.bar(revenue_per_product["product_name"], revenue_per_product["total_amount"], color=colors, alpha=0.8)
    ax1.set_ylabel("Total Amount", fontsize=15)
    ax1.set_xticks(range(len(revenue_per_product["product_name"])))
    ax1.set_xticklabels(revenue_per_product["product_name"], rotation=90)

    ax2 = ax1.twinx()
    ax2.plot(revenue_per_product["product_name"], revenue_per_product["cum_share"], color="red", alpha=0.8)
    ax2.set_ylabel("Cum_share (%)", fontsize=15)

    ax2.axhline(80, color="k", linestyle="--", label="80-%-Schwelle")

    ax1.axvline(n_products_80 - 1, color="purple", linestyle="--", label=f"{n_products_80} Produkte = 80 %")

    plt.title("Patero Analysis (80/20) by products", fontsize=15, fontweight="bold")
    ax2.legend(loc="lower right")

    plt.title(f"Patero Analysis (80/20) by products\n"
              f"Count of products generating 80% of revenue: {n_products_80}",
              fontsize=14, fontweight="bold")

    plt.tight_layout()
    plt.savefig(chart_path, dpi=300, bbox_inches="tight")
    plt.close(fig)

    print(f"Tabelle gespeichert: {table_path.relative_to(ROOT)}")
    print(f"Diagramm gespeichert: {chart_path.relative_to(ROOT)}")


# Aufgabe 2_03
# [Grundlagen] Data Quality Score
# Jeden DataFrame anhand von Qualitätsmetriken bewerten:
# completeness = 1 - % missing;
# uniqueness = 1 - % Duplikate;
# validity = % Zeilen ohne Anomalien;
# consistency = % Zeilen mit korrekten Datentypen und Wertebereichen;
# overall_score = Durchschnitt der vier Metriken.
# Datei mit dem höchsten und niedrigsten DQ Score bestimmen.
def task_2_03_data_quality_score() -> None:
    print("\nAufgabe 2_03. Data Quality Score")

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
            print(f"Datei {name} unter {path} nicht gefunden.")
            continue

        df = pd.read_csv(path)
        total_rows = len(df)

        if total_rows == 0:
            continue

        # Datenvollständigkeit der Dateien prüfen
        total_cells = df.size
        missing_cells = df.isna().sum().sum()
        completeness = 1.0 - (missing_cells / total_cells) if total_cells > 0 else 1.0

        # Dateien auf Duplikate prüfen
        duplicate_rows = df.duplicated().sum()
        uniqueness = 1.0 - (duplicate_rows / total_rows)

        # Zeilen auf Anomalien und korrekte Datentypen prüfen
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
            "Vollständigkeit (%)": round(completeness * 100, 2),
            "Eindeutigkeit (%)": round(uniqueness * 100, 2),
            "Validität (%)": round(validity * 100, 2),
            "Konsistenz (%)": round(consistency * 100, 2),
            "Gesamtbewertung (%)": round(overall_score * 100, 2)
        })

    df_dq_report = pd.DataFrame(dq_results)

    print(f"\nDatenqualitätsbericht(DATA QUALITY REPORT)\n\n{df_dq_report.to_string(index=False)}")
    print("-" * 20)

    best_file = df_dq_report.loc[df_dq_report["Gesamtbewertung (%)"].idxmax()]
    worst_file = df_dq_report.loc[df_dq_report["Gesamtbewertung (%)"].idxmin()]

    print(f"\nНайвищий DQ Score: файл '{best_file['File Name']}' mit dem Wert {best_file['Gesamtbewertung (%)']}%")
    print(f"Найнижчий DQ Score: файл '{worst_file['File Name']}' mit dem Wert {worst_file['Gesamtbewertung (%)']}%")

    result_dir.mkdir(parents=True, exist_ok=True)
    table_path = result_dir / "data_quality_score.csv"
    chart_path = result_dir / "data_quality_score.png"
    df_dq_report.to_csv(table_path, index=False, encoding="utf-8-sig")

    df_melted = df_dq_report.melt(id_vars="File Name",
                                  value_vars=["Vollständigkeit (%)", "Eindeutigkeit (%)", "Validität (%)", "Konsistenz (%)"],
                                  var_name="Metric", value_name="Percentage")

    plt.figure(figsize=(10, 5))
    sns.barplot(x="File Name", y="Percentage", hue="Metric", data=df_melted, palette="viridis")

    for i, name in enumerate(df_dq_report["File Name"]):
        score = df_dq_report.loc[df_dq_report["File Name"] == name, "Gesamtbewertung (%)"].values[0]
        plt.plot([i - 0.3, i + 0.3], [score, score], color="red", linestyle="--", linewidth=1.5)
        plt.text(i, score + 2, f"{score}%")

    plt.title("Vergleichende Analyse Metriken des Data Quality Score")
    plt.xlabel("Dateiname / Datensatz")
    plt.ylabel("Qualitätskennzahl (%)")
    plt.ylim(0, 115)
    plt.legend(title="Bewertungsmetriken", bbox_to_anchor=(1.02, 1), loc="upper left")
    plt.tight_layout()
    plt.savefig(chart_path, dpi=300, bbox_inches="tight")
    plt.close()

    print(f"Tabelle gespeichert: {table_path.relative_to(ROOT)}")
    print(f"Diagramm gespeichert: {chart_path.relative_to(ROOT)}")


# Aufgabe 2_04
# In matplotlib ein gestapeltes Balkendiagramm erstellen: revenue + cost + profit pro Monat (12 Monate des Jahres 2025). plt.bar() mit dem Parameter bottom verwenden.
def task_2_04_monthly_revenue_stacked_bar() -> None:
    print("\nAufgabe 2_04. Stacked bar: revenue, cost, profit")

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

    month_names = ["Jan", "Feb", "Mär", "Apr", "Mai", "Jun", "Jul", "Aug", "Sep", "Okt", "Nov", "Dez"]

    plt.bar(months, costs, label="Kosten (Cost)", color="#fc8d62", alpha=0.85)

    plt.bar(months, profits, bottom=costs, label="Nettogewinn (Profit)", color="#66c2a5", alpha=0.85)

    plt.title("Umsatzstruktur für 2025")
    plt.xlabel("Місяць")
    plt.ylabel("Summe")

    plt.xticks(range(1, 13), month_names)

    plt.ticklabel_format(style="plain", axis="y")

    plt.grid(axis="y", linestyle="--", alpha=0.5)
    plt.legend(loc="upper left", frameon=True)

    plt.tight_layout()
    plt.savefig(chart_path, dpi=300, bbox_inches="tight")
    plt.close()

    print("Gestapeltes Balkendiagramm für 2025 erstellt.")
    print(f"Tabelle gespeichert: {table_path.relative_to(ROOT)}")
    print(f"Diagramm gespeichert: {chart_path.relative_to(ROOT)}")


# Aufgabe 2_05
# [Visualisierung] Pareto-Kurve mit 80-%-Linie
# Pareto-Kurve erstellen: kumulierter Umsatz gegenüber Produkten (Balken + Linie). Zur besseren Lesbarkeit eine gestrichelte 80-%-Linie hinzufügen.
def task_2_05_pareto_curve() -> None:
    print("\nAufgabe 2_05. Pareto-Kurve mit 80-%-Linie")

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
    ax1.bar(product_revenue["product_id"], product_revenue["revenue"], color=color_bar, alpha=0.85, label="Produktumsatz")
    ax1.set_xlabel("Produkt-ID", fontsize=12, labelpad=10)
    ax1.set_ylabel("Umsatz", color=color_bar, fontsize=12)
    ax1.tick_params(axis="y", labelcolor=color_bar)

    clean_labels = [str(int(float(x))) for x in product_revenue["product_id"]]

    ax1.set_xticks(range(len(product_revenue)))
    ax1.set_xticklabels(clean_labels, rotation=90, fontsize=5)

    ax1.yaxis.get_major_formatter().set_scientific(False)

    ax2 = ax1.twinx()
    color_line = "#c00000"
    ax2.plot(product_revenue["product_id"], product_revenue["cum_percentage"], color=color_line, marker="o", ms=4, lw=2, label="Кумулятивний %")
    ax2.set_ylabel("Kumulierter Prozentsatz", color=color_line, fontsize=12)
    ax2.tick_params(axis="y", labelcolor=color_line)
    ax2.set_ylim(0, 105)

    ax2.axhline(y=80, color="gray", linestyle="--", linewidth=1.5, label="Pareto-Grenze (80 %)")

    plt.title("Pareto-Analyse", fontsize=16, pad=20)

    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="center right", frameon=True)

    ax1.grid(True, axis="y", linestyle=":", alpha=0.6)

    plt.tight_layout()
    plt.savefig(chart_path, dpi=300, bbox_inches="tight")
    plt.close()

    print("Pareto-Kurve erstellt.")
    print(f"Tabelle gespeichert: {table_path.relative_to(ROOT)}")
    print(f"Diagramm gespeichert: {chart_path.relative_to(ROOT)}")


# Aufgabe 2_06
# 6. [Visualisierung] Dashboard (Multi-Plot):
# Dashboard (Multi-Plot): 4 Diagramme auf einer Fläche (subplots(2,2)):
# Umsatztrend (Linie)
# Gewinnmarge nach Filialformat (sns.barplot)
# Retourenquote nach Kategorie (Kreisdiagramm — plt.pie)
# Monatliche Transaktionsanzahl (sns.lineplot mit marker='o')
def task_2_06_dashboard_multi_plot() -> None:
    print("\nAufgabe 2_06. Dashboard (multi-plot)")

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
    print(f"Unknown-Anteil: {share_unknown:.1f}%")

    # Aufgrund von 5.002 Transaktionen (5 %) mit NaN bei Filialformat und ID wird das Format umbenannt
    # in 'Unknown' und es werden Ersatz-IDs vergeben

    df_clean["store_format"] = df_clean["store_format"].fillna("Unknown")
    df_clean["store_id"] = df_clean["store_id"].fillna(-1)  # Ersatz-ID

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

    # 4. Monthly transaction count (lineplot mit marker='o')

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

    print(f"Tabelle gespeichert: {revenue_trend_path.relative_to(ROOT)}")
    print(f"Tabelle gespeichert: {profit_margin_path.relative_to(ROOT)}")
    print(f"Tabelle gespeichert: {returns_rate_path.relative_to(ROOT)}")
    print(f"Tabelle gespeichert: {monthly_counts_path.relative_to(ROOT)}")
    print(f"Diagramm gespeichert: {dashboard_path.relative_to(ROOT)}")


# Aufgabe 2_07
# Aufgabe 7. Block 2.
# Zeitreihenanalyse. Aus transactions.csv:
# Nach Tagen gruppieren: sum(total_amount)
# Variablen ergänzen: dayofweek, month, is_weekend, is_holiday_season (Nov–Dez)
# 7-Tage- und 30-Tage-Gleitmittel (rolling()) berechnen und beachten, wie rolling() das Rauschen glättet.
# shift() verwenden, um Tage mit starkem Umsatzanstieg oder -rückgang gegenüber dem Vortag zu bestimmen
# (Day-over-Day-Änderung). Die 5 Tage mit dem größten Anstieg und Rückgang finden.
# Tage mit anomalem Rückgang/Anstieg (>2 Standardabweichungen vom Mittelwert) bestimmen
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
    print("\nAufgabe 2_07. Time Series Analysis")

    result_dir = ROOT / "results" / "task_2_07"

    df = group_transactions_by_day()

    if df is not None:

        print("Schritt 1: Ergebnis der Gruppierung nach Tagen")
        print(df)
        print("\n" + "=" * 50 + "\n")

        result = analyze_revenue_trends(df)

        print("Ergebnisse mit gleitenden Mittelwerten (erste 40 Tage):")
        print(result[["date", "dayofweek", "month", "total_daily_amount", "is_weekend", "is_holiday_season",
                      "rolling_7d", "rolling_30d"]].head(40))
        print("\n" + "=" * 50 + "\n")

        print("Ergebnisse mit gleitenden Mittelwerten (Ende des Zeitraums):")
        print(result[["date", "dayofweek", "month", "total_daily_amount", "is_weekend", "is_holiday_season",
                      "rolling_7d", "rolling_30d"]].tail())
        print("\n" + "=" * 50 + "\n")

        top_growth = result.nlargest(5, "dod_change")
        top_drop = result.nsmallest(5, "dod_change")

        print("Top-5-Tage mit dem größten Anstieg:")
        print(top_growth[["date", "dayofweek", "month", "total_daily_amount", "is_weekend", "is_holiday_season",
                          "dod_change"]])
        print("\n" + "=" * 50 + "\n")

        print("Top-5-Tage mit dem größten Rückgang:")
        print(top_drop[["date", "dayofweek", "month", "total_daily_amount", "is_weekend", "is_holiday_season",
                        "dod_change"]])
        print("\n" + "=" * 50 + "\n")

        print("Tage mit anomalen Änderungen (> 2 Standardabweichungen)")
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
        print(f"Tabelle gespeichert: {daily_path.relative_to(ROOT)}")
        print(f"Tabelle gespeichert: {top_growth_path.relative_to(ROOT)}")
        print(f"Tabelle gespeichert: {top_drop_path.relative_to(ROOT)}")
        print(f"Tabelle gespeichert: {anomalies_path.relative_to(ROOT)}")


# Aufgabe 2_08
# Aufgabe 8. Block 2.
# Retourenanalyse. Aus returns.csv (separate Datei mit Retourendetails) und transactions.csv (wo is_return == 1):
# Retourenquote nach Kategorie (returns / Gesamttransaktionen) — merge mit Products verwenden, um die Kategorie zu erhalten
# Durchschnittlicher Erstattungsbetrag nach Grund (return_reason aus returns.csv). Welcher Grund ist am teuersten?
# Korreliert discount_percent mit der Retourenwahrscheinlichkeit? Durchschnittlichen Rabatt für Retouren und Nicht-Retouren vergleichen
# Unterscheidet sich die Retourenquote nach payment_method?
# Wie lange dauert es durchschnittlich zwischen Kauf und Retoure (return_date - transaction_date)?
# Anzeige-Konfiguration
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
            print(f"Помилка: Datei {path} nicht gefunden!")
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
    print("\nAufgabe 2_08. Returns Analysis")

    result_dir = ROOT / "results" / "task_2_08"

    if not all(f.exists() for f in FILES.values()):
        print("Fehler: Nicht alle Dateien wurden im Ordner cleaned_data gefunden!")
        return

    transactions = pd.read_csv(FILES["transactions"])
    returns = pd.read_csv(FILES["returns"])
    products = pd.read_excel(FILES["products"], sheet_name="Products")

    result_dir.mkdir(parents=True, exist_ok=True)

    category_results = analyze_return_rate_by_category(transactions, returns, products)
    print("Retourenquote nach Kategorien")
    print(category_results)
    category_path = result_dir / "return_rate_by_category.csv"
    category_results.to_csv(category_path, encoding="utf-8-sig")
    print(f"Tabelle gespeichert: {category_path.relative_to(ROOT)}")
    print("\n" + "=" * 50 + "\n")

    reason_results = analyze_refunds_by_reason(returns)
    print("Durchschnittlicher Erstattungsbetrag nach Grund")
    print(reason_results)
    reason_path = result_dir / "average_refund_by_reason.csv"
    reason_results.to_csv(reason_path, encoding="utf-8-sig")
    print(f"Tabelle gespeichert: {reason_path.relative_to(ROOT)}")
    print("\n" + "=" * 50 + "\n")

    discount_stats, correlation = analyze_discount_vs_return(transactions)

    print("Einfluss des Rabatts auf Retouren")

    print("Durchschnittlicher discount_percent:")

    print(f"Non-returns (is_return=0): {discount_stats[0]:.2f}%")

    print(f"Returns (is_return=1): {discount_stats[1]:.2f}%")

    print(f"Korrelationskoeffizient zwischen Rabatt und Retoure: {correlation:.4f}")

    if abs(correlation) < 0.1:
        print("Fazit: Zwischen Rabatt und Retourenwahrscheinlichkeit besteht kaum ein Zusammenhang.")
    else:
        print("Fazit: Zwischen Rabatthöhe und Retouren besteht ein erkennbarer statistischer Zusammenhang.")

    discount_path = result_dir / "discount_vs_return.csv"
    pd.DataFrame(
        {
            "is_return": discount_stats.index,
            "average_discount_percent": discount_stats.values,
            "correlation": correlation,
        }
    ).to_csv(discount_path, index=False, encoding="utf-8-sig")
    print(f"Tabelle gespeichert: {discount_path.relative_to(ROOT)}")
    print("\n" + "=" * 50 + "\n")

    print("Retourenquote nach Zahlungsmethode (%)")
    payment_results = analyze_return_rate_by_payment(transactions)
    print(payment_results)
    payment_path = result_dir / "return_rate_by_payment_method.csv"
    payment_results.to_csv(payment_path, encoding="utf-8-sig")
    print(f"Tabelle gespeichert: {payment_path.relative_to(ROOT)}")
    print("\n" + "=" * 50 + "\n")

    avg_days = analyze_return_time(returns)
    print(f"Durchschnittliche Zeit zwischen Kauf und Retoure")
    print(f"Kunden retournieren Produkte durchschnittlich nach {avg_days:.1f} Tagen.")
    time_path = result_dir / "average_return_time.csv"
    pd.DataFrame(
        {
            "metric": ["average_days_to_return"],
            "value": [avg_days],
        }
    ).to_csv(time_path, index=False, encoding="utf-8-sig")
    print(f"Tabelle gespeichert: {time_path.relative_to(ROOT)}")


# Aufgabe 2_09
# [Fortgeschritten] Filialanalyse
# Filialanalyse. Aus company_data.xlsx (Stores + Employees + Inventory + transactions):
# Umsatz pro Quadratmeter (total_amount / size_sqm) nach store_format
# Umsatz pro Mitarbeiter (total_amount / Mitarbeiterzahl) nach Filiale
# Effizienteste Filiale anhand beider Kennzahlen
def task_2_09_store_analytics() -> None:
    print("\nAufgabe 2_09. Filialanalyse")

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

    # Tatsächlich aktive Mitarbeiter (Status active)
    df_employees["status"] = df_employees["status"].astype(str).str.strip().str.lower()
    df_active_emp = df_employees[df_employees["status"] == "active"]
    employee_count = df_active_emp.groupby("store_id")["employee_id"].count().reset_index()
    employee_count.columns = ["store_id", "employee_count"]

    df_analytics = df_stores.merge(store_revenue, on="store_id", how="left").fillna(0)
    df_analytics = df_analytics.merge(employee_count, on="store_id", how="left").fillna(0)

    df_analytics["store_format"] = df_analytics["store_format"].astype(str).str.strip()
    df_analytics["store_format"] = df_analytics["store_format"].replace({"Streett": "Street", "Mal": "Mall"})

    # Kennzahlen auf Filialebene
    df_analytics["revenue_per_sqm"] = df_analytics.apply(
        lambda r: r["total_revenue"] / r["size_sqm"] if str(r["store_format"]).lower() != "online" and r[
            "size_sqm"] > 0 else 0,
        axis=1
    )

    df_analytics["revenue_per_employee"] = df_analytics.apply(
        lambda r: r["total_revenue"] / r["employee_count"] if r["employee_count"] > 0 else 0,
        axis=1
    )

    # Effizienz nach Filialformat
    df_offline_only = df_analytics[df_analytics["store_format"].str.lower() != "online"]
    format_grouped = df_offline_only.groupby("store_format").agg(
        total_revenue=("total_revenue", "sum"),
        total_size=("size_sqm", "sum")
    ).reset_index()
    format_grouped["revenue_per_sqm"] = format_grouped["total_revenue"] / format_grouped["total_size"]

    # Effizienteste Filiale (Rangmethode für Offline-Filialen)
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
    print(f"Gesamtbericht der Filialen (erste 20):\n\n"
          f"{df_console[['store_id', 'store_name', 'store_format', 'size_sqm', 'employee_count', 'total_revenue', 'revenue_per_sqm', 'revenue_per_employee']].head(20).to_string(index=False)}\n")
    print("-" * 20)

    if best_store is not None:
        print(f"Effizienteste physische Filiale anhand beider Kennzahlen:\n\n",
              f"Filiale: {best_store['store_name']} (ID: {best_store['store_id']})\n",
              f"Land: {best_store['country']}. Формат: {best_store['store_format']}\n",
              f"Fläche: {best_store['size_sqm']} кв.м. Mitarbeiter: {int(best_store['employee_count'])} співробітників\n",
              f"Umsatz/кв. метр: {best_store['revenue_per_sqm']:,.2f}\n",
              f"Umsatz/одного співробітника: {best_store['revenue_per_employee']:,.2f}")
        best_store.to_frame().T.to_csv(best_store_path, index=False, encoding="utf-8-sig")
        print(f"Tabelle gespeichert: {best_store_path.relative_to(ROOT)}")

    print(f"Tabelle gespeichert: {analytics_path.relative_to(ROOT)}")
    print(f"Tabelle gespeichert: {format_path.relative_to(ROOT)}")


# Aufgabe 2_10
# 10. [Fortgeschritten] Finanzmodellierung (P&L).
# Finanzmodellierung. Eine monatliche P&L erstellen:
# - Revenue: sum(total_amount)
# - COGS: sum(quantity * cost_price)
# - Gross Profit = Revenue - COGS
# - Marketing Cost: sum(budget) aus marketing.csv nach Kampagnenmonaten
# - Salary Cost: sum(net_pay) aus salaries.parquet nach Monaten
# - Operating Profit = Gross Profit - Marketing - Salaries - 5 % Betriebskosten
# - Net Margin % = Operating Profit / Revenue * 100
def task_2_10_load_table(filename: str, sep: str = ",") -> pd.DataFrame:
    path = OUT / filename
    if not path.exists():
        raise FileNotFoundError(f"Datei {path} nicht gefunden")
    return pd.read_csv(path, low_memory=False, sep=sep)


def task_2_10_pnl_financial_modeling() -> None:
    print("\nAufgabe 2_10. P&L Financial Modeling")

    RESULT_DIR = ROOT / "results" / "task_2_10"

    transactions = task_2_10_load_table("transactions_cleaned.csv")
    products = pd.read_excel(OUT / "company_data_cleaned.xlsx", sheet_name="Products")
    marketing = task_2_10_load_table("marketing_cleaned.csv")
    salaries = task_2_10_load_table("salaries_cleaned.csv")

    # Transactions
    transactions["transaction_date"] = pd.to_datetime(transactions["transaction_date"], errors="coerce")
    transactions["month"] = transactions["transaction_date"].dt.to_period("M")

    # - Revenue: sum(total_amount). Summe von total_amount pro Monat
    revenue = transactions.groupby("month")["total_amount"].sum().reset_index(name="Revenue")

    # - COGS: sum(quantity * cost_price). Summe von quantity * cost_price pro Monat
    transactions = transactions.merge(products[["product_id", "product_name", "cost_price"]], on="product_id", how="left")
    transactions["COGS"] = transactions["quantity"] * transactions["cost_price"]
    cogs = transactions.groupby("month")["COGS"].sum().reset_index()

    # - Gross Profit = Revenue - COGS.
    pnl = revenue.merge(cogs, on="month")
    pnl["Gross Profit"] = pnl["Revenue"] - pnl["COGS"]

    # - Marketing Cost: sum(budget) aus marketing.csv nach Kampagnenmonaten

    # Präzise Variante: Budget gleichmäßig auf alle Kampagnenmonate verteilen
    marketing["start_date"] = pd.to_datetime(marketing["start_date"], errors="coerce")
    marketing["end_date"] = pd.to_datetime(marketing["end_date"], errors="coerce")

    rows = []
    for _, row in marketing.iterrows():
        if pd.notnull(row["start_date"]) and pd.notnull(row["end_date"]):
            # Liste der Monate zwischen start_date und end_date
            months = pd.period_range(row["start_date"], row["end_date"], freq="M")
            # Gleichmäßige Verteilung des Budgets
            monthly_budget = row["budget"] / len(months) if len(months) > 0 else row["budget"]
            for m in months:
                rows.append({"month": m, "Marketing Cost": monthly_budget})

    marketing_cost = pd.DataFrame(rows).groupby("month")["Marketing Cost"].sum().reset_index()

    pnl = pnl.merge(marketing_cost, on="month", how="left").fillna({"Marketing Cost": 0})

    # - Salary Cost: sum(net_pay) aus salaries.parquet nach Monaten
    # Summe von net_pay pro Monat – die vorhandene month-Spalte verwenden
    salaries["month"] = salaries["month"].astype("period[M]")
    salary_cost = salaries.groupby("month")["net_pay"].sum().reset_index(name="Salary Cost")

    pnl = pnl.merge(salary_cost, on="month", how="left").fillna({"Salary Cost": 0})

    # - Operating Profit = Gross Profit - Marketing - Salaries - 5 % Betriebskosten
    pnl["Operating Profit"] = pnl["Gross Profit"] - pnl["Marketing Cost"] - pnl["Salary Cost"] - (pnl["Revenue"] * 0.05)

    # - Net Margin % = Operating Profit / Revenue * 100
    pnl["Net Margin %"] = pnl["Operating Profit"] / pnl["Revenue"] * 100

    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    table_path = RESULT_DIR / "pnl_financial_modeling.csv"
    net_margin_chart_path = RESULT_DIR / "net_margin_by_month.png"
    revenue_profit_chart_path = RESULT_DIR / "revenue_vs_operating_profit.png"
    pnl.to_csv(table_path, index=False, encoding="utf-8-sig")

    print(pnl.head())
    print(f"Tabelle gespeichert: {table_path.relative_to(ROOT)}")

    # Net Margin % ist negativ und zeigt die Verlustsituation.
    # Fazit: Die monatliche P&L zeigt, dass Personal- und Marketingkosten deutlich höher sind als
    # der Bruttogewinn. Daher sind Operating Profit und Net Margin % negativ (z. B. −58 % im Januar).
    # Es handelt sich um Testdaten: Das Modell funktioniert korrekt, die Kennzahlen zeigen lediglich einen Verlust.

    # Diagramme zur Visualisierung:
    # Liniendiagramm der Net Margin %
    plt.figure(figsize=(10, 4))
    plt.plot(pnl["month"].astype(str), pnl["Net Margin %"], marker="o", color="red")
    plt.xticks(rotation=90)
    plt.title("Net Margin % pro Monat", fontsize=14, fontweight="bold")
    plt.xlabel("Місяць")
    plt.ylabel("Net Margin %")
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(net_margin_chart_path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"Diagramm gespeichert: {net_margin_chart_path.relative_to(ROOT)}")

    # Balkendiagramm: Revenue vs. Operating Profit
    plt.figure(figsize=(10, 5))
    width = 0.35
    x = range(len(pnl["month"]))

    plt.bar(x, pnl["Revenue"], width=width, label="Revenue", color="skyblue")
    plt.bar([i + width for i in x], pnl["Operating Profit"], width=width, label="Operating Profit", color="green")

    plt.xticks([i + width / 2 for i in x], pnl["month"].astype(str), rotation=90)
    plt.title("Revenue vs. Operating Profit pro Monat", fontsize=14, fontweight="bold")
    plt.xlabel("Місяць", fontsize=14)
    plt.ylabel("Summe")
    plt.legend()
    plt.tight_layout()
    plt.savefig(revenue_profit_chart_path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"Diagramm gespeichert: {revenue_profit_chart_path.relative_to(ROOT)}")


# Aufgabe 2_11
# [Zusatzaufgabe] Dynamisches Executive-Dashboard
# Dynamisches Executive-Dashboard. Eine Funktion generate_dashboard(data_path, month) erstellen,
# die einen Datenpfad und einen Monat (z. B. '2025-06') übernimmt und 6 Diagramme erstellt:
# - KPI cards: Revenue, Profit, Margin %, Customers Count, Avg Order Value, Return Rate
# - Zusätzlich 2 frei gewählte Diagramme (Trend, Verteilung, Pareto usw.)
# - Die Funktion muss eine PNG-Datei mit dem Namen dashboard_{month}.png speichern
# - Für drei verschiedene Monate aufrufen: '2025-01', '2025-06', '2025-12'
# - Vergleichende Analyse: Welcher Monat ist der beste und warum?
def generate_dashboard(data_path, month: str) -> dict[str, float]:
    data_path = Path(data_path)
    result_dir = ROOT / "results" / "task_2_11"
    result_dir.mkdir(parents=True, exist_ok=True)

    transactions = pd.read_csv(data_path / "transactions_cleaned.csv", low_memory=False)
    products = pd.read_excel(data_path / "company_data_cleaned.xlsx", sheet_name="Products")

    transactions["transaction_date"] = pd.to_datetime(transactions["transaction_date"], errors="coerce")
    transactions["month"] = transactions["transaction_date"].dt.to_period("M").astype(str)
    transactions["day"] = transactions["transaction_date"].dt.date

    df = transactions[transactions["month"] == month].copy()
    if df.empty:
        raise ValueError(f"Keine Daten für den Monat {month}")

    products_small = products[["product_id", "category", "cost_price"]].copy()
    products_small["cost_price"] = pd.to_numeric(products_small["cost_price"], errors="coerce").fillna(0)
    df = df.merge(products_small, on="product_id", how="left")

    df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce").fillna(0)
    df["total_amount"] = pd.to_numeric(df["total_amount"], errors="coerce").fillna(0)
    df["is_return"] = pd.to_numeric(df["is_return"], errors="coerce").fillna(0)

    sales = df[df["is_return"] == 0].copy()
    revenue = sales["total_amount"].sum()
    cost = (sales["quantity"] * sales["cost_price"]).sum()
    profit = revenue - cost
    margin = profit / revenue * 100 if revenue != 0 else 0
    customers_count = sales["customer_id"].nunique()
    avg_order_value = revenue / len(sales) if len(sales) > 0 else 0
    return_rate = df["is_return"].mean() * 100

    daily_revenue = sales.groupby("day")["total_amount"].sum().reset_index()
    category_revenue = (
        sales.groupby("category")["total_amount"]
        .sum()
        .sort_values(ascending=False)
        .head(8)
        .reset_index()
    )

    kpis = [
        ("Revenue", revenue, "{:,.2f}"),
        ("Profit", profit, "{:,.2f}"),
        ("Margin %", margin, "{:.2f}%"),
        ("Customers Count", customers_count, "{:,.0f}"),
        ("Avg Order Value", avg_order_value, "{:,.2f}"),
        ("Return Rate", return_rate, "{:.2f}%"),
    ]

    fig = plt.figure(figsize=(18, 11))
    grid = fig.add_gridspec(3, 4)
    fig.suptitle(f"Executive Dashboard - {month}", fontsize=18, fontweight="bold")

    for i, (title, value, template) in enumerate(kpis):
        ax = fig.add_subplot(grid[i // 3, i % 3])
        ax.set_facecolor("#f5f5f5")
        ax.text(0.5, 0.62, template.format(value), ha="center", va="center", fontsize=20, fontweight="bold")
        ax.text(0.5, 0.28, title, ha="center", va="center", fontsize=11)
        ax.set_xticks([])
        ax.set_yticks([])
        for spine in ax.spines.values():
            spine.set_visible(False)

    ax_info = fig.add_subplot(grid[0:2, 3])
    ax_info.axis("off")
    ax_info.text(
        0.02,
        0.85,
        f"Transactions: {len(df):,}\n"
        f"Sales: {len(sales):,}\n"
        f"Returns: {int(df['is_return'].sum()):,}\n"
        f"Categories: {sales['category'].nunique():,}",
        fontsize=13,
        va="top",
    )

    ax_trend = fig.add_subplot(grid[2, 0:2])
    ax_trend.plot(daily_revenue["day"], daily_revenue["total_amount"], marker="o", color="#4f81bd")
    ax_trend.set_title("Daily Revenue Trend")
    ax_trend.set_xlabel("Day")
    ax_trend.set_ylabel("Revenue")
    ax_trend.tick_params(axis="x", rotation=45)
    ax_trend.grid(True, alpha=0.3)

    ax_category = fig.add_subplot(grid[2, 2:4])
    sns.barplot(data=category_revenue, x="total_amount", y="category", ax=ax_category, color="#66c2a5")
    ax_category.set_title("Revenue by Category")
    ax_category.set_xlabel("Revenue")
    ax_category.set_ylabel("Category")

    plt.tight_layout()
    dashboard_path = result_dir / f"dashboard_{month}.png"
    plt.savefig(dashboard_path, dpi=300, bbox_inches="tight")
    plt.close(fig)

    print(f"Diagramm gespeichert: {dashboard_path.relative_to(ROOT)}")

    return {
        "month": month,
        "revenue": revenue,
        "profit": profit,
        "margin_percent": margin,
        "customers_count": customers_count,
        "avg_order_value": avg_order_value,
        "return_rate": return_rate,
    }


def task_2_11_dynamic_executive_dashboard() -> None:
    print("\nAufgabe 2_11. Dynamisches Executive-Dashboard")

    result_dir = ROOT / "results" / "task_2_11"
    months = ["2025-01", "2025-06", "2025-12"]

    comparison = []
    for month in months:
        comparison.append(generate_dashboard(OUT, month))

    comparison_df = pd.DataFrame(comparison)
    comparison_path = result_dir / "dashboard_month_comparison.csv"
    comparison_df.to_csv(comparison_path, index=False, encoding="utf-8-sig")

    best_month = comparison_df.sort_values(
        by=["profit", "margin_percent", "revenue"],
        ascending=False,
    ).iloc[0]

    print("\nVergleichende Analyse")
    print(comparison_df.round(2).to_string(index=False))
    print(
        f"Bester Monat: {best_month['month']}. "
        f"Grund: höchster Gewinn = {best_month['profit']:.2f}, "
        f"margin = {best_month['margin_percent']:.2f}%, "
        f"revenue = {best_month['revenue']:.2f}, "
        f"return rate = {best_month['return_rate']:.2f}%."
    )
    print(f"Tabelle gespeichert: {comparison_path.relative_to(ROOT)}")


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
    task_2_11_dynamic_executive_dashboard()


if __name__ == "__main__":
    main()



