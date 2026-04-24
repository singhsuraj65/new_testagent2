"""
utils/state.py
Session-state initialisation and automatic data loading.
"""

import streamlit as st
from data_loader import load_all, build_material_summary


def init_session_state():
    """Initialise every key required by the app (idempotent)."""
    defaults = [
        ("data",              None),
        ("summary",           None),
        ("azure_client",      None),
        ("agent_cache",       {}),
        ("sim_ran",           False),
        ("data_error",        ""),
        ("dis_ran",           False),
        ("cc_insight",        None),
        ("last_analysed_mat", None),
        ("material_labels",   {}),
        ("logged_in",        False),
        ("current_user",     None),
    ]
    for key, value in defaults:
        if key not in st.session_state:
            st.session_state[key] = value


def auto_load_data():
    """
    Load source data exactly once per session.
    Stores results in st.session_state.data / .summary / .material_labels.
    On failure stores the error string in st.session_state.data_error.
    """
    if st.session_state.data is not None or st.session_state.data_error:
        return  # already loaded (or already failed)

    try:
        st.session_state.data = load_all()
        st.session_state.summary = build_material_summary(
            st.session_state.data)
        st.session_state.material_labels = {
            row["material"]: row["name"]
            for _, row in st.session_state.summary.iterrows()
        }
    except Exception as exc:
        st.session_state.data_error = str(exc)
