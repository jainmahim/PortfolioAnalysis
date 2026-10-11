# PREPARE.md — Interview Prep Guide for "Intelligent Portfolio Analyst" (AlphaBot)

This document exists so you can walk into an interview and talk about this project confidently,
**even if you built it a year ago and forgot the details.** Read it top to bottom once, then skim
the "Interview Q&A" and "Elevator Pitches" sections again right before the interview.

---

## 1. What This Project Is, In One Paragraph

You upload a portfolio holdings file (like a Zerodha statement, CSV/Excel). The app reads it, then
for **each stock** it fetches live market data (price, P/E ratio, RSI, etc.) from Yahoo Finance, asks
an AI model (Groq's LLaMA) to judge the stock's fundamentals and technicals, and combines those into
a final "Buy / Hold / Sell" recommendation. It also fetches recent news and summarizes it, then shows
everything in a dashboard — total P&L, risk profile, sector allocation, per-stock breakdown, and news
feed. There's also a separate "stock screener" tab where you can analyze any NSE stock on demand.

**The interesting engineering part isn't the finance — it's that the backend is built as a
"multi-agent pipeline"**: instead of one giant function that does everything, the work is split into
5 small, independent steps ("agents") that run one after another, each with a single job. This is
built using a library called **LangGraph**.

---

## 2. The Big Picture: What Is LangGraph, Really?

Forget the marketing term "agent." At the code level, LangGraph is just:

1. **A shared dictionary (`state`)** that gets passed from step to step.
2. **A list of "nodes"** — each node is just a normal Python function: `def my_node(state): ... return {"some_key": some_value}`.
3. **Edges** connecting nodes — "after node A runs, go to node B."
4. **Conditional edges** — "after node A runs, go to node B *or* node C, depending on something in the state."

That's it. There's no magic AI deciding the flow — *you* define the flow explicitly as a graph, and
LangGraph just runs it and merges each node's returned dict back into the shared state.

Think of it like a factory assembly line:
- Each station (node) does one job and passes the product (state) to the next station.
- If a station finds a defect (an error), it can send the product straight to the "reject" bin
  (`END`) instead of the next station.

### Why use this instead of just calling functions in sequence?
- **Inspectability**: you can log/stream what happens at each step (the Streamlit UI shows
  "Reading your portfolio file..." → "Fetching market data..." etc. — that's literally each node
  completing).
- **Early exit**: any node can abort the whole pipeline by setting `state["error"]`, and the
  conditional edges stop execution cleanly instead of crashing deep inside some function.
- **Modularity**: each node/agent can be tested, replaced, or reordered independently.

---

## 3. The Pipeline, As a Story

```
  User uploads file
        │
        ▼
┌───────────────────┐
│ ingest_portfolio   │  "What file type is this? Parse it into a list of stocks."
└───────────────────┘
        │  (if parsing failed → END, show error)
        ▼
┌───────────────────┐
│ validate_ingestion │  "Is the parsed data actually a valid {stocks: [...]} shape?"
└───────────────────┘
        │  (if invalid → END, show error)
        ▼
┌───────────────────┐
│ enrich_stocks      │  "For each stock: fetch live data, ask the AI for Buy/Hold/Sell."
└───────────────────┘
        │
        ▼
┌───────────────────┐
│ news_analyzer      │  "For each stock: fetch recent news, ask the AI to summarize it."
└───────────────────┘
        │
        ▼
┌───────────────────┐
│ report_generator   │  "Combine everything into one final_report dict."
└───────────────────┘
        │
        ▼
   Streamlit UI renders final_report in tabs
```

This exact graph is defined in `graph/graph_orchestrator.py`. Here's the actual wiring (simplified):

```python
workflow = StateGraph(AppState)
workflow.add_node("ingest_portfolio", portfolio_ingestion_agent)
workflow.add_node("validate_ingestion", validation_agent)
workflow.add_node("enrich_stocks", stock_analysis_agent)
workflow.add_node("news_analyzer", news_analysis_agent)
workflow.add_node("report_generator", report_generation_agent)

workflow.set_entry_point("ingest_portfolio")

def should_continue(state):
    return "end" if state.get("error") else "continue"

workflow.add_conditional_edges("ingest_portfolio", should_continue,
                                {"continue": "validate_ingestion", "end": END})
workflow.add_conditional_edges("validate_ingestion", should_continue,
                                {"continue": "enrich_stocks", "end": END})
workflow.add_edge("enrich_stocks", "news_analyzer")
workflow.add_edge("news_analyzer", "report_generator")
workflow.add_edge("report_generator", END)

app = workflow.compile()
```

**Key thing to say in an interview:** "Every node is a plain function that receives the shared
state dict and returns a partial update. LangGraph merges that update into the state and routes to
the next node. The only two 'conditional' hops are right after ingestion and validation — if either
fails, the whole pipeline short-circuits to `END` instead of crashing further down with bad data."

---

## 4. Walking Through Each File (What It Does, In Plain Words)

### `main_app.py` — the Streamlit UI
- This is what runs when you type `streamlit run main_app.py`.
- Shows a sidebar file uploader. When a file is uploaded, it calls `run_graph(uploaded_file)`
  (from `graph_orchestrator.py`) and streams results into a live "status" widget — that's why you
  see "Reading your portfolio file..." → "Validating..." → etc. update in real time.
- Once the graph finishes, `final_report` is stored in `st.session_state` and rendered across 5
  tabs: Dashboard, Stock Deep-Dive, Personalized News, What-If Analysis, and the standalone Screener.
- **Simple mental model:** this file has zero "intelligence" — it's just forms + charts + tables.
  All the real logic lives in `graph/` and `agents/`.

### `graph/graph_orchestrator.py` — wires the agents into a graph
- Defines `AppState` (the shape of the shared dict — what keys exist: `portfolio_data`,
  `stock_analysis_results`, `news`, `final_report`, `error`, etc.)
- Builds the `StateGraph`, adds nodes, adds edges (shown above).
- `run_graph(uploaded_file)` returns a generator that yields each node's output as it completes —
  this is what lets the UI "stream" progress live instead of waiting for everything at once.

### `agents/portfolio_ingestion_agent.py` — step 1
- Looks at the uploaded file's extension (`.csv`, `.xlsx`, `.pdf`).
- Calls the matching parser (`parsers/csv_parser.py`, etc.) to turn the file into
  `{"stocks": [{"ticker": "RELIANCE", "quantity": 10, ...}, ...]}`.
- If the parser returns `None` (couldn't understand the file) or throws an exception, sets
  `state["error"]` instead of crashing.

### `agents/validation_agent.py` — step 2 (a safety net)
- Just checks: is `portfolio_data` a dict? Does it have a `stocks` key? Is `stocks` a non-empty list?
- This exists so that a malformed/empty file fails with a clear message right away, instead of
  crashing three steps later inside the AI analysis code with a confusing stack trace.

### `agents/stock_analysis_agent.py` — step 3 (the core engine)
This is the most important file to understand deeply. For **each stock** in the portfolio:

1. **Fetch live data** (concurrently — see Concurrency section below):
   - `get_stock_name`, `get_fundamental_data` (P/E ratio, EPS, sector, etc.),
     `get_technical_data` (50/200-day moving averages, RSI), `get_price_history`, `get_beta`.
2. **Ask the AI three separate questions, in sequence** ("chain of thought"):
   - *Step A:* "Given these fundamentals, is the company's financial health Good/Neutral/Poor?"
   - *Step B:* "Given these technical indicators, is market sentiment Bullish/Neutral/Bearish?"
   - *Step C:* "Given both verdicts + the stock's beta, give me a final JSON:
     `{recommendation, urgency, reason}`."
3. **Parse the AI's JSON answer defensively** — the model is asked to wrap its answer in
   ` ```json ... ``` `, and `extract_json_from_response()` uses regex to pull that out, with a fallback
   regex and a `try/except` so a malformed AI response doesn't crash the whole stock (it just logs
   "AI synthesis failed" and moves to the next stock).

**Why three separate LLM calls instead of one big prompt?** Each call is narrower and more reliable
(the model is less likely to go off-topic), and you get **inspectable intermediate results** —
useful for debugging and for showing "reasoning" to the user, similar to how a human analyst would
first think about fundamentals, then technicals, then combine them.

### `agents/news_analysis_agent.py` — step 4
- For each already-enriched stock, fetch recent news: **try `yfinance` first** (free, no rate
  limit), and **only if that returns nothing**, fall back to the `NewsAPI` client (which has a
  strict free-tier daily limit).
- Each headline gets summarized into one sentence by the LLM.
- If the NewsAPI key is missing/invalid, that only disables the *fallback* — the primary yfinance
  path and LLM summarization still work. (This was a bug I fixed — see Section 7.)

### `agents/report_generation_agent.py` — step 5 (final assembly)
- Takes the enriched stock list + news results + any collected errors.
- Calls `utils/portfolio_aggregator.py` to compute portfolio-wide numbers (explained below).
- Returns one big `final_report` dict — this is the *only* thing the UI reads to render everything.

### `agents/screener_agent.py` — the separate, non-graph feature
- Not part of the LangGraph pipeline at all — it's a plain function `run_detailed_stock_analysis(ticker)`
  called directly from the UI when you use the "Detailed Stock Analysis / Screener" tab.
- Fetches one stock's fundamentals, asks the LLM for 3 pros and 3 cons as JSON.
- **Interview point:** "Not everything needs to be a graph — the screener is a single, simple
  request/response flow, so I kept it as a plain function instead of over-engineering it into
  agents."

### `utils/data_fetchers.py` — all the Yahoo Finance (yfinance) calls live here
- `get_stock_name`, `get_beta`, `get_fundamental_data`, `get_technical_data` (computes 50-day MA,
  200-day MA, 14-day RSI from scratch using pandas), `get_price_history`, `get_stock_news`.
- Every function has a `try/except` that returns a safe fallback (`'N/A'`, `{}`, `[]`, or `1.0` for
  beta) instead of crashing — because external APIs fail/rate-limit unpredictably, and one broken
  ticker shouldn't take down the whole analysis.

### `utils/portfolio_aggregator.py` — the portfolio-level math
- `total_investment`, `current_value`, `overall_pnl` — straightforward sums/subtraction.
- **Risk profile**: computes a *weighted average beta* across holdings (weighted by each stock's
  current value — bigger positions count more), then buckets it:
  - beta < 0.8 → "Conservative"
  - 0.8 to 1.2 → "Moderate Growth"
  - \> 1.2 → "Aggressive"
  - (Beta measures how much a stock moves relative to the market — beta 1.0 moves with the market,
    higher beta = more volatile.)
- **Sector allocation**: groups current value by sector (from the fundamentals data), falling back
  to "Other" if sector is missing/unknown.

### `utils/config.py` — secrets resolution
```python
def get_secret(key: str) -> str:
    try:
        if key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    value = os.getenv(key)
    if value:
        return value
    raise KeyError(f"Missing required secret '{key}'...")
```
- Tries Streamlit's `secrets.toml` first, falls back to environment variables (which come from a
  `.env` file via `python-dotenv`). This exists so the app works whether you're running it locally
  with a `.env` file or deployed on Streamlit Cloud with `secrets.toml`.

