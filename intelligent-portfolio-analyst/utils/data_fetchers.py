import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

def get_stock_name(ticker):
    """Fetches the long name of a stock from its ticker."""
    try:
        stock = yf.Ticker(ticker)
        return stock.info.get('longName', ticker)
    except Exception:
        return ticker

def get_beta(ticker):
    """Fetches the beta of a stock."""
    try:
        stock = yf.Ticker(ticker)
        beta = stock.info.get('beta')
        return round(beta, 2) if beta is not None else 1.0
    except Exception:
        return 1.0

def get_fundamental_data(ticker):
    """
    Fetches an expanded set of fundamental data, including the new
    metrics required for the Peter Lynch analysis.
    """
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        pe_ratio = info.get('trailingPE')
        eps = info.get('trailingEps')
        pb_ratio = info.get('priceToBook')
        debt_to_equity = info.get('debtToEquity')
        market_cap = info.get('marketCap')
        sector = info.get('sector')
        
        forward_pe = info.get('forwardPE')
        peg_ratio = info.get('pegRatio')

        return {
            "P/E Ratio": round(pe_ratio, 2) if pe_ratio else 'N/A',
            "Forward P/E Ratio": round(forward_pe, 2) if forward_pe else 'N/A',
            "PEG Ratio": round(peg_ratio, 2) if peg_ratio else 'N/A',
            "EPS": round(eps, 2) if eps else 'N/A',
            "Price-to-Book": round(pb_ratio, 2) if pb_ratio else 'N/A',
            "Debt-to-Equity": round(debt_to_equity / 100, 2) if debt_to_equity else 'N/A',
            "Market Cap": f"Rs.{market_cap:,.0f}" if market_cap else 'N/A',
            "sector": sector or 'N/A'
        }
    except Exception:
        return {}

def get_technical_data(ticker):
    """Fetches key technical indicators for a stock."""
    try:
        data = yf.download(ticker, period="1y", interval="1d", auto_adjust=True)
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
            "50-Day MA": f"Rs.{fifty_day_ma:,.2f}",
            "200-Day MA": f"Rs.{two_hundred_day_ma:,.2f}",
            "RSI (14)": f"{rsi:.2f}"
        }
    except Exception:
        return {}

def get_price_history(ticker, period="5y"):
    """Fetches historical price data for a stock."""
    try:
        data = yf.download(ticker, period=period, auto_adjust=True)
        if data.empty:
            return {}

        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.droplevel(1)

        data.reset_index(inplace=True)
        return data.to_dict("records")
    except Exception:
        return {}

def get_stock_news(ticker):
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

