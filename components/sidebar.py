"""
components/sidebar.py
Renders the left sidebar: logo, AI-agent status, API-key input, data reload button,
and a button to open a modal chat window.
"""

import os
import streamlit as st
from streamlit_modal import Modal
from agent import get_azure_client
from utils.helpers import img_b64, AZURE_ENDPOINT, AZURE_API_VER
from data_loader import load_all, build_material_summary
from components.chatbot import render_chat_modal_content

_LOGO_PATH = os.path.join(os.path.dirname(__file__), "..", "image.jpeg")
_logo_b64  = img_b64(_LOGO_PATH)

# Define modal once at module level (so it persists across reruns)
_CHAT_MODAL = Modal(
    "💬 ARIA Chat Assistant",
    key="aria-chat-modal",
    padding=20,
    max_width=700
)


def render_sidebar():
    with st.sidebar:
        # Logo
        if _logo_b64:
            st.markdown(
                "<div style='padding:14px 12px 12px;border-bottom:1px solid var(--bl);"
                "display:flex;align-items:center;justify-content:center;'>"
                "<img src='data:image/jpeg;base64," + _logo_b64 + "' "
                "style='max-height:44px;max-width:170px;object-fit:contain;'/>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                "<div style='padding:14px 12px 12px;border-bottom:1px solid var(--bl);'>"
                "<div style='font-size:16px;font-weight:800;color:var(--t);'>MResult</div>"
                "<div style='font-size:9px;color:var(--t3);'>Supply Intelligence</div></div>",
                unsafe_allow_html=True,
            )

        # AI status
        ai_on = st.session_state.azure_client is not None
        dot   = "#22C55E" if ai_on else "#CBD5E1"
        lbl   = "AI Agent Online" if ai_on else "AI Agent Offline"
        pulse = "animation:pdot 2s infinite;" if ai_on else ""
        st.markdown(
            "<div style='padding:8px 12px;border-bottom:1px solid var(--bl);"
            "display:flex;align-items:center;gap:6px;'>"
            f"<div style='width:6px;height:6px;border-radius:50%;background:{dot};flex-shrink:0;{pulse}'></div>"
            f"<span style='font-size:10px;color:{dot};font-weight:600;'>{lbl}</span>"
            "<span style='margin-left:auto;font-size:9px;color:var(--t3);'>gpt-4o-mini</span>"
            "</div>",
            unsafe_allow_html=True,
        )

        # API key input
        st.markdown(
            "<div style='padding:8px 12px 4px;'><div style='font-size:9px;color:var(--t3);letter-spacing:0.8px;margin-bottom:4px;'>API KEY</div></div>",
            unsafe_allow_html=True,
        )
        azure_key = st.text_input(
            "k", "",
            type="password",
            placeholder="Azure OpenAI key…",
            label_visibility="collapsed",
            key="az_key",
        )
        if azure_key and not st.session_state.azure_client:
            try:
                st.session_state.azure_client = get_azure_client(
                    azure_key, AZURE_ENDPOINT, AZURE_API_VER
                )
            except Exception:
                pass

        # Reload data button
        st.markdown("<div style='padding:8px 12px;margin-top:8px;'>", unsafe_allow_html=True)
        if st.button("⟳ Reload Data", use_container_width=True, key="reload_data"):
            st.session_state.data = None
            st.session_state.summary = None
            st.session_state.data_error = ""
            try:
                st.session_state.data = load_all()
                st.session_state.summary = build_material_summary(st.session_state.data)
                st.session_state.material_labels = {
                    row["material"]: row["name"]
                    for _, row in st.session_state.summary.iterrows()
                }
                st.success("Data reloaded successfully!")
                st.rerun()
            except Exception as e:
                st.session_state.data_error = str(e)
                st.error(f"Reload failed: {e}")
        st.markdown("</div>", unsafe_allow_html=True)

        # Styled button to open modal
        st.markdown("---")
        st.markdown(
            """
            <style>
            .chat-button {
                background: linear-gradient(90deg, #0066CC, #0099FF);
                border: none;
                color: white !important;
                padding: 8px 12px;
                text-align: center;
                text-decoration: none;
                display: inline-block;
                font-size: 14px;
                font-weight: 600;
                border-radius: 20px;
                width: 100%;
                cursor: pointer;
                transition: all 0.3s ease;
                margin-top: 10px;
            }
            .chat-button:hover {
                background: linear-gradient(90deg, #0052A3, #0077CC);
                transform: scale(1.02);
                box-shadow: 0 2px 8px rgba(0,102,204,0.3);
            }
            </style>
            """,
            unsafe_allow_html=True
        )
        # Use a standard Streamlit button but override its style with CSS class
        # Alternatively, use st.markdown with HTML button and JavaScript, but simpler: apply CSS to st.button
        # We'll use st.button with custom CSS via data-testid? Not reliable. Instead, use HTML button with onclick.
        # But HTML button would require Streamlit rerun logic. Better to use st.button and override its class.
        # Let's use a standard st.button and apply CSS to its container.
        chat_clicked = st.button(
            "💬 Chat with ARIA",
            use_container_width=True,
            key="open_chat_btn",
            help="Open AI assistant in a popup window"
        )
        # Override button style via markdown (target the specific button using its data-testid)
        st.markdown(
            """
            <style>
            div[data-testid="stButton"] button[key="open_chat_btn"] {
                background: linear-gradient(90deg, #0066CC, #0099FF);
                color: white;
                border: none;
                font-weight: 600;
                border-radius: 20px;
                transition: all 0.3s ease;
            }
            div[data-testid="stButton"] button[key="open_chat_btn"]:hover {
                background: linear-gradient(90deg, #0052A3, #0077CC);
                transform: scale(1.02);
                box-shadow: 0 2px 8px rgba(0,102,204,0.3);
            }
            </style>
            """,
            unsafe_allow_html=True
        )
        if chat_clicked:
            _CHAT_MODAL.open()

    # Check modal state and render content if open
    if _CHAT_MODAL.is_open():
        with _CHAT_MODAL.container():
            render_chat_modal_content()

