import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Any, List

# --- Caching ensures we don't re-fetch the same data repeatedly ---

@st.cache_data(ttl=3600)  # Cache for 1 hour
def get_stock_name(ticker: str) -> str:
    """Fetches the long name of a stock from its ticker."""
    try:
        stock = yf.Ticker(ticker)
        return stock.info.get('longName', ticker)
    except Exception:
        return ticker

@st.cache_data(ttl=3600)
def get_beta(ticker: str) -> float:
    """Fetches the beta of a stock, defaulting to 1.0 on failure."""
    try:
        stock = yf.Ticker(ticker)
        beta = stock.info.get('beta')
        return round(beta, 2) if beta is not None else 1.0
    except Exception:
        return 1.0

@st.cache_data(ttl=900) # Cache fundamental data for 15 minutes
def get_fundamental_data(ticker: str) -> Dict[str, Any]:
    """
    Fetches an expanded set of raw fundamental data for a stock.
    Formatting is handled by the UI layer.
    """
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        return {
            "P/E Ratio": info.get('trailingPE'),
            "Forward P/E Ratio": info.get('forwardPE'),
            "PEG Ratio": info.get('pegRatio'),
            "EPS": info.get('trailingEps'),
            "Price-to-Book": info.get('priceToBook'),
            "Debt-to-Equity": info.get('debtToEquity'),
            "Market Cap": info.get('marketCap'),
            "sector": info.get('sector'),
            "Current Price": info.get('regularMarketPrice') or info.get('currentPrice'),
            "High / Low": (info.get('fiftyTwoWeekHigh'), info.get('fiftyTwoWeekLow')),
            "Book Value": info.get('bookValue'),
            "Dividend Yield": info.get('dividendYield'),
            "ROE": info.get('returnOnEquity'),
            "ROCE": info.get('returnOnAssets'), # Using ROA as a proxy for ROCE
            "Face Value": info.get('faceValue')
        }
    except Exception:
        return {}

@st.cache_data(ttl=900) # Cache technical data for 15 minutes
def get_technical_data(ticker: str) -> Dict[str, Any]:
    """Fetches key raw technical indicators for a stock."""
    try:
        data = yf.download(ticker, period="1y", interval="1d", auto_adjust=True, progress=False)
        if data.empty:
            return {}
            
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.droplevel(1)

        fifty_day_ma = data['Close'].rolling(window=50).mean().iloc[-1]
        two_hundred_day_ma = data['Close'].rolling(window=200).mean().iloc[-1]
        
        delta = data['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs)).iloc[-1]

        return {
            "50-Day MA": fifty_day_ma,
            "200-Day MA": two_hundred_day_ma,
            "RSI (14)": rsi
        }
    except Exception:
        return {}

@st.cache_data(ttl=900) # Cache price history for 15 minutes
def get_price_history(ticker: str, period: str = "5y", interval: str = "1d") -> List[Dict[str, Any]]:
    """Fetches historical price data for a stock and calculates MAs."""
    try:
        data = yf.download(ticker, period=period, interval=interval, auto_adjust=True, progress=False)
        if data.empty:
            return []

        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.droplevel(1)

        data['50-Day MA'] = data['Close'].rolling(window=50).mean()
        data['200-Day MA'] = data['Close'].rolling(window=200).mean()
        
        data.reset_index(inplace=True)
        if 'Datetime' in data.columns:
            data.rename(columns={'Datetime': 'Date'}, inplace=True)
            
        return data.to_dict("records")
    except Exception:
        return []

@st.cache_data(ttl=3600) # Cache news for 1 hour
def get_stock_news(ticker: str) -> List[Dict[str, Any]]:
    """Fetches recent news for a stock directly from yfinance."""
    try:
        stock = yf.Ticker(ticker)
        news_list = stock.news
        
        two_months_ago = datetime.now() - timedelta(days=60)
        
        recent_news = []
        for news_item in news_list:
            publish_time = datetime.fromtimestamp(news_item['providerPublishTime'])
            if publish_time > two_months_ago:
                recent_news.append({
                    "title": news_item.get('title'),
                    "link": news_item.get('link'),
                    "publisher": news_item.get('publisher'),
                    "publish_date": publish_time.strftime('%Y-%m-%d'),
                    "summary": ""
                })
        return recent_news
    except Exception:
        return []
