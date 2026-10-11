import streamlit as st
import pytest


@pytest.fixture(autouse=True)
def streamlit_session_state():
    """
    Agents call st.session_state.analysis_logs.append(...) directly (see
    AGENTS.md). Outside of `streamlit run`, st.session_state works in
    "bare mode" without a ScriptRunContext, but it starts empty, so every
    test gets a fresh analysis_logs list to write into.
    """
    st.session_state.analysis_logs = []
    yield st.session_state.analysis_logs
