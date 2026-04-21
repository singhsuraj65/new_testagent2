# # # # """
# # # # tabs/supply_network.py
# # # # Supply Network tab: BOM propagation map, component detail table,
# # # # risk cascade analysis, and supplier consolidation opportunities.
# # # # """

# # # # import streamlit as st
# # # # import pandas as pd

# # # # from st_aggrid import AgGrid, GridOptionsBuilder, JsCode

# # # # from utils.helpers import sec, note, sbadge, plot_bom_tree, ORANGE, AZURE_DEPLOYMENT
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

# # # #     # ── BOM Map ───────────────────────────────────────────────────────────────
# # # #     with sn_tab:
# # # #         sec("BOM Propagation Map")
# # # #         note("Blue = External supplier named. Amber = External, no supplier data. "
# # # #              "Green = Revvity Inhouse production. Hover nodes for detail.")
# # # #         risk_color_map = {"CRITICAL": "#EF4444", "WARNING": "#F59E0B", "HEALTHY": "#22C55E"}
# # # #         root_color     = risk_color_map.get(snr["risk"], "#94A3B8")
# # # #         fig_tree       = plot_bom_tree(bsn, snr["name"], root_color)
# # # #         st.plotly_chart(fig_tree, use_container_width=True)

# # # #         if st.session_state.azure_client:
# # # #             if st.button("◈ Interpret BOM Map", key="interp_bom_tree"):
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

# # # #         # Free-form ARIA chat
# # # #         if st.session_state.azure_client:
# # # #             sec("Ask ARIA About This Network")
# # # #             uq = st.text_input(
# # # #                 "Question",
# # # #                 placeholder="e.g. Which supplier poses the highest single-source risk?",
# # # #                 key="snq", label_visibility="collapsed",
# # # #             )
# # # #             if uq and st.button("Ask ARIA", key="sna"):
# # # #                 ctx3 = (
# # # #                     f"Material: {snr['name']}, Risk: {snr['risk']}, Components: {tc}, "
# # # #                     f"Inhouse: {inhouse_n}, External: {external_n}, Missing supplier: {cn}, "
# # # #                     f"Unique suppliers: {us}, "
# # # #                     f"Suppliers: {', '.join(bsn['Supplier Name(Vendor)'].dropna().unique().tolist()[:5])}"
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
# # # Supply Network tab: BOM propagation map (colour-coded by risk/supplier type),
# # # component detail table, risk cascade analysis, and supplier consolidation opportunities.
# # # """

# # # import streamlit as st
# # # import pandas as pd

# # # from st_aggrid import AgGrid, GridOptionsBuilder, JsCode

# # # from utils.helpers import sec, note, sbadge, plot_bom_tree, ORANGE, AZURE_DEPLOYMENT
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
# # #         (n1, tc,        "Total Components",  "#1E293B"),
# # #         (n2, inhouse_n, "Revvity Inhouse",   "#22C55E"),
# # #         (n3, cn,        "Missing Supplier",  "#F59E0B" if cn > 0 else "#1E293B"),
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

# # #     # ── BOM Map (colour‑coded knowledge graph) ─────────────────────────────────
# # #     with sn_tab:
# # #         sec("BOM Propagation Map")
# # #         note("""
# # #         **Colour legend:**  
# # #         - 🟢 **Green** = Inhouse component (Revvity)  
# # #         - 🔵 **Blue** = External component with named supplier  
# # #         - 🟡 **Amber** = External component with **missing supplier data**  
# # #         - 🟣 **Purple** = Supplier node  
# # #         - Root node colour matches finished good risk (🔴 Critical / 🟠 Warning / 🟢 Healthy)  
# # #         Hover over any node for details.
# # #         """)
# # #         risk_color_map = {"CRITICAL": "#EF4444", "WARNING": "#F59E0B", "HEALTHY": "#22C55E"}
# # #         root_color     = risk_color_map.get(snr["risk"], "#94A3B8")
# # #         fig_tree       = plot_bom_tree(bsn, snr["name"], root_color)
# # #         st.plotly_chart(fig_tree, use_container_width=True)

# # #         if st.session_state.azure_client:
# # #             if st.button("◈ Interpret BOM Map", key="interp_bom_tree"):
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

