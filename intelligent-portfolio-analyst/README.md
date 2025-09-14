Intelligent Portfolio Analyst ©
Overview
The Intelligent Portfolio Analyst is a sophisticated web application built with Python and Streamlit, designed to provide retail investors with deep, AI-driven insights into their stock portfolios. Users can upload their holdings via a CSV or Excel file, and the application performs a comprehensive, live analysis, delivering actionable recommendations, dynamic risk assessment, and detailed financial data.

This application is built using a modern, multi-agent architecture with LangGraph, ensuring a clean separation of concerns and a scalable design.

Core Features
Simple Portfolio Upload: An intuitive interface for uploading your portfolio statement in .csv or .xlsx format.

Dynamic Dashboard:

Key Metrics: Get an at-a-glance view of your Total Investment, Current Value, and overall Profit/Loss, sourced directly from your uploaded file.

Dynamic Risk Profile: The application calculates your portfolio's weighted average beta to assign a dynamic risk profile (Conservative, Moderate Growth, or Aggressive).

Allocation Charts: Visualize your portfolio's sector-wise and asset allocation based on live market data.

AI-Powered Stock Deep-Dive:

Interactive Recommendations Table: A clean, interactive table summarizes the AI's analysis for each stock, providing a clear recommendation (Buy, Hold, Sell), the urgency of the action (High, Medium, Low), and a concise reason.

Click-to-Explore Details: Simply expand any stock in the list to view a detailed breakdown, including fundamental analysis, technical indicators, and an interactive 5-year price history chart.

Technical Architecture
Framework: Streamlit

Core Logic: Python

AI Orchestration: LangGraph (Multi-Agent System)

LLM Provider: Groq (meta-llama/llama-4-scout-17b-16e-instruct)

Live Market Data: yfinance

The application uses a four-step, agent-based workflow for analysis:

Ingestion: Parses the user's uploaded file.

Validation: A safeguard step that validates the parsed data to prevent errors.

Enrichment: Enriches the user's data with live market data and performs the "Chain of Thought" AI analysis for each stock.

Report Generation: Aggregates all the enriched data into a final, comprehensive report for the UI.

Setup and Installation
Follow these steps to run the application on your local machine.

1. Prerequisites
Python 3.10 or higher.

2. Clone or Download the Project
Get a local copy of all the project files in a single directory.

3. Set Up a Virtual Environment
It is highly recommended to use a virtual environment. Open your terminal in the project directory and run:

# Create the environment
python -m venv venv

# Activate the environment
# On Windows:
.\venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

4. Install Dependencies
With your virtual environment active, install all the required libraries:

pip install -r requirements.txt

5. Set Up API Keys
Create a file named .env in the root of your project directory.

Open the .env file and add your Groq API key:

GROQ_API_KEY="your_groq_api_key_here"

You can get a free API key from the Groq Console.

6. Prepare Your Portfolio File
Ensure your .csv or .xlsx file contains the following columns. The names can be slightly different (e.g., "P&L" vs. "p&l"), but they must be present.

Instrument (The stock ticker, e.g., "RELIANCE")

Qty

Avg. cost

Invested

Cur. val

P&L

7. Run the Application
In your terminal (with the virtual environment active), run the following command:

streamlit run main_app.py

Your web browser will automatically open a new tab with the application running.