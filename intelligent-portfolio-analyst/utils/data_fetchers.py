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
    metrics required for the Peter Lynch analysis and the new screener.
    """
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        # Fetch raw values safely using .get()
        pe_ratio = info.get('trailingPE')
        eps = info.get('trailingEps')
        pb_ratio = info.get('priceToBook')
        debt_to_equity = info.get('debtToEquity')
        market_cap = info.get('marketCap')
        sector = info.get('sector')
        forward_pe = info.get('forwardPE')
        peg_ratio = info.get('pegRatio')
        current_price = info.get('regularMarketPrice') or info.get('currentPrice')
        fifty_two_week_high = info.get('fiftyTwoWeekHigh')
        fifty_two_week_low = info.get('fiftyTwoWeekLow')
        book_value = info.get('bookValue')
        dividend_yield = info.get('dividendYield')
        roe = info.get('returnOnEquity')

        # Safely perform calculations only if the source value is not None
        debt_to_equity_val = (debt_to_equity / 100) if debt_to_equity is not None else None
        dividend_yield_val = (dividend_yield * 100) if dividend_yield is not None else None
        roe_val = (roe * 100) if roe is not None else None

        # Return the formatted dictionary, checking each value before formatting
        return {
            "P/E Ratio": f"{pe_ratio:.2f}" if pe_ratio is not None else 'N/A',
            "Forward P/E Ratio": f"{forward_pe:.2f}" if forward_pe is not None else 'N/A',
            "PEG Ratio": f"{peg_ratio:.2f}" if peg_ratio is not None else 'N/A',
            "EPS": f"{eps:.2f}" if eps is not None else 'N/A',
            "Price-to-Book": f"{pb_ratio:.2f}" if pb_ratio is not None else 'N/A',
            "Debt-to-Equity": f"{debt_to_equity_val:.2f}" if debt_to_equity_val is not None else 'N/A',
            "Market Cap": f"Rs.{market_cap:,.0f}" if market_cap is not None else 'N/A',
            "sector": sector or 'N/A',
            
            "Current Price": f"Rs.{current_price:,.2f}" if current_price is not None else 'N/A',
            "High / Low": f"Rs.{fifty_two_week_high:,.2f} / Rs.{fifty_two_week_low:,.2f}" if fifty_two_week_high is not None and fifty_two_week_low is not None else 'N/A',
            "Book Value": f"Rs.{book_value:,.2f}" if book_value is not None else 'N/A',
            "Dividend Yield": f"{dividend_yield_val:.2f}%" if dividend_yield_val is not None else 'N/A',
            "ROE": f"{roe_val:.2f}%" if roe_val is not None else 'N/A'
        }
    except Exception:
        # Fallback in case of a major yfinance error
        return {
            "P/E Ratio": 'N/A', "Forward P/E Ratio": 'N/A', "PEG Ratio": 'N/A',
            "EPS": 'N/A', "Price-to-Book": 'N/A', "Debt-to-Equity": 'N/A',
            "Market Cap": 'N/A', "sector": 'N/A', "Current Price": 'N/A',
            "High / Low": 'N/A', "Book Value": 'N/A', "Dividend Yield": 'N/A',
            "ROE": 'N/A'
        }

def get_technical_data(ticker):
    """Fetches key technical indicators for a stock."""
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
            "50-Day MA": f"Rs.{fifty_day_ma:,.2f}",
            "200-Day MA": f"Rs.{two_hundred_day_ma:,.2f}",
            "RSI (14)": f"{rsi:.2f}"
        }
    except Exception:
        return {}

def get_price_history(ticker, period="5y", interval="1d"):
    """Fetches historical price data for a stock."""
    try:
        data = yf.download(ticker, period=period, interval=interval, auto_adjust=True, progress=False)
        if data.empty:
            return {}

        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.droplevel(1)

        data['50-Day MA'] = data['Close'].rolling(window=50).mean()
        data['200-Day MA'] = data['Close'].rolling(window=200).mean()
        
        data.reset_index(inplace=True)
        if 'Datetime' in data.columns:
            data.rename(columns={'Datetime': 'Date'}, inplace=True)
            
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