# # #         # ── Ask ARIA with rich BOM context ────────────────────────────────────
# # #         if st.session_state.azure_client:
# # #             sec("Ask ARIA About This Network")
# # #             uq = st.text_input(
# # #                 "Question",
# # #                 placeholder="e.g. Which supplier provides more than 1 material for DELFIA Wash Concentrate?",
# # #                 key="snq", label_visibility="collapsed",
# # #             )
# # #             if uq and st.button("Ask ARIA", key="sna"):
# # #                 # Build a detailed BOM table as context
# # #                 bom_lines = []
# # #                 for _, row in bsn.iterrows():
# # #                     mat_desc = str(row["Material Description"])[:40] if pd.notna(row["Material Description"]) else str(row["Material"])
# # #                     qty = row["Effective Order Qty"] if "Effective Order Qty" in row else row["Comp. Qty (CUn)"]
# # #                     fixed = "X (order exactly 1)" if row.get("Fixed Qty Flag") else ""
# # #                     sup = row.get("Supplier Display", "—")
# # #                     loc = row.get("Supplier Location", "—")
# # #                     transit = row.get("Transit Days", "—")
# # #                     reliability = row.get("Supplier Reliability", "—")
# # #                     bom_lines.append(f"- Component: {mat_desc} | Qty: {qty} {fixed} | Supplier: {sup} | Location: {loc} | Transit: {transit}d | Reliability: {reliability}")
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

# #     # ── BOM Map – Sankey diagram (replaces tree) ──────────────────────────────
# #     with sn_tab:
# #         sec("BOM Propagation Map")
# #         note("""
# #         **Colour legend:**  
# #         - 🔵 **Blue** = External component with named supplier  
# #         - 🟢 **Green** = Inhouse component (Revvity)  
# #         - 🟡 **Amber** = External component with **missing supplier data**  
# #         - 🟣 **Purple** = Supplier node  
# #         - Root node colour matches finished good risk (🔴 Critical / 🟠 Warning / 🟢 Healthy)  
# #         Hover over nodes for details.
# #         """)

# #         # Build node list and links for Sankey
# #         nodes = []
# #         node_colors = []
# #         node_map = {}

# #         # Root node (finished good)
# #         root_name = snr["name"]
# #         root_risk_color = {"CRITICAL": "#EF4444", "WARNING": "#F59E0B", "HEALTHY": "#22C55E"}.get(snr["risk"], "#94A3B8")
# #         nodes.append(root_name)
# #         node_colors.append(root_risk_color)
# #         node_map[root_name] = 0

# #         sources = []
# #         targets = []
# #         values = []

# #         # Process each BOM row
# #         for _, row in bsn.iterrows():
# #             comp_desc = str(row["Material Description"])[:40] if pd.notna(row["Material Description"]) else str(row["Material"])
# #             comp_label = f"[C] {comp_desc}"
# #             sup_display = row.get("Supplier Display", "—")
# #             proc_type = str(row.get("Procurement type", "")).strip()
# #             qty = row.get("Effective Order Qty", row["Comp. Qty (CUn)"]) if pd.notna(row.get("Effective Order Qty", row["Comp. Qty (CUn)"]) ) else 1
# #             # Ensure qty is numeric
# #             try:
# #                 qty = float(qty)
# #             except:
# #                 qty = 1.0

# #             # Add component node if not already present
# #             if comp_label not in node_map:
# #                 # Determine component colour
# #                 if proc_type == "E":
# #                     comp_color = "#22C55E"   # Inhouse
# #                 elif sup_display.startswith("⚠"):
# #                     comp_color = "#F59E0B"   # Missing supplier
# #                 else:
# #                     comp_color = "#3B82F6"   # External named
# #                 nodes.append(comp_label)
# #                 node_colors.append(comp_color)
# #                 node_map[comp_label] = len(nodes) - 1

# #             # Link root -> component
# #             sources.append(node_map[root_name])
# #             targets.append(node_map[comp_label])
# #             values.append(qty)

# #             # Add supplier node if external and named
# #             if sup_display not in ["Revvity Inhouse", "—"] and not sup_display.startswith("⚠"):
# #                 sup_label = f"[S] {sup_display[:25]}"
# #                 if sup_label not in node_map:
# #                     nodes.append(sup_label)
# #                     node_colors.append("#8B5CF6")  # Purple for suppliers
# #                     node_map[sup_label] = len(nodes) - 1
# #                 # Link component -> supplier
# #                 sources.append(node_map[comp_label])
# #                 targets.append(node_map[sup_label])
# #                 values.append(1.0)  # connection weight

