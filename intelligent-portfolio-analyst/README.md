# Intelligent Portfolio Analyst 🤖

## Overview

The Intelligent Portfolio Analyst is a powerful tool built to democratize financial analysis for retail investors. By simply uploading a portfolio statement (CSV or Excel), users can unlock deep, AI-driven insights that were once only available to institutional firms. The application delivers actionable recommendations, dynamic risk assessment, and detailed financial data.

This application is built using a modern, multi-agent architecture with LangGraph, ensuring a clean separation of concerns and a scalable design for complex data processing and AI analysis.

## Core Features

* **Simple Portfolio Upload:** An intuitive interface for uploading your portfolio statement in `.csv` or `.xlsx` format.

* **Dynamic Dashboard:**

  * **Key Metrics:** Get an at-a-glance view of your Total Investment, Current Value, and overall Profit/Loss.

  * **Dynamic Risk Profile:** The application calculates your portfolio's weighted average beta to assign a dynamic risk profile (Conservative, Moderate Growth, or Aggressive).

  * **Allocation Charts:** Visualize your portfolio's sector-wise allocation based on live market data.

* **AI-Powered Stock Deep-Dive:**

  * **Interactive Recommendations Table:** A clean, interactive table summarizes the AI's analysis for each stock, providing a clear recommendation (Buy, Hold, Sell), the urgency of the action, and a concise, AI-generated reason.

  * **Click-to-Explore Details:** Simply expand any stock in the list to view a detailed breakdown, including fundamental analysis, technical indicators, and an interactive 5-year price history chart.

* **Personalized News Feed:** Get the latest headlines for your stocks, summarized into a single sentence by AI.

* **Advanced Stock Screener:** A powerful tool to analyze any stock on the NSE, complete with an AI-generated list of pros and cons and a peer comparison feature.

## Technical Architecture

The application's backend is powered by a multi-agent system orchestrated by **LangGraph**. This creates a stateful, directed graph where each node is an "agent" responsible for a specific task. The application state is passed from one agent to the next, creating a robust and maintainable workflow.

The workflow proceeds in the following sequence:

1. **Ingestion (`portfolio_inestion_agent`):** The entry point of the graph. This agent takes the user's uploaded file, determines its type (`.csv` or `.xlsx`), and calls the appropriate parser from the `/parsers` directory to extract the portfolio data.

2. **Validation (`validation_agent`):** A crucial safeguard node. It inspects the data from the ingestion step to ensure it is correctly formatted (e.g., a dictionary containing a list of stocks). This prevents errors in subsequent analysis steps.

3. **Enrichment (`stock_analysis_agent`):** This is the core analysis engine and the heart of the application. For each stock in the portfolio, it performs a sophisticated "Chain of Thought" analysis that mirrors a human analyst's workflow:

   * **Data Gathering:** It fetches comprehensive live market data using the `yfinance` library, including fundamental metrics, technical indicators, price history, and beta.

   * **AI Verdicts:** It makes sequential calls to the Groq API (running the `meta-llama/llama-4-scout-17b-16e-instruct` model) to get separate verdicts on the company's financial health and the current market sentiment.

   * **Final Synthesis:** It synthesizes the fundamental verdict, the technical verdict, and the stock's beta into a final, actionable recommendation, complete with an urgency level and a concise reason.

4. **News Analysis (`news_analysis_agent`):** This agent takes the enriched stock data and fetches recent news for each holding. It uses a hybrid approach, first trying `yfinance` and then falling back to the `NewsApiClient` if necessary. It then uses the AI model to summarize each news headline into a single sentence.

5. **Report Generation (`report_generation_agent`):** The final step in the workflow. It aggregates all the enriched data—the stock analysis, the news summaries, and any errors—into a single, comprehensive report that is then passed to the Streamlit UI for display.

This agent-based architecture makes the application highly modular and scalable. Each agent has a single responsibility, making it easy to debug, maintain, and extend the system with new capabilities in the future.

## Setup and Installation

Follow these steps to run the application on your local machine.

#### 1. Prerequisites

* Python 3.10 or higher.

#### 2. Clone or Download the Project

Get a local copy of all the project files in a single directory.

#### 3. Set Up a Virtual Environment

It is highly recommended to use a virtual environment. Open your terminal in the project directory and run:


Create the environment
python -m venv venv

Activate the environment
On Windows:
.\venv\Scripts\activate

On macOS/Linux:
source venv/bin/activate


#### 4. Install Dependencies

With your virtual environment active, install all the required libraries from the `requirements.txt` file:


pip install -r requirements.txt


#### 5. Set Up API Keys

Create a file named `.env` in the root of your project directory. Open the `.env` file and add your Groq and News API keys:


GROQ_API_KEY="your_groq_api_key_here"
NEWS_API_KEY="your_news_api_key_here"


You can get a free API key from the [Groq Console](https://console.groq.com/keys) and [NewsAPI](https://newsapi.org/).

#### 6. Prepare Your Portfolio File

Ensure your `.csv` or `.xlsx` file contains the following columns. The names can be slightly different (e.g., "P&L" vs. "p&l"), but they must be present.

* `Instrument` (The stock ticker, e.g., "RELIANCE")

* `Qty`

* `Avg. cost`

* `Invested`

* `Cur. val`

* `P&L`

#### 7. Run the Application

In your terminal (with the virtual environment active), run the following command:


streamlit run main_app.py


Your web browser will automatically open a new tab with the application running.
