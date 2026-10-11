import os
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from newsapi import NewsApiClient
import streamlit as st
from typing import Dict, Any
from utils import data_fetchers
from utils.config import get_secret
from utils.llm_retry import invoke_with_retry

def news_analysis_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Implements a robust, hybrid news fetching strategy. It first tries the
    unlimited yfinance source, and only uses the rate-limited NewsAPI as a fallback.
    """
    if not isinstance(state, dict):
        error_msg = f"CRITICAL Error: Agent received corrupt data (type: {type(state)})."
        st.session_state.analysis_logs.append(error_msg)
        return {"error": error_msg}

    st.session_state.analysis_logs.append("---FETCHING & SUMMARIZING NEWS (Hybrid Method)---")
    
    stock_results = state.get('stock_analysis_results', [])
    analysis_errors = state.get('analysis_errors', [])
    
    news_results = []
    
    if not stock_results:
        return {"news": []}

    try:
        # LLM summarization is required; abort the whole step if it can't be configured.
        llm = ChatGroq(
            model_name="meta-llama/llama-4-scout-17b-16e-instruct", 
            groq_api_key=get_secret("GROQ_API_KEY"),
            temperature=0.0
        )
        summary_prompt = ChatPromptTemplate.from_template(
            "Summarize the following news headline into a single, concise, and insightful sentence: {article_title}"
        )
        summary_chain = summary_prompt | llm

        # The NewsAPI fallback is optional: yfinance is the primary source, so a
        # missing/invalid NEWS_API_KEY should only disable the fallback, not the
        # whole news step.
        newsapi = None
        try:
            newsapi = NewsApiClient(api_key=get_secret("NEWS_API_KEY"))
        except Exception as e:
            fallback_unavailable = f"NewsAPI fallback disabled: {e}"
            if fallback_unavailable not in analysis_errors:
                analysis_errors.append(fallback_unavailable)
                st.session_state.analysis_logs.append(fallback_unavailable)

        news_api_rate_limited = newsapi is None

        for stock in stock_results:
            ticker = stock.get('ticker')
            stock_name = stock.get('name')
            if not ticker or not stock_name:
                continue

            try:
                formatted_ticker = f"{ticker}.NS"
                st.session_state.analysis_logs.append(f"Fetching news for {stock_name}...")
                
                # --- Primary Source: yfinance ---
                news_articles = data_fetchers.get_stock_news(formatted_ticker)
                
                # --- Secondary (Fallback) Source: NewsAPI ---
                if not news_articles and not news_api_rate_limited:
                    st.session_state.analysis_logs.append(f"yfinance had no news for {stock_name}. Trying NewsAPI fallback...")
                    try:
                        top_headlines = newsapi.get_everything(q=stock_name, language='en', sort_by='publishedAt', page_size=3)
                        # Reformat the NewsAPI data to match our standard format
                        for article in top_headlines.get('articles', []):
                            news_articles.append({
                                "title": article.get('title'),
                                "link": article.get('url'),
                                "publisher": article.get('source', {}).get('name'),
                                "publish_date": article.get('publishedAt', '').split('T')[0], # Format date
                                "summary": "" # Placeholder
                            })
                    except Exception as e:
                        if 'rateLimited' in str(e):
                            news_api_rate_limited = True
                            rate_limit_error = "NewsAPI fallback unavailable: Daily request limit reached."
                            if rate_limit_error not in analysis_errors:
                                analysis_errors.append(rate_limit_error)
                                st.session_state.analysis_logs.append(rate_limit_error)

                if not news_articles:
                    continue

                news_for_ticker = {"ticker": stock_name, "articles": []}
                
                for article in news_articles[:5]: # Limit total articles
                    title = article.get('title')
                    if not title:
                        continue
                        
                    article_summary = invoke_with_retry(
                        summary_chain,
                        {"article_title": title},
                        logger=st.session_state.analysis_logs.append
                    ).content
                    
                    article['summary'] = article_summary
                    news_for_ticker["articles"].append(article)
                
                if news_for_ticker["articles"]:
                    news_results.append(news_for_ticker)

            except Exception as e:
                st.session_state.analysis_logs.append(f"Could not process news for {stock_name}: {e}")

    except Exception as e:
        error_msg = f"An error occurred during news analysis initialization: {e}"
        st.session_state.analysis_logs.append(error_msg)
        analysis_errors.append(error_msg)

    return {"news": news_results, "analysis_errors": analysis_errors}