# #         # Build Sankey figure
# #         fig_sankey = go.Figure(data=[go.Sankey(
# #             arrangement="snap",
# #             node=dict(
# #                 pad=20,
# #                 thickness=20,
# #                 line=dict(color="white", width=0.5),
# #                 label=nodes,
# #                 color=node_colors,
# #                 hovertemplate="<b>%{label}</b><extra></extra>"
# #             ),
# #             link=dict(
# #                 source=sources,
# #                 target=targets,
# #                 value=values,
# #                 color="rgba(200,200,200,0.3)"
# #             )
# #         )])
# #         fig_sankey.update_layout(
# #             title=None,
# #             font=dict(size=11, family="Inter"),
# #             height=500,
# #             margin=dict(l=20, r=20, t=20, b=20),
# #             paper_bgcolor="white",
# #         )
# #         st.plotly_chart(fig_sankey, use_container_width=True)

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
# #             # Add disclaimer
# #             st.info("ℹ️ This assistant provides supplier‑related insights only for the currently selected finished good.")
# #             uq = st.text_input(
# #                 "Question",
# #                 placeholder="e.g. Which supplier provides more than 1 material for DELFIA Wash Concentrate?",
# #                 key="snq", label_visibility="collapsed",
# #             )
# #             if uq and st.button("Ask ARIA", key="sna"):
# #                 # Build a detailed BOM table as context, including Standard Price
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

# """
# tabs/supply_network.py
# Supply Network tab: BOM propagation map (Sankey diagram), component detail table,
# risk cascade analysis, and supplier consolidation opportunities.
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
#         st.markdown(
#             "<div class='flag-box'><div style='font-size:22px;margin-bottom:8px;'>🕸️</div>"
#             "<div style='font-size:14px;font-weight:800;color:var(--t2);'>No BOM data for this material</div></div>",
#             unsafe_allow_html=True,
#         )
#         return

#     cw        = int(bsn["Supplier Name(Vendor)"].notna().sum())
#     cn        = len(bsn[bsn["Supplier Display"].str.startswith("⚠", na=False)])
#     us        = int(bsn["Supplier Name(Vendor)"].dropna().nunique())
#     tc        = len(bsn)
#     inhouse_n = int((bsn["Procurement type"] == "E").sum())
#     external_n = int((bsn["Procurement type"] == "F").sum())

#     n1, n2, n3, n4 = st.columns(4)
#     for col, val, lbl, vc in [
#         (n1, tc,        "Total Components",  "#1E293B"),
#         (n2, inhouse_n, "Revvity Inhouse",   "#22C55E"),
#         (n3, cn,        "Missing Supplier",  "#F59E0B" if cn > 0 else "#1E293B"),
#         (n4, us,        "Unique Ext Suppliers", "#1E293B"),
#     ]:
#         with col:
#             st.markdown(
#                 f"<div class='sc'><div style='flex:1;'>"
#                 f"<div class='sv' style='color:{vc};'>{val}</div>"
#                 f"<div class='sl'>{lbl}</div></div></div>",
#                 unsafe_allow_html=True,
#             )

#     sn_tab, comp_tab, risk_tab = st.tabs(["🕸️  BOM Map", "📋  Components", "⚠️  Risk Analysis"])

#     # ── BOM Map – Sankey diagram with clean legend ──────────────────────────────
#     with sn_tab:
#         sec("BOM Propagation Map")
#         # Fixed legend: HTML list inside a note box (no bold/3D)
#         st.markdown("""
#         <div class='note-box'>
#         <strong>Colour legend:</strong>
#         <ul style='margin:5px 0 0 20px; padding-left:0;'>
#         <li>🔵 <strong>Blue</strong> = External component with named supplier</li>
#         <li>🟢 <strong>Green</strong> = Inhouse component (Revvity)</li>
#         <li>🟡 <strong>Amber</strong> = External component with <strong>missing supplier data</strong></li>
#         <li>🟣 <strong>Purple</strong> = Supplier node</li>
#         <li>Root node colour matches finished good risk (🔴 Critical / 🟠 Warning / 🟢 Healthy)</li>
#         </ul>
#         Hover over nodes for details.
#         </div>
#         """, unsafe_allow_html=True)

