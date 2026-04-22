"""
tabs/ask_aria.py
Dedicated chat tab for asking questions about the supply chain.
"""

import streamlit as st
import json
import os
from agent import chat_with_data

# Path to insights JSON
INSIGHTS_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "insights",
    "supply_chain_insights.json"
)

@st.cache_resource
def load_insights():
    try:
        with open(INSIGHTS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return None

def get_answer(question: str, insights: dict) -> str:
    if st.session_state.azure_client:
        full_knowledge = insights.get("full_markdown", "")
        if len(full_knowledge) > 12000:
            full_knowledge = full_knowledge[:12000] + "\n… (truncated)"
        context = f"""
You are ARIA, a supply chain intelligence assistant for Revvity FI11 Turku.
Answer the user's question based **only** on the following knowledge base.
Do not invent facts. If the answer is not in the knowledge base, say so clearly.

KNOWLEDGE BASE:
{full_knowledge}

USER QUESTION: {question}
"""
        try:
            return chat_with_data(
                st.session_state.azure_client,
                st.session_state.get("deployment_name", "gpt-4o-mini"),
                question,
                context
            )
        except Exception as e:
            return f"⚠️ LLM error: {e}"
    else:
        return manual_answer(question, insights)

def manual_answer(question: str, insights: dict) -> str:
    q = question.lower()
    critical = insights.get("critical_materials", [])
    healthy = insights.get("healthy_materials", [])
    replenish = insights.get("replenishment_actions", [])
    risks = insights.get("executive_risks", [])
    consol = insights.get("supplier_consolidation", [])

    if "critical" in q or "urgent" in q:
        if critical:
            names = ", ".join(m["name"] for m in critical)
            return f"⚠️ Critical: {names}. Order {critical[0]['order_quantity_required']} units of {critical[0]['name']}."
        return "No critical materials."
    elif "healthy" in q or "safe" in q:
        if healthy:
            names = ", ".join(m["name"] for m in healthy[:3])
            return f"✅ Healthy: {names}."
        return "No healthy materials."
    elif "replenish" in q or "order" in q:
        if replenish:
            r = replenish[0]
            return f"📦 Immediate order: {r['order_qty']} units of {r['name']}."
        return "No immediate orders."
    elif "risk" in q:
        if risks:
            return "Risks:\n" + "\n".join(f"- {r}" for r in risks[:2])
        return "No systemic risks."
    elif "supplier" in q:
        if consol:
            top = consol[0]
            return f"Top consolidation: {top['supplier']} supplies {len(top['materials'])} materials."
        return "No supplier data."
    else:
        return "I can answer about critical/healthy materials, orders, risks, and suppliers. Try a specific question (or add Azure API key for full intelligence)."

def render():
    st.markdown(
        "<div style='font-size:15px;font-weight:800;margin-bottom:4px;'>Ask ARIA</div>"
        "<div style='font-size:12px;color:var(--t3);margin-bottom:14px;'>"
        "Ask any question about your supply chain – stock levels, risks, BOM components, suppliers, and recommendations.</div>",
        unsafe_allow_html=True,
    )

    insights = load_insights()
    if not insights:
        st.warning("⚠️ Insights file not found. Please run `python insights/generate_insights.py` first.")
        return

    # Initialize chat history
    if "ask_aria_messages" not in st.session_state:
        st.session_state.ask_aria_messages = []

    # Display chat history
    for msg in st.session_state.ask_aria_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Input box
    if prompt := st.chat_input("Your question..."):
        st.session_state.ask_aria_messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.chat_message("assistant"):
            with st.spinner("Thinking…"):
                answer = get_answer(prompt, insights)
            st.markdown(answer)
        st.session_state.ask_aria_messages.append({"role": "assistant", "content": answer})
