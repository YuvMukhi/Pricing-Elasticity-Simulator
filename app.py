import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from query_runner import run_query
from db_setup import get_engine
from simulation_engine import simulate_financials, find_optimal_prices
import query_runner

st.set_page_config(page_title="Pricing & Promotion Simulator", layout="wide")

# Reload queries dynamically
query_runner.QUERIES = query_runner.load_queries()

st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["Portfolio View", "SKU Deep Dive"])

if page == "Portfolio View":
    st.title("Portfolio Pricing Optimization View")
    st.markdown("Overview of all reliable SKUs, identifying pricing opportunities.")
    
    try:
        portfolio_df = run_query('portfolio_overview')
        
        total_skus_query = pd.read_sql_query("SELECT COUNT(*) as c FROM elasticity_results", get_engine())
        total_skus = total_skus_query.iloc[0]['c']
        reliable_count = len(portfolio_df)
        pct_reliable = (reliable_count / total_skus * 100) if total_skus > 0 else 0
        total_upside = portfolio_df['rev_upside'].sum()
        
        overpriced = len(portfolio_df[portfolio_df['pricing_status'] == 'Overpriced'])
        underpriced = len(portfolio_df[portfolio_df['pricing_status'] == 'Underpriced'])
        
        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("Total SKUs Analyzed", f"{total_skus}")
        col2.metric("% Reliable Estimates", f"{pct_reliable:.1f}%")
        col3.metric("Total Rev Upside", f"${total_upside:,.0f}")
        col4.metric("Overpriced SKUs", f"{overpriced}")
        col5.metric("Underpriced SKUs", f"{underpriced}")
        
        st.divider()
        
        def color_status(val):
            if val == 'Overpriced': return 'color: red'
            elif val == 'Underpriced': return 'color: orange'
            return 'color: green'
            
        styled_df = portfolio_df.style.map(color_status, subset=['pricing_status']).format({
            'elasticity': '{:.2f}',
            'current_price': '${:.2f}',
            'rev_optimal_price': '${:.2f}',
            'margin_optimal_price': '${:.2f}',
            'constrained_optimal_price': '${:.2f}',
            'rev_upside': '${:,.0f}',
            'margin_upside': '${:,.0f}'
        })
        
        st.dataframe(styled_df, use_container_width=True)
        
        # Export CSV
        csv = portfolio_df.to_csv(index=False).encode('utf-8')
        st.download_button("Export to CSV", csv, "portfolio_view.csv", "text/csv")
        
        st.divider()
        st.subheader("Select SKU for Deep Dive")
        selected_sku = st.selectbox("Choose a SKU to analyze in detail:", portfolio_df['sku'].unique())
        
        if st.button("Go to SKU Deep Dive"):
            st.session_state['selected_sku'] = selected_sku
            st.rerun() # Automatically refresh to switch page logic if we tied it to state, but radio button is separate.
            # To actually change the radio button from code, we need a session state for the radio.
            
    except Exception as e:
        st.error(f"Error loading portfolio view: {e}")

elif page == "SKU Deep Dive":
    st.title("SKU Deep Dive")
    
    try:
        portfolio_df = run_query('portfolio_overview')
        reliable_skus = portfolio_df['sku'].unique()
        
        if len(reliable_skus) == 0:
            st.error("No reliable SKU elasticities found.")
            st.stop()
            
        default_idx = 0
        if 'selected_sku' in st.session_state and st.session_state['selected_sku'] in reliable_skus:
            default_idx = list(reliable_skus).index(st.session_state['selected_sku'])
            
        selected_sku = st.sidebar.selectbox("Select SKU", reliable_skus, index=default_idx)
        st.session_state['selected_sku'] = selected_sku 
        
        engine = get_engine()
        sku_data = pd.read_sql_query(f"SELECT * FROM sku_weekly_sales WHERE sku = '{selected_sku}'", engine)
        sku_elasticity_info = pd.read_sql_query(f"SELECT * FROM elasticity_results WHERE sku = '{selected_sku}'", engine).iloc[0]
        
        current_price = sku_elasticity_info['current_price']
        current_volume = sku_elasticity_info['current_volume']
        unit_cost = sku_elasticity_info['unit_cost']
        
        current_margin = (current_price - unit_cost) * current_volume
        current_revenue = current_price * current_volume
        
        st.header(f"SKU: {selected_sku} - {sku_elasticity_info['description']}")
        
        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("Current Price", f"${current_price:.2f}")
        col2.metric("Unit Cost", f"${unit_cost:.2f}")
        col3.metric("Current Vol/Week", f"{current_volume:.1f}")
        col4.metric("Elasticity", f"{sku_elasticity_info['elasticity']:.2f}")
        col5.metric("Model R²", f"{sku_elasticity_info['r_squared']:.2f}")
        
        st.divider()
        st.subheader("Price Simulation Engine")
        
        price_change_pct = st.slider("Simulate Price Change (%)", -20, 20, 0, 5) / 100.0
        
        sim_df = simulate_financials(current_volume, current_price, unit_cost, sku_elasticity_info['elasticity'])
        optimal = find_optimal_prices(sim_df)
        
        selected_sim = sim_df[sim_df['Price_Change_Pct'] == price_change_pct].iloc[0]
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Projected Volume", f"{selected_sim['New_Volume']:.1f}", f"{(selected_sim['New_Volume'] - current_volume):.1f}")
        c2.metric("Projected Revenue", f"${selected_sim['New_Revenue']:.2f}", f"${(selected_sim['New_Revenue'] - current_revenue):.2f}")
        c3.metric("Projected Margin", f"${selected_sim['New_Margin']:.2f}", f"${(selected_sim['New_Margin'] - current_margin):.2f}")
        
        fig, ax1 = plt.subplots(figsize=(10, 4))
        ax2 = ax1.twinx()
        
        sns.lineplot(data=sim_df, x='Price_Change_Pct', y='New_Revenue', color='blue', ax=ax1, label='Revenue')
        sns.lineplot(data=sim_df, x='Price_Change_Pct', y='New_Margin', color='green', ax=ax2, label='Margin')
        
        ax1.axvline(0, color='gray', linestyle='--', label='Current Price')
        ax1.axvline(optimal['Revenue_Max_Change'], color='blue', linestyle=':', label='Rev Optimal')
        ax2.axvline(optimal['Margin_Max_Change'], color='green', linestyle=':', label='Margin Optimal')
        
        vals = ax1.get_xticks()
        ax1.set_xticklabels(['{:,.0%}'.format(x) for x in vals])
        
        ax1.set_xlabel('Price Change %')
        ax1.set_ylabel('Revenue ($)', color='blue')
        ax2.set_ylabel('Margin ($)', color='green')
        
        lines, labels = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax2.legend(lines + lines2, labels + labels2, loc='upper right')
        
        st.pyplot(fig)
        
    except Exception as e:
        st.error(f"Error loading deep dive: {e}")
