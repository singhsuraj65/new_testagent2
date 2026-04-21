"""
tabs/supply_network.py
Supply Network tab: BOM propagation map (Sankey diagram), component detail table,
risk cascade analysis, and supplier consolidation opportunities.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from st_aggrid import AgGrid, GridOptionsBuilder, JsCode

from utils.helpers import sec, note, sbadge, ORANGE, AZURE_DEPLOYMENT
from data_loader import get_bom_components, get_supplier_consolidation
from agent import interpret_chart, chat_with_data

_AGGRID_CSS = {
    ".ag-root-wrapper": {"border": "1px solid #E2E8F0!important", "border-radius": "12px!important"},
    ".ag-header":       {"background": "#F8FAFE!important"},
    ".ag-row-even":     {"background": "#FFFFFF!important"},
    ".ag-row-odd":      {"background": "#F8FAFE!important"},
}


def render():
    data            = st.session_state.data
    summary         = st.session_state.summary
    MATERIAL_LABELS = st.session_state.material_labels

    st.markdown(
        "<div style='font-size:15px;font-weight:800;margin-bottom:4px;'>Supply Network</div>"
        "<div style='font-size:12px;color:var(--t3);margin-bottom:14px;'>"
        "BOM structure · Supplier locations · Risk cascade · Consolidation intelligence</div>",
        unsafe_allow_html=True,
    )

    snn  = st.selectbox("Finished Good", [r["name"] for _, r in summary.iterrows()], key="snm")
    snid = summary[summary.name == snn]["material"].values[0]
    snr  = summary[summary.material == snid].iloc[0]
    bsn  = get_bom_components(data, snid)

    if not len(bsn):
        st.markdown(
            "<div class='flag-box'><div style='font-size:22px;margin-bottom:8px;'>🕸️</div>"
            "<div style='font-size:14px;font-weight:800;color:var(--t2);'>No BOM data for this material</div></div>",
            unsafe_allow_html=True,
        )
        return

    cw        = int(bsn["Supplier Name(Vendor)"].notna().sum())
    cn        = len(bsn[bsn["Supplier Display"].str.startswith("⚠", na=False)])
    us        = int(bsn["Supplier Name(Vendor)"].dropna().nunique())
    tc        = len(bsn)
    inhouse_n = int((bsn["Procurement type"] == "E").sum())
    external_n = int((bsn["Procurement type"] == "F").sum())

    n1, n2, n3, n4 = st.columns(4)
    for col, val, lbl, vc in [
        (n1, tc,        "Total Components",  "#1E293B"),
        (n2, inhouse_n, "Revvity Inhouse",   "#22C55E"),
        (n3, cn,        "Missing Supplier",  "#F59E0B" if cn > 0 else "#1E293B"),
        (n4, us,        "Unique Ext Suppliers", "#1E293B"),
    ]:
        with col:
            st.markdown(
                f"<div class='sc'><div style='flex:1;'>"
                f"<div class='sv' style='color:{vc};'>{val}</div>"
                f"<div class='sl'>{lbl}</div></div></div>",
                unsafe_allow_html=True,
            )

    sn_tab, comp_tab, risk_tab = st.tabs(["🕸️  BOM Map", "📋  Components", "⚠️  Risk Analysis"])

    # ── BOM Map – Sankey diagram with error handling ──────────────────────────
    with sn_tab:
        sec("BOM Propagation Map")
        st.markdown("""
        <div class='note-box'>
        <strong>Colour legend:</strong>
        <ul style='margin:5px 0 0 20px; padding-left:0;'>
        <li>🔵 <strong>Blue</strong> = External component with named supplier</li>
        <li>🟢 <strong>Green</strong> = Inhouse component (Revvity)</li>
        <li>🟡 <strong>Amber</strong> = External component with <strong>missing supplier data</strong></li>
        <li>🟣 <strong>Purple</strong> = Supplier node</li>
        <li>Root node colour matches finished good risk (🔴 Critical / 🟠 Warning / 🟢 Healthy)</li>
        </ul>
        Hover over nodes for details. Use the interactive controls to zoom/pan.
        </div>
        """, unsafe_allow_html=True)

        try:
            # Build node list and links
            nodes = []
            node_colors = []
            node_map = {}

            # Root node
            root_name = snr["name"]
            risk_color_map = {"CRITICAL": "#EF4444", "WARNING": "#F59E0B", "HEALTHY": "#22C55E"}
            root_color = risk_color_map.get(snr["risk"], "#94A3B8")
            nodes.append(root_name)
            node_colors.append(root_color)
            node_map[root_name] = 0

            sources = []
            targets = []
            values = []

            # Process each BOM row
            for _, row in bsn.iterrows():
                # Component label (shortened)
                comp_desc = str(row["Material Description"])[:30] if pd.notna(row["Material Description"]) else str(row["Material"])
                comp_label = comp_desc
                sup_display = row.get("Supplier Display", "—")
                proc_type = str(row.get("Procurement type", "")).strip()
                qty_raw = row.get("Effective Order Qty", row["Comp. Qty (CUn)"])
                try:
                    qty = float(qty_raw) if pd.notna(qty_raw) else 1.0
                except:
                    qty = 1.0

                # Add component node
                if comp_label not in node_map:
                    if proc_type == "E":
                        comp_color = "#22C55E"
                    elif sup_display.startswith("⚠"):
                        comp_color = "#F59E0B"
                    else:
                        comp_color = "#3B82F6"
                    nodes.append(comp_label)
                    node_colors.append(comp_color)
                    node_map[comp_label] = len(nodes) - 1

                # Root -> component
                sources.append(node_map[root_name])
                targets.append(node_map[comp_label])
                values.append(qty)

                # Supplier node (if external and named)
                if sup_display not in ["Revvity Inhouse", "—"] and not sup_display.startswith("⚠"):
                    sup_label = sup_display[:25]
                    if sup_label not in node_map:
                        nodes.append(sup_label)
                        node_colors.append("#8B5CF6")
                        node_map[sup_label] = len(nodes) - 1
                    sources.append(node_map[comp_label])
                    targets.append(node_map[sup_label])
                    values.append(1.0)

            # Only create Sankey if there are links
            if len(sources) == 0:
                st.warning("No valid links found in the BOM. Cannot render Sankey diagram.")
            else:
                fig = go.Figure(data=[go.Sankey(
                    arrangement="snap",
                    node=dict(
                        pad=30,
                        thickness=15,
                        line=dict(color="white", width=0.5),
                        label=nodes,
                        color=node_colors,
                        hovertemplate="<b>%{label}</b><extra></extra>"
                    ),
                    link=dict(
                        source=sources,
                        target=targets,
                        value=values,
                        color="rgba(160,160,160,0.4)"
                    )
                )])
                fig.update_layout(
                    title=None,
                    font=dict(size=11, family="Inter", color="#1E293B"),
                    height=550,
                    margin=dict(l=20, r=20, t=20, b=20),
                    paper_bgcolor="white",
                    plot_bgcolor="white"
                )
                st.plotly_chart(fig, use_container_width=True)

        except Exception as e:
            st.error(f"Could not render Sankey diagram: {str(e)}")
            st.info("Try selecting a different finished good or check the BOM data.")

        if st.session_state.azure_client:
            if st.button("◈ Interpret BOM Map", key="interp_bom_sankey"):
                with st.spinner("ARIA interpreting…"):
                    bom_ctx = {
                        "material": snr["name"], "total_components": tc,
                        "inhouse": inhouse_n, "external_named": cw - inhouse_n,
                        "missing_supplier": cn, "unique_suppliers": us, "risk": snr["risk"],
                    }
                    interp = interpret_chart(
                        st.session_state.azure_client, AZURE_DEPLOYMENT,
                        "BOM Risk Propagation Map", bom_ctx,
                        "What are the key supply chain risks in this BOM and what should procurement prioritise?",
                    )
                st.markdown(
                    f"<div class='ic' style='margin-top:8px;'><div class='il'>◈ ARIA</div>"
                    f"<div class='ib'>{interp}</div></div>",
                    unsafe_allow_html=True,
                )

    # ── Component Detail ──────────────────────────────────────────────────────
    with comp_tab:
        sec("Component Detail")
        bom_display2 = []
        for _, b in bsn.iterrows():
            eff_qty = b.get("Effective Order Qty", b["Comp. Qty (CUn)"])
            fq_txt  = ("1 (Fixed)" if b.get("Fixed Qty Flag", False)
                       else str(round(float(eff_qty), 3)) if pd.notna(eff_qty) else "—")
            bom_display2.append({
                "Material":    str(b["Material"]),
                "Description": str(b["Material Description"])[:36] if pd.notna(b["Material Description"]) else "—",
                "Level":       str(b["Level"])[:25] if pd.notna(b["Level"]) else "—",
                "Qty":         fq_txt,
                "Unit":        str(b["Component unit"]) if pd.notna(b["Component unit"]) else "—",
                "Type":        b.get("Procurement Label", "—"),
                "Supplier":    b.get("Supplier Display", "—"),
                "Location":    b.get("Supplier Location", "—"),
                "Transit":     f"{b.get('Transit Days', '—')}d" if b.get("Transit Days") is not None else "—",
                "Std Price":   f"${b.get('Standard Price', 0):.2f}" if pd.notna(b.get('Standard Price')) else "—",
            })
        df_bd2  = pd.DataFrame(bom_display2)
        sup_r3  = JsCode("""class R{init(p){const v=p.value||'';this.e=document.createElement('span');if(v.startsWith('⚠')){this.e.style.cssText='background:#FEF3C7;color:#F59E0B;padding:2px 6px;border-radius:4px;font-size:10px;font-weight:600;';this.e.innerText=v;}else if(v==='Revvity Inhouse'){this.e.style.cssText='background:#DCFCE7;color:#16a34a;padding:2px 6px;border-radius:4px;font-size:10px;font-weight:600;';this.e.innerText='🏭 '+v;}else{this.e.style.cssText='background:#EFF6FF;color:#2563EB;padding:2px 6px;border-radius:4px;font-size:10px;';this.e.innerText='🚚 '+v;};}getGui(){return this.e;}}""")
        gb4     = GridOptionsBuilder.from_dataframe(df_bd2)
        gb4.configure_column("Material",    width=82)
        gb4.configure_column("Description", width=215)
        gb4.configure_column("Level",       width=85)
        gb4.configure_column("Qty",         width=75)
        gb4.configure_column("Unit",        width=50)
        gb4.configure_column("Type",        width=100)
        gb4.configure_column("Supplier",    width=170, cellRenderer=sup_r3)
        gb4.configure_column("Location",    width=130)
        gb4.configure_column("Transit",     width=58)
        gb4.configure_column("Std Price",   width=80)
        gb4.configure_grid_options(rowHeight=36, headerHeight=32)
        gb4.configure_default_column(resizable=True, sortable=True, filter=False)
        AgGrid(df_bd2, gridOptions=gb4.build(), height=320,
               allow_unsafe_jscode=True, theme="alpine", custom_css=_AGGRID_CSS)

    # ── Risk Cascade (unchanged) ─────────────────────────────────────────────
    with risk_tab:
        sec("Risk Cascade Analysis")
        risks = []
        if snr["risk"] in ["CRITICAL", "WARNING"]:
            risks.append({
                "icon": "⛔", "sev": 3, "color": "#EF4444", "bg": "#FEF2F2",
                "title": f"Finished Good at {snr['risk'].title()} Risk",
                "detail": (f"{snr['name']} has {round(snr['days_cover'])}d of cover. "
                           f"SIH={round(snr['sih'])} vs SAP SS={round(snr['safety_stock'])}. "
                           f"Production continuity at risk."),
                "action": f"Order {int(snr.get('repl_quantity', 0))} units immediately. Contact procurement today.",
            })
        if cn > 0:
            risks.append({
                "icon": "⚠", "sev": 2, "color": "#F59E0B", "bg": "#FFFBEB",
                "title": f"Missing Supplier Data — {cn} External Components",
                "detail": (f"{cn} of {external_n} external components have no named supplier. "
                           f"Single-source risk cannot be assessed for these."),
                "action": "Procurement to verify and update BOM with supplier names and lead times.",
            })
        if 0 < us <= 2:
            risks.append({
                "icon": "⚠", "sev": 2, "color": "#F59E0B", "bg": "#FFFBEB",
                "title": f"Supplier Concentration — {us} Unique Supplier(s)",
                "detail": f"High dependency on {us} supplier(s). Any disruption cascades to multiple components simultaneously.",
                "action": "Evaluate dual-sourcing for critical external components.",
            })
        ext_comps = bsn[bsn["Procurement type"] == "F"]
        if len(ext_comps) > 0:
            locs = list(set([str(r) for r in bsn[bsn["Procurement type"] == "F"]["Supplier Location"].dropna().tolist()[:4]]))
            risks.append({
                "icon": "🌍", "sev": 1, "color": "#3B82F6", "bg": "#EFF6FF",
                "title": f"External Procurement: {len(ext_comps)} Components",
                "detail": (f"External components depend on supplier availability and transit times. "
                           f"Suppliers located in: {', '.join(locs)}."),
                "action": "Review external component lead times — stock buffers for long-transit items.",
            })

        if not risks:
            st.markdown(
                "<div style='padding:10px 13px;background:var(--gbg);border:1px solid rgba(34,197,94,0.2);"
                "border-radius:var(--r);font-size:12px;color:#14532d;'>"
                "✓ No critical propagation risks identified.</div>",
                unsafe_allow_html=True,
            )
        else:
            for r in sorted(risks, key=lambda x: -x["sev"]):
                st.markdown(
                    f"<div style='background:{r['bg']};border:1px solid {r['color']}40;"
                    f"border-left:4px solid {r['color']};border-radius:var(--r);"
                    f"padding:12px 14px;margin-bottom:8px;'>"
                    f"<div style='display:flex;align-items:center;gap:8px;margin-bottom:5px;'>"
                    f"<span style='font-size:16px;'>{r['icon']}</span>"
                    f"<div style='font-size:12px;font-weight:800;color:{r['color']};'>{r['title']}</div>"
                    f"</div>"
                    f"<div style='font-size:11px;color:var(--t2);margin-bottom:5px;'>{r['detail']}</div>"
                    f"<div style='font-size:11px;color:{r['color']};font-weight:600;'>→ {r['action']}</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

        # Consolidation opportunities
        consol2   = get_supplier_consolidation(data, summary)
        relevant2 = consol2[
            consol2.material_list.apply(lambda x: snid in x)
            & (consol2.finished_goods_supplied > 1)
            & consol2.consolidation_opportunity
        ]
        if len(relevant2) > 0:
            sec("Supplier Consolidation Opportunities")
            for _, r2 in relevant2.iterrows():
                others = [MATERIAL_LABELS.get(m, m)[:18] for m in r2["material_list"] if m != snid]
                st.markdown(
                    f"<div class='prow'><div style='font-size:14px;'>🏭</div>"
                    f"<div style='flex:1;'>"
                    f"<div style='font-size:12px;font-weight:800;'>{r2['supplier']}</div>"
                    f"<div style='font-size:10px;color:var(--t3);'>{r2['city']} · {r2['email']}</div>"
                    f"<div style='font-size:10px;color:var(--t2);margin-top:2px;'>Also supplies: {', '.join(others[:3])}</div>"
                    f"</div>"
                    f"<div style='font-size:10px;font-weight:700;color:var(--or);'>⚡ Consolidate order</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

        # ── Ask ARIA with rich BOM context ────────────────────────────────────
        if st.session_state.azure_client:
            sec("Ask ARIA About This Network")
            st.info("ℹ️ This assistant provides supplier‑related insights only for the currently selected finished good.")
            uq = st.text_input(
                "Question",
                placeholder="e.g. Which supplier provides more than 1 material for DELFIA Wash Concentrate?",
                key="snq", label_visibility="collapsed",
            )
            if uq and st.button("Ask ARIA", key="sna"):
                bom_lines = []
                for _, row in bsn.iterrows():
                    mat_desc = str(row["Material Description"])[:40] if pd.notna(row["Material Description"]) else str(row["Material"])
                    qty = row["Effective Order Qty"] if "Effective Order Qty" in row else row["Comp. Qty (CUn)"]
                    fixed = "X (order exactly 1)" if row.get("Fixed Qty Flag") else ""
                    sup = row.get("Supplier Display", "—")
                    loc = row.get("Supplier Location", "—")
                    transit = row.get("Transit Days", "—")
                    reliability = row.get("Supplier Reliability", "—")
                    std_price = row.get("Standard Price", "—")
                    if pd.notna(std_price):
                        std_price = f"${std_price:.2f}"
                    bom_lines.append(f"- Component: {mat_desc} | Qty: {qty} {fixed} | Std Price: {std_price} | Supplier: {sup} | Location: {loc} | Transit: {transit}d | Reliability: {reliability}")
                bom_table = "\n".join(bom_lines)

                ctx3 = (
                    f"Material: {snr['name']} (ID: {snid})\n"
                    f"Risk: {snr['risk']}\n"
                    f"Total components: {tc}\n"
                    f"Inhouse components: {inhouse_n}\n"
                    f"External components: {external_n}\n"
                    f"Missing supplier data: {cn} components\n"
                    f"Unique external suppliers: {us}\n"
                    f"BOM details:\n{bom_table}"
                )
                with st.spinner("Thinking…"):
                    ans = chat_with_data(st.session_state.azure_client, AZURE_DEPLOYMENT, uq, ctx3)
                st.markdown(
                    f"<div class='ic' style='margin-top:8px;'><div class='il'>◈ ARIA</div>"
                    f"<div class='ib'>{ans}</div></div>",
                    unsafe_allow_html=True,
                )

    st.markdown('<div class="pfooter">🕸️ Powered by <strong>MResult</strong></div>', unsafe_allow_html=True)


# """
# tabs/supply_network.py
# Supply Network tab: BOM propagation map (Sankey diagram), component detail table,
# risk cascade analysis, and supplier consolidation opportunities.

