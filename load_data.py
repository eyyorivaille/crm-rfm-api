import os

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, "data", "online_retail_II.xlsx")

engine = create_engine(
    f"postgresql+psycopg2://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
    f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
)

sheets = pd.read_excel(DATA_PATH, sheet_name=None)
df = pd.concat(sheets.values(), ignore_index=True)

df = df.rename(columns={
    "Invoice": "invoice_id",
    "StockCode": "stock_code",
    "Description": "description",
    "Quantity": "quantity",
    "InvoiceDate": "invoice_date",
    "Price": "unit_price",
    "Customer ID": "customer_id",
    "Country": "country",
})

df = df.dropna(subset=["customer_id"])
df["customer_id"] = df["customer_id"].astype(int).astype(str)

customers = (
    df[["customer_id", "country"]]
    .drop_duplicates(subset="customer_id")
)
customers.to_sql("customers", engine, if_exists="append", index=False, method="multi", chunksize=5000)
print(f"customers tablosuna {len(customers)} satır yazıldı")

transactions = df[[
    "invoice_id", "customer_id", "stock_code", "description",
    "quantity", "invoice_date", "unit_price",
]]
transactions.to_sql("transactions", engine, if_exists="append", index=False, method="multi", chunksize=5000)
print(f"transactions tablosuna {len(transactions)} satır yazıldı")
