from utils.portfolio_aggregator import aggregate_portfolio_metrics


def _stock(invested, current, beta=1.0, sector="IT"):
    return {
        "invested_value": invested,
        "current_value": current,
        "beta": beta,
        "fundamentals": {"sector": sector},
    }


class TestAggregatePortfolioMetrics:
    def test_empty_list_returns_empty_dict(self):
        assert aggregate_portfolio_metrics([]) == {}

    def test_totals_and_pnl(self):
        stocks = [_stock(10000, 12000), _stock(5000, 4000)]
        result = aggregate_portfolio_metrics(stocks)

        assert result["total_investment"] == 15000
        assert result["current_value"] == 16000
        assert result["overall_pnl"] == 1000
        assert round(result["overall_pnl_percent"], 4) == round((1000 / 15000) * 100, 4)

    def test_pnl_percent_is_none_when_no_investment(self):
        # total_investment == 0 guards division by zero.
        stocks = [{"invested_value": 0, "current_value": 0, "beta": 1.0, "fundamentals": {}}]
        result = aggregate_portfolio_metrics(stocks)
        assert result["overall_pnl"] == 0.0
        assert result["overall_pnl_percent"] is None

    def test_risk_profile_conservative_below_point_eight_beta(self):
        stocks = [_stock(10000, 10000, beta=0.5)]
        result = aggregate_portfolio_metrics(stocks)
        assert result["risk_profile"] == "Conservative"

    def test_risk_profile_moderate_growth_in_range(self):
        stocks = [_stock(10000, 10000, beta=1.0)]
        result = aggregate_portfolio_metrics(stocks)
        assert result["risk_profile"] == "Moderate Growth"

    def test_risk_profile_aggressive_above_one_point_two_beta(self):
        stocks = [_stock(10000, 10000, beta=1.5)]
        result = aggregate_portfolio_metrics(stocks)
        assert result["risk_profile"] == "Aggressive"

    def test_risk_profile_is_weighted_by_current_value(self):
        # One large low-beta holding and one small high-beta holding should
        # skew the weighted average toward the larger position.
        stocks = [_stock(1000, 9000, beta=0.5), _stock(1000, 1000, beta=2.0)]
        result = aggregate_portfolio_metrics(stocks)
        # weighted beta = 0.5*0.9 + 2.0*0.1 = 0.65 -> Conservative
        assert result["risk_profile"] == "Conservative"

    def test_sector_allocation_groups_by_sector(self):
        stocks = [
            _stock(1000, 1000, sector="IT"),
            _stock(1000, 2000, sector="IT"),
            _stock(1000, 500, sector="Banking"),
        ]
        result = aggregate_portfolio_metrics(stocks)
        assert result["sector_allocation"]["IT"] == 3000
        assert result["sector_allocation"]["Banking"] == 500

    def test_missing_or_na_sector_falls_back_to_other(self):
        stocks = [
            _stock(1000, 1000, sector="N/A"),
            {"invested_value": 1000, "current_value": 500, "beta": 1.0, "fundamentals": {}},
        ]
        result = aggregate_portfolio_metrics(stocks)
        assert result["sector_allocation"]["Other"] == 1500

    def test_asset_allocation_is_total_current_value(self):
        stocks = [_stock(1000, 1000), _stock(1000, 2000)]
        result = aggregate_portfolio_metrics(stocks)
        assert result["asset_allocation"] == {"Stocks": 3000}
