import pandas as pd
import numpy as np
import requests
import io
import os

def load_or_generate_data(file_path='online_retail.csv'):
    """Loads existing data, downloads from public URL, or generates synthetic dataset if offline."""
    if os.path.exists(file_path):
        print(f"Loading data from {file_path}")
        return pd.read_csv(file_path)
    
    url = "https://raw.githubusercontent.com/datagy/data/main/Online%20Retail.csv"
    try:
        print(f"Attempting to download data from {url}...")
        response = requests.get(url, timeout=15)
        if response.status_code == 200:
            print("Download successful. Saving to file.")
            df = pd.read_csv(io.StringIO(response.text))
            df.to_csv(file_path, index=False)
            return df
        else:
            print(f"Download returned status code {response.status_code}.")
    except Exception as e:
        print(f"Download failed: {e}. Generating synthetic data instead.")
    
    # Generate synthetic data if download fails
    print("Generating synthetic retail data...")
    np.random.seed(42)
    dates = pd.date_range(start='2022-01-01', end='2023-12-31', freq='h')
    n_records = 50000
    chosen_dates = np.random.choice(dates, size=n_records)
    
    skus = [f"{i:05d}" for i in range(1, 51)]  # 50 SKUs
    descriptions = {sku: f"Product_{sku}" for sku in skus}
    
    base_prices = {sku: np.random.uniform(5, 50) for sku in skus}
    
    records = []
    for d in chosen_dates:
        sku = np.random.choice(skus)
        month = pd.Timestamp(d).month
        season_multiplier = 1.3 if month in [11, 12] else 1.0
        
        is_promo = np.random.rand() < 0.15
        price = base_prices[sku]
        if is_promo:
            price = price * np.random.uniform(0.6, 0.8) # 20-40% discount
            
        true_elasticity = np.random.uniform(-2.5, -0.5)
        base_qty = np.random.uniform(10, 100) * season_multiplier
        qty = int(base_qty * ((price / base_prices[sku]) ** true_elasticity))
        qty = max(1, qty)
        
        records.append({
            'InvoiceNo': f"5{np.random.randint(10000, 99999)}",
            'StockCode': sku,
            'Description': descriptions[sku],
            'Quantity': qty,
            'InvoiceDate': d,
            'UnitPrice': round(price, 2),
            'CustomerID': np.random.randint(10000, 20000),
            'Country': 'United Kingdom'
        })
        
    df = pd.DataFrame(records)
    
    # Introduce noise
    df.loc[np.random.choice(df.index, 500), 'Quantity'] = -5 
    df.loc[np.random.choice(df.index, 500), 'CustomerID'] = np.nan
    df.to_csv(file_path, index=False)
    return df

def clean_data(df):
    """Cleans raw transactional data."""
    df = df.copy()
    df = df.dropna(subset=['CustomerID', 'Description'])
    
    # Robust date parsing (mixed formats sometimes exist in raw UCI)
    df['InvoiceDate'] = pd.to_datetime(df['InvoiceDate'], errors='coerce')
    df = df.dropna(subset=['InvoiceDate'])
    
    df['Quantity'] = pd.to_numeric(df['Quantity'], errors='coerce')
    df['UnitPrice'] = pd.to_numeric(df['UnitPrice'], errors='coerce')
    
    df = df[df['Quantity'] > 0]
    df = df[df['UnitPrice'] > 0]
    
    df['InvoiceNo'] = df['InvoiceNo'].astype(str)
    df = df[~df['InvoiceNo'].str.startswith('C')]
    
    return df

