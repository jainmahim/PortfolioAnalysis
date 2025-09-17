import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dotenv import load_dotenv
from graph.graph_orchestrator import run_graph
from agents.screener_agent import run_detailed_stock_analysis
from utils.portfolio_aggregator import aggregate_portfolio_metrics
from utils import data_fetchers
from utils.stock_universe import get_stock_universe

# --- UI DISPLAY FUNCTIONS ---

def display_dashboard(data):
    """
    Displays the main dashboard with a cleaner, more readable layout.
    """
    st.header("Dashboard: 360° View")

    with st.container(border=True):
        total_investment = data.get('total_investment', 0)
        current_value = data.get('current_value', 0)
        pnl = data.get('overall_pnl', 0)
        pnl_percent = data.get('overall_pnl_percent', 0)

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Investment", f"₹{total_investment:,.2f}")
        col2.metric("Current Value", f"₹{current_value:,.2f}")
        
        pnl_color = "normal" if pnl >= 0 else "inverse"
        col3.metric("Profit/Loss", f"₹{pnl:,.2f}", f"{pnl_percent:.2f}%" if pnl_percent is not None else "", delta_color=pnl_color)
        col4.metric("Risk Profile", data.get('risk_profile', 'N/A'))

    st.subheader("Portfolio Allocation")
    with st.container(border=True):
        col1, col2 = st.columns(2) 
        with col1:
            st.markdown("<h6>Ideal Sector Allocation</h6>", unsafe_allow_html=True)
            ideal_allocation_data = {
                'Sector': ['Financials', 'IT', 'Consumer Goods', 'Healthcare', 'Energy', 'Industrials', 'Materials', 'Utilities'],
                'Value': [25, 15, 15,  10, 10, 10, 5, 10]
            }
            ideal_df = pd.DataFrame(ideal_allocation_data)
            fig = px.pie(ideal_df, names='Sector', values='Value', hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
            fig.update_layout(showlegend=False, margin=dict(l=10, r=10, t=10, b=10), height=300)
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.markdown("<h6>Your Sector Allocation</h6>", unsafe_allow_html=True)
            sector_allocation = data.get('sector_allocation', {})
            if sector_allocation and sum(sector_allocation.values()) > 0:
                sector_df = pd.DataFrame(sector_allocation.items(), columns=['Sector', 'Value'])
                fig = px.pie(sector_df, names='Sector', values='Value', hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
                fig.update_layout(showlegend=False, margin=dict(l=10, r=10, t=10, b=10), height=300)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No sector allocation data to display.", icon="📊")
    
    st.subheader("Holdings Summary")
    with st.container(border=True):
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
            st.info("No holdings data to display.", icon="📄")


def display_stock_deep_dive(data):
    """
    Displays the recommendation table and a detailed analysis.
    """
    st.header("AI-Powered Stock Recommendations")
    
    stocks = data.get('stock_analysis', [])
    if not stocks:
        st.warning("No stock analysis data available.")
        return
    
    with st.container(border=True):
        rec_data = []
        for stock in stocks:
            rec_data.append({
                "Symbol": stock.get('ticker', 'N/A'),
                "Recommendation": stock.get('recommendation', 'N/A'),
                "Urgency": stock.get('urgency', 'N/A'),
                "Reasoning": stock.get('reason', 'N/A')
            })
        rec_df = pd.DataFrame(rec_data)

        st.dataframe(
            rec_df,
            column_config={
                "Symbol": st.column_config.TextColumn("Symbol", width=100),
                "Recommendation": st.column_config.TextColumn("Recommendation", width=120),
                "Urgency": st.column_config.TextColumn("Urgency", width=100),
            },
            hide_index=True,
            use_container_width=True
        )

    st.subheader("Detailed Stock Analysis")
    for stock in stocks:
        with st.expander(f"Explore detailed data for {stock.get('name', 'N/A')}"):
            st.subheader(f"{stock.get('name', 'N/A')} ({stock.get('ticker', 'N/A')})")
            
            st.markdown("#### Key Metrics (Peter Lynch Style)")
            with st.container(border=True):
                fundamentals = stock.get('fundamentals', {})
                lynch_metrics = {
                    "P/E Ratio": fundamentals.get("P/E Ratio", "N/A"),
                    "Forward P/E": fundamentals.get("Forward P/E Ratio", "N/A"),
                    "PEG Ratio": fundamentals.get("PEG Ratio", "N/A"),
                    "Debt/Equity": fundamentals.get("Debt-to-Equity", "N/A"),
                    "Market Cap": fundamentals.get("Market Cap", "N/A"),
                }
                lynch_df = pd.DataFrame(lynch_metrics.items(), columns=["Metric", "Value"])
                st.dataframe(lynch_df, hide_index=True)

            col1, col2 = st.columns(2)
            with col1:
                st.subheader("More Fundamentals")
                with st.container(border=True):
                    other_fundamentals = {k: v for k, v in fundamentals.items() if k not in lynch_metrics and k != 'sector'}
                    if other_fundamentals:
                        other_df = pd.DataFrame(other_fundamentals.items(), columns=['Metric', 'Value'])
                        st.dataframe(other_df, hide_index=True)
                    else:
                        st.write("No other fundamental data available.")
            
            with col2:
                st.subheader("Technical Snapshot")
                with st.container(border=True):
                    technicals = stock.get('technicals', {})
                    if technicals:
                         df_tech = pd.DataFrame(technicals.items(), columns=['Indicator', 'Value'])
                         st.dataframe(df_tech, hide_index=True)
                    else:
                        st.write("Technical data not available.")
            
            st.subheader("Price History (5 Years)")
            with st.container(border=True):
                price_history = stock.get('price_history', {})
                if price_history:
                    price_df = pd.DataFrame(price_history)
                    fig = px.line(price_df, x='Date', y='Close', title=f"{stock.get('name')} Price Chart", template="plotly_white")
                    st.plotly_chart(fig, use_container_width=True)
                else:
                     st.write("Price history not available.")

def display_news_feed(data):
    """Displays the Personalized News Feed tab."""
    st.header("Personalized News Feed")
    st.write("Recent news (last 2 months) related to your stock holdings, summarized by AI.")
    
    all_news = data.get("news", [])
    if not all_news:
        st.info("Could not retrieve news articles at this time.", icon="📰")
        return

    for news_item in all_news:
        st.subheader(f"Latest on {news_item['ticker']}")
        for article in news_item['articles']:
            with st.container(border=True):
                st.write(f"**{article.get('title', 'No Title')}**")
                st.write(f"*{article.get('publisher', 'N/A')} | {article.get('publish_date', 'N/A')}*")
                st.info(f"**AI TL;DR:** {article.get('summary', 'Not available.')}")
                st.link_button("Read the Full Story", article.get('link', '#'))


def display_what_if_analysis(original_stocks):
    """
    Displays the 'What If?' analysis tab with a polished UI.
    """
    st.header("What If? Scenario Mode")
    st.write("See how a new trade could change up your portfolio's stats.")

    if not original_stocks:
        st.info("Upload your portfolio to start running scenarios.", icon="🔬")
        return
    
    with st.container(border=True):
        with st.form("what_if_form"):
            st.subheader("Simulate a New Investment")
            col1, col2 = st.columns(2)
            with col1:
                selected_ticker = st.selectbox(
                    "Search for a Stock", 
                    options=st.session_state.stock_universe,
                    index=None,
                    placeholder="Type to search...",
                )
            with col2:
                quantity = st.number_input("Quantity", min_value=1, value=10)
            
            submit_button = st.form_submit_button("Run Simulation", use_container_width=True, type="primary")

    if submit_button and selected_ticker:
        with st.spinner(f"Crunching the numbers for {selected_ticker}..."):
            price_history = data_fetchers.get_price_history(f"{selected_ticker}.NS", period="1d")
            
            if not price_history:
                st.error(f"Could not fetch price for {selected_ticker}. Try another stock.")
                return

            purchase_price = price_history[-1]['Close']
            invested_amount = quantity * purchase_price

            new_stock = {'ticker': selected_ticker, 'quantity': quantity, 'average_cost': purchase_price, 'invested_value': invested_amount, 'current_value': invested_amount, 'beta': data_fetchers.get_beta(f"{selected_ticker}.NS"), 'fundamentals': data_fetchers.get_fundamental_data(f"{selected_ticker}.NS")}
            
            hypothetical_portfolio = original_stocks + [new_stock]
            original_metrics = aggregate_portfolio_metrics(original_stocks)
            new_metrics = aggregate_portfolio_metrics(hypothetical_portfolio)
            
            with st.container(border=True):
                st.subheader("Sector Allocation: Before vs. After")
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("<h6>Your Original Allocation</h6>", unsafe_allow_html=True)
                    original_sector_allocation = original_metrics.get('sector_allocation', {})
                    if original_sector_allocation:
                        sector_df_orig = pd.DataFrame(original_sector_allocation.items(), columns=['Sector', 'Value'])
                        fig_orig = px.pie(sector_df_orig, names='Sector', values='Value', hole=0.5, height=250, color_discrete_sequence=px.colors.sequential.Tealgrn)
                        fig_orig.update_layout(showlegend=False, margin=dict(l=10, r=10, t=10, b=10))
                        st.plotly_chart(fig_orig, use_container_width=True)
                with col2:
                    st.markdown("<h6>New Allocation (Simulated)</h6>", unsafe_allow_html=True)
                    new_sector_allocation = new_metrics.get('sector_allocation', {})
                    if new_sector_allocation:
                        sector_df_new = pd.DataFrame(new_sector_allocation.items(), columns=['Sector', 'Value'])
                        fig_new = px.pie(sector_df_new, names='Sector', values='Value', hole=0.5, height=250, color_discrete_sequence=px.colors.sequential.Tealgrn)
                        fig_new.update_layout(showlegend=False, margin=dict(l=10, r=10, t=10, b=10))
                        st.plotly_chart(fig_new, use_container_width=True)
                
                st.subheader("The Impact")
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Purchase Price", f"₹{purchase_price:,.2f}")
                col2.metric("Invested Amount", f"₹{invested_amount:,.2f}")
                col3.metric("New Portfolio Value", f"₹{new_metrics.get('current_value', 0):,.2f}")
                col4.metric("New Risk Profile", new_metrics.get('risk_profile', 'N/A'))

    elif submit_button:
        st.error("Please select a stock from the list before analyzing.")

def display_screener():
    """ Displays the completely revamped Detailed Stock Analysis tab. """
    st.header("Detailed Stock Analysis")
    st.write("Search for any stock to get a detailed breakdown, AI-powered insights, and comparative analysis.")

    with st.form("stock_selection_form"):
        col1, col2 = st.columns([3, 1])
        with col1:
            selected_ticker = st.selectbox("Search for a Stock Ticker", options=st.session_state.stock_universe, index=None, placeholder="Type to search for a stock...", key="screener_stock_select")
        with col2:
            analyze_button = st.form_submit_button("Analyze", use_container_width=True, type="primary")

    if analyze_button and selected_ticker:
        with st.spinner(f"Getting the details for {selected_ticker}..."):
            analysis_result = run_detailed_stock_analysis(selected_ticker)
            st.session_state.screener_analysis_result = analysis_result
            st.session_state.comparison_stocks = []
            st.session_state.selected_screener_ticker = selected_ticker
    
    if 'screener_analysis_result' in st.session_state and st.session_state.screener_analysis_result:
        result = st.session_state.screener_analysis_result
        fundamentals = result.get('fundamentals', {})
        stock_name = result.get('name', st.session_state.get('selected_screener_ticker'))

        st.subheader(f"{stock_name} ({st.session_state.get('selected_screener_ticker')})")

        with st.container(border=True):
            cols = st.columns(3)
            metrics_to_show = [("Market Cap", "Market Cap"), ("Current Price", "Current Price"), ("High / Low", "High / Low"), ("Stock P/E", "P/E Ratio"), ("Book Value", "Book Value"), ("Dividend Yield", "Dividend Yield"), ("ROCE", "ROCE"), ("ROE", "ROE"), ("Face Value", "Face Value")]
            for i, (label, key) in enumerate(metrics_to_show):
                value = fundamentals.get(key, 'N/A')
                with cols[i % 3]:
                    st.metric(label=label, value=str(value))
        
        st.subheader("Price Performance")
        with st.container(border=True):
            timeframe_map = {"1M": "1mo", "6M": "6mo", "1Y": "1y", "3Y": "3y", "5Y": "5y"}
            col1, col2 = st.columns([3, 1])
            with col1:
                selected_timeframe = st.radio("Select Timeframe", options=list(timeframe_map.keys()), index=2, horizontal=True, key="screener_timeframe")
            with col2:
                show_50ma = st.toggle("50-Day MA", value=False, key="screener_50ma")
                show_200ma = st.toggle("200-Day MA", value=False, key="screener_200ma")

            price_history = data_fetchers.get_price_history(f"{st.session_state.get('selected_screener_ticker')}.NS", period=timeframe_map[selected_timeframe])
            if price_history:
                price_df = pd.DataFrame(price_history)
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=price_df['Date'], y=price_df['Close'], mode='lines', name='Price', line=dict(color='#007BFF'))) 
                if show_50ma and '50-Day MA' in price_df.columns:
                    fig.add_trace(go.Scatter(x=price_df['Date'], y=price_df['50-Day MA'], mode='lines', name='50-Day MA', line=dict(color='#FFA500', dash='dash'))) 
                if show_200ma and '200-Day MA' in price_df.columns:
                    fig.add_trace(go.Scatter(x=price_df['Date'], y=price_df['200-Day MA'], mode='lines', name='200-Day MA', line=dict(color='#FF4500', dash='dash'))) 
                fig.update_layout(title=f"{stock_name} Price Chart ({selected_timeframe})", yaxis_title="Price (₹)", legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1), template="plotly_white")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("Could not load price history.")
        
        st.subheader("AI-Generated Analysis: Pros & Cons")
        pros_cons = result.get('pros_cons', {})
        col1, col2 = st.columns(2)
        with col1:
            with st.container(border=True):
                st.markdown("<h5><span style='color: #28a745;'>Pros</span></h5>", unsafe_allow_html=True)
                for pro in pros_cons.get('pros', ["Analysis not available."]):
                    st.markdown(f"- {pro}")
        with col2:
            with st.container(border=True):
                st.markdown("<h5><span style='color: #dc3545;'>Cons</span></h5>", unsafe_allow_html=True)
                for con in pros_cons.get('cons', ["Analysis not available."]):
                    st.markdown(f"- {con}")
        
        st.caption("*The pros and cons are machine generated.")

        with st.container(border=True):
            st.subheader("Peer Comparison")
            if len(st.session_state.get('comparison_stocks', [])) < 3:
                with st.form("compare_form"):
                    col1, col2 = st.columns([3,1])
                    with col1:
                        compare_ticker = st.selectbox("Add a stock to compare (max 3)", options=[s for s in st.session_state.stock_universe if s != st.session_state.get('selected_screener_ticker')], index=None, placeholder="Search for a stock...")
                    with col2:
                        add_compare_button = st.form_submit_button("Add", type="primary", use_container_width=True)

                    if add_compare_button and compare_ticker and compare_ticker not in st.session_state.comparison_stocks:
                        st.session_state.comparison_stocks.append(compare_ticker)
                        st.rerun()
            
            if st.session_state.get('comparison_stocks'):
                st.write("Comparing against:")
                cols = st.columns(len(st.session_state.comparison_stocks))
                for i, stock in enumerate(st.session_state.comparison_stocks):
                    with cols[i]:
                        if st.button(f"Remove {stock}", key=f"remove_{stock}"):
                            st.session_state.comparison_stocks.remove(stock)
                            st.rerun()

                with st.spinner("Loading comparison data..."):
                    fig_compare = go.Figure()
                    primary_hist = data_fetchers.get_price_history(f"{st.session_state.get('selected_screener_ticker')}.NS", period="1y", interval="1d")
                    if primary_hist:
                        df_primary = pd.DataFrame(primary_hist)
                        fig_compare.add_trace(go.Scatter(x=df_primary['Date'], y=df_primary['Close'], name=st.session_state.get('selected_screener_ticker'), mode='lines'))
                    
                    for stock in st.session_state.comparison_stocks:
                        comp_hist = data_fetchers.get_price_history(f"{stock}.NS", period="1y", interval="1d")
                        if comp_hist:
                            df_comp = pd.DataFrame(comp_hist)
                            fig_compare.add_trace(go.Scatter(x=df_comp['Date'], y=df_comp['Close'], name=stock, mode='lines'))
                    
                    fig_compare.update_layout(title="1-Year Price Performance Comparison", yaxis_title="Price (₹)", legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1), template="plotly_white")
                    st.plotly_chart(fig_compare, use_container_width=True)

