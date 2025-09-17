import os
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
import json
import re
import streamlit as st
from utils import data_fetchers

def run_detailed_stock_analysis(ticker):
    """
    Runs a detailed, multi-faceted analysis on a single stock ticker,
    including an AI-driven "pros and cons" summary.
    """
    st.session_state.analysis_logs.append(f"---STARTING DETAILED ANALYSIS FOR {ticker}---")

    try:
        # 1. Format the ticker and fetch all necessary data in one go
        formatted_ticker = f"{ticker.strip().upper()}.NS"
        stock_name = data_fetchers.get_stock_name(formatted_ticker)
        fundamentals = data_fetchers.get_fundamental_data(formatted_ticker)

        # 2. AI-Powered Pros and Cons Generation
        llm = ChatGroq(
            model_name="meta-llama/llama-4-scout-17b-16e-instruct",
            groq_api_key=os.getenv("GROQ_API_KEY"),
            temperature=0.1
        )
        
        prompt_template = (
            "You are a senior stock analyst reviewing financial data for '{stock_name}'. "
            "Based on the following metrics: {fundamentals}, generate a balanced list of potential pros and cons for an investor. "
            "Focus on objective facts from the data. Provide 3 pros and 3 cons. "
            "Return ONLY a raw JSON object with two keys: 'pros' and 'cons'. Both keys should hold a list of concise, single-sentence strings."
        )
        
        prompt = ChatPromptTemplate.from_template(prompt_template)
        chain = prompt | llm
        
        response = chain.invoke({
            "stock_name": stock_name,
            "fundamentals": json.dumps(fundamentals)
        })

        # Safely parse the AI response
        def extract_json_from_response(response_text):
            match = re.search(r'```json\s*(\{.*?\})\s*```', response_text, re.DOTALL)
            if match:
                return json.loads(match.group(1))
            match = re.search(r'(\{.*?\})', response_text, re.DOTALL)
            if match:
                return json.loads(match.group(1))
            raise ValueError("No valid JSON object found in the LLM response.")

        try:
            pros_cons = extract_json_from_response(response.content)
        except (ValueError, json.JSONDecodeError):
            st.session_state.analysis_logs.append(f"Could not parse pros/cons JSON for {ticker}.")
            pros_cons = {"pros": ["AI analysis failed."], "cons": ["AI analysis failed."]}

        # 3. Assemble the final, comprehensive result
        analysis_result = {
            "name": stock_name,
            "fundamentals": fundamentals,
            "pros_cons": pros_cons
        }
        
        st.session_state.analysis_logs.append(f"---DETAILED ANALYSIS FOR {ticker} COMPLETE---")
        return analysis_result

    except Exception as e:
        st.session_state.analysis_logs.append(f"An error occurred during detailed analysis for {ticker}: {e}")
        return {
            "name": ticker,
            "fundamentals": {},
            "pros_cons": {"pros": ["Data fetching failed."], "cons": ["Data fetching failed."]}
        }