### `parsers/csv_parser.py` / `excel_parser.py` — turning uploaded files into data
- Read the file with pandas, standardize column names (`"Avg. cost"` → `average_cost`, lowercase,
  strip punctuation), check all required columns exist, convert rows to a list of dicts.
- Return `None` on any failure (never raise) so the calling agent can handle it cleanly.

### `parsers/pdf_parser.py` — PDF statement parsing (a template, not a finished feature)
- Extracts raw text from the PDF with `pdfplumber`, then uses a regex (`HOLDINGS_LINE_PATTERN`) to
  find lines that look like `TICKER QTY AVG_COST INVESTED CUR_VAL P&L`.
- **Important honesty point for interviews:** this is explicitly a *generic template* — every
  broker formats their PDF statement differently, so this regex needs to be customized per broker.
  I added a `_debug_dump_text()` helper to make that customization easier (dump what `pdfplumber`
  actually extracts from a sample PDF so you can see what the regex needs to match).

---

## 5. Core Concepts Explained From Scratch

### Concept: LangGraph `StateGraph`
A finite-state machine where "state" is a Python dict and "transitions" are function calls. You
declare nodes (`add_node`), then edges (`add_edge` for unconditional, `add_conditional_edges` for
branching), set an `entry_point`, then `.compile()` it into a runnable `app`. Calling
`app.stream(initial_state)` runs it step by step and yields each node's output as it finishes.

