import pandas as pd
import numpy as np
import statsmodels.api as sm

def estimate_elasticities(df):
    """
    Estimates price elasticity per SKU using a log-log regression.
    Equation: log(Q) = b0 + b1*log(P) + b2*Promo + seasons
    """
    results = []
    
    sku_counts = df['StockCode'].value_counts()
    # Require at least 10 weeks of data
    valid_skus = sku_counts[sku_counts >= 10].index
    
    for sku in valid_skus:
        sku_data = df[df['StockCode'] == sku].copy()
        
        # Check price variation (CV > 2%)
        price_std = sku_data['UnitPrice'].std()
        price_mean = sku_data['UnitPrice'].mean()
        if price_mean == 0 or pd.isna(price_std) or (price_std / price_mean) < 0.02:
            print(f"Skipping {sku}: Insufficient price variation (std: {price_std}, mean: {price_mean})")
            continue
            
        sku_data['log_Q'] = np.log(sku_data['Quantity'])
        sku_data['log_P'] = np.log(sku_data['UnitPrice'])
        
        # Use available season columns
        season_cols = [c for c in ['Season_Spring', 'Season_Summer', 'Season_Winter'] if c in sku_data.columns]
        features = ['log_P', 'Promo'] + season_cols
        
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
            
            # Analytical judgment: Flag if elasticity is positive (Giffen/Veblen behavior or noise),
            # or if the confidence interval is implausibly wide.
            if elasticity > 0 or ci_width > 5 or p_value > 0.20:
                reliable = False
                
            results.append({
                'StockCode': sku,
                'Description': sku_data['Description'].iloc[0],
                'Elasticity': elasticity,
                'CI_Lower': ci[0],
                'CI_Upper': ci[1],
                'P_Value': p_value,
                'R_Squared': r_squared,
                'Reliable': reliable,
                'Data_Points': len(sku_data)
            })
        except Exception as e:
            print(f"Skipping {sku} due to fit error: {e}")
            pass
            
    if not results:
        print("Warning: No SKUs were successfully processed.")
        return pd.DataFrame(columns=['StockCode', 'Elasticity', 'Reliable'])
        
    results_df = pd.DataFrame(results)
    return results_df

if __name__ == "__main__":
    print("Loading processed_data.csv...")
    try:
        df = pd.read_csv("processed_data.csv")
        print("Estimating elasticities...")
        results = estimate_elasticities(df)
        results.to_csv("elasticity_results.csv", index=False)
        print("Elasticity estimation complete. Results saved to elasticity_results.csv.")
        print(f"Total SKUs processed: {len(results)}")
        if 'Reliable' in results.columns:
            print(f"Reliable SKUs: {results['Reliable'].sum()}")
        print(results.head())
    except FileNotFoundError:
        print("processed_data.csv not found. Please run data_loader.py first.")
