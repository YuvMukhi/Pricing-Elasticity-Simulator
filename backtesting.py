import pandas as pd
import numpy as np
import statsmodels.api as sm
from db_setup import get_engine

def run_backtest(holdout_weeks=4, mape_threshold=0.35):
    engine = get_engine()
    
    df_sales = pd.read_sql_query("SELECT * FROM sku_weekly_sales", engine)
    df_results = pd.read_sql_query("SELECT sku FROM elasticity_results WHERE reliability_flag = 1", engine)
    
    reliable_skus = df_results['sku'].tolist()
    
    if 'Season_Spring' not in df_sales.columns:
        df_season = pd.get_dummies(df_sales['season'], prefix='Season', drop_first=False)
        df_sales = pd.concat([df_sales, df_season], axis=1)
        for s in ['Season_Spring', 'Season_Summer', 'Season_Autumn', 'Season_Winter']:
            if s not in df_sales.columns:
                df_sales[s] = 0
                
    backtest_results = []
    
    for sku in reliable_skus:
        sku_data = df_sales[df_sales['sku'] == sku].sort_values('week_start_date').copy()
        
        if len(sku_data) <= holdout_weeks + 5:
            continue
            
        train = sku_data.iloc[:-holdout_weeks].copy()
        test = sku_data.iloc[-holdout_weeks:].copy()
        
        train['log_Q'] = np.log(train['quantity'])
        train['log_P'] = np.log(train['unit_price'])
        
        season_cols = [c for c in ['Season_Spring', 'Season_Summer', 'Season_Winter'] if c in train.columns]
        features = ['log_P', 'promo_flag'] + season_cols
        
        X_train = train[features].astype(float)
        X_train.columns = [str(c) for c in X_train.columns]
        X_train = sm.add_constant(X_train)
        X_train.columns = [str(c) for c in X_train.columns]
        y_train = train['log_Q'].astype(float)
        
        try:
            model = sm.OLS(y_train, X_train).fit()
            
            test['log_P'] = np.log(test['unit_price'])
            X_test = test[features].astype(float)
            X_test.columns = [str(c) for c in X_test.columns]
            X_test = sm.add_constant(X_test, has_constant='add')
            
            for col in X_train.columns:
                if col not in X_test.columns:
                    X_test[col] = 1.0 if col == 'const' else 0.0
            X_test = X_test[X_train.columns]
            
            pred_log_Q = model.predict(X_test)
            pred_Q = np.exp(pred_log_Q)
            actual_Q = test['quantity'].values
            
            errors = pred_Q - actual_Q
            rmse = np.sqrt(np.mean(errors**2))
            mape = np.mean(np.abs(errors / actual_Q))
            
            high_error = 1 if mape > mape_threshold else 0
            
            backtest_results.append({
                'sku': sku,
                'rmse': rmse,
                'mape': mape,
                'high_backtest_error': high_error
            })
            
        except Exception as e:
            print(f"Error backtesting SKU {sku}: {e}")
            
    res_df = pd.DataFrame(backtest_results)
    
    if not res_df.empty:
        avg_rmse = res_df['rmse'].mean()
        avg_mape = res_df['mape'].mean()
        high_error_count = res_df['high_backtest_error'].sum()
        
        print("\n--- Backtest Results ---")
        print(f"SKUs tested: {len(res_df)}")
        print(f"Average RMSE: {avg_rmse:.2f}")
        print(f"Average MAPE: {avg_mape:.2%}")
        print(f"SKUs with High Error (> {mape_threshold*100}%): {high_error_count}")
        
        res_df.to_sql('backtest_results', engine, if_exists='replace', index=False)
        print("Saved to 'backtest_results' table.")
    else:
        print("No backtest results generated.")

if __name__ == "__main__":
    run_backtest()