# """
# components/sidebar.py
# Renders the left sidebar: logo, AI-agent status, API-key input, data reload button, and a modal chat button.
# """

# import os
# import streamlit as st
# from streamlit_modal import Modal
# from agent import get_azure_client
# from utils.helpers import img_b64, AZURE_ENDPOINT, AZURE_API_VER
# from data_loader import load_all, build_material_summary
# from components.chatbot import render_chat_modal_content

# _LOGO_PATH = os.path.join(os.path.dirname(__file__), "..", "image.jpeg")
# _logo_b64  = img_b64(_LOGO_PATH)


# def render_sidebar():
#     with st.sidebar:
#         # Logo
#         if _logo_b64:
#             st.markdown(
#                 "<div style='padding:14px 12px 12px;border-bottom:1px solid var(--bl);"
#                 "display:flex;align-items:center;justify-content:center;'>"
#                 "<img src='data:image/jpeg;base64," + _logo_b64 + "' "
#                 "style='max-height:44px;max-width:170px;object-fit:contain;'/>",
#                 unsafe_allow_html=True,
#             )
#         else:
#             st.markdown(
#                 "<div style='padding:14px 12px 12px;border-bottom:1px solid var(--bl);'>"
#                 "<div style='font-size:16px;font-weight:800;color:var(--t);'>MResult</div>"
#                 "<div style='font-size:9px;color:var(--t3);'>Supply Intelligence</div></div>",
#                 unsafe_allow_html=True,
#             )

#         # AI status
#         ai_on = st.session_state.azure_client is not None
#         dot   = "#22C55E" if ai_on else "#CBD5E1"
#         lbl   = "AI Agent Online" if ai_on else "AI Agent Offline"
#         pulse = "animation:pdot 2s infinite;" if ai_on else ""
#         st.markdown(
#             "<div style='padding:8px 12px;border-bottom:1px solid var(--bl);"
#             "display:flex;align-items:center;gap:6px;'>"
#             f"<div style='width:6px;height:6px;border-radius:50%;background:{dot};flex-shrink:0;{pulse}'></div>"
#             f"<span style='font-size:10px;color:{dot};font-weight:600;'>{lbl}</span>"
#             "<span style='margin-left:auto;font-size:9px;color:var(--t3);'>gpt-4o-mini</span>"
#             "</div>",
#             unsafe_allow_html=True,
#         )

