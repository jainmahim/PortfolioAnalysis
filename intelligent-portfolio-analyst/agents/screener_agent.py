import os
import re
import json
import streamlit as st
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from typing import Dict, Any
from utils import data_fetchers

# --- AGENT CONFIGURATION ---

# Define the prompt as a constant for better readability and maintenance
PROS_CONS_PROMPT_TEMPLATE = (
    "You are a senior stock analyst reviewing financial data for '{stock_name}'. "
    "Based on the following metrics: {fundamentals}, generate a balanced list of potential pros and cons for an investor. "
    "Focus on objective facts from the data. Provide 3 pros and 3 cons. "
    "Return ONLY a raw JSON object with two keys: 'pros' and 'cons'. Both keys should hold a list of concise, single-sentence strings."
)

# Initialize the LLM client once to improve performance
LLM = ChatGroq(
    model_name="meta-llama/llama-4-scout-17b-16e-instruct",
    groq_api_key=os.getenv("GROQ_API_KEY"),
    temperature=0.1
)

PROMPT = ChatPromptTemplate.from_template(PROS_CONS_PROMPT_TEMPLATE)
CHAIN = PROMPT | LLM

# --- HELPER FUNCTION ---

def extract_json_from_response(response_text: str) -> Dict[str, Any]:
    """A robust function to find and extract a JSON object from a string."""
    # This pattern is more robust as it captures JSON within markdown code blocks
    match = re.search(r'```json\s*(\{.*?\})\s*```', response_text, re.DOTALL)
    if match:
        return json.loads(match.group(1))
    
    # Fallback for raw JSON objects
    match = re.search(r'(\{.*?\})', response_text, re.DOTALL)
    if match:
        return json.loads(match.group(1))
        
    raise ValueError("No valid JSON object found in the LLM response.")

# --- MAIN AGENT FUNCTION ---

def run_detailed_stock_analysis(ticker: str) -> Dict[str, Any]:
    """
    Runs a detailed, multi-faceted analysis on a single stock ticker,
    including an AI-driven "pros and cons" summary.
    """
    st.session_state.analysis_logs.append(f"--- Running detailed analysis for {ticker} ---")

    try:
        formatted_ticker = f"{ticker.strip().upper()}.NS"
        stock_name = data_fetchers.get_stock_name(formatted_ticker)
        fundamentals = data_fetchers.get_fundamental_data(formatted_ticker)

        if not fundamentals:
            st.session_state.analysis_logs.append(f"Could not fetch fundamental data for {ticker}.")
            raise ValueError(f"Data fetching failed for {ticker}")

        response = CHAIN.invoke({
            "stock_name": stock_name,
            "fundamentals": json.dumps(fundamentals)
        })

        pros_cons = extract_json_from_response(response.content)

        analysis_result = {
            "name": stock_name,
            "fundamentals": fundamentals,
            "pros_cons": pros_cons
        }
        
        st.session_state.analysis_logs.append(f"--- Detailed analysis for {ticker} complete ---")
        return analysis_result

    except Exception as e:
        st.session_state.analysis_logs.append(f"ERROR in detailed analysis for {ticker}: {e}")
        # Return a consistent structure on failure
        return {
            "name": ticker,
            "fundamentals": {},
            "pros_cons": {"pros": ["Analysis failed."], "cons": ["Could not generate AI insights."]}
        }

