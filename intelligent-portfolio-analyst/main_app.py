import streamlit as st
import pandas as pd
import plotly.express as px
from dotenv import load_dotenv
from graph.graph_orchestrator import run_graph
from agents.screener_agent import run_screener
from utils.portfolio_aggregator import aggregate_portfolio_metrics
from utils import data_fetchers
from utils.stock_universe import get_stock_universe # <-- NEW IMPORT
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
    Displays the recommendation table and a detailed analysis, now featuring
    a dedicated Peter Lynch Scorecard for each stock.
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
            for col in lynch_df.columns:
                lynch_df[col] = lynch_df[col].astype(str)
            st.dataframe(lynch_df, hide_index=True)

            
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Other Fundamental Data")
                other_fundamentals = {k: v for k, v in fundamentals.items() if k not in lynch_metrics and k != 'sector'}
                if other_fundamentals:
                    other_df = pd.DataFrame(other_fundamentals.items(), columns=['Metric', 'Value'])
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
    """Displays the Personalized News Feed tab."""
    st.header("Personalized News Feed")
    st.write("Recent news (last 2 months) related to your stock holdings, summarized by AI.")
    
    all_news = data.get("news", [])
    if not all_news:
        st.warning("Could not retrieve news articles at this time.")
        return

    for news_item in all_news:
        st.subheader(f"News for {news_item['ticker']}")
        for article in news_item['articles']:
            with st.container():
                st.write(f"**{article.get('title', 'No Title')}**")
                st.write(f"*{article.get('publisher', 'N/A')} | {article.get('publish_date', 'N/A')}*")
                st.info(f"**AI Summary:** {article.get('summary', 'Not available.')}")
                st.link_button("Read Full Article", article.get('link', '#'))
                st.divider()

def display_what_if_analysis(original_stocks):
    """
    Displays the 'What If?' analysis tab, now with a dynamic, searchable
    stock ticker input and live price fetching.
    """
    st.header("What If? Scenario Analysis")
    st.write("Simulate how adding a new stock would impact your portfolio's key metrics.")

    if not original_stocks:
        st.warning("Please upload and analyze your portfolio on the Dashboard tab first.")
        return
        
    st.info(st.session_state.universe_status)

    with st.form("what_if_form"):
        st.subheader("Enter a Hypothetical Trade")
        
        # Use a searchable selectbox for a better user experience
        ticker = st.selectbox(
            "Search for a Stock Ticker (start typing to filter)", 
            options=st.session_state.stock_universe
        )
        
        # Use columns for a cleaner layout
        col1, col2 = st.columns(2)
        with col1:
            quantity = st.number_input("Quantity", min_value=1, value=10)
        with col2:
            # Price is now dynamically fetched and displayed
            ltp = 0
            if ticker:
                price_history = data_fetchers.get_price_history(f"{ticker}.NS", period="1d")
                if price_history:
                    ltp = price_history[-1]['Close']
            purchase_price = st.number_input(
                "Purchase Price (automatically fetched, editable)", 
                min_value=0.01, 
                value=float(ltp),
                key="what_if_price"
            )
        
        submit_button = st.form_submit_button("Analyze Scenario")

    if submit_button and ticker:
        with st.spinner(f"Analyzing scenario for {ticker}..."):
            # The purchase price is the one from the form
            final_purchase_price = st.session_state.what_if_price
            
            new_stock = {
                'ticker': ticker, 'quantity': quantity, 'average_cost': final_purchase_price,
                'invested_value': quantity * final_purchase_price, 'current_value': quantity * final_purchase_price, # Starts at purchase price
                'beta': data_fetchers.get_beta(f"{ticker}.NS"),
                'fundamentals': data_fetchers.get_fundamental_data(f"{ticker}.NS")
            }
            
            hypothetical_portfolio = original_stocks + [new_stock]
            original_metrics = aggregate_portfolio_metrics(original_stocks)
            new_metrics = aggregate_portfolio_metrics(hypothetical_portfolio)
            
            st.subheader("Scenario Impact Assessment")
            
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("#### Original Portfolio")
                st.metric("Current Value", f"Rs.{original_metrics.get('current_value', 0):,.2f}")
                st.metric("Risk Profile", original_metrics.get('risk_profile', 'N/A'))
            with col2:
                st.markdown("#### New Portfolio (Simulated)")
                st.metric("New Current Value", f"Rs.{new_metrics.get('current_value', 0):,.2f}")
                st.metric("New Risk Profile", new_metrics.get('risk_profile', 'N/A'))

            st.divider()
            st.subheader("New Sector Allocation")
            new_sector_allocation = new_metrics.get('sector_allocation', {})
            if new_sector_allocation:
                sector_df = pd.DataFrame(new_sector_allocation.items(), columns=['Sector', 'Value'])
                fig = px.pie(sector_df, names='Sector', values='Value', hole=0.4, title=" ")
                st.plotly_chart(fig, use_container_width=True)

def display_screener():
    """
    Displays the Personalized Stock Screener tab, now powered by the
    dynamic stock universe.
    """
    st.header("Personalized Stock Screener")
    st.write("Find new investment ideas that match your personal style. Provide a list of tickers to screen.")
    
    st.info(st.session_state.universe_status)
    default_tickers = ", ".join(st.session_state.stock_universe[:8])

    with st.form("screener_form"):
        st.subheader("1. Define Your Universe")
        st.info("You can find and copy tickers from the searchable list in the 'What If? Analysis' tab.")
        ticker_list = st.text_area("Enter a list of stock tickers to screen (comma-separated)", default_tickers)
        
        st.subheader("2. Define Your Investment Profile")
        risk_appetite = st.selectbox("Your Risk Appetite", ["Conservative", "Moderate", "Aggressive"])
        horizon = st.selectbox("Your Investment Horizon", ["Short-term (1-3 years)", "Long-term (5+ years)"])
        
        submit_button = st.form_submit_button("Find Matching Stocks")

    if submit_button and ticker_list:
        tickers = [ticker.strip().upper() for ticker in ticker_list.split(',')]
        with st.spinner("Screening stocks against your profile..."):
            recommendations = run_screener(tickers, risk_appetite, horizon)

        st.subheader("Screener Results")
        if recommendations:
            st.write(f"Found {len(recommendations)} stocks that match your criteria:")
            rec_df = pd.DataFrame(recommendations)
            st.dataframe(rec_df, hide_index=True)
        else:
            st.success("No stocks in your list matched your specific investment criteria.")


# --- MAIN APPLICATION LOGIC ---

def main():
    """Main function to run the Streamlit application."""
    st.set_page_config(layout="wide", page_title="Intelligent Portfolio Analyst")
    load_dotenv()

    # Load the stock universe once at the beginning
    if 'stock_universe' not in st.session_state:
        stock_universe = get_stock_universe()
        if len(stock_universe) > 10:
            st.session_state.universe_status = f"Loaded {len(stock_universe)} stocks from NSE for suggestions."
        else:
            st.session_state.universe_status = "Could not fetch the full list of stocks. Showing a limited sample."
        st.session_state.stock_universe = stock_universe

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