# FIXES:
#   1. "undefined" in Sankey -> all labels/customdata sanitised via _safe();
#      empty string is the #1 cause of Plotly rendering "undefined" on hover.
#   2. Invisible text -> removed dependency on undefined CSS class 'note-box';
#      legend rebuilt with native Streamlit columns + inline styles only.
#   3. Out-of-bound indices -> assertion guard before figure construction.
#   4. Zero/NaN qty -> clamped to 0.01 so Sankey never silently drops a link.
#   5. Supplier link value was hardcoded 1.0 -> now uses actual qty.
#   6. Font colour -> removed hardcoded dark colour invisible in dark themes;
#      paper_bgcolor is transparent so it respects Streamlit's theme.
# """

# import streamlit as st
# import pandas as pd
# import plotly.graph_objects as go

# from st_aggrid import AgGrid, GridOptionsBuilder, JsCode

# from utils.helpers import sec, note, sbadge, ORANGE, AZURE_DEPLOYMENT
# from data_loader import get_bom_components, get_supplier_consolidation
# from agent import interpret_chart, chat_with_data

# _AGGRID_CSS = {
#     ".ag-root-wrapper": {"border": "1px solid #E2E8F0!important", "border-radius": "12px!important"},
#     ".ag-header":       {"background": "#F8FAFE!important"},
#     ".ag-row-even":     {"background": "#FFFFFF!important"},
#     ".ag-row-odd":      {"background": "#F8FAFE!important"},
# }

# _RISK_COLOUR = {"CRITICAL": "#EF4444", "WARNING": "#F59E0B", "HEALTHY": "#22C55E"}


# # ---------------------------------------------------------------------------
# # Helpers
# # ---------------------------------------------------------------------------

# def _safe(val, fallback="—", maxlen=0):
#     """
#     Return a guaranteed non-empty string.
#     Plotly Sankey renders 'undefined' whenever a label or customdata entry
#     is an empty string or None — this function prevents that entirely.
#     """
#     if val is None or (isinstance(val, float) and pd.isna(val)):
#         return fallback
#     s = str(val).strip()
#     if not s:
#         return fallback
#     return s[:maxlen] if maxlen else s


# def _safe_qty(val):
#     """Return a positive float; Sankey silently drops links with value <= 0."""
#     try:
#         q = float(val)
#         return q if q > 0 else 0.01
#     except Exception:
#         return 0.01


# # ---------------------------------------------------------------------------
# # Legend  (zero CSS-class dependency — inline styles only)
# # ---------------------------------------------------------------------------

# def _render_legend():
#     st.markdown(
#         "<div style='"
#         "background:#F8FAFE;"
#         "border:1px solid #CBD5E1;"
#         "border-left:4px solid #3B82F6;"
#         "border-radius:10px;"
#         "padding:10px 16px 6px 16px;"
#         "margin-bottom:12px;"
#         "'>"
#         "<span style='font-size:12px;font-weight:700;color:#1E293B;'>"
#         "Colour legend&nbsp;&nbsp;"
#         "</span>"
#         "<span style='font-size:11px;color:#64748B;'>"
#         "Root node = finished-good risk &nbsp;|&nbsp; "
#         "🔴 Critical &nbsp; 🟠 Warning &nbsp; 🟢 Healthy"
#         "</span>"
#         "</div>",
#         unsafe_allow_html=True,
#     )
#     badges = [
#         ("#3B82F6", "🔵", "External – named supplier"),
#         ("#22C55E", "🟢", "Inhouse (Revvity)"),
#         ("#F59E0B", "🟡", "External – missing supplier"),
#         ("#8B5CF6", "🟣", "Supplier node"),
#     ]
#     cols = st.columns(4)
#     for col, (hex_c, emoji, label) in zip(cols, badges):
#         with col:
#             st.markdown(
#                 f"<div style='"
#                 f"background:{hex_c}1A;"
#                 f"border:1px solid {hex_c}88;"
#                 f"border-radius:8px;"
#                 f"padding:7px 8px;"
#                 f"text-align:center;"
#                 f"font-size:11px;"
#                 f"font-weight:600;"
#                 f"color:{hex_c};"
#                 f"margin-bottom:10px;"
#                 f"'>{emoji}&nbsp;{label}</div>",
#                 unsafe_allow_html=True,
#             )


# # ---------------------------------------------------------------------------
# # Sankey builder
# # ---------------------------------------------------------------------------

# def _build_sankey(bsn, snr):
#     """
#     Build and return a Plotly Sankey figure from BOM rows.
#     Raises ValueError with a descriptive message when data is unusable.
#     """
#     nodes = []
#     node_colors = []
#     node_custom = []          # drives %{customdata} in hovertemplate
#     node_map = {}             # stable_key -> int index

#     def _add(key, label, color, custom):
#         key = _safe(key, fallback="__unk__")
#         if key not in node_map:
#             node_map[key] = len(nodes)
#             nodes.append(_safe(label, fallback=key, maxlen=40))
#             node_colors.append(color or "#94A3B8")
#             node_custom.append(_safe(custom, fallback=_safe(label, fallback=key)))
#         return node_map[key]

#     root_color = _RISK_COLOUR.get(_safe(snr["risk"]), "#94A3B8")
#     root_idx = _add(
#         key    = f"FG_{snr['material']}",
#         label  = _safe(snr["name"], maxlen=40),
#         color  = root_color,
#         custom = (
#             f"Finished Good: {_safe(snr['name'])} | "
#             f"Risk: {_safe(snr['risk'])} | "
#             f"Cover: {round(float(snr['days_cover']))}d"
#         ),
#     )

#     sources   = []
#     targets   = []
#     values    = []
#     link_lbl  = []

#     for _, row in bsn.iterrows():
#         mat_id     = _safe(row.get("Material"), fallback="UNK")
#         comp_desc  = _safe(row.get("Material Description"), fallback=mat_id, maxlen=32)
#         proc_type  = _safe(row.get("Procurement type"), fallback="").upper()
#         sup_disp   = _safe(row.get("Supplier Display"), fallback="—")

#         qty_raw = row.get("Effective Order Qty") or row.get("Comp. Qty (CUn)")
#         qty     = _safe_qty(qty_raw)

#         if proc_type == "E":
#             comp_color  = "#22C55E"
#             comp_custom = f"{comp_desc} | Inhouse (Revvity) | Qty: {qty}"
#         elif sup_disp.startswith("⚠") or sup_disp == "—":
#             comp_color  = "#F59E0B"
#             comp_custom = f"{comp_desc} | No supplier data | Qty: {qty}"
#         else:
#             transit     = _safe(row.get("Transit Days"), fallback="—")
#             comp_color  = "#3B82F6"
#             comp_custom = (
#                 f"{comp_desc} | Supplier: {sup_disp} | "
#                 f"Qty: {qty} | Transit: {transit}d"
#             )

#         comp_idx = _add(
#             key    = f"COMP_{mat_id}",
#             label  = comp_desc,
#             color  = comp_color,
#             custom = comp_custom,
#         )

#         sources.append(root_idx)
#         targets.append(comp_idx)
#         values.append(qty)
#         link_lbl.append(f"{comp_desc} | qty: {qty}")

#         is_named_ext = (
#             proc_type == "F"
#             and sup_disp not in ("—", "Revvity Inhouse")
#             and not sup_disp.startswith("⚠")
#         )
#         if is_named_ext:
#             loc     = _safe(row.get("Supplier Location"), fallback="—")
#             rel     = _safe(row.get("Supplier Reliability"), fallback="—")
#             sup_idx = _add(
#                 key    = f"SUP_{sup_disp}",
#                 label  = _safe(sup_disp, maxlen=28),
#                 color  = "#8B5CF6",
#                 custom = (
#                     f"Supplier: {sup_disp} | "
#                     f"Location: {loc} | Reliability: {rel}"
#                 ),
#             )
#             sources.append(comp_idx)
#             targets.append(sup_idx)
#             values.append(qty)
#             link_lbl.append(f"{comp_desc} -> {_safe(sup_disp, maxlen=28)}")

#     # Safety check
#     n = len(nodes)
#     if n == 0 or not sources:
#         raise ValueError("No nodes or links were generated from BOM data.")

#     bad = [
#         (i, s, t)
#         for i, (s, t) in enumerate(zip(sources, targets))
#         if not (0 <= s < n) or not (0 <= t < n)
#     ]
#     if bad:
#         raise ValueError(
#             f"{len(bad)} link(s) reference out-of-range indices "
#             f"(total nodes={n}). First bad: link {bad[0][0]}, "
#             f"src={bad[0][1]}, tgt={bad[0][2]}."
#         )

#     fig = go.Figure(data=[go.Sankey(
#         arrangement="snap",
#         node=dict(
#             pad=18,
#             thickness=22,
#             line=dict(color="rgba(255,255,255,0.5)", width=0.8),
#             label=nodes,
#             color=node_colors,
#             customdata=node_custom,
#             hovertemplate="<b>%{customdata}</b><extra></extra>",
#         ),
#         link=dict(
#             source=sources,
#             target=targets,
#             value=values,
#             label=link_lbl,
#             color="rgba(148,163,184,0.30)",
#             hovertemplate=(
#                 "<b>%{label}</b><br>"
#                 "Flow: %{value:.2f}<extra></extra>"
#             ),
#         ),
#     )])

#     fig.update_layout(
#         title=None,
#         # No hardcoded font colour: Plotly auto-picks contrast vs node colour.
#         font=dict(size=11, family="Inter, sans-serif"),
#         height=520,
#         margin=dict(l=10, r=10, t=10, b=10),
#         # Transparent background respects Streamlit light/dark theme.
#         paper_bgcolor="rgba(0,0,0,0)",
#         plot_bgcolor="rgba(0,0,0,0)",
#     )
#     return fig


# # ---------------------------------------------------------------------------
# # Main render
# # ---------------------------------------------------------------------------

# def render():
#     data            = st.session_state.data
#     summary         = st.session_state.summary
#     MATERIAL_LABELS = st.session_state.material_labels

#     st.markdown(
#         "<div style='font-size:15px;font-weight:800;margin-bottom:4px;'>Supply Network</div>"
#         "<div style='font-size:12px;color:var(--t3);margin-bottom:14px;'>"
#         "BOM structure · Supplier locations · Risk cascade · Consolidation intelligence</div>",
#         unsafe_allow_html=True,
#     )

#     snn  = st.selectbox("Finished Good", [r["name"] for _, r in summary.iterrows()], key="snm")
#     snid = summary[summary.name == snn]["material"].values[0]
#     snr  = summary[summary.material == snid].iloc[0]
#     bsn  = get_bom_components(data, snid)

#     if not len(bsn):
#         st.warning("🕸️ No BOM data found for this material.")
#         return

#     cw         = int(bsn["Supplier Name(Vendor)"].notna().sum())
#     cn         = int(bsn["Supplier Display"].str.startswith("⚠", na=False).sum())
#     us         = int(bsn["Supplier Name(Vendor)"].dropna().nunique())
#     tc         = len(bsn)
#     inhouse_n  = int((bsn["Procurement type"] == "E").sum())
#     external_n = int((bsn["Procurement type"] == "F").sum())

#     n1, n2, n3, n4 = st.columns(4)
#     for col, val, lbl, vc in [
#         (n1, tc,        "Total Components",     "#1E293B"),
#         (n2, inhouse_n, "Revvity Inhouse",      "#22C55E"),
#         (n3, cn,        "Missing Supplier",     "#F59E0B" if cn > 0 else "#1E293B"),
#         (n4, us,        "Unique Ext Suppliers", "#1E293B"),
#     ]:
#         with col:
#             st.markdown(
#                 f"<div class='sc'><div style='flex:1;'>"
#                 f"<div class='sv' style='color:{vc};'>{val}</div>"
#                 f"<div class='sl'>{lbl}</div></div></div>",
#                 unsafe_allow_html=True,
#             )

#     sn_tab, comp_tab, risk_tab = st.tabs(
#         ["🕸️  BOM Map", "📋  Components", "⚠️  Risk Analysis"]
#     )

#     # ── BOM Map ──────────────────────────────────────────────────────────────
#     with sn_tab:
#         sec("BOM Propagation Map")
#         _render_legend()

#         try:
#             fig = _build_sankey(bsn, snr)
#             st.plotly_chart(fig, use_container_width=True)
#         except ValueError as exc:
#             st.error(f"⚠️ Could not render Sankey diagram: {exc}")
#             st.info(
#                 "This usually means BOM rows are missing Material IDs or all "
#                 "quantities are zero/null. Check your data loader output."
#             )
#             with st.expander("🔍 Raw BOM data (debug)"):
#                 st.dataframe(bsn)

#         if st.session_state.azure_client:
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