#         # Build node list and links for Sankey
#         nodes = []
#         node_colors = []
#         node_map = {}

#         # Root node (finished good)
#         root_name = str(snr["name"])  # ensure string
#         root_risk_color = {"CRITICAL": "#EF4444", "WARNING": "#F59E0B", "HEALTHY": "#22C55E"}.get(snr["risk"], "#94A3B8")
#         nodes.append(root_name)
#         node_colors.append(root_risk_color)
#         node_map[root_name] = 0

#         sources = []
#         targets = []
#         values = []

#         # Process each BOM row
#         for _, row in bsn.iterrows():
#             comp_desc = str(row["Material Description"])[:40] if pd.notna(row["Material Description"]) else str(row["Material"])
#             comp_label = f"[C] {comp_desc}"
#             sup_display = row.get("Supplier Display", "—")
#             proc_type = str(row.get("Procurement type", "")).strip()
#             qty = row.get("Effective Order Qty", row["Comp. Qty (CUn)"]) if pd.notna(row.get("Effective Order Qty", row["Comp. Qty (CUn)"]) ) else 1
#             # Ensure qty is numeric
#             try:
#                 qty = float(qty)
#             except:
#                 qty = 1.0

#             # Add component node if not already present
#             if comp_label not in node_map:
#                 # Determine component colour
#                 if proc_type == "E":
#                     comp_color = "#22C55E"   # Inhouse
#                 elif sup_display.startswith("⚠"):
#                     comp_color = "#F59E0B"   # Missing supplier
#                 else:
#                     comp_color = "#3B82F6"   # External named
#                 nodes.append(comp_label)
#                 node_colors.append(comp_color)
#                 node_map[comp_label] = len(nodes) - 1

#             # Link root -> component
#             sources.append(node_map[root_name])
#             targets.append(node_map[comp_label])
#             values.append(qty)

#             # Add supplier node if external and named
#             if sup_display not in ["Revvity Inhouse", "—"] and not sup_display.startswith("⚠"):
#                 sup_label = f"[S] {str(sup_display)[:25]}"
#                 if sup_label not in node_map:
#                     nodes.append(sup_label)
#                     node_colors.append("#8B5CF6")  # Purple for suppliers
#                     node_map[sup_label] = len(nodes) - 1
#                 # Link component -> supplier
#                 sources.append(node_map[comp_label])
#                 targets.append(node_map[sup_label])
#                 values.append(1.0)  # connection weight

#         # Build Sankey figure with normal font weight
#         fig_sankey = go.Figure(data=[go.Sankey(
#             arrangement="snap",
#             node=dict(
#                 pad=20,
#                 thickness=20,
#                 line=dict(color="white", width=0.5),
#                 label=nodes,
#                 color=node_colors,
#                 hovertemplate="<b>%{label}</b><extra></extra>"
#             ),
#             link=dict(
#                 source=sources,
#                 target=targets,
#                 value=values,
#                 color="rgba(200,200,200,0.3)"
#             )
#         )])
#         fig_sankey.update_layout(
#             title=None,
#             font=dict(size=11, family="Inter", weight="normal"),  # ensure normal font weight
#             height=500,
#             margin=dict(l=20, r=20, t=20, b=20),
#             paper_bgcolor="white",
#         )
#         st.plotly_chart(fig_sankey, use_container_width=True)

#         if st.session_state.azure_client:
#             if st.button("◈ Interpret BOM Map", key="interp_bom_sankey"):
#                 with st.spinner("ARIA interpreting…"):
#                     bom_ctx = {
#                         "material": snr["name"], "total_components": tc,
#                         "inhouse": inhouse_n, "external_named": cw - inhouse_n,
#                         "missing_supplier": cn, "unique_suppliers": us, "risk": snr["risk"],
#                     }
#                     interp = interpret_chart(
#                         st.session_state.azure_client, AZURE_DEPLOYMENT,
#                         "BOM Risk Propagation Map", bom_ctx,
#                         "What are the key supply chain risks in this BOM and what should procurement prioritise?",
#                     )
#                 st.markdown(
#                     f"<div class='ic' style='margin-top:8px;'><div class='il'>◈ ARIA</div>"
#                     f"<div class='ib'>{interp}</div></div>",
#                     unsafe_allow_html=True,
#                 )

