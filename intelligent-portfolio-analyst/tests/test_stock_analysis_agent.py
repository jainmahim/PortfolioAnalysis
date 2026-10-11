import json

from agents.stock_analysis_agent import stock_analysis_agent, extract_json_from_response
from tests.fakes import FakeLLM


SAMPLE_FUNDAMENTALS = {"P/E Ratio": "24.00", "sector": "Energy"}
SAMPLE_TECHNICALS = {"RSI (14)": "55.00"}
SAMPLE_PRICE_HISTORY = [{"Date": "2024-01-01", "Close": 2500.0}]


def _patch_data_fetchers(mocker, *, fundamentals=SAMPLE_FUNDAMENTALS,
                          technicals=SAMPLE_TECHNICALS,
                          price_history=SAMPLE_PRICE_HISTORY, beta=1.1,
                          name="Reliance Industries"):
    mocker.patch("agents.stock_analysis_agent.data_fetchers.get_stock_name", return_value=name)
    mocker.patch("agents.stock_analysis_agent.data_fetchers.get_fundamental_data", return_value=fundamentals)
    mocker.patch("agents.stock_analysis_agent.data_fetchers.get_technical_data", return_value=technicals)
    mocker.patch("agents.stock_analysis_agent.data_fetchers.get_price_history", return_value=price_history)
    mocker.patch("agents.stock_analysis_agent.data_fetchers.get_beta", return_value=beta)


class TestExtractJsonFromResponse:
    def test_extracts_fenced_json(self):
        text = '```json\n{"recommendation": "Buy"}\n```'
        assert extract_json_from_response(text) == {"recommendation": "Buy"}

    def test_extracts_bare_json(self):
        text = 'Here is the result: {"recommendation": "Hold"} done.'
        assert extract_json_from_response(text) == {"recommendation": "Hold"}

    def test_raises_when_no_json_present(self):
        import pytest
        with pytest.raises(ValueError):
            extract_json_from_response("no json here at all")


class TestStockAnalysisAgent:
    def test_corrupt_state_returns_error(self):
        result = stock_analysis_agent("not a dict")
        assert "error" in result

    def test_no_stocks_returns_empty_results(self, mocker):
        mocker.patch("utils.config.get_secret", return_value="fake-key")
        result = stock_analysis_agent({"portfolio_data": {"stocks": []}})
        assert result["stock_analysis_results"] == []
        assert result["analysis_errors"] == []

    def test_enriches_a_stock_end_to_end(self, mocker):
        _patch_data_fetchers(mocker)
        mocker.patch("agents.stock_analysis_agent.get_secret", return_value="fake-key")

        fake_llm = FakeLLM(
            responses=[
                "Good",  # fundamental verdict
                "Bullish",  # technical verdict
                '```json\n{"recommendation": "Buy", "urgency": "High", "reason": "Strong fundamentals."}\n```',
            ]
        )
        mocker.patch("agents.stock_analysis_agent.ChatGroq", return_value=fake_llm)

        state = {"portfolio_data": {"stocks": [{"ticker": "RELIANCE", "quantity": 10}]}}
        result = stock_analysis_agent(state)

        assert len(result["stock_analysis_results"]) == 1
        stock = result["stock_analysis_results"][0]
        assert stock["name"] == "Reliance Industries"
        assert stock["recommendation"] == "Buy"
        assert stock["urgency"] == "High"
        assert stock["reason"] == "Strong fundamentals."
        assert stock["beta"] == 1.1
        assert result["analysis_errors"] == []

    def test_stock_without_ticker_is_skipped(self, mocker):
        mocker.patch("agents.stock_analysis_agent.get_secret", return_value="fake-key")
        state = {"portfolio_data": {"stocks": [{"quantity": 10}]}}
        result = stock_analysis_agent(state)
        assert result["stock_analysis_results"] == []

    def test_missing_live_data_records_error_and_continues(self, mocker):
        _patch_data_fetchers(mocker, fundamentals={}, technicals={}, price_history={})
        mocker.patch("agents.stock_analysis_agent.get_secret", return_value="fake-key")
        mocker.patch("agents.stock_analysis_agent.ChatGroq", return_value=FakeLLM(content="unused"))

        state = {"portfolio_data": {"stocks": [{"ticker": "BADTICKER"}]}}
        result = stock_analysis_agent(state)

        assert result["stock_analysis_results"] == []
        assert len(result["analysis_errors"]) == 1
        assert "BADTICKER" in result["analysis_errors"][0]

    def test_unparseable_llm_response_falls_back_gracefully(self, mocker):
        _patch_data_fetchers(mocker)
        mocker.patch("agents.stock_analysis_agent.get_secret", return_value="fake-key")

        fake_llm = FakeLLM(
            responses=["Good", "Bullish", "not valid json at all"]
        )
        mocker.patch("agents.stock_analysis_agent.ChatGroq", return_value=fake_llm)

        state = {"portfolio_data": {"stocks": [{"ticker": "RELIANCE"}]}}
        result = stock_analysis_agent(state)

        stock = result["stock_analysis_results"][0]
        assert stock["recommendation"] == "N/A"
        assert stock["reason"] == "AI synthesis failed."

    def test_multiple_stocks_processed_independently(self, mocker):
        _patch_data_fetchers(mocker)
        mocker.patch("agents.stock_analysis_agent.get_secret", return_value="fake-key")

        # Each stock gets a fresh FakeLLM instance via a factory so their
        # response cursors don't interfere with each other.
        def make_llm(*args, **kwargs):
            return FakeLLM(
                responses=[
                    "Good", "Bullish",
                    '```json\n{"recommendation": "Buy", "urgency": "Low", "reason": "ok"}\n```',
                ]
            )

        mocker.patch("agents.stock_analysis_agent.ChatGroq", side_effect=make_llm)

        state = {
            "portfolio_data": {
                "stocks": [{"ticker": "RELIANCE"}, {"ticker": "TCS"}]
            }
        }
        result = stock_analysis_agent(state)
        assert len(result["stock_analysis_results"]) == 2