#         # API key input
#         st.markdown(
#             "<div style='padding:8px 12px 4px;'><div style='font-size:9px;color:var(--t3);letter-spacing:0.8px;margin-bottom:4px;'>API KEY</div></div>",
#             unsafe_allow_html=True,
#         )
#         azure_key = st.text_input(
#             "k", "",
#             type="password",
#             placeholder="Azure OpenAI key…",
#             label_visibility="collapsed",
#             key="az_key",
#         )
#         if azure_key and not st.session_state.azure_client:
#             try:
#                 st.session_state.azure_client = get_azure_client(
#                     azure_key, AZURE_ENDPOINT, AZURE_API_VER
#                 )
#             except Exception:
#                 pass

#         # Reload data button
#         st.markdown("<div style='padding:8px 12px;margin-top:8px;'>", unsafe_allow_html=True)
#         if st.button("⟳ Reload Data", use_container_width=True, key="reload_data"):
#             st.session_state.data = None
#             st.session_state.summary = None
#             st.session_state.data_error = ""
#             try:
#                 st.session_state.data = load_all()
#                 st.session_state.summary = build_material_summary(st.session_state.data)
#                 st.session_state.material_labels = {
#                     row["material"]: row["name"]
#                     for _, row in st.session_state.summary.iterrows()
#                 }
#                 st.success("Data reloaded successfully!")
#                 st.rerun()
#             except Exception as e:
#                 st.session_state.data_error = str(e)
#                 st.error(f"Reload failed: {e}")
#         st.markdown("</div>", unsafe_allow_html=True)

#         # ── Modal Chat Button ──────────────────────────────────────────────
#         st.markdown("---")
#         if st.button("💬 Chat with ARIA", use_container_width=True, key="open_chat_modal"):
#             # We'll store a flag to open the modal – but the modal itself must be created outside
#             # Actually, the modal needs to be defined once in the sidebar (outside the button logic)
#             # We'll define it after the button and check session state to open.
#             st.session_state.show_chat_modal = True

#     # Define modal outside the sidebar context (so it appears over the main area)
#     # But we need to define it in the sidebar function? Better define it in the main app.
#     # However, to keep everything self-contained, we'll define it here but the modal
#     # will be attached to the sidebar's DOM. It still works as an overlay.
#     modal = Modal(
#         "ARIA Chat Assistant",
#         key="aria-chat-modal",
#         padding=20,
#         max_width=700
#     )

#     if st.session_state.get("show_chat_modal", False):
#         modal.open()
#         st.session_state.show_chat_modal = False  # reset after opening

#     if modal.is_open():
#         with modal.container():
#             render_chat_modal_content()

# # """
# # components/sidebar.py
# # Renders the left sidebar: logo, AI-agent status, API-key input, data reload button, and chatbot.
# # """

# # import os
# # import streamlit as st
# # from agent import get_azure_client
# # from utils.helpers import img_b64, AZURE_ENDPOINT, AZURE_API_VER
# # from data_loader import load_all, build_material_summary
# # from components.chatbot import render_chatbot   # <-- import the chatbot

# # _LOGO_PATH = os.path.join(os.path.dirname(__file__), "..", "image.jpeg")
# # _logo_b64  = img_b64(_LOGO_PATH)


# # def render_sidebar():
# #     """Render the sidebar and handle Azure key authentication, data reload, and chatbot."""
# #     with st.sidebar:
# #         # ── Logo ──────────────────────────────────────────────────────────────
# #         if _logo_b64:
# #             st.markdown(
# #                 "<div style='padding:14px 12px 12px;border-bottom:1px solid var(--bl);"
# #                 "display:flex;align-items:center;justify-content:center;'>"
# #                 "<img src='data:image/jpeg;base64," + _logo_b64 + "' "
# #                 "style='max-height:44px;max-width:170px;object-fit:contain;'/>",
# #                 unsafe_allow_html=True,
# #             )
# #         else:
# #             st.markdown(
# #                 "<div style='padding:14px 12px 12px;border-bottom:1px solid var(--bl);'>"
# #                 "<div style='font-size:16px;font-weight:800;color:var(--t);'>MResult</div>"
# #                 "<div style='font-size:9px;color:var(--t3);'>Supply Intelligence</div></div>",
# #                 unsafe_allow_html=True,
# #             )

