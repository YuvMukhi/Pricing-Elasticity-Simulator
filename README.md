# Pricing & Promotion Optimization Simulator

This project is an end-to-end commercial decision-support tool that estimates price elasticity from historical retail sales data, simulates the revenue and margin impact of pricing decisions, and measures the ROI and cannibalization effects of promotions.

## Business Problem
Retailers often make pricing and promotion decisions based on intuition or simple historical averages. This tool brings statistical rigor to those decisions by estimating the true price elasticity of demand (how much volume changes when price changes) while controlling for seasonality and promotional effects.

## Methodology & Architecture

1. **Data Ingestion & Cleaning (`data_loader.py`)**
   - Automatically downloads the UCI Online Retail dataset or generates a statistically robust synthetic dataset if the network is unavailable.
   - Cleans the data by dropping cancelled orders and aggregating to SKU-week granularity (a stable unit of analysis that smooths daily noise while preserving price variation).
   - Writes the processed output to a local SQLite database table `sku_weekly_sales`.

2. **Elasticity Estimation (`elasticity_estimator_v2.py`)**
   - Uses `statsmodels` to run a log-log Ordinary Least Squares (OLS) regression for each SKU.
   - Evaluates a Ridge regression model (`sklearn.linear_model.RidgeCV`) using 5-fold cross-validation to select the optimal regularization strength $\alpha$.
   - By comparing the unregularized OLS elasticity against the regularized Ridge elasticity, the tool flags SKUs that diverge significantly (e.g. >30% relative difference). This divergence typically occurs on SKUs with sparse or noisy data where OLS overfits, providing a critical reliability check for business stakeholders.
   - The estimator calculates optimal price points for Revenue and Margin maximization.
   - **Constrained Price Optimization (`constrained_optimizer.py`)**: Uses `scipy.optimize.minimize_scalar` bounded search to calculate a "Constrained Optimal Price" that maximizes revenue strictly subject to a minimum margin floor (e.g. 30%). This prevents the simulation from recommending highly elastic price cuts that destroy profitability.
   - Writes the results directly to the SQLite table `elasticity_results`.

3. **Cross-Price Elasticity (`cross_price_elasticity.py`)**
   - Identifies overlapping SKU pairs and models them using an extended log-log regression: $\log(Q_A) = \beta_0 + \beta_1\log(P_A) + \beta_2\log(P_B) + \beta_3\text{Promo}_A$.
   - Programmatically pairs SKUs with the highest co-occurrence of sales weeks. (Note: Since the dataset is synthetic and lacks explicit product hierarchy categories, time-series overlap is used as a proxy for co-purchase viability).
   - Evaluates the cross-price coefficient $\beta_2$ to classify pairs statistically as Substitutes ($\beta_2 > 0$) or Complements ($\beta_2 < 0$), writing findings to `cross_price_elasticity` in the DB. Given the limited sample size of tested pairs, these results serve as an exploratory framework for broader category management.

3. **SQL Analytics Layer**
   - We utilize a local **SQLite database** (`pricing_simulator.db`) mapped via **SQLAlchemy**. SQLite was chosen because it allows for full standard SQL analytical capabilities without requiring external server setup or networking overhead, making the tool portable and fast.
   - `queries.sql` contains a series of well-commented analytical SQL queries representing questions a business stakeholder would typically ask, such as:
     - *Top 10 SKUs by projected revenue upside.*
     - *SKUs currently priced above their margin-optimal price.*
     - *Average elasticity by season to verify stability.*
   - `query_runner.py` parses and executes these named queries directly into Pandas DataFrames, cleanly decoupling SQL logic from Python application code.

4. **Interactive Dashboard (`app.py`)**
   - A multi-page Streamlit application fully backed by the local SQLite database.
   - **Portfolio View**: A high-level macro view showing all reliable SKUs, dynamically color-coding pricing status (Overpriced, Underpriced, Near-Optimal), and summarizing total potential revenue upside. This is crucial for business stakeholders deciding where to focus attention first.
   - **SKU Deep Dive**: A detailed simulator that visualizes the optimal revenue and margin curves for a specific product, alongside promotion effectiveness metrics.

## Concrete Commercial Findings
Using the synthetic/retail data approach, you will commonly find:
- **Margin vs. Revenue Divergence**: For highly elastic SKUs (elasticity < -2.0), a moderate price cut often increases total revenue but erodes total margin, highlighting the danger of revenue-chasing without cost awareness.
- **Cannibalization**: Some SKUs show high promotional lift but suffer a "post-promo dip," indicating the promotion merely pulled future full-price sales forward rather than generating net-new demand.

## Running the Project Locally

```bash
pip install -r requirements.txt
python data_loader.py
python elasticity_estimator.py
pytest test_db.py test_simulation.py
streamlit run app.py
```
