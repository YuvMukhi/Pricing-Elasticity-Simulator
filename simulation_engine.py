import pandas as pd
import numpy as np

def simulate_demand(current_volume, current_price, price_change_pct, elasticity):
    """
    Standard approximation: % change in Q = Elasticity * % change in P.
    Q_new = Q_old * (1 + Elasticity * price_change_pct)
    """
    new_volume = current_volume * (1 + elasticity * price_change_pct)
    return max(0, new_volume)

def simulate_financials(current_volume, current_price, unit_cost, elasticity, price_changes=None):
    """
    Simulates revenue and margin over a range of price changes.
    """
    if price_changes is None:
        price_changes = np.arange(-0.20, 0.25, 0.05)
        
    results = []
    for dp in price_changes:
        new_price = current_price * (1 + dp)
        new_volume = simulate_demand(current_volume, current_price, dp, elasticity)
        new_revenue = new_volume * new_price
        new_margin = new_volume * (new_price - unit_cost)
        
        results.append({
            'Price_Change_Pct': dp,
            'New_Price': new_price,
            'New_Volume': new_volume,
            'New_Revenue': new_revenue,
            'New_Margin': new_margin
        })
        
    return pd.DataFrame(results)

def find_optimal_prices(simulation_df):
    """
    Finds the price change that maximizes revenue and the one that maximizes margin.
    """
    opt_revenue = simulation_df.loc[simulation_df['New_Revenue'].idxmax()]
    opt_margin = simulation_df.loc[simulation_df['New_Margin'].idxmax()]
    
    return {
        'Revenue_Max_Price': opt_revenue['New_Price'],
        'Revenue_Max_Change': opt_revenue['Price_Change_Pct'],
        'Margin_Max_Price': opt_margin['New_Price'],
        'Margin_Max_Change': opt_margin['Price_Change_Pct'],
        'Max_Revenue': opt_revenue['New_Revenue'],
        'Max_Margin': opt_margin['New_Margin']
    }