def aggregate_to_sku_week(df):
    """Aggregates transactional data to SKU-week granularity."""
    df = df.set_index('InvoiceDate')
    
    # Weighted average price, sum of quantity
    def wavg(group):
        d = group['UnitPrice']
        w = group['Quantity']
        return (d * w).sum() / w.sum() if w.sum() > 0 else np.nan

    weekly_data = df.groupby(['StockCode', 'Description', pd.Grouper(freq='W')]).apply(
        lambda x: pd.Series({
            'Quantity': x['Quantity'].sum(),
            'UnitPrice': wavg(x)
        })
    ).reset_index()
    
    weekly_data = weekly_data.rename(columns={'level_2': 'Week', 'InvoiceDate': 'Week'})
    if 'level_2' not in weekly_data.columns and 'InvoiceDate' not in weekly_data.columns:
        # Depending on pandas version, the Grouper key might be named differently
        cols = list(weekly_data.columns)
        weekly_data.columns = [c if c not in ['level_2', 'InvoiceDate'] else 'Week' for c in cols]
        
    # Find the datetime column and rename to Week if necessary
    for col in weekly_data.columns:
        if pd.api.types.is_datetime64_any_dtype(weekly_data[col]):
            weekly_data = weekly_data.rename(columns={col: 'Week'})
            break
            
    weekly_data = weekly_data.dropna(subset=['Quantity', 'UnitPrice'])
    weekly_data = weekly_data[weekly_data['Quantity'] > 0]
    return weekly_data

def add_derived_features(df):
    """Adds synthetic cost, promo flags, and season dummies."""
    df = df.copy()
    
    df['Month'] = df['Week'].dt.month
    df['Season'] = df['Month'].apply(lambda x: 'Winter' if x in [12, 1, 2] 
                                     else 'Spring' if x in [3, 4, 5] 
                                     else 'Summer' if x in [6, 7, 8] 
                                     else 'Autumn')
    
    df['Season_original'] = df['Season']
    df = pd.get_dummies(df, columns=['Season'], drop_first=False)
    df['Season'] = df['Season_original']
    df = df.drop(columns=['Season_original'])
    for s in ['Season_Spring', 'Season_Summer', 'Season_Autumn', 'Season_Winter']:
        if s not in df.columns:
            df[s] = 0
            
    from config_loader import config
    
    # Add Cost (Assume margin from config for synthetic purposes if missing)
    cost_margin = config['data']['cost_margin_assumption']
    df['UnitCost'] = df['UnitPrice'] * (1 - cost_margin)
    
    # Simple promo flag: 1 if price is >X% below median price for that SKU
    threshold_pct = config['data']['promo_detection_threshold']
    median_price = df.groupby('StockCode')['UnitPrice'].transform('median')
    df['Promo'] = (df['UnitPrice'] < median_price * threshold_pct).astype(int)
    
    return df

def get_processed_data(file_path='online_retail.csv'):
    print("Loading/generating data...")
    df_raw = load_or_generate_data(file_path)
    print("Cleaning data...")
    df_clean = clean_data(df_raw)
    print("Aggregating to SKU-week...")
    df_weekly = aggregate_to_sku_week(df_clean)
    print("Adding derived features...")
    df_final = add_derived_features(df_weekly)
    return df_final

from db_setup import get_engine

if __name__ == "__main__":
    df = get_processed_data()
    print("Data processing complete. Saving to SQLite database...")
    
    # Rename columns to match schema
    df = df.rename(columns={
        'StockCode': 'sku',
        'Week': 'week_start_date',
        'Quantity': 'quantity',
        'UnitPrice': 'unit_price',
        'UnitCost': 'cost',
        'Promo': 'promo_flag',
        'Season': 'season'
    })
    
    df['revenue'] = df['quantity'] * df['unit_price']
    df['margin'] = df['quantity'] * (df['unit_price'] - df['cost'])
    
    cols = ['sku', 'week_start_date', 'quantity', 'unit_price', 'cost', 'promo_flag', 'season', 'revenue', 'margin']
    df_to_save = df[cols].copy()
    
    engine = get_engine()
    df_to_save.to_sql('sku_weekly_sales', con=engine, if_exists='replace', index=False)
    print("Saved to sku_weekly_sales in SQLite.")

