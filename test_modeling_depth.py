import pytest
import numpy as np
import pandas as pd
from constrained_optimizer import find_constrained_optimal_price

def test_constrained_optimizer_margin_floor():
    current_vol = 100
    current_price = 10.0
    unit_cost = 7.0 # Initial margin is 30%
    elasticity = -2.5
    
    # Require 40% margin
    price, _ = find_constrained_optimal_price(
        current_vol, current_price, unit_cost, elasticity, min_margin_pct=0.40
    )
    
    margin_pct = (price - unit_cost) / price
    assert margin_pct >= 0.399 # Floor logic holds
    assert price >= 11.66