#     # ── Component Detail ─────────────────────────────────────────────────────
#     with comp_tab:
#         sec("Component Detail")
#         bom_display2 = []
#         for _, b in bsn.iterrows():
#             eff_qty = b.get("Effective Order Qty", b["Comp. Qty (CUn)"])
#             fq_txt  = (
#                 "1 (Fixed)" if b.get("Fixed Qty Flag", False)
#                 else str(round(float(eff_qty), 3)) if pd.notna(eff_qty) else "—"
#             )
#             bom_display2.append({
#                 "Material":    _safe(b.get("Material")),
#                 "Description": _safe(b.get("Material Description"), maxlen=36),
#                 "Level":       _safe(b.get("Level"), maxlen=25),
#                 "Qty":         fq_txt,
#                 "Unit":        _safe(b.get("Component unit")),
#                 "Type":        _safe(b.get("Procurement Label")),
#                 "Supplier":    _safe(b.get("Supplier Display")),
#                 "Location":    _safe(b.get("Supplier Location")),
#                 "Transit":     (
#                     f"{b.get('Transit Days')}d"
#                     if b.get("Transit Days") is not None else "—"
#                 ),
#                 "Std Price":   (
#                     f"${b.get('Standard Price', 0):.2f}"
#                     if pd.notna(b.get("Standard Price")) else "—"
#                 ),
#             })
#         df_bd2 = pd.DataFrame(bom_display2)
#         sup_r3 = JsCode(
#             "class R{"
#             "init(p){const v=p.value||'';"
#             "this.e=document.createElement('span');"
#             "if(v.startsWith('⚠')){"
#             "this.e.style.cssText='background:#FEF3C7;color:#F59E0B;"
#             "padding:2px 6px;border-radius:4px;font-size:10px;font-weight:600;';"
#             "this.e.innerText=v;"
#             "}else if(v==='Revvity Inhouse'){"
#             "this.e.style.cssText='background:#DCFCE7;color:#16a34a;"
#             "padding:2px 6px;border-radius:4px;font-size:10px;font-weight:600;';"
#             "this.e.innerText='🏭 '+v;"
#             "}else if(v==='—'){"
#             "this.e.style.cssText='color:#94A3B8;font-size:10px;';"
#             "this.e.innerText=v;"
#             "}else{"
#             "this.e.style.cssText='background:#EFF6FF;color:#2563EB;"
#             "padding:2px 6px;border-radius:4px;font-size:10px;';"
#             "this.e.innerText='🚚 '+v;"
#             "};}"
#             "getGui(){return this.e;}}"
#         )
#         gb4 = GridOptionsBuilder.from_dataframe(df_bd2)
#         gb4.configure_column("Material",    width=82)
#         gb4.configure_column("Description", width=215)
#         gb4.configure_column("Level",       width=85)
#         gb4.configure_column("Qty",         width=75)
#         gb4.configure_column("Unit",        width=50)
#         gb4.configure_column("Type",        width=100)
#         gb4.configure_column("Supplier",    width=170, cellRenderer=sup_r3)
#         gb4.configure_column("Location",    width=130)
#         gb4.configure_column("Transit",     width=58)
#         gb4.configure_column("Std Price",   width=80)
#         gb4.configure_grid_options(rowHeight=36, headerHeight=32)
#         gb4.configure_default_column(resizable=True, sortable=True, filter=False)
#         AgGrid(
#             df_bd2, gridOptions=gb4.build(), height=320,
#             allow_unsafe_jscode=True, theme="alpine", custom_css=_AGGRID_CSS,
#         )

#     # ── Risk Cascade ──────────────────────────────────────────────────────────
#     with risk_tab:
#         sec("Risk Cascade Analysis")
#         risks = []

#         if snr["risk"] in ["CRITICAL", "WARNING"]:
#             risks.append({
#                 "icon": "⛔", "sev": 3, "color": "#EF4444", "bg": "#FEF2F2",
#                 "title": f"Finished Good at {snr['risk'].title()} Risk",
#                 "detail": (
#                     f"{snr['name']} has {round(snr['days_cover'])}d of cover. "
#                     f"SIH={round(snr['sih'])} vs SAP SS={round(snr['safety_stock'])}. "
#                     f"Production continuity at risk."
#                 ),
#                 "action": (
#                     f"Order {int(snr.get('repl_quantity', 0))} units immediately. "
#                     f"Contact procurement today."
#                 ),
#             })
#         if cn > 0:
#             risks.append({
#                 "icon": "⚠", "sev": 2, "color": "#F59E0B", "bg": "#FFFBEB",
#                 "title": f"Missing Supplier Data — {cn} External Components",
#                 "detail": (
#                     f"{cn} of {external_n} external components have no named supplier. "
#                     f"Single-source risk cannot be assessed for these."
#                 ),
#                 "action": "Procurement to verify and update BOM with supplier names and lead times.",
#             })
#         if 0 < us <= 2:
#             risks.append({
#                 "icon": "⚠", "sev": 2, "color": "#F59E0B", "bg": "#FFFBEB",
#                 "title": f"Supplier Concentration — {us} Unique Supplier(s)",
#                 "detail": (
#                     f"High dependency on {us} supplier(s). "
#                     f"Any disruption cascades to multiple components."
#                 ),
#                 "action": "Evaluate dual-sourcing for critical external components.",
#             })
#         if external_n > 0:
#             locs = list({
#                 str(r)
#                 for r in bsn[bsn["Procurement type"] == "F"]["Supplier Location"]
#                 .dropna().tolist()[:4]
#             })
#             risks.append({
#                 "icon": "🌍", "sev": 1, "color": "#3B82F6", "bg": "#EFF6FF",
#                 "title": f"External Procurement: {external_n} Components",
#                 "detail": (
#                     f"External components depend on supplier availability and transit times. "
#                     f"Suppliers in: {', '.join(locs) if locs else 'unknown'}."
#                 ),
#                 "action": "Review lead times — add stock buffers for long-transit items.",
#             })

#         if not risks:
#             st.success("✓ No critical propagation risks identified.")
#         else:
#             for r in sorted(risks, key=lambda x: -x["sev"]):
#                 st.markdown(
#                     f"<div style='"
#                     f"background:{r['bg']};"
#                     f"border:1px solid {r['color']}40;"
#                     f"border-left:4px solid {r['color']};"
#                     f"border-radius:8px;"
#                     f"padding:12px 14px;"
#                     f"margin-bottom:8px;"
#                     f"'>"
#                     f"<div style='display:flex;align-items:center;gap:8px;margin-bottom:5px;'>"
#                     f"<span style='font-size:16px;'>{r['icon']}</span>"
#                     f"<div style='font-size:12px;font-weight:800;color:{r['color']};'>"
#                     f"{r['title']}</div>"
#                     f"</div>"
#                     f"<div style='font-size:11px;color:#475569;margin-bottom:5px;'>"
#                     f"{r['detail']}</div>"
#                     f"<div style='font-size:11px;color:{r['color']};font-weight:600;'>"
#                     f"→ {r['action']}</div>"
#                     f"</div>",
#                     unsafe_allow_html=True,
#                 )

#         consol2   = get_supplier_consolidation(data, summary)
#         relevant2 = consol2[
#             consol2.material_list.apply(lambda x: snid in x)
#             & (consol2.finished_goods_supplied > 1)
#             & consol2.consolidation_opportunity
#         ]
#         if len(relevant2) > 0:
#             sec("Supplier Consolidation Opportunities")
#             for _, r2 in relevant2.iterrows():
#                 others = [MATERIAL_LABELS.get(m, m)[:18] for m in r2["material_list"] if m != snid]
#                 st.markdown(
#                     f"<div class='prow'><div style='font-size:14px;'>🏭</div>"
#                     f"<div style='flex:1;'>"
#                     f"<div style='font-size:12px;font-weight:800;'>{r2['supplier']}</div>"
#                     f"<div style='font-size:10px;color:var(--t3);'>"
#                     f"{r2['city']} · {r2['email']}</div>"
#                     f"<div style='font-size:10px;color:var(--t2);margin-top:2px;'>"
#                     f"Also supplies: {', '.join(others[:3])}</div>"
#                     f"</div>"
#                     f"<div style='font-size:10px;font-weight:700;color:var(--or);'>"
#                     f"⚡ Consolidate order</div>"
#                     f"</div>",
#                     unsafe_allow_html=True,
#                 )

#         if st.session_state.azure_client:
#             sec("Ask ARIA About This Network")
#             st.info("ℹ️ Insights are scoped to the currently selected finished good.")
#             uq = st.text_input(
#                 "Question",
#                 placeholder="e.g. Which supplier provides more than 1 material?",
#                 key="snq",
#                 label_visibility="collapsed",
#             )
#             if uq and st.button("Ask ARIA", key="sna"):
#                 bom_lines = []
#                 for _, row in bsn.iterrows():
#                     mat_desc  = _safe(row.get("Material Description"),
#                                       fallback=str(row.get("Material")), maxlen=40)
#                     qty       = row.get("Effective Order Qty") or row.get("Comp. Qty (CUn)")
#                     fixed     = "X (order exactly 1)" if row.get("Fixed Qty Flag") else ""
#                     sup       = _safe(row.get("Supplier Display"))
#                     loc       = _safe(row.get("Supplier Location"))
#                     transit   = _safe(row.get("Transit Days"))
#                     rel       = _safe(row.get("Supplier Reliability"))
#                     sp        = row.get("Standard Price")
#                     std_price = f"${sp:.2f}" if pd.notna(sp) else "—"
#                     bom_lines.append(
#                         f"- {mat_desc} | Qty: {qty} {fixed} | Price: {std_price} "
#                         f"| Supplier: {sup} | Location: {loc} "
#                         f"| Transit: {transit}d | Reliability: {rel}"
#                     )

#                 ctx3 = (
#                     f"Material: {snr['name']} (ID: {snid})\n"
#                     f"Risk: {snr['risk']}\n"
#                     f"Total: {tc} | Inhouse: {inhouse_n} | External: {external_n}\n"
#                     f"Missing supplier: {cn} | Unique suppliers: {us}\n"
#                     f"BOM details:\n" + "\n".join(bom_lines)
#                 )
#                 with st.spinner("Thinking…"):
#                     ans = chat_with_data(
#                         st.session_state.azure_client, AZURE_DEPLOYMENT, uq, ctx3
#                     )
#                 st.markdown(
#                     f"<div class='ic' style='margin-top:8px;'>"
#                     f"<div class='il'>◈ ARIA</div>"
#                     f"<div class='ib'>{ans}</div></div>",
#                     unsafe_allow_html=True,
#                 )

#     st.markdown(
#         '<div class="pfooter">🕸️ Powered by <strong>MResult</strong></div>',
#         unsafe_allow_html=True,
#     )


# # """
# # tabs/supply_network.py
# # Supply Network tab: BOM propagation map (Sankey diagram), component detail table,
# # risk cascade analysis, and supplier consolidation opportunities.
# # """

# # import streamlit as st
# # import pandas as pd
# # import plotly.graph_objects as go

# # from st_aggrid import AgGrid, GridOptionsBuilder, JsCode

# # from utils.helpers import sec, note, sbadge, ORANGE, AZURE_DEPLOYMENT
# # from data_loader import get_bom_components, get_supplier_consolidation
# # from agent import interpret_chart, chat_with_data

# # _AGGRID_CSS = {
# #     ".ag-root-wrapper": {"border": "1px solid #E2E8F0!important", "border-radius": "12px!important"},
# #     ".ag-header":       {"background": "#F8FAFE!important"},
# #     ".ag-row-even":     {"background": "#FFFFFF!important"},
# #     ".ag-row-odd":      {"background": "#F8FAFE!important"},
# # }


# # def render():
# #     data            = st.session_state.data
# #     summary         = st.session_state.summary
# #     MATERIAL_LABELS = st.session_state.material_labels

# #     st.markdown(
# #         "<div style='font-size:15px;font-weight:800;margin-bottom:4px;'>Supply Network</div>"
# #         "<div style='font-size:12px;color:var(--t3);margin-bottom:14px;'>"
# #         "BOM structure · Supplier locations · Risk cascade · Consolidation intelligence</div>",
# #         unsafe_allow_html=True,
# #     )

# #     snn  = st.selectbox("Finished Good", [r["name"] for _, r in summary.iterrows()], key="snm")
# #     snid = summary[summary.name == snn]["material"].values[0]
# #     snr  = summary[summary.material == snid].iloc[0]
# #     bsn  = get_bom_components(data, snid)

# #     if not len(bsn):
# #         st.markdown(
# #             "<div class='flag-box'><div style='font-size:22px;margin-bottom:8px;'>🕸️</div>"
# #             "<div style='font-size:14px;font-weight:800;color:var(--t2);'>No BOM data for this material</div></div>",
# #             unsafe_allow_html=True,
# #         )
# #         return

# #     cw        = int(bsn["Supplier Name(Vendor)"].notna().sum())
# #     cn        = len(bsn[bsn["Supplier Display"].str.startswith("⚠", na=False)])
# #     us        = int(bsn["Supplier Name(Vendor)"].dropna().nunique())
# #     tc        = len(bsn)
# #     inhouse_n = int((bsn["Procurement type"] == "E").sum())
# #     external_n = int((bsn["Procurement type"] == "F").sum())

# #     n1, n2, n3, n4 = st.columns(4)
# #     for col, val, lbl, vc in [
# #         (n1, tc,        "Total Components",  "#1E293B"),
# #         (n2, inhouse_n, "Revvity Inhouse",   "#22C55E"),
# #         (n3, cn,        "Missing Supplier",  "#F59E0B" if cn > 0 else "#1E293B"),
# #         (n4, us,        "Unique Ext Suppliers", "#1E293B"),
# #     ]:
# #         with col:
# #             st.markdown(
# #                 f"<div class='sc'><div style='flex:1;'>"
# #                 f"<div class='sv' style='color:{vc};'>{val}</div>"
# #                 f"<div class='sl'>{lbl}</div></div></div>",
# #                 unsafe_allow_html=True,
# #             )

# #     sn_tab, comp_tab, risk_tab = st.tabs(["🕸️  BOM Map", "📋  Components", "⚠️  Risk Analysis"])

# #     # ── BOM Map – Sankey diagram (improved layout) ─────────────────────────────
# #     with sn_tab:
# #         sec("BOM Propagation Map")
# #         # Legend as HTML list
# #         st.markdown("""
# #         <div class='note-box'>
# #         <strong>Colour legend:</strong>
# #         <ul style='margin:5px 0 0 20px; padding-left:0;'>
# #         <li>🔵 <strong>Blue</strong> = External component with named supplier</li>
# #         <li>🟢 <strong>Green</strong> = Inhouse component (Revvity)</li>
# #         <li>🟡 <strong>Amber</strong> = External component with <strong>missing supplier data</strong></li>
# #         <li>🟣 <strong>Purple</strong> = Supplier node</li>
# #         <li>Root node colour matches finished good risk (🔴 Critical / 🟠 Warning / 🟢 Healthy)</li>
# #         </ul>
# #         Hover over nodes for details. Use the interactive controls to zoom/pan.
# #         </div>
# #         """, unsafe_allow_html=True)

# #         # Build node list and links
# #         nodes = []
# #         node_colors = []
# #         node_map = {}

# #         # Root node
# #         root_name = snr["name"]
# #         risk_color_map = {"CRITICAL": "#EF4444", "WARNING": "#F59E0B", "HEALTHY": "#22C55E"}
# #         root_color = risk_color_map.get(snr["risk"], "#94A3B8")
# #         nodes.append(root_name)
# #         node_colors.append(root_color)
# #         node_map[root_name] = 0

# #         sources = []
# #         targets = []
# #         values = []

