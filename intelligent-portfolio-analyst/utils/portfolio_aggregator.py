from typing import List, Dict, Any, Optional

def aggregate_portfolio_metrics(stock_list: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    A centralized calculation engine that takes a list of enriched stocks
    and computes all portfolio-level aggregate metrics.

    Args:
        stock_list: A list of dictionaries, where each dictionary represents a stock
                    and its enriched data.

    Returns:
        A dictionary containing all aggregated portfolio metrics.
    """
    if not stock_list:
        return {}

    # --- Aggregate Financials ---
    total_investment = sum(stock.get('invested_value', 0) for stock in stock_list)
    total_current_value = sum(stock.get('current_value', 0) for stock in stock_list)
    
    overall_pnl: float = 0.0
    overall_pnl_percent: Optional[float] = None

    if total_investment > 0:
        overall_pnl = total_current_value - total_investment
        overall_pnl_percent = (overall_pnl / total_investment) * 100

    # --- Calculate Dynamic Risk Profile (Weighted Beta) ---
    risk_profile: str = "N/A"
    if total_current_value > 0:
        # Calculate the weighted average beta of the portfolio
        total_beta_weight = sum(
            (stock.get('current_value', 0) / total_current_value) * stock.get('beta', 1.0)
            for stock in stock_list
        )
    
        if total_beta_weight < 0.8:
            risk_profile = "Conservative"
        elif total_beta_weight <= 1.2:
            risk_profile = "Moderate Growth"
        else:
            risk_profile = "Aggressive"

    # --- Calculate Allocations ---
    asset_allocation: Dict[str, float] = {"Stocks": total_current_value}
    sector_allocation: Dict[str, float] = {}
    for stock in stock_list:
        sector = stock.get('fundamentals', {}).get('sector', 'Other')
        current_val = stock.get('current_value', 0)
        
        # Consolidate N/A or missing sectors into 'Other'
        if not sector or sector == 'N/A':
            sector = 'Other'
            
        sector_allocation[sector] = sector_allocation.get(sector, 0.0) + current_val
            
    # --- Return a structured dictionary with all results ---
    return {
        "total_investment": total_investment,
        "current_value": total_current_value,
        "overall_pnl": overall_pnl,
        "overall_pnl_percent": overall_pnl_percent,
        "risk_profile": risk_profile,
        "asset_allocation": asset_allocation,
        "sector_allocation": sector_allocation
    }
