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

from constrained_optimizer import find_constrained_optimal_price

def test_constrained_optimal_price():
    current_vol = 100
    current_price = 10.0
    unit_cost = 8.0
    elasticity = -2.5
    constrained_price, _ = find_constrained_optimal_price(current_vol, current_price, unit_cost, elasticity, min_margin_pct=0.30)
    margin_pct = (constrained_price - unit_cost) / constrained_price
    assert margin_pct >= 0.299
    assert constrained_price > current_price


from promo_effectiveness import analyze_promo_significance
import pandas as pd

def test_analyze_promo_significance():
    df = pd.DataFrame({'quantity': [10, 12, 11, 20, 22, 21], 'promo_flag': [0, 0, 0, 1, 1, 1]})
    stats = analyze_promo_significance(df)
    assert stats['base_volume'] == 11.0
    assert stats['promo_volume'] == 21.0
    assert stats['lift_pct'] > 0.9
    assert stats['significant'] == True