### Concept: LangChain "chains" (`prompt | llm`)
```python
prompt = ChatPromptTemplate.from_template("Based on {data}, answer X")
chain = prompt | llm          # the "|" pipes the formatted prompt into the LLM
response = chain.invoke({"data": some_value})
print(response.content)       # the LLM's text answer
```
This is just "fill in a template string with values, send it to the model, read back `.content`."
The `|` operator comes from LangChain's "Runnable" interface — both prompts and LLMs implement a
common `.invoke()` interface, so they can be chained together.

### Concept: Defensive JSON extraction from LLM output
LLMs are asked to answer in JSON wrapped in ` ```json ... ``` `, but they don't always comply
perfectly. `extract_json_from_response()` tries a regex for the fenced version first, then a looser
regex for any `{...}` in the text, and raises if neither matches — the caller catches that and
falls back to a safe default (e.g., `"recommendation": "N/A"`) rather than crashing.

### Concept: Concurrency with `ThreadPoolExecutor`
```python
with ThreadPoolExecutor(max_workers=4) as executor:
    name_future = executor.submit(data_fetchers.get_stock_name, ticker)
    fundamentals_future = executor.submit(data_fetchers.get_fundamental_data, ticker)
    ...
    result = {"stock_name": name_future.result(), "fundamentals": fundamentals_future.result(), ...}
```
These are 4 independent network calls (to Yahoo Finance) for the *same* stock — none depends on
another's result, so instead of waiting for each one to finish before starting the next
(4x the latency), they're fired off together and we wait for all 4 at once (~1x the latency).
This is "I/O-bound concurrency" — the CPU isn't doing the work, it's waiting on the network, so
Python threads work fine here (no GIL issue, since threads release the GIL while waiting on I/O).
**Important:** the LLM calls are deliberately *not* parallelized this way — Groq's free tier has
strict per-minute rate limits, so running many stocks' LLM calls simultaneously risks getting
rate-limited/throttled. Only the "free," unlimited-ish yfinance calls were parallelized.

