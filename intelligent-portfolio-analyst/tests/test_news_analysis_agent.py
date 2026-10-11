from agents.news_analysis_agent import news_analysis_agent
from tests.fakes import FakeLLM


class TestNewsAnalysisAgent:
    def test_corrupt_state_returns_error(self):
        result = news_analysis_agent("not a dict")
        assert "error" in result

    def test_no_stock_results_returns_empty_news(self):
        result = news_analysis_agent({"stock_analysis_results": []})
        assert result == {"news": []}

    def test_uses_yfinance_news_without_needing_newsapi(self, mocker):
        def fake_get_secret(key):
            if key == "GROQ_API_KEY":
                return "fake-groq-key"
            raise KeyError(key)  # NEWS_API_KEY unavailable

        mocker.patch("agents.news_analysis_agent.get_secret", side_effect=fake_get_secret)
        mocker.patch("agents.news_analysis_agent.ChatGroq", return_value=FakeLLM(content="One sentence summary."))
        mocker.patch(
            "agents.news_analysis_agent.data_fetchers.get_stock_news",
            return_value=[{"title": "RIL posts strong results", "link": "http://x", "publisher": "ET", "publish_date": "2024-01-01"}],
        )

        state = {
            "stock_analysis_results": [{"ticker": "RELIANCE", "name": "Reliance Industries"}],
            "analysis_errors": [],
        }
        result = news_analysis_agent(state)

        assert len(result["news"]) == 1
        assert result["news"][0]["ticker"] == "Reliance Industries"
        assert result["news"][0]["articles"][0]["summary"] == "One sentence summary."
        # Missing NEWS_API_KEY should be logged as non-fatal, not abort the step.
        assert any("NewsAPI fallback disabled" in e for e in result["analysis_errors"])

    def test_falls_back_to_newsapi_when_yfinance_has_no_news(self, mocker):
        mocker.patch("agents.news_analysis_agent.get_secret", return_value="fake-key")
        mocker.patch("agents.news_analysis_agent.ChatGroq", return_value=FakeLLM(content="Summary."))
        mocker.patch("agents.news_analysis_agent.data_fetchers.get_stock_news", return_value=[])

        fake_newsapi = mocker.Mock()
        fake_newsapi.get_everything.return_value = {
            "articles": [
                {
                    "title": "Fallback headline",
                    "url": "http://y",
                    "source": {"name": "Reuters"},
                    "publishedAt": "2024-02-01T10:00:00Z",
                }
            ]
        }
        mocker.patch("agents.news_analysis_agent.NewsApiClient", return_value=fake_newsapi)

        state = {
            "stock_analysis_results": [{"ticker": "TCS", "name": "Tata Consultancy Services"}],
            "analysis_errors": [],
        }
        result = news_analysis_agent(state)

        assert len(result["news"]) == 1
        assert result["news"][0]["articles"][0]["title"] == "Fallback headline"

    def test_stock_missing_name_is_skipped(self, mocker):
        mocker.patch("agents.news_analysis_agent.get_secret", return_value="fake-key")
        mocker.patch("agents.news_analysis_agent.ChatGroq", return_value=FakeLLM(content="Summary."))

        state = {
            "stock_analysis_results": [{"ticker": "RELIANCE"}],  # no 'name'
            "analysis_errors": [],
        }
        result = news_analysis_agent(state)
        assert result["news"] == []

    def test_groq_key_missing_aborts_whole_step(self, mocker):
        def raise_for_groq(key):
            raise KeyError(key)

        mocker.patch("agents.news_analysis_agent.get_secret", side_effect=raise_for_groq)

        state = {
            "stock_analysis_results": [{"ticker": "RELIANCE", "name": "Reliance Industries"}],
            "analysis_errors": [],
        }
        result = news_analysis_agent(state)
        assert result["news"] == []
        assert len(result["analysis_errors"]) == 1
