import pandas as pd
import numpy as np

def calculate_promo_lift(df):
    """
    Compares average sales during promo weeks vs baseline (non-promo) weeks.
    Matches on Season to avoid conflating promo lift with seasonal demand.
    """
    results = []
    
    for sku in df['StockCode'].unique():
        sku_data = df[df['StockCode'] == sku].copy()
        
        if sku_data['Promo'].nunique() < 2:
            continue
            
        for season in sku_data['Season'].unique():
            season_data = sku_data[sku_data['Season'] == season].copy()
            
            promo_data = season_data[season_data['Promo'] == 1]
            base_data = season_data[season_data['Promo'] == 0]
            
            if len(promo_data) == 0 or len(base_data) == 0:
                continue
                
            avg_promo_qty = promo_data['Quantity'].mean()
            avg_base_qty = base_data['Quantity'].mean()
            
            lift = (avg_promo_qty - avg_base_qty) / avg_base_qty if avg_base_qty > 0 else 0
            
            avg_promo_price = promo_data['UnitPrice'].mean()
            avg_base_price = base_data['UnitPrice'].mean()
            avg_cost = promo_data['UnitCost'].mean()
            
            base_margin = avg_base_qty * (avg_base_price - avg_cost)
            promo_margin = avg_promo_qty * (avg_promo_price - avg_cost)
            inc_margin = promo_margin - base_margin
            
            discount_cost = (avg_base_price - avg_promo_price) * avg_promo_qty
            roi = inc_margin / discount_cost if discount_cost > 0 else 0
            
            results.append({
                'StockCode': sku,
                'Description': sku_data['Description'].iloc[0],
                'Season': season,
                'Avg_Base_Qty': avg_base_qty,
                'Avg_Promo_Qty': avg_promo_qty,
                'Lift': lift,
                'Discount_Cost': discount_cost,
                'Inc_Margin': inc_margin,
                'ROI': roi
            })
            
    return pd.DataFrame(results)

def analyze_forward_buying(df):
    """
    Checks if sales drop significantly in the weeks following a promotion.
    """
    df = df.sort_values(by=['StockCode', 'Week']).copy()
    df['Prev_Week_Promo'] = df.groupby('StockCode')['Promo'].shift(1)
    df['Is_Post_Promo'] = ((df['Promo'] == 0) & (df['Prev_Week_Promo'] == 1)).astype(int)
    
    results = []
    for sku in df['StockCode'].unique():
        sku_data = df[df['StockCode'] == sku]
        
        baseline_qty = sku_data[(sku_data['Promo'] == 0) & (sku_data['Is_Post_Promo'] == 0)]['Quantity'].mean()
        post_promo_qty = sku_data[sku_data['Is_Post_Promo'] == 1]['Quantity'].mean()
        
        if pd.isna(baseline_qty) or pd.isna(post_promo_qty):
            continue
            
        drop_pct = (baseline_qty - post_promo_qty) / baseline_qty if baseline_qty > 0 else 0
        
        results.append({
            'StockCode': sku,
            'Forward_Buying_Flag': drop_pct > 0.15,
            'Post_Promo_Drop_Pct': drop_pct
        })
        
    return pd.DataFrame(results)

if __name__ == "__main__":
    df = pd.read_csv("processed_data.csv")
    df['Week'] = pd.to_datetime(df['Week'])
    
    lift_df = calculate_promo_lift(df)
    fb_df = analyze_forward_buying(df)
    
    print("Promo Lift Sample:")
    print(lift_df.head())
    print("\nForward Buying Sample:")
    print(fb_df.head())