### Concept: Conditional edges / early exit
```python
def should_continue(state):
    return "end" if state.get("error") else "continue"
```
A plain function inspecting the shared state decides routing. This is the entire "branching logic"
of the graph — no ML/AI involved, just an if/else wrapped in LangGraph's edge API.

---

## 6. Key Design Decisions (the "Why" — this is what interviewers actually probe)

| Decision | Why |
|---|---|
| Multi-agent graph instead of one script | Modularity, inspectability, independent testability, easy to extend (e.g., adding the news step later without touching other agents) |
| 3 sequential LLM calls per stock instead of 1 | Mirrors human analyst reasoning (fundamentals → technicals → synthesis); narrower prompts are more reliable than one mega-prompt |
| LLM calls sequential, yfinance calls parallel | Groq free-tier rate limits make concurrent LLM calls risky; yfinance I/O calls are independent and safe to parallelize |
| yfinance news first, NewsAPI as fallback only | yfinance has no hard rate limit; NewsAPI's free tier does — using it only when needed conserves the limited quota |
| Every data-fetch function has a safe fallback (`'N/A'`, `{}`, `1.0`) | External APIs are unreliable; one bad/delisted ticker shouldn't crash the whole portfolio's analysis |
| `get_secret()` checks `st.secrets` then `os.getenv` | Supports both local `.env` development and Streamlit Cloud `secrets.toml` deployment with the same code |
| PDF parsing is a template, not a finished parser | Every broker's PDF layout differs; a generic regex can't cover all of them, so it's designed to be customized rather than pretending to be universal |
| Static NSE ticker list (not a live API call) | The screener's dropdown shouldn't depend on an external API being reachable just to list stock names; refreshed offline via a maintenance script instead |

---

## 7. Known Limitations & What I'd Improve (your strongest interview material)

Be upfront about these — it shows maturity, not weakness:

1. **PDF parsing is a template.** It will not work out-of-the-box for most real broker statements —
   `HOLDINGS_LINE_PATTERN` needs to be customized per broker.
2. **Static stock universe.** The screener's ticker list can drift out of date; needs periodic
   manual refresh via `scripts/refresh_stock_universe.py`.
3. **Originally, a `.env`-only setup was broken** — the code read secrets only via `st.secrets`,
   which ignores environment variables, so `load_dotenv()` had no effect. Fixed by adding
   `utils/config.get_secret()`, which checks `st.secrets` first and falls back to `os.getenv()`.