# #         # Process each BOM row
# #         for _, row in bsn.iterrows():
# #             # Component label (shortened)
# #             comp_desc = str(row["Material Description"])[:30] if pd.notna(row["Material Description"]) else str(row["Material"])
# #             comp_label = comp_desc
# #             sup_display = row.get("Supplier Display", "—")
# #             proc_type = str(row.get("Procurement type", "")).strip()
# #             qty_raw = row.get("Effective Order Qty", row["Comp. Qty (CUn)"])
# #             try:
# #                 qty = float(qty_raw) if pd.notna(qty_raw) else 1.0
# #             except:
# #                 qty = 1.0

# #             # Add component node
# #             if comp_label not in node_map:
# #                 if proc_type == "E":
# #                     comp_color = "#22C55E"
# #                 elif sup_display.startswith("⚠"):
# #                     comp_color = "#F59E0B"
# #                 else:
# #                     comp_color = "#3B82F6"
# #                 nodes.append(comp_label)
# #                 node_colors.append(comp_color)
# #                 node_map[comp_label] = len(nodes) - 1

# #             # Root -> component
# #             sources.append(node_map[root_name])
# #             targets.append(node_map[comp_label])
# #             values.append(qty)

# #             # Supplier node (if external and named)
# #             if sup_display not in ["Revvity Inhouse", "—"] and not sup_display.startswith("⚠"):
# #                 sup_label = sup_display[:25]
# #                 if sup_label not in node_map:
# #                     nodes.append(sup_label)
# #                     node_colors.append("#8B5CF6")
# #                     node_map[sup_label] = len(nodes) - 1
# #                 sources.append(node_map[comp_label])
# #                 targets.append(node_map[sup_label])
# #                 values.append(1.0)

# #         # Build Sankey figure with improved layout
# #         fig = go.Figure(data=[go.Sankey(
# #             arrangement="snap",
# #             node=dict(
# #                 pad=30,               # more padding between nodes
# #                 thickness=15,
# #                 line=dict(color="white", width=0.5),
# #                 label=nodes,
# #                 color=node_colors,
# #                 hovertemplate="<b>%{label}</b><extra></extra>"
# #             ),
# #             link=dict(
# #                 source=sources,
# #                 target=targets,
# #                 value=values,
# #                 color="rgba(160,160,160,0.4)"
# #             )
# #         )])
# #         fig.update_layout(
# #             title=None,
# #             font=dict(size=11, family="Inter", color="#1E293B"),
# #             height=550,               # taller for better visibility
# #             margin=dict(l=20, r=20, t=20, b=20),
# #             paper_bgcolor="white",
# #             plot_bgcolor="white"
# #         )
# #         st.plotly_chart(fig, use_container_width=True)

# #         if st.session_state.azure_client:
# #             if st.button("◈ Interpret BOM Map", key="interp_bom_sankey"):
# #                 with st.spinner("ARIA interpreting…"):
# #                     bom_ctx = {
# #                         "material": snr["name"], "total_components": tc,
# #                         "inhouse": inhouse_n, "external_named": cw - inhouse_n,
# #                         "missing_supplier": cn, "unique_suppliers": us, "risk": snr["risk"],
# #                     }
# #                     interp = interpret_chart(
# #                         st.session_state.azure_client, AZURE_DEPLOYMENT,
# #                         "BOM Risk Propagation Map", bom_ctx,
# #                         "What are the key supply chain risks in this BOM and what should procurement prioritise?",
# #                     )
# #                 st.markdown(
# #                     f"<div class='ic' style='margin-top:8px;'><div class='il'>◈ ARIA</div>"
# #                     f"<div class='ib'>{interp}</div></div>",
# #                     unsafe_allow_html=True,
# #                 )

# #     # ── Component Detail (unchanged) ─────────────────────────────────────────
# #     with comp_tab:
# #         sec("Component Detail")
# #         bom_display2 = []
# #         for _, b in bsn.iterrows():
# #             eff_qty = b.get("Effective Order Qty", b["Comp. Qty (CUn)"])
# #             fq_txt  = ("1 (Fixed)" if b.get("Fixed Qty Flag", False)
# #                        else str(round(float(eff_qty), 3)) if pd.notna(eff_qty) else "—")
# #             bom_display2.append({
# #                 "Material":    str(b["Material"]),
# #                 "Description": str(b["Material Description"])[:36] if pd.notna(b["Material Description"]) else "—",
# #                 "Level":       str(b["Level"])[:25] if pd.notna(b["Level"]) else "—",
# #                 "Qty":         fq_txt,
# #                 "Unit":        str(b["Component unit"]) if pd.notna(b["Component unit"]) else "—",
# #                 "Type":        b.get("Procurement Label", "—"),
# #                 "Supplier":    b.get("Supplier Display", "—"),
# #                 "Location":    b.get("Supplier Location", "—"),
# #                 "Transit":     f"{b.get('Transit Days', '—')}d" if b.get("Transit Days") is not None else "—",
# #                 "Std Price":   f"${b.get('Standard Price', 0):.2f}" if pd.notna(b.get('Standard Price')) else "—",
# #             })
# #         df_bd2  = pd.DataFrame(bom_display2)
# #         sup_r3  = JsCode("""class R{init(p){const v=p.value||'';this.e=document.createElement('span');if(v.startsWith('⚠')){this.e.style.cssText='background:#FEF3C7;color:#F59E0B;padding:2px 6px;border-radius:4px;font-size:10px;font-weight:600;';this.e.innerText=v;}else if(v==='Revvity Inhouse'){this.e.style.cssText='background:#DCFCE7;color:#16a34a;padding:2px 6px;border-radius:4px;font-size:10px;font-weight:600;';this.e.innerText='🏭 '+v;}else{this.e.style.cssText='background:#EFF6FF;color:#2563EB;padding:2px 6px;border-radius:4px;font-size:10px;';this.e.innerText='🚚 '+v;};}getGui(){return this.e;}}""")
# #         gb4     = GridOptionsBuilder.from_dataframe(df_bd2)
# #         gb4.configure_column("Material",    width=82)
# #         gb4.configure_column("Description", width=215)
# #         gb4.configure_column("Level",       width=85)
# #         gb4.configure_column("Qty",         width=75)
# #         gb4.configure_column("Unit",        width=50)
# #         gb4.configure_column("Type",        width=100)
# #         gb4.configure_column("Supplier",    width=170, cellRenderer=sup_r3)
# #         gb4.configure_column("Location",    width=130)
# #         gb4.configure_column("Transit",     width=58)
# #         gb4.configure_column("Std Price",   width=80)
# #         gb4.configure_grid_options(rowHeight=36, headerHeight=32)
# #         gb4.configure_default_column(resizable=True, sortable=True, filter=False)
# #         AgGrid(df_bd2, gridOptions=gb4.build(), height=320,
# #                allow_unsafe_jscode=True, theme="alpine", custom_css=_AGGRID_CSS)

# #     # ── Risk Cascade (unchanged) ─────────────────────────────────────────────
# #     with risk_tab:
# #         sec("Risk Cascade Analysis")
# #         risks = []
# #         if snr["risk"] in ["CRITICAL", "WARNING"]:
# #             risks.append({
# #                 "icon": "⛔", "sev": 3, "color": "#EF4444", "bg": "#FEF2F2",
# #                 "title": f"Finished Good at {snr['risk'].title()} Risk",
# #                 "detail": (f"{snr['name']} has {round(snr['days_cover'])}d of cover. "
# #                            f"SIH={round(snr['sih'])} vs SAP SS={round(snr['safety_stock'])}. "
# #                            f"Production continuity at risk."),
# #                 "action": f"Order {int(snr.get('repl_quantity', 0))} units immediately. Contact procurement today.",
# #             })
# #         if cn > 0:
# #             risks.append({
# #                 "icon": "⚠", "sev": 2, "color": "#F59E0B", "bg": "#FFFBEB",
# #                 "title": f"Missing Supplier Data — {cn} External Components",
# #                 "detail": (f"{cn} of {external_n} external components have no named supplier. "
# #                            f"Single-source risk cannot be assessed for these."),
# #                 "action": "Procurement to verify and update BOM with supplier names and lead times.",
# #             })
# #         if 0 < us <= 2:
# #             risks.append({
# #                 "icon": "⚠", "sev": 2, "color": "#F59E0B", "bg": "#FFFBEB",
# #                 "title": f"Supplier Concentration — {us} Unique Supplier(s)",
# #                 "detail": f"High dependency on {us} supplier(s). Any disruption cascades to multiple components simultaneously.",
# #                 "action": "Evaluate dual-sourcing for critical external components.",
# #             })
# #         ext_comps = bsn[bsn["Procurement type"] == "F"]
# #         if len(ext_comps) > 0:
# #             locs = list(set([str(r) for r in bsn[bsn["Procurement type"] == "F"]["Supplier Location"].dropna().tolist()[:4]]))
# #             risks.append({
# #                 "icon": "🌍", "sev": 1, "color": "#3B82F6", "bg": "#EFF6FF",
# #                 "title": f"External Procurement: {len(ext_comps)} Components",
# #                 "detail": (f"External components depend on supplier availability and transit times. "
# #                            f"Suppliers located in: {', '.join(locs)}."),
# #                 "action": "Review external component lead times — stock buffers for long-transit items.",
# #             })

# #         if not risks:
# #             st.markdown(
# #                 "<div style='padding:10px 13px;background:var(--gbg);border:1px solid rgba(34,197,94,0.2);"
# #                 "border-radius:var(--r);font-size:12px;color:#14532d;'>"
# #                 "✓ No critical propagation risks identified.</div>",
# #                 unsafe_allow_html=True,
# #             )
# #         else:
# #             for r in sorted(risks, key=lambda x: -x["sev"]):
# #                 st.markdown(
# #                     f"<div style='background:{r['bg']};border:1px solid {r['color']}40;"
# #                     f"border-left:4px solid {r['color']};border-radius:var(--r);"
# #                     f"padding:12px 14px;margin-bottom:8px;'>"
# #                     f"<div style='display:flex;align-items:center;gap:8px;margin-bottom:5px;'>"
# #                     f"<span style='font-size:16px;'>{r['icon']}</span>"
# #                     f"<div style='font-size:12px;font-weight:800;color:{r['color']};'>{r['title']}</div>"
# #                     f"</div>"
# #                     f"<div style='font-size:11px;color:var(--t2);margin-bottom:5px;'>{r['detail']}</div>"
# #                     f"<div style='font-size:11px;color:{r['color']};font-weight:600;'>→ {r['action']}</div>"
# #                     f"</div>",
# #                     unsafe_allow_html=True,
# #                 )

# #         # Consolidation opportunities
# #         consol2   = get_supplier_consolidation(data, summary)
# #         relevant2 = consol2[
# #             consol2.material_list.apply(lambda x: snid in x)
# #             & (consol2.finished_goods_supplied > 1)
# #             & consol2.consolidation_opportunity
# #         ]
# #         if len(relevant2) > 0:
# #             sec("Supplier Consolidation Opportunities")
# #             for _, r2 in relevant2.iterrows():
# #                 others = [MATERIAL_LABELS.get(m, m)[:18] for m in r2["material_list"] if m != snid]
# #                 st.markdown(
# #                     f"<div class='prow'><div style='font-size:14px;'>🏭</div>"
# #                     f"<div style='flex:1;'>"
# #                     f"<div style='font-size:12px;font-weight:800;'>{r2['supplier']}</div>"
# #                     f"<div style='font-size:10px;color:var(--t3);'>{r2['city']} · {r2['email']}</div>"
# #                     f"<div style='font-size:10px;color:var(--t2);margin-top:2px;'>Also supplies: {', '.join(others[:3])}</div>"
# #                     f"</div>"
# #                     f"<div style='font-size:10px;font-weight:700;color:var(--or);'>⚡ Consolidate order</div>"
# #                     f"</div>",
# #                     unsafe_allow_html=True,
# #                 )

# #         # ── Ask ARIA with rich BOM context (including Standard Price) ─────────
# #         if st.session_state.azure_client:
# #             sec("Ask ARIA About This Network")
# #             st.info("ℹ️ This assistant provides supplier‑related insights only for the currently selected finished good.")
# #             uq = st.text_input(
# #                 "Question",
# #                 placeholder="e.g. Which supplier provides more than 1 material for DELFIA Wash Concentrate?",
# #                 key="snq", label_visibility="collapsed",
# #             )
# #             if uq and st.button("Ask ARIA", key="sna"):
# #                 bom_lines = []
# #                 for _, row in bsn.iterrows():
# #                     mat_desc = str(row["Material Description"])[:40] if pd.notna(row["Material Description"]) else str(row["Material"])
# #                     qty = row["Effective Order Qty"] if "Effective Order Qty" in row else row["Comp. Qty (CUn)"]
# #                     fixed = "X (order exactly 1)" if row.get("Fixed Qty Flag") else ""
# #                     sup = row.get("Supplier Display", "—")
# #                     loc = row.get("Supplier Location", "—")
# #                     transit = row.get("Transit Days", "—")
# #                     reliability = row.get("Supplier Reliability", "—")
# #                     std_price = row.get("Standard Price", "—")
# #                     if pd.notna(std_price):
# #                         std_price = f"${std_price:.2f}"
# #                     bom_lines.append(f"- Component: {mat_desc} | Qty: {qty} {fixed} | Std Price: {std_price} | Supplier: {sup} | Location: {loc} | Transit: {transit}d | Reliability: {reliability}")
# #                 bom_table = "\n".join(bom_lines)

# #                 ctx3 = (
# #                     f"Material: {snr['name']} (ID: {snid})\n"
# #                     f"Risk: {snr['risk']}\n"
# #                     f"Total components: {tc}\n"
# #                     f"Inhouse components: {inhouse_n}\n"
# #                     f"External components: {external_n}\n"
# #                     f"Missing supplier data: {cn} components\n"
# #                     f"Unique external suppliers: {us}\n"
# #                     f"BOM details:\n{bom_table}"
# #                 )
# #                 with st.spinner("Thinking…"):
# #                     ans = chat_with_data(st.session_state.azure_client, AZURE_DEPLOYMENT, uq, ctx3)
# #                 st.markdown(
# #                     f"<div class='ic' style='margin-top:8px;'><div class='il'>◈ ARIA</div>"
# #                     f"<div class='ib'>{ans}</div></div>",
# #                     unsafe_allow_html=True,
# #                 )

# #     st.markdown('<div class="pfooter">🕸️ Powered by <strong>MResult</strong></div>', unsafe_allow_html=True)



# # # # # # # # # """
# # # # # # # # # tabs/supply_network.py
# # # # # # # # # Supply Network tab: BOM propagation map, component detail table,
# # # # # # # # # risk cascade analysis, and supplier consolidation opportunities.
# # # # # # # # # """

# # # # # # # # # import streamlit as st
# # # # # # # # # import pandas as pd

# # # # # # # # # from st_aggrid import AgGrid, GridOptionsBuilder, JsCode

# # # # # # # # # from utils.helpers import sec, note, sbadge, plot_bom_tree, ORANGE, AZURE_DEPLOYMENT
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

# # # # # # # # #     # ── BOM Map ───────────────────────────────────────────────────────────────
# # # # # # # # #     with sn_tab:
# # # # # # # # #         sec("BOM Propagation Map")
# # # # # # # # #         note("Blue = External supplier named. Amber = External, no supplier data. "
# # # # # # # # #              "Green = Revvity Inhouse production. Hover nodes for detail.")
# # # # # # # # #         risk_color_map = {"CRITICAL": "#EF4444", "WARNING": "#F59E0B", "HEALTHY": "#22C55E"}
# # # # # # # # #         root_color     = risk_color_map.get(snr["risk"], "#94A3B8")
# # # # # # # # #         fig_tree       = plot_bom_tree(bsn, snr["name"], root_color)
# # # # # # # # #         st.plotly_chart(fig_tree, use_container_width=True)

