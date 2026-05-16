"""
Run this script once to load the CSV datasets into the shared SQLite database.

    python data/load_datasets.py

Tables added to app/services/database/database.db:
  - transactions  (fraud_dataset.csv)
  - customers     (product_purchase_dataset.csv)
"""

import os
import sys
import pandas as pd
from sqlalchemy import text

# Make sure the project root is on the path when running this script directly
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

# Reuse the shared engine so everything lands in the same database.db
from app.services.database.database import sqlite_engine

DATA_DIR = os.path.dirname(os.path.abspath(__file__))

DATASETS = {
    "transactions": os.path.join(DATA_DIR, "fraud_dataset.csv"),
    "customers": os.path.join(DATA_DIR, "product_purchase_dataset.csv"),
}


def load_datasets():
    for table_name, csv_path in DATASETS.items():
        df = pd.read_csv(csv_path)
        df.to_sql(table_name, sqlite_engine, index=False, if_exists="replace")
        print(f"  Loaded '{table_name}': {len(df)} rows from {os.path.basename(csv_path)}")

    with sqlite_engine.connect() as conn:
        for table in DATASETS:
            count = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
            print(f"  {table}: {count} rows")

    print(f"\nDatabase ready at: {sqlite_engine.url}")


if __name__ == "__main__":
    load_datasets()