4. **Originally, a missing NewsAPI key crashed the entire news step**, not just the fallback,
   because client initialization happened in the same `try` block as the main loop. Fixed by
   isolating NewsAPI client setup into its own try/except so only the fallback path is disabled.
5. **No automated tests originally.** Added a `pytest` suite (`tests/`) mocking `yfinance` and
   `ChatGroq` so the whole pipeline can be tested offline, deterministically, without real API keys.
6. **Per-stock yfinance calls were fully sequential**, meaning 4 network round-trips per stock, one
   after another. Fixed with a `ThreadPoolExecutor` to run them concurrently (`fetch_stock_data()`).
7. **Originally, no rate-limit backoff/retry on Groq calls** — a single transient failure (rate
   limit, timeout, 5xx) would immediately fail that stock's whole analysis. Fixed by adding
   `utils/llm_retry.invoke_with_retry()`, which wraps every `chain.invoke(...)` call and retries
   `RateLimitError`/`APIConnectionError`/`APITimeoutError`/`InternalServerError` with exponential
   backoff (2s, 4s, 8s, ...) for up to 3 attempts before giving up.

**Remaining gap worth naming honestly:** even with retry/backoff, a large portfolio (e.g. 50 stocks
× 3 LLM calls each = 150 sequential Groq requests) is still slow end-to-end, and persistent rate
limiting (not just transient blips) will still eventually fail — the retry helps with flakiness, not
with genuinely exceeding your quota. A production version would likely need request batching,
caching, or a background job queue instead of doing all of this inline in one web request.

---

## 8. Interview Q&A Bank

### Conceptual / "explain it like I don't know your project"
**Q: What does this project do, in 30 seconds?**
A: "It's a Streamlit app where you upload your stock portfolio statement, and a multi-agent pipeline
built with LangGraph fetches live market data per stock, runs it through an LLM to get a chain-of-
thought Buy/Hold/Sell recommendation, pulls recent news, and renders a dashboard with P&L, risk
profile, and sector allocation."

**Q: Why LangGraph instead of just writing a normal Python script?**
A: "The pipeline has distinct phases — parse, validate, enrich, fetch news, report — each with
different failure modes. LangGraph lets me express that as an explicit graph with conditional
early-exit edges, so a parsing failure cleanly stops the pipeline instead of crashing three steps
downstream with corrupted data. It also makes each phase independently testable and lets the UI
stream live progress updates as each node completes."

**Q: What is 'state' in your graph?**
A: "A plain Python dict that gets passed into every node and updated by each node's return value.
It holds things like `portfolio_data`, `stock_analysis_results`, `news`, `final_report`, and `error`.
LangGraph merges each node's returned dict into this shared state automatically."

**Q: How do you handle errors in the pipeline?**
A: "Each agent catches its own exceptions and, instead of raising, sets `state['error']`. After the
ingestion and validation nodes, I added a conditional edge (`should_continue`) that checks for that
key and routes straight to `END` if it's set, so the UI shows a clear error instead of a stack
trace or partial/corrupt results."

**Q: Why three separate LLM calls instead of one?**
A: "It mirrors how a human analyst actually reasons — first judge fundamentals, then judge
technicals, then synthesize both plus the stock's beta into a final call. Narrower prompts are also
more reliable than asking one giant prompt to do everything at once, and I get inspectable
intermediate verdicts for debugging."

**Q: How do you parse the LLM's response reliably?**
A: "The prompt asks for JSON fenced in a ```json code block. I regex-extract that, with a looser
fallback regex for any `{...}` in the text if the fence is missing, and if neither matches, I catch
that and fall back to a safe default like `'recommendation': 'N/A'` instead of crashing that stock's
analysis."

**Q: Why are the yfinance calls parallel but the LLM calls sequential?**
A: "The four yfinance calls per stock are independent network requests, so I run them concurrently
in a `ThreadPoolExecutor` — that's safe because they're I/O-bound and don't depend on each other.
The LLM calls stay sequential per stock because Groq's free tier has strict per-minute rate limits;
running many concurrently risks getting throttled, and I haven't added retry/backoff logic yet."

**Q: What's the risk profile calculation doing?**
A: "It computes a weighted average beta across all holdings, weighted by each stock's current
value, so bigger positions influence the result more. Then it buckets that into Conservative
(<0.8), Moderate Growth (0.8-1.2), or Aggressive (>1.2). Beta measures a stock's volatility
relative to the overall market."

