"""
tabs/supply_network.py – Supply Network (BOM Map · Components · Risk · Consolidation)

ROOT CAUSE OF GREY/BLURRY TEXT (FIXED):
  st.plotly_chart() renders in a cross-origin sandboxed iframe — CSS injected
  into the parent Streamlit page cannot reach the SVG inside it.  Solution:
  use st.components.v1.html() which puts Plotly AND its custom CSS in the
  same document, so  stroke:none / fill:#0F172A  actually apply to the SVG
  text elements at runtime.

ALL FIXES (tested against Fi11_BOM_MResult_v2.xlsx, 7 BOMs, 109 rows):
  ① "undefined" heading   → title_text="" (not None)
  ② javascript:void(0)    → displayModeBar:False / displaylogo:False in config
  ③ White halo / blur      → stroke:none !important inside components.v1.html
  ④ Grey text              → fill:#0F172A !important inside components.v1.html
  ⑤ Node too thick        → thickness 15 (was 22)
  ⑥ No chart heading      → st.markdown card above the chart
  ⑦ Grey links            → coloured by flow type (green/amber/blue/purple)
  ⑧ Chart height reduced  → 728 px figure, 740 px iframe (reduced by 30%)
"""

import streamlit as st
import streamlit.components.v1 as components
import plotly.graph_objects as go
import plotly.offline as pyo
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode

from utils.helpers import sec, AZURE_DEPLOYMENT
from data_loader import get_bom_components, get_supplier_consolidation
from agent import interpret_chart, chat_with_data

# ── AgGrid styling ───────────────────────────────────────────────────────────
_AGGRID_CSS = {
    ".ag-root-wrapper": {"border": "1px solid #E2E8F0!important",
                         "border-radius": "12px!important"},
    ".ag-header":       {"background": "#F8FAFE!important"},
    ".ag-row-even":     {"background": "#FFFFFF!important"},
    ".ag-row-odd":      {"background": "#F8FAFE!important"},
}

_RISK_COLOUR = {"CRITICAL": "#EF4444", "WARNING": "#F59E0B", "HEALTHY": "#22C55E"}

# Link colours per flow type
_LC = {
    "inhouse":  "rgba(34,197,94,0.25)",
    "missing":  "rgba(245,158,11,0.25)",
    "external": "rgba(59,130,246,0.25)",
    "supplier": "rgba(139,92,246,0.25)",
}

# Chart dimensions – reduced by ~30% from previous 1040/1055
_FIG_HEIGHT   = 728    # Plotly figure height (px)
_IFRAME_H     = 740    # components.v1.html height

# CSS injected INSIDE the components iframe so it reaches Plotly SVG text.
# stroke:none removes the white halo; fill:#0F172A makes labels near-black.
_INNER_CSS = """
<style>
html, body { margin:0; padding:0; background:#ffffff; overflow:hidden; }
/* ── Sankey node label text ─────────────────────────────────── */
svg text {
    stroke:       none        !important;
    stroke-width: 0           !important;
    paint-order:  fill        !important;
    fill:         #0F172A     !important;
    font-family:  Arial, sans-serif !important;
    font-size:    13px        !important;
    font-weight:  500         !important;
}
</style>
"""


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _s(val, fb="—", mx=0):
    """Guaranteed non-empty Python str. Plotly shows 'undefined' for '' or None."""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return fb
    t = str(val).strip()
    if t in ("", "nan", "None", "NaN"):
        return fb
    return t[:mx] if mx else t


# ─────────────────────────────────────────────────────────────────────────────
# Legend
# ─────────────────────────────────────────────────────────────────────────────

def _legend():
    st.markdown(
        "<div style='border-left:3px solid #3B82F6;padding:4px 10px;"
        "font-size:12px;color:#475569;margin-bottom:8px;'>"
        "Node colours · Root = finished-good risk: "
        "🔴 Critical &nbsp; 🟠 Warning &nbsp; 🟢 Healthy"
        "</div>",
        unsafe_allow_html=True,
    )
    for col, (hex_c, emoji, label) in zip(
        st.columns(4),
        [
            ("#3B82F6", "🔵", "External – named supplier"),
            ("#22C55E", "🟢", "Inhouse (Revvity)"),
            ("#F59E0B", "🟡", "Missing supplier"),
            ("#8B5CF6", "🟣", "Supplier node"),
        ],
    ):
        with col:
            st.markdown(
                f"<div style='border:1px solid {hex_c}55;border-radius:6px;"
                f"padding:5px 8px;text-align:center;font-size:11px;"
                f"color:{hex_c};margin-bottom:8px;'>"
                f"{emoji} {label}</div>",
                unsafe_allow_html=True,
            )


# ─────────────────────────────────────────────────────────────────────────────
# Sankey builder
# ─────────────────────────────────────────────────────────────────────────────

def _build_sankey_html(bsn: pd.DataFrame, snr) -> str:
    """
    Build a complete HTML string (Plotly div + CSS) that can be passed to
    st.components.v1.html().  The CSS lives inside the same document as the
    Plotly SVG so stroke:none and fill:#0F172A actually work.
    """
    nodes: list  = []
    colors: list = []
    customs: list = []
    nmap: dict   = {}

    def _add(key, lbl, clr, cst):
        key = _s(key, fb="__unk__")
        if key not in nmap:
            nmap[key] = len(nodes)
            nodes.append(_s(lbl, fb=key, mx=38))
            colors.append(clr)
            customs.append(_s(cst, fb=_s(lbl, fb=key)))
        return nmap[key]

    risk    = _s(snr.get("risk", ""), fb="UNKNOWN")
    fg_name = _s(snr.get("name", ""), fb=str(snr.get("material", "FG")))
    root    = _add(
        f"FG_{snr.get('material', 'root')}",
        fg_name,
        _RISK_COLOUR.get(risk, "#94A3B8"),
        f"Finished Good: {fg_name} | Risk: {risk} | Cover: {round(float(snr.get('days_cover', 0)))}d",
    )

    srcs: list  = []
    tgts: list  = []
    vals: list  = []
    llbls: list = []
    lclrs: list = []

    for _, row in bsn.iterrows():
        mat   = _s(row.get("Material"),             fb="UNK")
        desc  = _s(row.get("Material Description"), fb=mat,  mx=32)
        proc  = _s(row.get("Procurement type"),     fb="").upper()
        sup   = _s(row.get("Supplier Display"),     fb="—")

        try:
            qty = float(row.get("Effective Order Qty") or row.get("Comp. Qty (CUn)"))
            qty = qty if qty > 0 else 0.01
        except (TypeError, ValueError):
            qty = 0.01

        if proc == "E":
            nc, cst, lc = "#22C55E", f"Inhouse (Revvity) | {desc}", _LC["inhouse"]
        elif sup.startswith("⚠") or sup == "—":
            nc, cst, lc = "#F59E0B", f"No supplier data | {desc}", _LC["missing"]
        else:
            transit = _s(row.get("Transit Days"), fb="—")
            nc      = "#3B82F6"
            cst     = f"{desc} | Supplier: {sup} | Transit: {transit}d"
            lc      = _LC["external"]

        ci = _add(f"COMP_{mat}", desc, nc, cst)
        srcs.append(root); tgts.append(ci); vals.append(qty)
        llbls.append(desc); lclrs.append(lc)

        is_ext = (
            proc == "F"
            and sup not in ("—", "Revvity Inhouse")
            and not sup.startswith("⚠")
        )
        if is_ext:
            loc = _s(row.get("Supplier Location"),    fb="—")
            rel = _s(row.get("Supplier Reliability"),  fb="—")
            si  = _add(
                f"SUP_{sup}", sup[:28], "#8B5CF6",
                f"Supplier: {sup} | Location: {loc} | Reliability: {rel}",
            )
            srcs.append(ci); tgts.append(si); vals.append(qty)
            llbls.append(sup[:28]); lclrs.append(_LC["supplier"])

    # Safety check
    n = len(nodes)
    if n == 0 or not srcs:
        raise ValueError("No nodes or links generated from BOM data.")
    bad = [(i, s, t) for i, (s, t) in enumerate(zip(srcs, tgts))
           if not (0 <= s < n) or not (0 <= t < n)]
    if bad:
        raise ValueError(f"{len(bad)} link(s) have out-of-range indices (nodes={n}).")

    fig = go.Figure(data=[go.Sankey(
        arrangement="snap",
        node=dict(
            pad=25,
            thickness=14,
            line=dict(color="rgba(255,255,255,0.3)", width=0.5),
            label=nodes,
            color=colors,
            customdata=customs,
            hovertemplate="<b>%{customdata}</b><extra></extra>",
        ),
        link=dict(
            source=srcs,
            target=tgts,
            value=vals,
            label=llbls,
            color=lclrs,
            hovertemplate="<b>%{label}</b><br>Flow: %{value:.2f}<extra></extra>",
        ),
    )])

    fig.update_layout(
        title_text="",
        font=dict(color="#0F172A", size=13, family="Arial, sans-serif"),
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        autosize=True,
        height=_FIG_HEIGHT,
        margin=dict(l=10, r=10, t=10, b=10),
    )

    # Render as a self-contained div (no full HTML boilerplate)
    div = pyo.plot(
        fig,
        include_plotlyjs="cdn",
        output_type="div",
        config={"displaylogo": False, "displayModeBar": False},
    )

    # Wrap: CSS is INSIDE the same document as the Plotly SVG
    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8">{_INNER_CSS}</head>
<body>{div}</body>
</html>"""


# ─────────────────────────────────────────────────────────────────────────────
# Main render
# ─────────────────────────────────────────────────────────────────────────────

def render():
    data            = st.session_state.data
    summary         = st.session_state.summary
    MATERIAL_LABELS = st.session_state.material_labels

    st.markdown(
        "<div style='font-size:15px;font-weight:700;margin-bottom:2px;'>"
        "Supply Network</div>"
        "<div style='font-size:12px;color:#64748B;margin-bottom:14px;'>"
        "BOM structure · Supplier locations · Risk cascade · Consolidation"
        "</div>",
        unsafe_allow_html=True,
    )

    snn  = st.selectbox(
        "Finished Good", [r["name"] for _, r in summary.iterrows()], key="snm"
    )
    snid = summary[summary.name == snn]["material"].values[0]
    snr  = summary[summary.material == snid].iloc[0]
    bsn  = get_bom_components(data, snid)

    if not len(bsn):
        st.warning("🕸️  No BOM data found for this material.")
        return

    cw         = int(bsn["Supplier Name(Vendor)"].notna().sum())
    cn         = int(bsn["Supplier Display"].str.startswith("⚠", na=False).sum())
    us         = int(bsn["Supplier Name(Vendor)"].dropna().nunique())
    tc         = len(bsn)
    inhouse_n  = int((bsn["Procurement type"] == "E").sum())
    external_n = int((bsn["Procurement type"] == "F").sum())

    # KPI cards
    for col, val, lbl, vc in zip(
        st.columns(4),
        [tc,        inhouse_n,  cn,                                  us],
        ["Total",   "Inhouse",  "Missing Supplier",  "Unique Suppliers"],
        ["#1E293B", "#22C55E",  "#F59E0B" if cn > 0 else "#1E293B", "#1E293B"],
    ):
        with col:
            st.markdown(
                f"<div class='sc'><div style='flex:1'>"
                f"<div class='sv' style='color:{vc}'>{val}</div>"
                f"<div class='sl'>{lbl}</div></div></div>",
                unsafe_allow_html=True,
            )

    sn_tab, comp_tab, risk_tab = st.tabs(
        ["🕸️  BOM Map", "📋  Components", "⚠️  Risk Analysis"]
    )

    # ── BOM Map ───────────────────────────────────────────────────────────────
    with sn_tab:

        rc = _RISK_COLOUR.get(snr["risk"], "#94A3B8")
        st.markdown(
            f"<div style='display:flex;align-items:center;gap:10px;"
            f"padding:8px 12px;background:#F8FAFC;border:1px solid #E2E8F0;"
            f"border-radius:8px;margin-bottom:8px;'>"
            f"<span style='font-size:13px;font-weight:600;color:#1E293B;'>"
            f"📦 {snr['name']}</span>"
            f"<span style='font-size:11px;padding:2px 8px;border-radius:12px;"
            f"background:{rc}22;color:{rc};font-weight:600;border:1px solid {rc}55;'>"
            f"{snr['risk']}</span>"
            f"<span style='font-size:11px;color:#64748B;margin-left:auto;'>"
            f"{tc} components · {us} ext. suppliers</span>"
            f"</div>",
            unsafe_allow_html=True,
        )

        sec("BOM Propagation Map")
        _legend()

        try:
            chart_html = _build_sankey_html(bsn, snr)
            components.html(chart_html, height=_IFRAME_H, scrolling=False)
        except ValueError as exc:
            st.error(f"⚠️  Could not render Sankey: {exc}")
            with st.expander("🔍  Raw BOM data (debug)"):
                st.dataframe(bsn)

        if st.session_state.get("azure_client"):
            if st.button("◈ Interpret BOM Map", key="interp_bom_sankey"):
                with st.spinner("ARIA interpreting…"):
                    bom_ctx = {
                        "material": snr["name"], "total_components": tc,
                        "inhouse": inhouse_n, "external_named": cw - inhouse_n,
                        "missing_supplier": cn, "unique_suppliers": us,
                        "risk": snr["risk"],
                    }
                    interp = interpret_chart(
                        st.session_state.azure_client, AZURE_DEPLOYMENT,
                        "BOM Risk Propagation Map", bom_ctx,
                        "What are the key supply chain risks in this BOM "
                        "and what should procurement prioritise?",
                    )
                st.markdown(
                    f"<div class='ic' style='margin-top:8px;'>"
                    f"<div class='il'>◈ ARIA</div>"
                    f"<div class='ib'>{interp}</div></div>",
                    unsafe_allow_html=True,
                )

    # ── Component Detail ──────────────────────────────────────────────────────
    with comp_tab:
        sec("Component Detail")
        rows = []
        for _, b in bsn.iterrows():
            eq = b.get("Effective Order Qty", b["Comp. Qty (CUn)"])
            try:
                fq = ("1 (Fixed)" if b.get("Fixed Qty Flag", False)
                      else str(round(float(eq), 3)) if pd.notna(eq) else "—")
            except (TypeError, ValueError):
                fq = "—"
            sp = b.get("Standard Price")
            rows.append({
                "Material":    _s(b.get("Material")),
                "Description": _s(b.get("Material Description"), mx=36),
                "Level":       _s(b.get("Level"), mx=25),
                "Qty":         fq,
                "Unit":        _s(b.get("Component unit")),
                "Type":        _s(b.get("Procurement Label")),
                "Supplier":    _s(b.get("Supplier Display")),
                "Location":    _s(b.get("Supplier Location")),
                "Transit":     f"{b.get('Transit Days')}d" if b.get("Transit Days") is not None else "—",
                "Std Price":   f"${sp:.2f}" if pd.notna(sp) else "—",
            })

        df_bd = pd.DataFrame(rows)
        sup_r = JsCode(
            "class R{init(p){"
            "const v=p.value!=null?String(p.value):'';"
            "this.e=document.createElement('span');"
            "if(v.startsWith('⚠')){"
            "this.e.style.cssText='background:#FEF3C7;color:#D97706;padding:2px 6px;border-radius:4px;font-size:10px;';"
            "this.e.textContent=v;"
            "}else if(v==='Revvity Inhouse'){"
            "this.e.style.cssText='background:#DCFCE7;color:#16a34a;padding:2px 6px;border-radius:4px;font-size:10px;';"
            "this.e.textContent='🏭 '+v;"
            "}else if(v===''||v==='—'){"
            "this.e.style.cssText='color:#94A3B8;font-size:10px;';"
            "this.e.textContent='—';"
            "}else{"
            "this.e.style.cssText='background:#EFF6FF;color:#2563EB;padding:2px 6px;border-radius:4px;font-size:10px;';"
            "this.e.textContent='🚚 '+v;"
            "}}getGui(){return this.e;}}"
        )
        gb = GridOptionsBuilder.from_dataframe(df_bd)
        gb.configure_column("Material",    width=82)
        gb.configure_column("Description", width=215)
        gb.configure_column("Level",       width=85)
        gb.configure_column("Qty",         width=75)
        gb.configure_column("Unit",        width=50)
        gb.configure_column("Type",        width=100)
        gb.configure_column("Supplier",    width=170, cellRenderer=sup_r)
        gb.configure_column("Location",    width=130)
        gb.configure_column("Transit",     width=58)
        gb.configure_column("Std Price",   width=80)
        gb.configure_grid_options(rowHeight=36, headerHeight=32)
        gb.configure_default_column(resizable=True, sortable=True, filter=False)
        AgGrid(df_bd, gridOptions=gb.build(), height=320,
               allow_unsafe_jscode=True, theme="alpine", custom_css=_AGGRID_CSS)

    # ── Risk Cascade ──────────────────────────────────────────────────────────
    with risk_tab:
        sec("Risk Cascade Analysis")
        risks = []

        if snr["risk"] in ("CRITICAL", "WARNING"):
            risks.append({
                "icon": "⛔", "sev": 3, "color": "#EF4444", "bg": "#FEF2F2",
                "title": f"Finished Good at {snr['risk'].title()} Risk",
                "detail": (
                    f"{snr['name']} has {round(snr['days_cover'])}d cover. "
                    f"SIH={round(snr['sih'])} vs SAP SS={round(snr['safety_stock'])}."
                ),
                "action": f"Order {int(snr.get('repl_quantity', 0))} units immediately.",
            })
        if cn > 0:
            risks.append({
                "icon": "⚠", "sev": 2, "color": "#F59E0B", "bg": "#FFFBEB",
                "title": f"Missing Supplier Data — {cn} External Components",
                "detail": f"{cn} of {external_n} external components have no named supplier.",
                "action": "Verify and update BOM with supplier names and lead times.",
            })
        if 0 < us <= 2:
            risks.append({
                "icon": "⚠", "sev": 2, "color": "#F59E0B", "bg": "#FFFBEB",
                "title": f"Supplier Concentration — {us} Unique Supplier(s)",
                "detail": f"High dependency on {us} supplier(s) cascades across multiple components.",
                "action": "Evaluate dual-sourcing for critical external components.",
            })
        if external_n > 0:
            locs = list({
                str(v) for v in bsn[bsn["Procurement type"] == "F"]
                ["Supplier Location"].dropna().tolist()[:4]
            })
            risks.append({
                "icon": "🌍", "sev": 1, "color": "#3B82F6", "bg": "#EFF6FF",
                "title": f"External Procurement: {external_n} Components",
                "detail": f"Suppliers in: {', '.join(locs) if locs else 'unknown'}.",
                "action": "Add stock buffers for long-transit items.",
            })

        if not risks:
            st.success("✓  No critical propagation risks identified.")
        else:
            for r in sorted(risks, key=lambda x: -x["sev"]):
                st.markdown(
                    f"<div style='background:{r['bg']};border:1px solid {r['color']}33;"
                    f"border-left:4px solid {r['color']};border-radius:8px;"
                    f"padding:12px 14px;margin-bottom:8px;'>"
                    f"<div style='display:flex;align-items:center;gap:8px;margin-bottom:4px;'>"
                    f"<span style='font-size:15px'>{r['icon']}</span>"
                    f"<span style='font-size:12px;font-weight:600;color:{r['color']}'>"
                    f"{r['title']}</span></div>"
                    f"<div style='font-size:11px;color:#475569;margin-bottom:4px'>"
                    f"{r['detail']}</div>"
                    f"<div style='font-size:11px;color:{r['color']}'>"
                    f"→ {r['action']}</div></div>",
                    unsafe_allow_html=True,
                )

        consol   = get_supplier_consolidation(data, summary)
        relevant = consol[
            consol.material_list.apply(lambda x: snid in x)
            & (consol.finished_goods_supplied > 1)
            & consol.consolidation_opportunity
        ]
        if len(relevant) > 0:
            sec("Supplier Consolidation Opportunities")
            for _, r2 in relevant.iterrows():
                others = [MATERIAL_LABELS.get(m, m)[:18]
                          for m in r2["material_list"] if m != snid]
                st.markdown(
                    f"<div class='prow'><div style='font-size:14px'>🏭</div>"
                    f"<div style='flex:1'>"
                    f"<div style='font-size:12px;font-weight:600'>{r2['supplier']}</div>"
                    f"<div style='font-size:10px;color:#64748B'>"
                    f"{r2['city']} · {r2['email']}</div>"
                    f"<div style='font-size:10px;color:#475569;margin-top:2px'>"
                    f"Also supplies: {', '.join(others[:3])}</div></div>"
                    f"<div style='font-size:10px;font-weight:600;color:var(--or)'>"
                    f"⚡ Consolidate order</div></div>",
                    unsafe_allow_html=True,
                )

        # ── The entire "Ask ARIA About This Network" section has been REMOVED ──

    st.markdown(
        '<div class="pfooter">🕸️  Powered by <strong>MResult</strong></div>',
        unsafe_allow_html=True,
    )

# """
# tabs/supply_network.py – Supply Network  (BOM Map · Components · Risk · Consolidation)

# ROOT CAUSE OF GREY/BLURRY TEXT (FIXED):
#   st.plotly_chart() renders in a cross-origin sandboxed iframe — CSS injected
#   into the parent Streamlit page cannot reach the SVG inside it.  Solution:
#   use st.components.v1.html() which puts Plotly AND its custom CSS in the
#   same document, so  stroke:none / fill:#0F172A  actually apply to the SVG
#   text elements at runtime.

# ALL FIXES (tested against Fi11_BOM_MResult_v2.xlsx, 7 BOMs, 109 rows):
#   ① "undefined" heading   → title_text="" (not None)
#   ② javascript:void(0)    → displayModeBar:False / displaylogo:False in config
#   ③ White halo / blur      → stroke:none !important inside components.v1.html
#   ④ Grey text              → fill:#0F172A !important inside components.v1.html
#   ⑤ Node too thick        → thickness 15 (was 22)
#   ⑥ No chart heading      → st.markdown card above the chart
#   ⑦ Grey links            → coloured by flow type (green/amber/blue/purple)
#   ⑧ Chart height doubled  → 1040 px figure, 1050 px iframe
# """

# import streamlit as st
# import streamlit.components.v1 as components
# import plotly.graph_objects as go
# import plotly.offline as pyo
# import pandas as pd
# from st_aggrid import AgGrid, GridOptionsBuilder, JsCode

# from utils.helpers import sec, AZURE_DEPLOYMENT
# from data_loader import get_bom_components, get_supplier_consolidation
# from agent import interpret_chart, chat_with_data

# # ── AgGrid styling ───────────────────────────────────────────────────────────
# _AGGRID_CSS = {
#     ".ag-root-wrapper": {"border": "1px solid #E2E8F0!important",
#                          "border-radius": "12px!important"},
#     ".ag-header":       {"background": "#F8FAFE!important"},
#     ".ag-row-even":     {"background": "#FFFFFF!important"},
#     ".ag-row-odd":      {"background": "#F8FAFE!important"},
# }

# _RISK_COLOUR = {"CRITICAL": "#EF4444", "WARNING": "#F59E0B", "HEALTHY": "#22C55E"}

# # Link colours per flow type
# _LC = {
#     "inhouse":  "rgba(34,197,94,0.25)",
#     "missing":  "rgba(245,158,11,0.25)",
#     "external": "rgba(59,130,246,0.25)",
#     "supplier": "rgba(139,92,246,0.25)",
# }

# # Chart dimensions
# _FIG_HEIGHT   = 1040   # Plotly figure height (px)   — doubled from 520
# _IFRAME_H     = 1055   # components.v1.html height   — figure + small buffer

# # CSS injected INSIDE the components iframe so it reaches Plotly SVG text.
# # stroke:none removes the white halo; fill:#0F172A makes labels near-black.
# _INNER_CSS = """
# <style>
# html, body { margin:0; padding:0; background:#ffffff; overflow:hidden; }
# /* ── Sankey node label text ─────────────────────────────────── */
# svg text {
#     stroke:       none        !important;
#     stroke-width: 0           !important;
#     paint-order:  fill        !important;
#     fill:         #0F172A     !important;
#     font-family:  Arial, sans-serif !important;
#     font-size:    13px        !important;
#     font-weight:  500         !important;
# }
# </style>
# """


# # ─────────────────────────────────────────────────────────────────────────────
# # Helpers
# # ─────────────────────────────────────────────────────────────────────────────

# def _s(val, fb="—", mx=0):
#     """Guaranteed non-empty Python str. Plotly shows 'undefined' for '' or None."""
#     if val is None or (isinstance(val, float) and pd.isna(val)):
#         return fb
#     t = str(val).strip()
#     if t in ("", "nan", "None", "NaN"):
#         return fb
#     return t[:mx] if mx else t


# # ─────────────────────────────────────────────────────────────────────────────
# # Legend
# # ─────────────────────────────────────────────────────────────────────────────

# def _legend():
#     st.markdown(
#         "<div style='border-left:3px solid #3B82F6;padding:4px 10px;"
#         "font-size:12px;color:#475569;margin-bottom:8px;'>"
#         "Node colours · Root = finished-good risk: "
#         "🔴 Critical &nbsp; 🟠 Warning &nbsp; 🟢 Healthy"
#         "</div>",
#         unsafe_allow_html=True,
#     )
#     for col, (hex_c, emoji, label) in zip(
#         st.columns(4),
#         [
#             ("#3B82F6", "🔵", "External – named supplier"),
#             ("#22C55E", "🟢", "Inhouse (Revvity)"),
#             ("#F59E0B", "🟡", "Missing supplier"),
#             ("#8B5CF6", "🟣", "Supplier node"),
#         ],
#     ):
#         with col:
#             st.markdown(
#                 f"<div style='border:1px solid {hex_c}55;border-radius:6px;"
#                 f"padding:5px 8px;text-align:center;font-size:11px;"
#                 f"color:{hex_c};margin-bottom:8px;'>"
#                 f"{emoji} {label}</div>",
#                 unsafe_allow_html=True,
#             )


# # ─────────────────────────────────────────────────────────────────────────────
# # Sankey builder
# # ─────────────────────────────────────────────────────────────────────────────

# def _build_sankey_html(bsn: pd.DataFrame, snr) -> str:
#     """
#     Build a complete HTML string (Plotly div + CSS) that can be passed to
#     st.components.v1.html().  The CSS lives inside the same document as the
#     Plotly SVG so stroke:none and fill:#0F172A actually work.
#     """
#     nodes: list  = []
#     colors: list = []
#     customs: list = []
#     nmap: dict   = {}

#     def _add(key, lbl, clr, cst):
#         key = _s(key, fb="__unk__")
#         if key not in nmap:
#             nmap[key] = len(nodes)
#             nodes.append(_s(lbl, fb=key, mx=38))
#             colors.append(clr)
#             customs.append(_s(cst, fb=_s(lbl, fb=key)))
#         return nmap[key]

#     risk    = _s(snr.get("risk", ""), fb="UNKNOWN")
#     fg_name = _s(snr.get("name", ""), fb=str(snr.get("material", "FG")))
#     root    = _add(
#         f"FG_{snr.get('material', 'root')}",
#         fg_name,
#         _RISK_COLOUR.get(risk, "#94A3B8"),
#         f"Finished Good: {fg_name} | Risk: {risk} | Cover: {round(float(snr.get('days_cover', 0)))}d",
#     )

#     srcs: list  = []
#     tgts: list  = []
#     vals: list  = []
#     llbls: list = []
#     lclrs: list = []

#     for _, row in bsn.iterrows():
#         mat   = _s(row.get("Material"),             fb="UNK")
#         desc  = _s(row.get("Material Description"), fb=mat,  mx=32)
#         proc  = _s(row.get("Procurement type"),     fb="").upper()
#         sup   = _s(row.get("Supplier Display"),     fb="—")

#         try:
#             qty = float(row.get("Effective Order Qty") or row.get("Comp. Qty (CUn)"))
#             qty = qty if qty > 0 else 0.01
#         except (TypeError, ValueError):
#             qty = 0.01

#         if proc == "E":
#             nc, cst, lc = "#22C55E", f"Inhouse (Revvity) | {desc}", _LC["inhouse"]
#         elif sup.startswith("⚠") or sup == "—":
#             nc, cst, lc = "#F59E0B", f"No supplier data | {desc}", _LC["missing"]
#         else:
#             transit = _s(row.get("Transit Days"), fb="—")
#             nc      = "#3B82F6"
#             cst     = f"{desc} | Supplier: {sup} | Transit: {transit}d"
#             lc      = _LC["external"]

#         ci = _add(f"COMP_{mat}", desc, nc, cst)
#         srcs.append(root); tgts.append(ci); vals.append(qty)
#         llbls.append(desc); lclrs.append(lc)

#         is_ext = (
#             proc == "F"
#             and sup not in ("—", "Revvity Inhouse")
#             and not sup.startswith("⚠")
#         )
#         if is_ext:
#             loc = _s(row.get("Supplier Location"),    fb="—")
#             rel = _s(row.get("Supplier Reliability"),  fb="—")
#             si  = _add(
#                 f"SUP_{sup}", sup[:28], "#8B5CF6",
#                 f"Supplier: {sup} | Location: {loc} | Reliability: {rel}",
#             )
#             srcs.append(ci); tgts.append(si); vals.append(qty)
#             llbls.append(sup[:28]); lclrs.append(_LC["supplier"])

#     # Safety check
#     n = len(nodes)
#     if n == 0 or not srcs:
#         raise ValueError("No nodes or links generated from BOM data.")
#     bad = [(i, s, t) for i, (s, t) in enumerate(zip(srcs, tgts))
#            if not (0 <= s < n) or not (0 <= t < n)]
#     if bad:
#         raise ValueError(f"{len(bad)} link(s) have out-of-range indices (nodes={n}).")

#     fig = go.Figure(data=[go.Sankey(
#         arrangement="snap",
#         node=dict(
#             pad=25,
#             thickness=14,
#             line=dict(color="rgba(255,255,255,0.3)", width=0.5),
#             label=nodes,
#             color=colors,
#             customdata=customs,
#             hovertemplate="<b>%{customdata}</b><extra></extra>",
#         ),
#         link=dict(
#             source=srcs,
#             target=tgts,
#             value=vals,
#             label=llbls,
#             color=lclrs,
#             hovertemplate="<b>%{label}</b><br>Flow: %{value:.2f}<extra></extra>",
#         ),
#     )])

#     fig.update_layout(
#         title_text="",                                # ① explicit "" not None
#         font=dict(color="#0F172A", size=13, family="Arial, sans-serif"),
#         paper_bgcolor="#FFFFFF",
#         plot_bgcolor="#FFFFFF",
#         autosize=True,
#         height=_FIG_HEIGHT,                           # ⑧ doubled
#         margin=dict(l=10, r=10, t=10, b=10),
#     )

#     # Render as a self-contained div (no full HTML boilerplate)
#     div = pyo.plot(
#         fig,
#         include_plotlyjs="cdn",
#         output_type="div",
#         config={"displaylogo": False, "displayModeBar": False},  # ② no void(0)
#     )

#     # Wrap: CSS is INSIDE the same document as the Plotly SVG  ③④
#     return f"""<!DOCTYPE html>
# <html>
# <head><meta charset="utf-8">{_INNER_CSS}</head>
# <body>{div}</body>
# </html>"""


# # ─────────────────────────────────────────────────────────────────────────────
# # Main render
# # ─────────────────────────────────────────────────────────────────────────────

# def render():
#     data            = st.session_state.data
#     summary         = st.session_state.summary
#     MATERIAL_LABELS = st.session_state.material_labels

#     st.markdown(
#         "<div style='font-size:15px;font-weight:700;margin-bottom:2px;'>"
#         "Supply Network</div>"
#         "<div style='font-size:12px;color:#64748B;margin-bottom:14px;'>"
#         "BOM structure · Supplier locations · Risk cascade · Consolidation"
#         "</div>",
#         unsafe_allow_html=True,
#     )

#     snn  = st.selectbox(
#         "Finished Good", [r["name"] for _, r in summary.iterrows()], key="snm"
#     )
#     snid = summary[summary.name == snn]["material"].values[0]
#     snr  = summary[summary.material == snid].iloc[0]
#     bsn  = get_bom_components(data, snid)

#     if not len(bsn):
#         st.warning("🕸️  No BOM data found for this material.")
#         return

#     cw         = int(bsn["Supplier Name(Vendor)"].notna().sum())
#     cn         = int(bsn["Supplier Display"].str.startswith("⚠", na=False).sum())
#     us         = int(bsn["Supplier Name(Vendor)"].dropna().nunique())
#     tc         = len(bsn)
#     inhouse_n  = int((bsn["Procurement type"] == "E").sum())
#     external_n = int((bsn["Procurement type"] == "F").sum())

#     # KPI cards
#     for col, val, lbl, vc in zip(
#         st.columns(4),
#         [tc,        inhouse_n,  cn,                                  us],
#         ["Total",   "Inhouse",  "Missing Supplier",  "Unique Suppliers"],
#         ["#1E293B", "#22C55E",  "#F59E0B" if cn > 0 else "#1E293B", "#1E293B"],
#     ):
#         with col:
#             st.markdown(
#                 f"<div class='sc'><div style='flex:1'>"
#                 f"<div class='sv' style='color:{vc}'>{val}</div>"
#                 f"<div class='sl'>{lbl}</div></div></div>",
#                 unsafe_allow_html=True,
#             )

#     sn_tab, comp_tab, risk_tab = st.tabs(
#         ["🕸️  BOM Map", "📋  Components", "⚠️  Risk Analysis"]
#     )

#     # ── BOM Map ───────────────────────────────────────────────────────────────
#     with sn_tab:

#         # ⑥ Chart heading card
#         rc = _RISK_COLOUR.get(snr["risk"], "#94A3B8")
#         st.markdown(
#             f"<div style='display:flex;align-items:center;gap:10px;"
#             f"padding:8px 12px;background:#F8FAFC;border:1px solid #E2E8F0;"
#             f"border-radius:8px;margin-bottom:8px;'>"
#             f"<span style='font-size:13px;font-weight:600;color:#1E293B;'>"
#             f"📦 {snr['name']}</span>"
#             f"<span style='font-size:11px;padding:2px 8px;border-radius:12px;"
#             f"background:{rc}22;color:{rc};font-weight:600;border:1px solid {rc}55;'>"
#             f"{snr['risk']}</span>"
#             f"<span style='font-size:11px;color:#64748B;margin-left:auto;'>"
#             f"{tc} components · {us} ext. suppliers</span>"
#             f"</div>",
#             unsafe_allow_html=True,
#         )

#         sec("BOM Propagation Map")
#         _legend()

#         try:
#             chart_html = _build_sankey_html(bsn, snr)
#             # ③④ CSS inside iframe → stroke:none + fill:#0F172A reach SVG text
#             components.html(chart_html, height=_IFRAME_H, scrolling=False)
#         except ValueError as exc:
#             st.error(f"⚠️  Could not render Sankey: {exc}")
#             with st.expander("🔍  Raw BOM data (debug)"):
#                 st.dataframe(bsn)

#         if st.session_state.get("azure_client"):
#             if st.button("◈ Interpret BOM Map", key="interp_bom_sankey"):
#                 with st.spinner("ARIA interpreting…"):
#                     bom_ctx = {
#                         "material": snr["name"], "total_components": tc,
#                         "inhouse": inhouse_n, "external_named": cw - inhouse_n,
#                         "missing_supplier": cn, "unique_suppliers": us,
#                         "risk": snr["risk"],
#                     }
#                     interp = interpret_chart(
#                         st.session_state.azure_client, AZURE_DEPLOYMENT,
#                         "BOM Risk Propagation Map", bom_ctx,
#                         "What are the key supply chain risks in this BOM "
#                         "and what should procurement prioritise?",
#                     )
#                 st.markdown(
#                     f"<div class='ic' style='margin-top:8px;'>"
#                     f"<div class='il'>◈ ARIA</div>"
#                     f"<div class='ib'>{interp}</div></div>",
#                     unsafe_allow_html=True,
#                 )

#     # ── Component Detail ──────────────────────────────────────────────────────
#     with comp_tab:
#         sec("Component Detail")
#         rows = []
#         for _, b in bsn.iterrows():
#             eq = b.get("Effective Order Qty", b["Comp. Qty (CUn)"])
#             try:
#                 fq = ("1 (Fixed)" if b.get("Fixed Qty Flag", False)
#                       else str(round(float(eq), 3)) if pd.notna(eq) else "—")
#             except (TypeError, ValueError):
#                 fq = "—"
#             sp = b.get("Standard Price")
#             rows.append({
#                 "Material":    _s(b.get("Material")),
#                 "Description": _s(b.get("Material Description"), mx=36),
#                 "Level":       _s(b.get("Level"), mx=25),
#                 "Qty":         fq,
#                 "Unit":        _s(b.get("Component unit")),
#                 "Type":        _s(b.get("Procurement Label")),
#                 "Supplier":    _s(b.get("Supplier Display")),
#                 "Location":    _s(b.get("Supplier Location")),
#                 "Transit":     f"{b.get('Transit Days')}d" if b.get("Transit Days") is not None else "—",
#                 "Std Price":   f"${sp:.2f}" if pd.notna(sp) else "—",
#             })

#         df_bd = pd.DataFrame(rows)
#         sup_r = JsCode(
#             "class R{init(p){"
#             "const v=p.value!=null?String(p.value):'';"
#             "this.e=document.createElement('span');"
#             "if(v.startsWith('⚠')){"
#             "this.e.style.cssText='background:#FEF3C7;color:#D97706;padding:2px 6px;border-radius:4px;font-size:10px;';"
#             "this.e.textContent=v;"
#             "}else if(v==='Revvity Inhouse'){"
#             "this.e.style.cssText='background:#DCFCE7;color:#16a34a;padding:2px 6px;border-radius:4px;font-size:10px;';"
#             "this.e.textContent='🏭 '+v;"
#             "}else if(v===''||v==='—'){"
#             "this.e.style.cssText='color:#94A3B8;font-size:10px;';"
#             "this.e.textContent='—';"
#             "}else{"
#             "this.e.style.cssText='background:#EFF6FF;color:#2563EB;padding:2px 6px;border-radius:4px;font-size:10px;';"
#             "this.e.textContent='🚚 '+v;"
#             "}}getGui(){return this.e;}}"
#         )
#         gb = GridOptionsBuilder.from_dataframe(df_bd)
#         gb.configure_column("Material",    width=82)
#         gb.configure_column("Description", width=215)
#         gb.configure_column("Level",       width=85)
#         gb.configure_column("Qty",         width=75)
#         gb.configure_column("Unit",        width=50)
#         gb.configure_column("Type",        width=100)
#         gb.configure_column("Supplier",    width=170, cellRenderer=sup_r)
#         gb.configure_column("Location",    width=130)
#         gb.configure_column("Transit",     width=58)
#         gb.configure_column("Std Price",   width=80)
#         gb.configure_grid_options(rowHeight=36, headerHeight=32)
#         gb.configure_default_column(resizable=True, sortable=True, filter=False)
#         AgGrid(df_bd, gridOptions=gb.build(), height=320,
#                allow_unsafe_jscode=True, theme="alpine", custom_css=_AGGRID_CSS)

#     # ── Risk Cascade ──────────────────────────────────────────────────────────
#     with risk_tab:
#         sec("Risk Cascade Analysis")
#         risks = []

#         if snr["risk"] in ("CRITICAL", "WARNING"):
#             risks.append({
#                 "icon": "⛔", "sev": 3, "color": "#EF4444", "bg": "#FEF2F2",
#                 "title": f"Finished Good at {snr['risk'].title()} Risk",
#                 "detail": (
#                     f"{snr['name']} has {round(snr['days_cover'])}d cover. "
#                     f"SIH={round(snr['sih'])} vs SAP SS={round(snr['safety_stock'])}."
#                 ),
#                 "action": f"Order {int(snr.get('repl_quantity', 0))} units immediately.",
#             })
#         if cn > 0:
#             risks.append({
#                 "icon": "⚠", "sev": 2, "color": "#F59E0B", "bg": "#FFFBEB",
#                 "title": f"Missing Supplier Data — {cn} External Components",
#                 "detail": f"{cn} of {external_n} external components have no named supplier.",
#                 "action": "Verify and update BOM with supplier names and lead times.",
#             })
#         if 0 < us <= 2:
#             risks.append({
#                 "icon": "⚠", "sev": 2, "color": "#F59E0B", "bg": "#FFFBEB",
#                 "title": f"Supplier Concentration — {us} Unique Supplier(s)",
#                 "detail": f"High dependency on {us} supplier(s) cascades across multiple components.",
#                 "action": "Evaluate dual-sourcing for critical external components.",
#             })
#         if external_n > 0:
#             locs = list({
#                 str(v) for v in bsn[bsn["Procurement type"] == "F"]
#                 ["Supplier Location"].dropna().tolist()[:4]
#             })
#             risks.append({
#                 "icon": "🌍", "sev": 1, "color": "#3B82F6", "bg": "#EFF6FF",
#                 "title": f"External Procurement: {external_n} Components",
#                 "detail": f"Suppliers in: {', '.join(locs) if locs else 'unknown'}.",
#                 "action": "Add stock buffers for long-transit items.",
#             })

#         if not risks:
#             st.success("✓  No critical propagation risks identified.")
#         else:
#             for r in sorted(risks, key=lambda x: -x["sev"]):
#                 st.markdown(
#                     f"<div style='background:{r['bg']};border:1px solid {r['color']}33;"
#                     f"border-left:4px solid {r['color']};border-radius:8px;"
#                     f"padding:12px 14px;margin-bottom:8px;'>"
#                     f"<div style='display:flex;align-items:center;gap:8px;margin-bottom:4px;'>"
#                     f"<span style='font-size:15px'>{r['icon']}</span>"
#                     f"<span style='font-size:12px;font-weight:600;color:{r['color']}'>"
#                     f"{r['title']}</span></div>"
#                     f"<div style='font-size:11px;color:#475569;margin-bottom:4px'>"
#                     f"{r['detail']}</div>"
#                     f"<div style='font-size:11px;color:{r['color']}'>"
#                     f"→ {r['action']}</div></div>",
#                     unsafe_allow_html=True,
#                 )

#         consol   = get_supplier_consolidation(data, summary)
#         relevant = consol[
#             consol.material_list.apply(lambda x: snid in x)
#             & (consol.finished_goods_supplied > 1)
#             & consol.consolidation_opportunity
#         ]
#         if len(relevant) > 0:
#             sec("Supplier Consolidation Opportunities")
#             for _, r2 in relevant.iterrows():
#                 others = [MATERIAL_LABELS.get(m, m)[:18]
#                           for m in r2["material_list"] if m != snid]
#                 st.markdown(
#                     f"<div class='prow'><div style='font-size:14px'>🏭</div>"
#                     f"<div style='flex:1'>"
#                     f"<div style='font-size:12px;font-weight:600'>{r2['supplier']}</div>"
#                     f"<div style='font-size:10px;color:#64748B'>"
#                     f"{r2['city']} · {r2['email']}</div>"
#                     f"<div style='font-size:10px;color:#475569;margin-top:2px'>"
#                     f"Also supplies: {', '.join(others[:3])}</div></div>"
#                     f"<div style='font-size:10px;font-weight:600;color:var(--or)'>"
#                     f"⚡ Consolidate order</div></div>",
#                     unsafe_allow_html=True,
#                 )

#         if st.session_state.get("azure_client"):
#             sec("Ask ARIA About This Network")
#             st.info("ℹ️  Insights scoped to the currently selected finished good.")
#             uq = st.text_input(
#                 "Question",
#                 placeholder="e.g. Which supplier provides more than 1 component?",
#                 key="snq", label_visibility="collapsed",
#             )
#             if uq and st.button("Ask ARIA", key="sna"):
#                 lines = []
#                 for _, row in bsn.iterrows():
#                     md  = _s(row.get("Material Description"),
#                              fb=str(row.get("Material")), mx=40)
#                     qty = row.get("Effective Order Qty") or row.get("Comp. Qty (CUn)")
#                     fix = "X (order exactly 1)" if row.get("Fixed Qty Flag") else ""
#                     sup = _s(row.get("Supplier Display"))
#                     loc = _s(row.get("Supplier Location"))
#                     tra = _s(row.get("Transit Days"))
#                     rel = _s(row.get("Supplier Reliability"))
#                     sp  = row.get("Standard Price")
#                     pr  = f"${sp:.2f}" if pd.notna(sp) else "—"
#                     lines.append(
#                         f"- {md} | Qty:{qty} {fix} | Price:{pr} "
#                         f"| Supplier:{sup} | Loc:{loc} | Transit:{tra}d | Rel:{rel}"
#                     )
#                 ctx = (
#                     f"Material: {snr['name']} (ID:{snid})\n"
#                     f"Risk:{snr['risk']} | Total:{tc} | Inhouse:{inhouse_n} "
#                     f"| External:{external_n} | Missing:{cn} | Suppliers:{us}\n"
#                     f"BOM:\n" + "\n".join(lines)
#                 )
#                 with st.spinner("Thinking…"):
#                     ans = chat_with_data(
#                         st.session_state.azure_client, AZURE_DEPLOYMENT, uq, ctx
#                     )
#                 st.markdown(
#                     f"<div class='ic' style='margin-top:8px;'>"
#                     f"<div class='il'>◈ ARIA</div>"
#                     f"<div class='ib'>{ans}</div></div>",
#                     unsafe_allow_html=True,
#                 )

#     st.markdown(
#         '<div class="pfooter">🕸️  Powered by <strong>MResult</strong></div>',
#         unsafe_allow_html=True,
#     )


# # """
# # tabs/supply_network.py – Supply Network  (BOM Map · Components · Risk · Consolidation)

# # ALL FIXES APPLIED & TESTED AGAINST Fi11_BOM_MResult_v2.xlsx (7 BOMs, 109 rows):
# #   ① "undefined" heading   → title_text="" (explicit empty str, not None)
# #   ② javascript:void(0)    → config={"displaylogo":False,"displayModeBar":False}
# #   ③ Grey / blurry labels  → CSS injection removes SVG stroke (the halo/shadow);
# #                             font.color="#1E293B", size=13, family="Arial"
# #   ④ Node too thick        → thickness 22 → 15
# #   ⑤ No chart heading      → st.markdown title card above the Plotly chart
# #   ⑥ All-grey links        → links now coloured by component type (green/amber/blue/purple)
# #   ⑦ Bold/shadow text      → stroke:none injected via Streamlit CSS override
# #   ⑧ Messy legend          → simple st.columns badges, no bold, plain weight
# # """

# # import streamlit as st
# # import pandas as pd
# # import plotly.graph_objects as go
# # from st_aggrid import AgGrid, GridOptionsBuilder, JsCode

# # from utils.helpers import sec, AZURE_DEPLOYMENT
# # from data_loader import get_bom_components, get_supplier_consolidation
# # from agent import interpret_chart, chat_with_data

# # # ── AgGrid CSS ───────────────────────────────────────────────────────────────
# # _AGGRID_CSS = {
# #     ".ag-root-wrapper": {"border": "1px solid #E2E8F0!important",
# #                          "border-radius": "12px!important"},
# #     ".ag-header":       {"background": "#F8FAFE!important"},
# #     ".ag-row-even":     {"background": "#FFFFFF!important"},
# #     ".ag-row-odd":      {"background": "#F8FAFE!important"},
# # }

# # _RISK_COLOUR = {"CRITICAL": "#EF4444", "WARNING": "#F59E0B", "HEALTHY": "#22C55E"}

# # # ── Plotly config: removes modebar + logo which inject javascript:void(0) ────
# # _CFG = {"displaylogo": False, "displayModeBar": False}

# # # ── Link colours by flow type ────────────────────────────────────────────────
# # _LC = {
# #     "inhouse":  "rgba(34,197,94,0.22)",
# #     "missing":  "rgba(245,158,11,0.22)",
# #     "external": "rgba(59,130,246,0.22)",
# #     "supplier": "rgba(139,92,246,0.22)",
# # }

# # # ── CSS injected once per page: removes the SVG stroke/halo that makes
# # #    Plotly Sankey labels look blurry and bold on white backgrounds ────────────
# # _SANKEY_CSS = """
# # <style>
# # /* Remove SVG stroke halo from Plotly Sankey node labels */
# # [data-testid="stPlotlyChart"] text,
# # .js-plotly-plot text,
# # .plot-container text {
# #     stroke: none        !important;
# #     stroke-width: 0     !important;
# #     paint-order: normal !important;
# #     fill: #1E293B       !important;
# # }
# # </style>
# # """


# # # ─────────────────────────────────────────────────────────────────────────────
# # # String sanitiser — Plotly renders 'undefined' for '' or None
# # # ─────────────────────────────────────────────────────────────────────────────

# # def _s(val, fb="—", mx=0):
# #     if val is None:
# #         return fb
# #     if isinstance(val, float) and pd.isna(val):
# #         return fb
# #     t = str(val).strip()
# #     if t in ("", "nan", "None", "NaN"):
# #         return fb
# #     return t[:mx] if mx else t


# # # ─────────────────────────────────────────────────────────────────────────────
# # # Legend  (native st.columns, no CSS-class dependency)
# # # ─────────────────────────────────────────────────────────────────────────────

# # def _legend():
# #     st.markdown(
# #         "<div style='border-left:3px solid #3B82F6;padding:4px 10px;"
# #         "font-size:12px;color:#475569;margin-bottom:8px;'>"
# #         "Node colours &nbsp;·&nbsp; "
# #         "Root = finished-good risk: 🔴 Critical &nbsp; 🟠 Warning &nbsp; 🟢 Healthy"
# #         "</div>",
# #         unsafe_allow_html=True,
# #     )
# #     for col, (hex_c, emoji, label) in zip(
# #         st.columns(4),
# #         [
# #             ("#3B82F6", "🔵", "External – named supplier"),
# #             ("#22C55E", "🟢", "Inhouse (Revvity)"),
# #             ("#F59E0B", "🟡", "Missing supplier"),
# #             ("#8B5CF6", "🟣", "Supplier node"),
# #         ],
# #     ):
# #         with col:
# #             st.markdown(
# #                 f"<div style='border:1px solid {hex_c}55;border-radius:6px;"
# #                 f"padding:5px 8px;text-align:center;font-size:11px;"
# #                 f"color:{hex_c};margin-bottom:8px;'>"
# #                 f"{emoji} {label}</div>",
# #                 unsafe_allow_html=True,
# #             )


# # # ─────────────────────────────────────────────────────────────────────────────
# # # Sankey builder  (validated against all 7 BOMs in Fi11_BOM_MResult_v2.xlsx)
# # # ─────────────────────────────────────────────────────────────────────────────

# # def _sankey(bsn: pd.DataFrame, snr) -> go.Figure:
# #     nodes: list  = []
# #     colors: list = []
# #     customs: list = []
# #     nmap: dict   = {}

# #     def _add(key, lbl, clr, cst):
# #         key = _s(key, fb="__unk__")
# #         if key not in nmap:
# #             nmap[key] = len(nodes)
# #             nodes.append(_s(lbl, fb=key, mx=38))
# #             colors.append(clr)
# #             customs.append(_s(cst, fb=_s(lbl, fb=key)))
# #         return nmap[key]

# #     risk    = _s(snr.get("risk", ""), fb="UNKNOWN")
# #     fg_name = _s(snr.get("name", ""), fb=str(snr.get("material", "FG")))
# #     root = _add(
# #         f"FG_{snr.get('material','root')}",
# #         fg_name,
# #         _RISK_COLOUR.get(risk, "#94A3B8"),
# #         f"Finished Good: {fg_name} | Risk: {risk} | Cover: {round(float(snr.get('days_cover',0)))}d",
# #     )

# #     srcs: list = []; tgts: list = []; vals: list = []
# #     llbls: list = []; lclrs: list = []

# #     for _, row in bsn.iterrows():
# #         mat   = _s(row.get("Material"),             fb="UNK")
# #         desc  = _s(row.get("Material Description"), fb=mat,  mx=32)
# #         proc  = _s(row.get("Procurement type"),     fb="").upper()
# #         sup   = _s(row.get("Supplier Display"),     fb="—")

# #         try:
# #             qty = float(row.get("Effective Order Qty") or row.get("Comp. Qty (CUn)"))
# #             qty = qty if qty > 0 else 0.01
# #         except (TypeError, ValueError):
# #             qty = 0.01

# #         if proc == "E":
# #             nc, cst, lc = "#22C55E", f"Inhouse (Revvity) | {desc}", _LC["inhouse"]
# #         elif sup.startswith("⚠") or sup == "—":
# #             nc, cst, lc = "#F59E0B", f"No supplier data | {desc}", _LC["missing"]
# #         else:
# #             transit = _s(row.get("Transit Days"), fb="—")
# #             nc      = "#3B82F6"
# #             cst     = f"{desc} | Supplier: {sup} | Transit: {transit}d"
# #             lc      = _LC["external"]

# #         ci = _add(f"COMP_{mat}", desc, nc, cst)
# #         srcs.append(root); tgts.append(ci); vals.append(qty)
# #         llbls.append(desc); lclrs.append(lc)

# #         is_ext = (
# #             proc == "F"
# #             and sup not in ("—", "Revvity Inhouse")
# #             and not sup.startswith("⚠")
# #         )
# #         if is_ext:
# #             loc = _s(row.get("Supplier Location"),   fb="—")
# #             rel = _s(row.get("Supplier Reliability"), fb="—")
# #             si  = _add(
# #                 f"SUP_{sup}", sup[:28], "#8B5CF6",
# #                 f"Supplier: {sup} | Location: {loc} | Reliability: {rel}",
# #             )
# #             srcs.append(ci); tgts.append(si); vals.append(qty)
# #             llbls.append(sup[:28]); lclrs.append(_LC["supplier"])

# #     n = len(nodes)
# #     if n == 0 or not srcs:
# #         raise ValueError("No nodes or links generated from BOM data.")
# #     bad = [(i, s, t) for i, (s, t) in enumerate(zip(srcs, tgts))
# #            if not (0 <= s < n) or not (0 <= t < n)]
# #     if bad:
# #         raise ValueError(f"{len(bad)} link(s) have out-of-range indices (nodes={n}).")

# #     fig = go.Figure(data=[go.Sankey(
# #         arrangement="snap",
# #         node=dict(
# #             pad=20,
# #             thickness=15,          # ④ reduced from 22
# #             line=dict(color="rgba(255,255,255,0.5)", width=1),
# #             label=nodes,           # plain Python list[str] – no None
# #             color=colors,
# #             customdata=customs,    # plain Python list[str] – no None
# #             hovertemplate="<b>%{customdata}</b><extra></extra>",
# #         ),
# #         link=dict(
# #             source=srcs,
# #             target=tgts,
# #             value=vals,
# #             label=llbls,
# #             color=lclrs,           # ⑥ coloured by type
# #             hovertemplate="<b>%{label}</b><br>Flow: %{value:.2f}<extra></extra>",
# #         ),
# #     )])

# #     fig.update_layout(
# #         title_text="",             # ① explicit empty string – never "undefined"
# #         # ③ dark near-black; Arial avoids browser font-smoothing issues
# #         font=dict(color="#1E293B", size=13, family="Arial, sans-serif"),
# #         paper_bgcolor="#FFFFFF",   # solid white – halo invisible on white bg
# #         plot_bgcolor="#FFFFFF",
# #         height=520,
# #         margin=dict(l=8, r=8, t=8, b=8),
# #     )
# #     return fig


# # # ─────────────────────────────────────────────────────────────────────────────
# # # Main render
# # # ─────────────────────────────────────────────────────────────────────────────

# # def render():
# #     # ③ ⑦ Inject CSS once – removes SVG stroke halo from Plotly Sankey labels
# #     st.markdown(_SANKEY_CSS, unsafe_allow_html=True)

# #     data            = st.session_state.data
# #     summary         = st.session_state.summary
# #     MATERIAL_LABELS = st.session_state.material_labels

# #     st.markdown(
# #         "<div style='font-size:15px;font-weight:700;margin-bottom:2px;'>"
# #         "Supply Network</div>"
# #         "<div style='font-size:12px;color:#64748B;margin-bottom:14px;'>"
# #         "BOM structure · Supplier locations · Risk cascade · Consolidation</div>",
# #         unsafe_allow_html=True,
# #     )

# #     snn  = st.selectbox("Finished Good", [r["name"] for _, r in summary.iterrows()], key="snm")
# #     snid = summary[summary.name == snn]["material"].values[0]
# #     snr  = summary[summary.material == snid].iloc[0]
# #     bsn  = get_bom_components(data, snid)

# #     if not len(bsn):
# #         st.warning("🕸️  No BOM data found for this material.")
# #         return

# #     cw         = int(bsn["Supplier Name(Vendor)"].notna().sum())
# #     cn         = int(bsn["Supplier Display"].str.startswith("⚠", na=False).sum())
# #     us         = int(bsn["Supplier Name(Vendor)"].dropna().nunique())
# #     tc         = len(bsn)
# #     inhouse_n  = int((bsn["Procurement type"] == "E").sum())
# #     external_n = int((bsn["Procurement type"] == "F").sum())

# #     # KPI cards
# #     for col, val, lbl, vc in zip(
# #         st.columns(4),
# #         [tc, inhouse_n, cn, us],
# #         ["Total Components", "Revvity Inhouse", "Missing Supplier", "Unique Ext Suppliers"],
# #         ["#1E293B", "#22C55E", "#F59E0B" if cn > 0 else "#1E293B", "#1E293B"],
# #     ):
# #         with col:
# #             st.markdown(
# #                 f"<div class='sc'><div style='flex:1'>"
# #                 f"<div class='sv' style='color:{vc}'>{val}</div>"
# #                 f"<div class='sl'>{lbl}</div></div></div>",
# #                 unsafe_allow_html=True,
# #             )

# #     sn_tab, comp_tab, risk_tab = st.tabs(
# #         ["🕸️  BOM Map", "📋  Components", "⚠️  Risk Analysis"]
# #     )

# #     # ── BOM Map ───────────────────────────────────────────────────────────────
# #     with sn_tab:

# #         # ⑤ Chart heading above the Plotly chart (not inside it)
# #         risk_badge_colour = _RISK_COLOUR.get(snr["risk"], "#94A3B8")
# #         st.markdown(
# #             f"<div style='display:flex;align-items:center;gap:10px;"
# #             f"padding:8px 12px;background:#F8FAFC;border:1px solid #E2E8F0;"
# #             f"border-radius:8px;margin-bottom:8px;'>"
# #             f"<span style='font-size:13px;font-weight:600;color:#1E293B;'>"
# #             f"📦 {snr['name']}</span>"
# #             f"<span style='font-size:11px;padding:2px 8px;border-radius:12px;"
# #             f"background:{risk_badge_colour}22;color:{risk_badge_colour};"
# #             f"font-weight:600;border:1px solid {risk_badge_colour}55;'>"
# #             f"{snr['risk']}</span>"
# #             f"<span style='font-size:11px;color:#64748B;margin-left:auto;'>"
# #             f"{tc} components · {us} suppliers</span>"
# #             f"</div>",
# #             unsafe_allow_html=True,
# #         )

# #         sec("BOM Propagation Map")
# #         _legend()

# #         try:
# #             fig = _sankey(bsn, snr)
# #             # ② displaylogo + displayModeBar=False removes javascript:void(0) links
# #             st.plotly_chart(fig, use_container_width=True, config=_CFG)
# #         except ValueError as exc:
# #             st.error(f"⚠️  Could not render Sankey diagram: {exc}")
# #             st.info("Check that BOM rows have valid Material IDs and non-zero quantities.")
# #             with st.expander("🔍  Raw BOM data (debug)"):
# #                 st.dataframe(bsn)

# #         if st.session_state.get("azure_client"):
# #             if st.button("◈ Interpret BOM Map", key="interp_bom_sankey"):
# #                 with st.spinner("ARIA interpreting…"):
# #                     bom_ctx = {
# #                         "material": snr["name"], "total_components": tc,
# #                         "inhouse": inhouse_n,
# #                         "external_named": cw - inhouse_n,
# #                         "missing_supplier": cn, "unique_suppliers": us,
# #                         "risk": snr["risk"],
# #                     }
# #                     interp = interpret_chart(
# #                         st.session_state.azure_client, AZURE_DEPLOYMENT,
# #                         "BOM Risk Propagation Map", bom_ctx,
# #                         "What are the key supply chain risks in this BOM "
# #                         "and what should procurement prioritise?",
# #                     )
# #                 st.markdown(
# #                     f"<div class='ic' style='margin-top:8px;'>"
# #                     f"<div class='il'>◈ ARIA</div>"
# #                     f"<div class='ib'>{interp}</div></div>",
# #                     unsafe_allow_html=True,
# #                 )

# #     # ── Component Detail ──────────────────────────────────────────────────────
# #     with comp_tab:
# #         sec("Component Detail")
# #         rows = []
# #         for _, b in bsn.iterrows():
# #             eq = b.get("Effective Order Qty", b["Comp. Qty (CUn)"])
# #             try:
# #                 fq = ("1 (Fixed)" if b.get("Fixed Qty Flag", False)
# #                       else str(round(float(eq), 3)) if pd.notna(eq) else "—")
# #             except (TypeError, ValueError):
# #                 fq = "—"
# #             sp = b.get("Standard Price")
# #             rows.append({
# #                 "Material":    _s(b.get("Material")),
# #                 "Description": _s(b.get("Material Description"), mx=36),
# #                 "Level":       _s(b.get("Level"),                mx=25),
# #                 "Qty":         fq,
# #                 "Unit":        _s(b.get("Component unit")),
# #                 "Type":        _s(b.get("Procurement Label")),
# #                 "Supplier":    _s(b.get("Supplier Display")),
# #                 "Location":    _s(b.get("Supplier Location")),
# #                 "Transit":     f"{b.get('Transit Days')}d" if b.get("Transit Days") is not None else "—",
# #                 "Std Price":   f"${sp:.2f}" if pd.notna(sp) else "—",
# #             })

# #         df_bd = pd.DataFrame(rows)

# #         # Cell renderer uses textContent (never innerHTML) to avoid
# #         # the javascript:void(0) issue from anchor elements
# #         sup_r = JsCode(
# #             "class R{"
# #             "init(p){"
# #             "const v = p.value != null ? String(p.value) : '';"
# #             "this.e = document.createElement('span');"
# #             "if(v.startsWith('⚠')){"
# #             "this.e.style.cssText='background:#FEF3C7;color:#D97706;"
# #             "padding:2px 6px;border-radius:4px;font-size:10px;';"
# #             "this.e.textContent = v;"
# #             "}else if(v==='Revvity Inhouse'){"
# #             "this.e.style.cssText='background:#DCFCE7;color:#16a34a;"
# #             "padding:2px 6px;border-radius:4px;font-size:10px;';"
# #             "this.e.textContent = '🏭 ' + v;"
# #             "}else if(v==='' || v==='—'){"
# #             "this.e.style.cssText='color:#94A3B8;font-size:10px;';"
# #             "this.e.textContent = '—';"
# #             "}else{"
# #             "this.e.style.cssText='background:#EFF6FF;color:#2563EB;"
# #             "padding:2px 6px;border-radius:4px;font-size:10px;';"
# #             "this.e.textContent = '🚚 ' + v;"
# #             "}}"
# #             "getGui(){return this.e;}}"
# #         )

# #         gb = GridOptionsBuilder.from_dataframe(df_bd)
# #         gb.configure_column("Material",    width=82)
# #         gb.configure_column("Description", width=215)
# #         gb.configure_column("Level",       width=85)
# #         gb.configure_column("Qty",         width=75)
# #         gb.configure_column("Unit",        width=50)
# #         gb.configure_column("Type",        width=100)
# #         gb.configure_column("Supplier",    width=170, cellRenderer=sup_r)
# #         gb.configure_column("Location",    width=130)
# #         gb.configure_column("Transit",     width=58)
# #         gb.configure_column("Std Price",   width=80)
# #         gb.configure_grid_options(rowHeight=36, headerHeight=32)
# #         gb.configure_default_column(resizable=True, sortable=True, filter=False)
# #         AgGrid(df_bd, gridOptions=gb.build(), height=320,
# #                allow_unsafe_jscode=True, theme="alpine", custom_css=_AGGRID_CSS)

# #     # ── Risk Cascade ──────────────────────────────────────────────────────────
# #     with risk_tab:
# #         sec("Risk Cascade Analysis")
# #         risks = []

# #         if snr["risk"] in ("CRITICAL", "WARNING"):
# #             risks.append({
# #                 "icon": "⛔", "sev": 3, "color": "#EF4444", "bg": "#FEF2F2",
# #                 "title": f"Finished Good at {snr['risk'].title()} Risk",
# #                 "detail": (
# #                     f"{snr['name']} has {round(snr['days_cover'])}d of cover. "
# #                     f"SIH={round(snr['sih'])} vs SAP SS={round(snr['safety_stock'])}."
# #                 ),
# #                 "action": (
# #                     f"Order {int(snr.get('repl_quantity', 0))} units immediately."
# #                 ),
# #             })
# #         if cn > 0:
# #             risks.append({
# #                 "icon": "⚠", "sev": 2, "color": "#F59E0B", "bg": "#FFFBEB",
# #                 "title": f"Missing Supplier Data — {cn} External Components",
# #                 "detail": (
# #                     f"{cn} of {external_n} external components have no named supplier."
# #                 ),
# #                 "action": "Verify and update BOM with supplier names and lead times.",
# #             })
# #         if 0 < us <= 2:
# #             risks.append({
# #                 "icon": "⚠", "sev": 2, "color": "#F59E0B", "bg": "#FFFBEB",
# #                 "title": f"Supplier Concentration — {us} Unique Supplier(s)",
# #                 "detail": (
# #                     f"High dependency on {us} supplier(s). "
# #                     f"Any disruption cascades across multiple components."
# #                 ),
# #                 "action": "Evaluate dual-sourcing for critical external components.",
# #             })
# #         if external_n > 0:
# #             locs = list({
# #                 str(v) for v in bsn[bsn["Procurement type"] == "F"]
# #                 ["Supplier Location"].dropna().tolist()[:4]
# #             })
# #             risks.append({
# #                 "icon": "🌍", "sev": 1, "color": "#3B82F6", "bg": "#EFF6FF",
# #                 "title": f"External Procurement: {external_n} Components",
# #                 "detail": (
# #                     f"Suppliers in: {', '.join(locs) if locs else 'unknown'}."
# #                 ),
# #                 "action": "Add stock buffers for long-transit items.",
# #             })

# #         if not risks:
# #             st.success("✓  No critical propagation risks identified.")
# #         else:
# #             for r in sorted(risks, key=lambda x: -x["sev"]):
# #                 st.markdown(
# #                     f"<div style='background:{r['bg']};border:1px solid {r['color']}33;"
# #                     f"border-left:4px solid {r['color']};border-radius:8px;"
# #                     f"padding:12px 14px;margin-bottom:8px;'>"
# #                     f"<div style='display:flex;align-items:center;gap:8px;margin-bottom:4px;'>"
# #                     f"<span style='font-size:15px'>{r['icon']}</span>"
# #                     f"<span style='font-size:12px;font-weight:600;color:{r['color']}'>"
# #                     f"{r['title']}</span></div>"
# #                     f"<div style='font-size:11px;color:#475569;margin-bottom:4px'>"
# #                     f"{r['detail']}</div>"
# #                     f"<div style='font-size:11px;color:{r['color']}'>"
# #                     f"→ {r['action']}</div>"
# #                     f"</div>",
# #                     unsafe_allow_html=True,
# #                 )

# #         # Consolidation
# #         consol   = get_supplier_consolidation(data, summary)
# #         relevant = consol[
# #             consol.material_list.apply(lambda x: snid in x)
# #             & (consol.finished_goods_supplied > 1)
# #             & consol.consolidation_opportunity
# #         ]
# #         if len(relevant) > 0:
# #             sec("Supplier Consolidation Opportunities")
# #             for _, r2 in relevant.iterrows():
# #                 others = [MATERIAL_LABELS.get(m, m)[:18]
# #                           for m in r2["material_list"] if m != snid]
# #                 st.markdown(
# #                     f"<div class='prow'><div style='font-size:14px'>🏭</div>"
# #                     f"<div style='flex:1'>"
# #                     f"<div style='font-size:12px;font-weight:600'>{r2['supplier']}</div>"
# #                     f"<div style='font-size:10px;color:#64748B'>"
# #                     f"{r2['city']} · {r2['email']}</div>"
# #                     f"<div style='font-size:10px;color:#475569;margin-top:2px'>"
# #                     f"Also supplies: {', '.join(others[:3])}</div>"
# #                     f"</div>"
# #                     f"<div style='font-size:10px;font-weight:600;color:var(--or)'>"
# #                     f"⚡ Consolidate order</div>"
# #                     f"</div>",
# #                     unsafe_allow_html=True,
# #                 )

# #         # Ask ARIA
# #         if st.session_state.get("azure_client"):
# #             sec("Ask ARIA About This Network")
# #             st.info("ℹ️  Insights scoped to the currently selected finished good.")
# #             uq = st.text_input(
# #                 "Question",
# #                 placeholder="e.g. Which supplier provides more than 1 component?",
# #                 key="snq", label_visibility="collapsed",
# #             )
# #             if uq and st.button("Ask ARIA", key="sna"):
# #                 lines = []
# #                 for _, row in bsn.iterrows():
# #                     md   = _s(row.get("Material Description"),
# #                               fb=str(row.get("Material")), mx=40)
# #                     qty  = row.get("Effective Order Qty") or row.get("Comp. Qty (CUn)")
# #                     fix  = "X (order exactly 1)" if row.get("Fixed Qty Flag") else ""
# #                     sup  = _s(row.get("Supplier Display"))
# #                     loc  = _s(row.get("Supplier Location"))
# #                     tra  = _s(row.get("Transit Days"))
# #                     rel  = _s(row.get("Supplier Reliability"))
# #                     sp   = row.get("Standard Price")
# #                     pr   = f"${sp:.2f}" if pd.notna(sp) else "—"
# #                     lines.append(
# #                         f"- {md} | Qty: {qty} {fix} | Price: {pr} "
# #                         f"| Supplier: {sup} | Location: {loc} "
# #                         f"| Transit: {tra}d | Reliability: {rel}"
# #                     )
# #                 ctx = (
# #                     f"Material: {snr['name']} (ID: {snid})\n"
# #                     f"Risk: {snr['risk']}\n"
# #                     f"Total: {tc} | Inhouse: {inhouse_n} | External: {external_n}\n"
# #                     f"Missing supplier: {cn} | Unique suppliers: {us}\n"
# #                     f"BOM:\n" + "\n".join(lines)
# #                 )
# #                 with st.spinner("Thinking…"):
# #                     ans = chat_with_data(
# #                         st.session_state.azure_client, AZURE_DEPLOYMENT, uq, ctx
# #                     )
# #                 st.markdown(
# #                     f"<div class='ic' style='margin-top:8px;'>"
# #                     f"<div class='il'>◈ ARIA</div>"
# #                     f"<div class='ib'>{ans}</div></div>",
# #                     unsafe_allow_html=True,
# #                 )

# #     st.markdown(
# #         '<div class="pfooter">🕸️  Powered by <strong>MResult</strong></div>',
# #         unsafe_allow_html=True,
# #     )



# # # """
# # # tabs/supply_network.py
# # # Supply Network tab: BOM propagation map (Sankey diagram), component detail
# # # table, risk cascade analysis, and supplier consolidation opportunities.

# # # BUGS FIXED (tested against Fi11_BOM_MResult_v2.xlsx):
# # #   1. "undefined" Sankey heading  →  title=None gives {} in JSON; Plotly JS
# # #      reads that as undefined.  Fixed: title_text="" (explicit empty string).
# # #   2. javascript:void(0) links   →  Plotly modebar + logo inject these into
# # #      the Streamlit DOM.  Fixed: config={"displaylogo":False,
# # #      "displayModeBar":False} in st.plotly_chart().
# # #   3. Grey / blurry / bold text  →  Legend used font-weight:700 and dark hex
# # #      colours that bleed into Streamlit's theme.  Replaced with a clean,
# # #      lightweight native Streamlit st.columns legend.
# # #   4. paper_bgcolor transparent  →  Caused invisible labels in dark Streamlit
# # #      themes.  Fixed: white background + neutral font colour #374151.
# # #   5. All label / customdata strings are forced to plain Python str so
# # #      Plotly never receives None, float-nan, or numpy types.
# # # """

# # # import streamlit as st
# # # import pandas as pd
# # # import plotly.graph_objects as go
# # # from st_aggrid import AgGrid, GridOptionsBuilder, JsCode

# # # from utils.helpers import sec, note, sbadge, ORANGE, AZURE_DEPLOYMENT
# # # from data_loader import get_bom_components, get_supplier_consolidation
# # # from agent import interpret_chart, chat_with_data

# # # _AGGRID_CSS = {
# # #     ".ag-root-wrapper": {"border": "1px solid #E2E8F0!important",
# # #                          "border-radius": "12px!important"},
# # #     ".ag-header":       {"background": "#F8FAFE!important"},
# # #     ".ag-row-even":     {"background": "#FFFFFF!important"},
# # #     ".ag-row-odd":      {"background": "#F8FAFE!important"},
# # # }

# # # _RISK_COLOUR = {
# # #     "CRITICAL": "#EF4444",
# # #     "WARNING":  "#F59E0B",
# # #     "HEALTHY":  "#22C55E",
# # # }

# # # # ── Plotly chart config – removes modebar buttons and logo that inject
# # # #    javascript:void(0) links into the Streamlit DOM ──────────────────────────
# # # _PLOTLY_CFG = {
# # #     "displaylogo":    False,
# # #     "displayModeBar": False,
# # # }


# # # # ─────────────────────────────────────────────────────────────────────────────
# # # # Helper: guaranteed non-empty Python str
# # # # ─────────────────────────────────────────────────────────────────────────────

# # # def _s(val, fallback="—", maxlen=0):
# # #     """
# # #     Always return a plain Python str that is never empty, 'nan', or 'None'.
# # #     Plotly renders 'undefined' in JS whenever label / customdata is '' or None.
# # #     """
# # #     if val is None:
# # #         return fallback
# # #     if isinstance(val, float) and pd.isna(val):
# # #         return fallback
# # #     txt = str(val).strip()
# # #     if txt in ("", "nan", "None", "NaN"):
# # #         return fallback
# # #     return txt[:maxlen] if maxlen else txt


# # # # ─────────────────────────────────────────────────────────────────────────────
# # # # Legend (native Streamlit – no CSS-class dependency)
# # # # ─────────────────────────────────────────────────────────────────────────────

# # # def _render_legend():
# # #     """Colour legend using st.columns so it always shows correctly."""

# # #     # Header bar – simple, no bold, standard weight
# # #     st.markdown(
# # #         "<div style='"
# # #         "border-left: 4px solid #3B82F6;"
# # #         "padding: 6px 12px;"
# # #         "margin-bottom: 8px;"
# # #         "font-size: 12px;"
# # #         "color: #374151;"
# # #         "'>"
# # #         "Colour legend &nbsp;·&nbsp; "
# # #         "Root node matches finished-good risk: "
# # #         "🔴 Critical &nbsp; 🟠 Warning &nbsp; 🟢 Healthy"
# # #         "</div>",
# # #         unsafe_allow_html=True,
# # #     )

# # #     badges = [
# # #         ("#3B82F6", "🔵", "External – named supplier"),
# # #         ("#22C55E", "🟢", "Inhouse (Revvity)"),
# # #         ("#F59E0B", "🟡", "External – missing supplier"),
# # #         ("#8B5CF6", "🟣", "Supplier node"),
# # #     ]
# # #     cols = st.columns(4)
# # #     for col, (hex_c, emoji, label) in zip(cols, badges):
# # #         with col:
# # #             st.markdown(
# # #                 f"<div style='"
# # #                 f"border: 1px solid {hex_c}66;"
# # #                 f"border-radius: 6px;"
# # #                 f"padding: 5px 8px;"
# # #                 f"text-align: center;"
# # #                 f"font-size: 11px;"
# # #                 f"color: {hex_c};"
# # #                 f"margin-bottom: 10px;"
# # #                 f"'>{emoji} {label}</div>",
# # #                 unsafe_allow_html=True,
# # #             )


# # # # ─────────────────────────────────────────────────────────────────────────────
# # # # Sankey builder  (tested against Fi11_BOM_MResult_v2.xlsx)
# # # # ─────────────────────────────────────────────────────────────────────────────

# # # def _build_sankey(bsn: pd.DataFrame, snr) -> go.Figure:
# # #     """
# # #     Build a Plotly Sankey figure from BOM rows.
# # #     Raises ValueError with a clear message when the data cannot produce a chart.
# # #     """
# # #     nodes:  list = []
# # #     colors: list = []
# # #     customs: list = []
# # #     node_map: dict = {}   # stable key → int index

# # #     def _add(key: str, label: str, color: str, custom: str) -> int:
# # #         key = _s(key, fallback="__unk__")
# # #         if key not in node_map:
# # #             node_map[key] = len(nodes)
# # #             nodes.append(_s(label, fallback=key, maxlen=40))
# # #             colors.append(_s(color, fallback="#94A3B8"))
# # #             customs.append(_s(custom, fallback=_s(label, fallback=key)))
# # #         return node_map[key]

# # #     # Root node
# # #     risk    = _s(snr.get("risk", ""), fallback="UNKNOWN")
# # #     fg_name = _s(snr.get("name", ""), fallback=str(snr.get("material", "FG")))
# # #     root_idx = _add(
# # #         key    = f"FG_{snr.get('material', 'root')}",
# # #         label  = fg_name,
# # #         color  = _RISK_COLOUR.get(risk, "#94A3B8"),
# # #         custom = (
# # #             f"Finished Good: {fg_name} | "
# # #             f"Risk: {risk} | "
# # #             f"Cover: {round(float(snr.get('days_cover', 0)))}d"
# # #         ),
# # #     )

# # #     sources:  list = []
# # #     targets:  list = []
# # #     values:   list = []
# # #     link_lbl: list = []

# # #     for _, row in bsn.iterrows():
# # #         mat_id    = _s(row.get("Material"),             fallback="UNK")
# # #         comp_desc = _s(row.get("Material Description"), fallback=mat_id, maxlen=32)
# # #         proc_type = _s(row.get("Procurement type"),     fallback="").upper()
# # #         sup_disp  = _s(row.get("Supplier Display"),     fallback="—")

# # #         # Quantity – never zero so Sankey does not silently drop the link
# # #         qty_raw = row.get("Effective Order Qty") or row.get("Comp. Qty (CUn)")
# # #         try:
# # #             qty = float(qty_raw)
# # #             if pd.isna(qty) or qty <= 0:
# # #                 qty = 0.01
# # #         except (TypeError, ValueError):
# # #             qty = 0.01

# # #         # Node colour + hover text
# # #         if proc_type == "E":
# # #             comp_color  = "#22C55E"
# # #             comp_custom = f"{comp_desc} | Inhouse (Revvity) | Qty: {qty}"
# # #         elif sup_disp.startswith("⚠") or sup_disp == "—":
# # #             comp_color  = "#F59E0B"
# # #             comp_custom = f"{comp_desc} | No supplier data | Qty: {qty}"
# # #         else:
# # #             transit     = _s(row.get("Transit Days"), fallback="—")
# # #             comp_color  = "#3B82F6"
# # #             comp_custom = f"{comp_desc} | Supplier: {sup_disp} | Qty: {qty} | Transit: {transit}d"

# # #         comp_idx = _add(
# # #             key    = f"COMP_{mat_id}",
# # #             label  = comp_desc,
# # #             color  = comp_color,
# # #             custom = comp_custom,
# # #         )

# # #         # Root → Component link
# # #         sources.append(root_idx)
# # #         targets.append(comp_idx)
# # #         values.append(qty)
# # #         link_lbl.append(f"{comp_desc}")

# # #         # Component → Supplier link (external, named only)
# # #         is_named_ext = (
# # #             proc_type == "F"
# # #             and sup_disp not in ("—", "Revvity Inhouse")
# # #             and not sup_disp.startswith("⚠")
# # #         )
# # #         if is_named_ext:
# # #             loc     = _s(row.get("Supplier Location"),   fallback="—")
# # #             rel     = _s(row.get("Supplier Reliability"), fallback="—")
# # #             sup_idx = _add(
# # #                 key    = f"SUP_{sup_disp}",
# # #                 label  = sup_disp[:28],
# # #                 color  = "#8B5CF6",
# # #                 custom = f"Supplier: {sup_disp} | Location: {loc} | Reliability: {rel}",
# # #             )
# # #             sources.append(comp_idx)
# # #             targets.append(sup_idx)
# # #             values.append(qty)
# # #             link_lbl.append(sup_disp[:28])

# # #     # ── Sanity checks before handing to Plotly ────────────────────────────────
# # #     n = len(nodes)
# # #     if n == 0 or not sources:
# # #         raise ValueError("No nodes or links were generated from BOM data.")
# # #     bad = [
# # #         (i, s, t)
# # #         for i, (s, t) in enumerate(zip(sources, targets))
# # #         if not (0 <= s < n) or not (0 <= t < n)
# # #     ]
# # #     if bad:
# # #         raise ValueError(
# # #             f"{len(bad)} link(s) have out-of-range indices (total nodes={n}). "
# # #             f"First bad: link {bad[0][0]}, src={bad[0][1]}, tgt={bad[0][2]}."
# # #         )

# # #     fig = go.Figure(data=[go.Sankey(
# # #         arrangement="snap",
# # #         node=dict(
# # #             pad=18,
# # #             thickness=22,
# # #             line=dict(color="rgba(255,255,255,0.4)", width=0.8),
# # #             label=nodes,          # plain Python list of str
# # #             color=colors,
# # #             customdata=customs,   # plain Python list of str – no None / nan
# # #             hovertemplate="<b>%{customdata}</b><extra></extra>",
# # #         ),
# # #         link=dict(
# # #             source=sources,
# # #             target=targets,
# # #             value=values,
# # #             label=link_lbl,
# # #             color="rgba(148,163,184,0.28)",
# # #             hovertemplate="<b>%{label}</b><br>Flow: %{value:.2f}<extra></extra>",
# # #         ),
# # #     )])

# # #     fig.update_layout(
# # #         # FIX 1: title=None → {} in JSON → Plotly JS shows "undefined".
# # #         # title_text="" → {"text": ""} → blank heading, no undefined.
# # #         title_text="",
# # #         font=dict(size=11, family="Inter, sans-serif", color="#374151"),
# # #         height=520,
# # #         margin=dict(l=10, r=10, t=10, b=10),
# # #         # White background keeps label text visible in both light & dark themes.
# # #         paper_bgcolor="white",
# # #         plot_bgcolor="white",
# # #     )
# # #     return fig


# # # # ─────────────────────────────────────────────────────────────────────────────
# # # # Main render
# # # # ─────────────────────────────────────────────────────────────────────────────

# # # def render():
# # #     data            = st.session_state.data
# # #     summary         = st.session_state.summary
# # #     MATERIAL_LABELS = st.session_state.material_labels

# # #     st.markdown(
# # #         "<div style='font-size:15px;font-weight:800;margin-bottom:4px;'>"
# # #         "Supply Network</div>"
# # #         "<div style='font-size:12px;color:var(--t3);margin-bottom:14px;'>"
# # #         "BOM structure · Supplier locations · Risk cascade · Consolidation intelligence"
# # #         "</div>",
# # #         unsafe_allow_html=True,
# # #     )

# # #     snn  = st.selectbox(
# # #         "Finished Good", [r["name"] for _, r in summary.iterrows()], key="snm"
# # #     )
# # #     snid = summary[summary.name == snn]["material"].values[0]
# # #     snr  = summary[summary.material == snid].iloc[0]
# # #     bsn  = get_bom_components(data, snid)

# # #     if not len(bsn):
# # #         st.warning("🕸️  No BOM data found for this material.")
# # #         return

# # #     cw         = int(bsn["Supplier Name(Vendor)"].notna().sum())
# # #     cn         = int(bsn["Supplier Display"].str.startswith("⚠", na=False).sum())
# # #     us         = int(bsn["Supplier Name(Vendor)"].dropna().nunique())
# # #     tc         = len(bsn)
# # #     inhouse_n  = int((bsn["Procurement type"] == "E").sum())
# # #     external_n = int((bsn["Procurement type"] == "F").sum())

# # #     # KPI cards
# # #     n1, n2, n3, n4 = st.columns(4)
# # #     for col, val, lbl, vc in [
# # #         (n1, tc,        "Total Components",     "#1E293B"),
# # #         (n2, inhouse_n, "Revvity Inhouse",      "#22C55E"),
# # #         (n3, cn,        "Missing Supplier",     "#F59E0B" if cn > 0 else "#1E293B"),
# # #         (n4, us,        "Unique Ext Suppliers", "#1E293B"),
# # #     ]:
# # #         with col:
# # #             st.markdown(
# # #                 f"<div class='sc'><div style='flex:1;'>"
# # #                 f"<div class='sv' style='color:{vc};'>{val}</div>"
# # #                 f"<div class='sl'>{lbl}</div></div></div>",
# # #                 unsafe_allow_html=True,
# # #             )

# # #     sn_tab, comp_tab, risk_tab = st.tabs(
# # #         ["🕸️  BOM Map", "📋  Components", "⚠️  Risk Analysis"]
# # #     )

# # #     # ── BOM Map ───────────────────────────────────────────────────────────────
# # #     with sn_tab:
# # #         sec("BOM Propagation Map")
# # #         _render_legend()

# # #         try:
# # #             fig = _build_sankey(bsn, snr)
# # #             # FIX 2: displaylogo=False + displayModeBar=False removes the
# # #             # modebar buttons and Plotly logo that inject javascript:void(0)
# # #             # links into the Streamlit DOM.
# # #             st.plotly_chart(fig, use_container_width=True, config=_PLOTLY_CFG)

# # #         except ValueError as exc:
# # #             st.error(f"⚠️  Could not render Sankey diagram: {exc}")
# # #             st.info(
# # #                 "This usually means BOM rows are missing Material IDs or "
# # #                 "all quantities are zero/null. Check your data loader output."
# # #             )
# # #             with st.expander("🔍  Raw BOM data (debug)"):
# # #                 st.dataframe(bsn)

# # #         if st.session_state.get("azure_client"):
# # #             if st.button("◈ Interpret BOM Map", key="interp_bom_sankey"):
# # #                 with st.spinner("ARIA interpreting…"):
# # #                     bom_ctx = {
# # #                         "material":       snr["name"],
# # #                         "total_components": tc,
# # #                         "inhouse":        inhouse_n,
# # #                         "external_named": cw - inhouse_n,
# # #                         "missing_supplier": cn,
# # #                         "unique_suppliers":  us,
# # #                         "risk":           snr["risk"],
# # #                     }
# # #                     interp = interpret_chart(
# # #                         st.session_state.azure_client, AZURE_DEPLOYMENT,
# # #                         "BOM Risk Propagation Map", bom_ctx,
# # #                         "What are the key supply chain risks in this BOM "
# # #                         "and what should procurement prioritise?",
# # #                     )
# # #                 st.markdown(
# # #                     f"<div class='ic' style='margin-top:8px;'>"
# # #                     f"<div class='il'>◈ ARIA</div>"
# # #                     f"<div class='ib'>{interp}</div></div>",
# # #                     unsafe_allow_html=True,
# # #                 )

# # #     # ── Component Detail ──────────────────────────────────────────────────────
# # #     with comp_tab:
# # #         sec("Component Detail")
# # #         bom_rows = []
# # #         for _, b in bsn.iterrows():
# # #             eff_qty = b.get("Effective Order Qty", b["Comp. Qty (CUn)"])
# # #             try:
# # #                 fq_txt = ("1 (Fixed)" if b.get("Fixed Qty Flag", False)
# # #                           else str(round(float(eff_qty), 3)) if pd.notna(eff_qty) else "—")
# # #             except (TypeError, ValueError):
# # #                 fq_txt = "—"
# # #             bom_rows.append({
# # #                 "Material":    _s(b.get("Material")),
# # #                 "Description": _s(b.get("Material Description"), maxlen=36),
# # #                 "Level":       _s(b.get("Level"), maxlen=25),
# # #                 "Qty":         fq_txt,
# # #                 "Unit":        _s(b.get("Component unit")),
# # #                 "Type":        _s(b.get("Procurement Label")),
# # #                 "Supplier":    _s(b.get("Supplier Display")),
# # #                 "Location":    _s(b.get("Supplier Location")),
# # #                 "Transit":     (
# # #                     f"{b.get('Transit Days')}d"
# # #                     if b.get("Transit Days") is not None else "—"
# # #                 ),
# # #                 "Std Price": (
# # #                     f"${b.get('Standard Price', 0):.2f}"
# # #                     if pd.notna(b.get("Standard Price")) else "—"
# # #                 ),
# # #             })

# # #         df_bd = pd.DataFrame(bom_rows)

# # #         sup_renderer = JsCode(
# # #             "class R{"
# # #             "init(p){"
# # #             "const v = (p.value !== undefined && p.value !== null) ? String(p.value) : '';"
# # #             "this.e = document.createElement('span');"
# # #             "if(v.startsWith('⚠')){"
# # #             "this.e.style.cssText='background:#FEF3C7;color:#D97706;"
# # #             "padding:2px 6px;border-radius:4px;font-size:10px;';"
# # #             "this.e.textContent=v;"
# # #             "}else if(v==='Revvity Inhouse'){"
# # #             "this.e.style.cssText='background:#DCFCE7;color:#16a34a;"
# # #             "padding:2px 6px;border-radius:4px;font-size:10px;';"
# # #             "this.e.textContent='🏭 '+v;"
# # #             "}else if(v==='' || v==='—'){"
# # #             "this.e.style.cssText='color:#9CA3AF;font-size:10px;';"
# # #             "this.e.textContent='—';"
# # #             "}else{"
# # #             "this.e.style.cssText='background:#EFF6FF;color:#2563EB;"
# # #             "padding:2px 6px;border-radius:4px;font-size:10px;';"
# # #             "this.e.textContent='🚚 '+v;"
# # #             "}}"
# # #             "getGui(){return this.e;}}"
# # #         )

# # #         gb = GridOptionsBuilder.from_dataframe(df_bd)
# # #         gb.configure_column("Material",    width=82)
# # #         gb.configure_column("Description", width=215)
# # #         gb.configure_column("Level",       width=85)
# # #         gb.configure_column("Qty",         width=75)
# # #         gb.configure_column("Unit",        width=50)
# # #         gb.configure_column("Type",        width=100)
# # #         gb.configure_column("Supplier",    width=170, cellRenderer=sup_renderer)
# # #         gb.configure_column("Location",    width=130)
# # #         gb.configure_column("Transit",     width=58)
# # #         gb.configure_column("Std Price",   width=80)
# # #         gb.configure_grid_options(rowHeight=36, headerHeight=32)
# # #         gb.configure_default_column(resizable=True, sortable=True, filter=False)
# # #         AgGrid(
# # #             df_bd,
# # #             gridOptions=gb.build(),
# # #             height=320,
# # #             allow_unsafe_jscode=True,
# # #             theme="alpine",
# # #             custom_css=_AGGRID_CSS,
# # #         )

# # #     # ── Risk Cascade ──────────────────────────────────────────────────────────
# # #     with risk_tab:
# # #         sec("Risk Cascade Analysis")
# # #         risks = []

# # #         if snr["risk"] in ("CRITICAL", "WARNING"):
# # #             risks.append({
# # #                 "icon": "⛔", "sev": 3, "color": "#EF4444", "bg": "#FEF2F2",
# # #                 "title": f"Finished Good at {snr['risk'].title()} Risk",
# # #                 "detail": (
# # #                     f"{snr['name']} has {round(snr['days_cover'])}d of cover. "
# # #                     f"SIH={round(snr['sih'])} vs SAP SS={round(snr['safety_stock'])}. "
# # #                     f"Production continuity at risk."
# # #                 ),
# # #                 "action": (
# # #                     f"Order {int(snr.get('repl_quantity', 0))} units immediately. "
# # #                     f"Contact procurement today."
# # #                 ),
# # #             })
# # #         if cn > 0:
# # #             risks.append({
# # #                 "icon": "⚠", "sev": 2, "color": "#F59E0B", "bg": "#FFFBEB",
# # #                 "title": f"Missing Supplier Data — {cn} External Components",
# # #                 "detail": (
# # #                     f"{cn} of {external_n} external components have no named supplier. "
# # #                     f"Single-source risk cannot be assessed."
# # #                 ),
# # #                 "action": "Procurement to verify and update BOM with supplier names and lead times.",
# # #             })
# # #         if 0 < us <= 2:
# # #             risks.append({
# # #                 "icon": "⚠", "sev": 2, "color": "#F59E0B", "bg": "#FFFBEB",
# # #                 "title": f"Supplier Concentration — {us} Unique Supplier(s)",
# # #                 "detail": (
# # #                     f"High dependency on {us} supplier(s). "
# # #                     f"Any disruption cascades across multiple components."
# # #                 ),
# # #                 "action": "Evaluate dual-sourcing for critical external components.",
# # #             })
# # #         if external_n > 0:
# # #             locs = list({
# # #                 str(v) for v in
# # #                 bsn[bsn["Procurement type"] == "F"]["Supplier Location"]
# # #                 .dropna().tolist()[:4]
# # #             })
# # #             risks.append({
# # #                 "icon": "🌍", "sev": 1, "color": "#3B82F6", "bg": "#EFF6FF",
# # #                 "title": f"External Procurement: {external_n} Components",
# # #                 "detail": (
# # #                     f"External components depend on supplier availability and transit times. "
# # #                     f"Suppliers in: {', '.join(locs) if locs else 'unknown'}."
# # #                 ),
# # #                 "action": "Review lead times — add stock buffers for long-transit items.",
# # #             })

# # #         if not risks:
# # #             st.success("✓  No critical propagation risks identified.")
# # #         else:
# # #             for r in sorted(risks, key=lambda x: -x["sev"]):
# # #                 st.markdown(
# # #                     f"<div style='"
# # #                     f"background:{r['bg']};"
# # #                     f"border:1px solid {r['color']}40;"
# # #                     f"border-left:4px solid {r['color']};"
# # #                     f"border-radius:8px;"
# # #                     f"padding:12px 14px;"
# # #                     f"margin-bottom:8px;"
# # #                     f"'>"
# # #                     f"<div style='display:flex;align-items:center;gap:8px;margin-bottom:5px;'>"
# # #                     f"<span style='font-size:16px;'>{r['icon']}</span>"
# # #                     f"<span style='font-size:12px;font-weight:600;color:{r['color']};'>"
# # #                     f"{r['title']}</span>"
# # #                     f"</div>"
# # #                     f"<div style='font-size:11px;color:#475569;margin-bottom:5px;'>"
# # #                     f"{r['detail']}</div>"
# # #                     f"<div style='font-size:11px;color:{r['color']};'>"
# # #                     f"→ {r['action']}</div>"
# # #                     f"</div>",
# # #                     unsafe_allow_html=True,
# # #                 )

# # #         # Consolidation
# # #         consol    = get_supplier_consolidation(data, summary)
# # #         relevant  = consol[
# # #             consol.material_list.apply(lambda x: snid in x)
# # #             & (consol.finished_goods_supplied > 1)
# # #             & consol.consolidation_opportunity
# # #         ]
# # #         if len(relevant) > 0:
# # #             sec("Supplier Consolidation Opportunities")
# # #             for _, r2 in relevant.iterrows():
# # #                 others = [
# # #                     MATERIAL_LABELS.get(m, m)[:18]
# # #                     for m in r2["material_list"] if m != snid
# # #                 ]
# # #                 st.markdown(
# # #                     f"<div class='prow'><div style='font-size:14px;'>🏭</div>"
# # #                     f"<div style='flex:1;'>"
# # #                     f"<div style='font-size:12px;font-weight:600;'>{r2['supplier']}</div>"
# # #                     f"<div style='font-size:10px;color:var(--t3);'>"
# # #                     f"{r2['city']} · {r2['email']}</div>"
# # #                     f"<div style='font-size:10px;color:var(--t2);margin-top:2px;'>"
# # #                     f"Also supplies: {', '.join(others[:3])}</div>"
# # #                     f"</div>"
# # #                     f"<div style='font-size:10px;font-weight:600;color:var(--or);'>"
# # #                     f"⚡ Consolidate order</div>"
# # #                     f"</div>",
# # #                     unsafe_allow_html=True,
# # #                 )

# # #         # Ask ARIA
# # #         if st.session_state.get("azure_client"):
# # #             sec("Ask ARIA About This Network")
# # #             st.info("ℹ️  Insights are scoped to the currently selected finished good.")
# # #             uq = st.text_input(
# # #                 "Question",
# # #                 placeholder="e.g. Which supplier provides more than 1 material?",
# # #                 key="snq",
# # #                 label_visibility="collapsed",
# # #             )
# # #             if uq and st.button("Ask ARIA", key="sna"):
# # #                 bom_lines = []
# # #                 for _, row in bsn.iterrows():
# # #                     mat_desc  = _s(row.get("Material Description"),
# # #                                    fallback=str(row.get("Material")), maxlen=40)
# # #                     qty       = row.get("Effective Order Qty") or row.get("Comp. Qty (CUn)")
# # #                     fixed     = "X (order exactly 1)" if row.get("Fixed Qty Flag") else ""
# # #                     sup       = _s(row.get("Supplier Display"))
# # #                     loc       = _s(row.get("Supplier Location"))
# # #                     transit   = _s(row.get("Transit Days"))
# # #                     rel       = _s(row.get("Supplier Reliability"))
# # #                     sp        = row.get("Standard Price")
# # #                     std_price = f"${sp:.2f}" if pd.notna(sp) else "—"
# # #                     bom_lines.append(
# # #                         f"- {mat_desc} | Qty: {qty} {fixed} | Price: {std_price} "
# # #                         f"| Supplier: {sup} | Location: {loc} "
# # #                         f"| Transit: {transit}d | Reliability: {rel}"
# # #                     )

# # #                 ctx = (
# # #                     f"Material: {snr['name']} (ID: {snid})\n"
# # #                     f"Risk: {snr['risk']}\n"
# # #                     f"Total: {tc} | Inhouse: {inhouse_n} | External: {external_n}\n"
# # #                     f"Missing supplier: {cn} | Unique suppliers: {us}\n"
# # #                     f"BOM details:\n" + "\n".join(bom_lines)
# # #                 )
# # #                 with st.spinner("Thinking…"):
# # #                     ans = chat_with_data(
# # #                         st.session_state.azure_client, AZURE_DEPLOYMENT, uq, ctx
# # #                     )
# # #                 st.markdown(
# # #                     f"<div class='ic' style='margin-top:8px;'>"
# # #                     f"<div class='il'>◈ ARIA</div>"
# # #                     f"<div class='ib'>{ans}</div></div>",
# # #                     unsafe_allow_html=True,
# # #                 )

# # #     st.markdown(
# # #         '<div class="pfooter">🕸️  Powered by <strong>MResult</strong></div>',
# # #         unsafe_allow_html=True,
# # #     )


# # # # """
# # # # tabs/supply_network.py
# # # # Supply Network tab: BOM propagation map (Sankey diagram), component detail table,
# # # # risk cascade analysis, and supplier consolidation opportunities.
# # # # """

# # # # import streamlit as st
# # # # import pandas as pd
# # # # import plotly.graph_objects as go

# # # # from st_aggrid import AgGrid, GridOptionsBuilder, JsCode

# # # # from utils.helpers import sec, note, sbadge, ORANGE, AZURE_DEPLOYMENT
# # # # from data_loader import get_bom_components, get_supplier_consolidation
# # # # from agent import interpret_chart, chat_with_data

# # # # _AGGRID_CSS = {
# # # #     ".ag-root-wrapper": {"border": "1px solid #E2E8F0!important", "border-radius": "12px!important"},
# # # #     ".ag-header":       {"background": "#F8FAFE!important"},
# # # #     ".ag-row-even":     {"background": "#FFFFFF!important"},
# # # #     ".ag-row-odd":      {"background": "#F8FAFE!important"},
# # # # }


# # # # def render():
# # # #     data            = st.session_state.data
# # # #     summary         = st.session_state.summary
# # # #     MATERIAL_LABELS = st.session_state.material_labels

# # # #     st.markdown(
# # # #         "<div style='font-size:15px;font-weight:800;margin-bottom:4px;'>Supply Network</div>"
# # # #         "<div style='font-size:12px;color:var(--t3);margin-bottom:14px;'>"
# # # #         "BOM structure · Supplier locations · Risk cascade · Consolidation intelligence</div>",
# # # #         unsafe_allow_html=True,
# # # #     )

# # # #     snn  = st.selectbox("Finished Good", [r["name"] for _, r in summary.iterrows()], key="snm")
# # # #     snid = summary[summary.name == snn]["material"].values[0]
# # # #     snr  = summary[summary.material == snid].iloc[0]
# # # #     bsn  = get_bom_components(data, snid)

# # # #     if not len(bsn):
# # # #         st.markdown(
# # # #             "<div class='flag-box'><div style='font-size:22px;margin-bottom:8px;'>🕸️</div>"
# # # #             "<div style='font-size:14px;font-weight:800;color:var(--t2);'>No BOM data for this material</div></div>",
# # # #             unsafe_allow_html=True,
# # # #         )
# # # #         return

# # # #     cw        = int(bsn["Supplier Name(Vendor)"].notna().sum())
# # # #     cn        = len(bsn[bsn["Supplier Display"].str.startswith("⚠", na=False)])
# # # #     us        = int(bsn["Supplier Name(Vendor)"].dropna().nunique())
# # # #     tc        = len(bsn)
# # # #     inhouse_n = int((bsn["Procurement type"] == "E").sum())
# # # #     external_n = int((bsn["Procurement type"] == "F").sum())

# # # #     n1, n2, n3, n4 = st.columns(4)
# # # #     for col, val, lbl, vc in [
# # # #         (n1, tc,        "Total Components",  "#1E293B"),
# # # #         (n2, inhouse_n, "Revvity Inhouse",   "#22C55E"),
# # # #         (n3, cn,        "Missing Supplier",  "#F59E0B" if cn > 0 else "#1E293B"),
# # # #         (n4, us,        "Unique Ext Suppliers", "#1E293B"),
# # # #     ]:
# # # #         with col:
# # # #             st.markdown(
# # # #                 f"<div class='sc'><div style='flex:1;'>"
# # # #                 f"<div class='sv' style='color:{vc};'>{val}</div>"
# # # #                 f"<div class='sl'>{lbl}</div></div></div>",
# # # #                 unsafe_allow_html=True,
# # # #             )

# # # #     sn_tab, comp_tab, risk_tab = st.tabs(["🕸️  BOM Map", "📋  Components", "⚠️  Risk Analysis"])

# # # #     # ── BOM Map – Sankey diagram with error handling ──────────────────────────
# # # #     with sn_tab:
# # # #         sec("BOM Propagation Map")
# # # #         st.markdown("""
# # # #         <div class='note-box'>
# # # #         <strong>Colour legend:</strong>
# # # #         <ul style='margin:5px 0 0 20px; padding-left:0;'>
# # # #         <li>🔵 <strong>Blue</strong> = External component with named supplier</li>
# # # #         <li>🟢 <strong>Green</strong> = Inhouse component (Revvity)</li>
# # # #         <li>🟡 <strong>Amber</strong> = External component with <strong>missing supplier data</strong></li>
# # # #         <li>🟣 <strong>Purple</strong> = Supplier node</li>
# # # #         <li>Root node colour matches finished good risk (🔴 Critical / 🟠 Warning / 🟢 Healthy)</li>
# # # #         </ul>
# # # #         Hover over nodes for details. Use the interactive controls to zoom/pan.
# # # #         </div>
# # # #         """, unsafe_allow_html=True)

# # # #         try:
# # # #             # Build node list and links
# # # #             nodes = []
# # # #             node_colors = []
# # # #             node_map = {}

# # # #             # Root node
# # # #             root_name = snr["name"]
# # # #             risk_color_map = {"CRITICAL": "#EF4444", "WARNING": "#F59E0B", "HEALTHY": "#22C55E"}
# # # #             root_color = risk_color_map.get(snr["risk"], "#94A3B8")
# # # #             nodes.append(root_name)
# # # #             node_colors.append(root_color)
# # # #             node_map[root_name] = 0

# # # #             sources = []
# # # #             targets = []
# # # #             values = []

# # # #             # Process each BOM row
# # # #             for _, row in bsn.iterrows():
# # # #                 # Component label (shortened)
# # # #                 comp_desc = str(row["Material Description"])[:30] if pd.notna(row["Material Description"]) else str(row["Material"])
# # # #                 comp_label = comp_desc
# # # #                 sup_display = row.get("Supplier Display", "—")
# # # #                 proc_type = str(row.get("Procurement type", "")).strip()
# # # #                 qty_raw = row.get("Effective Order Qty", row["Comp. Qty (CUn)"])
# # # #                 try:
# # # #                     qty = float(qty_raw) if pd.notna(qty_raw) else 1.0
# # # #                 except:
# # # #                     qty = 1.0

# # # #                 # Add component node
# # # #                 if comp_label not in node_map:
# # # #                     if proc_type == "E":
# # # #                         comp_color = "#22C55E"
# # # #                     elif sup_display.startswith("⚠"):
# # # #                         comp_color = "#F59E0B"
# # # #                     else:
# # # #                         comp_color = "#3B82F6"
# # # #                     nodes.append(comp_label)
# # # #                     node_colors.append(comp_color)
# # # #                     node_map[comp_label] = len(nodes) - 1

# # # #                 # Root -> component
# # # #                 sources.append(node_map[root_name])
# # # #                 targets.append(node_map[comp_label])
# # # #                 values.append(qty)

# # # #                 # Supplier node (if external and named)
# # # #                 if sup_display not in ["Revvity Inhouse", "—"] and not sup_display.startswith("⚠"):
# # # #                     sup_label = sup_display[:25]
# # # #                     if sup_label not in node_map:
# # # #                         nodes.append(sup_label)
# # # #                         node_colors.append("#8B5CF6")
# # # #                         node_map[sup_label] = len(nodes) - 1
# # # #                     sources.append(node_map[comp_label])
# # # #                     targets.append(node_map[sup_label])
# # # #                     values.append(1.0)

# # # #             # Only create Sankey if there are links
# # # #             if len(sources) == 0:
# # # #                 st.warning("No valid links found in the BOM. Cannot render Sankey diagram.")
# # # #             else:
# # # #                 fig = go.Figure(data=[go.Sankey(
# # # #                     arrangement="snap",
# # # #                     node=dict(
# # # #                         pad=30,
# # # #                         thickness=15,
# # # #                         line=dict(color="white", width=0.5),
# # # #                         label=nodes,
# # # #                         color=node_colors,
# # # #                         hovertemplate="<b>%{label}</b><extra></extra>"
# # # #                     ),
# # # #                     link=dict(
# # # #                         source=sources,
# # # #                         target=targets,
# # # #                         value=values,
# # # #                         color="rgba(160,160,160,0.4)"
# # # #                     )
# # # #                 )])
# # # #                 fig.update_layout(
# # # #                     title=None,
# # # #                     font=dict(size=11, family="Inter", color="#1E293B"),
# # # #                     height=550,
# # # #                     margin=dict(l=20, r=20, t=20, b=20),
# # # #                     paper_bgcolor="white",
# # # #                     plot_bgcolor="white"
# # # #                 )
# # # #                 st.plotly_chart(fig, use_container_width=True)

# # # #         except Exception as e:
# # # #             st.error(f"Could not render Sankey diagram: {str(e)}")
# # # #             st.info("Try selecting a different finished good or check the BOM data.")

# # # #         if st.session_state.azure_client:
# # # #             if st.button("◈ Interpret BOM Map", key="interp_bom_sankey"):
# # # #                 with st.spinner("ARIA interpreting…"):
# # # #                     bom_ctx = {
# # # #                         "material": snr["name"], "total_components": tc,
# # # #                         "inhouse": inhouse_n, "external_named": cw - inhouse_n,
# # # #                         "missing_supplier": cn, "unique_suppliers": us, "risk": snr["risk"],
# # # #                     }
# # # #                     interp = interpret_chart(
# # # #                         st.session_state.azure_client, AZURE_DEPLOYMENT,
# # # #                         "BOM Risk Propagation Map", bom_ctx,
# # # #                         "What are the key supply chain risks in this BOM and what should procurement prioritise?",
# # # #                     )
# # # #                 st.markdown(
# # # #                     f"<div class='ic' style='margin-top:8px;'><div class='il'>◈ ARIA</div>"
# # # #                     f"<div class='ib'>{interp}</div></div>",
# # # #                     unsafe_allow_html=True,
# # # #                 )

# # # #     # ── Component Detail ──────────────────────────────────────────────────────
# # # #     with comp_tab:
# # # #         sec("Component Detail")
# # # #         bom_display2 = []
# # # #         for _, b in bsn.iterrows():
# # # #             eff_qty = b.get("Effective Order Qty", b["Comp. Qty (CUn)"])
# # # #             fq_txt  = ("1 (Fixed)" if b.get("Fixed Qty Flag", False)
# # # #                        else str(round(float(eff_qty), 3)) if pd.notna(eff_qty) else "—")
# # # #             bom_display2.append({
# # # #                 "Material":    str(b["Material"]),
# # # #                 "Description": str(b["Material Description"])[:36] if pd.notna(b["Material Description"]) else "—",
# # # #                 "Level":       str(b["Level"])[:25] if pd.notna(b["Level"]) else "—",
# # # #                 "Qty":         fq_txt,
# # # #                 "Unit":        str(b["Component unit"]) if pd.notna(b["Component unit"]) else "—",
# # # #                 "Type":        b.get("Procurement Label", "—"),
# # # #                 "Supplier":    b.get("Supplier Display", "—"),
# # # #                 "Location":    b.get("Supplier Location", "—"),
# # # #                 "Transit":     f"{b.get('Transit Days', '—')}d" if b.get("Transit Days") is not None else "—",
# # # #                 "Std Price":   f"${b.get('Standard Price', 0):.2f}" if pd.notna(b.get('Standard Price')) else "—",
# # # #             })
# # # #         df_bd2  = pd.DataFrame(bom_display2)
# # # #         sup_r3  = JsCode("""class R{init(p){const v=p.value||'';this.e=document.createElement('span');if(v.startsWith('⚠')){this.e.style.cssText='background:#FEF3C7;color:#F59E0B;padding:2px 6px;border-radius:4px;font-size:10px;font-weight:600;';this.e.innerText=v;}else if(v==='Revvity Inhouse'){this.e.style.cssText='background:#DCFCE7;color:#16a34a;padding:2px 6px;border-radius:4px;font-size:10px;font-weight:600;';this.e.innerText='🏭 '+v;}else{this.e.style.cssText='background:#EFF6FF;color:#2563EB;padding:2px 6px;border-radius:4px;font-size:10px;';this.e.innerText='🚚 '+v;};}getGui(){return this.e;}}""")
# # # #         gb4     = GridOptionsBuilder.from_dataframe(df_bd2)
# # # #         gb4.configure_column("Material",    width=82)
# # # #         gb4.configure_column("Description", width=215)
# # # #         gb4.configure_column("Level",       width=85)
# # # #         gb4.configure_column("Qty",         width=75)
# # # #         gb4.configure_column("Unit",        width=50)
# # # #         gb4.configure_column("Type",        width=100)
# # # #         gb4.configure_column("Supplier",    width=170, cellRenderer=sup_r3)
# # # #         gb4.configure_column("Location",    width=130)
# # # #         gb4.configure_column("Transit",     width=58)
# # # #         gb4.configure_column("Std Price",   width=80)
# # # #         gb4.configure_grid_options(rowHeight=36, headerHeight=32)
# # # #         gb4.configure_default_column(resizable=True, sortable=True, filter=False)
# # # #         AgGrid(df_bd2, gridOptions=gb4.build(), height=320,
# # # #                allow_unsafe_jscode=True, theme="alpine", custom_css=_AGGRID_CSS)

# # # #     # ── Risk Cascade (unchanged) ─────────────────────────────────────────────
# # # #     with risk_tab:
# # # #         sec("Risk Cascade Analysis")
# # # #         risks = []
# # # #         if snr["risk"] in ["CRITICAL", "WARNING"]:
# # # #             risks.append({
# # # #                 "icon": "⛔", "sev": 3, "color": "#EF4444", "bg": "#FEF2F2",
# # # #                 "title": f"Finished Good at {snr['risk'].title()} Risk",
# # # #                 "detail": (f"{snr['name']} has {round(snr['days_cover'])}d of cover. "
# # # #                            f"SIH={round(snr['sih'])} vs SAP SS={round(snr['safety_stock'])}. "
# # # #                            f"Production continuity at risk."),
# # # #                 "action": f"Order {int(snr.get('repl_quantity', 0))} units immediately. Contact procurement today.",
# # # #             })
# # # #         if cn > 0:
# # # #             risks.append({
# # # #                 "icon": "⚠", "sev": 2, "color": "#F59E0B", "bg": "#FFFBEB",
# # # #                 "title": f"Missing Supplier Data — {cn} External Components",
# # # #                 "detail": (f"{cn} of {external_n} external components have no named supplier. "
# # # #                            f"Single-source risk cannot be assessed for these."),
# # # #                 "action": "Procurement to verify and update BOM with supplier names and lead times.",
# # # #             })
# # # #         if 0 < us <= 2:
# # # #             risks.append({
# # # #                 "icon": "⚠", "sev": 2, "color": "#F59E0B", "bg": "#FFFBEB",
# # # #                 "title": f"Supplier Concentration — {us} Unique Supplier(s)",
# # # #                 "detail": f"High dependency on {us} supplier(s). Any disruption cascades to multiple components simultaneously.",
# # # #                 "action": "Evaluate dual-sourcing for critical external components.",
# # # #             })
# # # #         ext_comps = bsn[bsn["Procurement type"] == "F"]
# # # #         if len(ext_comps) > 0:
# # # #             locs = list(set([str(r) for r in bsn[bsn["Procurement type"] == "F"]["Supplier Location"].dropna().tolist()[:4]]))
# # # #             risks.append({
# # # #                 "icon": "🌍", "sev": 1, "color": "#3B82F6", "bg": "#EFF6FF",
# # # #                 "title": f"External Procurement: {len(ext_comps)} Components",
# # # #                 "detail": (f"External components depend on supplier availability and transit times. "
# # # #                            f"Suppliers located in: {', '.join(locs)}."),
# # # #                 "action": "Review external component lead times — stock buffers for long-transit items.",
# # # #             })

# # # #         if not risks:
# # # #             st.markdown(
# # # #                 "<div style='padding:10px 13px;background:var(--gbg);border:1px solid rgba(34,197,94,0.2);"
# # # #                 "border-radius:var(--r);font-size:12px;color:#14532d;'>"
# # # #                 "✓ No critical propagation risks identified.</div>",
# # # #                 unsafe_allow_html=True,
# # # #             )
# # # #         else:
# # # #             for r in sorted(risks, key=lambda x: -x["sev"]):
# # # #                 st.markdown(
# # # #                     f"<div style='background:{r['bg']};border:1px solid {r['color']}40;"
# # # #                     f"border-left:4px solid {r['color']};border-radius:var(--r);"
# # # #                     f"padding:12px 14px;margin-bottom:8px;'>"
# # # #                     f"<div style='display:flex;align-items:center;gap:8px;margin-bottom:5px;'>"
# # # #                     f"<span style='font-size:16px;'>{r['icon']}</span>"
# # # #                     f"<div style='font-size:12px;font-weight:800;color:{r['color']};'>{r['title']}</div>"
# # # #                     f"</div>"
# # # #                     f"<div style='font-size:11px;color:var(--t2);margin-bottom:5px;'>{r['detail']}</div>"
# # # #                     f"<div style='font-size:11px;color:{r['color']};font-weight:600;'>→ {r['action']}</div>"
# # # #                     f"</div>",
# # # #                     unsafe_allow_html=True,
# # # #                 )

# # # #         # Consolidation opportunities
# # # #         consol2   = get_supplier_consolidation(data, summary)
# # # #         relevant2 = consol2[
# # # #             consol2.material_list.apply(lambda x: snid in x)
# # # #             & (consol2.finished_goods_supplied > 1)
# # # #             & consol2.consolidation_opportunity
# # # #         ]
# # # #         if len(relevant2) > 0:
# # # #             sec("Supplier Consolidation Opportunities")
# # # #             for _, r2 in relevant2.iterrows():
# # # #                 others = [MATERIAL_LABELS.get(m, m)[:18] for m in r2["material_list"] if m != snid]
# # # #                 st.markdown(
# # # #                     f"<div class='prow'><div style='font-size:14px;'>🏭</div>"
# # # #                     f"<div style='flex:1;'>"
# # # #                     f"<div style='font-size:12px;font-weight:800;'>{r2['supplier']}</div>"
# # # #                     f"<div style='font-size:10px;color:var(--t3);'>{r2['city']} · {r2['email']}</div>"
# # # #                     f"<div style='font-size:10px;color:var(--t2);margin-top:2px;'>Also supplies: {', '.join(others[:3])}</div>"
# # # #                     f"</div>"
# # # #                     f"<div style='font-size:10px;font-weight:700;color:var(--or);'>⚡ Consolidate order</div>"
# # # #                     f"</div>",
# # # #                     unsafe_allow_html=True,
# # # #                 )

# # # #         # ── Ask ARIA with rich BOM context ────────────────────────────────────
# # # #         if st.session_state.azure_client:
# # # #             sec("Ask ARIA About This Network")
# # # #             st.info("ℹ️ This assistant provides supplier‑related insights only for the currently selected finished good.")
# # # #             uq = st.text_input(
# # # #                 "Question",
# # # #                 placeholder="e.g. Which supplier provides more than 1 material for DELFIA Wash Concentrate?",
# # # #                 key="snq", label_visibility="collapsed",
# # # #             )
# # # #             if uq and st.button("Ask ARIA", key="sna"):
# # # #                 bom_lines = []
# # # #                 for _, row in bsn.iterrows():
# # # #                     mat_desc = str(row["Material Description"])[:40] if pd.notna(row["Material Description"]) else str(row["Material"])
# # # #                     qty = row["Effective Order Qty"] if "Effective Order Qty" in row else row["Comp. Qty (CUn)"]
# # # #                     fixed = "X (order exactly 1)" if row.get("Fixed Qty Flag") else ""
# # # #                     sup = row.get("Supplier Display", "—")
# # # #                     loc = row.get("Supplier Location", "—")
# # # #                     transit = row.get("Transit Days", "—")
# # # #                     reliability = row.get("Supplier Reliability", "—")
# # # #                     std_price = row.get("Standard Price", "—")
# # # #                     if pd.notna(std_price):
# # # #                         std_price = f"${std_price:.2f}"
# # # #                     bom_lines.append(f"- Component: {mat_desc} | Qty: {qty} {fixed} | Std Price: {std_price} | Supplier: {sup} | Location: {loc} | Transit: {transit}d | Reliability: {reliability}")
# # # #                 bom_table = "\n".join(bom_lines)

# # # #                 ctx3 = (
# # # #                     f"Material: {snr['name']} (ID: {snid})\n"
# # # #                     f"Risk: {snr['risk']}\n"
# # # #                     f"Total components: {tc}\n"
# # # #                     f"Inhouse components: {inhouse_n}\n"
# # # #                     f"External components: {external_n}\n"
# # # #                     f"Missing supplier data: {cn} components\n"
# # # #                     f"Unique external suppliers: {us}\n"
# # # #                     f"BOM details:\n{bom_table}"
# # # #                 )
# # # #                 with st.spinner("Thinking…"):
# # # #                     ans = chat_with_data(st.session_state.azure_client, AZURE_DEPLOYMENT, uq, ctx3)
# # # #                 st.markdown(
# # # #                     f"<div class='ic' style='margin-top:8px;'><div class='il'>◈ ARIA</div>"
# # # #                     f"<div class='ib'>{ans}</div></div>",
# # # #                     unsafe_allow_html=True,
# # # #                 )

# # # #     st.markdown('<div class="pfooter">🕸️ Powered by <strong>MResult</strong></div>', unsafe_allow_html=True)


# # # # # """
# # # # # tabs/supply_network.py
# # # # # Supply Network tab: BOM propagation map (Sankey diagram), component detail table,
# # # # # risk cascade analysis, and supplier consolidation opportunities.

# # # # # FIXES:
# # # # #   1. "undefined" in Sankey -> all labels/customdata sanitised via _safe();
# # # # #      empty string is the #1 cause of Plotly rendering "undefined" on hover.
# # # # #   2. Invisible text -> removed dependency on undefined CSS class 'note-box';
# # # # #      legend rebuilt with native Streamlit columns + inline styles only.
# # # # #   3. Out-of-bound indices -> assertion guard before figure construction.
# # # # #   4. Zero/NaN qty -> clamped to 0.01 so Sankey never silently drops a link.
# # # # #   5. Supplier link value was hardcoded 1.0 -> now uses actual qty.
# # # # #   6. Font colour -> removed hardcoded dark colour invisible in dark themes;
# # # # #      paper_bgcolor is transparent so it respects Streamlit's theme.
# # # # # """

# # # # # import streamlit as st
# # # # # import pandas as pd
# # # # # import plotly.graph_objects as go

# # # # # from st_aggrid import AgGrid, GridOptionsBuilder, JsCode

# # # # # from utils.helpers import sec, note, sbadge, ORANGE, AZURE_DEPLOYMENT
# # # # # from data_loader import get_bom_components, get_supplier_consolidation
# # # # # from agent import interpret_chart, chat_with_data

# # # # # _AGGRID_CSS = {
# # # # #     ".ag-root-wrapper": {"border": "1px solid #E2E8F0!important", "border-radius": "12px!important"},
# # # # #     ".ag-header":       {"background": "#F8FAFE!important"},
# # # # #     ".ag-row-even":     {"background": "#FFFFFF!important"},
# # # # #     ".ag-row-odd":      {"background": "#F8FAFE!important"},
# # # # # }

# # # # # _RISK_COLOUR = {"CRITICAL": "#EF4444", "WARNING": "#F59E0B", "HEALTHY": "#22C55E"}


# # # # # # ---------------------------------------------------------------------------
# # # # # # Helpers
# # # # # # ---------------------------------------------------------------------------

# # # # # def _safe(val, fallback="—", maxlen=0):
# # # # #     """
# # # # #     Return a guaranteed non-empty string.
# # # # #     Plotly Sankey renders 'undefined' whenever a label or customdata entry
# # # # #     is an empty string or None — this function prevents that entirely.
# # # # #     """
# # # # #     if val is None or (isinstance(val, float) and pd.isna(val)):
# # # # #         return fallback
# # # # #     s = str(val).strip()
# # # # #     if not s:
# # # # #         return fallback
# # # # #     return s[:maxlen] if maxlen else s


# # # # # def _safe_qty(val):
# # # # #     """Return a positive float; Sankey silently drops links with value <= 0."""
# # # # #     try:
# # # # #         q = float(val)
# # # # #         return q if q > 0 else 0.01
# # # # #     except Exception:
# # # # #         return 0.01


# # # # # # ---------------------------------------------------------------------------
# # # # # # Legend  (zero CSS-class dependency — inline styles only)
# # # # # # ---------------------------------------------------------------------------

# # # # # def _render_legend():
# # # # #     st.markdown(
# # # # #         "<div style='"
# # # # #         "background:#F8FAFE;"
# # # # #         "border:1px solid #CBD5E1;"
# # # # #         "border-left:4px solid #3B82F6;"
# # # # #         "border-radius:10px;"
# # # # #         "padding:10px 16px 6px 16px;"
# # # # #         "margin-bottom:12px;"
# # # # #         "'>"
# # # # #         "<span style='font-size:12px;font-weight:700;color:#1E293B;'>"
# # # # #         "Colour legend&nbsp;&nbsp;"
# # # # #         "</span>"
# # # # #         "<span style='font-size:11px;color:#64748B;'>"
# # # # #         "Root node = finished-good risk &nbsp;|&nbsp; "
# # # # #         "🔴 Critical &nbsp; 🟠 Warning &nbsp; 🟢 Healthy"
# # # # #         "</span>"
# # # # #         "</div>",
# # # # #         unsafe_allow_html=True,
# # # # #     )
# # # # #     badges = [
# # # # #         ("#3B82F6", "🔵", "External – named supplier"),
# # # # #         ("#22C55E", "🟢", "Inhouse (Revvity)"),
# # # # #         ("#F59E0B", "🟡", "External – missing supplier"),
# # # # #         ("#8B5CF6", "🟣", "Supplier node"),
# # # # #     ]
# # # # #     cols = st.columns(4)
# # # # #     for col, (hex_c, emoji, label) in zip(cols, badges):
# # # # #         with col:
# # # # #             st.markdown(
# # # # #                 f"<div style='"
# # # # #                 f"background:{hex_c}1A;"
# # # # #                 f"border:1px solid {hex_c}88;"
# # # # #                 f"border-radius:8px;"
# # # # #                 f"padding:7px 8px;"
# # # # #                 f"text-align:center;"
# # # # #                 f"font-size:11px;"
# # # # #                 f"font-weight:600;"
# # # # #                 f"color:{hex_c};"
# # # # #                 f"margin-bottom:10px;"
# # # # #                 f"'>{emoji}&nbsp;{label}</div>",
# # # # #                 unsafe_allow_html=True,
# # # # #             )


# # # # # # ---------------------------------------------------------------------------
# # # # # # Sankey builder
# # # # # # ---------------------------------------------------------------------------

# # # # # def _build_sankey(bsn, snr):
# # # # #     """
# # # # #     Build and return a Plotly Sankey figure from BOM rows.
# # # # #     Raises ValueError with a descriptive message when data is unusable.
# # # # #     """
# # # # #     nodes = []
# # # # #     node_colors = []
# # # # #     node_custom = []          # drives %{customdata} in hovertemplate
# # # # #     node_map = {}             # stable_key -> int index

# # # # #     def _add(key, label, color, custom):
# # # # #         key = _safe(key, fallback="__unk__")
# # # # #         if key not in node_map:
# # # # #             node_map[key] = len(nodes)
# # # # #             nodes.append(_safe(label, fallback=key, maxlen=40))
# # # # #             node_colors.append(color or "#94A3B8")
# # # # #             node_custom.append(_safe(custom, fallback=_safe(label, fallback=key)))
# # # # #         return node_map[key]

# # # # #     root_color = _RISK_COLOUR.get(_safe(snr["risk"]), "#94A3B8")
# # # # #     root_idx = _add(
# # # # #         key    = f"FG_{snr['material']}",
# # # # #         label  = _safe(snr["name"], maxlen=40),
# # # # #         color  = root_color,
# # # # #         custom = (
# # # # #             f"Finished Good: {_safe(snr['name'])} | "
# # # # #             f"Risk: {_safe(snr['risk'])} | "
# # # # #             f"Cover: {round(float(snr['days_cover']))}d"
# # # # #         ),
# # # # #     )

# # # # #     sources   = []
# # # # #     targets   = []
# # # # #     values    = []
# # # # #     link_lbl  = []

# # # # #     for _, row in bsn.iterrows():
# # # # #         mat_id     = _safe(row.get("Material"), fallback="UNK")
# # # # #         comp_desc  = _safe(row.get("Material Description"), fallback=mat_id, maxlen=32)
# # # # #         proc_type  = _safe(row.get("Procurement type"), fallback="").upper()
# # # # #         sup_disp   = _safe(row.get("Supplier Display"), fallback="—")

# # # # #         qty_raw = row.get("Effective Order Qty") or row.get("Comp. Qty (CUn)")
# # # # #         qty     = _safe_qty(qty_raw)

# # # # #         if proc_type == "E":
# # # # #             comp_color  = "#22C55E"
# # # # #             comp_custom = f"{comp_desc} | Inhouse (Revvity) | Qty: {qty}"
# # # # #         elif sup_disp.startswith("⚠") or sup_disp == "—":
# # # # #             comp_color  = "#F59E0B"
# # # # #             comp_custom = f"{comp_desc} | No supplier data | Qty: {qty}"
# # # # #         else:
# # # # #             transit     = _safe(row.get("Transit Days"), fallback="—")
# # # # #             comp_color  = "#3B82F6"
# # # # #             comp_custom = (
# # # # #                 f"{comp_desc} | Supplier: {sup_disp} | "
# # # # #                 f"Qty: {qty} | Transit: {transit}d"
# # # # #             )

# # # # #         comp_idx = _add(
# # # # #             key    = f"COMP_{mat_id}",
# # # # #             label  = comp_desc,
# # # # #             color  = comp_color,
# # # # #             custom = comp_custom,
# # # # #         )

# # # # #         sources.append(root_idx)
# # # # #         targets.append(comp_idx)
# # # # #         values.append(qty)
# # # # #         link_lbl.append(f"{comp_desc} | qty: {qty}")

# # # # #         is_named_ext = (
# # # # #             proc_type == "F"
# # # # #             and sup_disp not in ("—", "Revvity Inhouse")
# # # # #             and not sup_disp.startswith("⚠")
# # # # #         )
# # # # #         if is_named_ext:
# # # # #             loc     = _safe(row.get("Supplier Location"), fallback="—")
# # # # #             rel     = _safe(row.get("Supplier Reliability"), fallback="—")
# # # # #             sup_idx = _add(
# # # # #                 key    = f"SUP_{sup_disp}",
# # # # #                 label  = _safe(sup_disp, maxlen=28),
# # # # #                 color  = "#8B5CF6",
# # # # #                 custom = (
# # # # #                     f"Supplier: {sup_disp} | "
# # # # #                     f"Location: {loc} | Reliability: {rel}"
# # # # #                 ),
# # # # #             )
# # # # #             sources.append(comp_idx)
# # # # #             targets.append(sup_idx)
# # # # #             values.append(qty)
# # # # #             link_lbl.append(f"{comp_desc} -> {_safe(sup_disp, maxlen=28)}")

# # # # #     # Safety check
# # # # #     n = len(nodes)
# # # # #     if n == 0 or not sources:
# # # # #         raise ValueError("No nodes or links were generated from BOM data.")

# # # # #     bad = [
# # # # #         (i, s, t)
# # # # #         for i, (s, t) in enumerate(zip(sources, targets))
# # # # #         if not (0 <= s < n) or not (0 <= t < n)
# # # # #     ]
# # # # #     if bad:
# # # # #         raise ValueError(
# # # # #             f"{len(bad)} link(s) reference out-of-range indices "
# # # # #             f"(total nodes={n}). First bad: link {bad[0][0]}, "
# # # # #             f"src={bad[0][1]}, tgt={bad[0][2]}."
# # # # #         )

# # # # #     fig = go.Figure(data=[go.Sankey(
# # # # #         arrangement="snap",
# # # # #         node=dict(
# # # # #             pad=18,
# # # # #             thickness=22,
# # # # #             line=dict(color="rgba(255,255,255,0.5)", width=0.8),
# # # # #             label=nodes,
# # # # #             color=node_colors,
# # # # #             customdata=node_custom,
# # # # #             hovertemplate="<b>%{customdata}</b><extra></extra>",
# # # # #         ),
# # # # #         link=dict(
# # # # #             source=sources,
# # # # #             target=targets,
# # # # #             value=values,
# # # # #             label=link_lbl,
# # # # #             color="rgba(148,163,184,0.30)",
# # # # #             hovertemplate=(
# # # # #                 "<b>%{label}</b><br>"
# # # # #                 "Flow: %{value:.2f}<extra></extra>"
# # # # #             ),
# # # # #         ),
# # # # #     )])

# # # # #     fig.update_layout(
# # # # #         title=None,
# # # # #         # No hardcoded font colour: Plotly auto-picks contrast vs node colour.
# # # # #         font=dict(size=11, family="Inter, sans-serif"),
# # # # #         height=520,
# # # # #         margin=dict(l=10, r=10, t=10, b=10),
# # # # #         # Transparent background respects Streamlit light/dark theme.
# # # # #         paper_bgcolor="rgba(0,0,0,0)",
# # # # #         plot_bgcolor="rgba(0,0,0,0)",
# # # # #     )
# # # # #     return fig


# # # # # # ---------------------------------------------------------------------------
# # # # # # Main render
# # # # # # ---------------------------------------------------------------------------

# # # # # def render():
# # # # #     data            = st.session_state.data
# # # # #     summary         = st.session_state.summary
# # # # #     MATERIAL_LABELS = st.session_state.material_labels

# # # # #     st.markdown(
# # # # #         "<div style='font-size:15px;font-weight:800;margin-bottom:4px;'>Supply Network</div>"
# # # # #         "<div style='font-size:12px;color:var(--t3);margin-bottom:14px;'>"
# # # # #         "BOM structure · Supplier locations · Risk cascade · Consolidation intelligence</div>",
# # # # #         unsafe_allow_html=True,
# # # # #     )

# # # # #     snn  = st.selectbox("Finished Good", [r["name"] for _, r in summary.iterrows()], key="snm")
# # # # #     snid = summary[summary.name == snn]["material"].values[0]
# # # # #     snr  = summary[summary.material == snid].iloc[0]
# # # # #     bsn  = get_bom_components(data, snid)

# # # # #     if not len(bsn):
# # # # #         st.warning("🕸️ No BOM data found for this material.")
# # # # #         return

# # # # #     cw         = int(bsn["Supplier Name(Vendor)"].notna().sum())
# # # # #     cn         = int(bsn["Supplier Display"].str.startswith("⚠", na=False).sum())
# # # # #     us         = int(bsn["Supplier Name(Vendor)"].dropna().nunique())
# # # # #     tc         = len(bsn)
# # # # #     inhouse_n  = int((bsn["Procurement type"] == "E").sum())
# # # # #     external_n = int((bsn["Procurement type"] == "F").sum())

# # # # #     n1, n2, n3, n4 = st.columns(4)
# # # # #     for col, val, lbl, vc in [
# # # # #         (n1, tc,        "Total Components",     "#1E293B"),
# # # # #         (n2, inhouse_n, "Revvity Inhouse",      "#22C55E"),
# # # # #         (n3, cn,        "Missing Supplier",     "#F59E0B" if cn > 0 else "#1E293B"),
# # # # #         (n4, us,        "Unique Ext Suppliers", "#1E293B"),
# # # # #     ]:
# # # # #         with col:
# # # # #             st.markdown(
# # # # #                 f"<div class='sc'><div style='flex:1;'>"
# # # # #                 f"<div class='sv' style='color:{vc};'>{val}</div>"
# # # # #                 f"<div class='sl'>{lbl}</div></div></div>",
# # # # #                 unsafe_allow_html=True,
# # # # #             )

# # # # #     sn_tab, comp_tab, risk_tab = st.tabs(
# # # # #         ["🕸️  BOM Map", "📋  Components", "⚠️  Risk Analysis"]
# # # # #     )

# # # # #     # ── BOM Map ──────────────────────────────────────────────────────────────
# # # # #     with sn_tab:
# # # # #         sec("BOM Propagation Map")
# # # # #         _render_legend()

# # # # #         try:
# # # # #             fig = _build_sankey(bsn, snr)
# # # # #             st.plotly_chart(fig, use_container_width=True)
# # # # #         except ValueError as exc:
# # # # #             st.error(f"⚠️ Could not render Sankey diagram: {exc}")
# # # # #             st.info(
# # # # #                 "This usually means BOM rows are missing Material IDs or all "
# # # # #                 "quantities are zero/null. Check your data loader output."
# # # # #             )
# # # # #             with st.expander("🔍 Raw BOM data (debug)"):
# # # # #                 st.dataframe(bsn)

# # # # #         if st.session_state.azure_client:
# # # # #             if st.button("◈ Interpret BOM Map", key="interp_bom_sankey"):
# # # # #                 with st.spinner("ARIA interpreting…"):
# # # # #                     bom_ctx = {
# # # # #                         "material": snr["name"], "total_components": tc,
# # # # #                         "inhouse": inhouse_n, "external_named": cw - inhouse_n,
# # # # #                         "missing_supplier": cn, "unique_suppliers": us,
# # # # #                         "risk": snr["risk"],
# # # # #                     }
# # # # #                     interp = interpret_chart(
# # # # #                         st.session_state.azure_client, AZURE_DEPLOYMENT,
# # # # #                         "BOM Risk Propagation Map", bom_ctx,
# # # # #                         "What are the key supply chain risks in this BOM "
# # # # #                         "and what should procurement prioritise?",
# # # # #                     )
# # # # #                 st.markdown(
# # # # #                     f"<div class='ic' style='margin-top:8px;'>"
# # # # #                     f"<div class='il'>◈ ARIA</div>"
# # # # #                     f"<div class='ib'>{interp}</div></div>",
# # # # #                     unsafe_allow_html=True,
# # # # #                 )

# # # # #     # ── Component Detail ─────────────────────────────────────────────────────
# # # # #     with comp_tab:
# # # # #         sec("Component Detail")
# # # # #         bom_display2 = []
# # # # #         for _, b in bsn.iterrows():
# # # # #             eff_qty = b.get("Effective Order Qty", b["Comp. Qty (CUn)"])
# # # # #             fq_txt  = (
# # # # #                 "1 (Fixed)" if b.get("Fixed Qty Flag", False)
# # # # #                 else str(round(float(eff_qty), 3)) if pd.notna(eff_qty) else "—"
# # # # #             )
# # # # #             bom_display2.append({
# # # # #                 "Material":    _safe(b.get("Material")),
# # # # #                 "Description": _safe(b.get("Material Description"), maxlen=36),
# # # # #                 "Level":       _safe(b.get("Level"), maxlen=25),
# # # # #                 "Qty":         fq_txt,
# # # # #                 "Unit":        _safe(b.get("Component unit")),
# # # # #                 "Type":        _safe(b.get("Procurement Label")),
# # # # #                 "Supplier":    _safe(b.get("Supplier Display")),
# # # # #                 "Location":    _safe(b.get("Supplier Location")),
# # # # #                 "Transit":     (
# # # # #                     f"{b.get('Transit Days')}d"
# # # # #                     if b.get("Transit Days") is not None else "—"
# # # # #                 ),
# # # # #                 "Std Price":   (
# # # # #                     f"${b.get('Standard Price', 0):.2f}"
# # # # #                     if pd.notna(b.get("Standard Price")) else "—"
# # # # #                 ),
# # # # #             })
# # # # #         df_bd2 = pd.DataFrame(bom_display2)
# # # # #         sup_r3 = JsCode(
# # # # #             "class R{"
# # # # #             "init(p){const v=p.value||'';"
# # # # #             "this.e=document.createElement('span');"
# # # # #             "if(v.startsWith('⚠')){"
# # # # #             "this.e.style.cssText='background:#FEF3C7;color:#F59E0B;"
# # # # #             "padding:2px 6px;border-radius:4px;font-size:10px;font-weight:600;';"
# # # # #             "this.e.innerText=v;"
# # # # #             "}else if(v==='Revvity Inhouse'){"
# # # # #             "this.e.style.cssText='background:#DCFCE7;color:#16a34a;"
# # # # #             "padding:2px 6px;border-radius:4px;font-size:10px;font-weight:600;';"
# # # # #             "this.e.innerText='🏭 '+v;"
# # # # #             "}else if(v==='—'){"
# # # # #             "this.e.style.cssText='color:#94A3B8;font-size:10px;';"
# # # # #             "this.e.innerText=v;"
# # # # #             "}else{"
# # # # #             "this.e.style.cssText='background:#EFF6FF;color:#2563EB;"
# # # # #             "padding:2px 6px;border-radius:4px;font-size:10px;';"
# # # # #             "this.e.innerText='🚚 '+v;"
# # # # #             "};}"
# # # # #             "getGui(){return this.e;}}"
# # # # #         )
# # # # #         gb4 = GridOptionsBuilder.from_dataframe(df_bd2)
# # # # #         gb4.configure_column("Material",    width=82)
# # # # #         gb4.configure_column("Description", width=215)
# # # # #         gb4.configure_column("Level",       width=85)
# # # # #         gb4.configure_column("Qty",         width=75)
# # # # #         gb4.configure_column("Unit",        width=50)
# # # # #         gb4.configure_column("Type",        width=100)
# # # # #         gb4.configure_column("Supplier",    width=170, cellRenderer=sup_r3)
# # # # #         gb4.configure_column("Location",    width=130)
# # # # #         gb4.configure_column("Transit",     width=58)
# # # # #         gb4.configure_column("Std Price",   width=80)
# # # # #         gb4.configure_grid_options(rowHeight=36, headerHeight=32)
# # # # #         gb4.configure_default_column(resizable=True, sortable=True, filter=False)
# # # # #         AgGrid(
# # # # #             df_bd2, gridOptions=gb4.build(), height=320,
# # # # #             allow_unsafe_jscode=True, theme="alpine", custom_css=_AGGRID_CSS,
# # # # #         )

# # # # #     # ── Risk Cascade ──────────────────────────────────────────────────────────
# # # # #     with risk_tab:
# # # # #         sec("Risk Cascade Analysis")
# # # # #         risks = []

# # # # #         if snr["risk"] in ["CRITICAL", "WARNING"]:
# # # # #             risks.append({
# # # # #                 "icon": "⛔", "sev": 3, "color": "#EF4444", "bg": "#FEF2F2",
# # # # #                 "title": f"Finished Good at {snr['risk'].title()} Risk",
# # # # #                 "detail": (
# # # # #                     f"{snr['name']} has {round(snr['days_cover'])}d of cover. "
# # # # #                     f"SIH={round(snr['sih'])} vs SAP SS={round(snr['safety_stock'])}. "
# # # # #                     f"Production continuity at risk."
# # # # #                 ),
# # # # #                 "action": (
# # # # #                     f"Order {int(snr.get('repl_quantity', 0))} units immediately. "
# # # # #                     f"Contact procurement today."
# # # # #                 ),
# # # # #             })
# # # # #         if cn > 0:
# # # # #             risks.append({
# # # # #                 "icon": "⚠", "sev": 2, "color": "#F59E0B", "bg": "#FFFBEB",
# # # # #                 "title": f"Missing Supplier Data — {cn} External Components",
# # # # #                 "detail": (
# # # # #                     f"{cn} of {external_n} external components have no named supplier. "
# # # # #                     f"Single-source risk cannot be assessed for these."
# # # # #                 ),
# # # # #                 "action": "Procurement to verify and update BOM with supplier names and lead times.",
# # # # #             })
# # # # #         if 0 < us <= 2:
# # # # #             risks.append({
# # # # #                 "icon": "⚠", "sev": 2, "color": "#F59E0B", "bg": "#FFFBEB",
# # # # #                 "title": f"Supplier Concentration — {us} Unique Supplier(s)",
# # # # #                 "detail": (
# # # # #                     f"High dependency on {us} supplier(s). "
# # # # #                     f"Any disruption cascades to multiple components."
# # # # #                 ),
# # # # #                 "action": "Evaluate dual-sourcing for critical external components.",
# # # # #             })
# # # # #         if external_n > 0:
# # # # #             locs = list({
# # # # #                 str(r)
# # # # #                 for r in bsn[bsn["Procurement type"] == "F"]["Supplier Location"]
# # # # #                 .dropna().tolist()[:4]
# # # # #             })
# # # # #             risks.append({
# # # # #                 "icon": "🌍", "sev": 1, "color": "#3B82F6", "bg": "#EFF6FF",
# # # # #                 "title": f"External Procurement: {external_n} Components",
# # # # #                 "detail": (
# # # # #                     f"External components depend on supplier availability and transit times. "
# # # # #                     f"Suppliers in: {', '.join(locs) if locs else 'unknown'}."
# # # # #                 ),
# # # # #                 "action": "Review lead times — add stock buffers for long-transit items.",
# # # # #             })

# # # # #         if not risks:
# # # # #             st.success("✓ No critical propagation risks identified.")
# # # # #         else:
# # # # #             for r in sorted(risks, key=lambda x: -x["sev"]):
# # # # #                 st.markdown(
# # # # #                     f"<div style='"
# # # # #                     f"background:{r['bg']};"
# # # # #                     f"border:1px solid {r['color']}40;"
# # # # #                     f"border-left:4px solid {r['color']};"
# # # # #                     f"border-radius:8px;"
# # # # #                     f"padding:12px 14px;"
# # # # #                     f"margin-bottom:8px;"
# # # # #                     f"'>"
# # # # #                     f"<div style='display:flex;align-items:center;gap:8px;margin-bottom:5px;'>"
# # # # #                     f"<span style='font-size:16px;'>{r['icon']}</span>"
# # # # #                     f"<div style='font-size:12px;font-weight:800;color:{r['color']};'>"
# # # # #                     f"{r['title']}</div>"
# # # # #                     f"</div>"
# # # # #                     f"<div style='font-size:11px;color:#475569;margin-bottom:5px;'>"
# # # # #                     f"{r['detail']}</div>"
# # # # #                     f"<div style='font-size:11px;color:{r['color']};font-weight:600;'>"
# # # # #                     f"→ {r['action']}</div>"
# # # # #                     f"</div>",
# # # # #                     unsafe_allow_html=True,
# # # # #                 )

# # # # #         consol2   = get_supplier_consolidation(data, summary)
# # # # #         relevant2 = consol2[
# # # # #             consol2.material_list.apply(lambda x: snid in x)
# # # # #             & (consol2.finished_goods_supplied > 1)
# # # # #             & consol2.consolidation_opportunity
# # # # #         ]
# # # # #         if len(relevant2) > 0:
# # # # #             sec("Supplier Consolidation Opportunities")
# # # # #             for _, r2 in relevant2.iterrows():
# # # # #                 others = [MATERIAL_LABELS.get(m, m)[:18] for m in r2["material_list"] if m != snid]
# # # # #                 st.markdown(
# # # # #                     f"<div class='prow'><div style='font-size:14px;'>🏭</div>"
# # # # #                     f"<div style='flex:1;'>"
# # # # #                     f"<div style='font-size:12px;font-weight:800;'>{r2['supplier']}</div>"
# # # # #                     f"<div style='font-size:10px;color:var(--t3);'>"
# # # # #                     f"{r2['city']} · {r2['email']}</div>"
# # # # #                     f"<div style='font-size:10px;color:var(--t2);margin-top:2px;'>"
# # # # #                     f"Also supplies: {', '.join(others[:3])}</div>"
# # # # #                     f"</div>"
# # # # #                     f"<div style='font-size:10px;font-weight:700;color:var(--or);'>"
# # # # #                     f"⚡ Consolidate order</div>"
# # # # #                     f"</div>",
# # # # #                     unsafe_allow_html=True,
# # # # #                 )

# # # # #         if st.session_state.azure_client:
# # # # #             sec("Ask ARIA About This Network")
# # # # #             st.info("ℹ️ Insights are scoped to the currently selected finished good.")
# # # # #             uq = st.text_input(
# # # # #                 "Question",
# # # # #                 placeholder="e.g. Which supplier provides more than 1 material?",
# # # # #                 key="snq",
# # # # #                 label_visibility="collapsed",
# # # # #             )
# # # # #             if uq and st.button("Ask ARIA", key="sna"):
# # # # #                 bom_lines = []
# # # # #                 for _, row in bsn.iterrows():
# # # # #                     mat_desc  = _safe(row.get("Material Description"),
# # # # #                                       fallback=str(row.get("Material")), maxlen=40)
# # # # #                     qty       = row.get("Effective Order Qty") or row.get("Comp. Qty (CUn)")
# # # # #                     fixed     = "X (order exactly 1)" if row.get("Fixed Qty Flag") else ""
# # # # #                     sup       = _safe(row.get("Supplier Display"))
# # # # #                     loc       = _safe(row.get("Supplier Location"))
# # # # #                     transit   = _safe(row.get("Transit Days"))
# # # # #                     rel       = _safe(row.get("Supplier Reliability"))
# # # # #                     sp        = row.get("Standard Price")
# # # # #                     std_price = f"${sp:.2f}" if pd.notna(sp) else "—"
# # # # #                     bom_lines.append(
# # # # #                         f"- {mat_desc} | Qty: {qty} {fixed} | Price: {std_price} "
# # # # #                         f"| Supplier: {sup} | Location: {loc} "
# # # # #                         f"| Transit: {transit}d | Reliability: {rel}"
# # # # #                     )

# # # # #                 ctx3 = (
# # # # #                     f"Material: {snr['name']} (ID: {snid})\n"
# # # # #                     f"Risk: {snr['risk']}\n"
# # # # #                     f"Total: {tc} | Inhouse: {inhouse_n} | External: {external_n}\n"
# # # # #                     f"Missing supplier: {cn} | Unique suppliers: {us}\n"
# # # # #                     f"BOM details:\n" + "\n".join(bom_lines)
# # # # #                 )
# # # # #                 with st.spinner("Thinking…"):
# # # # #                     ans = chat_with_data(
# # # # #                         st.session_state.azure_client, AZURE_DEPLOYMENT, uq, ctx3
# # # # #                     )
# # # # #                 st.markdown(
# # # # #                     f"<div class='ic' style='margin-top:8px;'>"
# # # # #                     f"<div class='il'>◈ ARIA</div>"
# # # # #                     f"<div class='ib'>{ans}</div></div>",
# # # # #                     unsafe_allow_html=True,
# # # # #                 )

# # # # #     st.markdown(
# # # # #         '<div class="pfooter">🕸️ Powered by <strong>MResult</strong></div>',
# # # # #         unsafe_allow_html=True,
# # # # #     )


# # # # # # """
# # # # # # tabs/supply_network.py
# # # # # # Supply Network tab: BOM propagation map (Sankey diagram), component detail table,
# # # # # # risk cascade analysis, and supplier consolidation opportunities.
# # # # # # """

# # # # # # import streamlit as st
# # # # # # import pandas as pd
# # # # # # import plotly.graph_objects as go

# # # # # # from st_aggrid import AgGrid, GridOptionsBuilder, JsCode

# # # # # # from utils.helpers import sec, note, sbadge, ORANGE, AZURE_DEPLOYMENT
# # # # # # from data_loader import get_bom_components, get_supplier_consolidation
# # # # # # from agent import interpret_chart, chat_with_data

# # # # # # _AGGRID_CSS = {
# # # # # #     ".ag-root-wrapper": {"border": "1px solid #E2E8F0!important", "border-radius": "12px!important"},
# # # # # #     ".ag-header":       {"background": "#F8FAFE!important"},
# # # # # #     ".ag-row-even":     {"background": "#FFFFFF!important"},
# # # # # #     ".ag-row-odd":      {"background": "#F8FAFE!important"},
# # # # # # }


# # # # # # def render():
# # # # # #     data            = st.session_state.data
# # # # # #     summary         = st.session_state.summary
# # # # # #     MATERIAL_LABELS = st.session_state.material_labels

# # # # # #     st.markdown(
# # # # # #         "<div style='font-size:15px;font-weight:800;margin-bottom:4px;'>Supply Network</div>"
# # # # # #         "<div style='font-size:12px;color:var(--t3);margin-bottom:14px;'>"
# # # # # #         "BOM structure · Supplier locations · Risk cascade · Consolidation intelligence</div>",
# # # # # #         unsafe_allow_html=True,
# # # # # #     )

# # # # # #     snn  = st.selectbox("Finished Good", [r["name"] for _, r in summary.iterrows()], key="snm")
# # # # # #     snid = summary[summary.name == snn]["material"].values[0]
# # # # # #     snr  = summary[summary.material == snid].iloc[0]
# # # # # #     bsn  = get_bom_components(data, snid)

# # # # # #     if not len(bsn):
# # # # # #         st.markdown(
# # # # # #             "<div class='flag-box'><div style='font-size:22px;margin-bottom:8px;'>🕸️</div>"
# # # # # #             "<div style='font-size:14px;font-weight:800;color:var(--t2);'>No BOM data for this material</div></div>",
# # # # # #             unsafe_allow_html=True,
# # # # # #         )
# # # # # #         return

# # # # # #     cw        = int(bsn["Supplier Name(Vendor)"].notna().sum())
# # # # # #     cn        = len(bsn[bsn["Supplier Display"].str.startswith("⚠", na=False)])
# # # # # #     us        = int(bsn["Supplier Name(Vendor)"].dropna().nunique())
# # # # # #     tc        = len(bsn)
# # # # # #     inhouse_n = int((bsn["Procurement type"] == "E").sum())
# # # # # #     external_n = int((bsn["Procurement type"] == "F").sum())

# # # # # #     n1, n2, n3, n4 = st.columns(4)
# # # # # #     for col, val, lbl, vc in [
# # # # # #         (n1, tc,        "Total Components",  "#1E293B"),
# # # # # #         (n2, inhouse_n, "Revvity Inhouse",   "#22C55E"),
# # # # # #         (n3, cn,        "Missing Supplier",  "#F59E0B" if cn > 0 else "#1E293B"),
# # # # # #         (n4, us,        "Unique Ext Suppliers", "#1E293B"),
# # # # # #     ]:
# # # # # #         with col:
# # # # # #             st.markdown(
# # # # # #                 f"<div class='sc'><div style='flex:1;'>"
# # # # # #                 f"<div class='sv' style='color:{vc};'>{val}</div>"
# # # # # #                 f"<div class='sl'>{lbl}</div></div></div>",
# # # # # #                 unsafe_allow_html=True,
# # # # # #             )

# # # # # #     sn_tab, comp_tab, risk_tab = st.tabs(["🕸️  BOM Map", "📋  Components", "⚠️  Risk Analysis"])

# # # # # #     # ── BOM Map – Sankey diagram (improved layout) ─────────────────────────────
# # # # # #     with sn_tab:
# # # # # #         sec("BOM Propagation Map")
# # # # # #         # Legend as HTML list
# # # # # #         st.markdown("""
# # # # # #         <div class='note-box'>
# # # # # #         <strong>Colour legend:</strong>
# # # # # #         <ul style='margin:5px 0 0 20px; padding-left:0;'>
# # # # # #         <li>🔵 <strong>Blue</strong> = External component with named supplier</li>
# # # # # #         <li>🟢 <strong>Green</strong> = Inhouse component (Revvity)</li>
# # # # # #         <li>🟡 <strong>Amber</strong> = External component with <strong>missing supplier data</strong></li>
# # # # # #         <li>🟣 <strong>Purple</strong> = Supplier node</li>
# # # # # #         <li>Root node colour matches finished good risk (🔴 Critical / 🟠 Warning / 🟢 Healthy)</li>
# # # # # #         </ul>
# # # # # #         Hover over nodes for details. Use the interactive controls to zoom/pan.
# # # # # #         </div>
# # # # # #         """, unsafe_allow_html=True)

# # # # # #         # Build node list and links
# # # # # #         nodes = []
# # # # # #         node_colors = []
# # # # # #         node_map = {}

# # # # # #         # Root node
# # # # # #         root_name = snr["name"]
# # # # # #         risk_color_map = {"CRITICAL": "#EF4444", "WARNING": "#F59E0B", "HEALTHY": "#22C55E"}
# # # # # #         root_color = risk_color_map.get(snr["risk"], "#94A3B8")
# # # # # #         nodes.append(root_name)
# # # # # #         node_colors.append(root_color)
# # # # # #         node_map[root_name] = 0

# # # # # #         sources = []
# # # # # #         targets = []
# # # # # #         values = []

# # # # # #         # Process each BOM row
# # # # # #         for _, row in bsn.iterrows():
# # # # # #             # Component label (shortened)
# # # # # #             comp_desc = str(row["Material Description"])[:30] if pd.notna(row["Material Description"]) else str(row["Material"])
# # # # # #             comp_label = comp_desc
# # # # # #             sup_display = row.get("Supplier Display", "—")
# # # # # #             proc_type = str(row.get("Procurement type", "")).strip()
# # # # # #             qty_raw = row.get("Effective Order Qty", row["Comp. Qty (CUn)"])
# # # # # #             try:
# # # # # #                 qty = float(qty_raw) if pd.notna(qty_raw) else 1.0
# # # # # #             except:
# # # # # #                 qty = 1.0

# # # # # #             # Add component node
# # # # # #             if comp_label not in node_map:
# # # # # #                 if proc_type == "E":
# # # # # #                     comp_color = "#22C55E"
# # # # # #                 elif sup_display.startswith("⚠"):
# # # # # #                     comp_color = "#F59E0B"
# # # # # #                 else:
# # # # # #                     comp_color = "#3B82F6"
# # # # # #                 nodes.append(comp_label)
# # # # # #                 node_colors.append(comp_color)
# # # # # #                 node_map[comp_label] = len(nodes) - 1

# # # # # #             # Root -> component
# # # # # #             sources.append(node_map[root_name])
# # # # # #             targets.append(node_map[comp_label])
# # # # # #             values.append(qty)

# # # # # #             # Supplier node (if external and named)
# # # # # #             if sup_display not in ["Revvity Inhouse", "—"] and not sup_display.startswith("⚠"):
# # # # # #                 sup_label = sup_display[:25]
# # # # # #                 if sup_label not in node_map:
# # # # # #                     nodes.append(sup_label)
# # # # # #                     node_colors.append("#8B5CF6")
# # # # # #                     node_map[sup_label] = len(nodes) - 1
# # # # # #                 sources.append(node_map[comp_label])
# # # # # #                 targets.append(node_map[sup_label])
# # # # # #                 values.append(1.0)

# # # # # #         # Build Sankey figure with improved layout
# # # # # #         fig = go.Figure(data=[go.Sankey(
# # # # # #             arrangement="snap",
# # # # # #             node=dict(
# # # # # #                 pad=30,               # more padding between nodes
# # # # # #                 thickness=15,
# # # # # #                 line=dict(color="white", width=0.5),
# # # # # #                 label=nodes,
# # # # # #                 color=node_colors,
# # # # # #                 hovertemplate="<b>%{label}</b><extra></extra>"
# # # # # #             ),
# # # # # #             link=dict(
# # # # # #                 source=sources,
# # # # # #                 target=targets,
# # # # # #                 value=values,
# # # # # #                 color="rgba(160,160,160,0.4)"
# # # # # #             )
# # # # # #         )])
# # # # # #         fig.update_layout(
# # # # # #             title=None,
# # # # # #             font=dict(size=11, family="Inter", color="#1E293B"),
# # # # # #             height=550,               # taller for better visibility
# # # # # #             margin=dict(l=20, r=20, t=20, b=20),
# # # # # #             paper_bgcolor="white",
# # # # # #             plot_bgcolor="white"
# # # # # #         )
# # # # # #         st.plotly_chart(fig, use_container_width=True)

# # # # # #         if st.session_state.azure_client:
# # # # # #             if st.button("◈ Interpret BOM Map", key="interp_bom_sankey"):
# # # # # #                 with st.spinner("ARIA interpreting…"):
# # # # # #                     bom_ctx = {
# # # # # #                         "material": snr["name"], "total_components": tc,
# # # # # #                         "inhouse": inhouse_n, "external_named": cw - inhouse_n,
# # # # # #                         "missing_supplier": cn, "unique_suppliers": us, "risk": snr["risk"],
# # # # # #                     }
# # # # # #                     interp = interpret_chart(
# # # # # #                         st.session_state.azure_client, AZURE_DEPLOYMENT,
# # # # # #                         "BOM Risk Propagation Map", bom_ctx,
# # # # # #                         "What are the key supply chain risks in this BOM and what should procurement prioritise?",
# # # # # #                     )
# # # # # #                 st.markdown(
# # # # # #                     f"<div class='ic' style='margin-top:8px;'><div class='il'>◈ ARIA</div>"
# # # # # #                     f"<div class='ib'>{interp}</div></div>",
# # # # # #                     unsafe_allow_html=True,
# # # # # #                 )

# # # # # #     # ── Component Detail (unchanged) ─────────────────────────────────────────
# # # # # #     with comp_tab:
# # # # # #         sec("Component Detail")
# # # # # #         bom_display2 = []
# # # # # #         for _, b in bsn.iterrows():
# # # # # #             eff_qty = b.get("Effective Order Qty", b["Comp. Qty (CUn)"])
# # # # # #             fq_txt  = ("1 (Fixed)" if b.get("Fixed Qty Flag", False)
# # # # # #                        else str(round(float(eff_qty), 3)) if pd.notna(eff_qty) else "—")
# # # # # #             bom_display2.append({
# # # # # #                 "Material":    str(b["Material"]),
# # # # # #                 "Description": str(b["Material Description"])[:36] if pd.notna(b["Material Description"]) else "—",
# # # # # #                 "Level":       str(b["Level"])[:25] if pd.notna(b["Level"]) else "—",
# # # # # #                 "Qty":         fq_txt,
# # # # # #                 "Unit":        str(b["Component unit"]) if pd.notna(b["Component unit"]) else "—",
# # # # # #                 "Type":        b.get("Procurement Label", "—"),
# # # # # #                 "Supplier":    b.get("Supplier Display", "—"),
# # # # # #                 "Location":    b.get("Supplier Location", "—"),
# # # # # #                 "Transit":     f"{b.get('Transit Days', '—')}d" if b.get("Transit Days") is not None else "—",
# # # # # #                 "Std Price":   f"${b.get('Standard Price', 0):.2f}" if pd.notna(b.get('Standard Price')) else "—",
# # # # # #             })
# # # # # #         df_bd2  = pd.DataFrame(bom_display2)
# # # # # #         sup_r3  = JsCode("""class R{init(p){const v=p.value||'';this.e=document.createElement('span');if(v.startsWith('⚠')){this.e.style.cssText='background:#FEF3C7;color:#F59E0B;padding:2px 6px;border-radius:4px;font-size:10px;font-weight:600;';this.e.innerText=v;}else if(v==='Revvity Inhouse'){this.e.style.cssText='background:#DCFCE7;color:#16a34a;padding:2px 6px;border-radius:4px;font-size:10px;font-weight:600;';this.e.innerText='🏭 '+v;}else{this.e.style.cssText='background:#EFF6FF;color:#2563EB;padding:2px 6px;border-radius:4px;font-size:10px;';this.e.innerText='🚚 '+v;};}getGui(){return this.e;}}""")
# # # # # #         gb4     = GridOptionsBuilder.from_dataframe(df_bd2)
# # # # # #         gb4.configure_column("Material",    width=82)
# # # # # #         gb4.configure_column("Description", width=215)
# # # # # #         gb4.configure_column("Level",       width=85)
# # # # # #         gb4.configure_column("Qty",         width=75)
# # # # # #         gb4.configure_column("Unit",        width=50)
# # # # # #         gb4.configure_column("Type",        width=100)
# # # # # #         gb4.configure_column("Supplier",    width=170, cellRenderer=sup_r3)
# # # # # #         gb4.configure_column("Location",    width=130)
# # # # # #         gb4.configure_column("Transit",     width=58)
# # # # # #         gb4.configure_column("Std Price",   width=80)
# # # # # #         gb4.configure_grid_options(rowHeight=36, headerHeight=32)
# # # # # #         gb4.configure_default_column(resizable=True, sortable=True, filter=False)
# # # # # #         AgGrid(df_bd2, gridOptions=gb4.build(), height=320,
# # # # # #                allow_unsafe_jscode=True, theme="alpine", custom_css=_AGGRID_CSS)

# # # # # #     # ── Risk Cascade (unchanged) ─────────────────────────────────────────────
# # # # # #     with risk_tab:
# # # # # #         sec("Risk Cascade Analysis")
# # # # # #         risks = []
# # # # # #         if snr["risk"] in ["CRITICAL", "WARNING"]:
# # # # # #             risks.append({
# # # # # #                 "icon": "⛔", "sev": 3, "color": "#EF4444", "bg": "#FEF2F2",
# # # # # #                 "title": f"Finished Good at {snr['risk'].title()} Risk",
# # # # # #                 "detail": (f"{snr['name']} has {round(snr['days_cover'])}d of cover. "
# # # # # #                            f"SIH={round(snr['sih'])} vs SAP SS={round(snr['safety_stock'])}. "
# # # # # #                            f"Production continuity at risk."),
# # # # # #                 "action": f"Order {int(snr.get('repl_quantity', 0))} units immediately. Contact procurement today.",
# # # # # #             })
# # # # # #         if cn > 0:
# # # # # #             risks.append({
# # # # # #                 "icon": "⚠", "sev": 2, "color": "#F59E0B", "bg": "#FFFBEB",
# # # # # #                 "title": f"Missing Supplier Data — {cn} External Components",
# # # # # #                 "detail": (f"{cn} of {external_n} external components have no named supplier. "
# # # # # #                            f"Single-source risk cannot be assessed for these."),
# # # # # #                 "action": "Procurement to verify and update BOM with supplier names and lead times.",
# # # # # #             })
# # # # # #         if 0 < us <= 2:
# # # # # #             risks.append({
# # # # # #                 "icon": "⚠", "sev": 2, "color": "#F59E0B", "bg": "#FFFBEB",
# # # # # #                 "title": f"Supplier Concentration — {us} Unique Supplier(s)",
# # # # # #                 "detail": f"High dependency on {us} supplier(s). Any disruption cascades to multiple components simultaneously.",
# # # # # #                 "action": "Evaluate dual-sourcing for critical external components.",
# # # # # #             })
# # # # # #         ext_comps = bsn[bsn["Procurement type"] == "F"]
# # # # # #         if len(ext_comps) > 0:
# # # # # #             locs = list(set([str(r) for r in bsn[bsn["Procurement type"] == "F"]["Supplier Location"].dropna().tolist()[:4]]))
# # # # # #             risks.append({
# # # # # #                 "icon": "🌍", "sev": 1, "color": "#3B82F6", "bg": "#EFF6FF",
# # # # # #                 "title": f"External Procurement: {len(ext_comps)} Components",
# # # # # #                 "detail": (f"External components depend on supplier availability and transit times. "
# # # # # #                            f"Suppliers located in: {', '.join(locs)}."),
# # # # # #                 "action": "Review external component lead times — stock buffers for long-transit items.",
# # # # # #             })

# # # # # #         if not risks:
# # # # # #             st.markdown(
# # # # # #                 "<div style='padding:10px 13px;background:var(--gbg);border:1px solid rgba(34,197,94,0.2);"
# # # # # #                 "border-radius:var(--r);font-size:12px;color:#14532d;'>"
# # # # # #                 "✓ No critical propagation risks identified.</div>",
# # # # # #                 unsafe_allow_html=True,
# # # # # #             )
# # # # # #         else:
# # # # # #             for r in sorted(risks, key=lambda x: -x["sev"]):
# # # # # #                 st.markdown(
# # # # # #                     f"<div style='background:{r['bg']};border:1px solid {r['color']}40;"
# # # # # #                     f"border-left:4px solid {r['color']};border-radius:var(--r);"
# # # # # #                     f"padding:12px 14px;margin-bottom:8px;'>"
# # # # # #                     f"<div style='display:flex;align-items:center;gap:8px;margin-bottom:5px;'>"
# # # # # #                     f"<span style='font-size:16px;'>{r['icon']}</span>"
# # # # # #                     f"<div style='font-size:12px;font-weight:800;color:{r['color']};'>{r['title']}</div>"
# # # # # #                     f"</div>"
# # # # # #                     f"<div style='font-size:11px;color:var(--t2);margin-bottom:5px;'>{r['detail']}</div>"
# # # # # #                     f"<div style='font-size:11px;color:{r['color']};font-weight:600;'>→ {r['action']}</div>"
# # # # # #                     f"</div>",
# # # # # #                     unsafe_allow_html=True,
# # # # # #                 )

# # # # # #         # Consolidation opportunities
# # # # # #         consol2   = get_supplier_consolidation(data, summary)
# # # # # #         relevant2 = consol2[
# # # # # #             consol2.material_list.apply(lambda x: snid in x)
# # # # # #             & (consol2.finished_goods_supplied > 1)
# # # # # #             & consol2.consolidation_opportunity
# # # # # #         ]
# # # # # #         if len(relevant2) > 0:
# # # # # #             sec("Supplier Consolidation Opportunities")
# # # # # #             for _, r2 in relevant2.iterrows():
# # # # # #                 others = [MATERIAL_LABELS.get(m, m)[:18] for m in r2["material_list"] if m != snid]
# # # # # #                 st.markdown(
# # # # # #                     f"<div class='prow'><div style='font-size:14px;'>🏭</div>"
# # # # # #                     f"<div style='flex:1;'>"
# # # # # #                     f"<div style='font-size:12px;font-weight:800;'>{r2['supplier']}</div>"
# # # # # #                     f"<div style='font-size:10px;color:var(--t3);'>{r2['city']} · {r2['email']}</div>"
# # # # # #                     f"<div style='font-size:10px;color:var(--t2);margin-top:2px;'>Also supplies: {', '.join(others[:3])}</div>"
# # # # # #                     f"</div>"
# # # # # #                     f"<div style='font-size:10px;font-weight:700;color:var(--or);'>⚡ Consolidate order</div>"
# # # # # #                     f"</div>",
# # # # # #                     unsafe_allow_html=True,
# # # # # #                 )

# # # # # #         # ── Ask ARIA with rich BOM context (including Standard Price) ─────────
# # # # # #         if st.session_state.azure_client:
# # # # # #             sec("Ask ARIA About This Network")
# # # # # #             st.info("ℹ️ This assistant provides supplier‑related insights only for the currently selected finished good.")
# # # # # #             uq = st.text_input(
# # # # # #                 "Question",
# # # # # #                 placeholder="e.g. Which supplier provides more than 1 material for DELFIA Wash Concentrate?",
# # # # # #                 key="snq", label_visibility="collapsed",
# # # # # #             )
# # # # # #             if uq and st.button("Ask ARIA", key="sna"):
# # # # # #                 bom_lines = []
# # # # # #                 for _, row in bsn.iterrows():
# # # # # #                     mat_desc = str(row["Material Description"])[:40] if pd.notna(row["Material Description"]) else str(row["Material"])
# # # # # #                     qty = row["Effective Order Qty"] if "Effective Order Qty" in row else row["Comp. Qty (CUn)"]
# # # # # #                     fixed = "X (order exactly 1)" if row.get("Fixed Qty Flag") else ""
# # # # # #                     sup = row.get("Supplier Display", "—")
# # # # # #                     loc = row.get("Supplier Location", "—")
# # # # # #                     transit = row.get("Transit Days", "—")
# # # # # #                     reliability = row.get("Supplier Reliability", "—")
# # # # # #                     std_price = row.get("Standard Price", "—")
# # # # # #                     if pd.notna(std_price):
# # # # # #                         std_price = f"${std_price:.2f}"
# # # # # #                     bom_lines.append(f"- Component: {mat_desc} | Qty: {qty} {fixed} | Std Price: {std_price} | Supplier: {sup} | Location: {loc} | Transit: {transit}d | Reliability: {reliability}")
# # # # # #                 bom_table = "\n".join(bom_lines)

# # # # # #                 ctx3 = (
# # # # # #                     f"Material: {snr['name']} (ID: {snid})\n"
# # # # # #                     f"Risk: {snr['risk']}\n"
# # # # # #                     f"Total components: {tc}\n"
# # # # # #                     f"Inhouse components: {inhouse_n}\n"
# # # # # #                     f"External components: {external_n}\n"
# # # # # #                     f"Missing supplier data: {cn} components\n"
# # # # # #                     f"Unique external suppliers: {us}\n"
# # # # # #                     f"BOM details:\n{bom_table}"
# # # # # #                 )
# # # # # #                 with st.spinner("Thinking…"):
# # # # # #                     ans = chat_with_data(st.session_state.azure_client, AZURE_DEPLOYMENT, uq, ctx3)
# # # # # #                 st.markdown(
# # # # # #                     f"<div class='ic' style='margin-top:8px;'><div class='il'>◈ ARIA</div>"
# # # # # #                     f"<div class='ib'>{ans}</div></div>",
# # # # # #                     unsafe_allow_html=True,
# # # # # #                 )

# # # # # #     st.markdown('<div class="pfooter">🕸️ Powered by <strong>MResult</strong></div>', unsafe_allow_html=True)



# # # # # # # # # # # # # """
# # # # # # # # # # # # # tabs/supply_network.py
# # # # # # # # # # # # # Supply Network tab: BOM propagation map, component detail table,
# # # # # # # # # # # # # risk cascade analysis, and supplier consolidation opportunities.
# # # # # # # # # # # # # """

# # # # # # # # # # # # # import streamlit as st
# # # # # # # # # # # # # import pandas as pd

# # # # # # # # # # # # # from st_aggrid import AgGrid, GridOptionsBuilder, JsCode

# # # # # # # # # # # # # from utils.helpers import sec, note, sbadge, plot_bom_tree, ORANGE, AZURE_DEPLOYMENT
# # # # # # # # # # # # # from data_loader import get_bom_components, get_supplier_consolidation
# # # # # # # # # # # # # from agent import interpret_chart, chat_with_data

# # # # # # # # # # # # # _AGGRID_CSS = {
# # # # # # # # # # # # #     ".ag-root-wrapper": {"border": "1px solid #E2E8F0!important", "border-radius": "12px!important"},
# # # # # # # # # # # # #     ".ag-header":       {"background": "#F8FAFE!important"},
# # # # # # # # # # # # #     ".ag-row-even":     {"background": "#FFFFFF!important"},
# # # # # # # # # # # # #     ".ag-row-odd":      {"background": "#F8FAFE!important"},
# # # # # # # # # # # # # }


# # # # # # # # # # # # # def render():
# # # # # # # # # # # # #     data            = st.session_state.data
# # # # # # # # # # # # #     summary         = st.session_state.summary
# # # # # # # # # # # # #     MATERIAL_LABELS = st.session_state.material_labels

# # # # # # # # # # # # #     st.markdown(
# # # # # # # # # # # # #         "<div style='font-size:15px;font-weight:800;margin-bottom:4px;'>Supply Network</div>"
# # # # # # # # # # # # #         "<div style='font-size:12px;color:var(--t3);margin-bottom:14px;'>"
# # # # # # # # # # # # #         "BOM structure · Supplier locations · Risk cascade · Consolidation intelligence</div>",
# # # # # # # # # # # # #         unsafe_allow_html=True,
# # # # # # # # # # # # #     )

# # # # # # # # # # # # #     snn  = st.selectbox("Finished Good", [r["name"] for _, r in summary.iterrows()], key="snm")
# # # # # # # # # # # # #     snid = summary[summary.name == snn]["material"].values[0]
# # # # # # # # # # # # #     snr  = summary[summary.material == snid].iloc[0]
# # # # # # # # # # # # #     bsn  = get_bom_components(data, snid)

# # # # # # # # # # # # #     if not len(bsn):
# # # # # # # # # # # # #         st.markdown(
# # # # # # # # # # # # #             "<div class='flag-box'><div style='font-size:22px;margin-bottom:8px;'>🕸️</div>"
# # # # # # # # # # # # #             "<div style='font-size:14px;font-weight:800;color:var(--t2);'>No BOM data for this material</div></div>",
# # # # # # # # # # # # #             unsafe_allow_html=True,
# # # # # # # # # # # # #         )
# # # # # # # # # # # # #         return

# # # # # # # # # # # # #     cw        = int(bsn["Supplier Name(Vendor)"].notna().sum())
# # # # # # # # # # # # #     cn        = len(bsn[bsn["Supplier Display"].str.startswith("⚠", na=False)])
# # # # # # # # # # # # #     us        = int(bsn["Supplier Name(Vendor)"].dropna().nunique())
# # # # # # # # # # # # #     tc        = len(bsn)
# # # # # # # # # # # # #     inhouse_n = int((bsn["Procurement type"] == "E").sum())
# # # # # # # # # # # # #     external_n = int((bsn["Procurement type"] == "F").sum())

# # # # # # # # # # # # #     n1, n2, n3, n4 = st.columns(4)
# # # # # # # # # # # # #     for col, val, lbl, vc in [
# # # # # # # # # # # # #         (n1, tc,        "Total Components",  "#1E293B"),
# # # # # # # # # # # # #         (n2, inhouse_n, "Revvity Inhouse",   "#22C55E"),
# # # # # # # # # # # # #         (n3, cn,        "Missing Supplier",  "#F59E0B" if cn > 0 else "#1E293B"),
# # # # # # # # # # # # #         (n4, us,        "Unique Ext Suppliers", "#1E293B"),
# # # # # # # # # # # # #     ]:
# # # # # # # # # # # # #         with col:
# # # # # # # # # # # # #             st.markdown(
# # # # # # # # # # # # #                 f"<div class='sc'><div style='flex:1;'>"
# # # # # # # # # # # # #                 f"<div class='sv' style='color:{vc};'>{val}</div>"
# # # # # # # # # # # # #                 f"<div class='sl'>{lbl}</div></div></div>",
# # # # # # # # # # # # #                 unsafe_allow_html=True,
# # # # # # # # # # # # #             )

# # # # # # # # # # # # #     sn_tab, comp_tab, risk_tab = st.tabs(["🕸️  BOM Map", "📋  Components", "⚠️  Risk Analysis"])

# # # # # # # # # # # # #     # ── BOM Map ───────────────────────────────────────────────────────────────
# # # # # # # # # # # # #     with sn_tab:
# # # # # # # # # # # # #         sec("BOM Propagation Map")
# # # # # # # # # # # # #         note("Blue = External supplier named. Amber = External, no supplier data. "
# # # # # # # # # # # # #              "Green = Revvity Inhouse production. Hover nodes for detail.")
# # # # # # # # # # # # #         risk_color_map = {"CRITICAL": "#EF4444", "WARNING": "#F59E0B", "HEALTHY": "#22C55E"}
# # # # # # # # # # # # #         root_color     = risk_color_map.get(snr["risk"], "#94A3B8")
# # # # # # # # # # # # #         fig_tree       = plot_bom_tree(bsn, snr["name"], root_color)
# # # # # # # # # # # # #         st.plotly_chart(fig_tree, use_container_width=True)

# # # # # # # # # # # # #         if st.session_state.azure_client:
# # # # # # # # # # # # #             if st.button("◈ Interpret BOM Map", key="interp_bom_tree"):
# # # # # # # # # # # # #                 with st.spinner("ARIA interpreting…"):
# # # # # # # # # # # # #                     bom_ctx = {
# # # # # # # # # # # # #                         "material": snr["name"], "total_components": tc,
# # # # # # # # # # # # #                         "inhouse": inhouse_n, "external_named": cw - inhouse_n,
# # # # # # # # # # # # #                         "missing_supplier": cn, "unique_suppliers": us, "risk": snr["risk"],
# # # # # # # # # # # # #                     }
# # # # # # # # # # # # #                     interp = interpret_chart(
# # # # # # # # # # # # #                         st.session_state.azure_client, AZURE_DEPLOYMENT,
# # # # # # # # # # # # #                         "BOM Risk Propagation Map", bom_ctx,
# # # # # # # # # # # # #                         "What are the key supply chain risks in this BOM and what should procurement prioritise?",
# # # # # # # # # # # # #                     )
# # # # # # # # # # # # #                 st.markdown(
# # # # # # # # # # # # #                     f"<div class='ic' style='margin-top:8px;'><div class='il'>◈ ARIA</div>"
# # # # # # # # # # # # #                     f"<div class='ib'>{interp}</div></div>",
# # # # # # # # # # # # #                     unsafe_allow_html=True,
# # # # # # # # # # # # #                 )

# # # # # # # # # # # # #     # ── Component Detail ──────────────────────────────────────────────────────
# # # # # # # # # # # # #     with comp_tab:
# # # # # # # # # # # # #         sec("Component Detail")
# # # # # # # # # # # # #         bom_display2 = []
# # # # # # # # # # # # #         for _, b in bsn.iterrows():
# # # # # # # # # # # # #             eff_qty = b.get("Effective Order Qty", b["Comp. Qty (CUn)"])
# # # # # # # # # # # # #             fq_txt  = ("1 (Fixed)" if b.get("Fixed Qty Flag", False)
# # # # # # # # # # # # #                        else str(round(float(eff_qty), 3)) if pd.notna(eff_qty) else "—")
# # # # # # # # # # # # #             bom_display2.append({
# # # # # # # # # # # # #                 "Material":    str(b["Material"]),
# # # # # # # # # # # # #                 "Description": str(b["Material Description"])[:36] if pd.notna(b["Material Description"]) else "—",
# # # # # # # # # # # # #                 "Level":       str(b["Level"])[:25] if pd.notna(b["Level"]) else "—",
# # # # # # # # # # # # #                 "Qty":         fq_txt,
# # # # # # # # # # # # #                 "Unit":        str(b["Component unit"]) if pd.notna(b["Component unit"]) else "—",
# # # # # # # # # # # # #                 "Type":        b.get("Procurement Label", "—"),
# # # # # # # # # # # # #                 "Supplier":    b.get("Supplier Display", "—"),
# # # # # # # # # # # # #                 "Location":    b.get("Supplier Location", "—"),
# # # # # # # # # # # # #                 "Transit":     f"{b.get('Transit Days', '—')}d" if b.get("Transit Days") is not None else "—",
# # # # # # # # # # # # #             })
# # # # # # # # # # # # #         df_bd2  = pd.DataFrame(bom_display2)
# # # # # # # # # # # # #         sup_r3  = JsCode("""class R{init(p){const v=p.value||'';this.e=document.createElement('span');if(v.startsWith('⚠')){this.e.style.cssText='background:#FEF3C7;color:#F59E0B;padding:2px 6px;border-radius:4px;font-size:10px;font-weight:600;';this.e.innerText=v;}else if(v==='Revvity Inhouse'){this.e.style.cssText='background:#DCFCE7;color:#16a34a;padding:2px 6px;border-radius:4px;font-size:10px;font-weight:600;';this.e.innerText='🏭 '+v;}else{this.e.style.cssText='background:#EFF6FF;color:#2563EB;padding:2px 6px;border-radius:4px;font-size:10px;';this.e.innerText='🚚 '+v;};}getGui(){return this.e;}}""")
# # # # # # # # # # # # #         gb4     = GridOptionsBuilder.from_dataframe(df_bd2)
# # # # # # # # # # # # #         gb4.configure_column("Material",    width=82)
# # # # # # # # # # # # #         gb4.configure_column("Description", width=215)
# # # # # # # # # # # # #         gb4.configure_column("Level",       width=85)
# # # # # # # # # # # # #         gb4.configure_column("Qty",         width=75)
# # # # # # # # # # # # #         gb4.configure_column("Unit",        width=50)
# # # # # # # # # # # # #         gb4.configure_column("Type",        width=100)
# # # # # # # # # # # # #         gb4.configure_column("Supplier",    width=170, cellRenderer=sup_r3)
# # # # # # # # # # # # #         gb4.configure_column("Location",    width=130)
# # # # # # # # # # # # #         gb4.configure_column("Transit",     width=58)
# # # # # # # # # # # # #         gb4.configure_grid_options(rowHeight=36, headerHeight=32)
# # # # # # # # # # # # #         gb4.configure_default_column(resizable=True, sortable=True, filter=False)
# # # # # # # # # # # # #         AgGrid(df_bd2, gridOptions=gb4.build(), height=320,
# # # # # # # # # # # # #                allow_unsafe_jscode=True, theme="alpine", custom_css=_AGGRID_CSS)

# # # # # # # # # # # # #     # ── Risk Cascade ──────────────────────────────────────────────────────────
# # # # # # # # # # # # #     with risk_tab:
# # # # # # # # # # # # #         sec("Risk Cascade Analysis")
# # # # # # # # # # # # #         risks = []
# # # # # # # # # # # # #         if snr["risk"] in ["CRITICAL", "WARNING"]:
# # # # # # # # # # # # #             risks.append({
# # # # # # # # # # # # #                 "icon": "⛔", "sev": 3, "color": "#EF4444", "bg": "#FEF2F2",
# # # # # # # # # # # # #                 "title": f"Finished Good at {snr['risk'].title()} Risk",
# # # # # # # # # # # # #                 "detail": (f"{snr['name']} has {round(snr['days_cover'])}d of cover. "
# # # # # # # # # # # # #                            f"SIH={round(snr['sih'])} vs SAP SS={round(snr['safety_stock'])}. "
# # # # # # # # # # # # #                            f"Production continuity at risk."),
# # # # # # # # # # # # #                 "action": f"Order {int(snr.get('repl_quantity', 0))} units immediately. Contact procurement today.",
# # # # # # # # # # # # #             })
# # # # # # # # # # # # #         if cn > 0:
# # # # # # # # # # # # #             risks.append({
# # # # # # # # # # # # #                 "icon": "⚠", "sev": 2, "color": "#F59E0B", "bg": "#FFFBEB",
# # # # # # # # # # # # #                 "title": f"Missing Supplier Data — {cn} External Components",
# # # # # # # # # # # # #                 "detail": (f"{cn} of {external_n} external components have no named supplier. "
# # # # # # # # # # # # #                            f"Single-source risk cannot be assessed for these."),
# # # # # # # # # # # # #                 "action": "Procurement to verify and update BOM with supplier names and lead times.",
# # # # # # # # # # # # #             })
# # # # # # # # # # # # #         if 0 < us <= 2:
# # # # # # # # # # # # #             risks.append({
# # # # # # # # # # # # #                 "icon": "⚠", "sev": 2, "color": "#F59E0B", "bg": "#FFFBEB",
# # # # # # # # # # # # #                 "title": f"Supplier Concentration — {us} Unique Supplier(s)",
# # # # # # # # # # # # #                 "detail": f"High dependency on {us} supplier(s). Any disruption cascades to multiple components simultaneously.",
# # # # # # # # # # # # #                 "action": "Evaluate dual-sourcing for critical external components.",
# # # # # # # # # # # # #             })
# # # # # # # # # # # # #         ext_comps = bsn[bsn["Procurement type"] == "F"]
# # # # # # # # # # # # #         if len(ext_comps) > 0:
# # # # # # # # # # # # #             locs = list(set([str(r) for r in bsn[bsn["Procurement type"] == "F"]["Supplier Location"].dropna().tolist()[:4]]))
# # # # # # # # # # # # #             risks.append({
# # # # # # # # # # # # #                 "icon": "🌍", "sev": 1, "color": "#3B82F6", "bg": "#EFF6FF",
# # # # # # # # # # # # #                 "title": f"External Procurement: {len(ext_comps)} Components",
# # # # # # # # # # # # #                 "detail": (f"External components depend on supplier availability and transit times. "
# # # # # # # # # # # # #                            f"Suppliers located in: {', '.join(locs)}."),
# # # # # # # # # # # # #                 "action": "Review external component lead times — stock buffers for long-transit items.",
# # # # # # # # # # # # #             })

# # # # # # # # # # # # #         if not risks:
# # # # # # # # # # # # #             st.markdown(
# # # # # # # # # # # # #                 "<div style='padding:10px 13px;background:var(--gbg);border:1px solid rgba(34,197,94,0.2);"
# # # # # # # # # # # # #                 "border-radius:var(--r);font-size:12px;color:#14532d;'>"
# # # # # # # # # # # # #                 "✓ No critical propagation risks identified.</div>",
# # # # # # # # # # # # #                 unsafe_allow_html=True,
# # # # # # # # # # # # #             )
# # # # # # # # # # # # #         else:
# # # # # # # # # # # # #             for r in sorted(risks, key=lambda x: -x["sev"]):
# # # # # # # # # # # # #                 st.markdown(
# # # # # # # # # # # # #                     f"<div style='background:{r['bg']};border:1px solid {r['color']}40;"
# # # # # # # # # # # # #                     f"border-left:4px solid {r['color']};border-radius:var(--r);"
# # # # # # # # # # # # #                     f"padding:12px 14px;margin-bottom:8px;'>"
# # # # # # # # # # # # #                     f"<div style='display:flex;align-items:center;gap:8px;margin-bottom:5px;'>"
# # # # # # # # # # # # #                     f"<span style='font-size:16px;'>{r['icon']}</span>"
# # # # # # # # # # # # #                     f"<div style='font-size:12px;font-weight:800;color:{r['color']};'>{r['title']}</div>"
# # # # # # # # # # # # #                     f"</div>"
# # # # # # # # # # # # #                     f"<div style='font-size:11px;color:var(--t2);margin-bottom:5px;'>{r['detail']}</div>"
# # # # # # # # # # # # #                     f"<div style='font-size:11px;color:{r['color']};font-weight:600;'>→ {r['action']}</div>"
# # # # # # # # # # # # #                     f"</div>",
# # # # # # # # # # # # #                     unsafe_allow_html=True,
# # # # # # # # # # # # #                 )

# # # # # # # # # # # # #         # Consolidation opportunities
# # # # # # # # # # # # #         consol2   = get_supplier_consolidation(data, summary)
# # # # # # # # # # # # #         relevant2 = consol2[
# # # # # # # # # # # # #             consol2.material_list.apply(lambda x: snid in x)
# # # # # # # # # # # # #             & (consol2.finished_goods_supplied > 1)
# # # # # # # # # # # # #             & consol2.consolidation_opportunity
# # # # # # # # # # # # #         ]
# # # # # # # # # # # # #         if len(relevant2) > 0:
# # # # # # # # # # # # #             sec("Supplier Consolidation Opportunities")
# # # # # # # # # # # # #             for _, r2 in relevant2.iterrows():
# # # # # # # # # # # # #                 others = [MATERIAL_LABELS.get(m, m)[:18] for m in r2["material_list"] if m != snid]
# # # # # # # # # # # # #                 st.markdown(
# # # # # # # # # # # # #                     f"<div class='prow'><div style='font-size:14px;'>🏭</div>"
# # # # # # # # # # # # #                     f"<div style='flex:1;'>"
# # # # # # # # # # # # #                     f"<div style='font-size:12px;font-weight:800;'>{r2['supplier']}</div>"
# # # # # # # # # # # # #                     f"<div style='font-size:10px;color:var(--t3);'>{r2['city']} · {r2['email']}</div>"
# # # # # # # # # # # # #                     f"<div style='font-size:10px;color:var(--t2);margin-top:2px;'>Also supplies: {', '.join(others[:3])}</div>"
# # # # # # # # # # # # #                     f"</div>"
# # # # # # # # # # # # #                     f"<div style='font-size:10px;font-weight:700;color:var(--or);'>⚡ Consolidate order</div>"
# # # # # # # # # # # # #                     f"</div>",
# # # # # # # # # # # # #                     unsafe_allow_html=True,
# # # # # # # # # # # # #                 )

# # # # # # # # # # # # #         # Free-form ARIA chat
# # # # # # # # # # # # #         if st.session_state.azure_client:
# # # # # # # # # # # # #             sec("Ask ARIA About This Network")
# # # # # # # # # # # # #             uq = st.text_input(
# # # # # # # # # # # # #                 "Question",
# # # # # # # # # # # # #                 placeholder="e.g. Which supplier poses the highest single-source risk?",
# # # # # # # # # # # # #                 key="snq", label_visibility="collapsed",
# # # # # # # # # # # # #             )
# # # # # # # # # # # # #             if uq and st.button("Ask ARIA", key="sna"):
# # # # # # # # # # # # #                 ctx3 = (
# # # # # # # # # # # # #                     f"Material: {snr['name']}, Risk: {snr['risk']}, Components: {tc}, "
# # # # # # # # # # # # #                     f"Inhouse: {inhouse_n}, External: {external_n}, Missing supplier: {cn}, "
# # # # # # # # # # # # #                     f"Unique suppliers: {us}, "
# # # # # # # # # # # # #                     f"Suppliers: {', '.join(bsn['Supplier Name(Vendor)'].dropna().unique().tolist()[:5])}"
# # # # # # # # # # # # #                 )
# # # # # # # # # # # # #                 with st.spinner("Thinking…"):
# # # # # # # # # # # # #                     ans = chat_with_data(st.session_state.azure_client, AZURE_DEPLOYMENT, uq, ctx3)
# # # # # # # # # # # # #                 st.markdown(
# # # # # # # # # # # # #                     f"<div class='ic' style='margin-top:8px;'><div class='il'>◈ ARIA</div>"
# # # # # # # # # # # # #                     f"<div class='ib'>{ans}</div></div>",
# # # # # # # # # # # # #                     unsafe_allow_html=True,
# # # # # # # # # # # # #                 )

# # # # # # # # # # # # #     st.markdown('<div class="pfooter">🕸️ Powered by <strong>MResult</strong></div>', unsafe_allow_html=True)

# # # # # # # # # # # # """
# # # # # # # # # # # # tabs/supply_network.py
# # # # # # # # # # # # Supply Network tab: BOM propagation map (colour-coded by risk/supplier type),
# # # # # # # # # # # # component detail table, risk cascade analysis, and supplier consolidation opportunities.
# # # # # # # # # # # # """

# # # # # # # # # # # # import streamlit as st
# # # # # # # # # # # # import pandas as pd

# # # # # # # # # # # # from st_aggrid import AgGrid, GridOptionsBuilder, JsCode

# # # # # # # # # # # # from utils.helpers import sec, note, sbadge, plot_bom_tree, ORANGE, AZURE_DEPLOYMENT
# # # # # # # # # # # # from data_loader import get_bom_components, get_supplier_consolidation
# # # # # # # # # # # # from agent import interpret_chart, chat_with_data

# # # # # # # # # # # # _AGGRID_CSS = {
# # # # # # # # # # # #     ".ag-root-wrapper": {"border": "1px solid #E2E8F0!important", "border-radius": "12px!important"},
# # # # # # # # # # # #     ".ag-header":       {"background": "#F8FAFE!important"},
# # # # # # # # # # # #     ".ag-row-even":     {"background": "#FFFFFF!important"},
# # # # # # # # # # # #     ".ag-row-odd":      {"background": "#F8FAFE!important"},
# # # # # # # # # # # # }


# # # # # # # # # # # # def render():
# # # # # # # # # # # #     data            = st.session_state.data
# # # # # # # # # # # #     summary         = st.session_state.summary
# # # # # # # # # # # #     MATERIAL_LABELS = st.session_state.material_labels

# # # # # # # # # # # #     st.markdown(
# # # # # # # # # # # #         "<div style='font-size:15px;font-weight:800;margin-bottom:4px;'>Supply Network</div>"
# # # # # # # # # # # #         "<div style='font-size:12px;color:var(--t3);margin-bottom:14px;'>"
# # # # # # # # # # # #         "BOM structure · Supplier locations · Risk cascade · Consolidation intelligence</div>",
# # # # # # # # # # # #         unsafe_allow_html=True,
# # # # # # # # # # # #     )

# # # # # # # # # # # #     snn  = st.selectbox("Finished Good", [r["name"] for _, r in summary.iterrows()], key="snm")
# # # # # # # # # # # #     snid = summary[summary.name == snn]["material"].values[0]
# # # # # # # # # # # #     snr  = summary[summary.material == snid].iloc[0]
# # # # # # # # # # # #     bsn  = get_bom_components(data, snid)

# # # # # # # # # # # #     if not len(bsn):
# # # # # # # # # # # #         st.markdown(
# # # # # # # # # # # #             "<div class='flag-box'><div style='font-size:22px;margin-bottom:8px;'>🕸️</div>"
# # # # # # # # # # # #             "<div style='font-size:14px;font-weight:800;color:var(--t2);'>No BOM data for this material</div></div>",
# # # # # # # # # # # #             unsafe_allow_html=True,
# # # # # # # # # # # #         )
# # # # # # # # # # # #         return

# # # # # # # # # # # #     cw        = int(bsn["Supplier Name(Vendor)"].notna().sum())
# # # # # # # # # # # #     cn        = len(bsn[bsn["Supplier Display"].str.startswith("⚠", na=False)])
# # # # # # # # # # # #     us        = int(bsn["Supplier Name(Vendor)"].dropna().nunique())
# # # # # # # # # # # #     tc        = len(bsn)
# # # # # # # # # # # #     inhouse_n = int((bsn["Procurement type"] == "E").sum())
# # # # # # # # # # # #     external_n = int((bsn["Procurement type"] == "F").sum())

# # # # # # # # # # # #     n1, n2, n3, n4 = st.columns(4)
# # # # # # # # # # # #     for col, val, lbl, vc in [
# # # # # # # # # # # #         (n1, tc,        "Total Components",  "#1E293B"),
# # # # # # # # # # # #         (n2, inhouse_n, "Revvity Inhouse",   "#22C55E"),
# # # # # # # # # # # #         (n3, cn,        "Missing Supplier",  "#F59E0B" if cn > 0 else "#1E293B"),
# # # # # # # # # # # #         (n4, us,        "Unique Ext Suppliers", "#1E293B"),
# # # # # # # # # # # #     ]:
# # # # # # # # # # # #         with col:
# # # # # # # # # # # #             st.markdown(
# # # # # # # # # # # #                 f"<div class='sc'><div style='flex:1;'>"
# # # # # # # # # # # #                 f"<div class='sv' style='color:{vc};'>{val}</div>"
# # # # # # # # # # # #                 f"<div class='sl'>{lbl}</div></div></div>",
# # # # # # # # # # # #                 unsafe_allow_html=True,
# # # # # # # # # # # #             )

# # # # # # # # # # # #     sn_tab, comp_tab, risk_tab = st.tabs(["🕸️  BOM Map", "📋  Components", "⚠️  Risk Analysis"])

# # # # # # # # # # # #     # ── BOM Map (colour‑coded knowledge graph) ─────────────────────────────────
# # # # # # # # # # # #     with sn_tab:
# # # # # # # # # # # #         sec("BOM Propagation Map")
# # # # # # # # # # # #         note("""
# # # # # # # # # # # #         **Colour legend:**  
# # # # # # # # # # # #         - 🟢 **Green** = Inhouse component (Revvity)  
# # # # # # # # # # # #         - 🔵 **Blue** = External component with named supplier  
# # # # # # # # # # # #         - 🟡 **Amber** = External component with **missing supplier data**  
# # # # # # # # # # # #         - 🟣 **Purple** = Supplier node  
# # # # # # # # # # # #         - Root node colour matches finished good risk (🔴 Critical / 🟠 Warning / 🟢 Healthy)  
# # # # # # # # # # # #         Hover over any node for details.
# # # # # # # # # # # #         """)
# # # # # # # # # # # #         risk_color_map = {"CRITICAL": "#EF4444", "WARNING": "#F59E0B", "HEALTHY": "#22C55E"}
# # # # # # # # # # # #         root_color     = risk_color_map.get(snr["risk"], "#94A3B8")
# # # # # # # # # # # #         fig_tree       = plot_bom_tree(bsn, snr["name"], root_color)
# # # # # # # # # # # #         st.plotly_chart(fig_tree, use_container_width=True)

# # # # # # # # # # # #         if st.session_state.azure_client:
# # # # # # # # # # # #             if st.button("◈ Interpret BOM Map", key="interp_bom_tree"):
# # # # # # # # # # # #                 with st.spinner("ARIA interpreting…"):
# # # # # # # # # # # #                     bom_ctx = {
# # # # # # # # # # # #                         "material": snr["name"], "total_components": tc,
# # # # # # # # # # # #                         "inhouse": inhouse_n, "external_named": cw - inhouse_n,
# # # # # # # # # # # #                         "missing_supplier": cn, "unique_suppliers": us, "risk": snr["risk"],
# # # # # # # # # # # #                     }
# # # # # # # # # # # #                     interp = interpret_chart(
# # # # # # # # # # # #                         st.session_state.azure_client, AZURE_DEPLOYMENT,
# # # # # # # # # # # #                         "BOM Risk Propagation Map", bom_ctx,
# # # # # # # # # # # #                         "What are the key supply chain risks in this BOM and what should procurement prioritise?",
# # # # # # # # # # # #                     )
# # # # # # # # # # # #                 st.markdown(
# # # # # # # # # # # #                     f"<div class='ic' style='margin-top:8px;'><div class='il'>◈ ARIA</div>"
# # # # # # # # # # # #                     f"<div class='ib'>{interp}</div></div>",
# # # # # # # # # # # #                     unsafe_allow_html=True,
# # # # # # # # # # # #                 )

# # # # # # # # # # # #     # ── Component Detail ──────────────────────────────────────────────────────
# # # # # # # # # # # #     with comp_tab:
# # # # # # # # # # # #         sec("Component Detail")
# # # # # # # # # # # #         bom_display2 = []
# # # # # # # # # # # #         for _, b in bsn.iterrows():
# # # # # # # # # # # #             eff_qty = b.get("Effective Order Qty", b["Comp. Qty (CUn)"])
# # # # # # # # # # # #             fq_txt  = ("1 (Fixed)" if b.get("Fixed Qty Flag", False)
# # # # # # # # # # # #                        else str(round(float(eff_qty), 3)) if pd.notna(eff_qty) else "—")
# # # # # # # # # # # #             bom_display2.append({
# # # # # # # # # # # #                 "Material":    str(b["Material"]),
# # # # # # # # # # # #                 "Description": str(b["Material Description"])[:36] if pd.notna(b["Material Description"]) else "—",
# # # # # # # # # # # #                 "Level":       str(b["Level"])[:25] if pd.notna(b["Level"]) else "—",
# # # # # # # # # # # #                 "Qty":         fq_txt,
# # # # # # # # # # # #                 "Unit":        str(b["Component unit"]) if pd.notna(b["Component unit"]) else "—",
# # # # # # # # # # # #                 "Type":        b.get("Procurement Label", "—"),
# # # # # # # # # # # #                 "Supplier":    b.get("Supplier Display", "—"),
# # # # # # # # # # # #                 "Location":    b.get("Supplier Location", "—"),
# # # # # # # # # # # #                 "Transit":     f"{b.get('Transit Days', '—')}d" if b.get("Transit Days") is not None else "—",
# # # # # # # # # # # #             })
# # # # # # # # # # # #         df_bd2  = pd.DataFrame(bom_display2)
# # # # # # # # # # # #         sup_r3  = JsCode("""class R{init(p){const v=p.value||'';this.e=document.createElement('span');if(v.startsWith('⚠')){this.e.style.cssText='background:#FEF3C7;color:#F59E0B;padding:2px 6px;border-radius:4px;font-size:10px;font-weight:600;';this.e.innerText=v;}else if(v==='Revvity Inhouse'){this.e.style.cssText='background:#DCFCE7;color:#16a34a;padding:2px 6px;border-radius:4px;font-size:10px;font-weight:600;';this.e.innerText='🏭 '+v;}else{this.e.style.cssText='background:#EFF6FF;color:#2563EB;padding:2px 6px;border-radius:4px;font-size:10px;';this.e.innerText='🚚 '+v;};}getGui(){return this.e;}}""")
# # # # # # # # # # # #         gb4     = GridOptionsBuilder.from_dataframe(df_bd2)
# # # # # # # # # # # #         gb4.configure_column("Material",    width=82)
# # # # # # # # # # # #         gb4.configure_column("Description", width=215)
# # # # # # # # # # # #         gb4.configure_column("Level",       width=85)
# # # # # # # # # # # #         gb4.configure_column("Qty",         width=75)
# # # # # # # # # # # #         gb4.configure_column("Unit",        width=50)
# # # # # # # # # # # #         gb4.configure_column("Type",        width=100)
# # # # # # # # # # # #         gb4.configure_column("Supplier",    width=170, cellRenderer=sup_r3)
# # # # # # # # # # # #         gb4.configure_column("Location",    width=130)
# # # # # # # # # # # #         gb4.configure_column("Transit",     width=58)
# # # # # # # # # # # #         gb4.configure_grid_options(rowHeight=36, headerHeight=32)
# # # # # # # # # # # #         gb4.configure_default_column(resizable=True, sortable=True, filter=False)
# # # # # # # # # # # #         AgGrid(df_bd2, gridOptions=gb4.build(), height=320,
# # # # # # # # # # # #                allow_unsafe_jscode=True, theme="alpine", custom_css=_AGGRID_CSS)

# # # # # # # # # # # #     # ── Risk Cascade ──────────────────────────────────────────────────────────
# # # # # # # # # # # #     with risk_tab:
# # # # # # # # # # # #         sec("Risk Cascade Analysis")
# # # # # # # # # # # #         risks = []
# # # # # # # # # # # #         if snr["risk"] in ["CRITICAL", "WARNING"]:
# # # # # # # # # # # #             risks.append({
# # # # # # # # # # # #                 "icon": "⛔", "sev": 3, "color": "#EF4444", "bg": "#FEF2F2",
# # # # # # # # # # # #                 "title": f"Finished Good at {snr['risk'].title()} Risk",
# # # # # # # # # # # #                 "detail": (f"{snr['name']} has {round(snr['days_cover'])}d of cover. "
# # # # # # # # # # # #                            f"SIH={round(snr['sih'])} vs SAP SS={round(snr['safety_stock'])}. "
# # # # # # # # # # # #                            f"Production continuity at risk."),
# # # # # # # # # # # #                 "action": f"Order {int(snr.get('repl_quantity', 0))} units immediately. Contact procurement today.",
# # # # # # # # # # # #             })
# # # # # # # # # # # #         if cn > 0:
# # # # # # # # # # # #             risks.append({
# # # # # # # # # # # #                 "icon": "⚠", "sev": 2, "color": "#F59E0B", "bg": "#FFFBEB",
# # # # # # # # # # # #                 "title": f"Missing Supplier Data — {cn} External Components",
# # # # # # # # # # # #                 "detail": (f"{cn} of {external_n} external components have no named supplier. "
# # # # # # # # # # # #                            f"Single-source risk cannot be assessed for these."),
# # # # # # # # # # # #                 "action": "Procurement to verify and update BOM with supplier names and lead times.",
# # # # # # # # # # # #             })
# # # # # # # # # # # #         if 0 < us <= 2:
# # # # # # # # # # # #             risks.append({
# # # # # # # # # # # #                 "icon": "⚠", "sev": 2, "color": "#F59E0B", "bg": "#FFFBEB",
# # # # # # # # # # # #                 "title": f"Supplier Concentration — {us} Unique Supplier(s)",
# # # # # # # # # # # #                 "detail": f"High dependency on {us} supplier(s). Any disruption cascades to multiple components simultaneously.",
# # # # # # # # # # # #                 "action": "Evaluate dual-sourcing for critical external components.",
# # # # # # # # # # # #             })
# # # # # # # # # # # #         ext_comps = bsn[bsn["Procurement type"] == "F"]
# # # # # # # # # # # #         if len(ext_comps) > 0:
# # # # # # # # # # # #             locs = list(set([str(r) for r in bsn[bsn["Procurement type"] == "F"]["Supplier Location"].dropna().tolist()[:4]]))
# # # # # # # # # # # #             risks.append({
# # # # # # # # # # # #                 "icon": "🌍", "sev": 1, "color": "#3B82F6", "bg": "#EFF6FF",
# # # # # # # # # # # #                 "title": f"External Procurement: {len(ext_comps)} Components",
# # # # # # # # # # # #                 "detail": (f"External components depend on supplier availability and transit times. "
# # # # # # # # # # # #                            f"Suppliers located in: {', '.join(locs)}."),
# # # # # # # # # # # #                 "action": "Review external component lead times — stock buffers for long-transit items.",
# # # # # # # # # # # #             })

# # # # # # # # # # # #         if not risks:
# # # # # # # # # # # #             st.markdown(
# # # # # # # # # # # #                 "<div style='padding:10px 13px;background:var(--gbg);border:1px solid rgba(34,197,94,0.2);"
# # # # # # # # # # # #                 "border-radius:var(--r);font-size:12px;color:#14532d;'>"
# # # # # # # # # # # #                 "✓ No critical propagation risks identified.</div>",
# # # # # # # # # # # #                 unsafe_allow_html=True,
# # # # # # # # # # # #             )
# # # # # # # # # # # #         else:
# # # # # # # # # # # #             for r in sorted(risks, key=lambda x: -x["sev"]):
# # # # # # # # # # # #                 st.markdown(
# # # # # # # # # # # #                     f"<div style='background:{r['bg']};border:1px solid {r['color']}40;"
# # # # # # # # # # # #                     f"border-left:4px solid {r['color']};border-radius:var(--r);"
# # # # # # # # # # # #                     f"padding:12px 14px;margin-bottom:8px;'>"
# # # # # # # # # # # #                     f"<div style='display:flex;align-items:center;gap:8px;margin-bottom:5px;'>"
# # # # # # # # # # # #                     f"<span style='font-size:16px;'>{r['icon']}</span>"
# # # # # # # # # # # #                     f"<div style='font-size:12px;font-weight:800;color:{r['color']};'>{r['title']}</div>"
# # # # # # # # # # # #                     f"</div>"
# # # # # # # # # # # #                     f"<div style='font-size:11px;color:var(--t2);margin-bottom:5px;'>{r['detail']}</div>"
# # # # # # # # # # # #                     f"<div style='font-size:11px;color:{r['color']};font-weight:600;'>→ {r['action']}</div>"
# # # # # # # # # # # #                     f"</div>",
# # # # # # # # # # # #                     unsafe_allow_html=True,
# # # # # # # # # # # #                 )

# # # # # # # # # # # #         # Consolidation opportunities
# # # # # # # # # # # #         consol2   = get_supplier_consolidation(data, summary)
# # # # # # # # # # # #         relevant2 = consol2[
# # # # # # # # # # # #             consol2.material_list.apply(lambda x: snid in x)
# # # # # # # # # # # #             & (consol2.finished_goods_supplied > 1)
# # # # # # # # # # # #             & consol2.consolidation_opportunity
# # # # # # # # # # # #         ]
# # # # # # # # # # # #         if len(relevant2) > 0:
# # # # # # # # # # # #             sec("Supplier Consolidation Opportunities")
# # # # # # # # # # # #             for _, r2 in relevant2.iterrows():
# # # # # # # # # # # #                 others = [MATERIAL_LABELS.get(m, m)[:18] for m in r2["material_list"] if m != snid]
# # # # # # # # # # # #                 st.markdown(
# # # # # # # # # # # #                     f"<div class='prow'><div style='font-size:14px;'>🏭</div>"
# # # # # # # # # # # #                     f"<div style='flex:1;'>"
# # # # # # # # # # # #                     f"<div style='font-size:12px;font-weight:800;'>{r2['supplier']}</div>"
# # # # # # # # # # # #                     f"<div style='font-size:10px;color:var(--t3);'>{r2['city']} · {r2['email']}</div>"
# # # # # # # # # # # #                     f"<div style='font-size:10px;color:var(--t2);margin-top:2px;'>Also supplies: {', '.join(others[:3])}</div>"
# # # # # # # # # # # #                     f"</div>"
# # # # # # # # # # # #                     f"<div style='font-size:10px;font-weight:700;color:var(--or);'>⚡ Consolidate order</div>"
# # # # # # # # # # # #                     f"</div>",
# # # # # # # # # # # #                     unsafe_allow_html=True,
# # # # # # # # # # # #                 )

# # # # # # # # # # # #         # ── Ask ARIA with rich BOM context ────────────────────────────────────
# # # # # # # # # # # #         if st.session_state.azure_client:
# # # # # # # # # # # #             sec("Ask ARIA About This Network")
# # # # # # # # # # # #             uq = st.text_input(
# # # # # # # # # # # #                 "Question",
# # # # # # # # # # # #                 placeholder="e.g. Which supplier provides more than 1 material for DELFIA Wash Concentrate?",
# # # # # # # # # # # #                 key="snq", label_visibility="collapsed",
# # # # # # # # # # # #             )
# # # # # # # # # # # #             if uq and st.button("Ask ARIA", key="sna"):
# # # # # # # # # # # #                 # Build a detailed BOM table as context
# # # # # # # # # # # #                 bom_lines = []
# # # # # # # # # # # #                 for _, row in bsn.iterrows():
# # # # # # # # # # # #                     mat_desc = str(row["Material Description"])[:40] if pd.notna(row["Material Description"]) else str(row["Material"])
# # # # # # # # # # # #                     qty = row["Effective Order Qty"] if "Effective Order Qty" in row else row["Comp. Qty (CUn)"]
# # # # # # # # # # # #                     fixed = "X (order exactly 1)" if row.get("Fixed Qty Flag") else ""
# # # # # # # # # # # #                     sup = row.get("Supplier Display", "—")
# # # # # # # # # # # #                     loc = row.get("Supplier Location", "—")
# # # # # # # # # # # #                     transit = row.get("Transit Days", "—")
# # # # # # # # # # # #                     reliability = row.get("Supplier Reliability", "—")
# # # # # # # # # # # #                     bom_lines.append(f"- Component: {mat_desc} | Qty: {qty} {fixed} | Supplier: {sup} | Location: {loc} | Transit: {transit}d | Reliability: {reliability}")
# # # # # # # # # # # #                 bom_table = "\n".join(bom_lines)

# # # # # # # # # # # #                 ctx3 = (
# # # # # # # # # # # #                     f"Material: {snr['name']} (ID: {snid})\n"
# # # # # # # # # # # #                     f"Risk: {snr['risk']}\n"
# # # # # # # # # # # #                     f"Total components: {tc}\n"
# # # # # # # # # # # #                     f"Inhouse components: {inhouse_n}\n"
# # # # # # # # # # # #                     f"External components: {external_n}\n"
# # # # # # # # # # # #                     f"Missing supplier data: {cn} components\n"
# # # # # # # # # # # #                     f"Unique external suppliers: {us}\n"
# # # # # # # # # # # #                     f"BOM details:\n{bom_table}"
# # # # # # # # # # # #                 )
# # # # # # # # # # # #                 with st.spinner("Thinking…"):
# # # # # # # # # # # #                     ans = chat_with_data(st.session_state.azure_client, AZURE_DEPLOYMENT, uq, ctx3)
# # # # # # # # # # # #                 st.markdown(
# # # # # # # # # # # #                     f"<div class='ic' style='margin-top:8px;'><div class='il'>◈ ARIA</div>"
# # # # # # # # # # # #                     f"<div class='ib'>{ans}</div></div>",
# # # # # # # # # # # #                     unsafe_allow_html=True,
# # # # # # # # # # # #                 )

# # # # # # # # # # # #     st.markdown('<div class="pfooter">🕸️ Powered by <strong>MResult</strong></div>', unsafe_allow_html=True)

# # # # # # # # # # # """
# # # # # # # # # # # tabs/supply_network.py
# # # # # # # # # # # Supply Network tab: BOM propagation map (Sankey diagram), component detail table,
# # # # # # # # # # # risk cascade analysis, and supplier consolidation opportunities.
# # # # # # # # # # # """

# # # # # # # # # # # import streamlit as st
# # # # # # # # # # # import pandas as pd
# # # # # # # # # # # import plotly.graph_objects as go

# # # # # # # # # # # from st_aggrid import AgGrid, GridOptionsBuilder, JsCode

# # # # # # # # # # # from utils.helpers import sec, note, sbadge, ORANGE, AZURE_DEPLOYMENT
# # # # # # # # # # # from data_loader import get_bom_components, get_supplier_consolidation
# # # # # # # # # # # from agent import interpret_chart, chat_with_data

# # # # # # # # # # # _AGGRID_CSS = {
# # # # # # # # # # #     ".ag-root-wrapper": {"border": "1px solid #E2E8F0!important", "border-radius": "12px!important"},
# # # # # # # # # # #     ".ag-header":       {"background": "#F8FAFE!important"},
# # # # # # # # # # #     ".ag-row-even":     {"background": "#FFFFFF!important"},
# # # # # # # # # # #     ".ag-row-odd":      {"background": "#F8FAFE!important"},
# # # # # # # # # # # }


# # # # # # # # # # # def render():
# # # # # # # # # # #     data            = st.session_state.data
# # # # # # # # # # #     summary         = st.session_state.summary
# # # # # # # # # # #     MATERIAL_LABELS = st.session_state.material_labels

# # # # # # # # # # #     st.markdown(
# # # # # # # # # # #         "<div style='font-size:15px;font-weight:800;margin-bottom:4px;'>Supply Network</div>"
# # # # # # # # # # #         "<div style='font-size:12px;color:var(--t3);margin-bottom:14px;'>"
# # # # # # # # # # #         "BOM structure · Supplier locations · Risk cascade · Consolidation intelligence</div>",
# # # # # # # # # # #         unsafe_allow_html=True,
# # # # # # # # # # #     )

# # # # # # # # # # #     snn  = st.selectbox("Finished Good", [r["name"] for _, r in summary.iterrows()], key="snm")
# # # # # # # # # # #     snid = summary[summary.name == snn]["material"].values[0]
# # # # # # # # # # #     snr  = summary[summary.material == snid].iloc[0]
# # # # # # # # # # #     bsn  = get_bom_components(data, snid)

# # # # # # # # # # #     if not len(bsn):
# # # # # # # # # # #         st.markdown(
# # # # # # # # # # #             "<div class='flag-box'><div style='font-size:22px;margin-bottom:8px;'>🕸️</div>"
# # # # # # # # # # #             "<div style='font-size:14px;font-weight:800;color:var(--t2);'>No BOM data for this material</div></div>",
# # # # # # # # # # #             unsafe_allow_html=True,
# # # # # # # # # # #         )
# # # # # # # # # # #         return

# # # # # # # # # # #     cw        = int(bsn["Supplier Name(Vendor)"].notna().sum())
# # # # # # # # # # #     cn        = len(bsn[bsn["Supplier Display"].str.startswith("⚠", na=False)])
# # # # # # # # # # #     us        = int(bsn["Supplier Name(Vendor)"].dropna().nunique())
# # # # # # # # # # #     tc        = len(bsn)
# # # # # # # # # # #     inhouse_n = int((bsn["Procurement type"] == "E").sum())
# # # # # # # # # # #     external_n = int((bsn["Procurement type"] == "F").sum())

# # # # # # # # # # #     n1, n2, n3, n4 = st.columns(4)
# # # # # # # # # # #     for col, val, lbl, vc in [
# # # # # # # # # # #         (n1, tc,        "Total Components",  "#1E293B"),
# # # # # # # # # # #         (n2, inhouse_n, "Revvity Inhouse",   "#22C55E"),
# # # # # # # # # # #         (n3, cn,        "Missing Supplier",  "#F59E0B" if cn > 0 else "#1E293B"),
# # # # # # # # # # #         (n4, us,        "Unique Ext Suppliers", "#1E293B"),
# # # # # # # # # # #     ]:
# # # # # # # # # # #         with col:
# # # # # # # # # # #             st.markdown(
# # # # # # # # # # #                 f"<div class='sc'><div style='flex:1;'>"
# # # # # # # # # # #                 f"<div class='sv' style='color:{vc};'>{val}</div>"
# # # # # # # # # # #                 f"<div class='sl'>{lbl}</div></div></div>",
# # # # # # # # # # #                 unsafe_allow_html=True,
# # # # # # # # # # #             )

# # # # # # # # # # #     sn_tab, comp_tab, risk_tab = st.tabs(["🕸️  BOM Map", "📋  Components", "⚠️  Risk Analysis"])

# # # # # # # # # # #     # ── BOM Map – Sankey diagram (replaces tree) ──────────────────────────────
# # # # # # # # # # #     with sn_tab:
# # # # # # # # # # #         sec("BOM Propagation Map")
# # # # # # # # # # #         note("""
# # # # # # # # # # #         **Colour legend:**  
# # # # # # # # # # #         - 🔵 **Blue** = External component with named supplier  
# # # # # # # # # # #         - 🟢 **Green** = Inhouse component (Revvity)  
# # # # # # # # # # #         - 🟡 **Amber** = External component with **missing supplier data**  
# # # # # # # # # # #         - 🟣 **Purple** = Supplier node  
# # # # # # # # # # #         - Root node colour matches finished good risk (🔴 Critical / 🟠 Warning / 🟢 Healthy)  
# # # # # # # # # # #         Hover over nodes for details.
# # # # # # # # # # #         """)

# # # # # # # # # # #         # Build node list and links for Sankey
# # # # # # # # # # #         nodes = []
# # # # # # # # # # #         node_colors = []
# # # # # # # # # # #         node_map = {}

# # # # # # # # # # #         # Root node (finished good)
# # # # # # # # # # #         root_name = snr["name"]
# # # # # # # # # # #         root_risk_color = {"CRITICAL": "#EF4444", "WARNING": "#F59E0B", "HEALTHY": "#22C55E"}.get(snr["risk"], "#94A3B8")
# # # # # # # # # # #         nodes.append(root_name)
# # # # # # # # # # #         node_colors.append(root_risk_color)
# # # # # # # # # # #         node_map[root_name] = 0

# # # # # # # # # # #         sources = []
# # # # # # # # # # #         targets = []
# # # # # # # # # # #         values = []

# # # # # # # # # # #         # Process each BOM row
# # # # # # # # # # #         for _, row in bsn.iterrows():
# # # # # # # # # # #             comp_desc = str(row["Material Description"])[:40] if pd.notna(row["Material Description"]) else str(row["Material"])
# # # # # # # # # # #             comp_label = f"[C] {comp_desc}"
# # # # # # # # # # #             sup_display = row.get("Supplier Display", "—")
# # # # # # # # # # #             proc_type = str(row.get("Procurement type", "")).strip()
# # # # # # # # # # #             qty = row.get("Effective Order Qty", row["Comp. Qty (CUn)"]) if pd.notna(row.get("Effective Order Qty", row["Comp. Qty (CUn)"]) ) else 1
# # # # # # # # # # #             # Ensure qty is numeric
# # # # # # # # # # #             try:
# # # # # # # # # # #                 qty = float(qty)
# # # # # # # # # # #             except:
# # # # # # # # # # #                 qty = 1.0

# # # # # # # # # # #             # Add component node if not already present
# # # # # # # # # # #             if comp_label not in node_map:
# # # # # # # # # # #                 # Determine component colour
# # # # # # # # # # #                 if proc_type == "E":
# # # # # # # # # # #                     comp_color = "#22C55E"   # Inhouse
# # # # # # # # # # #                 elif sup_display.startswith("⚠"):
# # # # # # # # # # #                     comp_color = "#F59E0B"   # Missing supplier
# # # # # # # # # # #                 else:
# # # # # # # # # # #                     comp_color = "#3B82F6"   # External named
# # # # # # # # # # #                 nodes.append(comp_label)
# # # # # # # # # # #                 node_colors.append(comp_color)
# # # # # # # # # # #                 node_map[comp_label] = len(nodes) - 1

# # # # # # # # # # #             # Link root -> component
# # # # # # # # # # #             sources.append(node_map[root_name])
# # # # # # # # # # #             targets.append(node_map[comp_label])
# # # # # # # # # # #             values.append(qty)

# # # # # # # # # # #             # Add supplier node if external and named
# # # # # # # # # # #             if sup_display not in ["Revvity Inhouse", "—"] and not sup_display.startswith("⚠"):
# # # # # # # # # # #                 sup_label = f"[S] {sup_display[:25]}"
# # # # # # # # # # #                 if sup_label not in node_map:
# # # # # # # # # # #                     nodes.append(sup_label)
# # # # # # # # # # #                     node_colors.append("#8B5CF6")  # Purple for suppliers
# # # # # # # # # # #                     node_map[sup_label] = len(nodes) - 1
# # # # # # # # # # #                 # Link component -> supplier
# # # # # # # # # # #                 sources.append(node_map[comp_label])
# # # # # # # # # # #                 targets.append(node_map[sup_label])
# # # # # # # # # # #                 values.append(1.0)  # connection weight

# # # # # # # # # # #         # Build Sankey figure
# # # # # # # # # # #         fig_sankey = go.Figure(data=[go.Sankey(
# # # # # # # # # # #             arrangement="snap",
# # # # # # # # # # #             node=dict(
# # # # # # # # # # #                 pad=20,
# # # # # # # # # # #                 thickness=20,
# # # # # # # # # # #                 line=dict(color="white", width=0.5),
# # # # # # # # # # #                 label=nodes,
# # # # # # # # # # #                 color=node_colors,
# # # # # # # # # # #                 hovertemplate="<b>%{label}</b><extra></extra>"
# # # # # # # # # # #             ),
# # # # # # # # # # #             link=dict(
# # # # # # # # # # #                 source=sources,
# # # # # # # # # # #                 target=targets,
# # # # # # # # # # #                 value=values,
# # # # # # # # # # #                 color="rgba(200,200,200,0.3)"
# # # # # # # # # # #             )
# # # # # # # # # # #         )])
# # # # # # # # # # #         fig_sankey.update_layout(
# # # # # # # # # # #             title=None,
# # # # # # # # # # #             font=dict(size=11, family="Inter"),
# # # # # # # # # # #             height=500,
# # # # # # # # # # #             margin=dict(l=20, r=20, t=20, b=20),
# # # # # # # # # # #             paper_bgcolor="white",
# # # # # # # # # # #         )
# # # # # # # # # # #         st.plotly_chart(fig_sankey, use_container_width=True)

# # # # # # # # # # #         if st.session_state.azure_client:
# # # # # # # # # # #             if st.button("◈ Interpret BOM Map", key="interp_bom_sankey"):
# # # # # # # # # # #                 with st.spinner("ARIA interpreting…"):
# # # # # # # # # # #                     bom_ctx = {
# # # # # # # # # # #                         "material": snr["name"], "total_components": tc,
# # # # # # # # # # #                         "inhouse": inhouse_n, "external_named": cw - inhouse_n,
# # # # # # # # # # #                         "missing_supplier": cn, "unique_suppliers": us, "risk": snr["risk"],
# # # # # # # # # # #                     }
# # # # # # # # # # #                     interp = interpret_chart(
# # # # # # # # # # #                         st.session_state.azure_client, AZURE_DEPLOYMENT,
# # # # # # # # # # #                         "BOM Risk Propagation Map", bom_ctx,
# # # # # # # # # # #                         "What are the key supply chain risks in this BOM and what should procurement prioritise?",
# # # # # # # # # # #                     )
# # # # # # # # # # #                 st.markdown(
# # # # # # # # # # #                     f"<div class='ic' style='margin-top:8px;'><div class='il'>◈ ARIA</div>"
# # # # # # # # # # #                     f"<div class='ib'>{interp}</div></div>",
# # # # # # # # # # #                     unsafe_allow_html=True,
# # # # # # # # # # #                 )

# # # # # # # # # # #     # ── Component Detail (unchanged) ─────────────────────────────────────────
# # # # # # # # # # #     with comp_tab:
# # # # # # # # # # #         sec("Component Detail")
# # # # # # # # # # #         bom_display2 = []
# # # # # # # # # # #         for _, b in bsn.iterrows():
# # # # # # # # # # #             eff_qty = b.get("Effective Order Qty", b["Comp. Qty (CUn)"])
# # # # # # # # # # #             fq_txt  = ("1 (Fixed)" if b.get("Fixed Qty Flag", False)
# # # # # # # # # # #                        else str(round(float(eff_qty), 3)) if pd.notna(eff_qty) else "—")
# # # # # # # # # # #             bom_display2.append({
# # # # # # # # # # #                 "Material":    str(b["Material"]),
# # # # # # # # # # #                 "Description": str(b["Material Description"])[:36] if pd.notna(b["Material Description"]) else "—",
# # # # # # # # # # #                 "Level":       str(b["Level"])[:25] if pd.notna(b["Level"]) else "—",
# # # # # # # # # # #                 "Qty":         fq_txt,
# # # # # # # # # # #                 "Unit":        str(b["Component unit"]) if pd.notna(b["Component unit"]) else "—",
# # # # # # # # # # #                 "Type":        b.get("Procurement Label", "—"),
# # # # # # # # # # #                 "Supplier":    b.get("Supplier Display", "—"),
# # # # # # # # # # #                 "Location":    b.get("Supplier Location", "—"),
# # # # # # # # # # #                 "Transit":     f"{b.get('Transit Days', '—')}d" if b.get("Transit Days") is not None else "—",
# # # # # # # # # # #                 "Std Price":   f"${b.get('Standard Price', 0):.2f}" if pd.notna(b.get('Standard Price')) else "—",
# # # # # # # # # # #             })
# # # # # # # # # # #         df_bd2  = pd.DataFrame(bom_display2)
# # # # # # # # # # #         sup_r3  = JsCode("""class R{init(p){const v=p.value||'';this.e=document.createElement('span');if(v.startsWith('⚠')){this.e.style.cssText='background:#FEF3C7;color:#F59E0B;padding:2px 6px;border-radius:4px;font-size:10px;font-weight:600;';this.e.innerText=v;}else if(v==='Revvity Inhouse'){this.e.style.cssText='background:#DCFCE7;color:#16a34a;padding:2px 6px;border-radius:4px;font-size:10px;font-weight:600;';this.e.innerText='🏭 '+v;}else{this.e.style.cssText='background:#EFF6FF;color:#2563EB;padding:2px 6px;border-radius:4px;font-size:10px;';this.e.innerText='🚚 '+v;};}getGui(){return this.e;}}""")
# # # # # # # # # # #         gb4     = GridOptionsBuilder.from_dataframe(df_bd2)
# # # # # # # # # # #         gb4.configure_column("Material",    width=82)
# # # # # # # # # # #         gb4.configure_column("Description", width=215)
# # # # # # # # # # #         gb4.configure_column("Level",       width=85)
# # # # # # # # # # #         gb4.configure_column("Qty",         width=75)
# # # # # # # # # # #         gb4.configure_column("Unit",        width=50)
# # # # # # # # # # #         gb4.configure_column("Type",        width=100)
# # # # # # # # # # #         gb4.configure_column("Supplier",    width=170, cellRenderer=sup_r3)
# # # # # # # # # # #         gb4.configure_column("Location",    width=130)
# # # # # # # # # # #         gb4.configure_column("Transit",     width=58)
# # # # # # # # # # #         gb4.configure_column("Std Price",   width=80)
# # # # # # # # # # #         gb4.configure_grid_options(rowHeight=36, headerHeight=32)
# # # # # # # # # # #         gb4.configure_default_column(resizable=True, sortable=True, filter=False)
# # # # # # # # # # #         AgGrid(df_bd2, gridOptions=gb4.build(), height=320,
# # # # # # # # # # #                allow_unsafe_jscode=True, theme="alpine", custom_css=_AGGRID_CSS)

# # # # # # # # # # #     # ── Risk Cascade (unchanged) ─────────────────────────────────────────────
# # # # # # # # # # #     with risk_tab:
# # # # # # # # # # #         sec("Risk Cascade Analysis")
# # # # # # # # # # #         risks = []
# # # # # # # # # # #         if snr["risk"] in ["CRITICAL", "WARNING"]:
# # # # # # # # # # #             risks.append({
# # # # # # # # # # #                 "icon": "⛔", "sev": 3, "color": "#EF4444", "bg": "#FEF2F2",
# # # # # # # # # # #                 "title": f"Finished Good at {snr['risk'].title()} Risk",
# # # # # # # # # # #                 "detail": (f"{snr['name']} has {round(snr['days_cover'])}d of cover. "
# # # # # # # # # # #                            f"SIH={round(snr['sih'])} vs SAP SS={round(snr['safety_stock'])}. "
# # # # # # # # # # #                            f"Production continuity at risk."),
# # # # # # # # # # #                 "action": f"Order {int(snr.get('repl_quantity', 0))} units immediately. Contact procurement today.",
# # # # # # # # # # #             })
# # # # # # # # # # #         if cn > 0:
# # # # # # # # # # #             risks.append({
# # # # # # # # # # #                 "icon": "⚠", "sev": 2, "color": "#F59E0B", "bg": "#FFFBEB",
# # # # # # # # # # #                 "title": f"Missing Supplier Data — {cn} External Components",
# # # # # # # # # # #                 "detail": (f"{cn} of {external_n} external components have no named supplier. "
# # # # # # # # # # #                            f"Single-source risk cannot be assessed for these."),
# # # # # # # # # # #                 "action": "Procurement to verify and update BOM with supplier names and lead times.",
# # # # # # # # # # #             })
# # # # # # # # # # #         if 0 < us <= 2:
# # # # # # # # # # #             risks.append({
# # # # # # # # # # #                 "icon": "⚠", "sev": 2, "color": "#F59E0B", "bg": "#FFFBEB",
# # # # # # # # # # #                 "title": f"Supplier Concentration — {us} Unique Supplier(s)",
# # # # # # # # # # #                 "detail": f"High dependency on {us} supplier(s). Any disruption cascades to multiple components simultaneously.",
# # # # # # # # # # #                 "action": "Evaluate dual-sourcing for critical external components.",
# # # # # # # # # # #             })
# # # # # # # # # # #         ext_comps = bsn[bsn["Procurement type"] == "F"]
# # # # # # # # # # #         if len(ext_comps) > 0:
# # # # # # # # # # #             locs = list(set([str(r) for r in bsn[bsn["Procurement type"] == "F"]["Supplier Location"].dropna().tolist()[:4]]))
# # # # # # # # # # #             risks.append({
# # # # # # # # # # #                 "icon": "🌍", "sev": 1, "color": "#3B82F6", "bg": "#EFF6FF",
# # # # # # # # # # #                 "title": f"External Procurement: {len(ext_comps)} Components",
# # # # # # # # # # #                 "detail": (f"External components depend on supplier availability and transit times. "
# # # # # # # # # # #                            f"Suppliers located in: {', '.join(locs)}."),
# # # # # # # # # # #                 "action": "Review external component lead times — stock buffers for long-transit items.",
# # # # # # # # # # #             })

# # # # # # # # # # #         if not risks:
# # # # # # # # # # #             st.markdown(
# # # # # # # # # # #                 "<div style='padding:10px 13px;background:var(--gbg);border:1px solid rgba(34,197,94,0.2);"
# # # # # # # # # # #                 "border-radius:var(--r);font-size:12px;color:#14532d;'>"
# # # # # # # # # # #                 "✓ No critical propagation risks identified.</div>",
# # # # # # # # # # #                 unsafe_allow_html=True,
# # # # # # # # # # #             )
# # # # # # # # # # #         else:
# # # # # # # # # # #             for r in sorted(risks, key=lambda x: -x["sev"]):
# # # # # # # # # # #                 st.markdown(
# # # # # # # # # # #                     f"<div style='background:{r['bg']};border:1px solid {r['color']}40;"
# # # # # # # # # # #                     f"border-left:4px solid {r['color']};border-radius:var(--r);"
# # # # # # # # # # #                     f"padding:12px 14px;margin-bottom:8px;'>"
# # # # # # # # # # #                     f"<div style='display:flex;align-items:center;gap:8px;margin-bottom:5px;'>"
# # # # # # # # # # #                     f"<span style='font-size:16px;'>{r['icon']}</span>"
# # # # # # # # # # #                     f"<div style='font-size:12px;font-weight:800;color:{r['color']};'>{r['title']}</div>"
# # # # # # # # # # #                     f"</div>"
# # # # # # # # # # #                     f"<div style='font-size:11px;color:var(--t2);margin-bottom:5px;'>{r['detail']}</div>"
# # # # # # # # # # #                     f"<div style='font-size:11px;color:{r['color']};font-weight:600;'>→ {r['action']}</div>"
# # # # # # # # # # #                     f"</div>",
# # # # # # # # # # #                     unsafe_allow_html=True,
# # # # # # # # # # #                 )

# # # # # # # # # # #         # Consolidation opportunities
# # # # # # # # # # #         consol2   = get_supplier_consolidation(data, summary)
# # # # # # # # # # #         relevant2 = consol2[
# # # # # # # # # # #             consol2.material_list.apply(lambda x: snid in x)
# # # # # # # # # # #             & (consol2.finished_goods_supplied > 1)
# # # # # # # # # # #             & consol2.consolidation_opportunity
# # # # # # # # # # #         ]
# # # # # # # # # # #         if len(relevant2) > 0:
# # # # # # # # # # #             sec("Supplier Consolidation Opportunities")
# # # # # # # # # # #             for _, r2 in relevant2.iterrows():
# # # # # # # # # # #                 others = [MATERIAL_LABELS.get(m, m)[:18] for m in r2["material_list"] if m != snid]
# # # # # # # # # # #                 st.markdown(
# # # # # # # # # # #                     f"<div class='prow'><div style='font-size:14px;'>🏭</div>"
# # # # # # # # # # #                     f"<div style='flex:1;'>"
# # # # # # # # # # #                     f"<div style='font-size:12px;font-weight:800;'>{r2['supplier']}</div>"
# # # # # # # # # # #                     f"<div style='font-size:10px;color:var(--t3);'>{r2['city']} · {r2['email']}</div>"
# # # # # # # # # # #                     f"<div style='font-size:10px;color:var(--t2);margin-top:2px;'>Also supplies: {', '.join(others[:3])}</div>"
# # # # # # # # # # #                     f"</div>"
# # # # # # # # # # #                     f"<div style='font-size:10px;font-weight:700;color:var(--or);'>⚡ Consolidate order</div>"
# # # # # # # # # # #                     f"</div>",
# # # # # # # # # # #                     unsafe_allow_html=True,
# # # # # # # # # # #                 )

# # # # # # # # # # #         # ── Ask ARIA with rich BOM context (including Standard Price) ─────────
# # # # # # # # # # #         if st.session_state.azure_client:
# # # # # # # # # # #             sec("Ask ARIA About This Network")
# # # # # # # # # # #             # Add disclaimer
# # # # # # # # # # #             st.info("ℹ️ This assistant provides supplier‑related insights only for the currently selected finished good.")
# # # # # # # # # # #             uq = st.text_input(
# # # # # # # # # # #                 "Question",
# # # # # # # # # # #                 placeholder="e.g. Which supplier provides more than 1 material for DELFIA Wash Concentrate?",
# # # # # # # # # # #                 key="snq", label_visibility="collapsed",
# # # # # # # # # # #             )
# # # # # # # # # # #             if uq and st.button("Ask ARIA", key="sna"):
# # # # # # # # # # #                 # Build a detailed BOM table as context, including Standard Price
# # # # # # # # # # #                 bom_lines = []
# # # # # # # # # # #                 for _, row in bsn.iterrows():
# # # # # # # # # # #                     mat_desc = str(row["Material Description"])[:40] if pd.notna(row["Material Description"]) else str(row["Material"])
# # # # # # # # # # #                     qty = row["Effective Order Qty"] if "Effective Order Qty" in row else row["Comp. Qty (CUn)"]
# # # # # # # # # # #                     fixed = "X (order exactly 1)" if row.get("Fixed Qty Flag") else ""
# # # # # # # # # # #                     sup = row.get("Supplier Display", "—")
# # # # # # # # # # #                     loc = row.get("Supplier Location", "—")
# # # # # # # # # # #                     transit = row.get("Transit Days", "—")
# # # # # # # # # # #                     reliability = row.get("Supplier Reliability", "—")
# # # # # # # # # # #                     std_price = row.get("Standard Price", "—")
# # # # # # # # # # #                     if pd.notna(std_price):
# # # # # # # # # # #                         std_price = f"${std_price:.2f}"
# # # # # # # # # # #                     bom_lines.append(f"- Component: {mat_desc} | Qty: {qty} {fixed} | Std Price: {std_price} | Supplier: {sup} | Location: {loc} | Transit: {transit}d | Reliability: {reliability}")
# # # # # # # # # # #                 bom_table = "\n".join(bom_lines)

# # # # # # # # # # #                 ctx3 = (
# # # # # # # # # # #                     f"Material: {snr['name']} (ID: {snid})\n"
# # # # # # # # # # #                     f"Risk: {snr['risk']}\n"
# # # # # # # # # # #                     f"Total components: {tc}\n"
# # # # # # # # # # #                     f"Inhouse components: {inhouse_n}\n"
# # # # # # # # # # #                     f"External components: {external_n}\n"
# # # # # # # # # # #                     f"Missing supplier data: {cn} components\n"
# # # # # # # # # # #                     f"Unique external suppliers: {us}\n"
# # # # # # # # # # #                     f"BOM details:\n{bom_table}"
# # # # # # # # # # #                 )
# # # # # # # # # # #                 with st.spinner("Thinking…"):
# # # # # # # # # # #                     ans = chat_with_data(st.session_state.azure_client, AZURE_DEPLOYMENT, uq, ctx3)
# # # # # # # # # # #                 st.markdown(
# # # # # # # # # # #                     f"<div class='ic' style='margin-top:8px;'><div class='il'>◈ ARIA</div>"

# # # # # # # # # # """
# # # # # # # # # # tabs/supply_network.py
# # # # # # # # # # Supply Network tab: BOM propagation map (Sankey diagram), component detail table,
# # # # # # # # # # risk cascade analysis, and supplier consolidation opportunities.
# # # # # # # # # # """

# # # # # # # # # # import streamlit as st
# # # # # # # # # # import pandas as pd
# # # # # # # # # # import plotly.graph_objects as go

# # # # # # # # # # from st_aggrid import AgGrid, GridOptionsBuilder, JsCode

# # # # # # # # # # from utils.helpers import sec, note, sbadge, ORANGE, AZURE_DEPLOYMENT
# # # # # # # # # # from data_loader import get_bom_components, get_supplier_consolidation
# # # # # # # # # # from agent import interpret_chart, chat_with_data

# # # # # # # # # # _AGGRID_CSS = {
# # # # # # # # # #     ".ag-root-wrapper": {"border": "1px solid #E2E8F0!important", "border-radius": "12px!important"},
# # # # # # # # # #     ".ag-header":       {"background": "#F8FAFE!important"},
# # # # # # # # # #     ".ag-row-even":     {"background": "#FFFFFF!important"},
# # # # # # # # # #     ".ag-row-odd":      {"background": "#F8FAFE!important"},
# # # # # # # # # # }


# # # # # # # # # # def render():
# # # # # # # # # #     data            = st.session_state.data
# # # # # # # # # #     summary         = st.session_state.summary
# # # # # # # # # #     MATERIAL_LABELS = st.session_state.material_labels

# # # # # # # # # #     st.markdown(
# # # # # # # # # #         "<div style='font-size:15px;font-weight:800;margin-bottom:4px;'>Supply Network</div>"
# # # # # # # # # #         "<div style='font-size:12px;color:var(--t3);margin-bottom:14px;'>"
# # # # # # # # # #         "BOM structure · Supplier locations · Risk cascade · Consolidation intelligence</div>",
# # # # # # # # # #         unsafe_allow_html=True,
# # # # # # # # # #     )

# # # # # # # # # #     snn  = st.selectbox("Finished Good", [r["name"] for _, r in summary.iterrows()], key="snm")
# # # # # # # # # #     snid = summary[summary.name == snn]["material"].values[0]
# # # # # # # # # #     snr  = summary[summary.material == snid].iloc[0]
# # # # # # # # # #     bsn  = get_bom_components(data, snid)

# # # # # # # # # #     if not len(bsn):
# # # # # # # # # #         st.markdown(
# # # # # # # # # #             "<div class='flag-box'><div style='font-size:22px;margin-bottom:8px;'>🕸️</div>"
# # # # # # # # # #             "<div style='font-size:14px;font-weight:800;color:var(--t2);'>No BOM data for this material</div></div>",
# # # # # # # # # #             unsafe_allow_html=True,
# # # # # # # # # #         )
# # # # # # # # # #         return

# # # # # # # # # #     cw        = int(bsn["Supplier Name(Vendor)"].notna().sum())
# # # # # # # # # #     cn        = len(bsn[bsn["Supplier Display"].str.startswith("⚠", na=False)])
# # # # # # # # # #     us        = int(bsn["Supplier Name(Vendor)"].dropna().nunique())
# # # # # # # # # #     tc        = len(bsn)
# # # # # # # # # #     inhouse_n = int((bsn["Procurement type"] == "E").sum())
# # # # # # # # # #     external_n = int((bsn["Procurement type"] == "F").sum())

# # # # # # # # # #     n1, n2, n3, n4 = st.columns(4)
# # # # # # # # # #     for col, val, lbl, vc in [
# # # # # # # # # #         (n1, tc,        "Total Components",  "#1E293B"),
# # # # # # # # # #         (n2, inhouse_n, "Revvity Inhouse",   "#22C55E"),
# # # # # # # # # #         (n3, cn,        "Missing Supplier",  "#F59E0B" if cn > 0 else "#1E293B"),
# # # # # # # # # #         (n4, us,        "Unique Ext Suppliers", "#1E293B"),
# # # # # # # # # #     ]:
# # # # # # # # # #         with col:
# # # # # # # # # #             st.markdown(
# # # # # # # # # #                 f"<div class='sc'><div style='flex:1;'>"
# # # # # # # # # #                 f"<div class='sv' style='color:{vc};'>{val}</div>"
# # # # # # # # # #                 f"<div class='sl'>{lbl}</div></div></div>",
# # # # # # # # # #                 unsafe_allow_html=True,
# # # # # # # # # #             )

# # # # # # # # # #     sn_tab, comp_tab, risk_tab = st.tabs(["🕸️  BOM Map", "📋  Components", "⚠️  Risk Analysis"])

# # # # # # # # # #     # ── BOM Map – Sankey diagram with clean legend ──────────────────────────────
# # # # # # # # # #     with sn_tab:
# # # # # # # # # #         sec("BOM Propagation Map")
# # # # # # # # # #         # Fixed legend: HTML list inside a note box (no bold/3D)
# # # # # # # # # #         st.markdown("""
# # # # # # # # # #         <div class='note-box'>
# # # # # # # # # #         <strong>Colour legend:</strong>
# # # # # # # # # #         <ul style='margin:5px 0 0 20px; padding-left:0;'>
# # # # # # # # # #         <li>🔵 <strong>Blue</strong> = External component with named supplier</li>
# # # # # # # # # #         <li>🟢 <strong>Green</strong> = Inhouse component (Revvity)</li>
# # # # # # # # # #         <li>🟡 <strong>Amber</strong> = External component with <strong>missing supplier data</strong></li>
# # # # # # # # # #         <li>🟣 <strong>Purple</strong> = Supplier node</li>
# # # # # # # # # #         <li>Root node colour matches finished good risk (🔴 Critical / 🟠 Warning / 🟢 Healthy)</li>
# # # # # # # # # #         </ul>
# # # # # # # # # #         Hover over nodes for details.
# # # # # # # # # #         </div>
# # # # # # # # # #         """, unsafe_allow_html=True)

# # # # # # # # # #         # Build node list and links for Sankey
# # # # # # # # # #         nodes = []
# # # # # # # # # #         node_colors = []
# # # # # # # # # #         node_map = {}

# # # # # # # # # #         # Root node (finished good)
# # # # # # # # # #         root_name = str(snr["name"])  # ensure string
# # # # # # # # # #         root_risk_color = {"CRITICAL": "#EF4444", "WARNING": "#F59E0B", "HEALTHY": "#22C55E"}.get(snr["risk"], "#94A3B8")
# # # # # # # # # #         nodes.append(root_name)
# # # # # # # # # #         node_colors.append(root_risk_color)
# # # # # # # # # #         node_map[root_name] = 0

# # # # # # # # # #         sources = []
# # # # # # # # # #         targets = []
# # # # # # # # # #         values = []

# # # # # # # # # #         # Process each BOM row
# # # # # # # # # #         for _, row in bsn.iterrows():
# # # # # # # # # #             comp_desc = str(row["Material Description"])[:40] if pd.notna(row["Material Description"]) else str(row["Material"])
# # # # # # # # # #             comp_label = f"[C] {comp_desc}"
# # # # # # # # # #             sup_display = row.get("Supplier Display", "—")
# # # # # # # # # #             proc_type = str(row.get("Procurement type", "")).strip()
# # # # # # # # # #             qty = row.get("Effective Order Qty", row["Comp. Qty (CUn)"]) if pd.notna(row.get("Effective Order Qty", row["Comp. Qty (CUn)"]) ) else 1
# # # # # # # # # #             # Ensure qty is numeric
# # # # # # # # # #             try:
# # # # # # # # # #                 qty = float(qty)
# # # # # # # # # #             except:
# # # # # # # # # #                 qty = 1.0

# # # # # # # # # #             # Add component node if not already present
# # # # # # # # # #             if comp_label not in node_map:
# # # # # # # # # #                 # Determine component colour
# # # # # # # # # #                 if proc_type == "E":
# # # # # # # # # #                     comp_color = "#22C55E"   # Inhouse
# # # # # # # # # #                 elif sup_display.startswith("⚠"):
# # # # # # # # # #                     comp_color = "#F59E0B"   # Missing supplier
# # # # # # # # # #                 else:
# # # # # # # # # #                     comp_color = "#3B82F6"   # External named
# # # # # # # # # #                 nodes.append(comp_label)
# # # # # # # # # #                 node_colors.append(comp_color)
# # # # # # # # # #                 node_map[comp_label] = len(nodes) - 1

# # # # # # # # # #             # Link root -> component
# # # # # # # # # #             sources.append(node_map[root_name])
# # # # # # # # # #             targets.append(node_map[comp_label])
# # # # # # # # # #             values.append(qty)

# # # # # # # # # #             # Add supplier node if external and named
# # # # # # # # # #             if sup_display not in ["Revvity Inhouse", "—"] and not sup_display.startswith("⚠"):
# # # # # # # # # #                 sup_label = f"[S] {str(sup_display)[:25]}"
# # # # # # # # # #                 if sup_label not in node_map:
# # # # # # # # # #                     nodes.append(sup_label)
# # # # # # # # # #                     node_colors.append("#8B5CF6")  # Purple for suppliers
# # # # # # # # # #                     node_map[sup_label] = len(nodes) - 1
# # # # # # # # # #                 # Link component -> supplier
# # # # # # # # # #                 sources.append(node_map[comp_label])
# # # # # # # # # #                 targets.append(node_map[sup_label])
# # # # # # # # # #                 values.append(1.0)  # connection weight

# # # # # # # # # #         # Build Sankey figure with normal font weight
# # # # # # # # # #         fig_sankey = go.Figure(data=[go.Sankey(
# # # # # # # # # #             arrangement="snap",
# # # # # # # # # #             node=dict(
# # # # # # # # # #                 pad=20,
# # # # # # # # # #                 thickness=20,
# # # # # # # # # #                 line=dict(color="white", width=0.5),
# # # # # # # # # #                 label=nodes,
# # # # # # # # # #                 color=node_colors,
# # # # # # # # # #                 hovertemplate="<b>%{label}</b><extra></extra>"
# # # # # # # # # #             ),
# # # # # # # # # #             link=dict(
# # # # # # # # # #                 source=sources,
# # # # # # # # # #                 target=targets,
# # # # # # # # # #                 value=values,
# # # # # # # # # #                 color="rgba(200,200,200,0.3)"
# # # # # # # # # #             )
# # # # # # # # # #         )])
# # # # # # # # # #         fig_sankey.update_layout(
# # # # # # # # # #             title=None,
# # # # # # # # # #             font=dict(size=11, family="Inter", weight="normal"),  # ensure normal font weight
# # # # # # # # # #             height=500,
# # # # # # # # # #             margin=dict(l=20, r=20, t=20, b=20),
# # # # # # # # # #             paper_bgcolor="white",
# # # # # # # # # #         )
# # # # # # # # # #         st.plotly_chart(fig_sankey, use_container_width=True)

# # # # # # # # # #         if st.session_state.azure_client:
# # # # # # # # # #             if st.button("◈ Interpret BOM Map", key="interp_bom_sankey"):
# # # # # # # # # #                 with st.spinner("ARIA interpreting…"):
# # # # # # # # # #                     bom_ctx = {
# # # # # # # # # #                         "material": snr["name"], "total_components": tc,
# # # # # # # # # #                         "inhouse": inhouse_n, "external_named": cw - inhouse_n,
# # # # # # # # # #                         "missing_supplier": cn, "unique_suppliers": us, "risk": snr["risk"],
# # # # # # # # # #                     }
# # # # # # # # # #                     interp = interpret_chart(
# # # # # # # # # #                         st.session_state.azure_client, AZURE_DEPLOYMENT,
# # # # # # # # # #                         "BOM Risk Propagation Map", bom_ctx,
# # # # # # # # # #                         "What are the key supply chain risks in this BOM and what should procurement prioritise?",
# # # # # # # # # #                     )
# # # # # # # # # #                 st.markdown(
# # # # # # # # # #                     f"<div class='ic' style='margin-top:8px;'><div class='il'>◈ ARIA</div>"
# # # # # # # # # #                     f"<div class='ib'>{interp}</div></div>",
# # # # # # # # # #                     unsafe_allow_html=True,
# # # # # # # # # #                 )

# # # # # # # # # #     # ── Component Detail ──────────────────────────────────────────────────────
# # # # # # # # # #     with comp_tab:
# # # # # # # # # #         sec("Component Detail")
# # # # # # # # # #         bom_display2 = []
# # # # # # # # # #         for _, b in bsn.iterrows():
# # # # # # # # # #             eff_qty = b.get("Effective Order Qty", b["Comp. Qty (CUn)"])
# # # # # # # # # #             fq_txt  = ("1 (Fixed)" if b.get("Fixed Qty Flag", False)
# # # # # # # # # #                        else str(round(float(eff_qty), 3)) if pd.notna(eff_qty) else "—")
# # # # # # # # # #             bom_display2.append({
# # # # # # # # # #                 "Material":    str(b["Material"]),
# # # # # # # # # #                 "Description": str(b["Material Description"])[:36] if pd.notna(b["Material Description"]) else "—",
# # # # # # # # # #                 "Level":       str(b["Level"])[:25] if pd.notna(b["Level"]) else "—",
# # # # # # # # # #                 "Qty":         fq_txt,
# # # # # # # # # #                 "Unit":        str(b["Component unit"]) if pd.notna(b["Component unit"]) else "—",
# # # # # # # # # #                 "Type":        b.get("Procurement Label", "—"),
# # # # # # # # # #                 "Supplier":    b.get("Supplier Display", "—"),
# # # # # # # # # #                 "Location":    b.get("Supplier Location", "—"),
# # # # # # # # # #                 "Transit":     f"{b.get('Transit Days', '—')}d" if b.get("Transit Days") is not None else "—",
# # # # # # # # # #                 "Std Price":   f"${b.get('Standard Price', 0):.2f}" if pd.notna(b.get('Standard Price')) else "—",
# # # # # # # # # #             })
# # # # # # # # # #         df_bd2  = pd.DataFrame(bom_display2)
# # # # # # # # # #         sup_r3  = JsCode("""class R{init(p){const v=p.value||'';this.e=document.createElement('span');if(v.startsWith('⚠')){this.e.style.cssText='background:#FEF3C7;color:#F59E0B;padding:2px 6px;border-radius:4px;font-size:10px;font-weight:600;';this.e.innerText=v;}else if(v==='Revvity Inhouse'){this.e.style.cssText='background:#DCFCE7;color:#16a34a;padding:2px 6px;border-radius:4px;font-size:10px;font-weight:600;';this.e.innerText='🏭 '+v;}else{this.e.style.cssText='background:#EFF6FF;color:#2563EB;padding:2px 6px;border-radius:4px;font-size:10px;';this.e.innerText='🚚 '+v;};}getGui(){return this.e;}}""")
# # # # # # # # # #         gb4     = GridOptionsBuilder.from_dataframe(df_bd2)
# # # # # # # # # #         gb4.configure_column("Material",    width=82)
# # # # # # # # # #         gb4.configure_column("Description", width=215)
# # # # # # # # # #         gb4.configure_column("Level",       width=85)
# # # # # # # # # #         gb4.configure_column("Qty",         width=75)
# # # # # # # # # #         gb4.configure_column("Unit",        width=50)
# # # # # # # # # #         gb4.configure_column("Type",        width=100)
# # # # # # # # # #         gb4.configure_column("Supplier",    width=170, cellRenderer=sup_r3)
# # # # # # # # # #         gb4.configure_column("Location",    width=130)
# # # # # # # # # #         gb4.configure_column("Transit",     width=58)
# # # # # # # # # #         gb4.configure_column("Std Price",   width=80)
# # # # # # # # # #         gb4.configure_grid_options(rowHeight=36, headerHeight=32)
# # # # # # # # # #         gb4.configure_default_column(resizable=True, sortable=True, filter=False)
# # # # # # # # # #         AgGrid(df_bd2, gridOptions=gb4.build(), height=320,
# # # # # # # # # #                allow_unsafe_jscode=True, theme="alpine", custom_css=_AGGRID_CSS)

# # # # # # # # # #     # ── Risk Cascade (unchanged) ─────────────────────────────────────────────
# # # # # # # # # #     with risk_tab:
# # # # # # # # # #         sec("Risk Cascade Analysis")
# # # # # # # # # #         risks = []
# # # # # # # # # #         if snr["risk"] in ["CRITICAL", "WARNING"]:
# # # # # # # # # #             risks.append({
# # # # # # # # # #                 "icon": "⛔", "sev": 3, "color": "#EF4444", "bg": "#FEF2F2",
# # # # # # # # # #                 "title": f"Finished Good at {snr['risk'].title()} Risk",
# # # # # # # # # #                 "detail": (f"{snr['name']} has {round(snr['days_cover'])}d of cover. "
# # # # # # # # # #                            f"SIH={round(snr['sih'])} vs SAP SS={round(snr['safety_stock'])}. "
# # # # # # # # # #                            f"Production continuity at risk."),
# # # # # # # # # #                 "action": f"Order {int(snr.get('repl_quantity', 0))} units immediately. Contact procurement today.",
# # # # # # # # # #             })
# # # # # # # # # #         if cn > 0:
# # # # # # # # # #             risks.append({
# # # # # # # # # #                 "icon": "⚠", "sev": 2, "color": "#F59E0B", "bg": "#FFFBEB",
# # # # # # # # # #                 "title": f"Missing Supplier Data — {cn} External Components",
# # # # # # # # # #                 "detail": (f"{cn} of {external_n} external components have no named supplier. "
# # # # # # # # # #                            f"Single-source risk cannot be assessed for these."),
# # # # # # # # # #                 "action": "Procurement to verify and update BOM with supplier names and lead times.",
# # # # # # # # # #             })
# # # # # # # # # #         if 0 < us <= 2:
# # # # # # # # # #             risks.append({
# # # # # # # # # #                 "icon": "⚠", "sev": 2, "color": "#F59E0B", "bg": "#FFFBEB",
# # # # # # # # # #                 "title": f"Supplier Concentration — {us} Unique Supplier(s)",
# # # # # # # # # #                 "detail": f"High dependency on {us} supplier(s). Any disruption cascades to multiple components simultaneously.",
# # # # # # # # # #                 "action": "Evaluate dual-sourcing for critical external components.",
# # # # # # # # # #             })
# # # # # # # # # #         ext_comps = bsn[bsn["Procurement type"] == "F"]
# # # # # # # # # #         if len(ext_comps) > 0:
# # # # # # # # # #             locs = list(set([str(r) for r in bsn[bsn["Procurement type"] == "F"]["Supplier Location"].dropna().tolist()[:4]]))
# # # # # # # # # #             risks.append({
# # # # # # # # # #                 "icon": "🌍", "sev": 1, "color": "#3B82F6", "bg": "#EFF6FF",
# # # # # # # # # #                 "title": f"External Procurement: {len(ext_comps)} Components",
# # # # # # # # # #                 "detail": (f"External components depend on supplier availability and transit times. "
# # # # # # # # # #                            f"Suppliers located in: {', '.join(locs)}."),
# # # # # # # # # #                 "action": "Review external component lead times — stock buffers for long-transit items.",
# # # # # # # # # #             })

# # # # # # # # # #         if not risks:
# # # # # # # # # #             st.markdown(
# # # # # # # # # #                 "<div style='padding:10px 13px;background:var(--gbg);border:1px solid rgba(34,197,94,0.2);"
# # # # # # # # # #                 "border-radius:var(--r);font-size:12px;color:#14532d;'>"
# # # # # # # # # #                 "✓ No critical propagation risks identified.</div>",
# # # # # # # # # #                 unsafe_allow_html=True,
# # # # # # # # # #             )
# # # # # # # # # #         else:
# # # # # # # # # #             for r in sorted(risks, key=lambda x: -x["sev"]):
# # # # # # # # # #                 st.markdown(
# # # # # # # # # #                     f"<div style='background:{r['bg']};border:1px solid {r['color']}40;"
# # # # # # # # # #                     f"border-left:4px solid {r['color']};border-radius:var(--r);"
# # # # # # # # # #                     f"padding:12px 14px;margin-bottom:8px;'>"
# # # # # # # # # #                     f"<div style='display:flex;align-items:center;gap:8px;margin-bottom:5px;'>"
# # # # # # # # # #                     f"<span style='font-size:16px;'>{r['icon']}</span>"
# # # # # # # # # #                     f"<div style='font-size:12px;font-weight:800;color:{r['color']};'>{r['title']}</div>"
# # # # # # # # # #                     f"</div>"
# # # # # # # # # #                     f"<div style='font-size:11px;color:var(--t2);margin-bottom:5px;'>{r['detail']}</div>"
# # # # # # # # # #                     f"<div style='font-size:11px;color:{r['color']};font-weight:600;'>→ {r['action']}</div>"
# # # # # # # # # #                     f"</div>",
# # # # # # # # # #                     unsafe_allow_html=True,
# # # # # # # # # #                 )

# # # # # # # # # #         # Consolidation opportunities
# # # # # # # # # #         consol2   = get_supplier_consolidation(data, summary)
# # # # # # # # # #         relevant2 = consol2[
# # # # # # # # # #             consol2.material_list.apply(lambda x: snid in x)
# # # # # # # # # #             & (consol2.finished_goods_supplied > 1)
# # # # # # # # # #             & consol2.consolidation_opportunity
# # # # # # # # # #         ]
# # # # # # # # # #         if len(relevant2) > 0:
# # # # # # # # # #             sec("Supplier Consolidation Opportunities")
# # # # # # # # # #             for _, r2 in relevant2.iterrows():
# # # # # # # # # #                 others = [MATERIAL_LABELS.get(m, m)[:18] for m in r2["material_list"] if m != snid]
# # # # # # # # # #                 st.markdown(
# # # # # # # # # #                     f"<div class='prow'><div style='font-size:14px;'>🏭</div>"
# # # # # # # # # #                     f"<div style='flex:1;'>"
# # # # # # # # # #                     f"<div style='font-size:12px;font-weight:800;'>{r2['supplier']}</div>"
# # # # # # # # # #                     f"<div style='font-size:10px;color:var(--t3);'>{r2['city']} · {r2['email']}</div>"
# # # # # # # # # #                     f"<div style='font-size:10px;color:var(--t2);margin-top:2px;'>Also supplies: {', '.join(others[:3])}</div>"
# # # # # # # # # #                     f"</div>"
# # # # # # # # # #                     f"<div style='font-size:10px;font-weight:700;color:var(--or);'>⚡ Consolidate order</div>"
# # # # # # # # # #                     f"</div>",
# # # # # # # # # #                     unsafe_allow_html=True,
# # # # # # # # # #                 )

# # # # # # # # # #         # ── Ask ARIA with rich BOM context (including Standard Price) ─────────
# # # # # # # # # #         if st.session_state.azure_client:
# # # # # # # # # #             sec("Ask ARIA About This Network")
# # # # # # # # # #             st.info("ℹ️ This assistant provides supplier‑related insights only for the currently selected finished good.")
# # # # # # # # # #             uq = st.text_input(
# # # # # # # # # #                 "Question",
# # # # # # # # # #                 placeholder="e.g. Which supplier provides more than 1 material for DELFIA Wash Concentrate?",
# # # # # # # # # #                 key="snq", label_visibility="collapsed",
# # # # # # # # # #             )
# # # # # # # # # #             if uq and st.button("Ask ARIA", key="sna"):
# # # # # # # # # #                 bom_lines = []
# # # # # # # # # #                 for _, row in bsn.iterrows():
# # # # # # # # # #                     mat_desc = str(row["Material Description"])[:40] if pd.notna(row["Material Description"]) else str(row["Material"])
# # # # # # # # # #                     qty = row["Effective Order Qty"] if "Effective Order Qty" in row else row["Comp. Qty (CUn)"]
# # # # # # # # # #                     fixed = "X (order exactly 1)" if row.get("Fixed Qty Flag") else ""
# # # # # # # # # #                     sup = row.get("Supplier Display", "—")
# # # # # # # # # #                     loc = row.get("Supplier Location", "—")
# # # # # # # # # #                     transit = row.get("Transit Days", "—")
# # # # # # # # # #                     reliability = row.get("Supplier Reliability", "—")
# # # # # # # # # #                     std_price = row.get("Standard Price", "—")
# # # # # # # # # #                     if pd.notna(std_price):
# # # # # # # # # #                         std_price = f"${std_price:.2f}"
# # # # # # # # # #                     bom_lines.append(f"- Component: {mat_desc} | Qty: {qty} {fixed} | Std Price: {std_price} | Supplier: {sup} | Location: {loc} | Transit: {transit}d | Reliability: {reliability}")
# # # # # # # # # #                 bom_table = "\n".join(bom_lines)

# # # # # # # # # #                 ctx3 = (
# # # # # # # # # #                     f"Material: {snr['name']} (ID: {snid})\n"
# # # # # # # # # #                     f"Risk: {snr['risk']}\n"
# # # # # # # # # #                     f"Total components: {tc}\n"
# # # # # # # # # #                     f"Inhouse components: {inhouse_n}\n"
# # # # # # # # # #                     f"External components: {external_n}\n"
# # # # # # # # # #                     f"Missing supplier data: {cn} components\n"
# # # # # # # # # #                     f"Unique external suppliers: {us}\n"
# # # # # # # # # #                     f"BOM details:\n{bom_table}"
# # # # # # # # # #                 )
# # # # # # # # # #                 with st.spinner("Thinking…"):
# # # # # # # # # #                     ans = chat_with_data(st.session_state.azure_client, AZURE_DEPLOYMENT, uq, ctx3)
# # # # # # # # # #                 st.markdown(
# # # # # # # # # #                     f"<div class='ic' style='margin-top:8px;'><div class='il'>◈ ARIA</div>"
# # # # # # # # # #                     f"<div class='ib'>{ans}</div></div>",
# # # # # # # # # #                     unsafe_allow_html=True,
# # # # # # # # # #                 )

# # # # # # # # # #     st.markdown('<div class="pfooter">🕸️ Powered by <strong>MResult</strong></div>', unsafe_allow_html=True)
# # # # # # # # # # #                     f"<div class='ib'>{ans}</div></div>",
# # # # # # # # # # #                     unsafe_allow_html=True,
# # # # # # # # # # #                 )

# # # # # # # # # # #     st.markdown('<div class="pfooter">🕸️ Powered by <strong>MResult</strong></div>', unsafe_allow_html=True)

# # # # # # # # # """
# # # # # # # # # tabs/supply_network.py
# # # # # # # # # Supply Network tab: BOM propagation map (Sankey diagram), component detail table,
# # # # # # # # # risk cascade analysis, and supplier consolidation opportunities.
# # # # # # # # # """

# # # # # # # # # import streamlit as st
# # # # # # # # # import pandas as pd
# # # # # # # # # import plotly.graph_objects as go

# # # # # # # # # from st_aggrid import AgGrid, GridOptionsBuilder, JsCode

# # # # # # # # # from utils.helpers import sec, note, sbadge, ORANGE, AZURE_DEPLOYMENT
# # # # # # # # # from data_loader import get_bom_components, get_supplier_consolidation
# # # # # # # # # from agent import interpret_chart, chat_with_data

# # # # # # # # # _AGGRID_CSS = {
# # # # # # # # #     ".ag-root-wrapper": {"border": "1px solid #E2E8F0!important", "border-radius": "12px!important"},
# # # # # # # # #     ".ag-header":       {"background": "#F8FAFE!important"},
# # # # # # # # #     ".ag-row-even":     {"background": "#FFFFFF!important"},
# # # # # # # # #     ".ag-row-odd":      {"background": "#F8FAFE!important"},
# # # # # # # # # }


# # # # # # # # # def render():
# # # # # # # # #     data            = st.session_state.data
# # # # # # # # #     summary         = st.session_state.summary
# # # # # # # # #     MATERIAL_LABELS = st.session_state.material_labels

# # # # # # # # #     st.markdown(
# # # # # # # # #         "<div style='font-size:15px;font-weight:800;margin-bottom:4px;'>Supply Network</div>"
# # # # # # # # #         "<div style='font-size:12px;color:var(--t3);margin-bottom:14px;'>"
# # # # # # # # #         "BOM structure · Supplier locations · Risk cascade · Consolidation intelligence</div>",
# # # # # # # # #         unsafe_allow_html=True,
# # # # # # # # #     )

# # # # # # # # #     snn  = st.selectbox("Finished Good", [r["name"] for _, r in summary.iterrows()], key="snm")
# # # # # # # # #     snid = summary[summary.name == snn]["material"].values[0]
# # # # # # # # #     snr  = summary[summary.material == snid].iloc[0]
# # # # # # # # #     bsn  = get_bom_components(data, snid)

# # # # # # # # #     if not len(bsn):
# # # # # # # # #         st.markdown(
# # # # # # # # #             "<div class='flag-box'><div style='font-size:22px;margin-bottom:8px;'>🕸️</div>"
# # # # # # # # #             "<div style='font-size:14px;font-weight:800;color:var(--t2);'>No BOM data for this material</div></div>",
# # # # # # # # #             unsafe_allow_html=True,
# # # # # # # # #         )
# # # # # # # # #         return

# # # # # # # # #     cw        = int(bsn["Supplier Name(Vendor)"].notna().sum())
# # # # # # # # #     cn        = len(bsn[bsn["Supplier Display"].str.startswith("⚠", na=False)])
# # # # # # # # #     us        = int(bsn["Supplier Name(Vendor)"].dropna().nunique())
# # # # # # # # #     tc        = len(bsn)
# # # # # # # # #     inhouse_n = int((bsn["Procurement type"] == "E").sum())
# # # # # # # # #     external_n = int((bsn["Procurement type"] == "F").sum())

# # # # # # # # #     n1, n2, n3, n4 = st.columns(4)
# # # # # # # # #     for col, val, lbl, vc in [
# # # # # # # # #         (n1, tc,        "Total Components",  "#1E293B"),
# # # # # # # # #         (n2, inhouse_n, "Revvity Inhouse",   "#22C55E"),
# # # # # # # # #         (n3, cn,        "Missing Supplier",  "#F59E0B" if cn > 0 else "#1E293B"),
# # # # # # # # #         (n4, us,        "Unique Ext Suppliers", "#1E293B"),
# # # # # # # # #     ]:
# # # # # # # # #         with col:
# # # # # # # # #             st.markdown(
# # # # # # # # #                 f"<div class='sc'><div style='flex:1;'>"
# # # # # # # # #                 f"<div class='sv' style='color:{vc};'>{val}</div>"
# # # # # # # # #                 f"<div class='sl'>{lbl}</div></div></div>",
# # # # # # # # #                 unsafe_allow_html=True,
# # # # # # # # #             )

# # # # # # # # #     sn_tab, comp_tab, risk_tab = st.tabs(["🕸️  BOM Map", "📋  Components", "⚠️  Risk Analysis"])

# # # # # # # # #     # ── BOM Map – Sankey diagram with clean legend ──────────────────────────────
# # # # # # # # #     with sn_tab:
# # # # # # # # #         sec("BOM Propagation Map")
# # # # # # # # #         # Fixed legend: HTML list inside a note box (no bold/3D)
# # # # # # # # #         st.markdown("""
# # # # # # # # #         <div class='note-box'>
# # # # # # # # #         <strong>Colour legend:</strong>
# # # # # # # # #         <ul style='margin:5px 0 0 20px; padding-left:0;'>
# # # # # # # # #         <li>🔵 <strong>Blue</strong> = External component with named supplier</li>
# # # # # # # # #         <li>🟢 <strong>Green</strong> = Inhouse component (Revvity)</li>
# # # # # # # # #         <li>🟡 <strong>Amber</strong> = External component with <strong>missing supplier data</strong></li>
# # # # # # # # #         <li>🟣 <strong>Purple</strong> = Supplier node</li>
# # # # # # # # #         <li>Root node colour matches finished good risk (🔴 Critical / 🟠 Warning / 🟢 Healthy)</li>
# # # # # # # # #         </ul>
# # # # # # # # #         Hover over nodes for details.
# # # # # # # # #         </div>
# # # # # # # # #         """, unsafe_allow_html=True)

# # # # # # # # #         # Build node list and links for Sankey
# # # # # # # # #         nodes = []
# # # # # # # # #         node_colors = []
# # # # # # # # #         node_map = {}

# # # # # # # # #         # Root node (finished good)
# # # # # # # # #         root_name = str(snr["name"])  # ensure string
# # # # # # # # #         root_risk_color = {"CRITICAL": "#EF4444", "WARNING": "#F59E0B", "HEALTHY": "#22C55E"}.get(snr["risk"], "#94A3B8")
# # # # # # # # #         nodes.append(root_name)
# # # # # # # # #         node_colors.append(root_risk_color)
# # # # # # # # #         node_map[root_name] = 0

# # # # # # # # #         sources = []
# # # # # # # # #         targets = []
# # # # # # # # #         values = []

# # # # # # # # #         # Process each BOM row
# # # # # # # # #         for _, row in bsn.iterrows():
# # # # # # # # #             comp_desc = str(row["Material Description"])[:40] if pd.notna(row["Material Description"]) else str(row["Material"])
# # # # # # # # #             comp_label = f"[C] {comp_desc}"
# # # # # # # # #             sup_display = row.get("Supplier Display", "—")
# # # # # # # # #             proc_type = str(row.get("Procurement type", "")).strip()
# # # # # # # # #             qty = row.get("Effective Order Qty", row["Comp. Qty (CUn)"]) if pd.notna(row.get("Effective Order Qty", row["Comp. Qty (CUn)"]) ) else 1
# # # # # # # # #             # Ensure qty is numeric
# # # # # # # # #             try:
# # # # # # # # #                 qty = float(qty)
# # # # # # # # #             except:
# # # # # # # # #                 qty = 1.0

# # # # # # # # #             # Add component node if not already present
# # # # # # # # #             if comp_label not in node_map:
# # # # # # # # #                 # Determine component colour
# # # # # # # # #                 if proc_type == "E":
# # # # # # # # #                     comp_color = "#22C55E"   # Inhouse
# # # # # # # # #                 elif sup_display.startswith("⚠"):
# # # # # # # # #                     comp_color = "#F59E0B"   # Missing supplier
# # # # # # # # #                 else:
# # # # # # # # #                     comp_color = "#3B82F6"   # External named
# # # # # # # # #                 nodes.append(comp_label)
# # # # # # # # #                 node_colors.append(comp_color)
# # # # # # # # #                 node_map[comp_label] = len(nodes) - 1

# # # # # # # # #             # Link root -> component
# # # # # # # # #             sources.append(node_map[root_name])
# # # # # # # # #             targets.append(node_map[comp_label])
# # # # # # # # #             values.append(qty)

# # # # # # # # #             # Add supplier node if external and named
# # # # # # # # #             if sup_display not in ["Revvity Inhouse", "—"] and not sup_display.startswith("⚠"):
# # # # # # # # #                 sup_label = f"[S] {str(sup_display)[:25]}"
# # # # # # # # #                 if sup_label not in node_map:
# # # # # # # # #                     nodes.append(sup_label)
# # # # # # # # #                     node_colors.append("#8B5CF6")  # Purple for suppliers
# # # # # # # # #                     node_map[sup_label] = len(nodes) - 1
# # # # # # # # #                 # Link component -> supplier
# # # # # # # # #                 sources.append(node_map[comp_label])
# # # # # # # # #                 targets.append(node_map[sup_label])
# # # # # # # # #                 values.append(1.0)  # connection weight

# # # # # # # # #         # Build Sankey figure with normal font weight
# # # # # # # # #         fig_sankey = go.Figure(data=[go.Sankey(
# # # # # # # # #             arrangement="snap",
# # # # # # # # #             node=dict(
# # # # # # # # #                 pad=20,
# # # # # # # # #                 thickness=20,
# # # # # # # # #                 line=dict(color="white", width=0.5),
# # # # # # # # #                 label=nodes,
# # # # # # # # #                 color=node_colors,
# # # # # # # # #                 hovertemplate="<b>%{label}</b><extra></extra>"
# # # # # # # # #             ),
# # # # # # # # #             link=dict(
# # # # # # # # #                 source=sources,
# # # # # # # # #                 target=targets,
# # # # # # # # #                 value=values,
# # # # # # # # #                 color="rgba(200,200,200,0.3)"
# # # # # # # # #             )
# # # # # # # # #         )])
# # # # # # # # #         fig_sankey.update_layout(
# # # # # # # # #             title=None,
# # # # # # # # #             font=dict(size=11, family="Inter", weight="normal"),  # ensure normal font weight
# # # # # # # # #             height=500,
# # # # # # # # #             margin=dict(l=20, r=20, t=20, b=20),
# # # # # # # # #             paper_bgcolor="white",
# # # # # # # # #         )
# # # # # # # # #         st.plotly_chart(fig_sankey, use_container_width=True)

# # # # # # # # #         if st.session_state.azure_client:
# # # # # # # # #             if st.button("◈ Interpret BOM Map", key="interp_bom_sankey"):
# # # # # # # # #                 with st.spinner("ARIA interpreting…"):
# # # # # # # # #                     bom_ctx = {
# # # # # # # # #                         "material": snr["name"], "total_components": tc,
# # # # # # # # #                         "inhouse": inhouse_n, "external_named": cw - inhouse_n,
# # # # # # # # #                         "missing_supplier": cn, "unique_suppliers": us, "risk": snr["risk"],
# # # # # # # # #                     }
# # # # # # # # #                     interp = interpret_chart(
# # # # # # # # #                         st.session_state.azure_client, AZURE_DEPLOYMENT,
# # # # # # # # #                         "BOM Risk Propagation Map", bom_ctx,
# # # # # # # # #                         "What are the key supply chain risks in this BOM and what should procurement prioritise?",
# # # # # # # # #                     )
# # # # # # # # #                 st.markdown(
# # # # # # # # #                     f"<div class='ic' style='margin-top:8px;'><div class='il'>◈ ARIA</div>"
# # # # # # # # #                     f"<div class='ib'>{interp}</div></div>",
# # # # # # # # #                     unsafe_allow_html=True,
# # # # # # # # #                 )

# # # # # # # # #     # ── Component Detail ──────────────────────────────────────────────────────
# # # # # # # # #     with comp_tab:
# # # # # # # # #         sec("Component Detail")
# # # # # # # # #         bom_display2 = []
# # # # # # # # #         for _, b in bsn.iterrows():
# # # # # # # # #             eff_qty = b.get("Effective Order Qty", b["Comp. Qty (CUn)"])
# # # # # # # # #             fq_txt  = ("1 (Fixed)" if b.get("Fixed Qty Flag", False)
# # # # # # # # #                        else str(round(float(eff_qty), 3)) if pd.notna(eff_qty) else "—")
# # # # # # # # #             bom_display2.append({
# # # # # # # # #                 "Material":    str(b["Material"]),
# # # # # # # # #                 "Description": str(b["Material Description"])[:36] if pd.notna(b["Material Description"]) else "—",
# # # # # # # # #                 "Level":       str(b["Level"])[:25] if pd.notna(b["Level"]) else "—",
# # # # # # # # #                 "Qty":         fq_txt,
# # # # # # # # #                 "Unit":        str(b["Component unit"]) if pd.notna(b["Component unit"]) else "—",
# # # # # # # # #                 "Type":        b.get("Procurement Label", "—"),
# # # # # # # # #                 "Supplier":    b.get("Supplier Display", "—"),
# # # # # # # # #                 "Location":    b.get("Supplier Location", "—"),
# # # # # # # # #                 "Transit":     f"{b.get('Transit Days', '—')}d" if b.get("Transit Days") is not None else "—",
# # # # # # # # #                 "Std Price":   f"${b.get('Standard Price', 0):.2f}" if pd.notna(b.get('Standard Price')) else "—",
# # # # # # # # #             })
# # # # # # # # #         df_bd2  = pd.DataFrame(bom_display2)
# # # # # # # # #         sup_r3  = JsCode("""class R{init(p){const v=p.value||'';this.e=document.createElement('span');if(v.startsWith('⚠')){this.e.style.cssText='background:#FEF3C7;color:#F59E0B;padding:2px 6px;border-radius:4px;font-size:10px;font-weight:600;';this.e.innerText=v;}else if(v==='Revvity Inhouse'){this.e.style.cssText='background:#DCFCE7;color:#16a34a;padding:2px 6px;border-radius:4px;font-size:10px;font-weight:600;';this.e.innerText='🏭 '+v;}else{this.e.style.cssText='background:#EFF6FF;color:#2563EB;padding:2px 6px;border-radius:4px;font-size:10px;';this.e.innerText='🚚 '+v;};}getGui(){return this.e;}}""")
# # # # # # # # #         gb4     = GridOptionsBuilder.from_dataframe(df_bd2)
# # # # # # # # #         gb4.configure_column("Material",    width=82)
# # # # # # # # #         gb4.configure_column("Description", width=215)
# # # # # # # # #         gb4.configure_column("Level",       width=85)
# # # # # # # # #         gb4.configure_column("Qty",         width=75)
# # # # # # # # #         gb4.configure_column("Unit",        width=50)
# # # # # # # # #         gb4.configure_column("Type",        width=100)
# # # # # # # # #         gb4.configure_column("Supplier",    width=170, cellRenderer=sup_r3)
# # # # # # # # #         gb4.configure_column("Location",    width=130)
# # # # # # # # #         gb4.configure_column("Transit",     width=58)
# # # # # # # # #         gb4.configure_column("Std Price",   width=80)
# # # # # # # # #         gb4.configure_grid_options(rowHeight=36, headerHeight=32)
# # # # # # # # #         gb4.configure_default_column(resizable=True, sortable=True, filter=False)
# # # # # # # # #         AgGrid(df_bd2, gridOptions=gb4.build(), height=320,
# # # # # # # # #                allow_unsafe_jscode=True, theme="alpine", custom_css=_AGGRID_CSS)

# # # # # # # # #     # ── Risk Cascade (unchanged) ─────────────────────────────────────────────
# # # # # # # # #     with risk_tab:
# # # # # # # # #         sec("Risk Cascade Analysis")
# # # # # # # # #         risks = []
# # # # # # # # #         if snr["risk"] in ["CRITICAL", "WARNING"]:
# # # # # # # # #             risks.append({
# # # # # # # # #                 "icon": "⛔", "sev": 3, "color": "#EF4444", "bg": "#FEF2F2",
# # # # # # # # #                 "title": f"Finished Good at {snr['risk'].title()} Risk",
# # # # # # # # #                 "detail": (f"{snr['name']} has {round(snr['days_cover'])}d of cover. "
# # # # # # # # #                            f"SIH={round(snr['sih'])} vs SAP SS={round(snr['safety_stock'])}. "
# # # # # # # # #                            f"Production continuity at risk."),
# # # # # # # # #                 "action": f"Order {int(snr.get('repl_quantity', 0))} units immediately. Contact procurement today.",
# # # # # # # # #             })
# # # # # # # # #         if cn > 0:
# # # # # # # # #             risks.append({
# # # # # # # # #                 "icon": "⚠", "sev": 2, "color": "#F59E0B", "bg": "#FFFBEB",
# # # # # # # # #                 "title": f"Missing Supplier Data — {cn} External Components",
# # # # # # # # #                 "detail": (f"{cn} of {external_n} external components have no named supplier. "
# # # # # # # # #                            f"Single-source risk cannot be assessed for these."),
# # # # # # # # #                 "action": "Procurement to verify and update BOM with supplier names and lead times.",
# # # # # # # # #             })
# # # # # # # # #         if 0 < us <= 2:
# # # # # # # # #             risks.append({
# # # # # # # # #                 "icon": "⚠", "sev": 2, "color": "#F59E0B", "bg": "#FFFBEB",
# # # # # # # # #                 "title": f"Supplier Concentration — {us} Unique Supplier(s)",
# # # # # # # # #                 "detail": f"High dependency on {us} supplier(s). Any disruption cascades to multiple components simultaneously.",
# # # # # # # # #                 "action": "Evaluate dual-sourcing for critical external components.",
# # # # # # # # #             })
# # # # # # # # #         ext_comps = bsn[bsn["Procurement type"] == "F"]
# # # # # # # # #         if len(ext_comps) > 0:
# # # # # # # # #             locs = list(set([str(r) for r in bsn[bsn["Procurement type"] == "F"]["Supplier Location"].dropna().tolist()[:4]]))
# # # # # # # # #             risks.append({
# # # # # # # # #                 "icon": "🌍", "sev": 1, "color": "#3B82F6", "bg": "#EFF6FF",
# # # # # # # # #                 "title": f"External Procurement: {len(ext_comps)} Components",
# # # # # # # # #                 "detail": (f"External components depend on supplier availability and transit times. "
# # # # # # # # #                            f"Suppliers located in: {', '.join(locs)}."),
# # # # # # # # #                 "action": "Review external component lead times — stock buffers for long-transit items.",
# # # # # # # # #             })

# # # # # # # # #         if not risks:
# # # # # # # # #             st.markdown(
# # # # # # # # #                 "<div style='padding:10px 13px;background:var(--gbg);border:1px solid rgba(34,197,94,0.2);"
# # # # # # # # #                 "border-radius:var(--r);font-size:12px;color:#14532d;'>"
# # # # # # # # #                 "✓ No critical propagation risks identified.</div>",
# # # # # # # # #                 unsafe_allow_html=True,
# # # # # # # # #             )
# # # # # # # # #         else:
# # # # # # # # #             for r in sorted(risks, key=lambda x: -x["sev"]):
# # # # # # # # #                 st.markdown(
# # # # # # # # #                     f"<div style='background:{r['bg']};border:1px solid {r['color']}40;"
# # # # # # # # #                     f"border-left:4px solid {r['color']};border-radius:var(--r);"
# # # # # # # # #                     f"padding:12px 14px;margin-bottom:8px;'>"
# # # # # # # # #                     f"<div style='display:flex;align-items:center;gap:8px;margin-bottom:5px;'>"
# # # # # # # # #                     f"<span style='font-size:16px;'>{r['icon']}</span>"
# # # # # # # # #                     f"<div style='font-size:12px;font-weight:800;color:{r['color']};'>{r['title']}</div>"
# # # # # # # # #                     f"</div>"
# # # # # # # # #                     f"<div style='font-size:11px;color:var(--t2);margin-bottom:5px;'>{r['detail']}</div>"
# # # # # # # # #                     f"<div style='font-size:11px;color:{r['color']};font-weight:600;'>→ {r['action']}</div>"
# # # # # # # # #                     f"</div>",
# # # # # # # # #                     unsafe_allow_html=True,
# # # # # # # # #                 )

# # # # # # # # #         # Consolidation opportunities
# # # # # # # # #         consol2   = get_supplier_consolidation(data, summary)
# # # # # # # # #         relevant2 = consol2[
# # # # # # # # #             consol2.material_list.apply(lambda x: snid in x)
# # # # # # # # #             & (consol2.finished_goods_supplied > 1)
# # # # # # # # #             & consol2.consolidation_opportunity
# # # # # # # # #         ]
# # # # # # # # #         if len(relevant2) > 0:
# # # # # # # # #             sec("Supplier Consolidation Opportunities")
# # # # # # # # #             for _, r2 in relevant2.iterrows():
# # # # # # # # #                 others = [MATERIAL_LABELS.get(m, m)[:18] for m in r2["material_list"] if m != snid]
# # # # # # # # #                 st.markdown(
# # # # # # # # #                     f"<div class='prow'><div style='font-size:14px;'>🏭</div>"
# # # # # # # # #                     f"<div style='flex:1;'>"
# # # # # # # # #                     f"<div style='font-size:12px;font-weight:800;'>{r2['supplier']}</div>"
# # # # # # # # #                     f"<div style='font-size:10px;color:var(--t3);'>{r2['city']} · {r2['email']}</div>"
# # # # # # # # #                     f"<div style='font-size:10px;color:var(--t2);margin-top:2px;'>Also supplies: {', '.join(others[:3])}</div>"
# # # # # # # # #                     f"</div>"
# # # # # # # # #                     f"<div style='font-size:10px;font-weight:700;color:var(--or);'>⚡ Consolidate order</div>"
# # # # # # # # #                     f"</div>",
# # # # # # # # #                     unsafe_allow_html=True,
# # # # # # # # #                 )

# # # # # # # # #         # ── Ask ARIA with rich BOM context (including Standard Price) ─────────
# # # # # # # # #         if st.session_state.azure_client:
# # # # # # # # #             sec("Ask ARIA About This Network")
# # # # # # # # #             st.info("ℹ️ This assistant provides supplier‑related insights only for the currently selected finished good.")
# # # # # # # # #             uq = st.text_input(
# # # # # # # # #                 "Question",
# # # # # # # # #                 placeholder="e.g. Which supplier provides more than 1 material for DELFIA Wash Concentrate?",
# # # # # # # # #                 key="snq", label_visibility="collapsed",
# # # # # # # # #             )
# # # # # # # # #             if uq and st.button("Ask ARIA", key="sna"):
# # # # # # # # #                 bom_lines = []
# # # # # # # # #                 for _, row in bsn.iterrows():
# # # # # # # # #                     mat_desc = str(row["Material Description"])[:40] if pd.notna(row["Material Description"]) else str(row["Material"])
# # # # # # # # #                     qty = row["Effective Order Qty"] if "Effective Order Qty" in row else row["Comp. Qty (CUn)"]
# # # # # # # # #                     fixed = "X (order exactly 1)" if row.get("Fixed Qty Flag") else ""
# # # # # # # # #                     sup = row.get("Supplier Display", "—")
# # # # # # # # #                     loc = row.get("Supplier Location", "—")
# # # # # # # # #                     transit = row.get("Transit Days", "—")
# # # # # # # # #                     reliability = row.get("Supplier Reliability", "—")
# # # # # # # # #                     std_price = row.get("Standard Price", "—")
# # # # # # # # #                     if pd.notna(std_price):
# # # # # # # # #                         std_price = f"${std_price:.2f}"
# # # # # # # # #                     bom_lines.append(f"- Component: {mat_desc} | Qty: {qty} {fixed} | Std Price: {std_price} | Supplier: {sup} | Location: {loc} | Transit: {transit}d | Reliability: {reliability}")
# # # # # # # # #                 bom_table = "\n".join(bom_lines)

# # # # # # # # #                 ctx3 = (
# # # # # # # # #                     f"Material: {snr['name']} (ID: {snid})\n"
# # # # # # # # #                     f"Risk: {snr['risk']}\n"
# # # # # # # # #                     f"Total components: {tc}\n"
# # # # # # # # #                     f"Inhouse components: {inhouse_n}\n"
# # # # # # # # #                     f"External components: {external_n}\n"
# # # # # # # # #                     f"Missing supplier data: {cn} components\n"
# # # # # # # # #                     f"Unique external suppliers: {us}\n"
# # # # # # # # #                     f"BOM details:\n{bom_table}"
# # # # # # # # #                 )
# # # # # # # # #                 with st.spinner("Thinking…"):
# # # # # # # # #                     ans = chat_with_data(st.session_state.azure_client, AZURE_DEPLOYMENT, uq, ctx3)
# # # # # # # # #                 st.markdown(
# # # # # # # # #                     f"<div class='ic' style='margin-top:8px;'><div class='il'>◈ ARIA</div>"
# # # # # # # # #                     f"<div class='ib'>{ans}</div></div>",
# # # # # # # # #                     unsafe_allow_html=True,
# # # # # # # # #                 )

# # # # # # # # #     st.markdown('<div class="pfooter">🕸️ Powered by <strong>MResult</strong></div>', unsafe_allow_html=True)

# # # # # # # # """
# # # # # # # # tabs/supply_network.py
# # # # # # # # Supply Network tab: BOM propagation map (Sankey diagram), component detail table,
# # # # # # # # risk cascade analysis, and supplier consolidation opportunities.
# # # # # # # # """

# # # # # # # # import streamlit as st
# # # # # # # # import pandas as pd
# # # # # # # # import plotly.graph_objects as go

# # # # # # # # from st_aggrid import AgGrid, GridOptionsBuilder, JsCode

# # # # # # # # from utils.helpers import sec, note, sbadge, ORANGE, AZURE_DEPLOYMENT
# # # # # # # # from data_loader import get_bom_components, get_supplier_consolidation
# # # # # # # # from agent import interpret_chart, chat_with_data

# # # # # # # # _AGGRID_CSS = {
# # # # # # # #     ".ag-root-wrapper": {"border": "1px solid #E2E8F0!important", "border-radius": "12px!important"},
# # # # # # # #     ".ag-header":       {"background": "#F8FAFE!important"},
# # # # # # # #     ".ag-row-even":     {"background": "#FFFFFF!important"},
# # # # # # # #     ".ag-row-odd":      {"background": "#F8FAFE!important"},
# # # # # # # # }


# # # # # # # # def render():
# # # # # # # #     data            = st.session_state.data
# # # # # # # #     summary         = st.session_state.summary
# # # # # # # #     MATERIAL_LABELS = st.session_state.material_labels

# # # # # # # #     st.markdown(
# # # # # # # #         "<div style='font-size:15px;font-weight:800;margin-bottom:4px;'>Supply Network</div>"
# # # # # # # #         "<div style='font-size:12px;color:var(--t3);margin-bottom:14px;'>"
# # # # # # # #         "BOM structure · Supplier locations · Risk cascade · Consolidation intelligence</div>",
# # # # # # # #         unsafe_allow_html=True,
# # # # # # # #     )

# # # # # # # #     snn  = st.selectbox("Finished Good", [r["name"] for _, r in summary.iterrows()], key="snm")
# # # # # # # #     snid = summary[summary.name == snn]["material"].values[0]
# # # # # # # #     snr  = summary[summary.material == snid].iloc[0]
# # # # # # # #     bsn  = get_bom_components(data, snid)

# # # # # # # #     if not len(bsn):
# # # # # # # #         st.markdown(
# # # # # # # #             "<div class='flag-box'><div style='font-size:22px;margin-bottom:8px;'>🕸️</div>"
# # # # # # # #             "<div style='font-size:14px;font-weight:800;color:var(--t2);'>No BOM data for this material</div></div>",
# # # # # # # #             unsafe_allow_html=True,
# # # # # # # #         )
# # # # # # # #         return

# # # # # # # #     cw        = int(bsn["Supplier Name(Vendor)"].notna().sum())
# # # # # # # #     cn        = len(bsn[bsn["Supplier Display"].str.startswith("⚠", na=False)])
# # # # # # # #     us        = int(bsn["Supplier Name(Vendor)"].dropna().nunique())
# # # # # # # #     tc        = len(bsn)
# # # # # # # #     inhouse_n = int((bsn["Procurement type"] == "E").sum())
# # # # # # # #     external_n = int((bsn["Procurement type"] == "F").sum())

# # # # # # # #     n1, n2, n3, n4 = st.columns(4)
# # # # # # # #     for col, val, lbl, vc in [
# # # # # # # #         (n1, tc,        "Total Components",  "#1E293B"),
# # # # # # # #         (n2, inhouse_n, "Revvity Inhouse",   "#22C55E"),
# # # # # # # #         (n3, cn,        "Missing Supplier",  "#F59E0B" if cn > 0 else "#1E293B"),
# # # # # # # #         (n4, us,        "Unique Ext Suppliers", "#1E293B"),
# # # # # # # #     ]:
# # # # # # # #         with col:
# # # # # # # #             st.markdown(
# # # # # # # #                 f"<div class='sc'><div style='flex:1;'>"
# # # # # # # #                 f"<div class='sv' style='color:{vc};'>{val}</div>"
# # # # # # # #                 f"<div class='sl'>{lbl}</div></div></div>",
# # # # # # # #                 unsafe_allow_html=True,
# # # # # # # #             )

# # # # # # # #     sn_tab, comp_tab, risk_tab = st.tabs(["🕸️  BOM Map", "📋  Components", "⚠️  Risk Analysis"])

# # # # # # # #     # ── BOM Map – Sankey diagram with clean legend ──────────────────────────────
# # # # # # # #     with sn_tab:
# # # # # # # #         sec("BOM Propagation Map")
# # # # # # # #         # Clean legend using HTML list inside note box
# # # # # # # #         st.markdown("""
# # # # # # # #         <div class='note-box'>
# # # # # # # #         <strong>Colour legend:</strong>
# # # # # # # #         <ul style='margin:5px 0 0 20px; padding-left:0;'>
# # # # # # # #         <li>🔵 <strong>Blue</strong> = External component with named supplier</li>
# # # # # # # #         <li>🟢 <strong>Green</strong> = Inhouse component (Revvity)</li>
# # # # # # # #         <li>🟡 <strong>Amber</strong> = External component with <strong>missing supplier data</strong></li>
# # # # # # # #         <li>🟣 <strong>Purple</strong> = Supplier node</li>
# # # # # # # #         <li>Root node colour matches finished good risk (🔴 Critical / 🟠 Warning / 🟢 Healthy)</li>
# # # # # # # #         </ul>
# # # # # # # #         Hover over nodes for details.
# # # # # # # #         </div>
# # # # # # # #         """, unsafe_allow_html=True)

# # # # # # # #         # Build node list and links for Sankey
# # # # # # # #         nodes = []
# # # # # # # #         node_colors = []
# # # # # # # #         node_map = {}

# # # # # # # #         # Root node (finished good)
# # # # # # # #         root_name = snr["name"]
# # # # # # # #         risk_color_map = {"CRITICAL": "#EF4444", "WARNING": "#F59E0B", "HEALTHY": "#22C55E"}
# # # # # # # #         root_color = risk_color_map.get(snr["risk"], "#94A3B8")
# # # # # # # #         nodes.append(root_name)
# # # # # # # #         node_colors.append(root_color)
# # # # # # # #         node_map[root_name] = 0

# # # # # # # #         sources = []
# # # # # # # #         targets = []
# # # # # # # #         values = []

# # # # # # # #         # Process each BOM row
# # # # # # # #         for _, row in bsn.iterrows():
# # # # # # # #             # Component label (truncated for readability)
# # # # # # # #             comp_desc = str(row["Material Description"])[:30] if pd.notna(row["Material Description"]) else str(row["Material"])
# # # # # # # #             comp_label = f"{comp_desc}"
# # # # # # # #             sup_display = row.get("Supplier Display", "—")
# # # # # # # #             proc_type = str(row.get("Procurement type", "")).strip()
# # # # # # # #             # Get quantity, default to 1
# # # # # # # #             qty_raw = row.get("Effective Order Qty", row["Comp. Qty (CUn)"])
# # # # # # # #             try:
# # # # # # # #                 qty = float(qty_raw) if pd.notna(qty_raw) else 1.0
# # # # # # # #             except:
# # # # # # # #                 qty = 1.0

# # # # # # # #             # Add component node if new
# # # # # # # #             if comp_label not in node_map:
# # # # # # # #                 # Determine colour
# # # # # # # #                 if proc_type == "E":
# # # # # # # #                     comp_color = "#22C55E"   # inhouse
# # # # # # # #                 elif sup_display.startswith("⚠"):
# # # # # # # #                     comp_color = "#F59E0B"   # missing supplier
# # # # # # # #                 else:
# # # # # # # #                     comp_color = "#3B82F6"   # external named
# # # # # # # #                 nodes.append(comp_label)
# # # # # # # #                 node_colors.append(comp_color)
# # # # # # # #                 node_map[comp_label] = len(nodes) - 1

# # # # # # # #             # Link root -> component
# # # # # # # #             sources.append(node_map[root_name])
# # # # # # # #             targets.append(node_map[comp_label])
# # # # # # # #             values.append(qty)

# # # # # # # #             # Add supplier node if external and named
# # # # # # # #             if sup_display not in ["Revvity Inhouse", "—"] and not sup_display.startswith("⚠"):
# # # # # # # #                 sup_label = sup_display[:25]
# # # # # # # #                 if sup_label not in node_map:
# # # # # # # #                     nodes.append(sup_label)
# # # # # # # #                     node_colors.append("#8B5CF6")  # purple
# # # # # # # #                     node_map[sup_label] = len(nodes) - 1
# # # # # # # #                 # Link component -> supplier
# # # # # # # #                 sources.append(node_map[comp_label])
# # # # # # # #                 targets.append(node_map[sup_label])
# # # # # # # #                 values.append(1.0)

# # # # # # # #         # Build Sankey figure
# # # # # # # #         fig = go.Figure(data=[go.Sankey(
# # # # # # # #             arrangement="snap",
# # # # # # # #             node=dict(
# # # # # # # #                 pad=15,
# # # # # # # #                 thickness=20,
# # # # # # # #                 line=dict(color="white", width=0.5),
# # # # # # # #                 label=nodes,
# # # # # # # #                 color=node_colors,
# # # # # # # #                 hovertemplate="<b>%{label}</b><extra></extra>"
# # # # # # # #             ),
# # # # # # # #             link=dict(
# # # # # # # #                 source=sources,
# # # # # # # #                 target=targets,
# # # # # # # #                 value=values,
# # # # # # # #                 color="rgba(160,160,160,0.4)"
# # # # # # # #             )
# # # # # # # #         )])
# # # # # # # #         fig.update_layout(
# # # # # # # #             title=None,
# # # # # # # #             font=dict(size=10, family="Inter", color="#1E293B"),
# # # # # # # #             height=500,
# # # # # # # #             margin=dict(l=10, r=10, t=10, b=10),
# # # # # # # #             paper_bgcolor="white",
# # # # # # # #             plot_bgcolor="white"
# # # # # # # #         )
# # # # # # # #         st.plotly_chart(fig, use_container_width=True)

# # # # # # # #         if st.session_state.azure_client:
# # # # # # # #             if st.button("◈ Interpret BOM Map", key="interp_bom_sankey"):
# # # # # # # #                 with st.spinner("ARIA interpreting…"):
# # # # # # # #                     bom_ctx = {
# # # # # # # #                         "material": snr["name"], "total_components": tc,
# # # # # # # #                         "inhouse": inhouse_n, "external_named": cw - inhouse_n,
# # # # # # # #                         "missing_supplier": cn, "unique_suppliers": us, "risk": snr["risk"],
# # # # # # # #                     }
# # # # # # # #                     interp = interpret_chart(
# # # # # # # #                         st.session_state.azure_client, AZURE_DEPLOYMENT,
# # # # # # # #                         "BOM Risk Propagation Map", bom_ctx,
# # # # # # # #                         "What are the key supply chain risks in this BOM and what should procurement prioritise?",
# # # # # # # #                     )
# # # # # # # #                 st.markdown(
# # # # # # # #                     f"<div class='ic' style='margin-top:8px;'><div class='il'>◈ ARIA</div>"
# # # # # # # #                     f"<div class='ib'>{interp}</div></div>",
# # # # # # # #                     unsafe_allow_html=True,
# # # # # # # #                 )

# # # # # # # #     # ── Component Detail ──────────────────────────────────────────────────────
# # # # # # # #     with comp_tab:
# # # # # # # #         sec("Component Detail")
# # # # # # # #         bom_display2 = []
# # # # # # # #         for _, b in bsn.iterrows():
# # # # # # # #             eff_qty = b.get("Effective Order Qty", b["Comp. Qty (CUn)"])
# # # # # # # #             fq_txt  = ("1 (Fixed)" if b.get("Fixed Qty Flag", False)
# # # # # # # #                        else str(round(float(eff_qty), 3)) if pd.notna(eff_qty) else "—")
# # # # # # # #             bom_display2.append({
# # # # # # # #                 "Material":    str(b["Material"]),
# # # # # # # #                 "Description": str(b["Material Description"])[:36] if pd.notna(b["Material Description"]) else "—",
# # # # # # # #                 "Level":       str(b["Level"])[:25] if pd.notna(b["Level"]) else "—",
# # # # # # # #                 "Qty":         fq_txt,
# # # # # # # #                 "Unit":        str(b["Component unit"]) if pd.notna(b["Component unit"]) else "—",
# # # # # # # #                 "Type":        b.get("Procurement Label", "—"),
# # # # # # # #                 "Supplier":    b.get("Supplier Display", "—"),
# # # # # # # #                 "Location":    b.get("Supplier Location", "—"),
# # # # # # # #                 "Transit":     f"{b.get('Transit Days', '—')}d" if b.get("Transit Days") is not None else "—",
# # # # # # # #                 "Std Price":   f"${b.get('Standard Price', 0):.2f}" if pd.notna(b.get('Standard Price')) else "—",
# # # # # # # #             })
# # # # # # # #         df_bd2  = pd.DataFrame(bom_display2)
# # # # # # # #         sup_r3  = JsCode("""class R{init(p){const v=p.value||'';this.e=document.createElement('span');if(v.startsWith('⚠')){this.e.style.cssText='background:#FEF3C7;color:#F59E0B;padding:2px 6px;border-radius:4px;font-size:10px;font-weight:600;';this.e.innerText=v;}else if(v==='Revvity Inhouse'){this.e.style.cssText='background:#DCFCE7;color:#16a34a;padding:2px 6px;border-radius:4px;font-size:10px;font-weight:600;';this.e.innerText='🏭 '+v;}else{this.e.style.cssText='background:#EFF6FF;color:#2563EB;padding:2px 6px;border-radius:4px;font-size:10px;';this.e.innerText='🚚 '+v;};}getGui(){return this.e;}}""")
# # # # # # # #         gb4     = GridOptionsBuilder.from_dataframe(df_bd2)
# # # # # # # #         gb4.configure_column("Material",    width=82)
# # # # # # # #         gb4.configure_column("Description", width=215)
# # # # # # # #         gb4.configure_column("Level",       width=85)
# # # # # # # #         gb4.configure_column("Qty",         width=75)
# # # # # # # #         gb4.configure_column("Unit",        width=50)
# # # # # # # #         gb4.configure_column("Type",        width=100)
# # # # # # # #         gb4.configure_column("Supplier",    width=170, cellRenderer=sup_r3)
# # # # # # # #         gb4.configure_column("Location",    width=130)
# # # # # # # #         gb4.configure_column("Transit",     width=58)
# # # # # # # #         gb4.configure_column("Std Price",   width=80)
# # # # # # # #         gb4.configure_grid_options(rowHeight=36, headerHeight=32)
# # # # # # # #         gb4.configure_default_column(resizable=True, sortable=True, filter=False)
# # # # # # # #         AgGrid(df_bd2, gridOptions=gb4.build(), height=320,
# # # # # # # #                allow_unsafe_jscode=True, theme="alpine", custom_css=_AGGRID_CSS)

# # # # # # # #     # ── Risk Cascade ──────────────────────────────────────────────────────────
# # # # # # # #     with risk_tab:
# # # # # # # #         sec("Risk Cascade Analysis")
# # # # # # # #         risks = []
# # # # # # # #         if snr["risk"] in ["CRITICAL", "WARNING"]:
# # # # # # # #             risks.append({
# # # # # # # #                 "icon": "⛔", "sev": 3, "color": "#EF4444", "bg": "#FEF2F2",
# # # # # # # #                 "title": f"Finished Good at {snr['risk'].title()} Risk",
# # # # # # # #                 "detail": (f"{snr['name']} has {round(snr['days_cover'])}d of cover. "
# # # # # # # #                            f"SIH={round(snr['sih'])} vs SAP SS={round(snr['safety_stock'])}. "
# # # # # # # #                            f"Production continuity at risk."),
# # # # # # # #                 "action": f"Order {int(snr.get('repl_quantity', 0))} units immediately. Contact procurement today.",
# # # # # # # #             })
# # # # # # # #         if cn > 0:
# # # # # # # #             risks.append({
# # # # # # # #                 "icon": "⚠", "sev": 2, "color": "#F59E0B", "bg": "#FFFBEB",
# # # # # # # #                 "title": f"Missing Supplier Data — {cn} External Components",
# # # # # # # #                 "detail": (f"{cn} of {external_n} external components have no named supplier. "
# # # # # # # #                            f"Single-source risk cannot be assessed for these."),
# # # # # # # #                 "action": "Procurement to verify and update BOM with supplier names and lead times.",
# # # # # # # #             })
# # # # # # # #         if 0 < us <= 2:
# # # # # # # #             risks.append({
# # # # # # # #                 "icon": "⚠", "sev": 2, "color": "#F59E0B", "bg": "#FFFBEB",
# # # # # # # #                 "title": f"Supplier Concentration — {us} Unique Supplier(s)",
# # # # # # # #                 "detail": f"High dependency on {us} supplier(s). Any disruption cascades to multiple components simultaneously.",
# # # # # # # #                 "action": "Evaluate dual-sourcing for critical external components.",
# # # # # # # #             })
# # # # # # # #         ext_comps = bsn[bsn["Procurement type"] == "F"]
# # # # # # # #         if len(ext_comps) > 0:
# # # # # # # #             locs = list(set([str(r) for r in bsn[bsn["Procurement type"] == "F"]["Supplier Location"].dropna().tolist()[:4]]))
# # # # # # # #             risks.append({
# # # # # # # #                 "icon": "🌍", "sev": 1, "color": "#3B82F6", "bg": "#EFF6FF",
# # # # # # # #                 "title": f"External Procurement: {len(ext_comps)} Components",
# # # # # # # #                 "detail": (f"External components depend on supplier availability and transit times. "
# # # # # # # #                            f"Suppliers located in: {', '.join(locs)}."),
# # # # # # # #                 "action": "Review external component lead times — stock buffers for long-transit items.",
# # # # # # # #             })

# # # # # # # #         if not risks:
# # # # # # # #             st.markdown(
# # # # # # # #                 "<div style='padding:10px 13px;background:var(--gbg);border:1px solid rgba(34,197,94,0.2);"
# # # # # # # #                 "border-radius:var(--r);font-size:12px;color:#14532d;'>"
# # # # # # # #                 "✓ No critical propagation risks identified.</div>",
# # # # # # # #                 unsafe_allow_html=True,
# # # # # # # #             )
# # # # # # # #         else:
# # # # # # # #             for r in sorted(risks, key=lambda x: -x["sev"]):
# # # # # # # #                 st.markdown(
# # # # # # # #                     f"<div style='background:{r['bg']};border:1px solid {r['color']}40;"
# # # # # # # #                     f"border-left:4px solid {r['color']};border-radius:var(--r);"
# # # # # # # #                     f"padding:12px 14px;margin-bottom:8px;'>"
# # # # # # # #                     f"<div style='display:flex;align-items:center;gap:8px;margin-bottom:5px;'>"
# # # # # # # #                     f"<span style='font-size:16px;'>{r['icon']}</span>"
# # # # # # # #                     f"<div style='font-size:12px;font-weight:800;color:{r['color']};'>{r['title']}</div>"
# # # # # # # #                     f"</div>"
# # # # # # # #                     f"<div style='font-size:11px;color:var(--t2);margin-bottom:5px;'>{r['detail']}</div>"
# # # # # # # #                     f"<div style='font-size:11px;color:{r['color']};font-weight:600;'>→ {r['action']}</div>"
# # # # # # # #                     f"</div>",
# # # # # # # #                     unsafe_allow_html=True,
# # # # # # # #                 )

# # # # # # # #         # Consolidation opportunities
# # # # # # # #         consol2   = get_supplier_consolidation(data, summary)
# # # # # # # #         relevant2 = consol2[
# # # # # # # #             consol2.material_list.apply(lambda x: snid in x)
# # # # # # # #             & (consol2.finished_goods_supplied > 1)
# # # # # # # #             & consol2.consolidation_opportunity
# # # # # # # #         ]
# # # # # # # #         if len(relevant2) > 0:
# # # # # # # #             sec("Supplier Consolidation Opportunities")
# # # # # # # #             for _, r2 in relevant2.iterrows():
# # # # # # # #                 others = [MATERIAL_LABELS.get(m, m)[:18] for m in r2["material_list"] if m != snid]
# # # # # # # #                 st.markdown(
# # # # # # # #                     f"<div class='prow'><div style='font-size:14px;'>🏭</div>"
# # # # # # # #                     f"<div style='flex:1;'>"
# # # # # # # #                     f"<div style='font-size:12px;font-weight:800;'>{r2['supplier']}</div>"
# # # # # # # #                     f"<div style='font-size:10px;color:var(--t3);'>{r2['city']} · {r2['email']}</div>"
# # # # # # # #                     f"<div style='font-size:10px;color:var(--t2);margin-top:2px;'>Also supplies: {', '.join(others[:3])}</div>"
# # # # # # # #                     f"</div>"
# # # # # # # #                     f"<div style='font-size:10px;font-weight:700;color:var(--or);'>⚡ Consolidate order</div>"
# # # # # # # #                     f"</div>",
# # # # # # # #                     unsafe_allow_html=True,
# # # # # # # #                 )

# # # # # # # #         # ── Ask ARIA with rich BOM context (including Standard Price) ─────────
# # # # # # # #         if st.session_state.azure_client:
# # # # # # # #             sec("Ask ARIA About This Network")
# # # # # # # #             st.info("ℹ️ This assistant provides supplier‑related insights only for the currently selected finished good.")
# # # # # # # #             uq = st.text_input(
# # # # # # # #                 "Question",
# # # # # # # #                 placeholder="e.g. Which supplier provides more than 1 material for DELFIA Wash Concentrate?",
# # # # # # # #                 key="snq", label_visibility="collapsed",
# # # # # # # #             )
# # # # # # # #             if uq and st.button("Ask ARIA", key="sna"):
# # # # # # # #                 bom_lines = []
# # # # # # # #                 for _, row in bsn.iterrows():
# # # # # # # #                     mat_desc = str(row["Material Description"])[:40] if pd.notna(row["Material Description"]) else str(row["Material"])
# # # # # # # #                     qty = row["Effective Order Qty"] if "Effective Order Qty" in row else row["Comp. Qty (CUn)"]
# # # # # # # #                     fixed = "X (order exactly 1)" if row.get("Fixed Qty Flag") else ""
# # # # # # # #                     sup = row.get("Supplier Display", "—")
# # # # # # # #                     loc = row.get("Supplier Location", "—")
# # # # # # # #                     transit = row.get("Transit Days", "—")
# # # # # # # #                     reliability = row.get("Supplier Reliability", "—")
# # # # # # # #                     std_price = row.get("Standard Price", "—")
# # # # # # # #                     if pd.notna(std_price):
# # # # # # # #                         std_price = f"${std_price:.2f}"
# # # # # # # #                     bom_lines.append(f"- Component: {mat_desc} | Qty: {qty} {fixed} | Std Price: {std_price} | Supplier: {sup} | Location: {loc} | Transit: {transit}d | Reliability: {reliability}")
# # # # # # # #                 bom_table = "\n".join(bom_lines)

# # # # # # # #                 ctx3 = (
# # # # # # # #                     f"Material: {snr['name']} (ID: {snid})\n"
# # # # # # # #                     f"Risk: {snr['risk']}\n"
# # # # # # # #                     f"Total components: {tc}\n"
# # # # # # # #                     f"Inhouse components: {inhouse_n}\n"
# # # # # # # #                     f"External components: {external_n}\n"
# # # # # # # #                     f"Missing supplier data: {cn} components\n"
# # # # # # # #                     f"Unique external suppliers: {us}\n"
# # # # # # # #                     f"BOM details:\n{bom_table}"
# # # # # # # #                 )
# # # # # # # #                 with st.spinner("Thinking…"):
# # # # # # # #                     ans = chat_with_data(st.session_state.azure_client, AZURE_DEPLOYMENT, uq, ctx3)
# # # # # # # #                 st.markdown(
# # # # # # # #                     f"<div class='ic' style='margin-top:8px;'><div class='il'>◈ ARIA</div>"
# # # # # # # #                     f"<div class='ib'>{ans}</div></div>",
# # # # # # # #                     unsafe_allow_html=True,
# # # # # # # #                 )

# # # # # # # #     st.markdown('<div class="pfooter">🕸️ Powered by <strong>MResult</strong></div>', unsafe_allow_html=True)

# # # # # # # """
# # # # # # # tabs/supply_network.py
# # # # # # # Supply Network tab: BOM propagation map (Sankey diagram), component detail table,
# # # # # # # risk cascade analysis, and supplier consolidation opportunities.

# # # # # # # FIXES (Sankey):
# # # # # # #   1. Node keys now use material/supplier IDs, not truncated labels → no collisions
# # # # # # #   2. qty is clamped to 0.01 minimum → Sankey never drops zero-value links silently
# # # # # # #   3. Supplier→component links use actual qty, not hardcoded 1.0 → flow conserved
# # # # # # #   4. customdata + hovertemplate added → clean hover tooltips
# # # # # # #   5. sup_display null/empty guard added → no KeyError / ⚠ false-positives
# # # # # # # """

# # # # # # # import streamlit as st
# # # # # # # import pandas as pd
# # # # # # # import plotly.graph_objects as go

# # # # # # # from st_aggrid import AgGrid, GridOptionsBuilder, JsCode

# # # # # # # from utils.helpers import sec, note, sbadge, ORANGE, AZURE_DEPLOYMENT
# # # # # # # from data_loader import get_bom_components, get_supplier_consolidation
# # # # # # # from agent import interpret_chart, chat_with_data

# # # # # # # _AGGRID_CSS = {
# # # # # # #     ".ag-root-wrapper": {"border": "1px solid #E2E8F0!important", "border-radius": "12px!important"},
# # # # # # #     ".ag-header":       {"background": "#F8FAFE!important"},
# # # # # # #     ".ag-row-even":     {"background": "#FFFFFF!important"},
# # # # # # #     ".ag-row-odd":      {"background": "#F8FAFE!important"},
# # # # # # # }


# # # # # # # def render():
# # # # # # #     data            = st.session_state.data
# # # # # # #     summary         = st.session_state.summary
# # # # # # #     MATERIAL_LABELS = st.session_state.material_labels

# # # # # # #     st.markdown(
# # # # # # #         "<div style='font-size:15px;font-weight:800;margin-bottom:4px;'>Supply Network</div>"
# # # # # # #         "<div style='font-size:12px;color:var(--t3);margin-bottom:14px;'>"
# # # # # # #         "BOM structure · Supplier locations · Risk cascade · Consolidation intelligence</div>",
# # # # # # #         unsafe_allow_html=True,
# # # # # # #     )

# # # # # # #     snn  = st.selectbox("Finished Good", [r["name"] for _, r in summary.iterrows()], key="snm")
# # # # # # #     snid = summary[summary.name == snn]["material"].values[0]
# # # # # # #     snr  = summary[summary.material == snid].iloc[0]
# # # # # # #     bsn  = get_bom_components(data, snid)

# # # # # # #     if not len(bsn):
# # # # # # #         st.markdown(
# # # # # # #             "<div class='flag-box'><div style='font-size:22px;margin-bottom:8px;'>🕸️</div>"
# # # # # # #             "<div style='font-size:14px;font-weight:800;color:var(--t2);'>No BOM data for this material</div></div>",
# # # # # # #             unsafe_allow_html=True,
# # # # # # #         )
# # # # # # #         return

# # # # # # #     cw        = int(bsn["Supplier Name(Vendor)"].notna().sum())
# # # # # # #     cn        = len(bsn[bsn["Supplier Display"].str.startswith("⚠", na=False)])
# # # # # # #     us        = int(bsn["Supplier Name(Vendor)"].dropna().nunique())
# # # # # # #     tc        = len(bsn)
# # # # # # #     inhouse_n = int((bsn["Procurement type"] == "E").sum())
# # # # # # #     external_n = int((bsn["Procurement type"] == "F").sum())

# # # # # # #     n1, n2, n3, n4 = st.columns(4)
# # # # # # #     for col, val, lbl, vc in [
# # # # # # #         (n1, tc,        "Total Components",     "#1E293B"),
# # # # # # #         (n2, inhouse_n, "Revvity Inhouse",      "#22C55E"),
# # # # # # #         (n3, cn,        "Missing Supplier",     "#F59E0B" if cn > 0 else "#1E293B"),
# # # # # # #         (n4, us,        "Unique Ext Suppliers", "#1E293B"),
# # # # # # #     ]:
# # # # # # #         with col:
# # # # # # #             st.markdown(
# # # # # # #                 f"<div class='sc'><div style='flex:1;'>"
# # # # # # #                 f"<div class='sv' style='color:{vc};'>{val}</div>"
# # # # # # #                 f"<div class='sl'>{lbl}</div></div></div>",
# # # # # # #                 unsafe_allow_html=True,
# # # # # # #             )

# # # # # # #     sn_tab, comp_tab, risk_tab = st.tabs(["🕸️  BOM Map", "📋  Components", "⚠️  Risk Analysis"])

# # # # # # #     # ── BOM Map – Sankey diagram ─────────────────────────────────────────────
# # # # # # #     with sn_tab:
# # # # # # #         sec("BOM Propagation Map")
# # # # # # #         st.markdown("""
# # # # # # #         <div class='note-box'>
# # # # # # #         <strong>Colour legend:</strong>
# # # # # # #         <ul style='margin:5px 0 0 20px; padding-left:0;'>
# # # # # # #         <li>🔵 <strong>Blue</strong> = External component with named supplier</li>
# # # # # # #         <li>🟢 <strong>Green</strong> = Inhouse component (Revvity)</li>
# # # # # # #         <li>🟡 <strong>Amber</strong> = External component with <strong>missing supplier data</strong></li>
# # # # # # #         <li>🟣 <strong>Purple</strong> = Supplier node</li>
# # # # # # #         <li>Root node colour matches finished good risk (🔴 Critical / 🟠 Warning / 🟢 Healthy)</li>
# # # # # # #         </ul>
# # # # # # #         Hover over nodes for details.
# # # # # # #         </div>
# # # # # # #         """, unsafe_allow_html=True)

# # # # # # #         # ── Node/link builders ────────────────────────────────────────────────
# # # # # # #         risk_color_map = {"CRITICAL": "#EF4444", "WARNING": "#F59E0B", "HEALTHY": "#22C55E"}

# # # # # # #         nodes        = []   # display labels
# # # # # # #         node_colors  = []
# # # # # # #         node_custom  = []   # shown in hovertemplate
# # # # # # #         node_map     = {}   # stable key → index  (FIX 1: key ≠ label)

# # # # # # #         def _add_node(key: str, label: str, color: str, custom: str) -> int:
# # # # # # #             """Add node only if key is new; always return its index."""
# # # # # # #             if key not in node_map:
# # # # # # #                 node_map[key] = len(nodes)
# # # # # # #                 nodes.append(label)
# # # # # # #                 node_colors.append(color)
# # # # # # #                 node_custom.append(custom)
# # # # # # #             return node_map[key]

# # # # # # #         sources, targets, values, link_labels = [], [], [], []

# # # # # # #         # Root (finished good)
# # # # # # #         root_key   = f"FG_{snid}"
# # # # # # #         root_color = risk_color_map.get(snr["risk"], "#94A3B8")
# # # # # # #         root_idx   = _add_node(
# # # # # # #             root_key,
# # # # # # #             snr["name"][:40],
# # # # # # #             root_color,
# # # # # # #             f"{snr['name']} | Risk: {snr['risk']} | Cover: {round(snr['days_cover'])}d",
# # # # # # #         )

# # # # # # #         for _, row in bsn.iterrows():
# # # # # # #             mat_id     = str(row["Material"])
# # # # # # #             comp_desc  = (str(row["Material Description"])[:30]
# # # # # # #                           if pd.notna(row["Material Description"]) else mat_id)

# # # # # # #             # FIX 1: key uses stable mat_id; label uses human description
# # # # # # #             comp_key   = f"COMP_{mat_id}"
# # # # # # #             comp_label = comp_desc

# # # # # # #             sup_display = str(row.get("Supplier Display") or "—").strip()
# # # # # # #             proc_type   = str(row.get("Procurement type") or "").strip()

# # # # # # #             # FIX 2: clamp qty to avoid zero/NaN links being silently dropped
# # # # # # #             qty_raw = row.get("Effective Order Qty", row.get("Comp. Qty (CUn)", 1.0))
# # # # # # #             try:
# # # # # # #                 qty = float(qty_raw) if pd.notna(qty_raw) else 1.0
# # # # # # #             except Exception:
# # # # # # #                 qty = 1.0
# # # # # # #             qty = max(qty, 0.01)

# # # # # # #             # Component colour + hover text
# # # # # # #             if proc_type == "E":
# # # # # # #                 comp_color  = "#22C55E"
# # # # # # #                 comp_custom = f"{comp_desc} | Inhouse (Revvity) | Qty: {qty}"
# # # # # # #             elif sup_display.startswith("⚠") or sup_display in ("—", ""):
# # # # # # #                 comp_color  = "#F59E0B"
# # # # # # #                 comp_custom = f"{comp_desc} | ⚠ Missing Supplier | Qty: {qty}"
# # # # # # #             else:
# # # # # # #                 comp_color  = "#3B82F6"
# # # # # # #                 transit     = row.get("Transit Days", "—")
# # # # # # #                 comp_custom = (f"{comp_desc} | Supplier: {sup_display} "
# # # # # # #                                f"| Qty: {qty} | Transit: {transit}d")

# # # # # # #             comp_idx = _add_node(comp_key, comp_label, comp_color, comp_custom)

# # # # # # #             # Root → Component link
# # # # # # #             sources.append(root_idx)
# # # # # # #             targets.append(comp_idx)
# # # # # # #             values.append(qty)
# # # # # # #             link_labels.append(f"{comp_desc}: qty {qty}")

# # # # # # #             # Component → Supplier link (only for external, named suppliers)
# # # # # # #             # FIX 3: use actual qty (not hardcoded 1.0) so flow is conserved
# # # # # # #             is_named_external = (
# # # # # # #                 proc_type == "F"
# # # # # # #                 and sup_display not in ("—", "", "Revvity Inhouse")
# # # # # # #                 and not sup_display.startswith("⚠")
# # # # # # #             )
# # # # # # #             if is_named_external:
# # # # # # #                 sup_key   = f"SUP_{sup_display}"
# # # # # # #                 sup_label = sup_display[:28]
# # # # # # #                 loc       = str(row.get("Supplier Location") or "—")
# # # # # # #                 rel       = row.get("Supplier Reliability", "—")
# # # # # # #                 sup_custom = f"Supplier: {sup_display} | Location: {loc} | Reliability: {rel}"

# # # # # # #                 sup_idx = _add_node(sup_key, sup_label, "#8B5CF6", sup_custom)

# # # # # # #                 sources.append(comp_idx)
# # # # # # #                 targets.append(sup_idx)
# # # # # # #                 values.append(qty)                          # FIX 3
# # # # # # #                 link_labels.append(f"{comp_desc} → {sup_label}")

# # # # # # #         # ── Build figure ──────────────────────────────────────────────────────
# # # # # # #         fig = go.Figure(data=[go.Sankey(
# # # # # # #             arrangement="snap",
# # # # # # #             node=dict(
# # # # # # #                 pad=18,
# # # # # # #                 thickness=22,
# # # # # # #                 line=dict(color="white", width=0.8),
# # # # # # #                 label=nodes,
# # # # # # #                 color=node_colors,
# # # # # # #                 # FIX 4: customdata drives the hovertemplate
# # # # # # #                 customdata=node_custom,
# # # # # # #                 hovertemplate="<b>%{customdata}</b><extra></extra>",
# # # # # # #             ),
# # # # # # #             link=dict(
# # # # # # #                 source=sources,
# # # # # # #                 target=targets,
# # # # # # #                 value=values,
# # # # # # #                 label=link_labels,
# # # # # # #                 color="rgba(160,160,160,0.35)",
# # # # # # #                 hovertemplate=(
# # # # # # #                     "<b>%{label}</b><br>"
# # # # # # #                     "Flow value: %{value:.2f}<extra></extra>"
# # # # # # #                 ),
# # # # # # #             ),
# # # # # # #         )])

# # # # # # #         fig.update_layout(
# # # # # # #             title=None,
# # # # # # #             font=dict(size=10, family="Inter", color="#1E293B"),
# # # # # # #             height=520,
# # # # # # #             margin=dict(l=10, r=10, t=10, b=10),
# # # # # # #             paper_bgcolor="white",
# # # # # # #             plot_bgcolor="white",
# # # # # # #         )

# # # # # # #         st.plotly_chart(fig, use_container_width=True)

# # # # # # #         if st.session_state.azure_client:
# # # # # # #             if st.button("◈ Interpret BOM Map", key="interp_bom_sankey"):
# # # # # # #                 with st.spinner("ARIA interpreting…"):
# # # # # # #                     bom_ctx = {
# # # # # # #                         "material": snr["name"], "total_components": tc,
# # # # # # #                         "inhouse": inhouse_n, "external_named": cw - inhouse_n,
# # # # # # #                         "missing_supplier": cn, "unique_suppliers": us, "risk": snr["risk"],
# # # # # # #                     }
# # # # # # #                     interp = interpret_chart(
# # # # # # #                         st.session_state.azure_client, AZURE_DEPLOYMENT,
# # # # # # #                         "BOM Risk Propagation Map", bom_ctx,
# # # # # # #                         "What are the key supply chain risks in this BOM and what should procurement prioritise?",
# # # # # # #                     )
# # # # # # #                 st.markdown(
# # # # # # #                     f"<div class='ic' style='margin-top:8px;'><div class='il'>◈ ARIA</div>"
# # # # # # #                     f"<div class='ib'>{interp}</div></div>",
# # # # # # #                     unsafe_allow_html=True,
# # # # # # #                 )

# # # # # # #     # ── Component Detail ──────────────────────────────────────────────────────
# # # # # # #     with comp_tab:
# # # # # # #         sec("Component Detail")
# # # # # # #         bom_display2 = []
# # # # # # #         for _, b in bsn.iterrows():
# # # # # # #             eff_qty = b.get("Effective Order Qty", b["Comp. Qty (CUn)"])
# # # # # # #             fq_txt  = ("1 (Fixed)" if b.get("Fixed Qty Flag", False)
# # # # # # #                        else str(round(float(eff_qty), 3)) if pd.notna(eff_qty) else "—")
# # # # # # #             bom_display2.append({
# # # # # # #                 "Material":    str(b["Material"]),
# # # # # # #                 "Description": str(b["Material Description"])[:36] if pd.notna(b["Material Description"]) else "—",
# # # # # # #                 "Level":       str(b["Level"])[:25] if pd.notna(b["Level"]) else "—",
# # # # # # #                 "Qty":         fq_txt,
# # # # # # #                 "Unit":        str(b["Component unit"]) if pd.notna(b["Component unit"]) else "—",
# # # # # # #                 "Type":        b.get("Procurement Label", "—"),
# # # # # # #                 "Supplier":    b.get("Supplier Display", "—"),
# # # # # # #                 "Location":    b.get("Supplier Location", "—"),
# # # # # # #                 "Transit":     f"{b.get('Transit Days', '—')}d" if b.get("Transit Days") is not None else "—",
# # # # # # #                 "Std Price":   f"${b.get('Standard Price', 0):.2f}" if pd.notna(b.get('Standard Price')) else "—",
# # # # # # #             })
# # # # # # #         df_bd2  = pd.DataFrame(bom_display2)
# # # # # # #         sup_r3  = JsCode("""class R{init(p){const v=p.value||'';this.e=document.createElement('span');if(v.startsWith('⚠')){this.e.style.cssText='background:#FEF3C7;color:#F59E0B;padding:2px 6px;border-radius:4px;font-size:10px;font-weight:600;';this.e.innerText=v;}else if(v==='Revvity Inhouse'){this.e.style.cssText='background:#DCFCE7;color:#16a34a;padding:2px 6px;border-radius:4px;font-size:10px;font-weight:600;';this.e.innerText='🏭 '+v;}else{this.e.style.cssText='background:#EFF6FF;color:#2563EB;padding:2px 6px;border-radius:4px;font-size:10px;';this.e.innerText='🚚 '+v;};}getGui(){return this.e;}}""")
# # # # # # #         gb4     = GridOptionsBuilder.from_dataframe(df_bd2)
# # # # # # #         gb4.configure_column("Material",    width=82)
# # # # # # #         gb4.configure_column("Description", width=215)
# # # # # # #         gb4.configure_column("Level",       width=85)
# # # # # # #         gb4.configure_column("Qty",         width=75)
# # # # # # #         gb4.configure_column("Unit",        width=50)
# # # # # # #         gb4.configure_column("Type",        width=100)
# # # # # # #         gb4.configure_column("Supplier",    width=170, cellRenderer=sup_r3)
# # # # # # #         gb4.configure_column("Location",    width=130)
# # # # # # #         gb4.configure_column("Transit",     width=58)
# # # # # # #         gb4.configure_column("Std Price",   width=80)
# # # # # # #         gb4.configure_grid_options(rowHeight=36, headerHeight=32)
# # # # # # #         gb4.configure_default_column(resizable=True, sortable=True, filter=False)
# # # # # # #         AgGrid(df_bd2, gridOptions=gb4.build(), height=320,
# # # # # # #                allow_unsafe_jscode=True, theme="alpine", custom_css=_AGGRID_CSS)

# # # # # # #     # ── Risk Cascade ──────────────────────────────────────────────────────────
# # # # # # #     with risk_tab:
# # # # # # #         sec("Risk Cascade Analysis")
# # # # # # #         risks = []
# # # # # # #         if snr["risk"] in ["CRITICAL", "WARNING"]:
# # # # # # #             risks.append({
# # # # # # #                 "icon": "⛔", "sev": 3, "color": "#EF4444", "bg": "#FEF2F2",
# # # # # # #                 "title": f"Finished Good at {snr['risk'].title()} Risk",
# # # # # # #                 "detail": (f"{snr['name']} has {round(snr['days_cover'])}d of cover. "
# # # # # # #                            f"SIH={round(snr['sih'])} vs SAP SS={round(snr['safety_stock'])}. "
# # # # # # #                            f"Production continuity at risk."),
# # # # # # #                 "action": f"Order {int(snr.get('repl_quantity', 0))} units immediately. Contact procurement today.",
# # # # # # #             })
# # # # # # #         if cn > 0:
# # # # # # #             risks.append({
# # # # # # #                 "icon": "⚠", "sev": 2, "color": "#F59E0B", "bg": "#FFFBEB",
# # # # # # #                 "title": f"Missing Supplier Data — {cn} External Components",
# # # # # # #                 "detail": (f"{cn} of {external_n} external components have no named supplier. "
# # # # # # #                            f"Single-source risk cannot be assessed for these."),
# # # # # # #                 "action": "Procurement to verify and update BOM with supplier names and lead times.",
# # # # # # #             })
# # # # # # #         if 0 < us <= 2:
# # # # # # #             risks.append({
# # # # # # #                 "icon": "⚠", "sev": 2, "color": "#F59E0B", "bg": "#FFFBEB",
# # # # # # #                 "title": f"Supplier Concentration — {us} Unique Supplier(s)",
# # # # # # #                 "detail": f"High dependency on {us} supplier(s). Any disruption cascades to multiple components simultaneously.",
# # # # # # #                 "action": "Evaluate dual-sourcing for critical external components.",
# # # # # # #             })
# # # # # # #         ext_comps = bsn[bsn["Procurement type"] == "F"]
# # # # # # #         if len(ext_comps) > 0:
# # # # # # #             locs = list(set([str(r) for r in bsn[bsn["Procurement type"] == "F"]["Supplier Location"].dropna().tolist()[:4]]))
# # # # # # #             risks.append({
# # # # # # #                 "icon": "🌍", "sev": 1, "color": "#3B82F6", "bg": "#EFF6FF",
# # # # # # #                 "title": f"External Procurement: {len(ext_comps)} Components",
# # # # # # #                 "detail": (f"External components depend on supplier availability and transit times. "
# # # # # # #                            f"Suppliers located in: {', '.join(locs)}."),
# # # # # # #                 "action": "Review external component lead times — stock buffers for long-transit items.",
# # # # # # #             })

# # # # # # #         if not risks:
# # # # # # #             st.markdown(
# # # # # # #                 "<div style='padding:10px 13px;background:var(--gbg);border:1px solid rgba(34,197,94,0.2);"
# # # # # # #                 "border-radius:var(--r);font-size:12px;color:#14532d;'>"
# # # # # # #                 "✓ No critical propagation risks identified.</div>",
# # # # # # #                 unsafe_allow_html=True,
# # # # # # #             )
# # # # # # #         else:
# # # # # # #             for r in sorted(risks, key=lambda x: -x["sev"]):
# # # # # # #                 st.markdown(
# # # # # # #                     f"<div style='background:{r['bg']};border:1px solid {r['color']}40;"
# # # # # # #                     f"border-left:4px solid {r['color']};border-radius:var(--r);"
# # # # # # #                     f"padding:12px 14px;margin-bottom:8px;'>"
# # # # # # #                     f"<div style='display:flex;align-items:center;gap:8px;margin-bottom:5px;'>"
# # # # # # #                     f"<span style='font-size:16px;'>{r['icon']}</span>"
# # # # # # #                     f"<div style='font-size:12px;font-weight:800;color:{r['color']};'>{r['title']}</div>"
# # # # # # #                     f"</div>"
# # # # # # #                     f"<div style='font-size:11px;color:var(--t2);margin-bottom:5px;'>{r['detail']}</div>"
# # # # # # #                     f"<div style='font-size:11px;color:{r['color']};font-weight:600;'>→ {r['action']}</div>"
# # # # # # #                     f"</div>",
# # # # # # #                     unsafe_allow_html=True,
# # # # # # #                 )

# # # # # # #         # Consolidation opportunities
# # # # # # #         consol2   = get_supplier_consolidation(data, summary)
# # # # # # #         relevant2 = consol2[
# # # # # # #             consol2.material_list.apply(lambda x: snid in x)
# # # # # # #             & (consol2.finished_goods_supplied > 1)
# # # # # # #             & consol2.consolidation_opportunity
# # # # # # #         ]
# # # # # # #         if len(relevant2) > 0:
# # # # # # #             sec("Supplier Consolidation Opportunities")
# # # # # # #             for _, r2 in relevant2.iterrows():
# # # # # # #                 others = [MATERIAL_LABELS.get(m, m)[:18] for m in r2["material_list"] if m != snid]
# # # # # # #                 st.markdown(
# # # # # # #                     f"<div class='prow'><div style='font-size:14px;'>🏭</div>"
# # # # # # #                     f"<div style='flex:1;'>"
# # # # # # #                     f"<div style='font-size:12px;font-weight:800;'>{r2['supplier']}</div>"
# # # # # # #                     f"<div style='font-size:10px;color:var(--t3);'>{r2['city']} · {r2['email']}</div>"
# # # # # # #                     f"<div style='font-size:10px;color:var(--t2);margin-top:2px;'>Also supplies: {', '.join(others[:3])}</div>"
# # # # # # #                     f"</div>"
# # # # # # #                     f"<div style='font-size:10px;font-weight:700;color:var(--or);'>⚡ Consolidate order</div>"
# # # # # # #                     f"</div>",
# # # # # # #                     unsafe_allow_html=True,
# # # # # # #                 )

# # # # # # #         # ── Ask ARIA ──────────────────────────────────────────────────────────
# # # # # # #         if st.session_state.azure_client:
# # # # # # #             sec("Ask ARIA About This Network")
# # # # # # #             st.info("ℹ️ This assistant provides supplier‑related insights only for the currently selected finished good.")
# # # # # # #             uq = st.text_input(
# # # # # # #                 "Question",
# # # # # # #                 placeholder="e.g. Which supplier provides more than 1 material for DELFIA Wash Concentrate?",
# # # # # # #                 key="snq", label_visibility="collapsed",
# # # # # # #             )
# # # # # # #             if uq and st.button("Ask ARIA", key="sna"):
# # # # # # #                 bom_lines = []
# # # # # # #                 for _, row in bsn.iterrows():
# # # # # # #                     mat_desc = str(row["Material Description"])[:40] if pd.notna(row["Material Description"]) else str(row["Material"])
# # # # # # #                     qty = row["Effective Order Qty"] if "Effective Order Qty" in row else row["Comp. Qty (CUn)"]
# # # # # # #                     fixed = "X (order exactly 1)" if row.get("Fixed Qty Flag") else ""
# # # # # # #                     sup = row.get("Supplier Display", "—")
# # # # # # #                     loc = row.get("Supplier Location", "—")
# # # # # # #                     transit = row.get("Transit Days", "—")
# # # # # # #                     reliability = row.get("Supplier Reliability", "—")
# # # # # # #                     std_price = row.get("Standard Price", "—")
# # # # # # #                     if pd.notna(std_price):
# # # # # # #                         std_price = f"${std_price:.2f}"
# # # # # # #                     bom_lines.append(
# # # # # # #                         f"- Component: {mat_desc} | Qty: {qty} {fixed} | Std Price: {std_price} "
# # # # # # #                         f"| Supplier: {sup} | Location: {loc} | Transit: {transit}d | Reliability: {reliability}"
# # # # # # #                     )
# # # # # # #                 bom_table = "\n".join(bom_lines)
# # # # # # #                 ctx3 = (
# # # # # # #                     f"Material: {snr['name']} (ID: {snid})\n"
# # # # # # #                     f"Risk: {snr['risk']}\n"
# # # # # # #                     f"Total components: {tc}\n"
# # # # # # #                     f"Inhouse components: {inhouse_n}\n"
# # # # # # #                     f"External components: {external_n}\n"
# # # # # # #                     f"Missing supplier data: {cn} components\n"
# # # # # # #                     f"Unique external suppliers: {us}\n"
# # # # # # #                     f"BOM details:\n{bom_table}"
# # # # # # #                 )
# # # # # # #                 with st.spinner("Thinking…"):
# # # # # # #                     ans = chat_with_data(st.session_state.azure_client, AZURE_DEPLOYMENT, uq, ctx3)
# # # # # # #                 st.markdown(
# # # # # # #                     f"<div class='ic' style='margin-top:8px;'><div class='il'>◈ ARIA</div>"
# # # # # # #                     f"<div class='ib'>{ans}</div></div>",
# # # # # # #                     unsafe_allow_html=True,
# # # # # # #                 )

# # # # # # #     st.markdown('<div class="pfooter">🕸️ Powered by <strong>MResult</strong></div>', unsafe_allow_html=True)
