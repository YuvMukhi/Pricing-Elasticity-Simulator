import pytest
import pandas as pd
from db_setup import get_engine
from query_runner import run_query, QUERIES
from sqlalchemy import inspect

def test_db_connection():
    engine = get_engine()
    insp = inspect(engine)
    tables = insp.get_table_names()
    assert 'sku_weekly_sales' in tables
    assert 'elasticity_results' in tables

def test_sku_sales_schema():
    engine = get_engine()
    df = pd.read_sql_table('sku_weekly_sales', engine)
    assert not df.empty
    expected_cols = {'sku', 'week_start_date', 'quantity', 'unit_price', 'cost', 'promo_flag', 'season', 'revenue', 'margin'}
    assert expected_cols.issubset(set(df.columns))

def test_elasticity_results_schema():
    engine = get_engine()
    df = pd.read_sql_table('elasticity_results', engine)
    assert not df.empty
    expected_cols = {'sku', 'elasticity', 'ci_lower', 'ci_upper', 'r_squared', 'reliability_flag', 'current_price', 'rev_optimal_price'}
    assert expected_cols.issubset(set(df.columns))

def test_all_named_queries():
    for name in QUERIES.keys():
        df = run_query(name)
        assert isinstance(df, pd.DataFrame)
        if name == 'top_revenue_upside':
            assert not df.empty