# # # # # # # # #         if st.session_state.azure_client:
# # # # # # # # #             if st.button("◈ Interpret BOM Map", key="interp_bom_tree"):
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
# # # # # # # # #         gb4.configure_grid_options(rowHeight=36, headerHeight=32)
# # # # # # # # #         gb4.configure_default_column(resizable=True, sortable=True, filter=False)
# # # # # # # # #         AgGrid(df_bd2, gridOptions=gb4.build(), height=320,
# # # # # # # # #                allow_unsafe_jscode=True, theme="alpine", custom_css=_AGGRID_CSS)

# # # # # # # # #     # ── Risk Cascade ──────────────────────────────────────────────────────────
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

# # # # # # # # #         # Free-form ARIA chat
# # # # # # # # #         if st.session_state.azure_client:
# # # # # # # # #             sec("Ask ARIA About This Network")
# # # # # # # # #             uq = st.text_input(
# # # # # # # # #                 "Question",
# # # # # # # # #                 placeholder="e.g. Which supplier poses the highest single-source risk?",
# # # # # # # # #                 key="snq", label_visibility="collapsed",
# # # # # # # # #             )
# # # # # # # # #             if uq and st.button("Ask ARIA", key="sna"):
# # # # # # # # #                 ctx3 = (
# # # # # # # # #                     f"Material: {snr['name']}, Risk: {snr['risk']}, Components: {tc}, "
# # # # # # # # #                     f"Inhouse: {inhouse_n}, External: {external_n}, Missing supplier: {cn}, "
# # # # # # # # #                     f"Unique suppliers: {us}, "
# # # # # # # # #                     f"Suppliers: {', '.join(bsn['Supplier Name(Vendor)'].dropna().unique().tolist()[:5])}"
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
# # # # # # # # Supply Network tab: BOM propagation map (colour-coded by risk/supplier type),
# # # # # # # # component detail table, risk cascade analysis, and supplier consolidation opportunities.
# # # # # # # # """

# # # # # # # # import streamlit as st
# # # # # # # # import pandas as pd

# # # # # # # # from st_aggrid import AgGrid, GridOptionsBuilder, JsCode

# # # # # # # # from utils.helpers import sec, note, sbadge, plot_bom_tree, ORANGE, AZURE_DEPLOYMENT
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

# # # # # # # #     # ── BOM Map (colour‑coded knowledge graph) ─────────────────────────────────
# # # # # # # #     with sn_tab:
# # # # # # # #         sec("BOM Propagation Map")
# # # # # # # #         note("""
# # # # # # # #         **Colour legend:**  
# # # # # # # #         - 🟢 **Green** = Inhouse component (Revvity)  
# # # # # # # #         - 🔵 **Blue** = External component with named supplier  
# # # # # # # #         - 🟡 **Amber** = External component with **missing supplier data**  
# # # # # # # #         - 🟣 **Purple** = Supplier node  
# # # # # # # #         - Root node colour matches finished good risk (🔴 Critical / 🟠 Warning / 🟢 Healthy)  
# # # # # # # #         Hover over any node for details.
# # # # # # # #         """)
# # # # # # # #         risk_color_map = {"CRITICAL": "#EF4444", "WARNING": "#F59E0B", "HEALTHY": "#22C55E"}
# # # # # # # #         root_color     = risk_color_map.get(snr["risk"], "#94A3B8")
# # # # # # # #         fig_tree       = plot_bom_tree(bsn, snr["name"], root_color)
# # # # # # # #         st.plotly_chart(fig_tree, use_container_width=True)

# # # # # # # #         if st.session_state.azure_client:
# # # # # # # #             if st.button("◈ Interpret BOM Map", key="interp_bom_tree"):
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

# # # # # # # #         # ── Ask ARIA with rich BOM context ────────────────────────────────────
# # # # # # # #         if st.session_state.azure_client:
# # # # # # # #             sec("Ask ARIA About This Network")
# # # # # # # #             uq = st.text_input(
# # # # # # # #                 "Question",
# # # # # # # #                 placeholder="e.g. Which supplier provides more than 1 material for DELFIA Wash Concentrate?",
# # # # # # # #                 key="snq", label_visibility="collapsed",
# # # # # # # #             )
# # # # # # # #             if uq and st.button("Ask ARIA", key="sna"):
# # # # # # # #                 # Build a detailed BOM table as context
# # # # # # # #                 bom_lines = []
# # # # # # # #                 for _, row in bsn.iterrows():
# # # # # # # #                     mat_desc = str(row["Material Description"])[:40] if pd.notna(row["Material Description"]) else str(row["Material"])
# # # # # # # #                     qty = row["Effective Order Qty"] if "Effective Order Qty" in row else row["Comp. Qty (CUn)"]
# # # # # # # #                     fixed = "X (order exactly 1)" if row.get("Fixed Qty Flag") else ""
# # # # # # # #                     sup = row.get("Supplier Display", "—")
# # # # # # # #                     loc = row.get("Supplier Location", "—")
# # # # # # # #                     transit = row.get("Transit Days", "—")
# # # # # # # #                     reliability = row.get("Supplier Reliability", "—")
# # # # # # # #                     bom_lines.append(f"- Component: {mat_desc} | Qty: {qty} {fixed} | Supplier: {sup} | Location: {loc} | Transit: {transit}d | Reliability: {reliability}")
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
# # # # # # #         (n1, tc,        "Total Components",  "#1E293B"),
# # # # # # #         (n2, inhouse_n, "Revvity Inhouse",   "#22C55E"),
# # # # # # #         (n3, cn,        "Missing Supplier",  "#F59E0B" if cn > 0 else "#1E293B"),
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

# # # # # # #     # ── BOM Map – Sankey diagram (replaces tree) ──────────────────────────────
# # # # # # #     with sn_tab:
# # # # # # #         sec("BOM Propagation Map")
# # # # # # #         note("""
# # # # # # #         **Colour legend:**  
# # # # # # #         - 🔵 **Blue** = External component with named supplier  
# # # # # # #         - 🟢 **Green** = Inhouse component (Revvity)  
# # # # # # #         - 🟡 **Amber** = External component with **missing supplier data**  
# # # # # # #         - 🟣 **Purple** = Supplier node  
# # # # # # #         - Root node colour matches finished good risk (🔴 Critical / 🟠 Warning / 🟢 Healthy)  
# # # # # # #         Hover over nodes for details.
# # # # # # #         """)

# # # # # # #         # Build node list and links for Sankey
# # # # # # #         nodes = []
# # # # # # #         node_colors = []
# # # # # # #         node_map = {}

# # # # # # #         # Root node (finished good)
# # # # # # #         root_name = snr["name"]
# # # # # # #         root_risk_color = {"CRITICAL": "#EF4444", "WARNING": "#F59E0B", "HEALTHY": "#22C55E"}.get(snr["risk"], "#94A3B8")
# # # # # # #         nodes.append(root_name)
# # # # # # #         node_colors.append(root_risk_color)
# # # # # # #         node_map[root_name] = 0

# # # # # # #         sources = []
# # # # # # #         targets = []
# # # # # # #         values = []

# # # # # # #         # Process each BOM row
# # # # # # #         for _, row in bsn.iterrows():
# # # # # # #             comp_desc = str(row["Material Description"])[:40] if pd.notna(row["Material Description"]) else str(row["Material"])
# # # # # # #             comp_label = f"[C] {comp_desc}"
# # # # # # #             sup_display = row.get("Supplier Display", "—")
# # # # # # #             proc_type = str(row.get("Procurement type", "")).strip()
# # # # # # #             qty = row.get("Effective Order Qty", row["Comp. Qty (CUn)"]) if pd.notna(row.get("Effective Order Qty", row["Comp. Qty (CUn)"]) ) else 1
# # # # # # #             # Ensure qty is numeric
# # # # # # #             try:
# # # # # # #                 qty = float(qty)
# # # # # # #             except:
# # # # # # #                 qty = 1.0

# # # # # # #             # Add component node if not already present
# # # # # # #             if comp_label not in node_map:
# # # # # # #                 # Determine component colour
# # # # # # #                 if proc_type == "E":
# # # # # # #                     comp_color = "#22C55E"   # Inhouse
# # # # # # #                 elif sup_display.startswith("⚠"):
# # # # # # #                     comp_color = "#F59E0B"   # Missing supplier
# # # # # # #                 else:
# # # # # # #                     comp_color = "#3B82F6"   # External named
# # # # # # #                 nodes.append(comp_label)
# # # # # # #                 node_colors.append(comp_color)
# # # # # # #                 node_map[comp_label] = len(nodes) - 1

# # # # # # #             # Link root -> component
# # # # # # #             sources.append(node_map[root_name])
# # # # # # #             targets.append(node_map[comp_label])
# # # # # # #             values.append(qty)

# # # # # # #             # Add supplier node if external and named
# # # # # # #             if sup_display not in ["Revvity Inhouse", "—"] and not sup_display.startswith("⚠"):
# # # # # # #                 sup_label = f"[S] {sup_display[:25]}"
# # # # # # #                 if sup_label not in node_map:
# # # # # # #                     nodes.append(sup_label)
# # # # # # #                     node_colors.append("#8B5CF6")  # Purple for suppliers
# # # # # # #                     node_map[sup_label] = len(nodes) - 1
# # # # # # #                 # Link component -> supplier
# # # # # # #                 sources.append(node_map[comp_label])
# # # # # # #                 targets.append(node_map[sup_label])
# # # # # # #                 values.append(1.0)  # connection weight

# # # # # # #         # Build Sankey figure
# # # # # # #         fig_sankey = go.Figure(data=[go.Sankey(
# # # # # # #             arrangement="snap",
# # # # # # #             node=dict(
# # # # # # #                 pad=20,
# # # # # # #                 thickness=20,
# # # # # # #                 line=dict(color="white", width=0.5),
# # # # # # #                 label=nodes,
# # # # # # #                 color=node_colors,
# # # # # # #                 hovertemplate="<b>%{label}</b><extra></extra>"
# # # # # # #             ),
# # # # # # #             link=dict(
# # # # # # #                 source=sources,
# # # # # # #                 target=targets,
# # # # # # #                 value=values,
# # # # # # #                 color="rgba(200,200,200,0.3)"
# # # # # # #             )
# # # # # # #         )])
# # # # # # #         fig_sankey.update_layout(
# # # # # # #             title=None,
# # # # # # #             font=dict(size=11, family="Inter"),
# # # # # # #             height=500,
# # # # # # #             margin=dict(l=20, r=20, t=20, b=20),
# # # # # # #             paper_bgcolor="white",
# # # # # # #         )
# # # # # # #         st.plotly_chart(fig_sankey, use_container_width=True)

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

# # # # # # #     # ── Component Detail (unchanged) ─────────────────────────────────────────
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

# # # # # # #     # ── Risk Cascade (unchanged) ─────────────────────────────────────────────
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

# # # # # # #         # ── Ask ARIA with rich BOM context (including Standard Price) ─────────
# # # # # # #         if st.session_state.azure_client:
# # # # # # #             sec("Ask ARIA About This Network")
# # # # # # #             # Add disclaimer
# # # # # # #             st.info("ℹ️ This assistant provides supplier‑related insights only for the currently selected finished good.")
# # # # # # #             uq = st.text_input(
# # # # # # #                 "Question",
# # # # # # #                 placeholder="e.g. Which supplier provides more than 1 material for DELFIA Wash Concentrate?",
# # # # # # #                 key="snq", label_visibility="collapsed",
# # # # # # #             )
# # # # # # #             if uq and st.button("Ask ARIA", key="sna"):
# # # # # # #                 # Build a detailed BOM table as context, including Standard Price
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
# # # # # # #                     bom_lines.append(f"- Component: {mat_desc} | Qty: {qty} {fixed} | Std Price: {std_price} | Supplier: {sup} | Location: {loc} | Transit: {transit}d | Reliability: {reliability}")
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

# # # # # #     # ── BOM Map – Sankey diagram with clean legend ──────────────────────────────
# # # # # #     with sn_tab:
# # # # # #         sec("BOM Propagation Map")
# # # # # #         # Fixed legend: HTML list inside a note box (no bold/3D)
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
# # # # # #         Hover over nodes for details.
# # # # # #         </div>
# # # # # #         """, unsafe_allow_html=True)

# # # # # #         # Build node list and links for Sankey
# # # # # #         nodes = []
# # # # # #         node_colors = []
# # # # # #         node_map = {}

# # # # # #         # Root node (finished good)
# # # # # #         root_name = str(snr["name"])  # ensure string
# # # # # #         root_risk_color = {"CRITICAL": "#EF4444", "WARNING": "#F59E0B", "HEALTHY": "#22C55E"}.get(snr["risk"], "#94A3B8")
# # # # # #         nodes.append(root_name)
# # # # # #         node_colors.append(root_risk_color)
# # # # # #         node_map[root_name] = 0

# # # # # #         sources = []
# # # # # #         targets = []
# # # # # #         values = []

# # # # # #         # Process each BOM row
# # # # # #         for _, row in bsn.iterrows():
# # # # # #             comp_desc = str(row["Material Description"])[:40] if pd.notna(row["Material Description"]) else str(row["Material"])
# # # # # #             comp_label = f"[C] {comp_desc}"
# # # # # #             sup_display = row.get("Supplier Display", "—")
# # # # # #             proc_type = str(row.get("Procurement type", "")).strip()
# # # # # #             qty = row.get("Effective Order Qty", row["Comp. Qty (CUn)"]) if pd.notna(row.get("Effective Order Qty", row["Comp. Qty (CUn)"]) ) else 1
# # # # # #             # Ensure qty is numeric
# # # # # #             try:
# # # # # #                 qty = float(qty)
# # # # # #             except:
# # # # # #                 qty = 1.0

# # # # # #             # Add component node if not already present
# # # # # #             if comp_label not in node_map:
# # # # # #                 # Determine component colour
# # # # # #                 if proc_type == "E":
# # # # # #                     comp_color = "#22C55E"   # Inhouse
# # # # # #                 elif sup_display.startswith("⚠"):
# # # # # #                     comp_color = "#F59E0B"   # Missing supplier
# # # # # #                 else:
# # # # # #                     comp_color = "#3B82F6"   # External named
# # # # # #                 nodes.append(comp_label)
# # # # # #                 node_colors.append(comp_color)
# # # # # #                 node_map[comp_label] = len(nodes) - 1

# # # # # #             # Link root -> component
# # # # # #             sources.append(node_map[root_name])
# # # # # #             targets.append(node_map[comp_label])
# # # # # #             values.append(qty)

# # # # # #             # Add supplier node if external and named
# # # # # #             if sup_display not in ["Revvity Inhouse", "—"] and not sup_display.startswith("⚠"):
# # # # # #                 sup_label = f"[S] {str(sup_display)[:25]}"
# # # # # #                 if sup_label not in node_map:
# # # # # #                     nodes.append(sup_label)
# # # # # #                     node_colors.append("#8B5CF6")  # Purple for suppliers
# # # # # #                     node_map[sup_label] = len(nodes) - 1
# # # # # #                 # Link component -> supplier
# # # # # #                 sources.append(node_map[comp_label])
# # # # # #                 targets.append(node_map[sup_label])
# # # # # #                 values.append(1.0)  # connection weight

