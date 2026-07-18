import pandas as pd
from scipy import stats

def analyze_promo_significance(sku_data):
    """
    Analyzes the statistical significance of promotional lift using a two-sample t-test.
    Expects a DataFrame with 'quantity' and 'promo_flag' columns.
    """
    if 'promo_flag' not in sku_data.columns or 'quantity' not in sku_data.columns:
        raise ValueError("DataFrame must contain 'promo_flag' and 'quantity'")
        
    promo_data = sku_data[sku_data['promo_flag'] == 1]['quantity']
    base_data = sku_data[sku_data['promo_flag'] == 0]['quantity']
    
    if len(promo_data) < 2 or len(base_data) < 2:
        return {
            'base_volume': base_data.mean() if len(base_data) > 0 else 0,
            'promo_volume': promo_data.mean() if len(promo_data) > 0 else 0,
            'lift_pct': 0.0,
            't_stat': 0.0,
            'p_value': 1.0,
            'significant': False
        }
        
    base_mean = base_data.mean()
    promo_mean = promo_data.mean()
    
    lift_pct = ((promo_mean - base_mean) / base_mean) if base_mean > 0 else 0
    
    # Welch's t-test (unequal variances)
    t_stat, p_value = stats.ttest_ind(promo_data, base_data, equal_var=False)
    
    return {
        'base_volume': base_mean,
        'promo_volume': promo_mean,
        'lift_pct': lift_pct,
        't_stat': t_stat,
        'p_value': p_value,
        'significant': bool(p_value < 0.05)
    }
