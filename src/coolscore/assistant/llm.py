"""Thin access to Claude (official Anthropic SDK). Everything works without a key.

The key comes from ``ANTHROPIC_API_KEY`` (or the SDK's other credential
sources); the Streamlit app copies ``st.secrets["ANTHROPIC_API_KEY"]`` into the
environment. When no credential is configured, callers use their no-key
fallbacks (manual form, template explanations), so the public demo costs nothing.
"""

from __future__ import annotations

import os

from coolscore import config


def settings() -> dict:
    return config.settings()["llm"]


def available() -> bool:
    """True when an API key is configured (the no-key path never calls the network)."""
    return bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"))


def client():
    import anthropic

    return anthropic.Anthropic(timeout=float(settings().get("timeout_s", 30)), max_retries=2)
