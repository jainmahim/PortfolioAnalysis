import os
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
import json
import re
import streamlit as st
from utils import data_fetchers

def get_llm_response(llm, prompt_template, **kwargs):
    """A helper function to get a response from the LLM with flexible inputs."""
    prompt = ChatPromptTemplate.from_template(prompt_template)
    chain = prompt | llm
    response = chain.invoke(kwargs)
    return response.content.strip()

def extract_json_from_response(response_text):
    """A robust function to find and extract a JSON object from a string."""
    match = re.search(r'```json\s*(\{.*?\})\s*```', response_text, re.DOTALL)
    if match:
        return json.loads(match.group(1))
    match = re.search(r'(\{.*?\})', response_text, re.DOTALL)
    if match:
        return json.loads(match.group(1))
    raise ValueError("No valid JSON object found in the LLM response.")

def stock_analysis_agent(state):
    """
    Performs a robust, sequential, "Chain of Thought" analysis for each stock,
    mirroring a human analyst's workflow for maximum reliability and insight.
    """
    if not isinstance(state, dict):
        error_msg = f"CRITICAL Error: Agent received corrupt data (type: {type(state)})."
        st.session_state.analysis_logs.append(error_msg)
        return {"error": error_msg}

    st.session_state.analysis_logs.append("---ENRICHING STOCK DATA---")
    
    portfolio_data = state.get('portfolio_data', {})
    stocks_to_analyze = portfolio_data.get('stocks', [])
    analysis_errors = state.get('analysis_errors', [])

    enriched_stock_results = []
    
    # Process stocks one by one (sequentially) for stability
    for stock_data in stocks_to_analyze:
        ticker = stock_data.get('ticker')
        if not ticker:
            continue
            
        formatted_ticker = f"{ticker}.NS"
        st.session_state.analysis_logs.append(f"Analyzing {formatted_ticker}...")
        
        try:
            # 1. Data Gathering (now includes Peter Lynch metrics)
            stock_name = data_fetchers.get_stock_name(formatted_ticker)
            fundamentals = data_fetchers.get_fundamental_data(formatted_ticker)
            technicals = data_fetchers.get_technical_data(formatted_ticker)
            price_history = data_fetchers.get_price_history(formatted_ticker)
            beta = data_fetchers.get_beta(formatted_ticker)
            
            # Circuit Breaker: If live data fails, stop analysis for this stock
            if not fundamentals or not technicals or not price_history:
                raise ValueError("Live market data could not be retrieved from the provider.")

            # 2. Chain of Thought AI Analysis
            llm = ChatGroq(
                model_name="meta-llama/llama-4-scout-17b-16e-instruct", 
                groq_api_key=os.getenv("GROQ_API_KEY"),
                temperature=0.0
            )

            # Step 1: Fundamental Verdict
            fundamental_prompt = "Based on these fundamentals: {data}, is the company's financial health Good, Neutral, or Poor?"
            fundamental_verdict = get_llm_response(llm, prompt_template=fundamental_prompt, data=fundamentals)

            # Step 2: Technical Verdict
            technical_prompt = "Based on these technical indicators: {data}, is the current market sentiment Bullish, Neutral, or Bearish?"
            technical_verdict = get_llm_response(llm, prompt_template=technical_prompt, data=technicals)

            # Step 3: Final Synthesis
            synthesis_prompt = ChatPromptTemplate.from_template(
                "You are a Senior Analyst. Synthesize the data below. "
                "Data: Fundamental Verdict: {fundamental_verdict}, Technical Verdict: {technical_verdict}, Beta: {beta}. "
                "Return ONLY a raw JSON with keys 'recommendation', 'urgency', and 'reason'."
            )
            synthesis_chain = synthesis_prompt | llm
            final_response = synthesis_chain.invoke({
                "fundamental_verdict": fundamental_verdict,
                "technical_verdict": technical_verdict,
                "beta": beta
            })

            # Safely parse the final JSON response
            try:
                ai_analysis = extract_json_from_response(final_response.content)
            except (ValueError, json.JSONDecodeError) as e:
                st.session_state.analysis_logs.append(f"Could not parse final AI response for {ticker}: {e}")
                ai_analysis = {}

            enriched_stock = stock_data.copy()
            enriched_stock.update({
                "name": stock_name,
                "recommendation": ai_analysis.get('recommendation', 'N/A'),
                "urgency": ai_analysis.get('urgency', 'N/A'),
                "reason": ai_analysis.get('reason', 'AI synthesis failed.'),
                "fundamentals": fundamentals, "technicals": technicals,
                "price_history": price_history, "beta": beta
            })
            enriched_stock_results.append(enriched_stock)

        except Exception as e:
            error_message = f"Could not process stock {ticker}: {e}"
            st.session_state.analysis_logs.append(error_message)
            analysis_errors.append(error_message)

    return {
        "stock_analysis_results": enriched_stock_results,
        "analysis_errors": analysis_errors
    }

