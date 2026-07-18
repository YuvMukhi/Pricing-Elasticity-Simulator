-- @name: top_revenue_upside
-- Top 10 SKUs by projected revenue upside (current price vs. revenue-optimal price)
SELECT 
    sku,
    elasticity,
    current_price,
    rev_optimal_price,
    rev_upside
FROM elasticity_results
WHERE reliability_flag = 1
ORDER BY rev_upside DESC
LIMIT 10;

-- @name: pricing_status
-- SKUs currently priced above their margin-optimal price (overpriced) and below it (underpriced)
SELECT 
    sku,
    current_price,
    margin_optimal_price,
    CASE 
        WHEN current_price > margin_optimal_price * 1.05 THEN 'Overpriced'
        WHEN current_price < margin_optimal_price * 0.95 THEN 'Underpriced'
        ELSE 'Near-Optimal'
    END as status
FROM elasticity_results
WHERE reliability_flag = 1;

-- @name: thin_margins
-- SKUs with negative or thin margins at current price (margin < 10%)
SELECT 
    sku,
    current_price,
    unit_cost,
    ((current_price - unit_cost) / current_price) as margin_pct
FROM elasticity_results
WHERE reliability_flag = 1 AND ((current_price - unit_cost) / current_price) < 0.10;

-- @name: elasticity_by_season
-- Average elasticity by season, to check seasonal stability
SELECT 
    s.season,
    AVG(e.elasticity) as avg_elasticity,
    COUNT(DISTINCT s.sku) as sku_count
FROM sku_weekly_sales s
JOIN elasticity_results e ON s.sku = e.sku
WHERE e.reliability_flag = 1
GROUP BY s.season;

-- @name: promo_vs_non_promo
-- Promo weeks vs non-promo weeks average quantity sold, joined across both tables
SELECT 
    s.promo_flag,
    AVG(s.quantity) as avg_weekly_qty,
    AVG(s.revenue) as avg_weekly_revenue
FROM sku_weekly_sales s
JOIN elasticity_results e ON s.sku = e.sku
WHERE e.reliability_flag = 1
GROUP BY s.promo_flag;

-- @name: unreliable_estimates
-- SKUs with unreliable elasticity estimates (wide confidence interval or positive elasticity)
SELECT 
    sku,
    elasticity,
    ci_lower,
    ci_upper,
    (ci_upper - ci_lower) as ci_width
FROM elasticity_results
WHERE reliability_flag = 0;

-- @name: top_5_mom_trend
-- Month-over-month revenue trend for the top 5 highest-revenue SKUs
WITH TopSKUs AS (
    SELECT sku, SUM(revenue) as total_rev
    FROM sku_weekly_sales
    GROUP BY sku
    ORDER BY total_rev DESC
    LIMIT 5
),
MonthlyRev AS (
    SELECT 
        s.sku,
        strftime('%Y-%m', s.week_start_date) as month,
        SUM(s.revenue) as monthly_revenue
    FROM sku_weekly_sales s
    JOIN TopSKUs t ON s.sku = t.sku
    GROUP BY s.sku, strftime('%Y-%m', s.week_start_date)
)
SELECT 
    sku,
    month,
    monthly_revenue,
    LAG(monthly_revenue) OVER(PARTITION BY sku ORDER BY month) as prev_month_revenue,
    (monthly_revenue - LAG(monthly_revenue) OVER(PARTITION BY sku ORDER BY month)) / NULLIF(LAG(monthly_revenue) OVER(PARTITION BY sku ORDER BY month), 0) as mom_growth_pct
FROM MonthlyRev
ORDER BY sku, month;

-- @name: portfolio_overview
SELECT sku, description, elasticity, current_price, rev_optimal_price, margin_optimal_price, rev_upside, margin_upside, CASE WHEN current_price > margin_optimal_price * 1.05 THEN 'Overpriced' WHEN current_price < margin_optimal_price * 0.95 THEN 'Underpriced' ELSE 'Near-Optimal' END as pricing_status FROM elasticity_results WHERE reliability_flag = 1 ORDER BY rev_upside DESC;
