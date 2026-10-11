import os
import streamlit as st


def get_secret(key: str) -> str:
    """
    Resolve a required secret/API key, preferring Streamlit's secrets store
    (`.streamlit/secrets.toml`) and falling back to an environment variable
    (e.g. loaded from `.env` via python-dotenv's `load_dotenv()`).

    `st.secrets` raises if no secrets.toml exists at all, so that lookup is
    guarded and treated as "not found" rather than letting it bubble up.
    """
    try:
        if key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass

    value = os.getenv(key)
    if value:
        return value

    raise KeyError(
        f"Missing required secret '{key}'. Set it in a .env file in the project "
        f"root (loaded via python-dotenv) or in .streamlit/secrets.toml."
    )
