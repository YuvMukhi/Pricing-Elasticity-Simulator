import pandas as pd
import numpy as np
import statsmodels.api as sm
from db_setup import get_engine
from simulation_engine import simulate_financials, find_optimal_prices

def estimate_elasticities(df):
    """
    Estimates price elasticity per SKU using a log-log regression.
    Reads from SQLite 'sku_weekly_sales' format.
    """
    results = []
    
    sku_counts = df['sku'].value_counts()
    valid_skus = sku_counts[sku_counts >= 10].index
    
    # Re-create dummies for regression if not present
    if 'Season_Spring' not in df.columns:
        # Create dummies on the fly
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
            print(f"Skipping {sku}: Insufficient price variation")
            continue
            
        sku_data['log_Q'] = np.log(sku_data['quantity'])
        sku_data['log_P'] = np.log(sku_data['unit_price'])
        
        season_cols = [c for c in ['Season_Spring', 'Season_Summer', 'Season_Winter'] if c in sku_data.columns]
        features = ['log_P', 'promo_flag'] + season_cols
        
        X = sku_data[features].astype(float)
        X = sm.add_constant(X)
        y = sku_data['log_Q'].astype(float)
        
        try:
            model = sm.OLS(y, X).fit()
            
            if 'log_P' not in model.params:
                continue
                
            elasticity = model.params['log_P']
            ci = model.conf_int().loc['log_P']
            p_value = model.pvalues['log_P']
            r_squared = model.rsquared
            
            ci_width = ci[1] - ci[0]
            reliable = True
            
            if elasticity > 0 or ci_width > 5 or p_value > 0.20:
                reliable = False
                
            # Current KPIs
            latest = sku_data.sort_values('week_start_date').tail(4)
            current_price = latest['unit_price'].mean()
            current_vol = latest['quantity'].mean()
            unit_cost = latest['cost'].mean()
            
            # Simulate optimal prices
            if reliable:
                sim_df = simulate_financials(current_vol, current_price, unit_cost, elasticity)
                opts = find_optimal_prices(sim_df)
                rev_optimal_price = opts['Revenue_Max_Price']
                rev_upside = opts['Max_Revenue'] - (current_price * current_vol)
                margin_optimal_price = opts['Margin_Max_Price']
                margin_upside = opts['Max_Margin'] - (current_vol * (current_price - unit_cost))
            else:
                rev_optimal_price = current_price
                rev_upside = 0.0
                margin_optimal_price = current_price
                margin_upside = 0.0
                
            # Use 'description' from df if available, else placeholder
            description = sku_data['description'].iloc[0] if 'description' in sku_data.columns else f"Product_{sku}"

            results.append({
                'sku': sku,
                'description': description,
                'elasticity': elasticity,
                'ci_lower': ci[0],
                'ci_upper': ci[1],
                'p_value': p_value,
                'r_squared': r_squared,
                'reliability_flag': int(reliable),
                'current_price': current_price,
                'current_volume': current_vol,
                'unit_cost': unit_cost,
                'rev_optimal_price': rev_optimal_price,
                'rev_upside': rev_upside,
                'margin_optimal_price': margin_optimal_price,
                'margin_upside': margin_upside
            })
        except Exception as e:
            print(f"Skipping {sku} due to fit error: {e}")
            pass
            
    if not results:
        print("Warning: No SKUs were successfully processed.")
        return pd.DataFrame(columns=['sku', 'elasticity', 'reliability_flag'])
        
    return pd.DataFrame(results)

if __name__ == "__main__":
    print("Connecting to SQLite database to read sku_weekly_sales...")
    engine = get_engine()
    try:
        df = pd.read_sql_table('sku_weekly_sales', con=engine)
        print("Estimating elasticities and simulating optimals...")
        results = estimate_elasticities(df)
        
        results.to_sql('elasticity_results', con=engine, if_exists='replace', index=False)
        print("Elasticity estimation complete. Saved to 'elasticity_results' table in SQLite.")
        
        print(f"Total SKUs processed: {len(results)}")
        if 'reliability_flag' in results.columns:
            print(f"Reliable SKUs: {results['reliability_flag'].sum()}")
    except Exception as e:
        print(f"Error during elasticity estimation: {e}")
