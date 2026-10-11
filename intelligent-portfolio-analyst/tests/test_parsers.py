import io

from parsers import csv_parser, excel_parser, pdf_parser


CSV_HEADER = "Instrument,Qty,Avg. cost,Invested,Cur. val,P&L\n"


def _csv_file(body: str):
    return io.BytesIO((CSV_HEADER + body).encode("utf-8"))


class TestCsvParser:
    def test_parses_valid_csv_into_stocks(self):
        content = _csv_file("RELIANCE,10,2450.00,24500.00,28900.00,4400.00\n")
        result = csv_parser.parse(content)

        assert result is not None
        assert len(result["stocks"]) == 1
        stock = result["stocks"][0]
        assert stock["ticker"] == "RELIANCE"
        assert stock["quantity"] == 10
        assert stock["average_cost"] == 2450.00
        assert stock["invested_value"] == 24500.00
        assert stock["current_value"] == 28900.00
        assert stock["pnl"] == 4400.00

    def test_parses_multiple_rows(self):
        content = _csv_file(
            "RELIANCE,10,2450.00,24500.00,28900.00,4400.00\n"
            "TCS,5,3200.00,16000.00,17500.00,1500.00\n"
        )
        result = csv_parser.parse(content)
        assert len(result["stocks"]) == 2
        assert {s["ticker"] for s in result["stocks"]} == {"RELIANCE", "TCS"}

    def test_missing_required_column_returns_none(self):
        bad_content = io.BytesIO(
            b"Instrument,Qty,Avg. cost,Invested,Cur. val\n"
            b"RELIANCE,10,2450.00,24500.00,28900.00\n"
        )
        result = csv_parser.parse(bad_content)
        assert result is None

    def test_malformed_csv_returns_none_not_raises(self):
        garbage = io.BytesIO(b"not,a,valid\xffcsv\x00file")
        result = csv_parser.parse(garbage)
        assert result is None

    def test_header_matching_is_case_and_format_tolerant(self):
        # Mixed case / extra whitespace, matching README's stated tolerance.
        content = io.BytesIO(
            b" INSTRUMENT , QTY ,AVG. COST,INVESTED,CUR. VAL,P&L\n"
            b"INFY,20,1500.50,30010.00,32000.00,1989.50\n"
        )
        result = csv_parser.parse(content)
        assert result is not None
        assert result["stocks"][0]["ticker"] == "INFY"


class TestExcelParser:
    def test_parses_valid_xlsx_into_stocks(self, tmp_path):
        import pandas as pd

        df = pd.DataFrame(
            [
                {
                    "Instrument": "HDFCBANK",
                    "Qty": 15,
                    "Avg. cost": 1600.00,
                    "Invested": 24000.00,
                    "Cur. val": 25500.00,
                    "P&L": 1500.00,
                }
            ]
        )
        xlsx_path = tmp_path / "holdings.xlsx"
        df.to_excel(xlsx_path, index=False)

        with open(xlsx_path, "rb") as f:
            result = excel_parser.parse(f)

        assert result is not None
        stock = result["stocks"][0]
        assert stock["ticker"] == "HDFCBANK"
        assert stock["quantity"] == 15

    def test_missing_required_column_returns_none(self, tmp_path):
        import pandas as pd

        df = pd.DataFrame([{"Instrument": "HDFCBANK", "Qty": 15}])
        xlsx_path = tmp_path / "bad.xlsx"
        df.to_excel(xlsx_path, index=False)

        with open(xlsx_path, "rb") as f:
            result = excel_parser.parse(f)

        assert result is None

    def test_invalid_file_returns_none_not_raises(self):
        garbage = io.BytesIO(b"this is not an xlsx file")
        result = excel_parser.parse(garbage)
        assert result is None


class TestPdfParser:
    def test_returns_none_when_no_pages_match_pattern(self, mocker):
        fake_page = mocker.Mock()
        fake_page.extract_text.return_value = "Nothing resembling a holdings line here."
        fake_pdf = mocker.MagicMock()
        fake_pdf.pages = [fake_page]
        fake_pdf.__enter__.return_value = fake_pdf

        mocker.patch("parsers.pdf_parser.pdfplumber.open", return_value=fake_pdf)

        result = pdf_parser.parse(io.BytesIO(b"%PDF-fake"))
        assert result is None

    def test_parses_matching_lines(self, mocker):
        fake_page = mocker.Mock()
        fake_page.extract_text.return_value = (
            "RELIANCE 10 2,450.00 24,500.00 28,900.00 4,400.00"
        )
        fake_pdf = mocker.MagicMock()
        fake_pdf.pages = [fake_page]
        fake_pdf.__enter__.return_value = fake_pdf

        mocker.patch("parsers.pdf_parser.pdfplumber.open", return_value=fake_pdf)

        result = pdf_parser.parse(io.BytesIO(b"%PDF-fake"))
        assert result is not None
        stock = result["stocks"][0]
        assert stock["ticker"] == "RELIANCE"
        assert stock["quantity"] == 10
        assert stock["pnl"] == 4400.00

    def test_handles_image_only_page_without_crashing(self, mocker):
        # extract_text() returns None on pages with no extractable text
        # (e.g. scanned images); the parser must not crash with a TypeError.
        fake_page = mocker.Mock()
        fake_page.extract_text.return_value = None
        fake_pdf = mocker.MagicMock()
        fake_pdf.pages = [fake_page]
        fake_pdf.__enter__.return_value = fake_pdf

        mocker.patch("parsers.pdf_parser.pdfplumber.open", return_value=fake_pdf)

        result = pdf_parser.parse(io.BytesIO(b"%PDF-fake"))
        assert result is None

    def test_no_pages_returns_none(self, mocker):
        fake_pdf = mocker.MagicMock()
        fake_pdf.pages = []
        fake_pdf.__enter__.return_value = fake_pdf

        mocker.patch("parsers.pdf_parser.pdfplumber.open", return_value=fake_pdf)

        result = pdf_parser.parse(io.BytesIO(b"%PDF-fake"))
        assert result is None
