"""
components/sidebar.py
Renders the left sidebar with custom width, compact chat, and all controls.
"""

import os
import streamlit as st
from agent import get_azure_client
from utils.helpers import img_b64, AZURE_ENDPOINT, AZURE_API_VER
from data_loader import load_all, build_material_summary
from components.chatbot import render_sidebar_chat

_LOGO_PATH = os.path.join(os.path.dirname(__file__), "..", "image.jpeg")
_logo_b64 = img_b64(_LOGO_PATH)

# ============================================================
# Set sidebar width (simple and works)
# ============================================================
st.markdown(
    """
    <style>
        section[data-testid="stSidebar"] {
            width: 380px !important;
            min-width: 380px !important;
        }
        /* Make fonts slightly smaller inside sidebar */
        .stSidebar .stMarkdown, 
        .stSidebar .stText, 
        .stSidebar .stButton, 
        .stSidebar .stChatMessage,
        .stSidebar .stChatInput {
            font-size: 12px !important;
        }
        .stSidebar .stButton button {
            font-size: 12px !important;
            padding: 4px 8px !important;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


def render_sidebar():
    with st.sidebar:
        # Logo
        if _logo_b64:
            st.markdown(
                "<div style='padding:10px 0 10px 0;border-bottom:1px solid var(--bl);"
                "display:flex;align-items:center;justify-content:center;'>"
                "<img src='data:image/jpeg;base64," + _logo_b64 + "' "
                "style='max-height:38px;max-width:150px;object-fit:contain;'/>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                "<div style='padding:10px 0;border-bottom:1px solid var(--bl);'>"
                "<div style='font-size:14px;font-weight:800;color:var(--t);'>MResult</div>"
                "<div style='font-size:8px;color:var(--t3);'>Supply Intelligence</div></div>",
                unsafe_allow_html=True,
            )

        # AI status
        ai_on = st.session_state.azure_client is not None
        dot = "#22C55E" if ai_on else "#CBD5E1"
        lbl = "AI Agent Online" if ai_on else "AI Agent Offline"
        pulse = "animation:pdot 2s infinite;" if ai_on else ""
        st.markdown(
            "<div style='padding:6px 0;border-bottom:1px solid var(--bl);"
            "display:flex;align-items:center;gap:6px;'>"
            f"<div style='width:6px;height:6px;border-radius:50%;background:{dot};flex-shrink:0;{pulse}'></div>"
            f"<span style='font-size:9px;color:{dot};font-weight:600;'>{lbl}</span>"
            "<span style='margin-left:auto;font-size:8px;color:var(--t3);'>gpt-4o-mini</span>"
            "</div>",
            unsafe_allow_html=True,
        )

        # API key input
        st.markdown(
            "<div style='padding:4px 0 2px;'><div style='font-size:8px;color:var(--t3);letter-spacing:0.8px;'>API KEY</div></div>",
            unsafe_allow_html=True,
        )
        azure_key = st.text_input(
            "k",
            "",
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

        # # ── Inline Chat ──────────────────────────────────────────────
        # render_sidebar_chat()

        # Footer
        st.markdown(
            "<div style='padding:6px 0;border-top:1px solid var(--bl);margin-top:12px;'>"
            "<div style='font-size:8px;color:var(--t3);'>FI11 Turku · Apr 2026</div></div>",
            unsafe_allow_html=True,
        )

# """
# components/sidebar.py
# Renders the left sidebar with wider width, smaller fonts, and inline chat.
# """

# import os
# import streamlit as st
# from agent import get_azure_client
# from utils.helpers import img_b64, AZURE_ENDPOINT, AZURE_API_VER
# from data_loader import load_all, build_material_summary
# from components.chatbot import render_sidebar_chat

# _LOGO_PATH = os.path.join(os.path.dirname(__file__), "..", "image.jpeg")
# _logo_b64 = img_b64(_LOGO_PATH)

# # ============================================================
# # Force sidebar width to 400px and adjust fonts
# # ============================================================
# st.markdown(
#     """
#     <style>
#         /* Increase sidebar width */
#         section[data-testid="stSidebar"] {
#             min-width: 400px !important;
#             width: 400px !important;
#         }
#         /* Main content area adjusts automatically */
#         /* Smaller fonts inside sidebar */
#         .stSidebar .stMarkdown,
#         .stSidebar .stText,
#         .stSidebar .stButton,
#         .stSidebar .stCaption,
#         .stSidebar .stChatMessage,
#         .stSidebar .stChatInput {
#             font-size: 12px !important;
#         }
#         .stSidebar .stMarkdown h1,
#         .stSidebar .stMarkdown h2,
#         .stSidebar .stMarkdown h3 {
#             font-size: 14px !important;
#         }
#         .stSidebar .stButton button {
#             font-size: 12px !important;
#             padding: 4px 8px !important;
#         }
#         /* Chat input box smaller */
#         .stSidebar .stChatInput textarea {
#             font-size: 12px !important;
#         }
#     </style>
#     """,
#     unsafe_allow_html=True,
# )


# def render_sidebar():
#     with st.sidebar:
#         # Logo
#         if _logo_b64:
#             st.markdown(
#                 "<div style='padding:10px 0 10px 0;border-bottom:1px solid var(--bl);"
#                 "display:flex;align-items:center;justify-content:center;'>"
#                 "<img src='data:image/jpeg;base64," + _logo_b64 + "' "
#                 "style='max-height:38px;max-width:150px;object-fit:contain;'/>",
#                 unsafe_allow_html=True,
#             )
#         else:
#             st.markdown(
#                 "<div style='padding:10px 0;border-bottom:1px solid var(--bl);'>"
#                 "<div style='font-size:14px;font-weight:800;color:var(--t);'>MResult</div>"
#                 "<div style='font-size:8px;color:var(--t3);'>Supply Intelligence</div></div>",
#                 unsafe_allow_html=True,
#             )

#         # AI status indicator
#         ai_on = st.session_state.azure_client is not None
#         dot = "#22C55E" if ai_on else "#CBD5E1"
#         lbl = "AI Agent Online" if ai_on else "AI Agent Offline"
#         pulse = "animation:pdot 2s infinite;" if ai_on else ""
#         st.markdown(
#             "<div style='padding:6px 0;border-bottom:1px solid var(--bl);"
#             "display:flex;align-items:center;gap:6px;'>"
#             f"<div style='width:6px;height:6px;border-radius:50%;background:{dot};flex-shrink:0;{pulse}'></div>"
#             f"<span style='font-size:9px;color:{dot};font-weight:600;'>{lbl}</span>"
#             "<span style='margin-left:auto;font-size:8px;color:var(--t3);'>gpt-4o-mini</span>"
#             "</div>",
#             unsafe_allow_html=True,
#         )

#         # API key input
#         st.markdown(
#             "<div style='padding:4px 0 2px;'><div style='font-size:8px;color:var(--t3);letter-spacing:0.8px;'>API KEY</div></div>",
#             unsafe_allow_html=True,
#         )
#         azure_key = st.text_input(
#             "k",
#             "",
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

#         # ── Inline Chat ──────────────────────────────────────────────
#         render_sidebar_chat()

#         # Footer
#         st.markdown(
#             "<div style='padding:6px 0;border-top:1px solid var(--bl);margin-top:12px;'>"
#             "<div style='font-size:8px;color:var(--t3);'>FI11 Turku · Apr 2026</div></div>",
#             unsafe_allow_html=True,
#         )

# # """
# # components/sidebar.py
# # Renders the left sidebar with wider width, smaller fonts, and inline chat.
# # """

# # import os
# # import streamlit as st
# # from agent import get_azure_client
# # from utils.helpers import img_b64, AZURE_ENDPOINT, AZURE_API_VER
# # from data_loader import load_all, build_material_summary
# # from components.chatbot import render_sidebar_chat

# # _LOGO_PATH = os.path.join(os.path.dirname(__file__), "..", "image.jpeg")
# # _logo_b64  = img_b64(_LOGO_PATH)

# # # Increase sidebar width and make fonts smaller globally inside sidebar
# # st.markdown(
# #     """
# #     <style>
# #         [data-testid="stSidebar"] {
# #             min-width: 320px;
# #             width: 320px;
# #         }
# #         [data-testid="stSidebar"] .stMarkdown, 
# #         [data-testid="stSidebar"] .stText, 
# #         [data-testid="stSidebar"] .stButton, 
# #         [data-testid="stSidebar"] .stCaption,
# #         [data-testid="stSidebar"] .stChatMessage,
# #         [data-testid="stSidebar"] .stChatInput {
# #             font-size: 12px !important;
# #         }
# #         [data-testid="stSidebar"] .stMarkdown h1, 
# #         [data-testid="stSidebar"] .stMarkdown h2, 
# #         [data-testid="stSidebar"] .stMarkdown h3 {
# #             font-size: 14px !important;
# #         }
# #         [data-testid="stSidebar"] .stButton button {
# #             font-size: 12px !important;
# #             padding: 4px 8px !important;
# #         }
# #     </style>
# #     """,
# #     unsafe_allow_html=True,
# # )


# # def render_sidebar():
# #     with st.sidebar:
# #         # Logo
# #         if _logo_b64:
# #             st.markdown(
# #                 "<div style='padding:10px 0 10px 0;border-bottom:1px solid var(--bl);"
# #                 "display:flex;align-items:center;justify-content:center;'>"
# #                 "<img src='data:image/jpeg;base64," + _logo_b64 + "' "
# #                 "style='max-height:38px;max-width:150px;object-fit:contain;'/>",
# #                 unsafe_allow_html=True,
# #             )
# #         else:
# #             st.markdown(
# #                 "<div style='padding:10px 0;border-bottom:1px solid var(--bl);'>"
# #                 "<div style='font-size:14px;font-weight:800;color:var(--t);'>MResult</div>"
# #                 "<div style='font-size:8px;color:var(--t3);'>Supply Intelligence</div></div>",
# #                 unsafe_allow_html=True,
# #             )

# #         # AI status
# #         ai_on = st.session_state.azure_client is not None
# #         dot   = "#22C55E" if ai_on else "#CBD5E1"
# #         lbl   = "AI Agent Online" if ai_on else "AI Agent Offline"
# #         pulse = "animation:pdot 2s infinite;" if ai_on else ""
# #         st.markdown(
# #             "<div style='padding:6px 0;border-bottom:1px solid var(--bl);"
# #             "display:flex;align-items:center;gap:6px;'>"
# #             f"<div style='width:6px;height:6px;border-radius:50%;background:{dot};flex-shrink:0;{pulse}'></div>"
# #             f"<span style='font-size:9px;color:{dot};font-weight:600;'>{lbl}</span>"
# #             "<span style='margin-left:auto;font-size:8px;color:var(--t3);'>gpt-4o-mini</span>"
# #             "</div>",
# #             unsafe_allow_html=True,
# #         )

# #         # API key input
# #         st.markdown(
# #             "<div style='padding:4px 0 2px;'><div style='font-size:8px;color:var(--t3);letter-spacing:0.8px;'>API KEY</div></div>",
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

# #         # Reload data button
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

# #         # ── Inline Chat ──────────────────────────────────────────────
# #         render_sidebar_chat()

# #         # Footer
# #         st.markdown(
# #             "<div style='padding:6px 0;border-top:1px solid var(--bl);margin-top:12px;'>"
# #             "<div style='font-size:8px;color:var(--t3);'>FI11 Turku · Apr 2026</div></div>",
# #             unsafe_allow_html=True,
# #         )


# # # """
# # # components/sidebar.py
# # # Renders the left sidebar: logo, AI-agent status, API-key input, data reload button, and chatbot.
# # # """

# # # import os
# # # import streamlit as st
# # # from agent import get_azure_client
# # # from utils.helpers import img_b64, AZURE_ENDPOINT, AZURE_API_VER
# # # from data_loader import load_all, build_material_summary
# # # from components.chatbot import render_chatbot   # <-- import the chatbot

# # # _LOGO_PATH = os.path.join(os.path.dirname(__file__), "..", "image.jpeg")
# # # _logo_b64  = img_b64(_LOGO_PATH)


# # # def render_sidebar():
# # #     """Render the sidebar and handle Azure key authentication, data reload, and chatbot."""
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
# # #             st.session_state.data = None
# # #             st.session_state.summary = None
# # #             st.session_state.data_error = ""
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

# # #         # ── Chatbot (new) ──────────────────────────────────────────────────────
# # #         render_chatbot()

# # #         # ── Footer ────────────────────────────────────────────────────────────
# # #         st.markdown(
# # #             "<div style='padding:6px 12px;border-top:1px solid var(--bl);margin-top:8px;'>"
# # #             "<div style='font-size:9px;color:var(--t3);'>FI11 Turku · Apr 2026</div></div>",
# # #             unsafe_allow_html=True,
# # #         )

# # # # # """
# # # # # components/sidebar.py
# # # # # Renders the left sidebar: logo, AI-agent status, and Azure API-key input.
# # # # # """

# # # # # import os
# # # # # import streamlit as st
# # # # # from agent import get_azure_client
# # # # # from utils.helpers import img_b64, AZURE_ENDPOINT, AZURE_API_VER

# # # # # _LOGO_PATH = os.path.join(os.path.dirname(__file__), "..", "image.jpeg")
# # # # # _logo_b64  = img_b64(_LOGO_PATH)


# # # # # def render_sidebar():
# # # # #     """Render the sidebar and handle Azure key authentication."""
# # # # #     with st.sidebar:
# # # # #         # ── Logo ──────────────────────────────────────────────────────────────
# # # # #         if _logo_b64:
# # # # #             st.markdown(
# # # # #                 "<div style='padding:14px 12px 12px;border-bottom:1px solid var(--bl);"
# # # # #                 "display:flex;align-items:center;justify-content:center;'>"
# # # # #                 "<img src='data:image/jpeg;base64," + _logo_b64 + "' "
# # # # #                 "style='max-height:44px;max-width:170px;object-fit:contain;'/>",
# # # # #                 unsafe_allow_html=True,
# # # # #             )
# # # # #         else:
# # # # #             st.markdown(
# # # # #                 "<div style='padding:14px 12px 12px;border-bottom:1px solid var(--bl);'>"
# # # # #                 "<div style='font-size:16px;font-weight:800;color:var(--t);'>MResult</div>"
# # # # #                 "<div style='font-size:9px;color:var(--t3);'>Supply Intelligence</div></div>",
# # # # #                 unsafe_allow_html=True,
# # # # #             )

# # # # #         # ── AI-agent status indicator ──────────────────────────────────────────
# # # # #         ai_on = st.session_state.azure_client is not None
# # # # #         dot   = "#22C55E" if ai_on else "#CBD5E1"
# # # # #         lbl   = "AI Agent Online" if ai_on else "AI Agent Offline"
# # # # #         pulse = "animation:pdot 2s infinite;" if ai_on else ""
# # # # #         st.markdown(
# # # # #             "<div style='padding:8px 12px;border-bottom:1px solid var(--bl);"
# # # # #             "display:flex;align-items:center;gap:6px;'>"
# # # # #             f"<div style='width:6px;height:6px;border-radius:50%;background:{dot};flex-shrink:0;{pulse}'></div>"
# # # # #             f"<span style='font-size:10px;color:{dot};font-weight:600;'>{lbl}</span>"
# # # # #             "<span style='margin-left:auto;font-size:9px;color:var(--t3);'>gpt-4o-mini</span>"
# # # # #             "</div>",
# # # # #             unsafe_allow_html=True,
# # # # #         )

# # # # #         # ── API-key input ──────────────────────────────────────────────────────
# # # # #         st.markdown(
# # # # #             "<div style='padding:8px 12px 4px;'>"
# # # # #             "<div style='font-size:9px;color:var(--t3);letter-spacing:0.8px;margin-bottom:4px;'>API KEY</div>"
# # # # #             "</div>",
# # # # #             unsafe_allow_html=True,
# # # # #         )
# # # # #         azure_key = st.text_input(
# # # # #             "k", "",
# # # # #             type="password",
# # # # #             placeholder="Azure OpenAI key…",
# # # # #             label_visibility="collapsed",
# # # # #             key="az_key",
# # # # #         )
# # # # #         if azure_key and not st.session_state.azure_client:
# # # # #             try:
# # # # #                 st.session_state.azure_client = get_azure_client(
# # # # #                     azure_key, AZURE_ENDPOINT, AZURE_API_VER
# # # # #                 )
# # # # #             except Exception:
# # # # #                 pass

# # # # #         # ── Footer ────────────────────────────────────────────────────────────
# # # # #         st.markdown(
# # # # #             "<div style='padding:6px 12px;border-top:1px solid var(--bl);margin-top:8px;'>"
# # # # #             "<div style='font-size:9px;color:var(--t3);'>FI11 Turku · Apr 2026</div></div>",
# # # # #             unsafe_allow_html=True,
# # # # #         )

# # # # """
# # # # components/sidebar.py
# # # # Renders the left sidebar: logo, AI-agent status, API-key input, and a data reload button.
# # # # """

# # # # import os
# # # # import streamlit as st
# # # # from agent import get_azure_client
# # # # from utils.helpers import img_b64, AZURE_ENDPOINT, AZURE_API_VER
# # # # from data_loader import load_all, build_material_summary

# # # # _LOGO_PATH = os.path.join(os.path.dirname(__file__), "..", "image.jpeg")
# # # # _logo_b64  = img_b64(_LOGO_PATH)


# # # # def render_sidebar():
# # # #     """Render the sidebar and handle Azure key authentication and data reload."""
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

# # # #         # ── Data reload button ─────────────────────────────────────────────────
# # # #         st.markdown("<div style='padding:8px 12px;margin-top:8px;'>", unsafe_allow_html=True)
# # # #         if st.button("⟳ Reload Data", use_container_width=True, key="reload_data"):
# # # #             # Clear the cached data and summary
# # # #             st.session_state.data = None
# # # #             st.session_state.summary = None
# # # #             st.session_state.data_error = ""
# # # #             # Force immediate reload
# # # #             try:
# # # #                 st.session_state.data = load_all()
# # # #                 st.session_state.summary = build_material_summary(st.session_state.data)
# # # #                 st.session_state.material_labels = {
# # # #                     row["material"]: row["name"]
# # # #                     for _, row in st.session_state.summary.iterrows()
# # # #                 }
# # # #                 st.success("Data reloaded successfully!")
# # # #                 st.rerun()
# # # #             except Exception as e:
# # # #                 st.session_state.data_error = str(e)
# # # #                 st.error(f"Reload failed: {e}")
# # # #         st.markdown("</div>", unsafe_allow_html=True)

# # # #         # ── Footer ────────────────────────────────────────────────────────────
# # # #         st.markdown(
# # # #             "<div style='padding:6px 12px;border-top:1px solid var(--bl);margin-top:8px;'>"
# # # #             "<div style='font-size:9px;color:var(--t3);'>FI11 Turku · Apr 2026</div></div>",
# # # #             unsafe_allow_html=True,
# # # #         )
