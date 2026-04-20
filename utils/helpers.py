"""
utils/helpers.py
Shared constants, small helper functions, and chart styling utilities.
"""

import os
import base64
import math
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import networkx as nx
import streamlit as st

# ── Azure / App Constants ──────────────────────────────────────────────────────
AZURE_ENDPOINT   = "https://bu24-demo.openai.azure.com/"
AZURE_DEPLOYMENT = "gpt-4o-mini"
AZURE_API_VER    = "2025-01-01-preview"
ORANGE           = "#F47B25"


# ── Image Utility ──────────────────────────────────────────────────────────────
def img_b64(path: str) -> str:
    """Return base64-encoded content of an image file, or '' on error."""
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except Exception:
        return ""


# ── Chart Theming ──────────────────────────────────────────────────────────────
def ct(fig, h=280, margin=None):
    """Apply consistent ARIA theme to a Plotly figure."""
    m = margin or dict(l=8, r=8, t=28, b=8)
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#FFFFFF", height=h, margin=m,
        font=dict(family="Inter", color="#94A3B8", size=11),
        xaxis=dict(
            gridcolor="#F0F4F9", zerolinecolor="#F0F4F9",
            tickfont_color="#94A3B8", showline=False,
        ),
        yaxis=dict(
            gridcolor="#F0F4F9", zerolinecolor="#F0F4F9",
            tickfont_color="#94A3B8", showline=False,
        ),
        legend=dict(
            bgcolor="rgba(0,0,0,0)", font_color="#94A3B8",
            font_size=10, orientation="h", y=1.1,
        ),
        hoverlabel=dict(
            bgcolor="#FFFFFF", font_color="#1E293B",
            bordercolor="#E2E8F0", font_size=11,
        ),
    )
    return fig


# ── Formatters ─────────────────────────────────────────────────────────────────
def fmt_p(p) -> str:
    """Format a fiscal period integer (YYYYMM) as 'Mon 'YY'."""
    try:
        return pd.to_datetime(str(p), format="%Y%m").strftime("%b '%y")
    except Exception:
        return str(p)


# ── HTML Badge ─────────────────────────────────────────────────────────────────
def sbadge(risk: str) -> str:
    """Return an HTML risk badge string for the given risk level."""
    m = {
        "CRITICAL":         ("sbc", "dot-r", "⛔ Critical"),
        "WARNING":          ("sbw", "dot-a", "⚠ Warning"),
        "HEALTHY":          ("sbh", "dot-g", "✓ Healthy"),
        "INSUFFICIENT_DATA":("sbn", "dot-n", "◌ No Data"),
    }
    sc, dc, lb = m.get(risk, ("sbn", "dot-n", risk))
    return f'<span class="sb {sc}"><span class="dot {dc}"></span>{lb}</span>'


# ── Section Dividers ───────────────────────────────────────────────────────────
def sec(t: str):
    """Render a styled section divider."""
    st.markdown(f'<div class="sdv">{t}</div>', unsafe_allow_html=True)


def note(t: str):
    """Render an orange left-bordered note box."""
    st.markdown(f'<div class="note-box">{t}</div>', unsafe_allow_html=True)


# ── Enhanced BOM Tree Plot (Fix #11 & #12) ─────────────────────────────────────
def plot_bom_tree(bom_df: pd.DataFrame, root_name: str, risk_color: str):
    """
    Create a networkx spring-layout tree graph for BOM propagation.
    Nodes are coloured by:
      - Root: risk_color (based on finished good risk)
      - Component (inhouse): #22C55E (green)
      - Component (external, missing supplier): #F59E0B (amber)
      - Component (external, named supplier): #3B82F6 (blue)
      - Supplier node: #8B5CF6 (purple)
    Labels are prefixed with [C] for components and [S] for suppliers (Fix #12).
    """
    G = nx.DiGraph()
    G.add_node(root_name, color=risk_color, node_type="root")

    for _, row in bom_df.iterrows():
        # Component name
        comp = (
            str(row["Material Description"])[:30]
            if pd.notna(row["Material Description"])
            else str(row["Material"])
        )
        comp_label = f"[C] {comp}"
        sup_display = row.get("Supplier Display", "—")
        proc_type = str(row.get("Procurement type", "")).strip()

        # Determine component colour (Fix #11)
        if proc_type == "E":
            comp_color = "#22C55E"      # Inhouse (Revvity)
        elif sup_display.startswith("⚠"):
            comp_color = "#F59E0B"      # Missing supplier data
        else:
            comp_color = "#3B82F6"      # External named supplier

        G.add_node(comp_label, color=comp_color, node_type="component")
        G.add_edge(root_name, comp_label)

        # Add supplier node if external and named
        if sup_display not in ["Revvity Inhouse", "—"] and not sup_display.startswith("⚠"):
            sup_label = f"[S] {sup_display[:25]}"
            sup_color = "#8B5CF6"       # Purple for suppliers
            if sup_label not in G.nodes:
                G.add_node(sup_label, color=sup_color, node_type="supplier")
            G.add_edge(comp_label, sup_label)

    # Layout
    pos = nx.spring_layout(G, k=2, seed=42, iterations=50)

    # Prepare edge traces
    edge_x, edge_y = [], []
    for edge in G.edges():
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])

    # Prepare node traces
    node_x, node_y, node_text, node_color = [], [], [], []
    for node in G.nodes():
        x, y = pos[node]
        node_x.append(x)
        node_y.append(y)
        node_text.append(node)
        node_color.append(G.nodes[node].get("color", "#3B82F6"))

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=edge_x, y=edge_y, mode="lines",
        line=dict(width=1, color="#E2E8F0"), hoverinfo="none",
    ))
    fig.add_trace(go.Scatter(
        x=node_x, y=node_y, mode="markers+text",
        text=node_text, textposition="bottom center",
        marker=dict(size=25, color=node_color, line=dict(width=2, color="white")),
        textfont=dict(size=10, color="#1E293B"),
        hoverinfo="text",
    ))
    fig.update_layout(
        showlegend=False, height=500,
        xaxis=dict(visible=False), yaxis=dict(visible=False),
        margin=dict(l=0, r=0, t=0, b=0),
        plot_bgcolor="white",
    )
    return fig