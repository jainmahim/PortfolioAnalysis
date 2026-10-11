from agents.report_generation_agent import report_generation_agent


class TestReportGenerationAgent:
    def test_assembles_final_report_from_state(self):
        state = {
            "stock_analysis_results": [
                {
                    "ticker": "RELIANCE",
                    "invested_value": 10000,
                    "current_value": 12000,
                    "beta": 1.1,
                    "fundamentals": {"sector": "Energy"},
                }
            ],
            "news": [{"ticker": "Reliance Industries", "articles": []}],
            "analysis_errors": ["some warning"],
        }
        result = report_generation_agent(state)

        report = result["final_report"]
        assert report["stock_analysis"] == state["stock_analysis_results"]
        assert report["news"] == state["news"]
        assert report["analysis_errors"] == state["analysis_errors"]
        # Aggregate metrics from utils.portfolio_aggregator are merged in.
        assert report["total_investment"] == 10000
        assert report["current_value"] == 12000

    def test_handles_empty_state_gracefully(self):
        result = report_generation_agent({})
        report = result["final_report"]
        assert report["stock_analysis"] == []
        assert report["news"] == []
        assert report["analysis_errors"] == []
