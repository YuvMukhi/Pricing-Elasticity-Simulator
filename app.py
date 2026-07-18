import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from simulation_engine import simulate_financials, find_optimal_prices
from promo_effectiveness import calculate_promo_lift, analyze_forward_buying

st.set_page_config(page_title="Pricing & Promotion Simulator", layout="wide")

@st.cache_data
def load_data():
    try:
        data = pd.read_csv("processed_data.csv")
        data['Week'] = pd.to_datetime(data['Week'])
        elasticity_results = pd.read_csv("elasticity_results.csv")
        return data, elasticity_results
    except FileNotFoundError:
        return None, None

data, elasticity_results = load_data()

if data is None or elasticity_results is None:
    st.error("Data not found. Please run data_loader.py and elasticity_estimator.py first.")
    st.stop()

reliable_skus = elasticity_results[elasticity_results['Reliable'] == True]

if reliable_skus.empty:
    st.error("No reliable SKU elasticities found.")
    st.stop()

st.title("Pricing & Promotion Optimization Simulator")
st.markdown("A commercial decision-support tool to estimate price elasticity and simulate revenue/margin impacts.")

st.sidebar.header("Controls")
selected_sku = st.sidebar.selectbox("Select SKU", reliable_skus['StockCode'].unique())

sku_data = data[data['StockCode'] == selected_sku]
sku_elasticity_info = reliable_skus[reliable_skus['StockCode'] == selected_sku].iloc[0]

latest_weeks = sku_data.sort_values('Week').tail(4)
current_price = latest_weeks['UnitPrice'].mean()
current_volume = latest_weeks['Quantity'].mean()
unit_cost = latest_weeks['UnitCost'].mean()
current_margin = (current_price - unit_cost) * current_volume
current_revenue = current_price * current_volume

st.header(f"SKU: {selected_sku} - {sku_elasticity_info['Description']}")

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Current Price", f"${current_price:.2f}")
col2.metric("Unit Cost", f"${unit_cost:.2f}")
col3.metric("Current Vol/Week", f"{current_volume:.1f}")
col4.metric("Elasticity", f"{sku_elasticity_info['Elasticity']:.2f}")
col5.metric("Model R²", f"{sku_elasticity_info['R_Squared']:.2f}")

st.markdown(f"**95% Confidence Interval for Elasticity:** [{sku_elasticity_info['CI_Lower']:.2f}, {sku_elasticity_info['CI_Upper']:.2f}]")

st.divider()

st.subheader("Price Simulation Engine")

price_change_pct = st.slider("Simulate Price Change (%)", -20, 20, 0, 5) / 100.0

sim_df = simulate_financials(current_volume, current_price, unit_cost, sku_elasticity_info['Elasticity'])
optimal = find_optimal_prices(sim_df)

selected_sim = sim_df[sim_df['Price_Change_Pct'] == price_change_pct].iloc[0]

c1, c2, c3 = st.columns(3)
c1.metric(f"Projected Volume", f"{selected_sim['New_Volume']:.1f}", f"{(selected_sim['New_Volume'] - current_volume):.1f}")
c2.metric(f"Projected Revenue", f"${selected_sim['New_Revenue']:.2f}", f"${(selected_sim['New_Revenue'] - current_revenue):.2f}")
c3.metric(f"Projected Margin", f"${selected_sim['New_Margin']:.2f}", f"${(selected_sim['New_Margin'] - current_margin):.2f}")


fig, ax1 = plt.subplots(figsize=(10, 4))
ax2 = ax1.twinx()

sns.lineplot(data=sim_df, x='Price_Change_Pct', y='New_Revenue', color='blue', ax=ax1, label='Revenue')
sns.lineplot(data=sim_df, x='Price_Change_Pct', y='New_Margin', color='green', ax=ax2, label='Margin')

ax1.axvline(0, color='gray', linestyle='--', label='Current Price')
ax1.axvline(optimal['Revenue_Max_Change'], color='blue', linestyle=':', label='Rev Optimal')
ax2.axvline(optimal['Margin_Max_Change'], color='green', linestyle=':', label='Margin Optimal')

# Format x-axis as percentage
vals = ax1.get_xticks()
ax1.set_xticklabels(['{:,.0%}'.format(x) for x in vals])

ax1.set_xlabel('Price Change %')
ax1.set_ylabel('Revenue ($)', color='blue')
ax2.set_ylabel('Margin ($)', color='green')

lines, labels = ax1.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax2.legend(lines + lines2, labels + labels2, loc='upper right')

st.pyplot(fig)

st.subheader("Actionable Recommendation")
if optimal['Margin_Max_Change'] > 0:
    rec = f"**INCREASE PRICE:** The current price sits below the margin-optimal price. A price increase of {optimal['Margin_Max_Change']*100:.0f}% is projected to maximize margin."
elif optimal['Margin_Max_Change'] < 0:
    rec = f"**DECREASE PRICE:** The current price sits above the margin-optimal price. A price cut of {abs(optimal['Margin_Max_Change'])*100:.0f}% is projected to improve overall margin."
else:
    rec = "**HOLD PRICE:** The current price is near the margin-optimal point."
st.info(rec)

st.divider()

st.subheader("Promotion Effectiveness & Cannibalization")
lift_df = calculate_promo_lift(data)
fb_df = analyze_forward_buying(data)

sku_lift = lift_df[lift_df['StockCode'] == selected_sku]
sku_fb = fb_df[fb_df['StockCode'] == selected_sku]

if not sku_lift.empty:
    st.dataframe(sku_lift[['Season', 'Avg_Base_Qty', 'Avg_Promo_Qty', 'Lift', 'ROI']].style.format({'Lift': '{:.1%}', 'ROI': '{:.1%}'}))
else:
    st.write("Not enough historical promotion data for this SKU.")

if not sku_fb.empty and sku_fb.iloc[0]['Forward_Buying_Flag']:
    st.warning(f"⚠️ **Demand Pull-Forward Detected**: Sales drop by {sku_fb.iloc[0]['Post_Promo_Drop_Pct']:.1%} in the week following a promotion. The promo lift may be partially cannibalizing future full-price sales.")
else:
    st.success("✅ No significant forward-buying or post-promo dip detected.")
