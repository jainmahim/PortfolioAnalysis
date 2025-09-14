import streamlit as st
from typing import Dict, Any
from utils.portfolio_aggregator import aggregate_portfolio_metrics

def report_generation_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Assembles the final report by calling the centralized portfolio aggregator
    and including all enriched data sources like news.
    """
    st.session_state.analysis_logs.append("---GENERATING FINAL REPORT---")
    
    # Retrieve all pieces of data from the current state
    enriched_stocks = state.get('stock_analysis_results', [])
    news_results = state.get('news', [])
    analysis_errors = state.get('analysis_errors', [])

    st.session_state.analysis_logs.append(f"Report generator received {len(enriched_stocks)} enriched stock results to process.")

    # Use the centralized aggregator for all financial calculations
    aggregate_metrics = aggregate_portfolio_metrics(enriched_stocks)

    # Assemble the final report by combining all data sources
    final_report = {
        "stock_analysis": enriched_stocks,
        "news": news_results,
        "analysis_errors": analysis_errors,
        **aggregate_metrics 
    }

    st.session_state.analysis_logs.append("---FINAL REPORT GENERATED SUCCESSFULLY---")
    return {"final_report": final_report}

