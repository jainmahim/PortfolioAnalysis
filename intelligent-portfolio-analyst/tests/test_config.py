import pytest
import streamlit as st

from utils.config import get_secret


class TestGetSecret:
    def test_reads_from_streamlit_secrets_when_present(self, mocker):
        mocker.patch.object(st, "secrets", {"GROQ_API_KEY": "from-secrets-toml"})
        assert get_secret("GROQ_API_KEY") == "from-secrets-toml"

    def test_falls_back_to_env_var_when_no_secrets_toml(self, mocker, monkeypatch):
        # Simulate the real StreamlitSecretNotFoundError raised by `in st.secrets`
        # when no secrets.toml file exists anywhere on disk.
        class RaisingSecrets:
            def __contains__(self, key):
                raise RuntimeError("No secrets found")

        mocker.patch.object(st, "secrets", RaisingSecrets())
        monkeypatch.setenv("GROQ_API_KEY", "from-dot-env")

        assert get_secret("GROQ_API_KEY") == "from-dot-env"

    def test_falls_back_to_env_var_when_key_missing_from_secrets(self, mocker, monkeypatch):
        mocker.patch.object(st, "secrets", {})
        monkeypatch.setenv("NEWS_API_KEY", "from-dot-env-2")

        assert get_secret("NEWS_API_KEY") == "from-dot-env-2"

    def test_raises_keyerror_when_not_found_anywhere(self, mocker, monkeypatch):
        mocker.patch.object(st, "secrets", {})
        monkeypatch.delenv("GROQ_API_KEY", raising=False)

        with pytest.raises(KeyError):
            get_secret("GROQ_API_KEY")

    def test_streamlit_secrets_take_priority_over_env(self, mocker, monkeypatch):
        mocker.patch.object(st, "secrets", {"GROQ_API_KEY": "secrets-wins"})
        monkeypatch.setenv("GROQ_API_KEY", "env-loses")

        assert get_secret("GROQ_API_KEY") == "secrets-wins"
