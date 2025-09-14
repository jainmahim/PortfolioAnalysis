def aggregate_portfolio_metrics(stock_list):
    """
    A centralized calculation engine that takes a list of enriched stocks
    and computes all portfolio-level aggregate metrics.
    """
    if not stock_list:
        return {}

    # --- Aggregate Financials ---
    total_investment = sum(stock.get('invested_value', 0) for stock in stock_list)
    total_current_value = sum(stock.get('current_value', 0) for stock in stock_list)
    
    overall_pnl = 0.0
    overall_pnl_percent = None
    if total_investment > 0:
        overall_pnl = total_current_value - total_investment
        overall_pnl_percent = (overall_pnl / total_investment) * 100

    # --- Calculate Dynamic Risk Profile (Weighted Beta) ---
    risk_profile = "N/A"
    total_beta_weight = 0.0
    if total_current_value > 0:
        for stock in stock_list:
            stock_weight = stock.get('current_value', 0) / total_current_value
            total_beta_weight += stock.get('beta', 1.0) * stock_weight
    
        if total_beta_weight < 0.8:
            risk_profile = "Conservative"
        elif total_beta_weight <= 1.2:
            risk_profile = "Moderate Growth"
        else:
            risk_profile = "Aggressive"

    # --- Calculate Allocations ---
    asset_allocation = {"Stocks": total_current_value}
    sector_allocation = {}
    for stock in stock_list:
        sector = stock.get('fundamentals', {}).get('sector', 'Other')
        current_val = stock.get('current_value', 0)
        if sector and sector != 'N/A':
            sector_allocation[sector] = sector_allocation.get(sector, 0.0) + current_val
        else:
            sector_allocation['Other'] = sector_allocation.get('Other', 0.0) + current_val
            
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