**Q: How do you manage API keys/secrets?**
A: "Through a small `get_secret()` helper that checks Streamlit's `st.secrets` first, then falls
back to `os.getenv()` so the same code works with a local `.env` file (via python-dotenv) or a
deployed `secrets.toml` on Streamlit Cloud."

**Q: What would you change if you rebuilt this today?**
A: "Add retry/backoff for Groq rate limits so larger portfolios don't fail partway through, make
the PDF parser pluggable per broker instead of one generic regex, and consider batching the LLM
calls or caching per-ticker results so re-analyzing the same portfolio doesn't redo all the API
calls."

### Code-specific / "show me you understand your own code"
**Q: Walk me through what happens when `enrich_stocks` fails for one stock out of ten.**
A: "Each stock is processed inside its own try/except in the loop. If `fetch_stock_data` returns
empty fundamentals/technicals/price history, I raise a `ValueError` deliberately (a 'circuit
breaker'), which is caught, logged to `analysis_errors`, and the loop just moves to the next stock —
the other nine still get analyzed and the pipeline doesn't stop."

**Q: Where does `.NS` come from on tickers?**
A: "NSE (India's National Stock Exchange) tickers need a `.NS` suffix for Yahoo Finance to resolve
them, e.g. `RELIANCE` becomes `RELIANCE.NS`. That's appended once right before any yfinance call."

**Q: What's the difference between `agents/screener_agent.py` and the main graph agents?**
A: "The screener isn't part of the LangGraph pipeline at all — it's a plain function called
directly from the UI for one-off single-stock lookups. It doesn't need the multi-step
orchestration since it's just one data fetch + one LLM call."

**Q: How did you test this without hitting real APIs or spending LLM credits?**
A: "I mock `data_fetchers` functions and replace `ChatGroq` with a `FakeLLM` test double — a small
class implementing the same `.invoke()` interface that returns scripted responses — using
`pytest-mock`'s `mocker.patch()` at the import site inside each agent module. That makes the whole
pipeline testable offline and deterministically."

### "Gotcha" / deeper-dive questions
**Q: Why patch `agents.stock_analysis_agent.ChatGroq` instead of `langchain_groq.ChatGroq`?**
A: "Because of how Python imports work — `stock_analysis_agent.py` does
`from langchain_groq import ChatGroq`, which binds the name `ChatGroq` into that module's own
namespace. Patching the original `langchain_groq.ChatGroq` wouldn't affect the already-imported
name inside `stock_analysis_agent`. You have to patch it where it's *used*, not where it's defined."

**Q: Is this actually 'agentic AI,' or is it just an LLM pipeline?**
A: "Honestly, it's closer to a structured, fixed pipeline than true autonomous agents — the control
flow (which node runs next) is deterministic and defined by me upfront, not decided by the LLM
itself. 'Agent' here mostly means 'a function with one specific responsibility,' not an LLM that
plans its own next action. True agentic systems would let the model choose tools/next-steps
dynamically, which this doesn't do."

**Q: What's a real production risk in this design?**
A: "The Groq LLM calls have no retry/backoff, so a rate-limit error on stock #30 of 50 just logs an
error and moves on — the user silently gets a partial report. In production I'd want retry with
exponential backoff, and probably a queue/batching system rather than one request per stock inline
in a web request."

---

## 9. Elevator Pitches

### 15-second version (if asked "what projects have you worked on")
"A multi-agent portfolio analysis tool — upload your holdings, and a LangGraph pipeline fetches live
market data and runs it through an LLM for AI-generated Buy/Hold/Sell calls, risk profiling, and news
summarization."

### 60-second version (if asked to elaborate)
"It's called AlphaBot. You upload a stock portfolio CSV, and instead of one big script, I built the
backend as a 5-step LangGraph pipeline: ingest the file, validate its shape, enrich each stock with
live Yahoo Finance data and a 3-step chain-of-thought LLM analysis — fundamentals verdict, technical
verdict, then a final synthesis — fetch and summarize recent news, and assemble a final report. Each
step is an independent function operating on a shared state dict, with conditional edges that let
early failures short-circuit the pipeline cleanly. I also added concurrency for the per-stock market
data fetches since those are independent I/O calls, while keeping the LLM calls sequential to respect
Groq's rate limits. More recently I added a pytest suite with mocked LLM/API clients, fixed a couple
of real bugs around secrets resolution and error isolation, and documented the known limitations like
the PDF parser being a broker-specific template rather than a universal solution."

### If asked "what was the hardest part?"
"Getting reliable structured output from the LLM. It doesn't always return clean JSON, so I built a
defensive extractor that tries a fenced ```json block first, falls back to a looser regex, and if
neither parses, the code logs it and falls back to a safe default rather than crashing that stock's
analysis — so one bad AI response never takes down the whole portfolio report."

---

## 10. Quick Cheat Sheet (read this 5 minutes before the interview)

- **Project**: Streamlit app, portfolio upload → AI-enriched dashboard. Tech: Streamlit, LangGraph,
  LangChain + Groq (LLaMA model), yfinance, pandas, Plotly, pdfplumber/openpyxl, NewsAPI.
- **Graph = 5 nodes**: ingest → validate → enrich (core) → news → report. Shared state dict flows
  through all of them. Conditional edges after ingest/validate exit early on error.
- **Per-stock enrichment**: fetch 4 data points concurrently (thread pool) → 3 sequential LLM calls
  (fundamental verdict, technical verdict, synthesis) → defensive JSON parsing.
- **News**: yfinance first (free), NewsAPI fallback only if needed (rate-limited).
- **Risk profile**: value-weighted average beta → Conservative/Moderate Growth/Aggressive buckets.
- **Secrets**: `get_secret()` tries `st.secrets` then `os.getenv()` — works locally and deployed.
- **Screener tab**: standalone, not part of the graph — one function, one LLM call.
- **Tests**: `pytest` + `pytest-mock`, `FakeLLM` double standing in for `ChatGroq`, mocked
  `data_fetchers` — fully offline, no real API keys needed.
- **Known gaps I can speak to**: no LLM retry/backoff, PDF parser is a per-broker template, static
  ticker list needs manual refresh.
- **One-liner if your mind goes blank**: "It's a multi-agent LangGraph pipeline that turns a raw
  portfolio file into an AI-analyzed investment dashboard, one stock at a time."

---

## 11. Resume Points

**One-line summary (for a project list):**
"AI-powered portfolio analysis platform using a multi-agent LangGraph pipeline (Streamlit + Groq LLM
+ yfinance) with concurrent data fetching, defensive parsing, and a 77-test pytest suite."

**Resume bullets (pick 3-4 depending on space):**

- Designed and built a multi-agent LLM pipeline using **LangGraph's StateGraph** to orchestrate 5
  sequential agents (ingestion → validation → enrichment → news → reporting) with conditional
  early-exit edges for graceful error handling.
- Integrated **Groq LLM (Llama-4)** via LangChain for a chain-of-thought financial analysis
  workflow — separate fundamental/technical verdicts synthesized into a final Buy/Hold/Sell
  recommendation with urgency scoring.
- Built a portfolio risk engine computing weighted-beta risk profiles and sector allocation from
  live market data fetched via `yfinance`, with a hybrid news pipeline (yfinance primary, NewsAPI
  fallback) for resilience against rate limits.
- Optimized per-stock data enrichment with a `ThreadPoolExecutor`, parallelizing I/O-bound
  market-data calls while keeping LLM calls sequential to respect API rate limits.
- Wrote a 77-test **pytest** suite (parsers, agents, utils) using mocked LLM/API clients, enabling
  fully offline, deterministic CI without real API keys.
- Hardened file-ingestion parsers (CSV/XLSX/PDF) against malformed input and silent failure modes
  (e.g., fixed a crash on scanned/image-only PDF pages).

**Framing tips:**
- Lead with "multi-agent architecture" / "LangGraph" — that's the differentiator over a generic
  "chatbot wrapper" project; recruiters and interviewers increasingly filter for agentic-system
  experience.
- Mention the testing work explicitly — a lot of AI-demo projects have zero tests, so having a
  mocked offline suite signals engineering maturity, not just prototyping.
- Be ready to talk about *why* things are structured the way they are (sequential LLM calls for
  rate limits, hybrid news fallback, secrets resolution across `.env`/`st.secrets`) — that's where
  this stands out from a copy-paste tutorial project.