# # # # # #         # Build Sankey figure with normal font weight
# # # # # #         fig_sankey = go.Figure(data=[go.Sankey(
# # # # # #             arrangement="snap",
# # # # # #             node=dict(
# # # # # #                 pad=20,
# # # # # #                 thickness=20,
# # # # # #                 line=dict(color="white", width=0.5),
# # # # # #                 label=nodes,
# # # # # #                 color=node_colors,
# # # # # #                 hovertemplate="<b>%{label}</b><extra></extra>"
# # # # # #             ),
# # # # # #             link=dict(
# # # # # #                 source=sources,
# # # # # #                 target=targets,
# # # # # #                 value=values,
# # # # # #                 color="rgba(200,200,200,0.3)"
# # # # # #             )
# # # # # #         )])
# # # # # #         fig_sankey.update_layout(
# # # # # #             title=None,
# # # # # #             font=dict(size=11, family="Inter", weight="normal"),  # ensure normal font weight
# # # # # #             height=500,
# # # # # #             margin=dict(l=20, r=20, t=20, b=20),
# # # # # #             paper_bgcolor="white",
# # # # # #         )
# # # # # #         st.plotly_chart(fig_sankey, use_container_width=True)

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

# # # # # #     # ── Component Detail ──────────────────────────────────────────────────────
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
# # # # # # #                     f"<div class='ib'>{ans}</div></div>",
# # # # # # #                     unsafe_allow_html=True,
# # # # # # #                 )

# # # # # # #     st.markdown('<div class="pfooter">🕸️ Powered by <strong>MResult</strong></div>', unsafe_allow_html=True)

# # # # # """
# # # # # tabs/supply_network.py
# # # # # Supply Network tab: BOM propagation map (Sankey diagram), component detail table,
# # # # # risk cascade analysis, and supplier consolidation opportunities.
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
# # # # #         st.markdown(
# # # # #             "<div class='flag-box'><div style='font-size:22px;margin-bottom:8px;'>🕸️</div>"
# # # # #             "<div style='font-size:14px;font-weight:800;color:var(--t2);'>No BOM data for this material</div></div>",
# # # # #             unsafe_allow_html=True,
# # # # #         )
# # # # #         return

# # # # #     cw        = int(bsn["Supplier Name(Vendor)"].notna().sum())
# # # # #     cn        = len(bsn[bsn["Supplier Display"].str.startswith("⚠", na=False)])
# # # # #     us        = int(bsn["Supplier Name(Vendor)"].dropna().nunique())
# # # # #     tc        = len(bsn)
# # # # #     inhouse_n = int((bsn["Procurement type"] == "E").sum())
# # # # #     external_n = int((bsn["Procurement type"] == "F").sum())

# # # # #     n1, n2, n3, n4 = st.columns(4)
# # # # #     for col, val, lbl, vc in [
# # # # #         (n1, tc,        "Total Components",  "#1E293B"),
# # # # #         (n2, inhouse_n, "Revvity Inhouse",   "#22C55E"),
# # # # #         (n3, cn,        "Missing Supplier",  "#F59E0B" if cn > 0 else "#1E293B"),
# # # # #         (n4, us,        "Unique Ext Suppliers", "#1E293B"),
# # # # #     ]:
# # # # #         with col:
# # # # #             st.markdown(
# # # # #                 f"<div class='sc'><div style='flex:1;'>"
# # # # #                 f"<div class='sv' style='color:{vc};'>{val}</div>"
# # # # #                 f"<div class='sl'>{lbl}</div></div></div>",
# # # # #                 unsafe_allow_html=True,
# # # # #             )

# # # # #     sn_tab, comp_tab, risk_tab = st.tabs(["🕸️  BOM Map", "📋  Components", "⚠️  Risk Analysis"])

# # # # #     # ── BOM Map – Sankey diagram with clean legend ──────────────────────────────
# # # # #     with sn_tab:
# # # # #         sec("BOM Propagation Map")
# # # # #         # Fixed legend: HTML list inside a note box (no bold/3D)
# # # # #         st.markdown("""
# # # # #         <div class='note-box'>
# # # # #         <strong>Colour legend:</strong>
# # # # #         <ul style='margin:5px 0 0 20px; padding-left:0;'>
# # # # #         <li>🔵 <strong>Blue</strong> = External component with named supplier</li>
# # # # #         <li>🟢 <strong>Green</strong> = Inhouse component (Revvity)</li>
# # # # #         <li>🟡 <strong>Amber</strong> = External component with <strong>missing supplier data</strong></li>
# # # # #         <li>🟣 <strong>Purple</strong> = Supplier node</li>
# # # # #         <li>Root node colour matches finished good risk (🔴 Critical / 🟠 Warning / 🟢 Healthy)</li>
# # # # #         </ul>
# # # # #         Hover over nodes for details.
# # # # #         </div>
# # # # #         """, unsafe_allow_html=True)

# # # # #         # Build node list and links for Sankey
# # # # #         nodes = []
# # # # #         node_colors = []
# # # # #         node_map = {}

# # # # #         # Root node (finished good)
# # # # #         root_name = str(snr["name"])  # ensure string
# # # # #         root_risk_color = {"CRITICAL": "#EF4444", "WARNING": "#F59E0B", "HEALTHY": "#22C55E"}.get(snr["risk"], "#94A3B8")
# # # # #         nodes.append(root_name)
# # # # #         node_colors.append(root_risk_color)
# # # # #         node_map[root_name] = 0

# # # # #         sources = []
# # # # #         targets = []
# # # # #         values = []

# # # # #         # Process each BOM row
# # # # #         for _, row in bsn.iterrows():
# # # # #             comp_desc = str(row["Material Description"])[:40] if pd.notna(row["Material Description"]) else str(row["Material"])
# # # # #             comp_label = f"[C] {comp_desc}"
# # # # #             sup_display = row.get("Supplier Display", "—")
# # # # #             proc_type = str(row.get("Procurement type", "")).strip()
# # # # #             qty = row.get("Effective Order Qty", row["Comp. Qty (CUn)"]) if pd.notna(row.get("Effective Order Qty", row["Comp. Qty (CUn)"]) ) else 1
# # # # #             # Ensure qty is numeric
# # # # #             try:
# # # # #                 qty = float(qty)
# # # # #             except:
# # # # #                 qty = 1.0

# # # # #             # Add component node if not already present
# # # # #             if comp_label not in node_map:
# # # # #                 # Determine component colour
# # # # #                 if proc_type == "E":
# # # # #                     comp_color = "#22C55E"   # Inhouse
# # # # #                 elif sup_display.startswith("⚠"):
# # # # #                     comp_color = "#F59E0B"   # Missing supplier
# # # # #                 else:
# # # # #                     comp_color = "#3B82F6"   # External named
# # # # #                 nodes.append(comp_label)
# # # # #                 node_colors.append(comp_color)
# # # # #                 node_map[comp_label] = len(nodes) - 1

# # # # #             # Link root -> component
# # # # #             sources.append(node_map[root_name])
# # # # #             targets.append(node_map[comp_label])
# # # # #             values.append(qty)

# # # # #             # Add supplier node if external and named
# # # # #             if sup_display not in ["Revvity Inhouse", "—"] and not sup_display.startswith("⚠"):
# # # # #                 sup_label = f"[S] {str(sup_display)[:25]}"
# # # # #                 if sup_label not in node_map:
# # # # #                     nodes.append(sup_label)
# # # # #                     node_colors.append("#8B5CF6")  # Purple for suppliers
# # # # #                     node_map[sup_label] = len(nodes) - 1
# # # # #                 # Link component -> supplier
# # # # #                 sources.append(node_map[comp_label])
# # # # #                 targets.append(node_map[sup_label])
# # # # #                 values.append(1.0)  # connection weight

# # # # #         # Build Sankey figure with normal font weight
# # # # #         fig_sankey = go.Figure(data=[go.Sankey(
# # # # #             arrangement="snap",
# # # # #             node=dict(
# # # # #                 pad=20,
# # # # #                 thickness=20,
# # # # #                 line=dict(color="white", width=0.5),
# # # # #                 label=nodes,
# # # # #                 color=node_colors,
# # # # #                 hovertemplate="<b>%{label}</b><extra></extra>"
# # # # #             ),
# # # # #             link=dict(
# # # # #                 source=sources,
# # # # #                 target=targets,
# # # # #                 value=values,
# # # # #                 color="rgba(200,200,200,0.3)"
# # # # #             )
# # # # #         )])
# # # # #         fig_sankey.update_layout(
# # # # #             title=None,
# # # # #             font=dict(size=11, family="Inter", weight="normal"),  # ensure normal font weight
# # # # #             height=500,
# # # # #             margin=dict(l=20, r=20, t=20, b=20),
# # # # #             paper_bgcolor="white",
# # # # #         )
# # # # #         st.plotly_chart(fig_sankey, use_container_width=True)

# # # # #         if st.session_state.azure_client:
# # # # #             if st.button("◈ Interpret BOM Map", key="interp_bom_sankey"):
# # # # #                 with st.spinner("ARIA interpreting…"):
# # # # #                     bom_ctx = {
# # # # #                         "material": snr["name"], "total_components": tc,
# # # # #                         "inhouse": inhouse_n, "external_named": cw - inhouse_n,
# # # # #                         "missing_supplier": cn, "unique_suppliers": us, "risk": snr["risk"],
# # # # #                     }
# # # # #                     interp = interpret_chart(
# # # # #                         st.session_state.azure_client, AZURE_DEPLOYMENT,
# # # # #                         "BOM Risk Propagation Map", bom_ctx,
# # # # #                         "What are the key supply chain risks in this BOM and what should procurement prioritise?",
# # # # #                     )
# # # # #                 st.markdown(
# # # # #                     f"<div class='ic' style='margin-top:8px;'><div class='il'>◈ ARIA</div>"
# # # # #                     f"<div class='ib'>{interp}</div></div>",
# # # # #                     unsafe_allow_html=True,
# # # # #                 )

# # # # #     # ── Component Detail ──────────────────────────────────────────────────────
# # # # #     with comp_tab:
# # # # #         sec("Component Detail")
# # # # #         bom_display2 = []
# # # # #         for _, b in bsn.iterrows():
# # # # #             eff_qty = b.get("Effective Order Qty", b["Comp. Qty (CUn)"])
# # # # #             fq_txt  = ("1 (Fixed)" if b.get("Fixed Qty Flag", False)
# # # # #                        else str(round(float(eff_qty), 3)) if pd.notna(eff_qty) else "—")
# # # # #             bom_display2.append({
# # # # #                 "Material":    str(b["Material"]),
# # # # #                 "Description": str(b["Material Description"])[:36] if pd.notna(b["Material Description"]) else "—",
# # # # #                 "Level":       str(b["Level"])[:25] if pd.notna(b["Level"]) else "—",
# # # # #                 "Qty":         fq_txt,
# # # # #                 "Unit":        str(b["Component unit"]) if pd.notna(b["Component unit"]) else "—",
# # # # #                 "Type":        b.get("Procurement Label", "—"),
# # # # #                 "Supplier":    b.get("Supplier Display", "—"),
# # # # #                 "Location":    b.get("Supplier Location", "—"),
# # # # #                 "Transit":     f"{b.get('Transit Days', '—')}d" if b.get("Transit Days") is not None else "—",
# # # # #                 "Std Price":   f"${b.get('Standard Price', 0):.2f}" if pd.notna(b.get('Standard Price')) else "—",
# # # # #             })
# # # # #         df_bd2  = pd.DataFrame(bom_display2)
# # # # #         sup_r3  = JsCode("""class R{init(p){const v=p.value||'';this.e=document.createElement('span');if(v.startsWith('⚠')){this.e.style.cssText='background:#FEF3C7;color:#F59E0B;padding:2px 6px;border-radius:4px;font-size:10px;font-weight:600;';this.e.innerText=v;}else if(v==='Revvity Inhouse'){this.e.style.cssText='background:#DCFCE7;color:#16a34a;padding:2px 6px;border-radius:4px;font-size:10px;font-weight:600;';this.e.innerText='🏭 '+v;}else{this.e.style.cssText='background:#EFF6FF;color:#2563EB;padding:2px 6px;border-radius:4px;font-size:10px;';this.e.innerText='🚚 '+v;};}getGui(){return this.e;}}""")
# # # # #         gb4     = GridOptionsBuilder.from_dataframe(df_bd2)
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
# # # # #         AgGrid(df_bd2, gridOptions=gb4.build(), height=320,
# # # # #                allow_unsafe_jscode=True, theme="alpine", custom_css=_AGGRID_CSS)

# # # # #     # ── Risk Cascade (unchanged) ─────────────────────────────────────────────
# # # # #     with risk_tab:
# # # # #         sec("Risk Cascade Analysis")
# # # # #         risks = []
# # # # #         if snr["risk"] in ["CRITICAL", "WARNING"]:
# # # # #             risks.append({
# # # # #                 "icon": "⛔", "sev": 3, "color": "#EF4444", "bg": "#FEF2F2",
# # # # #                 "title": f"Finished Good at {snr['risk'].title()} Risk",
# # # # #                 "detail": (f"{snr['name']} has {round(snr['days_cover'])}d of cover. "
# # # # #                            f"SIH={round(snr['sih'])} vs SAP SS={round(snr['safety_stock'])}. "
# # # # #                            f"Production continuity at risk."),
# # # # #                 "action": f"Order {int(snr.get('repl_quantity', 0))} units immediately. Contact procurement today.",
# # # # #             })
# # # # #         if cn > 0:
# # # # #             risks.append({
# # # # #                 "icon": "⚠", "sev": 2, "color": "#F59E0B", "bg": "#FFFBEB",
# # # # #                 "title": f"Missing Supplier Data — {cn} External Components",
# # # # #                 "detail": (f"{cn} of {external_n} external components have no named supplier. "
# # # # #                            f"Single-source risk cannot be assessed for these."),
# # # # #                 "action": "Procurement to verify and update BOM with supplier names and lead times.",
# # # # #             })
# # # # #         if 0 < us <= 2:
# # # # #             risks.append({
# # # # #                 "icon": "⚠", "sev": 2, "color": "#F59E0B", "bg": "#FFFBEB",
# # # # #                 "title": f"Supplier Concentration — {us} Unique Supplier(s)",
# # # # #                 "detail": f"High dependency on {us} supplier(s). Any disruption cascades to multiple components simultaneously.",
# # # # #                 "action": "Evaluate dual-sourcing for critical external components.",
# # # # #             })
# # # # #         ext_comps = bsn[bsn["Procurement type"] == "F"]
# # # # #         if len(ext_comps) > 0:
# # # # #             locs = list(set([str(r) for r in bsn[bsn["Procurement type"] == "F"]["Supplier Location"].dropna().tolist()[:4]]))
# # # # #             risks.append({
# # # # #                 "icon": "🌍", "sev": 1, "color": "#3B82F6", "bg": "#EFF6FF",
# # # # #                 "title": f"External Procurement: {len(ext_comps)} Components",
# # # # #                 "detail": (f"External components depend on supplier availability and transit times. "
# # # # #                            f"Suppliers located in: {', '.join(locs)}."),
# # # # #                 "action": "Review external component lead times — stock buffers for long-transit items.",
# # # # #             })

