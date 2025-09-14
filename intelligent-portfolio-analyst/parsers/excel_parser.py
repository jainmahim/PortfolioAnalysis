import pandas as pd

def parse(file_content):
    """
    Parses the uploaded Excel file, capturing all financial columns provided
    by the user to use as the primary source of truth.
    """
    try:
        # Read the entire Excel file into a DataFrame
        df = pd.read_excel(file_content)

        # --- Data Cleaning and Validation ---
        # Standardize column names for consistency
        df.columns = df.columns.str.strip().str.replace('.', '', regex=False).str.replace(' ', '_').str.lower()

        # Define the full set of columns we will now use from the file
        required_cols = {
            'instrument': 'ticker', 
            'qty': 'quantity', 
            'avg_cost': 'average_cost',
            'invested': 'invested_value',
            'cur_val': 'current_value',
            'p&l': 'pnl'
        }
        
        # Rename the columns to our internal standard
        df.rename(columns=required_cols, inplace=True)

        # Validate that all these essential columns exist in the file
        if not all(col in df.columns for col in required_cols.values()):
            raise ValueError("Excel file is missing required columns. Please ensure it contains: 'Instrument', 'Qty', 'Avg. cost', 'Invested', 'Cur. val', and 'P&L'.")

        # Convert the DataFrame to a list of dictionaries
        holdings = df.to_dict('records')
        
        return {"stocks": holdings}

    except Exception as e:
        print(f"Error parsing Excel file: {e}")
        return None

