import streamlit as st
from . import data_fetchers # Use relative import for clean architecture

@st.cache_data(ttl=86400) # Cache the data for 24 hours for performance
def get_stock_universe():
    """
    Fetches a comprehensive list of all traded stocks from the NSE.
    The result is cached to ensure high performance after the first run.
    This function replaces the old, static STOCK_UNIVERSE list.
    """
    # This will call our new data fetching function
    return data_fetchers.fetch_all_nse_tickers()