#     # ── Component Detail ──────────────────────────────────────────────────────
#     with comp_tab:
#         sec("Component Detail")
#         bom_display2 = []
#         for _, b in bsn.iterrows():
#             eff_qty = b.get("Effective Order Qty", b["Comp. Qty (CUn)"])
#             fq_txt  = ("1 (Fixed)" if b.get("Fixed Qty Flag", False)
#                        else str(round(float(eff_qty), 3)) if pd.notna(eff_qty) else "—")
#             bom_display2.append({
#                 "Material":    str(b["Material"]),
#                 "Description": str(b["Material Description"])[:36] if pd.notna(b["Material Description"]) else "—",
#                 "Level":       str(b["Level"])[:25] if pd.notna(b["Level"]) else "—",
#                 "Qty":         fq_txt,
#                 "Unit":        str(b["Component unit"]) if pd.notna(b["Component unit"]) else "—",
#                 "Type":        b.get("Procurement Label", "—"),
#                 "Supplier":    b.get("Supplier Display", "—"),
#                 "Location":    b.get("Supplier Location", "—"),
#                 "Transit":     f"{b.get('Transit Days', '—')}d" if b.get("Transit Days") is not None else "—",
#                 "Std Price":   f"${b.get('Standard Price', 0):.2f}" if pd.notna(b.get('Standard Price')) else "—",
#             })
#         df_bd2  = pd.DataFrame(bom_display2)
#         sup_r3  = JsCode("""class R{init(p){const v=p.value||'';this.e=document.createElement('span');if(v.startsWith('⚠')){this.e.style.cssText='background:#FEF3C7;color:#F59E0B;padding:2px 6px;border-radius:4px;font-size:10px;font-weight:600;';this.e.innerText=v;}else if(v==='Revvity Inhouse'){this.e.style.cssText='background:#DCFCE7;color:#16a34a;padding:2px 6px;border-radius:4px;font-size:10px;font-weight:600;';this.e.innerText='🏭 '+v;}else{this.e.style.cssText='background:#EFF6FF;color:#2563EB;padding:2px 6px;border-radius:4px;font-size:10px;';this.e.innerText='🚚 '+v;};}getGui(){return this.e;}}""")
#         gb4     = GridOptionsBuilder.from_dataframe(df_bd2)
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
#         AgGrid(df_bd2, gridOptions=gb4.build(), height=320,
#                allow_unsafe_jscode=True, theme="alpine", custom_css=_AGGRID_CSS)

#     # ── Risk Cascade (unchanged) ─────────────────────────────────────────────
#     with risk_tab:
#         sec("Risk Cascade Analysis")
#         risks = []
#         if snr["risk"] in ["CRITICAL", "WARNING"]:
#             risks.append({
#                 "icon": "⛔", "sev": 3, "color": "#EF4444", "bg": "#FEF2F2",
#                 "title": f"Finished Good at {snr['risk'].title()} Risk",
#                 "detail": (f"{snr['name']} has {round(snr['days_cover'])}d of cover. "
#                            f"SIH={round(snr['sih'])} vs SAP SS={round(snr['safety_stock'])}. "
#                            f"Production continuity at risk."),
#                 "action": f"Order {int(snr.get('repl_quantity', 0))} units immediately. Contact procurement today.",
#             })
#         if cn > 0:
#             risks.append({
#                 "icon": "⚠", "sev": 2, "color": "#F59E0B", "bg": "#FFFBEB",
#                 "title": f"Missing Supplier Data — {cn} External Components",
#                 "detail": (f"{cn} of {external_n} external components have no named supplier. "
#                            f"Single-source risk cannot be assessed for these."),
#                 "action": "Procurement to verify and update BOM with supplier names and lead times.",
#             })
#         if 0 < us <= 2:
#             risks.append({
#                 "icon": "⚠", "sev": 2, "color": "#F59E0B", "bg": "#FFFBEB",
#                 "title": f"Supplier Concentration — {us} Unique Supplier(s)",
#                 "detail": f"High dependency on {us} supplier(s). Any disruption cascades to multiple components simultaneously.",
#                 "action": "Evaluate dual-sourcing for critical external components.",
#             })
#         ext_comps = bsn[bsn["Procurement type"] == "F"]
#         if len(ext_comps) > 0:
#             locs = list(set([str(r) for r in bsn[bsn["Procurement type"] == "F"]["Supplier Location"].dropna().tolist()[:4]]))
#             risks.append({
#                 "icon": "🌍", "sev": 1, "color": "#3B82F6", "bg": "#EFF6FF",
#                 "title": f"External Procurement: {len(ext_comps)} Components",
#                 "detail": (f"External components depend on supplier availability and transit times. "
#                            f"Suppliers located in: {', '.join(locs)}."),
#                 "action": "Review external component lead times — stock buffers for long-transit items.",
#             })

