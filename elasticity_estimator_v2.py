import pandas as pd
import numpy as np
import statsmodels.api as sm
from sklearn.linear_model import RidgeCV
from db_setup import get_engine
from simulation_engine import simulate_financials, find_optimal_prices
from constrained_optimizer import find_constrained_optimal_price

def estimate_elasticities(df):
    results = []
    
    sku_counts = df['sku'].value_counts()
    valid_skus = sku_counts[sku_counts >= 10].index
    
    if 'Season_Spring' not in df.columns:
        df_season = pd.get_dummies(df['season'], prefix='Season', drop_first=False)
        df = pd.concat([df, df_season], axis=1)
        for s in ['Season_Spring', 'Season_Summer', 'Season_Autumn', 'Season_Winter']:
            if s not in df.columns:
                df[s] = 0
    
    for sku in valid_skus:
        sku_data = df[df['sku'] == sku].copy()
        
        price_std = sku_data['unit_price'].std()
        price_mean = sku_data['unit_price'].mean()
        if price_mean == 0 or pd.isna(price_std) or (price_std / price_mean) < 0.02:
            continue
            
        sku_data['log_Q'] = np.log(sku_data['quantity'])
        sku_data['log_P'] = np.log(sku_data['unit_price'])
        
        season_cols = [c for c in ['Season_Spring', 'Season_Summer', 'Season_Winter'] if c in sku_data.columns]
        features = ['log_P', 'promo_flag'] + season_cols
        
        X = sku_data[features].astype(float)
        X.columns = [str(c) for c in X.columns]
        X_with_const = sm.add_constant(X)
        X_with_const.columns = [str(c) for c in X_with_const.columns]
        y = sku_data['log_Q'].astype(float)
        
        try:
            # 1. OLS
            model_ols = sm.OLS(y, X_with_const).fit()
            if 'log_P' not in model_ols.params:
                continue
                
            elasticity_ols = model_ols.params['log_P']
            ci = model_ols.conf_int().loc['log_P']
            r_squared_ols = model_ols.rsquared
            
            ci_width = ci[1] - ci[0]
            reliable = True
            if elasticity_ols > 0 or ci_width > 5 or model_ols.pvalues['log_P'] > 0.20:
                reliable = False
                
            # 2. RidgeCV
            alphas = [0.1, 1.0, 10.0, 100.0]
            model_ridge = RidgeCV(alphas=alphas, cv=5)
            model_ridge.fit(X, y)
            
            log_p_idx = list(X.columns).index('log_P')
            elasticity_ridge = model_ridge.coef_[log_p_idx]
            r_squared_ridge = model_ridge.score(X, y)
            alpha_selected = model_ridge.alpha_
            
            # Divergence flag
            diff = abs(elasticity_ols - elasticity_ridge)
            divergence_flag = int((diff / abs(elasticity_ols)) > 0.30 if elasticity_ols != 0 else False)
            
            latest = sku_data.sort_values('week_start_date').tail(4)
            current_price = latest['unit_price'].mean()
            current_vol = latest['quantity'].mean()
            unit_cost = latest['cost'].mean()
            
            if reliable:
                sim_df = simulate_financials(current_vol, current_price, unit_cost, elasticity_ols)
                opts = find_optimal_prices(sim_df)
                rev_optimal_price = opts['Revenue_Max_Price']
                rev_upside = opts['Max_Revenue'] - (current_price * current_vol)
                margin_optimal_price = opts['Margin_Max_Price']
                margin_upside = opts['Max_Margin'] - (current_vol * (current_price - unit_cost))
                
                # Constrained Optimizer
                constrained_opt_price, _ = find_constrained_optimal_price(
                    current_vol, current_price, unit_cost, elasticity_ols, min_margin_pct=0.30
                )
            else:
                rev_optimal_price = current_price
                rev_upside = 0.0
                margin_optimal_price = current_price
                margin_upside = 0.0
                constrained_opt_price = current_price
                
            description = sku_data['description'].iloc[0] if 'description' in sku_data.columns else f"Product_{sku}"

            results.append({
                'sku': sku,
                'description': description,
                'elasticity': elasticity_ols, # Keep default elasticity name for backwards compatibility
                'elasticity_ols': elasticity_ols,
                'elasticity_ridge': elasticity_ridge,
                'ci_lower': ci[0], # Default for queries.sql
                'ci_upper': ci[1],
                'ci_lower_ols': ci[0],
                'ci_upper_ols': ci[1],
                'r_squared': r_squared_ols,
                'r_squared_ols': r_squared_ols,
                'r_squared_ridge': r_squared_ridge,
                'alpha_selected': alpha_selected,
                'divergence_flag': divergence_flag,
                'reliability_flag': int(reliable),
                'current_price': current_price,
                'current_volume': current_vol,
                'unit_cost': unit_cost,
                'rev_optimal_price': rev_optimal_price,
                'margin_optimal_price': margin_optimal_price,
                'constrained_optimal_price': constrained_opt_price,
                'rev_upside': rev_upside,
                'margin_upside': margin_upside
            })
        except Exception as e:
            print(f"Skipping {sku} due to fit error: {e}")
            pass
            
    return pd.DataFrame(results)

if __name__ == "__main__":
    print("Connecting to SQLite database to read sku_weekly_sales...")
    engine = get_engine()
    df = pd.read_sql_table('sku_weekly_sales', con=engine)
    print("Estimating OLS & Ridge elasticities...")
    results = estimate_elasticities(df)
    
    if not results.empty:
        results.to_sql('elasticity_results', con=engine, if_exists='replace', index=False)
        print("Elasticity estimation complete. Saved to 'elasticity_results' table in SQLite.")
    else:
        print("No valid results computed.")
