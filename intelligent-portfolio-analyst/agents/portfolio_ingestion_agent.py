import streamlit as st
from parsers import csv_parser, excel_parser, pdf_parser
from typing import Dict, Any

def portfolio_ingestion_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ingests the user's uploaded portfolio file, determines its type,
    and calls the appropriate parser. Handles parsing failures gracefully.
    """
    st.session_state.analysis_logs.append("---INGESTING PORTFOLIO---")
    
    uploaded_file = state.get('uploaded_file')
    if not uploaded_file:
        return {"error": "No file was uploaded."}

    file_extension = uploaded_file.name.split('.')[-1].lower()
    portfolio_data = None

    try:
        if file_extension == 'csv':
            portfolio_data = csv_parser.parse(uploaded_file)
        elif file_extension == 'xlsx':
            portfolio_data = excel_parser.parse(uploaded_file)
        elif file_extension == 'pdf':
            portfolio_data = pdf_parser.parse(uploaded_file)
        else:
            return {"error": f"Unsupported file type: .{file_extension}"}

        # If the parser returned None, it means parsing failed. We must stop here.
        if portfolio_data is None:
            error_msg = "Failed to parse the uploaded file. Please ensure the format is correct and all required columns are present."
            st.session_state.analysis_logs.append(error_msg)
            return {"error": error_msg}
        
        # If successful, return the parsed data.
        return {"portfolio_data": portfolio_data}

    except Exception as e:
        error_msg = f"An unexpected error occurred during file ingestion: {e}"
        st.session_state.analysis_logs.append(error_msg)
        return {"error": error_msg}