# # # # #         if not risks:
# # # # #             st.markdown(
# # # # #                 "<div style='padding:10px 13px;background:var(--gbg);border:1px solid rgba(34,197,94,0.2);"
# # # # #                 "border-radius:var(--r);font-size:12px;color:#14532d;'>"
# # # # #                 "✓ No critical propagation risks identified.</div>",
# # # # #                 unsafe_allow_html=True,
# # # # #             )
# # # # #         else:
# # # # #             for r in sorted(risks, key=lambda x: -x["sev"]):
# # # # #                 st.markdown(
# # # # #                     f"<div style='background:{r['bg']};border:1px solid {r['color']}40;"
# # # # #                     f"border-left:4px solid {r['color']};border-radius:var(--r);"
# # # # #                     f"padding:12px 14px;margin-bottom:8px;'>"
# # # # #                     f"<div style='display:flex;align-items:center;gap:8px;margin-bottom:5px;'>"
# # # # #                     f"<span style='font-size:16px;'>{r['icon']}</span>"
# # # # #                     f"<div style='font-size:12px;font-weight:800;color:{r['color']};'>{r['title']}</div>"
# # # # #                     f"</div>"
# # # # #                     f"<div style='font-size:11px;color:var(--t2);margin-bottom:5px;'>{r['detail']}</div>"
# # # # #                     f"<div style='font-size:11px;color:{r['color']};font-weight:600;'>→ {r['action']}</div>"
# # # # #                     f"</div>",
# # # # #                     unsafe_allow_html=True,
# # # # #                 )

# # # # #         # Consolidation opportunities
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
# # # # #                     f"<div style='font-size:10px;color:var(--t3);'>{r2['city']} · {r2['email']}</div>"
# # # # #                     f"<div style='font-size:10px;color:var(--t2);margin-top:2px;'>Also supplies: {', '.join(others[:3])}</div>"
# # # # #                     f"</div>"
# # # # #                     f"<div style='font-size:10px;font-weight:700;color:var(--or);'>⚡ Consolidate order</div>"
# # # # #                     f"</div>",
# # # # #                     unsafe_allow_html=True,
# # # # #                 )

# # # # #         # ── Ask ARIA with rich BOM context (including Standard Price) ─────────
# # # # #         if st.session_state.azure_client:
# # # # #             sec("Ask ARIA About This Network")
# # # # #             st.info("ℹ️ This assistant provides supplier‑related insights only for the currently selected finished good.")
# # # # #             uq = st.text_input(
# # # # #                 "Question",
# # # # #                 placeholder="e.g. Which supplier provides more than 1 material for DELFIA Wash Concentrate?",
# # # # #                 key="snq", label_visibility="collapsed",
# # # # #             )
# # # # #             if uq and st.button("Ask ARIA", key="sna"):
# # # # #                 bom_lines = []
# # # # #                 for _, row in bsn.iterrows():
# # # # #                     mat_desc = str(row["Material Description"])[:40] if pd.notna(row["Material Description"]) else str(row["Material"])
# # # # #                     qty = row["Effective Order Qty"] if "Effective Order Qty" in row else row["Comp. Qty (CUn)"]
# # # # #                     fixed = "X (order exactly 1)" if row.get("Fixed Qty Flag") else ""
# # # # #                     sup = row.get("Supplier Display", "—")
# # # # #                     loc = row.get("Supplier Location", "—")
# # # # #                     transit = row.get("Transit Days", "—")
# # # # #                     reliability = row.get("Supplier Reliability", "—")
# # # # #                     std_price = row.get("Standard Price", "—")
# # # # #                     if pd.notna(std_price):
# # # # #                         std_price = f"${std_price:.2f}"
# # # # #                     bom_lines.append(f"- Component: {mat_desc} | Qty: {qty} {fixed} | Std Price: {std_price} | Supplier: {sup} | Location: {loc} | Transit: {transit}d | Reliability: {reliability}")
# # # # #                 bom_table = "\n".join(bom_lines)

# # # # #                 ctx3 = (
# # # # #                     f"Material: {snr['name']} (ID: {snid})\n"
# # # # #                     f"Risk: {snr['risk']}\n"
# # # # #                     f"Total components: {tc}\n"
# # # # #                     f"Inhouse components: {inhouse_n}\n"
# # # # #                     f"External components: {external_n}\n"
# # # # #                     f"Missing supplier data: {cn} components\n"
# # # # #                     f"Unique external suppliers: {us}\n"
# # # # #                     f"BOM details:\n{bom_table}"
# # # # #                 )
# # # # #                 with st.spinner("Thinking…"):
# # # # #                     ans = chat_with_data(st.session_state.azure_client, AZURE_DEPLOYMENT, uq, ctx3)
# # # # #                 st.markdown(
# # # # #                     f"<div class='ic' style='margin-top:8px;'><div class='il'>◈ ARIA</div>"
# # # # #                     f"<div class='ib'>{ans}</div></div>",
# # # # #                     unsafe_allow_html=True,
# # # # #                 )

# # # # #     st.markdown('<div class="pfooter">🕸️ Powered by <strong>MResult</strong></div>', unsafe_allow_html=True)

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

# # # #     # ── BOM Map – Sankey diagram with clean legend ──────────────────────────────
# # # #     with sn_tab:
# # # #         sec("BOM Propagation Map")
# # # #         # Clean legend using HTML list inside note box
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
# # # #         Hover over nodes for details.
# # # #         </div>
# # # #         """, unsafe_allow_html=True)

# # # #         # Build node list and links for Sankey
# # # #         nodes = []
# # # #         node_colors = []
# # # #         node_map = {}

# # # #         # Root node (finished good)
# # # #         root_name = snr["name"]
# # # #         risk_color_map = {"CRITICAL": "#EF4444", "WARNING": "#F59E0B", "HEALTHY": "#22C55E"}
# # # #         root_color = risk_color_map.get(snr["risk"], "#94A3B8")
# # # #         nodes.append(root_name)
# # # #         node_colors.append(root_color)
# # # #         node_map[root_name] = 0

# # # #         sources = []
# # # #         targets = []
# # # #         values = []

# # # #         # Process each BOM row
# # # #         for _, row in bsn.iterrows():
# # # #             # Component label (truncated for readability)
# # # #             comp_desc = str(row["Material Description"])[:30] if pd.notna(row["Material Description"]) else str(row["Material"])
# # # #             comp_label = f"{comp_desc}"
# # # #             sup_display = row.get("Supplier Display", "—")
# # # #             proc_type = str(row.get("Procurement type", "")).strip()
# # # #             # Get quantity, default to 1
# # # #             qty_raw = row.get("Effective Order Qty", row["Comp. Qty (CUn)"])
# # # #             try:
# # # #                 qty = float(qty_raw) if pd.notna(qty_raw) else 1.0
# # # #             except:
# # # #                 qty = 1.0

# # # #             # Add component node if new
# # # #             if comp_label not in node_map:
# # # #                 # Determine colour
# # # #                 if proc_type == "E":
# # # #                     comp_color = "#22C55E"   # inhouse
# # # #                 elif sup_display.startswith("⚠"):
# # # #                     comp_color = "#F59E0B"   # missing supplier
# # # #                 else:
# # # #                     comp_color = "#3B82F6"   # external named
# # # #                 nodes.append(comp_label)
# # # #                 node_colors.append(comp_color)
# # # #                 node_map[comp_label] = len(nodes) - 1

# # # #             # Link root -> component
# # # #             sources.append(node_map[root_name])
# # # #             targets.append(node_map[comp_label])
# # # #             values.append(qty)

# # # #             # Add supplier node if external and named
# # # #             if sup_display not in ["Revvity Inhouse", "—"] and not sup_display.startswith("⚠"):
# # # #                 sup_label = sup_display[:25]
# # # #                 if sup_label not in node_map:
# # # #                     nodes.append(sup_label)
# # # #                     node_colors.append("#8B5CF6")  # purple
# # # #                     node_map[sup_label] = len(nodes) - 1
# # # #                 # Link component -> supplier
# # # #                 sources.append(node_map[comp_label])
# # # #                 targets.append(node_map[sup_label])
# # # #                 values.append(1.0)

# # # #         # Build Sankey figure
# # # #         fig = go.Figure(data=[go.Sankey(
# # # #             arrangement="snap",
# # # #             node=dict(
# # # #                 pad=15,
# # # #                 thickness=20,
# # # #                 line=dict(color="white", width=0.5),
# # # #                 label=nodes,
# # # #                 color=node_colors,
# # # #                 hovertemplate="<b>%{label}</b><extra></extra>"
# # # #             ),
# # # #             link=dict(
# # # #                 source=sources,
# # # #                 target=targets,
# # # #                 value=values,
# # # #                 color="rgba(160,160,160,0.4)"
# # # #             )
# # # #         )])
# # # #         fig.update_layout(
# # # #             title=None,
# # # #             font=dict(size=10, family="Inter", color="#1E293B"),
# # # #             height=500,
# # # #             margin=dict(l=10, r=10, t=10, b=10),
# # # #             paper_bgcolor="white",
# # # #             plot_bgcolor="white"
# # # #         )
# # # #         st.plotly_chart(fig, use_container_width=True)

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

# # # #     # ── Risk Cascade ──────────────────────────────────────────────────────────
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

# # # #         # ── Ask ARIA with rich BOM context (including Standard Price) ─────────
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

# # # """
# # # tabs/supply_network.py
# # # Supply Network tab: BOM propagation map (Sankey diagram), component detail table,
# # # risk cascade analysis, and supplier consolidation opportunities.

# # # FIXES (Sankey):
# # #   1. Node keys now use material/supplier IDs, not truncated labels → no collisions
# # #   2. qty is clamped to 0.01 minimum → Sankey never drops zero-value links silently
# # #   3. Supplier→component links use actual qty, not hardcoded 1.0 → flow conserved
# # #   4. customdata + hovertemplate added → clean hover tooltips
# # #   5. sup_display null/empty guard added → no KeyError / ⚠ false-positives
# # # """

# # # import streamlit as st
# # # import pandas as pd
# # # import plotly.graph_objects as go

# # # from st_aggrid import AgGrid, GridOptionsBuilder, JsCode

# # # from utils.helpers import sec, note, sbadge, ORANGE, AZURE_DEPLOYMENT
# # # from data_loader import get_bom_components, get_supplier_consolidation
# # # from agent import interpret_chart, chat_with_data

# # # _AGGRID_CSS = {
# # #     ".ag-root-wrapper": {"border": "1px solid #E2E8F0!important", "border-radius": "12px!important"},
# # #     ".ag-header":       {"background": "#F8FAFE!important"},
# # #     ".ag-row-even":     {"background": "#FFFFFF!important"},
# # #     ".ag-row-odd":      {"background": "#F8FAFE!important"},
# # # }


# # # def render():
# # #     data            = st.session_state.data
# # #     summary         = st.session_state.summary
# # #     MATERIAL_LABELS = st.session_state.material_labels

# # #     st.markdown(
# # #         "<div style='font-size:15px;font-weight:800;margin-bottom:4px;'>Supply Network</div>"
# # #         "<div style='font-size:12px;color:var(--t3);margin-bottom:14px;'>"
# # #         "BOM structure · Supplier locations · Risk cascade · Consolidation intelligence</div>",
# # #         unsafe_allow_html=True,
# # #     )

# # #     snn  = st.selectbox("Finished Good", [r["name"] for _, r in summary.iterrows()], key="snm")
# # #     snid = summary[summary.name == snn]["material"].values[0]
# # #     snr  = summary[summary.material == snid].iloc[0]
# # #     bsn  = get_bom_components(data, snid)

# # #     if not len(bsn):
# # #         st.markdown(
# # #             "<div class='flag-box'><div style='font-size:22px;margin-bottom:8px;'>🕸️</div>"
# # #             "<div style='font-size:14px;font-weight:800;color:var(--t2);'>No BOM data for this material</div></div>",
# # #             unsafe_allow_html=True,
# # #         )
# # #         return

# # #     cw        = int(bsn["Supplier Name(Vendor)"].notna().sum())
# # #     cn        = len(bsn[bsn["Supplier Display"].str.startswith("⚠", na=False)])
# # #     us        = int(bsn["Supplier Name(Vendor)"].dropna().nunique())
# # #     tc        = len(bsn)
# # #     inhouse_n = int((bsn["Procurement type"] == "E").sum())
# # #     external_n = int((bsn["Procurement type"] == "F").sum())

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

# # #     sn_tab, comp_tab, risk_tab = st.tabs(["🕸️  BOM Map", "📋  Components", "⚠️  Risk Analysis"])

# # #     # ── BOM Map – Sankey diagram ─────────────────────────────────────────────
# # #     with sn_tab:
# # #         sec("BOM Propagation Map")
# # #         st.markdown("""
# # #         <div class='note-box'>
# # #         <strong>Colour legend:</strong>
# # #         <ul style='margin:5px 0 0 20px; padding-left:0;'>
# # #         <li>🔵 <strong>Blue</strong> = External component with named supplier</li>
# # #         <li>🟢 <strong>Green</strong> = Inhouse component (Revvity)</li>
# # #         <li>🟡 <strong>Amber</strong> = External component with <strong>missing supplier data</strong></li>
# # #         <li>🟣 <strong>Purple</strong> = Supplier node</li>
# # #         <li>Root node colour matches finished good risk (🔴 Critical / 🟠 Warning / 🟢 Healthy)</li>
# # #         </ul>
# # #         Hover over nodes for details.
# # #         </div>
# # #         """, unsafe_allow_html=True)

# # #         # ── Node/link builders ────────────────────────────────────────────────
# # #         risk_color_map = {"CRITICAL": "#EF4444", "WARNING": "#F59E0B", "HEALTHY": "#22C55E"}

# # #         nodes        = []   # display labels
# # #         node_colors  = []
# # #         node_custom  = []   # shown in hovertemplate
# # #         node_map     = {}   # stable key → index  (FIX 1: key ≠ label)

# # #         def _add_node(key: str, label: str, color: str, custom: str) -> int:
# # #             """Add node only if key is new; always return its index."""
# # #             if key not in node_map:
# # #                 node_map[key] = len(nodes)
# # #                 nodes.append(label)
# # #                 node_colors.append(color)
# # #                 node_custom.append(custom)
# # #             return node_map[key]

# # #         sources, targets, values, link_labels = [], [], [], []

# # #         # Root (finished good)
# # #         root_key   = f"FG_{snid}"
# # #         root_color = risk_color_map.get(snr["risk"], "#94A3B8")
# # #         root_idx   = _add_node(
# # #             root_key,
# # #             snr["name"][:40],
# # #             root_color,
# # #             f"{snr['name']} | Risk: {snr['risk']} | Cover: {round(snr['days_cover'])}d",
# # #         )

# # #         for _, row in bsn.iterrows():
# # #             mat_id     = str(row["Material"])
# # #             comp_desc  = (str(row["Material Description"])[:30]
# # #                           if pd.notna(row["Material Description"]) else mat_id)

# # #             # FIX 1: key uses stable mat_id; label uses human description
# # #             comp_key   = f"COMP_{mat_id}"
# # #             comp_label = comp_desc

# # #             sup_display = str(row.get("Supplier Display") or "—").strip()
# # #             proc_type   = str(row.get("Procurement type") or "").strip()

# # #             # FIX 2: clamp qty to avoid zero/NaN links being silently dropped
# # #             qty_raw = row.get("Effective Order Qty", row.get("Comp. Qty (CUn)", 1.0))
# # #             try:
# # #                 qty = float(qty_raw) if pd.notna(qty_raw) else 1.0
# # #             except Exception:
# # #                 qty = 1.0
# # #             qty = max(qty, 0.01)

