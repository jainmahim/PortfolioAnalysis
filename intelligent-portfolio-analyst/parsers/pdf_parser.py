import pdfplumber
import pandas as pd
import re

def parse(file_content):
    """
    A template for parsing PDF files, updated to capture all financial columns.
    NOTE: The regex pattern MUST be customized for your specific PDF statement layout.
    """
    try:
        text = ""
        with pdfplumber.open(file_content) as pdf:
            for page in pdf.pages:
                text += page.extract_text() + "\n"
        
        # This regex is a generic example. You WILL need to modify it.
        # It looks for lines with a ticker, numbers for qty, cost, invested, value, and p&l.
        pattern = re.compile(
            r"([A-Z&]+)\s+"      # Instrument (Ticker)
            r"(\d+)\s+"          # Qty
            r"([\d,]+\.\d{2})\s+" # Avg. cost
            r"([\d,]+\.\d{2})\s+" # Invested
            r"([\d,]+\.\d{2})\s+" # Cur. val
            r"(-?[\d,]+\.\d{2})" # P&L
        )
        
        matches = pattern.findall(text)
        
        if not matches:
            raise ValueError("Could not find any holdings in the PDF that match the expected format.")
            
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

