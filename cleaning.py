from __future__ import annotations

import csv
import json
import re
import shutil
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd


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
    log_id = pd.to_numeric(df["log_id"], errors="coerce").round().astype("Int64")
    df["log_id"] = log_id.where(log_id.gt(0))
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


def main() -> None:
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


if __name__ == "__main__":
    main()
