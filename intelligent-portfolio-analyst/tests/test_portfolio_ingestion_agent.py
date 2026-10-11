from agents.portfolio_ingestion_agent import portfolio_ingestion_agent


class FakeUploadedFile:
    """Minimal stand-in for Streamlit's UploadedFile (only `.name` is used)."""

    def __init__(self, name):
        self.name = name


class TestPortfolioIngestionAgent:
    def test_no_file_uploaded_errors(self):
        result = portfolio_ingestion_agent({"uploaded_file": None})
        assert "error" in result

    def test_unsupported_extension_errors(self):
        state = {"uploaded_file": FakeUploadedFile("holdings.txt")}
        result = portfolio_ingestion_agent(state)
        assert "error" in result
        assert "Unsupported file type" in result["error"]

    def test_csv_dispatches_to_csv_parser(self, mocker):
        mocker.patch(
            "agents.portfolio_ingestion_agent.csv_parser.parse",
            return_value={"stocks": [{"ticker": "RELIANCE"}]},
        )
        state = {"uploaded_file": FakeUploadedFile("holdings.csv")}
        result = portfolio_ingestion_agent(state)
        assert result == {"portfolio_data": {"stocks": [{"ticker": "RELIANCE"}]}}

    def test_xlsx_dispatches_to_excel_parser(self, mocker):
        mocker.patch(
            "agents.portfolio_ingestion_agent.excel_parser.parse",
            return_value={"stocks": [{"ticker": "TCS"}]},
        )
        state = {"uploaded_file": FakeUploadedFile("holdings.xlsx")}
        result = portfolio_ingestion_agent(state)
        assert result == {"portfolio_data": {"stocks": [{"ticker": "TCS"}]}}

    def test_pdf_dispatches_to_pdf_parser(self, mocker):
        mocker.patch(
            "agents.portfolio_ingestion_agent.pdf_parser.parse",
            return_value={"stocks": [{"ticker": "INFY"}]},
        )
        state = {"uploaded_file": FakeUploadedFile("holdings.pdf")}
        result = portfolio_ingestion_agent(state)
        assert result == {"portfolio_data": {"stocks": [{"ticker": "INFY"}]}}

    def test_parser_returning_none_surfaces_error(self, mocker):
        mocker.patch(
            "agents.portfolio_ingestion_agent.csv_parser.parse", return_value=None
        )
        state = {"uploaded_file": FakeUploadedFile("holdings.csv")}
        result = portfolio_ingestion_agent(state)
        assert "error" in result

    def test_parser_raising_exception_is_caught(self, mocker):
        mocker.patch(
            "agents.portfolio_ingestion_agent.csv_parser.parse",
            side_effect=RuntimeError("boom"),
        )
        state = {"uploaded_file": FakeUploadedFile("holdings.csv")}
        result = portfolio_ingestion_agent(state)
        assert "error" in result
        assert "boom" in result["error"]

    def test_extension_matching_is_case_insensitive(self, mocker):
        mocker.patch(
            "agents.portfolio_ingestion_agent.csv_parser.parse",
            return_value={"stocks": []},
        )
        state = {"uploaded_file": FakeUploadedFile("holdings.CSV")}
        result = portfolio_ingestion_agent(state)
        assert "portfolio_data" in result