# #         # ── AI-agent status indicator ──────────────────────────────────────────
# #         ai_on = st.session_state.azure_client is not None
# #         dot   = "#22C55E" if ai_on else "#CBD5E1"
# #         lbl   = "AI Agent Online" if ai_on else "AI Agent Offline"
# #         pulse = "animation:pdot 2s infinite;" if ai_on else ""
# #         st.markdown(
# #             "<div style='padding:8px 12px;border-bottom:1px solid var(--bl);"
# #             "display:flex;align-items:center;gap:6px;'>"
# #             f"<div style='width:6px;height:6px;border-radius:50%;background:{dot};flex-shrink:0;{pulse}'></div>"
# #             f"<span style='font-size:10px;color:{dot};font-weight:600;'>{lbl}</span>"
# #             "<span style='margin-left:auto;font-size:9px;color:var(--t3);'>gpt-4o-mini</span>"
# #             "</div>",
# #             unsafe_allow_html=True,
# #         )

# #         # ── API-key input ──────────────────────────────────────────────────────
# #         st.markdown(
# #             "<div style='padding:8px 12px 4px;'>"
# #             "<div style='font-size:9px;color:var(--t3);letter-spacing:0.8px;margin-bottom:4px;'>API KEY</div>"
# #             "</div>",
# #             unsafe_allow_html=True,
# #         )
# #         azure_key = st.text_input(
# #             "k", "",
# #             type="password",
# #             placeholder="Azure OpenAI key…",
# #             label_visibility="collapsed",
# #             key="az_key",
# #         )
# #         if azure_key and not st.session_state.azure_client:
# #             try:
# #                 st.session_state.azure_client = get_azure_client(
# #                     azure_key, AZURE_ENDPOINT, AZURE_API_VER
# #                 )
# #             except Exception:
# #                 pass

# #         # ── Data reload button ─────────────────────────────────────────────────
# #         st.markdown("<div style='padding:8px 12px;margin-top:8px;'>", unsafe_allow_html=True)
# #         if st.button("⟳ Reload Data", use_container_width=True, key="reload_data"):
# #             st.session_state.data = None
# #             st.session_state.summary = None
# #             st.session_state.data_error = ""
# #             try:
# #                 st.session_state.data = load_all()
# #                 st.session_state.summary = build_material_summary(st.session_state.data)
# #                 st.session_state.material_labels = {
# #                     row["material"]: row["name"]
# #                     for _, row in st.session_state.summary.iterrows()
# #                 }
# #                 st.success("Data reloaded successfully!")
# #                 st.rerun()
# #             except Exception as e:
# #                 st.session_state.data_error = str(e)
# #                 st.error(f"Reload failed: {e}")
# #         st.markdown("</div>", unsafe_allow_html=True)

# #         # ── Chatbot (new) ──────────────────────────────────────────────────────
# #         render_chatbot()

# #         # ── Footer ────────────────────────────────────────────────────────────
# #         st.markdown(
# #             "<div style='padding:6px 12px;border-top:1px solid var(--bl);margin-top:8px;'>"
# #             "<div style='font-size:9px;color:var(--t3);'>FI11 Turku · Apr 2026</div></div>",
# #             unsafe_allow_html=True,
# #         )

# # # # """
# # # # components/sidebar.py
# # # # Renders the left sidebar: logo, AI-agent status, and Azure API-key input.
# # # # """

# # # # import os
# # # # import streamlit as st
# # # # from agent import get_azure_client
# # # # from utils.helpers import img_b64, AZURE_ENDPOINT, AZURE_API_VER

# # # # _LOGO_PATH = os.path.join(os.path.dirname(__file__), "..", "image.jpeg")
# # # # _logo_b64  = img_b64(_LOGO_PATH)


