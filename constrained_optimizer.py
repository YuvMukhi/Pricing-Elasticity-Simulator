from scipy.optimize import minimize_scalar
from simulation_engine import simulate_demand

def find_constrained_optimal_price(current_volume, current_price, unit_cost, elasticity, min_margin_pct=0.30):
    """
    Finds the revenue-maximizing price change bounded by a minimum margin percentage.
    Uses minimize_scalar bounded search over a realistic range of price changes.
    """
    def objective(price_change_pct):
        new_price = current_price * (1 + price_change_pct)
        new_volume = simulate_demand(current_volume, current_price, price_change_pct, elasticity)
        
        revenue = new_volume * new_price
        margin = new_volume * (new_price - unit_cost)
        
        # Constraint check: Margin % >= min_margin_pct
        current_margin_pct = margin / revenue if revenue > 0 else 0
        if current_margin_pct < min_margin_pct:
            return 1e9 # Penalty for violating constraint
            
        return -revenue

    res = minimize_scalar(objective, bounds=(-0.50, 0.50), method='bounded')
    
    if res.success and res.fun < 1e8:
        optimal_change = res.x
        new_price = current_price * (1 + optimal_change)
        return new_price, optimal_change
    else:
        # Fallback if no feasible solution exists (e.g. impossible to meet margin threshold)
        return current_price, 0.0