#         if not risks:
#             st.markdown(
#                 "<div style='padding:10px 13px;background:var(--gbg);border:1px solid rgba(34,197,94,0.2);"
#                 "border-radius:var(--r);font-size:12px;color:#14532d;'>"
#                 "✓ No critical propagation risks identified.</div>",
#                 unsafe_allow_html=True,
#             )
#         else:
#             for r in sorted(risks, key=lambda x: -x["sev"]):
#                 st.markdown(
#                     f"<div style='background:{r['bg']};border:1px solid {r['color']}40;"
#                     f"border-left:4px solid {r['color']};border-radius:var(--r);"
#                     f"padding:12px 14px;margin-bottom:8px;'>"
#                     f"<div style='display:flex;align-items:center;gap:8px;margin-bottom:5px;'>"
#                     f"<span style='font-size:16px;'>{r['icon']}</span>"
#                     f"<div style='font-size:12px;font-weight:800;color:{r['color']};'>{r['title']}</div>"
#                     f"</div>"
#                     f"<div style='font-size:11px;color:var(--t2);margin-bottom:5px;'>{r['detail']}</div>"
#                     f"<div style='font-size:11px;color:{r['color']};font-weight:600;'>→ {r['action']}</div>"
#                     f"</div>",
#                     unsafe_allow_html=True,
#                 )

#         # Consolidation opportunities
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
#                     f"<div style='font-size:10px;color:var(--t3);'>{r2['city']} · {r2['email']}</div>"
#                     f"<div style='font-size:10px;color:var(--t2);margin-top:2px;'>Also supplies: {', '.join(others[:3])}</div>"
#                     f"</div>"
#                     f"<div style='font-size:10px;font-weight:700;color:var(--or);'>⚡ Consolidate order</div>"
#                     f"</div>",
#                     unsafe_allow_html=True,
#                 )

#         # ── Ask ARIA with rich BOM context (including Standard Price) ─────────
#         if st.session_state.azure_client:
#             sec("Ask ARIA About This Network")
#             st.info("ℹ️ This assistant provides supplier‑related insights only for the currently selected finished good.")
#             uq = st.text_input(
#                 "Question",
#                 placeholder="e.g. Which supplier provides more than 1 material for DELFIA Wash Concentrate?",
#                 key="snq", label_visibility="collapsed",
#             )
#             if uq and st.button("Ask ARIA", key="sna"):
#                 bom_lines = []
#                 for _, row in bsn.iterrows():
#                     mat_desc = str(row["Material Description"])[:40] if pd.notna(row["Material Description"]) else str(row["Material"])
#                     qty = row["Effective Order Qty"] if "Effective Order Qty" in row else row["Comp. Qty (CUn)"]
#                     fixed = "X (order exactly 1)" if row.get("Fixed Qty Flag") else ""
#                     sup = row.get("Supplier Display", "—")
#                     loc = row.get("Supplier Location", "—")
#                     transit = row.get("Transit Days", "—")
#                     reliability = row.get("Supplier Reliability", "—")
#                     std_price = row.get("Standard Price", "—")
#                     if pd.notna(std_price):
#                         std_price = f"${std_price:.2f}"
#                     bom_lines.append(f"- Component: {mat_desc} | Qty: {qty} {fixed} | Std Price: {std_price} | Supplier: {sup} | Location: {loc} | Transit: {transit}d | Reliability: {reliability}")
#                 bom_table = "\n".join(bom_lines)

