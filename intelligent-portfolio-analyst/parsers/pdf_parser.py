import pdfplumber
import pandas as pd
import re

# This regex is a generic EXAMPLE and is NOT guaranteed to match any real
# broker's PDF layout. It expects a line of the form:
#   TICKER  QTY  AVG_COST  INVESTED  CUR_VAL  P&L
# e.g. "RELIANCE  10  2,450.00  24,500.00  28,900.00  4,400.00"
#
# You MUST customize this pattern for your broker's actual statement layout
# before relying on PDF import: open a sample statement, inspect the text
# pdfplumber extracts (see the `_debug_dump_text` helper below), and adjust
# the groups/column order/number formats accordingly.
HOLDINGS_LINE_PATTERN = re.compile(
    r"([A-Z&]+)\s+"       # Instrument (Ticker)
    r"(\d+)\s+"           # Qty
    r"([\d,]+\.\d{2})\s+" # Avg. cost
    r"([\d,]+\.\d{2})\s+" # Invested
    r"([\d,]+\.\d{2})\s+" # Cur. val
    r"(-?[\d,]+\.\d{2})"  # P&L
)


def _debug_dump_text(file_content, max_chars: int = 2000) -> str:
    """
    Helper for customizing HOLDINGS_LINE_PATTERN: returns the raw text
    pdfplumber extracts from a statement so you can see what the regex needs
    to match. Not called by `parse()`; use it interactively / in a notebook
    when adapting this parser to a new broker's layout.
    """
    text = ""
    with pdfplumber.open(file_content) as pdf:
        for page in pdf.pages:
            text += (page.extract_text() or "") + "\n"
    return text[:max_chars]


def parse(file_content):
    """
    A template for parsing PDF files, updated to capture all financial columns.
    NOTE: HOLDINGS_LINE_PATTERN MUST be customized for your specific PDF
    statement layout (see the comment above it); this generic pattern is a
    starting point, not a working parser for every broker.
    """
    try:
        text = ""
        with pdfplumber.open(file_content) as pdf:
            if not pdf.pages:
                raise ValueError("The PDF has no pages to parse.")
            for page in pdf.pages:
                # extract_text() returns None for pages with no extractable
                # text (e.g. scanned/image-only pages); guard against that
                # instead of letting `text += None` raise a TypeError.
                text += (page.extract_text() or "") + "\n"

        if not text.strip():
            raise ValueError(
                "No text could be extracted from the PDF. It may be a scanned "
                "image rather than a text-based PDF, which this parser cannot read."
            )

        matches = HOLDINGS_LINE_PATTERN.findall(text)

        if not matches:
            raise ValueError(
                "Could not find any holdings matching the expected layout. "
                "HOLDINGS_LINE_PATTERN in parsers/pdf_parser.py is a generic template "
                "and must be customized for your broker's PDF statement format."
            )

        # Create a list of dictionaries from the matches
        holdings = []
        for match in matches:
            holdings.append({
                'ticker': match[0],
                'quantity': int(match[1]),
                'average_cost': float(match[2].replace(',', '')),
                'invested_value': float(match[3].replace(',', '')),
                'current_value': float(match[4].replace(',', '')),
                'pnl': float(match[5].replace(',', ''))
            })
            
        return {"stocks": holdings}

    except Exception as e:
        print(f"Error parsing PDF file: {e}")
        return None