# # # # def render_sidebar():
# # # #     """Render the sidebar and handle Azure key authentication."""
# # # #     with st.sidebar:
# # # #         # ── Logo ──────────────────────────────────────────────────────────────
# # # #         if _logo_b64:
# # # #             st.markdown(
# # # #                 "<div style='padding:14px 12px 12px;border-bottom:1px solid var(--bl);"
# # # #                 "display:flex;align-items:center;justify-content:center;'>"
# # # #                 "<img src='data:image/jpeg;base64," + _logo_b64 + "' "
# # # #                 "style='max-height:44px;max-width:170px;object-fit:contain;'/>",
# # # #                 unsafe_allow_html=True,
# # # #             )
# # # #         else:
# # # #             st.markdown(
# # # #                 "<div style='padding:14px 12px 12px;border-bottom:1px solid var(--bl);'>"
# # # #                 "<div style='font-size:16px;font-weight:800;color:var(--t);'>MResult</div>"
# # # #                 "<div style='font-size:9px;color:var(--t3);'>Supply Intelligence</div></div>",
# # # #                 unsafe_allow_html=True,
# # # #             )

# # # #         # ── AI-agent status indicator ──────────────────────────────────────────
# # # #         ai_on = st.session_state.azure_client is not None
# # # #         dot   = "#22C55E" if ai_on else "#CBD5E1"
# # # #         lbl   = "AI Agent Online" if ai_on else "AI Agent Offline"
# # # #         pulse = "animation:pdot 2s infinite;" if ai_on else ""
# # # #         st.markdown(
# # # #             "<div style='padding:8px 12px;border-bottom:1px solid var(--bl);"
# # # #             "display:flex;align-items:center;gap:6px;'>"
# # # #             f"<div style='width:6px;height:6px;border-radius:50%;background:{dot};flex-shrink:0;{pulse}'></div>"
# # # #             f"<span style='font-size:10px;color:{dot};font-weight:600;'>{lbl}</span>"
# # # #             "<span style='margin-left:auto;font-size:9px;color:var(--t3);'>gpt-4o-mini</span>"
# # # #             "</div>",
# # # #             unsafe_allow_html=True,
# # # #         )

# # # #         # ── API-key input ──────────────────────────────────────────────────────
# # # #         st.markdown(
# # # #             "<div style='padding:8px 12px 4px;'>"
# # # #             "<div style='font-size:9px;color:var(--t3);letter-spacing:0.8px;margin-bottom:4px;'>API KEY</div>"
# # # #             "</div>",
# # # #             unsafe_allow_html=True,
# # # #         )
# # # #         azure_key = st.text_input(
# # # #             "k", "",
# # # #             type="password",
# # # #             placeholder="Azure OpenAI key…",
# # # #             label_visibility="collapsed",
# # # #             key="az_key",
# # # #         )
# # # #         if azure_key and not st.session_state.azure_client:
# # # #             try:
# # # #                 st.session_state.azure_client = get_azure_client(
# # # #                     azure_key, AZURE_ENDPOINT, AZURE_API_VER
# # # #                 )
# # # #             except Exception:
# # # #                 pass

# # # #         # ── Footer ────────────────────────────────────────────────────────────
# # # #         st.markdown(
# # # #             "<div style='padding:6px 12px;border-top:1px solid var(--bl);margin-top:8px;'>"
# # # #             "<div style='font-size:9px;color:var(--t3);'>FI11 Turku · Apr 2026</div></div>",
# # # #             unsafe_allow_html=True,
# # # #         )

# # # """
# # # components/sidebar.py
# # # Renders the left sidebar: logo, AI-agent status, API-key input, and a data reload button.
# # # """

# # # import os
# # # import streamlit as st
# # # from agent import get_azure_client
# # # from utils.helpers import img_b64, AZURE_ENDPOINT, AZURE_API_VER
# # # from data_loader import load_all, build_material_summary

# # # _LOGO_PATH = os.path.join(os.path.dirname(__file__), "..", "image.jpeg")
# # # _logo_b64  = img_b64(_LOGO_PATH)


