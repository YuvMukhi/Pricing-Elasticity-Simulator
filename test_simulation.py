import pytest
import pandas as pd
from simulation_engine import simulate_demand, simulate_financials, find_optimal_prices

def test_simulate_demand_zero_change():
    q = simulate_demand(100, 10, 0.0, -1.5)
    assert q == 100

def test_simulate_demand_negative_elasticity():
    q = simulate_demand(100, 10, 0.10, -1.5)
    assert q == 85.0

def test_simulate_financials():
    df = simulate_financials(100, 10, 6, -2.0, price_changes=[-0.10, 0.0, 0.10])
    assert len(df) == 3
    base = df[df['Price_Change_Pct'] == 0.0].iloc[0]
    assert base['New_Revenue'] == 1000
    assert base['New_Margin'] == 400

def test_find_optimal_prices():
    df = simulate_financials(100, 10, 6, -3.0)
    opts = find_optimal_prices(df)
    assert opts['Revenue_Max_Change'] < 0
