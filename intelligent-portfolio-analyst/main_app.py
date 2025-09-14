import streamlit as st
import pandas as pd
import plotly.express as px
from dotenv import load_dotenv
from graph.graph_orchestrator import run_graph
from agents.screener_agent import run_screener
from utils.portfolio_aggregator import aggregate_portfolio_metrics
from utils import data_fetchers
import time

# --- UI DISPLAY FUNCTIONS ---

def setup_tabs(data):
    """Creates the final, multi-tab layout."""
    tab_names = ["Dashboard", "Stock Deep-Dive", "Personalized News", "What If? Analysis", "Personalized Stock Screener"]
    tab1, tab2, tab3, tab4, tab5 = st.tabs(tab_names)
    
    with tab1:
        display_dashboard(data)
    with tab2:
        display_stock_deep_dive(data)
    with tab3:
        display_news_feed(data)
    with tab4:
        display_what_if_analysis(data.get('stock_analysis', []))
    with tab5:
        display_screener()

def display_dashboard(data):
    """
    Displays the main dashboard with a cleaner, more readable layout.
    """
    st.header("Dashboard: 360° View")

    total_investment = data.get('total_investment', 0)
    current_value = data.get('current_value', 0)
    pnl = data.get('overall_pnl', 0)
    pnl_percent = data.get('overall_pnl_percent', 0)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Investment", f"Rs.{total_investment:,.2f}")
    col2.metric("Current Value", f"Rs.{current_value:,.2f}")
    col3.metric("Profit/Loss", f"Rs.{pnl:,.2f}", f"{pnl_percent:.2f}%" if pnl_percent is not None else "")
    col4.metric("Risk Profile", data.get('risk_profile', 'N/A'))

    st.divider()
    
    # Row for Allocation Charts
    col1, col2 = st.columns(2) 
    
    with col1:
        st.subheader("Ideal Sector Allocation")
        ideal_allocation_data = {
            'Sector': ['Financials', 'IT', 'Consumer Goods', 'Healthcare', 'Energy', 'Industrials', 'Materials', 'Utilities'],
            'Value': [25, 15, 15, 10, 10, 10, 5, 10]
        }
        ideal_df = pd.DataFrame(ideal_allocation_data)
        fig = px.pie(ideal_df, names='Sector', values='Value', hole=0.4, title=" ")
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Your Sector Allocation")
        sector_allocation = data.get('sector_allocation', {})
        if sector_allocation and sum(sector_allocation.values()) > 0:
            sector_df = pd.DataFrame(sector_allocation.items(), columns=['Sector', 'Value'])
            fig = px.pie(sector_df, names='Sector', values='Value', hole=0.4, title=" ")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("No sector allocation data to display.")
    
    st.divider()

    # Row for Holdings Summary
    st.subheader("Holdings Summary")
    stocks = data.get('stock_analysis', [])
    if stocks:
        summary_df = pd.DataFrame(stocks)
        display_cols = {
            "ticker": "Instrument", "quantity": "Qty", "average_cost": "Avg. cost",
            "current_value": "Cur. val", "pnl": "P&L"
        }
        summary_df_display = summary_df[list(display_cols.keys())].rename(columns=display_cols)
        st.dataframe(summary_df_display, hide_index=True)
    else:
        st.warning("No holdings data to display.")


