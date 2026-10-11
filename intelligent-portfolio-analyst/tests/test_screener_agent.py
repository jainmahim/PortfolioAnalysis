from agents.screener_agent import run_detailed_stock_analysis
from tests.fakes import FakeLLM


class TestRunDetailedStockAnalysis:
    def test_happy_path_returns_pros_and_cons(self, mocker):
        mocker.patch("agents.screener_agent.get_secret", return_value="fake-key")
        mocker.patch(
            "agents.screener_agent.data_fetchers.get_stock_name",
            return_value="Reliance Industries",
        )
        mocker.patch(
            "agents.screener_agent.data_fetchers.get_fundamental_data",
            return_value={"P/E Ratio": "24.00", "sector": "Energy"},
        )
        mocker.patch(
            "agents.screener_agent.ChatGroq",
            return_value=FakeLLM(
                content='```json\n{"pros": ["Strong revenue"], "cons": ["High debt"]}\n```'
            ),
        )

        result = run_detailed_stock_analysis("reliance")

        assert result["name"] == "Reliance Industries"
        assert result["fundamentals"]["sector"] == "Energy"
        assert result["pros_cons"] == {"pros": ["Strong revenue"], "cons": ["High debt"]}

    def test_unparseable_llm_response_falls_back(self, mocker):
        mocker.patch("agents.screener_agent.get_secret", return_value="fake-key")
        mocker.patch("agents.screener_agent.data_fetchers.get_stock_name", return_value="TCS")
        mocker.patch("agents.screener_agent.data_fetchers.get_fundamental_data", return_value={})
        mocker.patch("agents.screener_agent.ChatGroq", return_value=FakeLLM(content="not json"))

        result = run_detailed_stock_analysis("tcs")

        assert result["pros_cons"]["pros"] == ["AI analysis failed."]

    def test_exception_returns_graceful_failure_result(self, mocker):
        mocker.patch(
            "agents.screener_agent.data_fetchers.get_stock_name",
            side_effect=RuntimeError("network down"),
        )

        result = run_detailed_stock_analysis("badticker")

        assert result["name"] == "badticker"
        assert result["pros_cons"]["pros"] == ["Data fetching failed."]

    def test_ticker_is_normalized_before_formatting(self, mocker):
        mocker.patch("agents.screener_agent.get_secret", return_value="fake-key")
        name_mock = mocker.patch(
            "agents.screener_agent.data_fetchers.get_stock_name", return_value="Infosys"
        )
        mocker.patch("agents.screener_agent.data_fetchers.get_fundamental_data", return_value={})
        mocker.patch(
            "agents.screener_agent.ChatGroq",
            return_value=FakeLLM(content='{"pros": [], "cons": []}'),
        )

        run_detailed_stock_analysis("  infy ")

        name_mock.assert_called_once_with("INFY.NS")