# --- MAIN APPLICATION LOGIC ---

def main():
    """Main function to run the Streamlit application."""
    st.set_page_config(layout="wide", page_title="Intelligent Portfolio Analyst")
    load_dotenv()

    # Initialize session state keys
    if 'active_tab_index' not in st.session_state:
        st.session_state.active_tab_index = 0
    if 'stock_universe' not in st.session_state:
        st.session_state.stock_universe = get_stock_universe()
        
    st.markdown("""
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700&display=swap');
            
            html, body, [class*="st-"] {
                font-family: 'Poppins', sans-serif;
            }
            .main { background-color: #F8F9FA; }
            h1 {
                font-weight: 700;
                color: #212529;
            }
            h2, h3 { color: #343A40; font-weight: 600; }
            h6 { color: #6C757D; }
            [data-testid="stVerticalBlock"] > [data-testid="stVerticalBlock"] > [data-testid="stVerticalBlock"] {
                border: 1px solid #E9ECEF;
                border-radius: 1rem;
                padding: 1.5rem;
                background-color: #FFFFFF;
                box-shadow: 0 8px 16px rgba(0,0,0,0.04);
            }
            [data-testid="stMetricValue"] { font-size: 2rem; color: #212529; font-weight: 600; }
            [data-testid="stMetricLabel"] { font-size: 0.9rem; color: #6C757D; }
            .stTabs [data-baseweb="tab-list"] { gap: 8px; border-bottom: 1px solid #DEE2E6; }
            .stTabs [data-baseweb="tab"] { height: 50px; background-color: transparent; padding: 0 1.5rem; border: 1px solid transparent; border-radius: 0.5rem 0.5rem 0 0; margin-bottom: -1px; color: #495057; transition: all 0.2s; }
            .stTabs [data-baseweb="tab"]:hover { background-color: #F1F3F5; color: #000; }
            .stTabs [aria-selected="true"] { background-color: #FFFFFF; border-color: #DEE2E6 #DEE2E6 #FFFFFF; color: #007BFF; font-weight: 600; }
            .stButton > button, .stDownloadButton > button { border: 2px solid #007BFF; border-radius: 0.75rem; color: #007BFF; background-color: #FFFFFF; font-weight: 600; padding: 0.5rem 1.25rem; transition: all 0.2s; }
            .stButton > button:hover, .stDownloadButton > button:hover { background-color: #007BFF; color: #FFFFFF; transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,123,255,0.2); }
            .stForm .stButton > button { background-color: #007BFF; color: #FFFFFF; }
            .stForm .stButton > button:hover { background-color: #0056b3; border-color: #0056b3; }
        </style>
    """, unsafe_allow_html=True)

    st.title("Intelligent Portfolio Analyst ©")

    if 'analysis_logs' not in st.session_state:
        st.session_state.analysis_logs = []
    
    with st.sidebar:
        st.header("Portfolio Upload")
        st.write("Upload your statement (CSV or XLSX) to get started.")
        uploaded_file = st.file_uploader("Drag and drop file here", type=["csv", "xlsx"], label_visibility="collapsed")

    if 'final_report' not in st.session_state:
        st.session_state.final_report = None
        
    if uploaded_file:
        st.session_state.analysis_logs = []
        st.session_state.final_report = None
        
        status_map = {
            "ingest_portfolio": "Reading your portfolio file...",
            "validate_ingestion": "Validating the data format...",
            "enrich_stocks": "Fetching market data & running AI analysis...",
            "news_analyzer": "Gathering & summarizing news...",
            "report_generator": "Compiling your final report..."
        }

        with st.status("Initializing analysis...", expanded=True) as status:
            for chunk in run_graph(uploaded_file):
                agent_name = list(chunk.keys())[0]
                if agent_name in status_map:
                    status.update(label=status_map[agent_name])
                if "report_generator" in chunk:
                    st.session_state.final_report = chunk["report_generator"].get("final_report")
            status.update(label="Analysis Complete! Your report is ready.", state="complete", expanded=False)

    tab_names = ["Dashboard", "Stock Deep-Dive", "Personalized News", "What If? Analysis", "Detailed Stock Analysis"]
    tab1, tab2, tab3, tab4, tab5 = st.tabs(tab_names)

    with tab1:
        if st.session_state.get('final_report'):
            display_dashboard(st.session_state.final_report)
        else:
            st.info("Upload your portfolio using the sidebar to see your Dashboard.", icon="📊")

    with tab2:
        if st.session_state.get('final_report'):
            display_stock_deep_dive(st.session_state.final_report)
        else:
            st.info("Upload your portfolio to get your AI Stock Report Card.", icon="💡")

    with tab3:
        if st.session_state.get('final_report'):
            display_news_feed(st.session_state.final_report)
        else:
            st.info("Upload your portfolio to see your personalized news feed.", icon="📰")
    
    with tab4:
        if st.session_state.get('final_report'):
            display_what_if_analysis(st.session_state.final_report.get('stock_analysis', []))
        else:
            st.info("Upload your portfolio to use the What If? Scenario Mode.", icon="🔬")

    with tab5:
        display_screener()
    
    st.divider()
    
    with st.container(border=True):
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Peter Lynch's Ideal Metrics")
            st.info("""
            - **P/E Ratio:** < 25
            - **Forward P/E Ratio:** < 15
            - **Debt/Equity Ratio:** < 35% (0.35)
            - **EPS Annual Growth:** > 15%
            - **Market Cap:** > ₹40,000 Crore
            - **PEG Ratio:** < 1.2
            """)
        with col2:
            st.subheader("Analysis Logs")
            log_text = "\n".join(st.session_state.analysis_logs)
            st.text_area("Logs", log_text, height=150, key="footer_logs")

    st.warning("""**Disclaimer:** Investment in securities market are subject to market risks. Read all related documents carefully before investing. This is AI-generated content for educational purposes only. AI can make mistakes. All financial data is provided by yfinance.""", icon="⚠️")

if __name__ == "__main__":
    main()

