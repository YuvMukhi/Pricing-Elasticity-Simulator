import os
import pandas as pd
from sqlalchemy import create_engine

DB_PATH = 'sqlite:///pricing_simulator.db'

def get_engine():
    """Returns a SQLAlchemy engine for the local SQLite database."""
    return create_engine(DB_PATH)

if __name__ == "__main__":
    print("Database setup module.")