#                 ctx3 = (
#                     f"Material: {snr['name']} (ID: {snid})\n"
#                     f"Risk: {snr['risk']}\n"
#                     f"Total components: {tc}\n"
#                     f"Inhouse components: {inhouse_n}\n"
#                     f"External components: {external_n}\n"
#                     f"Missing supplier data: {cn} components\n"
#                     f"Unique external suppliers: {us}\n"
#                     f"BOM details:\n{bom_table}"
#                 )
#                 with st.spinner("Thinking…"):
#                     ans = chat_with_data(st.session_state.azure_client, AZURE_DEPLOYMENT, uq, ctx3)
#                 st.markdown(
#                     f"<div class='ic' style='margin-top:8px;'><div class='il'>◈ ARIA</div>"
#                     f"<div class='ib'>{ans}</div></div>",
#                     unsafe_allow_html=True,
#                 )

#     st.markdown('<div class="pfooter">🕸️ Powered by <strong>MResult</strong></div>', unsafe_allow_html=True)
# #                     f"<div class='ib'>{ans}</div></div>",
# #                     unsafe_allow_html=True,
# #                 )

# #     st.markdown('<div class="pfooter">🕸️ Powered by <strong>MResult</strong></div>', unsafe_allow_html=True)

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

    # ── BOM Map – Sankey diagram with clean legend ──────────────────────────────
    with sn_tab:
        sec("BOM Propagation Map")
        # Fixed legend: HTML list inside a note box (no bold/3D)
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
        Hover over nodes for details.
        </div>
        """, unsafe_allow_html=True)

        # Build node list and links for Sankey
        nodes = []
        node_colors = []
        node_map = {}

        # Root node (finished good)
        root_name = str(snr["name"])  # ensure string
        root_risk_color = {"CRITICAL": "#EF4444", "WARNING": "#F59E0B", "HEALTHY": "#22C55E"}.get(snr["risk"], "#94A3B8")
        nodes.append(root_name)
        node_colors.append(root_risk_color)
        node_map[root_name] = 0

        sources = []
        targets = []
        values = []

        # Process each BOM row
        for _, row in bsn.iterrows():
            comp_desc = str(row["Material Description"])[:40] if pd.notna(row["Material Description"]) else str(row["Material"])
            comp_label = f"[C] {comp_desc}"
            sup_display = row.get("Supplier Display", "—")
            proc_type = str(row.get("Procurement type", "")).strip()
            qty = row.get("Effective Order Qty", row["Comp. Qty (CUn)"]) if pd.notna(row.get("Effective Order Qty", row["Comp. Qty (CUn)"]) ) else 1
            # Ensure qty is numeric
            try:
                qty = float(qty)
            except:
                qty = 1.0

            # Add component node if not already present
            if comp_label not in node_map:
                # Determine component colour
                if proc_type == "E":
                    comp_color = "#22C55E"   # Inhouse
                elif sup_display.startswith("⚠"):
                    comp_color = "#F59E0B"   # Missing supplier
                else:
                    comp_color = "#3B82F6"   # External named
                nodes.append(comp_label)
                node_colors.append(comp_color)
                node_map[comp_label] = len(nodes) - 1

            # Link root -> component
            sources.append(node_map[root_name])
            targets.append(node_map[comp_label])
            values.append(qty)

            # Add supplier node if external and named
            if sup_display not in ["Revvity Inhouse", "—"] and not sup_display.startswith("⚠"):
                sup_label = f"[S] {str(sup_display)[:25]}"
                if sup_label not in node_map:
                    nodes.append(sup_label)
                    node_colors.append("#8B5CF6")  # Purple for suppliers
                    node_map[sup_label] = len(nodes) - 1
                # Link component -> supplier
                sources.append(node_map[comp_label])
                targets.append(node_map[sup_label])
                values.append(1.0)  # connection weight

        # Build Sankey figure with normal font weight
        fig_sankey = go.Figure(data=[go.Sankey(
            arrangement="snap",
            node=dict(
                pad=20,
                thickness=20,
                line=dict(color="white", width=0.5),
                label=nodes,
                color=node_colors,
                hovertemplate="<b>%{label}</b><extra></extra>"
            ),
            link=dict(
                source=sources,
                target=targets,
                value=values,
                color="rgba(200,200,200,0.3)"
            )
        )])
        fig_sankey.update_layout(
            title=None,
            font=dict(size=11, family="Inter", weight="normal"),  # ensure normal font weight
            height=500,
            margin=dict(l=20, r=20, t=20, b=20),
            paper_bgcolor="white",
        )
        st.plotly_chart(fig_sankey, use_container_width=True)

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

        # ── Ask ARIA with rich BOM context (including Standard Price) ─────────
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