# # #             # Component colour + hover text
# # #             if proc_type == "E":
# # #                 comp_color  = "#22C55E"
# # #                 comp_custom = f"{comp_desc} | Inhouse (Revvity) | Qty: {qty}"
# # #             elif sup_display.startswith("⚠") or sup_display in ("—", ""):
# # #                 comp_color  = "#F59E0B"
# # #                 comp_custom = f"{comp_desc} | ⚠ Missing Supplier | Qty: {qty}"
# # #             else:
# # #                 comp_color  = "#3B82F6"
# # #                 transit     = row.get("Transit Days", "—")
# # #                 comp_custom = (f"{comp_desc} | Supplier: {sup_display} "
# # #                                f"| Qty: {qty} | Transit: {transit}d")

# # #             comp_idx = _add_node(comp_key, comp_label, comp_color, comp_custom)

# # #             # Root → Component link
# # #             sources.append(root_idx)
# # #             targets.append(comp_idx)
# # #             values.append(qty)
# # #             link_labels.append(f"{comp_desc}: qty {qty}")

# # #             # Component → Supplier link (only for external, named suppliers)
# # #             # FIX 3: use actual qty (not hardcoded 1.0) so flow is conserved
# # #             is_named_external = (
# # #                 proc_type == "F"
# # #                 and sup_display not in ("—", "", "Revvity Inhouse")
# # #                 and not sup_display.startswith("⚠")
# # #             )
# # #             if is_named_external:
# # #                 sup_key   = f"SUP_{sup_display}"
# # #                 sup_label = sup_display[:28]
# # #                 loc       = str(row.get("Supplier Location") or "—")
# # #                 rel       = row.get("Supplier Reliability", "—")
# # #                 sup_custom = f"Supplier: {sup_display} | Location: {loc} | Reliability: {rel}"

# # #                 sup_idx = _add_node(sup_key, sup_label, "#8B5CF6", sup_custom)

# # #                 sources.append(comp_idx)
# # #                 targets.append(sup_idx)
# # #                 values.append(qty)                          # FIX 3
# # #                 link_labels.append(f"{comp_desc} → {sup_label}")

# # #         # ── Build figure ──────────────────────────────────────────────────────
# # #         fig = go.Figure(data=[go.Sankey(
# # #             arrangement="snap",
# # #             node=dict(
# # #                 pad=18,
# # #                 thickness=22,
# # #                 line=dict(color="white", width=0.8),
# # #                 label=nodes,
# # #                 color=node_colors,
# # #                 # FIX 4: customdata drives the hovertemplate
# # #                 customdata=node_custom,
# # #                 hovertemplate="<b>%{customdata}</b><extra></extra>",
# # #             ),
# # #             link=dict(
# # #                 source=sources,
# # #                 target=targets,
# # #                 value=values,
# # #                 label=link_labels,
# # #                 color="rgba(160,160,160,0.35)",
# # #                 hovertemplate=(
# # #                     "<b>%{label}</b><br>"
# # #                     "Flow value: %{value:.2f}<extra></extra>"
# # #                 ),
# # #             ),
# # #         )])

# # #         fig.update_layout(
# # #             title=None,
# # #             font=dict(size=10, family="Inter", color="#1E293B"),
# # #             height=520,
# # #             margin=dict(l=10, r=10, t=10, b=10),
# # #             paper_bgcolor="white",
# # #             plot_bgcolor="white",
# # #         )

# # #         st.plotly_chart(fig, use_container_width=True)

# # #         if st.session_state.azure_client:
# # #             if st.button("◈ Interpret BOM Map", key="interp_bom_sankey"):
# # #                 with st.spinner("ARIA interpreting…"):
# # #                     bom_ctx = {
# # #                         "material": snr["name"], "total_components": tc,
# # #                         "inhouse": inhouse_n, "external_named": cw - inhouse_n,
# # #                         "missing_supplier": cn, "unique_suppliers": us, "risk": snr["risk"],
# # #                     }
# # #                     interp = interpret_chart(
# # #                         st.session_state.azure_client, AZURE_DEPLOYMENT,
# # #                         "BOM Risk Propagation Map", bom_ctx,
# # #                         "What are the key supply chain risks in this BOM and what should procurement prioritise?",
# # #                     )
# # #                 st.markdown(
# # #                     f"<div class='ic' style='margin-top:8px;'><div class='il'>◈ ARIA</div>"
# # #                     f"<div class='ib'>{interp}</div></div>",
# # #                     unsafe_allow_html=True,
# # #                 )

# # #     # ── Component Detail ──────────────────────────────────────────────────────
# # #     with comp_tab:
# # #         sec("Component Detail")
# # #         bom_display2 = []
# # #         for _, b in bsn.iterrows():
# # #             eff_qty = b.get("Effective Order Qty", b["Comp. Qty (CUn)"])
# # #             fq_txt  = ("1 (Fixed)" if b.get("Fixed Qty Flag", False)
# # #                        else str(round(float(eff_qty), 3)) if pd.notna(eff_qty) else "—")
# # #             bom_display2.append({
# # #                 "Material":    str(b["Material"]),
# # #                 "Description": str(b["Material Description"])[:36] if pd.notna(b["Material Description"]) else "—",
# # #                 "Level":       str(b["Level"])[:25] if pd.notna(b["Level"]) else "—",
# # #                 "Qty":         fq_txt,
# # #                 "Unit":        str(b["Component unit"]) if pd.notna(b["Component unit"]) else "—",
# # #                 "Type":        b.get("Procurement Label", "—"),
# # #                 "Supplier":    b.get("Supplier Display", "—"),
# # #                 "Location":    b.get("Supplier Location", "—"),
# # #                 "Transit":     f"{b.get('Transit Days', '—')}d" if b.get("Transit Days") is not None else "—",
# # #                 "Std Price":   f"${b.get('Standard Price', 0):.2f}" if pd.notna(b.get('Standard Price')) else "—",
# # #             })
# # #         df_bd2  = pd.DataFrame(bom_display2)
# # #         sup_r3  = JsCode("""class R{init(p){const v=p.value||'';this.e=document.createElement('span');if(v.startsWith('⚠')){this.e.style.cssText='background:#FEF3C7;color:#F59E0B;padding:2px 6px;border-radius:4px;font-size:10px;font-weight:600;';this.e.innerText=v;}else if(v==='Revvity Inhouse'){this.e.style.cssText='background:#DCFCE7;color:#16a34a;padding:2px 6px;border-radius:4px;font-size:10px;font-weight:600;';this.e.innerText='🏭 '+v;}else{this.e.style.cssText='background:#EFF6FF;color:#2563EB;padding:2px 6px;border-radius:4px;font-size:10px;';this.e.innerText='🚚 '+v;};}getGui(){return this.e;}}""")
# # #         gb4     = GridOptionsBuilder.from_dataframe(df_bd2)
# # #         gb4.configure_column("Material",    width=82)
# # #         gb4.configure_column("Description", width=215)
# # #         gb4.configure_column("Level",       width=85)
# # #         gb4.configure_column("Qty",         width=75)
# # #         gb4.configure_column("Unit",        width=50)
# # #         gb4.configure_column("Type",        width=100)
# # #         gb4.configure_column("Supplier",    width=170, cellRenderer=sup_r3)
# # #         gb4.configure_column("Location",    width=130)
# # #         gb4.configure_column("Transit",     width=58)
# # #         gb4.configure_column("Std Price",   width=80)
# # #         gb4.configure_grid_options(rowHeight=36, headerHeight=32)
# # #         gb4.configure_default_column(resizable=True, sortable=True, filter=False)
# # #         AgGrid(df_bd2, gridOptions=gb4.build(), height=320,
# # #                allow_unsafe_jscode=True, theme="alpine", custom_css=_AGGRID_CSS)

# # #     # ── Risk Cascade ──────────────────────────────────────────────────────────
# # #     with risk_tab:
# # #         sec("Risk Cascade Analysis")
# # #         risks = []
# # #         if snr["risk"] in ["CRITICAL", "WARNING"]:
# # #             risks.append({
# # #                 "icon": "⛔", "sev": 3, "color": "#EF4444", "bg": "#FEF2F2",
# # #                 "title": f"Finished Good at {snr['risk'].title()} Risk",
# # #                 "detail": (f"{snr['name']} has {round(snr['days_cover'])}d of cover. "
# # #                            f"SIH={round(snr['sih'])} vs SAP SS={round(snr['safety_stock'])}. "
# # #                            f"Production continuity at risk."),
# # #                 "action": f"Order {int(snr.get('repl_quantity', 0))} units immediately. Contact procurement today.",
# # #             })
# # #         if cn > 0:
# # #             risks.append({
# # #                 "icon": "⚠", "sev": 2, "color": "#F59E0B", "bg": "#FFFBEB",
# # #                 "title": f"Missing Supplier Data — {cn} External Components",
# # #                 "detail": (f"{cn} of {external_n} external components have no named supplier. "
# # #                            f"Single-source risk cannot be assessed for these."),
# # #                 "action": "Procurement to verify and update BOM with supplier names and lead times.",
# # #             })
# # #         if 0 < us <= 2:
# # #             risks.append({
# # #                 "icon": "⚠", "sev": 2, "color": "#F59E0B", "bg": "#FFFBEB",
# # #                 "title": f"Supplier Concentration — {us} Unique Supplier(s)",
# # #                 "detail": f"High dependency on {us} supplier(s). Any disruption cascades to multiple components simultaneously.",
# # #                 "action": "Evaluate dual-sourcing for critical external components.",
# # #             })
# # #         ext_comps = bsn[bsn["Procurement type"] == "F"]
# # #         if len(ext_comps) > 0:
# # #             locs = list(set([str(r) for r in bsn[bsn["Procurement type"] == "F"]["Supplier Location"].dropna().tolist()[:4]]))
# # #             risks.append({
# # #                 "icon": "🌍", "sev": 1, "color": "#3B82F6", "bg": "#EFF6FF",
# # #                 "title": f"External Procurement: {len(ext_comps)} Components",
# # #                 "detail": (f"External components depend on supplier availability and transit times. "
# # #                            f"Suppliers located in: {', '.join(locs)}."),
# # #                 "action": "Review external component lead times — stock buffers for long-transit items.",
# # #             })

# # #         if not risks:
# # #             st.markdown(
# # #                 "<div style='padding:10px 13px;background:var(--gbg);border:1px solid rgba(34,197,94,0.2);"
# # #                 "border-radius:var(--r);font-size:12px;color:#14532d;'>"
# # #                 "✓ No critical propagation risks identified.</div>",
# # #                 unsafe_allow_html=True,
# # #             )
# # #         else:
# # #             for r in sorted(risks, key=lambda x: -x["sev"]):
# # #                 st.markdown(
# # #                     f"<div style='background:{r['bg']};border:1px solid {r['color']}40;"
# # #                     f"border-left:4px solid {r['color']};border-radius:var(--r);"
# # #                     f"padding:12px 14px;margin-bottom:8px;'>"
# # #                     f"<div style='display:flex;align-items:center;gap:8px;margin-bottom:5px;'>"
# # #                     f"<span style='font-size:16px;'>{r['icon']}</span>"
# # #                     f"<div style='font-size:12px;font-weight:800;color:{r['color']};'>{r['title']}</div>"
# # #                     f"</div>"
# # #                     f"<div style='font-size:11px;color:var(--t2);margin-bottom:5px;'>{r['detail']}</div>"
# # #                     f"<div style='font-size:11px;color:{r['color']};font-weight:600;'>→ {r['action']}</div>"
# # #                     f"</div>",
# # #                     unsafe_allow_html=True,
# # #                 )

# # #         # Consolidation opportunities
# # #         consol2   = get_supplier_consolidation(data, summary)
# # #         relevant2 = consol2[
# # #             consol2.material_list.apply(lambda x: snid in x)
# # #             & (consol2.finished_goods_supplied > 1)
# # #             & consol2.consolidation_opportunity
# # #         ]
# # #         if len(relevant2) > 0:
# # #             sec("Supplier Consolidation Opportunities")
# # #             for _, r2 in relevant2.iterrows():
# # #                 others = [MATERIAL_LABELS.get(m, m)[:18] for m in r2["material_list"] if m != snid]
# # #                 st.markdown(
# # #                     f"<div class='prow'><div style='font-size:14px;'>🏭</div>"
# # #                     f"<div style='flex:1;'>"
# # #                     f"<div style='font-size:12px;font-weight:800;'>{r2['supplier']}</div>"
# # #                     f"<div style='font-size:10px;color:var(--t3);'>{r2['city']} · {r2['email']}</div>"
# # #                     f"<div style='font-size:10px;color:var(--t2);margin-top:2px;'>Also supplies: {', '.join(others[:3])}</div>"
# # #                     f"</div>"
# # #                     f"<div style='font-size:10px;font-weight:700;color:var(--or);'>⚡ Consolidate order</div>"
# # #                     f"</div>",
# # #                     unsafe_allow_html=True,
# # #                 )

# # #         # ── Ask ARIA ──────────────────────────────────────────────────────────
# # #         if st.session_state.azure_client:
# # #             sec("Ask ARIA About This Network")
# # #             st.info("ℹ️ This assistant provides supplier‑related insights only for the currently selected finished good.")
# # #             uq = st.text_input(
# # #                 "Question",
# # #                 placeholder="e.g. Which supplier provides more than 1 material for DELFIA Wash Concentrate?",
# # #                 key="snq", label_visibility="collapsed",
# # #             )
# # #             if uq and st.button("Ask ARIA", key="sna"):
# # #                 bom_lines = []
# # #                 for _, row in bsn.iterrows():
# # #                     mat_desc = str(row["Material Description"])[:40] if pd.notna(row["Material Description"]) else str(row["Material"])
# # #                     qty = row["Effective Order Qty"] if "Effective Order Qty" in row else row["Comp. Qty (CUn)"]
# # #                     fixed = "X (order exactly 1)" if row.get("Fixed Qty Flag") else ""
# # #                     sup = row.get("Supplier Display", "—")
# # #                     loc = row.get("Supplier Location", "—")
# # #                     transit = row.get("Transit Days", "—")
# # #                     reliability = row.get("Supplier Reliability", "—")
# # #                     std_price = row.get("Standard Price", "—")
# # #                     if pd.notna(std_price):
# # #                         std_price = f"${std_price:.2f}"
# # #                     bom_lines.append(
# # #                         f"- Component: {mat_desc} | Qty: {qty} {fixed} | Std Price: {std_price} "
# # #                         f"| Supplier: {sup} | Location: {loc} | Transit: {transit}d | Reliability: {reliability}"
# # #                     )
# # #                 bom_table = "\n".join(bom_lines)
# # #                 ctx3 = (
# # #                     f"Material: {snr['name']} (ID: {snid})\n"
# # #                     f"Risk: {snr['risk']}\n"
# # #                     f"Total components: {tc}\n"
# # #                     f"Inhouse components: {inhouse_n}\n"
# # #                     f"External components: {external_n}\n"
# # #                     f"Missing supplier data: {cn} components\n"
# # #                     f"Unique external suppliers: {us}\n"
# # #                     f"BOM details:\n{bom_table}"
# # #                 )
# # #                 with st.spinner("Thinking…"):
# # #                     ans = chat_with_data(st.session_state.azure_client, AZURE_DEPLOYMENT, uq, ctx3)
# # #                 st.markdown(
# # #                     f"<div class='ic' style='margin-top:8px;'><div class='il'>◈ ARIA</div>"
# # #                     f"<div class='ib'>{ans}</div></div>",
# # #                     unsafe_allow_html=True,
# # #                 )

# # #     st.markdown('<div class="pfooter">🕸️ Powered by <strong>MResult</strong></div>', unsafe_allow_html=True)
