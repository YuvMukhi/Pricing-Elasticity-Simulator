# Pricing & Promotion Optimization Simulator

This project is an end-to-end commercial decision-support tool that estimates price elasticity from historical retail sales data, simulates the revenue and margin impact of pricing decisions, and measures the ROI and cannibalization effects of promotions.

## Business Problem
Retailers often make pricing and promotion decisions based on intuition or simple historical averages. This tool brings statistical rigor to those decisions by estimating the true price elasticity of demand (how much volume changes when price changes) while controlling for seasonality and promotional effects.

## Methodology & Architecture

1. **Data Ingestion & Cleaning (`data_loader.py`)**
   - Automatically downloads the UCI Online Retail dataset or generates a statistically robust synthetic dataset if the network is unavailable.
   - Cleans the data by dropping cancelled orders and aggregating to SKU-week granularity (a stable unit of analysis that smooths daily noise while preserving price variation).
   - **Assumptions**: Since the UCI dataset lacks product cost and explicit promo flags, this module synthesizes a `UnitCost` (at 60% of the historical median price) and a `Promo` flag (triggered when a weekly price drops >10% below the median).

2. **Elasticity Estimation (`elasticity_estimator.py`)**
   - Uses `statsmodels` to run a log-log regression for each SKU: $\log(Q) = \beta_0 + \beta_1 \log(P) + \beta_2 \text{Promo} + \beta_{Seasons}$.
   - The coefficient $\beta_1$ represents the price elasticity.
   - Applies an analytical reliability filter: SKUs with positive elasticities, highly unstable standard errors, or insufficient price variation are explicitly flagged as unreliable and excluded from recommendations.

3. **Simulation Engine (`simulation_engine.py`)**
   - A standalone, testable module that projects volume, revenue, and margin across a range of hypothetical price changes (-20% to +20%).
   - Identifies divergent optimal price points (e.g., the price that maximizes revenue vs. the price that maximizes margin).

4. **Promotion Effectiveness (`promo_effectiveness.py`)**
   - Calculates true promo lift by matching on season.
   - Identifies "demand pull-forward" (cannibalization) by flagging SKUs where sales drop significantly in the weeks immediately following a promotion.

5. **Interactive Dashboard (`app.py`)**
   - A Streamlit app that brings the models to life with interactive sliders, visualizations, and automated natural-language recommendations.

## Concrete Commercial Findings
Using the synthetic/retail data approach, you will commonly find:
- **Margin vs. Revenue Divergence**: For highly elastic SKUs (elasticity < -2.0), a moderate price cut often increases total revenue but erodes total margin, highlighting the danger of revenue-chasing without cost awareness.
- **Cannibalization**: Some SKUs show high promotional lift but suffer a "post-promo dip," indicating the promotion merely pulled future full-price sales forward rather than generating net-new demand.

## Limitations & Future Enhancements
As a decision analyst, it is critical to state where the model's assumptions break:
1. **Competitor Reaction**: The simulation assumes competitors hold their prices constant. In reality, a 20% price cut might trigger a price war.
2. **Inventory Constraints**: The model projects unconstrained demand. It does not account for stockouts or supply chain limits if volume spikes.
3. **Causal Inference**: The promotion lift uses a simple before/after control. A more advanced design would use propensity matching or a controlled synthetic control group to isolate pure causal lift.

## Running the Project Locally

```bash
pip install -r requirements.txt
python data_loader.py
python elasticity_estimator.py
pytest test_simulation.py
streamlit run app.py
```