def display_stock_deep_dive(data):
    """
    Displays the recommendation table and a detailed analysis, now with
    robust data type conversion to prevent rendering errors.
    """
    st.header("AI-Powered Stock Recommendations")
    
    stocks = data.get('stock_analysis', [])
    if not stocks:
        st.warning("No stock analysis data available.")
        return

    rec_data = []
    for stock in stocks:
        rec_data.append({
            "Symbol": stock.get('ticker', 'N/A'),
            "Recommendation": stock.get('recommendation', 'N/A'),
            "Urgency": stock.get('urgency', 'N/A'),
            "Reason": stock.get('reason', 'N/A')
        })
    rec_df = pd.DataFrame(rec_data)

    st.dataframe(
        rec_df,
        column_config={
            "Symbol": st.column_config.TextColumn("Symbol", width=100),
            "Recommendation": st.column_config.TextColumn("Recommendation", width=120),
            "Urgency": st.column_config.TextColumn("Urgency", width=50),
            "Reason": st.column_config.TextColumn("Reason", width=800),
        },
        hide_index=True,
        use_container_width=True
    )
    st.divider()

    st.subheader("Detailed Stock Analysis")
    for stock in stocks:
        with st.expander(f"Explore detailed data for {stock.get('name', 'N/A')}"):
            st.subheader(f"{stock.get('name', 'N/A')} ({stock.get('ticker', 'N/A')})")
            
            st.markdown("#### Peter Lynch Scorecard")
            fundamentals = stock.get('fundamentals', {})
            lynch_metrics = {
                "P/E Ratio": fundamentals.get("P/E Ratio", "N/A"),
                "Forward P/E Ratio": fundamentals.get("Forward P/E Ratio", "N/A"),
                "PEG Ratio": fundamentals.get("PEG Ratio", "N/A"),
                "Debt-to-Equity": fundamentals.get("Debt-to-Equity", "N/A"),
                "Market Cap": fundamentals.get("Market Cap", "N/A"),
            }
            lynch_df = pd.DataFrame(lynch_metrics.items(), columns=["Metric", "Value"])
            # --- CRITICAL FIX: Convert all columns to strings before display ---
            for col in lynch_df.columns:
                lynch_df[col] = lynch_df[col].astype(str)
            st.dataframe(lynch_df, hide_index=True)

            
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Other Fundamental Data")
                other_fundamentals = {k: v for k, v in fundamentals.items() if k not in lynch_metrics and k != 'sector'}
                if other_fundamentals:
                    other_df = pd.DataFrame(other_fundamentals.items(), columns=['Metric', 'Value'])
                    # --- CRITICAL FIX: Convert all columns to strings before display ---
                    for col in other_df.columns:
                        other_df[col] = other_df[col].astype(str)
                    st.dataframe(other_df, hide_index=True)
                else:
                    st.write("No other fundamental data available.")
            
            with col2:
                st.subheader("Technical Snapshot")
                technicals = stock.get('technicals', {})
                if technicals:
                     df_tech = pd.DataFrame(technicals.items(), columns=['Indicator', 'Value'])
                     # --- CRITICAL FIX: Convert all columns to strings before display ---
                     for col in df_tech.columns:
                        df_tech[col] = df_tech[col].astype(str)
                     st.dataframe(df_tech, hide_index=True)
                else:
                    st.write("Technical data not available.")
            
            st.subheader("Price Performance (5-Year History)")
            price_history = stock.get('price_history', {})
            if price_history:
                price_df = pd.DataFrame(price_history)
                fig = px.line(price_df, x='Date', y='Close', title=f"{stock.get('name')} Price Chart")
                st.plotly_chart(fig, use_container_width=True)
            else:
                 st.write("Price history not available.")

def display_news_feed(data):
    # ... (code remains the same)
    pass

def display_what_if_analysis(original_stocks):
    # ... (code remains the same)
    pass

def display_screener():
    # ... (code remains the same)
    pass


# --- MAIN APPLICATION LOGIC ---

def main():
    """Main function to run the Streamlit application."""
    st.set_page_config(layout="wide", page_title="Intelligent Portfolio Analyst")
    load_dotenv()

    st.markdown("""
        <style>
            .stDataFrame [data-col="3"] div {
                white-space: normal !important;
                word-wrap: break-word !important;
            }
        </style>
    """, unsafe_allow_html=True)

    st.title("Intelligent Portfolio Analyst ©")

    if 'analysis_logs' not in st.session_state:
        st.session_state.analysis_logs = []
    
    with st.sidebar:
        st.header("Portfolio Upload")
        st.write("Upload your portfolio statement (CSV or XLSX)")
        uploaded_file = st.file_uploader("Drag and drop file here", type=["csv", "xlsx"])

    if 'final_report' not in st.session_state:
        st.session_state.final_report = None

    if uploaded_file:
        st.session_state.analysis_logs = []
        st.session_state.final_report = None
        
        spinner_placeholder = st.empty()
        
        with spinner_placeholder, st.spinner("Analyzing your portfolio... This may take a moment."):
            for chunk in run_graph(uploaded_file):
                if "report_generator" in chunk:
                    st.session_state.final_report = chunk["report_generator"].get("final_report")
        
        spinner_placeholder.empty()

    if st.session_state.final_report:
        final_report = st.session_state.final_report
        analysis_errors = final_report.get("analysis_errors", [])
        
        if "Analysis Complete!" not in st.session_state:
            st.success("Analysis Complete!")
            st.session_state["Analysis Complete!"] = True
        
        if analysis_errors:
            st.subheader("Analysis Issues Encountered:")
            for err in analysis_errors:
                st.warning(err)
        
        setup_tabs(final_report)

    elif not uploaded_file:
        st.info("Please upload your portfolio file to begin analysis.")
    else:
        st.error("An unexpected error occurred. Please check the logs or your file and try again.")
    
    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Peter Lynch's Ideal Metrics")
        st.write("") 
        st.info("""
        - **P/E Ratio:** < 25
        - **Forward P/E Ratio:** < 15
        - **Debt/Equity Ratio:** < 35% (0.35)
        - **EPS Annual Growth:** > 15%
        - **Market Cap:** > Rs.40,000 Crore
        - **PEG Ratio:** < 1.2
        """)
    with col2:
        st.subheader("Analysis Logs")
        log_text = "\n".join(st.session_state.analysis_logs)
        st.text_area("Logs", log_text, height=215, key="footer_logs")

    st.divider()
    st.warning("""
    **Disclaimer**

    Investment in securities market are subject to market risks, read all the related documents carefully before investing. 
    This is AI generated content and AI can make mistakes and this is for educational purpose only, and all the API's used in this app is taken from yfinance.
    """)


if __name__ == "__main__":
    main()

