from utils import data_fetchers


class TestGetStockName:
    def test_returns_long_name(self, mocker):
        fake_ticker = mocker.Mock()
        fake_ticker.info = {"longName": "Reliance Industries Limited"}
        mocker.patch("utils.data_fetchers.yf.Ticker", return_value=fake_ticker)

        assert data_fetchers.get_stock_name("RELIANCE.NS") == "Reliance Industries Limited"

    def test_falls_back_to_ticker_on_exception(self, mocker):
        mocker.patch("utils.data_fetchers.yf.Ticker", side_effect=RuntimeError("down"))
        assert data_fetchers.get_stock_name("RELIANCE.NS") == "RELIANCE.NS"


class TestGetBeta:
    def test_rounds_beta(self, mocker):
        fake_ticker = mocker.Mock()
        fake_ticker.info = {"beta": 1.2345}
        mocker.patch("utils.data_fetchers.yf.Ticker", return_value=fake_ticker)

        assert data_fetchers.get_beta("RELIANCE.NS") == 1.23

    def test_defaults_to_one_when_missing(self, mocker):
        fake_ticker = mocker.Mock()
        fake_ticker.info = {}
        mocker.patch("utils.data_fetchers.yf.Ticker", return_value=fake_ticker)

        assert data_fetchers.get_beta("RELIANCE.NS") == 1.0

    def test_defaults_to_one_on_exception(self, mocker):
        mocker.patch("utils.data_fetchers.yf.Ticker", side_effect=RuntimeError("down"))
        assert data_fetchers.get_beta("RELIANCE.NS") == 1.0


class TestGetFundamentalData:
    def test_formats_known_fields(self, mocker):
        fake_ticker = mocker.Mock()
        fake_ticker.info = {
            "trailingPE": 24.567,
            "trailingEps": 50.1,
            "priceToBook": 3.2,
            "debtToEquity": 35.0,  # yfinance reports this as a percent-like number
            "marketCap": 1_500_000_000,
            "sector": "Energy",
            "forwardPE": 20.1,
            "pegRatio": 1.1,
            "regularMarketPrice": 2500.0,
            "fiftyTwoWeekHigh": 3000.0,
            "fiftyTwoWeekLow": 2000.0,
            "bookValue": 800.0,
            "dividendYield": 0.015,
            "returnOnEquity": 0.18,
        }
        mocker.patch("utils.data_fetchers.yf.Ticker", return_value=fake_ticker)

        result = data_fetchers.get_fundamental_data("RELIANCE.NS")

        assert result["P/E Ratio"] == "24.57"
        assert result["sector"] == "Energy"
        assert result["Debt-to-Equity"] == "0.35"
        assert result["Dividend Yield"] == "1.50%"
        assert result["ROE"] == "18.00%"
        assert result["Current Price"] == "Rs.2,500.00"

    def test_missing_fields_become_na(self, mocker):
        fake_ticker = mocker.Mock()
        fake_ticker.info = {}
        mocker.patch("utils.data_fetchers.yf.Ticker", return_value=fake_ticker)

        result = data_fetchers.get_fundamental_data("RELIANCE.NS")
        assert all(v == "N/A" for v in result.values())

    def test_exception_returns_na_fallback_dict(self, mocker):
        mocker.patch("utils.data_fetchers.yf.Ticker", side_effect=RuntimeError("down"))
        result = data_fetchers.get_fundamental_data("RELIANCE.NS")
        assert result["P/E Ratio"] == "N/A"
        assert result["sector"] == "N/A"


class TestGetTechnicalData:
    def test_empty_data_returns_empty_dict(self, mocker):
        import pandas as pd

        mocker.patch("utils.data_fetchers.yf.download", return_value=pd.DataFrame())
        assert data_fetchers.get_technical_data("RELIANCE.NS") == {}

    def test_exception_returns_empty_dict(self, mocker):
        mocker.patch("utils.data_fetchers.yf.download", side_effect=RuntimeError("down"))
        assert data_fetchers.get_technical_data("RELIANCE.NS") == {}


class TestGetPriceHistory:
    def test_empty_data_returns_empty_dict(self, mocker):
        import pandas as pd

        mocker.patch("utils.data_fetchers.yf.download", return_value=pd.DataFrame())
        assert data_fetchers.get_price_history("RELIANCE.NS") == {}

    def test_exception_returns_empty_dict(self, mocker):
        mocker.patch("utils.data_fetchers.yf.download", side_effect=RuntimeError("down"))
        assert data_fetchers.get_price_history("RELIANCE.NS") == {}


class TestGetStockNews:
    def test_filters_to_recent_news_only(self, mocker):
        from datetime import datetime, timedelta

        now = datetime.now()
        recent_ts = (now - timedelta(days=5)).timestamp()
        old_ts = (now - timedelta(days=90)).timestamp()

        fake_ticker = mocker.Mock()
        fake_ticker.news = [
            {
                "title": "Recent headline",
                "link": "http://a",
                "publisher": "ET",
                "providerPublishTime": recent_ts,
            },
            {
                "title": "Old headline",
                "link": "http://b",
                "publisher": "ET",
                "providerPublishTime": old_ts,
            },
        ]
        mocker.patch("utils.data_fetchers.yf.Ticker", return_value=fake_ticker)

        result = data_fetchers.get_stock_news("RELIANCE.NS")
        assert len(result) == 1
        assert result[0]["title"] == "Recent headline"

    def test_exception_returns_empty_list(self, mocker):
        mocker.patch("utils.data_fetchers.yf.Ticker", side_effect=RuntimeError("down"))
        assert data_fetchers.get_stock_news("RELIANCE.NS") == []
