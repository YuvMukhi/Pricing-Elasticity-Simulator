import pandas as pd
import numpy as np
import statsmodels.api as sm
from db_setup import get_engine

def find_best_pairs(df, num_pairs=3):
    """
    Finds pairs of SKUs with the most overlapping sales weeks.
    Since we lack explicit categories, overlap count is a proxy for statistical viability.
    """
    presence = df.pivot(index='sku', columns='week_start_date', values='quantity').notna()
    
    overlap = presence.astype(int).dot(presence.astype(int).T)
    np.fill_diagonal(overlap.values, 0)
    
    stacked = overlap.stack()
    stacked = stacked[stacked.index.get_level_values(0) < stacked.index.get_level_values(1)]
    top_pairs = stacked.sort_values(ascending=False).head(num_pairs)
    
    return [(idx[0], idx[1], val) for idx, val in top_pairs.items()]

def estimate_cross_price_elasticity():
    engine = get_engine()
    df = pd.read_sql_table('sku_weekly_sales', engine)
    
    pairs = find_best_pairs(df, 3)
    results = []
    
    for sku_A, sku_B, overlap_weeks in pairs:
        # We model Demand(A) based on Price(A) and Price(B)
        df_A = df[df['sku'] == sku_A][['week_start_date', 'quantity', 'unit_price', 'promo_flag']]
        df_B = df[df['sku'] == sku_B][['week_start_date', 'unit_price']]
        
        merged = pd.merge(df_A, df_B, on='week_start_date', suffixes=('_A', '_B'))
        
        if len(merged) < 10:
            continue
            
        merged['log_Q_A'] = np.log(merged['quantity'])
        merged['log_P_A'] = np.log(merged['unit_price_A'])
        merged['log_P_B'] = np.log(merged['unit_price_B'])
        
        X = merged[['log_P_A', 'log_P_B', 'promo_flag']].astype(float)
        X = sm.add_constant(X)
        y = merged['log_Q_A'].astype(float)
        
        try:
            model = sm.OLS(y, X).fit()
            
            if 'log_P_B' in model.params:
                cross_elasticity = model.params['log_P_B']
                p_value = model.pvalues['log_P_B']
                
                if p_value < 0.15: # slightly relaxed for synthetic data
                    classification = 'Substitute' if cross_elasticity > 0 else 'Complement'
                else:
                    classification = 'Insignificant'
                    
                results.append({
                    'sku_A': sku_A,
                    'sku_B': sku_B,
                    'overlap_weeks': overlap_weeks,
                    'own_elasticity_A': model.params['log_P_A'],
                    'cross_elasticity_B': cross_elasticity,
                    'cross_p_value': p_value,
                    'classification': classification
                })
        except Exception as e:
            print(f"Error fitting pair {sku_A} and {sku_B}: {e}")
            
    results_df = pd.DataFrame(results)
    print("\n--- Cross-Price Elasticity Results ---")
    print(results_df)
    
    results_df.to_sql('cross_price_elasticity', engine, if_exists='replace', index=False)
    print("Saved to 'cross_price_elasticity' table.")
    
if __name__ == "__main__":
    estimate_cross_price_elasticity()