# # # def render_sidebar():
# # #     """Render the sidebar and handle Azure key authentication and data reload."""
# # #     with st.sidebar:
# # #         # ── Logo ──────────────────────────────────────────────────────────────
# # #         if _logo_b64:
# # #             st.markdown(
# # #                 "<div style='padding:14px 12px 12px;border-bottom:1px solid var(--bl);"
# # #                 "display:flex;align-items:center;justify-content:center;'>"
# # #                 "<img src='data:image/jpeg;base64," + _logo_b64 + "' "
# # #                 "style='max-height:44px;max-width:170px;object-fit:contain;'/>",
# # #                 unsafe_allow_html=True,
# # #             )
# # #         else:
# # #             st.markdown(
# # #                 "<div style='padding:14px 12px 12px;border-bottom:1px solid var(--bl);'>"
# # #                 "<div style='font-size:16px;font-weight:800;color:var(--t);'>MResult</div>"
# # #                 "<div style='font-size:9px;color:var(--t3);'>Supply Intelligence</div></div>",
# # #                 unsafe_allow_html=True,
# # #             )

# # #         # ── AI-agent status indicator ──────────────────────────────────────────
# # #         ai_on = st.session_state.azure_client is not None
# # #         dot   = "#22C55E" if ai_on else "#CBD5E1"
# # #         lbl   = "AI Agent Online" if ai_on else "AI Agent Offline"
# # #         pulse = "animation:pdot 2s infinite;" if ai_on else ""
# # #         st.markdown(
# # #             "<div style='padding:8px 12px;border-bottom:1px solid var(--bl);"
# # #             "display:flex;align-items:center;gap:6px;'>"
# # #             f"<div style='width:6px;height:6px;border-radius:50%;background:{dot};flex-shrink:0;{pulse}'></div>"
# # #             f"<span style='font-size:10px;color:{dot};font-weight:600;'>{lbl}</span>"
# # #             "<span style='margin-left:auto;font-size:9px;color:var(--t3);'>gpt-4o-mini</span>"
# # #             "</div>",
# # #             unsafe_allow_html=True,
# # #         )

# # #         # ── API-key input ──────────────────────────────────────────────────────
# # #         st.markdown(
# # #             "<div style='padding:8px 12px 4px;'>"
# # #             "<div style='font-size:9px;color:var(--t3);letter-spacing:0.8px;margin-bottom:4px;'>API KEY</div>"
# # #             "</div>",
# # #             unsafe_allow_html=True,
# # #         )
# # #         azure_key = st.text_input(
# # #             "k", "",
# # #             type="password",
# # #             placeholder="Azure OpenAI key…",
# # #             label_visibility="collapsed",
# # #             key="az_key",
# # #         )
# # #         if azure_key and not st.session_state.azure_client:
# # #             try:
# # #                 st.session_state.azure_client = get_azure_client(
# # #                     azure_key, AZURE_ENDPOINT, AZURE_API_VER
# # #                 )
# # #             except Exception:
# # #                 pass

# # #         # ── Data reload button ─────────────────────────────────────────────────
# # #         st.markdown("<div style='padding:8px 12px;margin-top:8px;'>", unsafe_allow_html=True)
# # #         if st.button("⟳ Reload Data", use_container_width=True, key="reload_data"):
# # #             # Clear the cached data and summary
# # #             st.session_state.data = None
# # #             st.session_state.summary = None
# # #             st.session_state.data_error = ""
# # #             # Force immediate reload
# # #             try:
# # #                 st.session_state.data = load_all()
# # #                 st.session_state.summary = build_material_summary(st.session_state.data)
# # #                 st.session_state.material_labels = {
# # #                     row["material"]: row["name"]
# # #                     for _, row in st.session_state.summary.iterrows()
# # #                 }
# # #                 st.success("Data reloaded successfully!")
# # #                 st.rerun()
# # #             except Exception as e:
# # #                 st.session_state.data_error = str(e)
# # #                 st.error(f"Reload failed: {e}")
# # #         st.markdown("</div>", unsafe_allow_html=True)

# # #         # ── Footer ────────────────────────────────────────────────────────────
# # #         st.markdown(
# # #             "<div style='padding:6px 12px;border-top:1px solid var(--bl);margin-top:8px;'>"
# # #             "<div style='font-size:9px;color:var(--t3);'>FI11 Turku · Apr 2026</div></div>",
# # #             unsafe_allow_html=True,
# # #         )
