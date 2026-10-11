from agents.validation_agent import validation_agent


class TestValidationAgent:
    def test_valid_portfolio_data_passes(self):
        state = {"portfolio_data": {"stocks": [{"ticker": "RELIANCE"}]}}
        result = validation_agent(state)
        assert result == {}

    def test_non_dict_portfolio_data_errors(self):
        state = {"portfolio_data": ["not", "a", "dict"]}
        result = validation_agent(state)
        assert "error" in result

    def test_missing_portfolio_data_errors(self):
        result = validation_agent({})
        assert "error" in result

    def test_missing_stocks_key_errors(self):
        state = {"portfolio_data": {"not_stocks": []}}
        result = validation_agent(state)
        assert "error" in result

    def test_stocks_not_a_list_errors(self):
        state = {"portfolio_data": {"stocks": "RELIANCE"}}
        result = validation_agent(state)
        assert "error" in result

    def test_empty_stocks_list_errors(self):
        state = {"portfolio_data": {"stocks": []}}
        result = validation_agent(state)
        assert "error" in result
