from langgraph.graph import StateGraph, END
from typing import Dict, Any
from agents.portfolio_ingestion_agent import portfolio_ingestion_agent
from agents.validation_agent import validation_agent
from agents.stock_analysis_agent import stock_analysis_agent
from agents.news_analysis_agent import news_analysis_agent # <-- IMPORT THE CORRECT AGENT
from agents.report_generation_agent import report_generation_agent
import streamlit as st
import traceback

def run_graph(uploaded_file):
    """
    Initializes and runs the analysis workflow, now including the new
    hybrid Personalized News Feed agent.
    """
    # Define the application's state, adding a key for news results
    class AppState(Dict):
        uploaded_file: Any
        portfolio_data: Dict[str, Any]
        stock_analysis_results: Dict[str, Any]
        news: Dict[str, Any] # <-- Key for news results
        final_report: Dict[str, Any]
        error: str
        analysis_errors: list

    workflow = StateGraph(AppState)

    # Add all the nodes, including the new news agent
    workflow.add_node("ingest_portfolio", portfolio_ingestion_agent)
    workflow.add_node("validate_ingestion", validation_agent)
    workflow.add_node("enrich_stocks", stock_analysis_agent)
    workflow.add_node("news_analyzer", news_analysis_agent) # <-- NEW NODE
    workflow.add_node("report_generator", report_generation_agent)

    # Define the updated workflow edges
    workflow.set_entry_point("ingest_portfolio")

    def should_continue(state):
        return "end" if state.get("error") else "continue"

    workflow.add_conditional_edges(
        "ingest_portfolio",
        should_continue,
        {"continue": "validate_ingestion", "end": END}
    )

    workflow.add_conditional_edges(
        "validate_ingestion",
        should_continue,
        {"continue": "enrich_stocks", "end": END}
    )

    # The flow now goes from stock enrichment to the new news analyzer
    workflow.add_edge("enrich_stocks", "news_analyzer")
    workflow.add_edge("news_analyzer", "report_generator")
    workflow.add_edge("report_generator", END)
    
    app = workflow.compile()

    # Initial state
    initial_state = {"uploaded_file": uploaded_file, "analysis_errors": []}
    
    # Use a generator to stream results for real-time log updates
    def stream_workflow():
        try:
            for chunk in app.stream(initial_state):
                yield chunk
        except Exception as e:
            tb_str = traceback.format_exc()
            error_msg = f"A critical error occurred in the analysis engine: {e}\nTraceback:\n{tb_str}"
            st.session_state.analysis_logs.append(error_msg)
            yield {"error": error_msg}
            
    return stream_workflow()

