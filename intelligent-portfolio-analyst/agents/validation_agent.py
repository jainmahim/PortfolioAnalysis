import streamlit as st
from typing import Dict, Any

def validation_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    A safeguard node that validates the state after file ingestion.
    It ensures that the portfolio_data is a dictionary and contains a valid 'stocks' list.
    This prevents crashes in subsequent analysis steps.
    """
    st.session_state.analysis_logs.append("---VALIDATING PORTFOLIO DATA---")
    
    # Safely get the portfolio data from the state
    portfolio_data = state.get('portfolio_data')

    # Check 1: Is the portfolio_data a dictionary?
    if not isinstance(portfolio_data, dict):
        error_msg = f"Validation failed: Portfolio data is not in the correct format (expected dict, got {type(portfolio_data)})."
        st.session_state.analysis_logs.append(error_msg)
        return {"error": error_msg}

    # Check 2: Does it contain a 'stocks' list?
    if 'stocks' not in portfolio_data or not isinstance(portfolio_data.get('stocks'), list):
        error_msg = "Validation failed: 'stocks' key is missing or is not a list in the portfolio data. Please check the file format."
        st.session_state.analysis_logs.append(error_msg)
        return {"error": error_msg}

    # Check 3: Is the list of stocks empty?
    if not portfolio_data.get('stocks'):
        error_msg = "Validation failed: The portfolio file was parsed, but it contains no stocks to analyze."
        st.session_state.analysis_logs.append(error_msg)
        return {"error": error_msg}

    # If all checks pass, return an empty dictionary to allow the workflow to continue.
    return {}

