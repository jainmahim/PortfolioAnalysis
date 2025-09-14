import os
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
import json
import re
import streamlit as st
from utils import data_fetchers
from concurrent.futures import ThreadPoolExecutor, as_completed

def analyze_screener_stock(ticker, risk_appetite, horizon):
    """
    Analyzes a single stock against user-defined criteria.
    Returns a dictionary with the recommendation if it's a match, otherwise None.
    """
    try:
        # 1. Fetch Key Data
        formatted_ticker = f"{ticker.strip().upper()}.NS"
        beta = data_fetchers.get_beta(formatted_ticker)
        fundamentals = data_fetchers.get_fundamental_data(formatted_ticker)

        # 2. Fast Pre-filtering based on Risk Appetite and Beta
        is_risk_match = False
        if risk_appetite == "Conservative" and beta < 1.0:
            is_risk_match = True
        elif risk_appetite == "Moderate" and 0.8 <= beta <= 1.2:
            is_risk_match = True
        elif risk_appetite == "Aggressive" and beta > 1.0:
            is_risk_match = True
        
        if not is_risk_match:
            return None

        # 3. AI-Powered Final Verdict for stocks that pass the filter
        llm = ChatGroq(
            model_name="meta-llama/llama-4-scout-17b-16e-instruct",
            groq_api_key=os.getenv("GROQ_API_KEY"),
            temperature=0.0
        )
        prompt = ChatPromptTemplate.from_template(
            "You are a professional investment advisor. A client has a '{horizon}' investment horizon "
            "and a '{risk_appetite}' risk appetite. Based on the following data for the stock '{ticker}', "
            "would you recommend it to them? Data: Beta={beta}, Fundamentals={fundamentals}. "
            "Return ONLY a raw JSON object with two keys: 'match' ('Yes' or 'No') and 'reason' (a concise justification)."
        )
        chain = prompt | llm
        response = chain.invoke({
            "horizon": horizon,
            "risk_appetite": risk_appetite,
            "ticker": ticker,
            "beta": beta,
            "fundamentals": fundamentals
        })

        # 4. Parse the response and return if it's a match
        match_json = json.loads(response.content)
        if match_json.get('match') == 'Yes':
            return {
                "Symbol": ticker,
                "Reason": match_json.get('reason', 'N/A'),
                "Beta": beta,
                "P/E Ratio": fundamentals.get("P/E Ratio", "N/A")
            }
        
        return None

    except Exception:
        return None


def run_screener(tickers, risk_appetite, horizon):
    """
    Runs the personalized stock screener on a user-provided list of tickers.
    """
    st.session_state.analysis_logs.append("---STARTING PERSONALIZED STOCK SCREENER---")
    
    recommendations = []
    
    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_ticker = {executor.submit(analyze_screener_stock, ticker, risk_appetite, horizon): ticker for ticker in tickers}
        
        for future in as_completed(future_to_ticker):
            result = future.result()
            if result:
                recommendations.append(result)

    st.session_state.analysis_logs.append("---STOCK SCREENER COMPLETE---")
    return recommendations

