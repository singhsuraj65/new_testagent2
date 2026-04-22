
"""
tabs/scenario_engine.py
Scenario Engine tab: Demand Shock simulation, Supply Disruption simulation,
and Historical Replay.
"""

import math
import streamlit as st
import plotly.graph_objects as go

from utils.helpers import ct, sec, note, ORANGE, AZURE_DEPLOYMENT
from data_loader import get_stock_history
from agent import simulate_scenario, simulate_multi_sku_disruption, chat_with_data


def render():
    summary = st.session_state.summary

    st.markdown(
        "<div style='font-size:15px;font-weight:800;margin-bottom:4px;'>Scenario Engine</div>"
        "<div style='font-size:12px;color:var(--t3);margin-bottom:14px;'>"
        "Forward simulation · Supply disruption · Historical replay · LLM interpretation</div>",
        unsafe_allow_html=True,
    )

    sim_tab, dis_tab, rep_tab = st.tabs(["📈  Demand Shock", "🔴  Supply Disruption", "↺  Historical Replay"])

    # ── Demand Shock ──────────────────────────────────────────────────────────
    with sim_tab:
        st.markdown(
            "<div style='padding:8px 0;font-size:12px;color:var(--t2);'>"
            "<strong>Demand Shock</strong> simulates how different demand levels affect your stock over 6 months. "
            "Use the shock month/multiplier to model sudden demand spikes (e.g. seasonal peak or unexpected order).</div>",
            unsafe_allow_html=True,
        )
        cc2, rc = st.columns([1, 2])
        with cc2:
            sec("Controls")
            sim_opts = {r["name"]: r["material"] for _, r in summary[summary.risk != "INSUFFICIENT_DATA"].iterrows()}
            sn       = st.selectbox("Material", list(sim_opts.keys()), key="sm")
            sid      = sim_opts[sn]
            sr       = summary[summary.material == sid].iloc[0]
            ad       = sr["avg_monthly_demand"]
            ss_sim   = sr["safety_stock"]
            lot_sim  = sr["lot_size"]
            lt_sim   = sr["lead_time"]
            st.markdown(
                f'<div class="chip" style="margin-bottom:8px;font-size:10px;">'
                f'SIH: {round(sr["sih"])} · SS: {round(ss_sim)} · LT: {round(lt_sim)}d · Lot: {round(lot_sim)}</div>',
                unsafe_allow_html=True,
            )
            st.markdown("<div style='font-size:10px;color:var(--t3);margin-bottom:4px;'>Expected demand/month</div>", unsafe_allow_html=True)
            ed = st.number_input("Expected demand/month", min_value=int(ad * 0.3), max_value=int(ad * 3 + 50), value=int(ad), step=1, label_visibility="collapsed", key="exp_demand")
            son = st.toggle("Add demand shock", False, key="son", help="Simulates a sudden spike in one specific month")
            smo = smx = None
            if son:
                st.markdown("<div style='font-size:10px;color:var(--t3);'>Shock month: which month the spike occurs</div>", unsafe_allow_html=True)
                smo = st.slider("Shock month", 1, 6, 2, key="smo")
                st.markdown("<div style='font-size:10px;color:var(--t3);'>Multiplier: how many times the normal demand</div>", unsafe_allow_html=True)
                smx = st.slider("Multiplier", 1.5, 5.0, 2.5, step=0.5, key="smx")
            oon = st.toggle("Place order", False, key="oon", help="Simulates placing an emergency order that arrives after the lead time")
            oq = ot = None
            if oon:
                repl_default = max(
                    int(max(ss_sim - sr["sih"], 0) / max(lot_sim, 1)) * int(lot_sim) if lot_sim > 0 else int(max(ss_sim - sr["sih"], 0)),
                    100,
                )
                oq = st.slider("Order qty", 50, 2000, repl_default, step=50)
                ot = st.slider("Arrives (days)", 1, 60, int(lt_sim))
            rsim = st.button("▶  Run Demand Simulation", use_container_width=True)

        with rc:
            sec("6-Month Projection")
            if rsim or st.session_state.get("sim_ran"):
                mos = 6
                stk = sr["sih"]
                ss = ss_sim
                scns = {"Low (−40%)": [ed * 0.6] * mos, "Expected": [ed] * mos, "High (+60%)": [ed * 1.6] * mos}
                if son and smo and smx:
                    for k in scns:
                        if k != "Low (−40%)":
                            scns[k][smo - 1] = ed * smx
                oa = int(ot / 30) if oon and ot else None
                fs = go.Figure()
                scc = {"Low (−40%)": "#22C55E", "Expected": ORANGE, "High (+60%)": "#EF4444"}
                bi = {}
                for sc_k, dems in scns.items():
                    proj = []
                    s = stk
                    for m, d in enumerate(dems):
                        if oon and oq and m == oa:
                            s += oq
                        s = max(0.0, s - d)
                        proj.append(s)
                    bi[sc_k] = next((m + 1 for m, sp in enumerate(proj) if sp < max(ss, 1)), None)
                    fs.add_trace(go.Scatter(
                        x=[f"M{i+1}" for i in range(mos)], y=proj, mode="lines+markers", name=sc_k,
                        line=dict(color=scc[sc_k], width=2.5), marker=dict(size=5, color=scc[sc_k]),
                    ))
                if ss > 0:
                    fs.add_hline(y=ss, line_color="#EF4444", line_dash="dot", line_width=1.5,
                                 annotation_text=f"SAP SS ({round(ss)})",
                                 annotation_font_color="#EF4444", annotation_font_size=9)
                ct(fs, 270)
                st.plotly_chart(fs, use_container_width=True)
                st.session_state["sim_ran"] = True

                vc = st.columns(3)
                for col, (sc_k, br) in zip(vc, bi.items()):
                    cl = "#EF4444" if br else "#22C55E"
                    bg = "#FEF2F2" if br else "#F0FDF4"
                    txt = f"⛔ Breach M{br}" if br else "✓ Safe 6mo"
                    with col:
                        st.markdown(
                            f"<div class='sc' style='padding:9px 11px;flex-direction:column;gap:2px;'>"
                            f"<div style='font-size:9px;color:var(--t3);'>{sc_k}</div>"
                            f"<div style='font-size:12px;font-weight:800;color:{cl};background:{bg};padding:3px 7px;border-radius:6px;'>{txt}</div>"
                            f"</div>",
                            unsafe_allow_html=True,
                        )

                order_qty = int(math.ceil(max(0, ss - stk) / lot_sim) * lot_sim) if lot_sim > 0 else 0
                note(f"**Order quantity:** {order_qty} units (calculated as CEILING(shortfall / lot size) × lot size).")

                # Build detailed HTML manual verdict for Demand Shock (with "Safety stock breach" wording)
                expected_breach = bi.get("Expected")
                low_breach = bi.get("Low (−40%)")
                high_breach = bi.get("High (+60%)")

                html_lines = []
                if expected_breach is not None:
                    html_lines.append(f"<p>⚠️ <strong>Expected demand scenario:</strong> Safety stock breach would occur in <strong>month {expected_breach}</strong>.</p>")
                    html_lines.append(f"<p style='margin-left:20px;'>Current stock: {stk} units | Safety stock: {ss} units.<br>")
                    html_lines.append(f"<strong>Action:</strong> Place an order immediately or before month {expected_breach} to avoid disruption.</p>")
                else:
                    html_lines.append(f"<p>✅ <strong>Expected demand scenario:</strong> Stock remains above safety stock for all 6 months.</p>")
                    html_lines.append(f"<p style='margin-left:20px;'>Current stock: {stk} units | Safety stock: {ss} units.<br>")
                    html_lines.append(f"<strong>Action:</strong> Continue monitoring; no urgent order needed.</p>")
                
                html_lines.append("<hr style='margin:8px 0;'>")
                if low_breach is not None:
                    html_lines.append(f"<p>📉 <strong>Low demand (−40%):</strong> Safety stock breach in month {low_breach}.</p>")
                else:
                    html_lines.append(f"<p>📉 <strong>Low demand (−40%):</strong> No safety stock breach.</p>")
                
                if high_breach is not None:
                    html_lines.append(f"<p>📈 <strong>High demand (+60%):</strong> Safety stock breach in month {high_breach}.</p>")
                else:
                    html_lines.append(f"<p>📈 <strong>High demand (+60%):</strong> No safety stock breach.</p>")
                
                html_lines.append("<hr style='margin:8px 0;'>")
                if expected_breach is not None:
                    html_lines.append(f"<p><strong>Summary:</strong> Under expected demand, you have only {expected_breach} month(s) of cover. The high-demand scenario shows risk as early as month {high_breach if high_breach else 'N/A'}. <strong>Consider increasing safety stock or placing a buffer order immediately.</strong></p>")
                else:
                    html_lines.append(f"<p><strong>Summary:</strong> Under expected demand, you have more than 6 months of cover. The high-demand scenario shows risk in month {high_breach if high_breach else 'N/A'}. No immediate action required, but monitor demand trends.</p>")
                
                manual_explanation_html = "".join(html_lines)

                if st.session_state.azure_client and rsim:
                    with st.spinner("ARIA evaluating…"):
                        sv = simulate_scenario(
                            st.session_state.azure_client, AZURE_DEPLOYMENT,
                            sn, stk, ss, lt_sim, lot_sim,
                            {"low": ed * 0.6, "expected": ed, "high": ed * 1.6},
                            {"quantity": oq, "timing_days": ot} if oon else None,
                        )
                    if sv.get("simulation_verdict") == "Simulation completed, but ARIA could not generate a verdict. Please review the graph manually.":
                        sv["simulation_verdict"] = manual_explanation_html
                    else:
                        # Post-process the verdict to replace "stockout" with "safety stock breach"
                        verdict_text = sv.get("simulation_verdict", "")
                        verdict_text = verdict_text.replace("stockout", "safety stock breach").replace("Stockout", "Safety stock breach")
                        sv["simulation_verdict"] = verdict_text
                    urg = sv.get("urgency", "MONITOR")
                    uc = {"ACT TODAY": "#EF4444", "ACT THIS WEEK": "#F59E0B", "MONITOR": ORANGE, "SAFE": "#22C55E"}.get(urg, ORANGE)
                    st.markdown(
                        f"<div class='ic' style='margin-top:10px;'><div class='il'>◈ ARIA Verdict</div>"
                        f"<div style='display:flex;align-items:center;gap:8px;margin-bottom:6px;'>"
                        f"<span style='font-size:12px;font-weight:800;color:{uc};'>{urg}</span>"
                        f"</div>"
                        f"<div class='ib'>{sv.get('simulation_verdict', '')}</div></div>",
                        unsafe_allow_html=True,
                    )
                elif rsim and not st.session_state.azure_client:
                    st.markdown(
                        f"<div class='ic' style='margin-top:10px;'><div class='il'>◈ ARIA Verdict (Manual)</div>"
                        f"<div class='ib'>{manual_explanation_html}</div></div>",
                        unsafe_allow_html=True,
                    )

    # ── Supply Disruption ─────────────────────────────────────────────────────
    with dis_tab:
        st.markdown(
            "<div style='padding:8px 0 10px;font-size:12px;color:var(--t2);'>"
            "<strong>Supply Disruption</strong> simulates a freeze in replenishment across selected materials. "
            "This models scenarios like supplier insolvency, geopolitical disruption, or production shutdown. "
            "ARIA ranks which SKUs breach safety stock first and by how much.</div>",
            unsafe_allow_html=True,
        )
        note("Formula: daily consumption × disruption days = stock consumed. "
             "Breach = remaining stock < Safety Stock. Emergency order = CEILING(Shortfall/FLS)×FLS.")
        dc2, dr = st.columns([1, 2])
        with dc2:
            sec("Disruption Parameters")
            st.markdown("<div style='font-size:10px;color:var(--t3);margin-bottom:3px;'>Duration of supply freeze</div>", unsafe_allow_html=True)
            disruption_days = st.slider("days", 7, 90, 30, step=7, label_visibility="collapsed", key="dis_days")
            affected = st.multiselect(
                "Affected materials (blank=all)",
                [r["name"] for _, r in summary[summary.risk != "INSUFFICIENT_DATA"].iterrows()],
                key="dis_mats",
            )
            run_dis = st.button("🔴  Run Disruption", use_container_width=True)

        with dr:
            sec("Impact — Ranked by Severity")
            if run_dis or st.session_state.get("dis_ran"):
                adis = summary[summary.risk != "INSUFFICIENT_DATA"]
                if affected:
                    adis = adis[adis.name.isin(affected)]
                sku_data = [{
                    "material": r["material"], "name": r["name"],
                    "current_stock": r["sih"], "safety_stock": r["safety_stock"],
                    "lead_time": r["lead_time"], "fixed_lot_size": r["lot_size"],
                    "avg_monthly_demand": r["avg_monthly_demand"], "risk": r["risk"],
                } for _, r in adis.iterrows()]
                results = simulate_multi_sku_disruption(None, None, disruption_days, sku_data)
                st.session_state["dis_ran"] = True

                # Build a manual summary for the disruption (fallback if LLM fails)
                breached_materials = [r for r in results if r["breach_occurs"]]
                if breached_materials:
                    worst = breached_materials[0]
                    manual_disruption_html = f"""
                    <p>⚠️ <strong>Supply disruption of {disruption_days} days would cause safety stock breaches for {len(breached_materials)} material(s).</strong></p>
                    <p><strong>Most critical:</strong> {worst['name']} would breach on day {worst['days_to_breach']} (shortfall {worst['shortfall_units']} units).</p>
                    <p><strong>Recommended action:</strong> Place emergency orders for {worst['name']} ({worst['reorder_qty']} units) and review safety stocks for all affected materials.</p>
                    """
                else:
                    manual_disruption_html = f"<p>✅ <strong>Supply disruption of {disruption_days} days would NOT cause any safety stock breach.</strong> Current stock levels are sufficient to cover the freeze period.</p>"

                for i, r in enumerate(results):
                    bc = r["breach_occurs"]
                    brd = "#EF4444" if bc else "#22C55E"
                    bgc = "rgba(239,68,68,0.03)" if bc else "#FFFFFF"
                    days_txt = (f"Breach Day {r['days_to_breach']}" if bc and r['days_to_breach'] is not None
                                else ("Already breached" if bc else f"Safe for {disruption_days}d"))
                    metric_cells = ""
                    for val, lbl, c in [
                        (str(r["stock_at_end"]), "End", "#EF4444" if r["shortfall_units"] > 0 else "#22C55E"),
                        (str(r["shortfall_units"]), "Short", "#EF4444" if r["shortfall_units"] > 0 else "#94A3B8"),
                        (f"{r['lead_time']}d", "LT", "#1E293B"),
                        (str(r["reorder_qty"]), "Order", "#EF4444" if r["reorder_qty"] > 0 else "#94A3B8"),
                    ]:
                        metric_cells += (
                            f"<div style='background:var(--s3);border-radius:5px;padding:4px;'>"
                            f"<div style='font-size:11px;font-weight:800;color:{c};'>{val}</div>"
                            f"<div style='font-size:8px;color:var(--t3);'>{lbl}</div></div>"
                        )
                    st.markdown(
                        f"<div class='prow' style='border-left:3px solid {brd};background:{bgc};margin-bottom:6px;'>"
                        f"<div style='min-width:22px;font-size:13px;font-weight:900;color:{brd};'>{i+1}</div>"
                        f"<div style='font-size:16px;'>{'⛔' if bc else '✓'}</div>"
                        f"<div style='flex:1;'>"
                        f"<div style='font-size:12px;font-weight:800;color:var(--t);'>{r['name']}</div>"
                        f"<div style='font-size:10px;color:{brd};font-weight:600;margin-top:1px;'>{days_txt}</div>"
                        f"</div>"
                        f"<div style='display:grid;grid-template-columns:repeat(4,62px);gap:4px;text-align:center;'>"
                        + metric_cells +
                        f"</div></div>",
                        unsafe_allow_html=True,
                    )

                if st.session_state.azure_client and run_dis:
                    breached = [r for r in results if r["breach_occurs"]]
                    if breached:
                        ctx_dis = (f"Disruption: {disruption_days}d freeze. "
                                   f"Breaches: {', '.join([r['name'] for r in breached])}. "
                                   f"Worst: {breached[0]['name']} on day {breached[0]['days_to_breach'] or 0}.")
                        with st.spinner("ARIA evaluating…"):
                            dv = chat_with_data(
                                st.session_state.azure_client, AZURE_DEPLOYMENT,
                                "2-sentence executive verdict on this supply disruption. What is most critical?",
                                ctx_dis,
                            )
                        # If LLM returns a generic error, replace with manual fallback
                        if dv == "Error:" or "could not generate" in dv.lower() or len(dv) < 20:
                            dv = manual_disruption_html
                        st.markdown(
                            f"<div class='ic' style='margin-top:10px;'>"
                            f"<div class='il'>◈ ARIA DISRUPTION VERDICT</div>"
                            f"<div class='ib'>{dv}</div></div>",
                            unsafe_allow_html=True,
                        )
                    else:
                        st.markdown(
                            f"<div class='ic' style='margin-top:10px;'>"
                            f"<div class='il'>◈ ARIA DISRUPTION VERDICT</div>"
                            f"<div class='ib'>{manual_disruption_html}</div></div>",
                            unsafe_allow_html=True,
                        )
                elif run_dis and not st.session_state.azure_client:
                    st.markdown(
                        f"<div class='ic' style='margin-top:10px;'>"
                        f"<div class='il'>◈ DISRUPTION ANALYSIS (Manual)</div>"
                        f"<div class='ib'>{manual_disruption_html}</div></div>",
                        unsafe_allow_html=True,
                    )

    # ── Historical Replay ──────────────────────────────────────────────────────
    with rep_tab:
        st.markdown(
            "<div style='padding:8px 0 10px;font-size:12px;color:var(--t2);'>"
            "<strong>Historical Replay</strong> shows what actually happened in a past period and reconstructs "
            "when ARIA would have triggered an order signal — demonstrating the value of predictive replenishment.</div>",
            unsafe_allow_html=True,
        )
        rp_opts = {r["name"]: r["material"] for _, r in summary[summary.risk != "INSUFFICIENT_DATA"].iterrows()}
        rp_sn = st.selectbox("Material", list(rp_opts.keys()), key="rp_mat")
        rp_sid = rp_opts[rp_sn]
        rp_sr = summary[summary.material == rp_sid].iloc[0]
        shrp = get_stock_history(st.session_state.data, rp_sid)
        pds_lbl = shrp["label"].tolist()

        if len(pds_lbl) > 4:
            rps = st.selectbox("Replay from period", pds_lbl[:-3],
                               index=min(8, len(pds_lbl) - 4), key="rps")
            if st.button("↺  Replay this period", key="rpb"):
                idx = pds_lbl.index(rps)
                rd = shrp.iloc[idx:idx + 6]
                ssr = rp_sr["safety_stock"]
                fr = go.Figure()
                fr.add_trace(go.Scatter(
                    x=rd["label"], y=rd["Gross Stock"], mode="lines+markers", name="Actual Stock",
                    line=dict(color=ORANGE, width=2.5), marker=dict(size=7, color=ORANGE),
                    fill="tozeroy", fillcolor="rgba(244,123,37,0.07)",
                    hovertemplate="<b>%{x}</b><br>%{y} units<extra></extra>",
                ))
                if ssr > 0:
                    fr.add_hline(y=ssr, line_color="#EF4444", line_dash="dot",
                                 annotation_text=f"SAP SS {round(ssr)}", annotation_font_color="#EF4444")
                
                # FIX #2: Handle potential errors when adding vertical lines for breach
                br2 = rd[rd["Gross Stock"] < max(ssr, 1)]
                if len(br2) > 0:
                    try:
                        bp = br2.iloc[0]["label"]
                        # Find index safely
                        breach_idx = br2.index[0]
                        if breach_idx in rd.index:
                            current_pos = rd.index.get_loc(breach_idx)
                            prev_idx = max(0, current_pos - 1)
                            prev_label = rd.iloc[prev_idx]["label"]
                            fr.add_vline(x=bp, line_color="#EF4444", line_dash="dash",
                                         annotation_text="⛔ Breach", annotation_font_color="#EF4444")
                            fr.add_vline(x=prev_label, line_color="#22C55E", line_dash="dash",
                                         annotation_text="◈ ARIA signal", annotation_font_color="#22C55E")
                    except Exception as e:
                        st.warning(f"Could not draw breach annotations: {e}")
                
                ct(fr, 260)
                st.plotly_chart(fr, use_container_width=True)
                msg = ("⛔ Breach detected. ARIA would have signalled an order one period earlier."
                       if len(br2) > 0 else
                       "✓ No breach in this period — stock remained above safety stock.")
                mc2 = "#EF4444" if len(br2) > 0 else "#22C55E"
                mb2 = "#FEF2F2" if len(br2) > 0 else "#F0FDF4"
                st.markdown(
                    f"<div style='font-size:11px;color:{mc2};padding:7px 11px;background:{mb2};border-radius:8px;'>{msg}</div>",
                    unsafe_allow_html=True,
                )

    st.markdown('<div class="pfooter">⚡ Powered by <strong>MResult</strong></div>', unsafe_allow_html=True)

# """
# tabs/material_intelligence.py
# Material Intelligence tab: agentic analysis, Monte Carlo simulation,
# stock trajectory, safety stock audit, BOM components, supplier email draft,
# and consolidation opportunities.
# """

# import streamlit as st
# import pandas as pd
# import plotly.graph_objects as go
# from st_aggrid import AgGrid, GridOptionsBuilder, JsCode

# from utils.helpers import ct, fmt_p, sbadge, sec, note, ORANGE, AZURE_DEPLOYMENT
# from data_loader import (
#     get_stock_history, get_demand_history, get_bom_components,
#     get_material_context, get_supplier_consolidation,
# )
# from agent import analyse_material, chat_with_data, run_monte_carlo, draft_supplier_email

# _AGGRID_CSS = {
#     ".ag-root-wrapper": {"border": "1px solid #E2E8F0!important", "border-radius": "12px!important"},
#     ".ag-header":       {"background": "#F8FAFE!important"},
#     ".ag-row-even":     {"background": "#FFFFFF!important"},
#     ".ag-row-odd":      {"background": "#F8FAFE!important"},
# }


# def render():
#     data           = st.session_state.data
#     summary        = st.session_state.summary
#     MATERIAL_LABELS = st.session_state.material_labels

#     mat_opts = {row["name"]: row["material"] for _, row in summary.iterrows()}
#     sel_name = st.selectbox("Select Material", list(mat_opts.keys()), key="mi_mat",
#                             help="Select a finished good to analyse")
#     sel_mat  = mat_opts[sel_name]
#     mat_row  = summary[summary.material == sel_mat].iloc[0]
#     risk     = mat_row["risk"]

#     # ── Insufficient data guard ───────────────────────────────────────────────
#     if risk == "INSUFFICIENT_DATA":
#         reasons = []
#         if mat_row["nonzero_demand_months"] < 3:
#             reasons.append(f"Only {mat_row['nonzero_demand_months']} months demand (min 6)")
#         if mat_row["zero_periods"] > 10:
#             reasons.append(f"Zero stock in {mat_row['zero_periods']}/{mat_row['total_periods']} periods")
#         if sel_mat == "3515-0010":
#             reasons.append("Marked inactive in sales history")
#         r_html = "".join(f'<div style="font-size:11px;color:var(--t3);margin:3px 0;">• {r}</div>' for r in reasons)
#         st.markdown(
#             f"<div style='display:flex;align-items:center;gap:12px;margin-bottom:16px;'>"
#             f"<div style='font-size:18px;font-weight:800;'>{sel_name}</div>{sbadge(risk)}</div>"
#             f"<div class='flag-box' style='max-width:520px;'>"
#             f"<div style='font-size:22px;margin-bottom:8px;'>◌</div>"
#             f"<div style='font-size:14px;font-weight:800;color:var(--t2);margin-bottom:5px;'>Insufficient Data for ARIA Analysis</div>"
#             f"<div style='font-size:12px;color:var(--t3);margin-bottom:8px;'>Requires 6+ months confirmed demand history.</div>"
#             f"{r_html}</div>",
#             unsafe_allow_html=True,
#         )
#         st.stop()

#     # ── Header ────────────────────────────────────────────────────────────────
#     h1c, h2c = st.columns([5, 1])
#     with h1c:
#         dq_flags   = mat_row.get("data_quality_flags", [])
#         flags_html = "".join(
#             f'<span class="chip" style="margin-right:4px;color:#F59E0B;border-color:#F59E0B40;">⚠ {f}</span>'
#             for f in dq_flags[:2]
#         ) if dq_flags else ""
#         st.markdown(
#             f"<div style='display:flex;align-items:center;flex-wrap:wrap;gap:8px;margin-bottom:6px;'>"
#             f"<div style='font-size:18px;font-weight:900;'>{sel_name}</div>"
#             f"{sbadge(risk)}<div class='chip'>{sel_mat}</div>{flags_html}</div>",
#             unsafe_allow_html=True,
#         )
#     with h2c:
#         run_an = st.button("◈ Analyse", use_container_width=True, key=f"analyse_btn_{sel_mat}")

#     # ── ARIA Analysis ─────────────────────────────────────────────────────────
#     analysis = st.session_state.agent_cache.get(sel_mat)
#     if run_an:
#         if st.session_state.azure_client:
#             with st.spinner("ARIA investigating…"):
#                 ctx      = get_material_context(data, sel_mat, summary)
#                 analysis = analyse_material(st.session_state.azure_client, AZURE_DEPLOYMENT, ctx)
#                 st.session_state.agent_cache[sel_mat]  = analysis
#                 st.session_state.last_analysed_mat     = sel_mat
#         else:
#             st.markdown(
#                 "<div style='padding:9px 12px;background:var(--ob);border:1px solid var(--obr);"
#                 "border-radius:9px;font-size:12px;color:var(--or);'>"
#                 "Enter Azure API key in sidebar to enable ARIA analysis.</div>",
#                 unsafe_allow_html=True,
#             )

#     if analysis and st.session_state.agent_cache.get(sel_mat):
#         # Key findings
#         key_findings = analysis.get("key_findings", [])
#         if not isinstance(key_findings, list):
#             key_findings = [str(key_findings)]
#         else:
#             key_findings = [str(f) for f in key_findings]
#         fh = "".join(f'<div class="iff"><div class="ifd"></div><div>{f}</div></div>' for f in key_findings)

#         # Confidence
#         conf       = str(analysis.get("data_confidence", "MEDIUM"))
#         conf_clean = conf.split("—")[0].split("-")[0].strip().upper()[:6]
#         cc         = "#22C55E" if "HIGH" in conf_clean else "#F59E0B" if "MEDIUM" in conf_clean else "#EF4444"

#         # Data quality flags
#         dq      = analysis.get("data_quality_flags", [])
#         dq_html = (
#             "<div style='margin-top:10px;padding-top:8px;border-top:1px solid var(--bl);'>"
#             + "".join(f'<div style="font-size:10px;color:#F59E0B;margin:2px 0;">⚠ {f}</div>' for f in dq)
#             + "</div>"
#         ) if dq else ""

#         # Display ARIA Intelligence box
#         st.markdown(
#             f"<div class='ic'><div class='il'>◈ ARIA Intelligence</div>"
#             f"<div class='ih'>{analysis.get('headline', '')}</div>"
#             f"<div class='ib'>{analysis.get('executive_summary', '')}</div>"
#             f"<div style='margin-top:10px;border-top:1px solid var(--bl);padding-top:10px;'>"
#             f"<div style='font-size:9px;font-weight:700;color:var(--or);text-transform:uppercase;letter-spacing:1px;margin-bottom:6px;'>Key Findings</div>"
#             f"{fh}{dq_html}</div>"
#             f"<div style='margin-top:8px;font-size:10px;color:var(--t3);'>"
#             f"Confidence: <span style='color:{cc};font-weight:700;'>{conf_clean}</span>"
#             f"</div></div>",
#             unsafe_allow_html=True,
#         )

#         # SAP Gap and ARIA Recommendation (clean bullet list)
#         ca, cb = st.columns(2)
#         sap_gap = analysis.get("sap_gap", "")
#         if not isinstance(sap_gap, str):
#             sap_gap = str(sap_gap)
#         recom_raw = analysis.get("recommendation", "")
        
#         # Convert recommendation to a clean bullet list if it's a dict or dict-like string
#         if isinstance(recom_raw, dict):
#             recom_lines = []
#             for k, v in recom_raw.items():
#                 if k.lower() == "reason":
#                     recom_lines.append(f"<strong>Reason:</strong> {v}")
#                 else:
#                     recom_lines.append(f"<strong>{k}:</strong> {v}")
#             recom = "<ul style='margin:0; padding-left:16px; font-size:11px; color:#14532d;'>" + "".join(f"<li>{line}</li>" for line in recom_lines) + "</ul>"
#         else:
#             recom = str(recom_raw)
#             # Try to parse if it looks like a dictionary string
#             if recom.startswith("{") and "SKU" in recom:
#                 try:
#                     import ast
#                     d = ast.literal_eval(recom)
#                     if isinstance(d, dict):
#                         recom_lines = [f"<strong>{k}:</strong> {v}" for k, v in d.items()]
#                         recom = "<ul style='margin:0; padding-left:16px; font-size:11px; color:#14532d;'>" + "".join(f"<li>{line}</li>" for line in recom_lines) + "</ul>"
#                 except:
#                     pass

#         if "Unable to parse" in sap_gap:
#             sap_gap = (f"SAP Safety Stock: {mat_row['safety_stock']:.0f} units. "
#                        f"ARIA recommends: {mat_row['rec_safety_stock']:.0f} units. "
#                        f"Gap: {mat_row['rec_safety_stock'] - mat_row['safety_stock']:.0f} units.")
#         if "No replenishment triggered" in str(recom_raw) and mat_row["repl_triggered"]:
#             recom = (f"<strong>Order {int(mat_row['repl_quantity'])} units immediately.</strong><br>"
#                      f"Stock-in-Hand ({mat_row['sih']:.0f}) below SAP SS ({mat_row['safety_stock']:.0f}).<br>"
#                      f"Lead time: {mat_row['lead_time']:.0f}d. Formula: {mat_row['repl_formula']}")

#         with ca:
#             st.markdown(f"<div class='sap-box'><div class='sap-lbl'>SAP Gap Assessment</div>{sap_gap}</div>", unsafe_allow_html=True)
#         with cb:
#             st.markdown(
#                 f"<div class='rec-box'><div class='rec-lbl'>ARIA Recommendation</div>"
#                 f"{recom}"
#                 f"<div style='margin-top:8px;font-size:10px;opacity:0.75;'>If ignored: {analysis.get('risk_if_ignored', '')}</div></div>",
#                 unsafe_allow_html=True,
#             )

#         # Supplier action
#         sup_action = analysis.get("supplier_action")
#         if sup_action:
#             st.markdown(
#                 f"<div style='padding:8px 12px;background:rgba(59,130,246,0.06);"
#                 f"border:1px solid rgba(59,130,246,0.2);border-radius:8px;font-size:11px;color:#1d4ed8;margin-top:8px;'>"
#                 f"📧 <strong>Supplier Action:</strong> {sup_action}</div>",
#                 unsafe_allow_html=True,
#             )
#     elif not run_an:
#         st.markdown(
#             "<div style='padding:12px 14px;background:var(--s2);border:1px solid var(--bl);"
#             "border-radius:var(--r);font-size:12px;color:var(--t3);text-align:center;'>"
#             "Click <strong style='color:var(--or);'>◈ Analyse</strong> above to run ARIA intelligence on this material.</div>",
#             unsafe_allow_html=True,
#         )

#     # ── Monte Carlo Risk Simulation ──────────────────────────────────────────
#     sec("Monte Carlo Risk Simulation — 1,000 Demand Scenarios")
#     note("Runs 1,000 simulations of 6-month demand using historical mean & std deviation. "
#          "Shows probability of stockout and range of outcomes.")
#     avg_d = mat_row["avg_monthly_demand"]
#     std_d = mat_row["std_demand"]
#     ss_v  = mat_row["safety_stock"]
#     rec   = mat_row["rec_safety_stock"]
#     lt_v  = mat_row["lead_time"]

#     if avg_d > 0 and std_d > 0:
#         mc = run_monte_carlo(mat_row["sih"], ss_v, avg_d, std_d, lt_v, months=6, n_sims=1000)
#         risk_color = {"HIGH RISK": "#EF4444", "MODERATE RISK": "#F59E0B",
#                       "LOW RISK": "#22C55E", "VERY LOW RISK": "#22C55E"}.get(mc["verdict"], ORANGE)

#         mc_col1, mc_col2, mc_col3 = st.columns(3)
#         with mc_col1:
#             st.markdown(
#                 f"<div class='sc' style='flex-direction:column;align-items:center;padding:16px;'>"
#                 f"<div style='font-size:28px;font-weight:900;color:{risk_color};'>{mc['probability_breach_pct']}%</div>"
#                 f"<div style='font-size:11px;color:var(--t3);text-align:center;'>Probability of stockout<br>in next 6 months</div>"
#                 f"<div style='font-size:12px;font-weight:700;color:{risk_color};margin-top:4px;'>{mc['verdict']}</div>"
#                 f"</div>",
#                 unsafe_allow_html=True,
#             )
#         with mc_col2:
#             st.markdown(
#                 f"<div class='sc' style='flex-direction:column;gap:0;'>"
#                 f"<div style='font-size:10px;color:var(--t3);margin-bottom:8px;font-weight:600;'>OUTCOME RANGE (6mo)</div>"
#                 f"<div style='display:flex;justify-content:space-between;margin-bottom:4px;'>"
#                 f"<span style='font-size:10px;color:var(--t3);'>Pessimistic (P10)</span>"
#                 f"<span style='font-size:12px;font-weight:700;color:#EF4444;'>{int(mc['p10_end_stock'])} units</span></div>"
#                 f"<div style='display:flex;justify-content:space-between;margin-bottom:4px;'>"
#                 f"<span style='font-size:10px;color:var(--t3);'>Median (P50)</span>"
#                 f"<span style='font-size:12px;font-weight:700;color:{ORANGE};'>{int(mc['p50_end_stock'])} units</span></div>"
#                 f"<div style='display:flex;justify-content:space-between;'>"
#                 f"<span style='font-size:10px;color:var(--t3);'>Optimistic (P90)</span>"
#                 f"<span style='font-size:12px;font-weight:700;color:#22C55E;'>{int(mc['p90_end_stock'])} units</span></div>"
#                 f"</div>",
#                 unsafe_allow_html=True,
#             )
#         with mc_col3:
#             if mc["avg_breach_month"]:
#                 st.markdown(
#                     f"<div class='sc' style='flex-direction:column;align-items:center;padding:16px;'>"
#                     f"<div style='font-size:28px;font-weight:900;color:#EF4444;'>M{mc['avg_breach_month']}</div>"
#                     f"<div style='font-size:11px;color:var(--t3);text-align:center;'>Average month when<br>stockout occurs</div>"
#                     f"<div style='font-size:10px;color:var(--t3);margin-top:4px;'>Based on breach scenarios</div>"
#                     f"</div>",
#                     unsafe_allow_html=True,
#                 )
#             else:
#                 st.markdown(
#                     f"<div class='sc' style='flex-direction:column;align-items:center;padding:16px;'>"
#                     f"<div style='font-size:28px;font-weight:900;color:#22C55E;'>✓</div>"
#                     f"<div style='font-size:11px;color:var(--t3);text-align:center;'>No stockout in most<br>simulated scenarios</div>"
#                     f"</div>",
#                     unsafe_allow_html=True,
#                 )

#         # Distribution chart
#         if mc["end_stock_distribution"]:
#             dist   = mc["end_stock_distribution"]
#             fig_mc = go.Figure()
#             fig_mc.add_trace(go.Histogram(x=dist, nbinsx=20, name="End Stock",
#                                           marker_color=ORANGE, marker_line_width=0, opacity=0.7))
#             if ss_v > 0:
#                 fig_mc.add_vline(x=ss_v, line_color="#EF4444", line_dash="dot", line_width=1.5,
#                                  annotation_text=f"Safety Stock {round(ss_v)}",
#                                  annotation_font_color="#EF4444", annotation_font_size=9)
#             ct(fig_mc, 180)
#             fig_mc.update_layout(showlegend=False, xaxis_title="End Stock (units)", yaxis_title="Frequency",
#                                  margin=dict(l=8, r=8, t=16, b=8))
#             st.plotly_chart(fig_mc, use_container_width=True)

#         # Monte Carlo explanation (bullet list in note box)
#         st.markdown("""
#         <div class='note-box'>
#         <p style='margin:0 0 8px 0; font-weight:700;'>📊 What is Monte Carlo simulation?</p>
#         <ul style='margin:0; padding-left:20px;'>
#         <li>Runs 1,000 possible future demand scenarios based on historical mean and standard deviation.</li>
#         <li>The <strong>probability of stockout</strong> shows the percentage of scenarios where stock falls below safety stock in the next 6 months.</li>
#         <li>The <strong>outcome range</strong> (P10, P50, P90) shows possible ending stock levels under pessimistic, median, and optimistic conditions.</li>
#         <li>The <strong>histogram</strong> visualises the distribution of possible ending stock levels.</li>
#         </ul>
#         </div>
#         """, unsafe_allow_html=True)

#     # ── Stock Trajectory ──────────────────────────────────────────────────────
#     sec("Stock Trajectory")
#     note("Stock from Inventory extract. Demand from Sales file (includes write-offs, internal consumption). "
#          "Safety Stock from Material Master. Lead time max(Planned Delivery, Inhouse Production).")

#     month_filter = st.slider("Show last N months", 6, 60, 25, step=1, key="mi_months")
#     sh = get_stock_history(data, sel_mat).tail(month_filter)
#     dh = get_demand_history(data, sel_mat).tail(month_filter)

#     fig = go.Figure()
#     fig.add_trace(go.Scatter(x=sh["label"], y=sh["Gross Stock"], mode="lines+markers", name="Stock",
#                              line=dict(color=ORANGE, width=2.5), marker=dict(size=4, color=ORANGE),
#                              fill="tozeroy", fillcolor="rgba(244,123,37,0.07)", yaxis="y1",
#                              hovertemplate="<b>%{x}</b><br>Stock: %{y} units<extra></extra>"))
#     if ss_v > 0:
#         fig.add_trace(go.Scatter(x=sh["label"], y=[ss_v] * len(sh), mode="lines",
#                                  name=f"SAP SS ({round(ss_v)})", yaxis="y1",
#                                  line=dict(color="#EF4444", width=1.5, dash="dot")))
#     if rec > ss_v:
#         fig.add_trace(go.Scatter(x=sh["label"], y=[rec] * len(sh), mode="lines",
#                                  name=f"ARIA SS ({round(rec)})", yaxis="y1",
#                                  line=dict(color="#22C55E", width=1.5, dash="dash")))
#     if len(dh) > 0:
#         dh_aligned = dh[dh.label.isin(sh["label"].tolist())]
#         if len(dh_aligned) > 0:
#             fig.add_trace(go.Bar(x=dh_aligned["label"], y=dh_aligned["demand"], name="Demand/mo",
#                                  marker_color="rgba(148,163,184,0.3)", marker_line_width=0, yaxis="y2",
#                                  hovertemplate="<b>%{x}</b><br>Demand: %{y} units<extra></extra>"))
#     ct(fig, 320)
#     fig.update_layout(
#         yaxis=dict(title="Stock (units)", gridcolor="#F0F4F9"),
#         yaxis2=dict(title="Demand/mo", overlaying="y", side="right", showgrid=False),
#         xaxis=dict(tickangle=-35), margin=dict(l=8, r=50, t=32, b=8),
#     )
#     st.plotly_chart(fig, use_container_width=True)

#     # ── Safety Stock Audit (with cost impact) ─────────────────────────────────
#     ss_col, repl_col = st.columns(2)
#     with ss_col:
#         sec("Safety Stock Audit")
#         note("SAP SS: Material Master → Safety Stock column. "
#              "ARIA SS: 1.65 × σ_demand × √(lead_time/30) at 95% service level. "
#              "Current Inventory SS = 0 for all SKUs (known data gap).")
#         gap = rec - ss_v
#         gp  = (gap / ss_v * 100) if ss_v > 0 else 100
#         if gap > 10:
#             gi, gc, gm = "⚠", "#F59E0B", f"SAP SS of {round(ss_v)} is {round(gp)}% below ARIA recommended {round(rec)}."
#         else:
#             gi, gc, gm = "✓", "#22C55E", f"SAP SS of {round(ss_v)} is adequately calibrated."
#         st.markdown(
#             f"<div class='sc' style='flex-direction:column;align-items:stretch;gap:0;'>"
#             f"<div style='display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:10px;'>"
#             f"<div><div style='font-size:9px;color:var(--t3);text-transform:uppercase;letter-spacing:0.8px;'>SAP SS (Material Master)</div>"
#             f"<div style='font-size:20px;font-weight:900;color:var(--rd);'>{round(ss_v)}</div></div>"
#             f"<div><div style='font-size:9px;color:var(--t3);text-transform:uppercase;letter-spacing:0.8px;'>ARIA Recommended (95% SL)</div>"
#             f"<div style='font-size:20px;font-weight:900;color:var(--gr);'>{round(rec)}</div></div></div>"
#             f"<div style='background:var(--s3);border-radius:8px;padding:8px 10px;font-size:11px;color:var(--t2);'>"
#             f"<span style='color:{gc};font-weight:700;'>{gi} </span>{gm}</div>"
#             f"</div>",
#             unsafe_allow_html=True,
#         )

#         # ── Inventory cost impact (Fix #8) ────────────────────────────────────
#         unit_price = mat_row.get("unit_price", 0)
#         if unit_price > 0:
#             current_inv_value = mat_row["sih"] * unit_price
#             rec_inv_value = rec * unit_price
#             diff_value = (rec - ss_v) * unit_price
#             if diff_value > 0:
#                 cost_text = f"⚠️ **Additional investment required:** Following ARIA recommendation would increase inventory holding cost by **${diff_value:,.0f}** (from ${current_inv_value:,.0f} to ${rec_inv_value:,.0f})."
#             elif diff_value < 0:
#                 cost_text = f"✅ **Potential savings:** Following ARIA recommendation could reduce inventory holding cost by **${-diff_value:,.0f}** (from ${current_inv_value:,.0f} to ${rec_inv_value:,.0f})."
#             else:
#                 cost_text = f"ℹ️ No change in inventory holding cost (${current_inv_value:,.0f})."
#             st.markdown(f"<div class='note-box' style='margin-top:10px;'>{cost_text}</div>", unsafe_allow_html=True)
#         # ───────────────────────────────────────────────────────────────────────

#         if st.session_state.azure_client and analysis:
#             if st.button("◈ Explain ARIA SS Recommendation", key="ss_rec"):
#                 with st.spinner("ARIA analysing safety stock…"):
#                     ss_ctx = (f"Material: {sel_name}, SAP SS: {ss_v:.0f}, ARIA SS: {rec:.0f}, "
#                               f"Lead time: {lt_v:.0f}d, Avg demand: {avg_d:.0f}/mo, Std: {std_d:.0f}, "
#                               f"Current stock: {mat_row['sih']:.0f}, Breach count: {mat_row['breach_count']}, "
#                               f"Monte Carlo breach probability: "
#                               f"{run_monte_carlo(mat_row['sih'], ss_v, avg_d, std_d, lt_v)['probability_breach_pct']}%")
#                     rec_txt = chat_with_data(
#                         st.session_state.azure_client, AZURE_DEPLOYMENT,
#                         f"Explain why the recommended safety stock for {sel_name} is {rec:.0f} units, based on the formula 1.65 × σ_demand × √(lead_time/30). Justify this value with the data provided.",
#                         ss_ctx,
#                     )
#                 st.markdown(
#                     f"<div class='ic' style='margin-top:8px;'><div class='il'>◈ ARIA SS Explanation</div>"
#                     f"<div class='ib' style='margin-top:4px;'>{rec_txt}</div></div>",
#                     unsafe_allow_html=True,
#                 )

#     with repl_col:
#         sec("Replenishment Details")
#         repl_t = mat_row["repl_triggered"]
#         repl_q = int(mat_row["repl_quantity"])
#         repl_s = int(mat_row["repl_shortfall"])
#         repl_f = mat_row["repl_formula"]
#         if repl_t:
#             st.markdown(
#                 f"<div style='background:#FEF2F2;border:1px solid rgba(239,68,68,0.2);"
#                 f"border-left:3px solid #EF4444;border-radius:var(--r);padding:12px 14px;'>"
#                 f"<div style='font-size:10px;font-weight:800;color:#EF4444;margin-bottom:6px;'>IMMEDIATE ORDER REQUIRED</div>"
#                 f"<table style='font-size:11px;width:100%;border-collapse:collapse;'>"
#                 f"<tr><td style='color:#475569;padding:2px 0;'>Stock-in-Hand</td><td style='font-weight:700;text-align:right;'>{round(mat_row['sih'])} units</td></tr>"
#                 f"<tr><td style='color:#475569;padding:2px 0;'>Safety Stock (MM)</td><td style='font-weight:700;text-align:right;'>{round(ss_v)} units</td></tr>"
#                 f"<tr><td style='color:#475569;padding:2px 0;'>Shortfall</td><td style='font-weight:700;color:#EF4444;text-align:right;'>{repl_s} units</td></tr>"
#                 f"<tr><td style='color:#475569;padding:2px 0;'>Lead Time (MM)</td><td style='font-weight:700;text-align:right;'>{round(lt_v)}d</td></tr>"
#                 f"<tr><td style='color:#475569;padding:2px 0;'>Lot Size (Curr Inv)</td><td style='font-weight:700;text-align:right;'>{round(mat_row['lot_size'])} units</td></tr>"
#                 f"<tr style='border-top:1px solid #E2E8F0;'><td style='color:#EF4444;font-weight:800;padding:4px 0;'>Order Quantity</td><td style='font-weight:900;font-size:15px;color:#EF4444;text-align:right;'>{repl_q} units</td></tr>"
#                 f"<tr><td colspan='2' style='font-size:9px;color:#94A3B8;padding-top:3px;'>{repl_f}</td></tr>"
#                 f"</table></div>",
#                 unsafe_allow_html=True,
#             )
#         else:
#             st.markdown(
#                 f"<div style='background:#F0FDF4;border:1px solid rgba(34,197,94,0.2);"
#                 f"border-radius:var(--r);padding:12px 14px;font-size:12px;color:#14532d;'>"
#                 f"✓ No replenishment triggered — stock above safety stock.<br>"
#                 f"<span style='font-size:10px;color:#94A3B8;'>SIH={round(mat_row['sih'])} | SS={round(ss_v)}</span>"
#                 f"</div>",
#                 unsafe_allow_html=True,
#             )

#     # ── BOM Components ─────────────────────────────────────────────────────────
#     bom = get_bom_components(data, sel_mat)
#     if len(bom) > 0:
#         sec("BOM Components &amp; Supplier Intelligence")
#         lvl = bom[bom["Level"].str.contains("Level 03|Level 02|Level 1", na=False, regex=True)]
#         if len(lvl) > 0:
#             bom_display = []
#             for _, b in lvl.iterrows():
#                 fq  = ("✓ Fixed=1" if b.get("Fixed Qty Flag", False)
#                        else str(round(float(b["Comp. Qty (CUn)"]), 3)) if pd.notna(b["Comp. Qty (CUn)"]) else "—")
#                 sup = b.get("Supplier Display", "—")
#                 loc = b.get("Supplier Location", "—")
#                 transit = b.get("Transit Days", None)
#                 bom_display.append({
#                     "Material": str(b["Material"]),
#                     "Description": str(b["Material Description"])[:36] if pd.notna(b["Material Description"]) else "—",
#                     "Qty": fq, "Unit": str(b["Component unit"]) if pd.notna(b["Component unit"]) else "—",
#                     "Procurement": b.get("Procurement Label", "—"),
#                     "Supplier": sup, "Location": loc,
#                     "Transit": f"{transit}d" if transit is not None else "—",
#                 })
#             df_bom_disp = pd.DataFrame(bom_display)
#             sup_r2 = JsCode("""class R{init(p){const v=p.value||'';this.e=document.createElement('span');if(v.startsWith('⚠')){this.e.style.cssText='background:#FEF3C7;color:#F59E0B;padding:2px 6px;border-radius:4px;font-size:10px;font-weight:600;';this.e.innerText=v;}else if(v==='Revvity Inhouse'){this.e.style.cssText='background:#DCFCE7;color:#16a34a;padding:2px 6px;border-radius:4px;font-size:10px;';this.e.innerText=v;}else{this.e.style.cssText='background:#EFF6FF;color:#2563EB;padding:2px 6px;border-radius:4px;font-size:10px;';this.e.innerText=v;};}getGui(){return this.e;}}""")
#             gb3 = GridOptionsBuilder.from_dataframe(df_bom_disp)
#             gb3.configure_column("Material",    width=85)
#             gb3.configure_column("Description", width=220)
#             gb3.configure_column("Qty",         width=78)
#             gb3.configure_column("Unit",        width=52)
#             gb3.configure_column("Procurement", width=110)
#             gb3.configure_column("Supplier",    width=175, cellRenderer=sup_r2)
#             gb3.configure_column("Location",    width=130)
#             gb3.configure_column("Transit",     width=62)
#             gb3.configure_grid_options(rowHeight=36, headerHeight=32)
#             gb3.configure_default_column(resizable=True, sortable=True, filter=False)
#             AgGrid(df_bom_disp, gridOptions=gb3.build(), height=290,
#                    allow_unsafe_jscode=True, theme="alpine", custom_css=_AGGRID_CSS)

#             # Supplier email draft
#             if st.session_state.azure_client:
#                 external_suppliers = []
#                 for _, b in lvl.iterrows():
#                     sup_raw = b.get("Supplier Name(Vendor)", "")
#                     if pd.notna(sup_raw) and str(sup_raw).strip() and b.get("Procurement Label", "") == "External":
#                         email_raw = b.get("Supplier Email address(Vendor)", "")
#                         email     = str(email_raw) if pd.notna(email_raw) else "—"
#                         if mat_row["repl_triggered"]:
#                             if not any(s["supplier"] == str(sup_raw).strip() for s in external_suppliers):
#                                 external_suppliers.append({"supplier": str(sup_raw).strip(), "email": email})

#                 if external_suppliers and st.button("📧 Draft Supplier Order Emails", key="email_btn"):
#                     for sup_info in external_suppliers[:3]:
#                         with st.spinner(f"Drafting email to {sup_info['supplier']}…"):
#                             email_txt = draft_supplier_email(
#                                 st.session_state.azure_client, AZURE_DEPLOYMENT,
#                                 sup_info["supplier"], sup_info["email"],
#                                 [{"name": sel_name, "quantity": mat_row["repl_quantity"], "lot_size": mat_row["lot_size"]}],
#                             )
#                         st.markdown(
#                             f"<div style='background:#EFF6FF;border:1px solid #BFDBFE;border-radius:var(--r);"
#                             f"padding:12px 14px;margin-top:8px;'>"
#                             f"<div style='font-size:10px;font-weight:700;color:#1d4ed8;margin-bottom:4px;'>"
#                             f"📧 Draft email to {sup_info['supplier']} ({sup_info['email']})</div>"
#                             f"<pre style='font-size:11px;white-space:pre-wrap;color:#1e293b;margin:0;'>{email_txt}</pre>"
#                             f"</div>",
#                             unsafe_allow_html=True,
#                         )

#     # ── Supplier Consolidation (Fix #6: add source note) ──────────────────────
#     consol   = get_supplier_consolidation(data, summary)
#     relevant = consol[
#         consol.material_list.apply(lambda x: sel_mat in x)
#         & (consol.finished_goods_supplied > 1)
#     ]
#     if len(relevant) > 0:
#         sec("Supplier Consolidation Opportunities")
#         note("Data source: BOM file (Supplier Name column).")
#         note("These suppliers also supply other finished goods. If ordering from them for this material, consider consolidating orders.")
#         for _, r in relevant.iterrows():
#             other_mats  = [m for m in r["material_list"] if m != sel_mat]
#             other_names = [MATERIAL_LABELS.get(m, m)[:20] for m in other_mats]
#             needs_order = r["consolidation_opportunity"]
#             bc          = "#22C55E" if not needs_order else "#F47B25"
#             st.markdown(
#                 f"<div class='prow'><div style='font-size:14px;'>🏭</div>"
#                 f"<div style='flex:1;'>"
#                 f"<div style='font-size:12px;font-weight:800;color:var(--t);'>{r['supplier']}</div>"
#                 f"<div style='font-size:10px;color:var(--t3);'>{r['city']} · {r['email']}</div>"
#                 f"<div style='font-size:10px;color:var(--t2);margin-top:2px;'>Also supplies: {', '.join(other_names[:4])}</div>"
#                 f"</div>"
#                 f"<div style='font-size:10px;font-weight:700;color:{bc};text-align:right;'>"
#                 f"{'⚡ Consolidation opportunity' if needs_order else 'No other orders needed'}"
#                 f"</div></div>",
#                 unsafe_allow_html=True,
#             )

#     st.markdown('<div class="pfooter">🔬 Powered by <strong>MResult</strong></div>', unsafe_allow_html=True)


# # # # # """
# # # # # tabs/material_intelligence.py
# # # # # Material Intelligence tab: agentic analysis, Monte Carlo simulation,
# # # # # stock trajectory, safety stock audit, BOM components, supplier email draft,
# # # # # and consolidation opportunities.
# # # # # """

# # # # # import streamlit as st
# # # # # import pandas as pd
# # # # # import plotly.graph_objects as go
# # # # # from st_aggrid import AgGrid, GridOptionsBuilder, JsCode

# # # # # from utils.helpers import ct, fmt_p, sbadge, sec, note, ORANGE, AZURE_DEPLOYMENT
# # # # # from data_loader import (
# # # # #     get_stock_history, get_demand_history, get_bom_components,
# # # # #     get_material_context, get_supplier_consolidation,
# # # # # )
# # # # # from agent import analyse_material, chat_with_data, run_monte_carlo, draft_supplier_email

# # # # # _AGGRID_CSS = {
# # # # #     ".ag-root-wrapper": {"border": "1px solid #E2E8F0!important", "border-radius": "12px!important"},
# # # # #     ".ag-header":       {"background": "#F8FAFE!important"},
# # # # #     ".ag-row-even":     {"background": "#FFFFFF!important"},
# # # # #     ".ag-row-odd":      {"background": "#F8FAFE!important"},
# # # # # }


# # # # # def render():
# # # # #     data           = st.session_state.data
# # # # #     summary        = st.session_state.summary
# # # # #     MATERIAL_LABELS = st.session_state.material_labels

# # # # #     mat_opts = {row["name"]: row["material"] for _, row in summary.iterrows()}
# # # # #     sel_name = st.selectbox("Select Material", list(mat_opts.keys()), key="mi_mat",
# # # # #                             help="Select a finished good to analyse")
# # # # #     sel_mat  = mat_opts[sel_name]
# # # # #     mat_row  = summary[summary.material == sel_mat].iloc[0]
# # # # #     risk     = mat_row["risk"]

# # # # #     # ── Insufficient data guard ───────────────────────────────────────────────
# # # # #     if risk == "INSUFFICIENT_DATA":
# # # # #         reasons = []
# # # # #         if mat_row["nonzero_demand_months"] < 3:
# # # # #             reasons.append(f"Only {mat_row['nonzero_demand_months']} months demand (min 6)")
# # # # #         if mat_row["zero_periods"] > 10:
# # # # #             reasons.append(f"Zero stock in {mat_row['zero_periods']}/{mat_row['total_periods']} periods")
# # # # #         if sel_mat == "3515-0010":
# # # # #             reasons.append("Marked inactive in sales history")
# # # # #         r_html = "".join(f'<div style="font-size:11px;color:var(--t3);margin:3px 0;">• {r}</div>' for r in reasons)
# # # # #         st.markdown(
# # # # #             f"<div style='display:flex;align-items:center;gap:12px;margin-bottom:16px;'>"
# # # # #             f"<div style='font-size:18px;font-weight:800;'>{sel_name}</div>{sbadge(risk)}</div>"
# # # # #             f"<div class='flag-box' style='max-width:520px;'>"
# # # # #             f"<div style='font-size:22px;margin-bottom:8px;'>◌</div>"
# # # # #             f"<div style='font-size:14px;font-weight:800;color:var(--t2);margin-bottom:5px;'>Insufficient Data for ARIA Analysis</div>"
# # # # #             f"<div style='font-size:12px;color:var(--t3);margin-bottom:8px;'>Requires 6+ months confirmed demand history.</div>"
# # # # #             f"{r_html}</div>",
# # # # #             unsafe_allow_html=True,
# # # # #         )
# # # # #         st.stop()

# # # # #     # ── Header ────────────────────────────────────────────────────────────────
# # # # #     h1c, h2c = st.columns([5, 1])
# # # # #     with h1c:
# # # # #         dq_flags   = mat_row.get("data_quality_flags", [])
# # # # #         flags_html = "".join(
# # # # #             f'<span class="chip" style="margin-right:4px;color:#F59E0B;border-color:#F59E0B40;">⚠ {f}</span>'
# # # # #             for f in dq_flags[:2]
# # # # #         ) if dq_flags else ""
# # # # #         st.markdown(
# # # # #             f"<div style='display:flex;align-items:center;flex-wrap:wrap;gap:8px;margin-bottom:6px;'>"
# # # # #             f"<div style='font-size:18px;font-weight:900;'>{sel_name}</div>"
# # # # #             f"{sbadge(risk)}<div class='chip'>{sel_mat}</div>{flags_html}</div>",
# # # # #             unsafe_allow_html=True,
# # # # #         )
# # # # #     with h2c:
# # # # #         run_an = st.button("◈ Analyse", use_container_width=True, key=f"analyse_btn_{sel_mat}")

# # # # #     # ── ARIA Analysis ─────────────────────────────────────────────────────────
# # # # #     analysis = st.session_state.agent_cache.get(sel_mat)
# # # # #     if run_an:
# # # # #         if st.session_state.azure_client:
# # # # #             with st.spinner("ARIA investigating…"):
# # # # #                 ctx      = get_material_context(data, sel_mat, summary)
# # # # #                 analysis = analyse_material(st.session_state.azure_client, AZURE_DEPLOYMENT, ctx)
# # # # #                 st.session_state.agent_cache[sel_mat]  = analysis
# # # # #                 st.session_state.last_analysed_mat     = sel_mat
# # # # #         else:
# # # # #             st.markdown(
# # # # #                 "<div style='padding:9px 12px;background:var(--ob);border:1px solid var(--obr);"
# # # # #                 "border-radius:9px;font-size:12px;color:var(--or);'>"
# # # # #                 "Enter Azure API key in sidebar to enable ARIA analysis.</div>",
# # # # #                 unsafe_allow_html=True,
# # # # #             )

# # # # #     if analysis and st.session_state.agent_cache.get(sel_mat):
# # # # #         key_findings = analysis.get("key_findings", [])
# # # # #         if not isinstance(key_findings, list):
# # # # #             key_findings = [str(key_findings)]
# # # # #         else:
# # # # #             key_findings = [str(f) for f in key_findings]
# # # # #         fh = "".join(f'<div class="iff"><div class="ifd"></div><div>{f}</div></div>' for f in key_findings)

# # # # #         conf       = str(analysis.get("data_confidence", "MEDIUM"))
# # # # #         conf_clean = conf.split("—")[0].split("-")[0].strip().upper()[:6]
# # # # #         cc         = "#22C55E" if "HIGH" in conf_clean else "#F59E0B" if "MEDIUM" in conf_clean else "#EF4444"

# # # # #         dq      = analysis.get("data_quality_flags", [])
# # # # #         dq_html = (
# # # # #             "<div style='margin-top:10px;padding-top:8px;border-top:1px solid var(--bl);'>"
# # # # #             + "".join(f'<div style="font-size:10px;color:#F59E0B;margin:2px 0;">⚠ {f}</div>' for f in dq)
# # # # #             + "</div>"
# # # # #         ) if dq else ""

# # # # #         st.markdown(
# # # # #             f"<div class='ic'><div class='il'>◈ ARIA Intelligence</div>"
# # # # #             f"<div class='ih'>{analysis.get('headline', '')}</div>"
# # # # #             f"<div class='ib'>{analysis.get('executive_summary', '')}</div>"
# # # # #             f"<div style='margin-top:10px;border-top:1px solid var(--bl);padding-top:10px;'>"
# # # # #             f"<div style='font-size:9px;font-weight:700;color:var(--or);text-transform:uppercase;letter-spacing:1px;margin-bottom:6px;'>Key Findings</div>"
# # # # #             f"{fh}{dq_html}</div>"
# # # # #             f"<div style='margin-top:8px;font-size:10px;color:var(--t3);'>"
# # # # #             f"Confidence: <span style='color:{cc};font-weight:700;'>{conf_clean}</span>"
# # # # #             f"</div></div>",
# # # # #             unsafe_allow_html=True,
# # # # #         )

# # # # #         ca, cb = st.columns(2)
# # # # #         sap_gap = analysis.get("sap_gap", "")
# # # # #         if not isinstance(sap_gap, str):
# # # # #             sap_gap = str(sap_gap)
# # # # #         recom = analysis.get("recommendation", "")
# # # # #         if not isinstance(recom, str):
# # # # #             recom = str(recom)

# # # # #         if "Unable to parse" in sap_gap:
# # # # #             sap_gap = (f"SAP Safety Stock: {mat_row['safety_stock']:.0f} units. "
# # # # #                        f"ARIA recommends: {mat_row['rec_safety_stock']:.0f} units. "
# # # # #                        f"Gap: {mat_row['rec_safety_stock'] - mat_row['safety_stock']:.0f} units.")
# # # # #         if "No replenishment triggered" in recom and mat_row["repl_triggered"]:
# # # # #             recom = (f"Order {int(mat_row['repl_quantity'])} units immediately. "
# # # # #                      f"Stock-in-Hand ({mat_row['sih']:.0f}) below SAP SS ({mat_row['safety_stock']:.0f}). "
# # # # #                      f"Lead time: {mat_row['lead_time']:.0f}d. Formula: {mat_row['repl_formula']}")
# # # # #         with ca:
# # # # #             st.markdown(f"<div class='sap-box'><div class='sap-lbl'>SAP Gap Assessment</div>{sap_gap}</div>", unsafe_allow_html=True)
# # # # #         with cb:
# # # # #             st.markdown(
# # # # #                 f"<div class='rec-box'><div class='rec-lbl'>ARIA Recommendation</div>"
# # # # #                 f"<pre style='font-size:11px;white-space:pre-wrap;margin:0;color:#14532d;'>{recom}</pre>"
# # # # #                 f"<div style='margin-top:5px;font-size:10px;opacity:0.75;'>If ignored: {analysis.get('risk_if_ignored', '')}</div></div>",
# # # # #                 unsafe_allow_html=True,
# # # # #             )

# # # # #         sup_action = analysis.get("supplier_action")
# # # # #         if sup_action:
# # # # #             st.markdown(
# # # # #                 f"<div style='padding:8px 12px;background:rgba(59,130,246,0.06);"
# # # # #                 f"border:1px solid rgba(59,130,246,0.2);border-radius:8px;font-size:11px;color:#1d4ed8;margin-top:8px;'>"
# # # # #                 f"📧 <strong>Supplier Action:</strong> {sup_action}</div>",
# # # # #                 unsafe_allow_html=True,
# # # # #             )
# # # # #     elif not run_an:
# # # # #         st.markdown(
# # # # #             "<div style='padding:12px 14px;background:var(--s2);border:1px solid var(--bl);"
# # # # #             "border-radius:var(--r);font-size:12px;color:var(--t3);text-align:center;'>"
# # # # #             "Click <strong style='color:var(--or);'>◈ Analyse</strong> above to run ARIA intelligence on this material.</div>",
# # # # #             unsafe_allow_html=True,
# # # # #         )

# # # # #     # ── Monte Carlo ───────────────────────────────────────────────────────────
# # # # #     sec("Monte Carlo Risk Simulation — 1,000 Demand Scenarios")
# # # # #     note("Runs 1,000 simulations of 6-month demand using historical mean & std deviation. "
# # # # #          "Shows probability of stockout and range of outcomes.")
# # # # #     avg_d = mat_row["avg_monthly_demand"]
# # # # #     std_d = mat_row["std_demand"]
# # # # #     ss_v  = mat_row["safety_stock"]
# # # # #     rec   = mat_row["rec_safety_stock"]
# # # # #     lt_v  = mat_row["lead_time"]

# # # # #     if avg_d > 0 and std_d > 0:
# # # # #         mc = run_monte_carlo(mat_row["sih"], ss_v, avg_d, std_d, lt_v, months=6, n_sims=1000)
# # # # #         risk_color = {"HIGH RISK": "#EF4444", "MODERATE RISK": "#F59E0B",
# # # # #                       "LOW RISK": "#22C55E", "VERY LOW RISK": "#22C55E"}.get(mc["verdict"], ORANGE)

# # # # #         mc_col1, mc_col2, mc_col3 = st.columns(3)
# # # # #         with mc_col1:
# # # # #             st.markdown(
# # # # #                 f"<div class='sc' style='flex-direction:column;align-items:center;padding:16px;'>"
# # # # #                 f"<div style='font-size:28px;font-weight:900;color:{risk_color};'>{mc['probability_breach_pct']}%</div>"
# # # # #                 f"<div style='font-size:11px;color:var(--t3);text-align:center;'>Probability of stockout<br>in next 6 months</div>"
# # # # #                 f"<div style='font-size:12px;font-weight:700;color:{risk_color};margin-top:4px;'>{mc['verdict']}</div>"
# # # # #                 f"</div>",
# # # # #                 unsafe_allow_html=True,
# # # # #             )
# # # # #         with mc_col2:
# # # # #             st.markdown(
# # # # #                 f"<div class='sc' style='flex-direction:column;gap:0;'>"
# # # # #                 f"<div style='font-size:10px;color:var(--t3);margin-bottom:8px;font-weight:600;'>OUTCOME RANGE (6mo)</div>"
# # # # #                 f"<div style='display:flex;justify-content:space-between;margin-bottom:4px;'>"
# # # # #                 f"<span style='font-size:10px;color:var(--t3);'>Pessimistic (P10)</span>"
# # # # #                 f"<span style='font-size:12px;font-weight:700;color:#EF4444;'>{int(mc['p10_end_stock'])} units</span></div>"
# # # # #                 f"<div style='display:flex;justify-content:space-between;margin-bottom:4px;'>"
# # # # #                 f"<span style='font-size:10px;color:var(--t3);'>Median (P50)</span>"
# # # # #                 f"<span style='font-size:12px;font-weight:700;color:{ORANGE};'>{int(mc['p50_end_stock'])} units</span></div>"
# # # # #                 f"<div style='display:flex;justify-content:space-between;'>"
# # # # #                 f"<span style='font-size:10px;color:var(--t3);'>Optimistic (P90)</span>"
# # # # #                 f"<span style='font-size:12px;font-weight:700;color:#22C55E;'>{int(mc['p90_end_stock'])} units</span></div>"
# # # # #                 f"</div>",
# # # # #                 unsafe_allow_html=True,
# # # # #             )
# # # # #         with mc_col3:
# # # # #             if mc["avg_breach_month"]:
# # # # #                 st.markdown(
# # # # #                     f"<div class='sc' style='flex-direction:column;align-items:center;padding:16px;'>"
# # # # #                     f"<div style='font-size:28px;font-weight:900;color:#EF4444;'>M{mc['avg_breach_month']}</div>"
# # # # #                     f"<div style='font-size:11px;color:var(--t3);text-align:center;'>Average month when<br>stockout occurs</div>"
# # # # #                     f"<div style='font-size:10px;color:var(--t3);margin-top:4px;'>Based on breach scenarios</div>"
# # # # #                     f"</div>",
# # # # #                     unsafe_allow_html=True,
# # # # #                 )
# # # # #             else:
# # # # #                 st.markdown(
# # # # #                     f"<div class='sc' style='flex-direction:column;align-items:center;padding:16px;'>"
# # # # #                     f"<div style='font-size:28px;font-weight:900;color:#22C55E;'>✓</div>"
# # # # #                     f"<div style='font-size:11px;color:var(--t3);text-align:center;'>No stockout in most<br>simulated scenarios</div>"
# # # # #                     f"</div>",
# # # # #                     unsafe_allow_html=True,
# # # # #                 )

# # # # #         if mc["end_stock_distribution"]:
# # # # #             dist   = mc["end_stock_distribution"]
# # # # #             fig_mc = go.Figure()
# # # # #             fig_mc.add_trace(go.Histogram(x=dist, nbinsx=20, name="End Stock",
# # # # #                                           marker_color=ORANGE, marker_line_width=0, opacity=0.7))
# # # # #             if ss_v > 0:
# # # # #                 fig_mc.add_vline(x=ss_v, line_color="#EF4444", line_dash="dot", line_width=1.5,
# # # # #                                  annotation_text=f"Safety Stock {round(ss_v)}",
# # # # #                                  annotation_font_color="#EF4444", annotation_font_size=9)
# # # # #             ct(fig_mc, 180)
# # # # #             fig_mc.update_layout(showlegend=False, xaxis_title="End Stock (units)", yaxis_title="Frequency",
# # # # #                                  margin=dict(l=8, r=8, t=16, b=8))
# # # # #             st.plotly_chart(fig_mc, use_container_width=True)

# # # # #     # ── Stock Trajectory ──────────────────────────────────────────────────────
# # # # #     sec("Stock Trajectory")
# # # # #     note("Stock from Inventory extract. Demand from Sales file (includes write-offs, internal consumption). "
# # # # #          "Safety Stock from Material Master. Lead time max(Planned Delivery, Inhouse Production).")

# # # # #     month_filter = st.slider("Show last N months", 6, 60, 25, step=1, key="mi_months")
# # # # #     sh = get_stock_history(data, sel_mat).tail(month_filter)
# # # # #     dh = get_demand_history(data, sel_mat).tail(month_filter)

# # # # #     fig = go.Figure()
# # # # #     fig.add_trace(go.Scatter(x=sh["label"], y=sh["Gross Stock"], mode="lines+markers", name="Stock",
# # # # #                              line=dict(color=ORANGE, width=2.5), marker=dict(size=4, color=ORANGE),
# # # # #                              fill="tozeroy", fillcolor="rgba(244,123,37,0.07)", yaxis="y1",
# # # # #                              hovertemplate="<b>%{x}</b><br>Stock: %{y} units<extra></extra>"))
# # # # #     if ss_v > 0:
# # # # #         fig.add_trace(go.Scatter(x=sh["label"], y=[ss_v] * len(sh), mode="lines",
# # # # #                                  name=f"SAP SS ({round(ss_v)})", yaxis="y1",
# # # # #                                  line=dict(color="#EF4444", width=1.5, dash="dot")))
# # # # #     if rec > ss_v:
# # # # #         fig.add_trace(go.Scatter(x=sh["label"], y=[rec] * len(sh), mode="lines",
# # # # #                                  name=f"ARIA SS ({round(rec)})", yaxis="y1",
# # # # #                                  line=dict(color="#22C55E", width=1.5, dash="dash")))
# # # # #     if len(dh) > 0:
# # # # #         dh_aligned = dh[dh.label.isin(sh["label"].tolist())]
# # # # #         if len(dh_aligned) > 0:
# # # # #             fig.add_trace(go.Bar(x=dh_aligned["label"], y=dh_aligned["demand"], name="Demand/mo",
# # # # #                                  marker_color="rgba(148,163,184,0.3)", marker_line_width=0, yaxis="y2",
# # # # #                                  hovertemplate="<b>%{x}</b><br>Demand: %{y} units<extra></extra>"))
# # # # #     ct(fig, 320)
# # # # #     fig.update_layout(
# # # # #         yaxis=dict(title="Stock (units)", gridcolor="#F0F4F9"),
# # # # #         yaxis2=dict(title="Demand/mo", overlaying="y", side="right", showgrid=False),
# # # # #         xaxis=dict(tickangle=-35), margin=dict(l=8, r=50, t=32, b=8),
# # # # #     )
# # # # #     st.plotly_chart(fig, use_container_width=True)

# # # # #     # ── Safety Stock Audit + Replenishment ────────────────────────────────────
# # # # #     ss_col, repl_col = st.columns(2)
# # # # #     with ss_col:
# # # # #         sec("Safety Stock Audit")
# # # # #         note("SAP SS: Material Master → Safety Stock column. "
# # # # #              "ARIA SS: 1.65 × σ_demand × √(lead_time/30) at 95% service level. "
# # # # #              "Current Inventory SS = 0 for all SKUs (known data gap).")
# # # # #         gap = rec - ss_v
# # # # #         gp  = (gap / ss_v * 100) if ss_v > 0 else 100
# # # # #         if gap > 10:
# # # # #             gi, gc, gm = "⚠", "#F59E0B", f"SAP SS of {round(ss_v)} is {round(gp)}% below ARIA recommended {round(rec)}."
# # # # #         else:
# # # # #             gi, gc, gm = "✓", "#22C55E", f"SAP SS of {round(ss_v)} is adequately calibrated."
# # # # #         st.markdown(
# # # # #             f"<div class='sc' style='flex-direction:column;align-items:stretch;gap:0;'>"
# # # # #             f"<div style='display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:10px;'>"
# # # # #             f"<div><div style='font-size:9px;color:var(--t3);text-transform:uppercase;letter-spacing:0.8px;'>SAP SS (Material Master)</div>"
# # # # #             f"<div style='font-size:20px;font-weight:900;color:var(--rd);'>{round(ss_v)}</div></div>"
# # # # #             f"<div><div style='font-size:9px;color:var(--t3);text-transform:uppercase;letter-spacing:0.8px;'>ARIA Recommended (95% SL)</div>"
# # # # #             f"<div style='font-size:20px;font-weight:900;color:var(--gr);'>{round(rec)}</div></div></div>"
# # # # #             f"<div style='background:var(--s3);border-radius:8px;padding:8px 10px;font-size:11px;color:var(--t2);'>"
# # # # #             f"<span style='color:{gc};font-weight:700;'>{gi} </span>{gm}</div>"
# # # # #             f"</div>",
# # # # #             unsafe_allow_html=True,
# # # # #         )

# # # # #         if st.session_state.azure_client and analysis:
# # # # #             if st.button("◈ Get SS Recommendation", key="ss_rec"):
# # # # #                 with st.spinner("ARIA analysing safety stock…"):
# # # # #                     ss_ctx  = (f"Material: {sel_name}, SAP SS: {ss_v:.0f}, ARIA SS: {rec:.0f}, "
# # # # #                                f"Lead time: {lt_v:.0f}d, Avg demand: {avg_d:.0f}/mo, Std: {std_d:.0f}, "
# # # # #                                f"Current stock: {mat_row['sih']:.0f}, Breach count: {mat_row['breach_count']}, "
# # # # #                                f"Monte Carlo breach probability: "
# # # # #                                f"{run_monte_carlo(mat_row['sih'], ss_v, avg_d, std_d, lt_v)['probability_breach_pct']}%")
# # # # #                     rec_txt = chat_with_data(
# # # # #                         st.session_state.azure_client, AZURE_DEPLOYMENT,
# # # # #                         "Should the safety stock be adjusted? Give a specific recommendation with reasoning and the recommended value.",
# # # # #                         ss_ctx,
# # # # #                     )
# # # # #                 st.markdown(
# # # # #                     f"<div class='ic' style='margin-top:8px;'><div class='il'>◈ SS Recommendation</div>"
# # # # #                     f"<div class='ib' style='margin-top:4px;'>{rec_txt}</div></div>",
# # # # #                     unsafe_allow_html=True,
# # # # #                 )

# # # # #     with repl_col:
# # # # #         sec("Replenishment Details")
# # # # #         repl_t = mat_row["repl_triggered"]
# # # # #         repl_q = int(mat_row["repl_quantity"])
# # # # #         repl_s = int(mat_row["repl_shortfall"])
# # # # #         repl_f = mat_row["repl_formula"]
# # # # #         if repl_t:
# # # # #             st.markdown(
# # # # #                 f"<div style='background:#FEF2F2;border:1px solid rgba(239,68,68,0.2);"
# # # # #                 f"border-left:3px solid #EF4444;border-radius:var(--r);padding:12px 14px;'>"
# # # # #                 f"<div style='font-size:10px;font-weight:800;color:#EF4444;margin-bottom:6px;'>IMMEDIATE ORDER REQUIRED</div>"
# # # # #                 f"<table style='font-size:11px;width:100%;border-collapse:collapse;'>"
# # # # #                 f"<tr><td style='color:#475569;padding:2px 0;'>Stock-in-Hand</td><td style='font-weight:700;text-align:right;'>{round(mat_row['sih'])} units</td></tr>"
# # # # #                 f"<tr><td style='color:#475569;padding:2px 0;'>Safety Stock (MM)</td><td style='font-weight:700;text-align:right;'>{round(ss_v)} units</td></tr>"
# # # # #                 f"<tr><td style='color:#475569;padding:2px 0;'>Shortfall</td><td style='font-weight:700;color:#EF4444;text-align:right;'>{repl_s} units</td></tr>"
# # # # #                 f"<tr><td style='color:#475569;padding:2px 0;'>Lead Time (MM)</td><td style='font-weight:700;text-align:right;'>{round(lt_v)}d</td></tr>"
# # # # #                 f"<tr><td style='color:#475569;padding:2px 0;'>Lot Size (Curr Inv)</td><td style='font-weight:700;text-align:right;'>{round(mat_row['lot_size'])} units</td></tr>"
# # # # #                 f"<tr style='border-top:1px solid #E2E8F0;'><td style='color:#EF4444;font-weight:800;padding:4px 0;'>Order Quantity</td><td style='font-weight:900;font-size:15px;color:#EF4444;text-align:right;'>{repl_q} units</td></tr>"
# # # # #                 f"<tr><td colspan='2' style='font-size:9px;color:#94A3B8;padding-top:3px;'>{repl_f}</td></tr>"
# # # # #                 f"</table></div>",
# # # # #                 unsafe_allow_html=True,
# # # # #             )
# # # # #         else:
# # # # #             st.markdown(
# # # # #                 f"<div style='background:#F0FDF4;border:1px solid rgba(34,197,94,0.2);"
# # # # #                 f"border-radius:var(--r);padding:12px 14px;font-size:12px;color:#14532d;'>"
# # # # #                 f"✓ No replenishment triggered — stock above safety stock.<br>"
# # # # #                 f"<span style='font-size:10px;color:#94A3B8;'>SIH={round(mat_row['sih'])} | SS={round(ss_v)}</span>"
# # # # #                 f"</div>",
# # # # #                 unsafe_allow_html=True,
# # # # #             )

# # # # #     # ── BOM Components ─────────────────────────────────────────────────────────
# # # # #     bom = get_bom_components(data, sel_mat)
# # # # #     if len(bom) > 0:
# # # # #         sec("BOM Components &amp; Supplier Intelligence")
# # # # #         lvl = bom[bom["Level"].str.contains("Level 03|Level 02|Level 1", na=False, regex=True)]
# # # # #         if len(lvl) > 0:
# # # # #             bom_display = []
# # # # #             for _, b in lvl.iterrows():
# # # # #                 fq  = ("✓ Fixed=1" if b.get("Fixed Qty Flag", False)
# # # # #                        else str(round(float(b["Comp. Qty (CUn)"]), 3)) if pd.notna(b["Comp. Qty (CUn)"]) else "—")
# # # # #                 sup = b.get("Supplier Display", "—")
# # # # #                 loc = b.get("Supplier Location", "—")
# # # # #                 transit = b.get("Transit Days", None)
# # # # #                 bom_display.append({
# # # # #                     "Material": str(b["Material"]),
# # # # #                     "Description": str(b["Material Description"])[:36] if pd.notna(b["Material Description"]) else "—",
# # # # #                     "Qty": fq, "Unit": str(b["Component unit"]) if pd.notna(b["Component unit"]) else "—",
# # # # #                     "Procurement": b.get("Procurement Label", "—"),
# # # # #                     "Supplier": sup, "Location": loc,
# # # # #                     "Transit": f"{transit}d" if transit is not None else "—",
# # # # #                 })
# # # # #             df_bom_disp = pd.DataFrame(bom_display)
# # # # #             sup_r2 = JsCode("""class R{init(p){const v=p.value||'';this.e=document.createElement('span');if(v.startsWith('⚠')){this.e.style.cssText='background:#FEF3C7;color:#F59E0B;padding:2px 6px;border-radius:4px;font-size:10px;font-weight:600;';this.e.innerText=v;}else if(v==='Revvity Inhouse'){this.e.style.cssText='background:#DCFCE7;color:#16a34a;padding:2px 6px;border-radius:4px;font-size:10px;';this.e.innerText=v;}else{this.e.style.cssText='background:#EFF6FF;color:#2563EB;padding:2px 6px;border-radius:4px;font-size:10px;';this.e.innerText=v;};}getGui(){return this.e;}}""")
# # # # #             gb3 = GridOptionsBuilder.from_dataframe(df_bom_disp)
# # # # #             gb3.configure_column("Material",    width=85)
# # # # #             gb3.configure_column("Description", width=220)
# # # # #             gb3.configure_column("Qty",         width=78)
# # # # #             gb3.configure_column("Unit",        width=52)
# # # # #             gb3.configure_column("Procurement", width=110)
# # # # #             gb3.configure_column("Supplier",    width=175, cellRenderer=sup_r2)
# # # # #             gb3.configure_column("Location",    width=130)
# # # # #             gb3.configure_column("Transit",     width=62)
# # # # #             gb3.configure_grid_options(rowHeight=36, headerHeight=32)
# # # # #             gb3.configure_default_column(resizable=True, sortable=True, filter=False)
# # # # #             AgGrid(df_bom_disp, gridOptions=gb3.build(), height=290,
# # # # #                    allow_unsafe_jscode=True, theme="alpine", custom_css=_AGGRID_CSS)

# # # # #             # Supplier email draft
# # # # #             if st.session_state.azure_client:
# # # # #                 external_suppliers = []
# # # # #                 for _, b in lvl.iterrows():
# # # # #                     sup_raw = b.get("Supplier Name(Vendor)", "")
# # # # #                     if pd.notna(sup_raw) and str(sup_raw).strip() and b.get("Procurement Label", "") == "External":
# # # # #                         email_raw = b.get("Supplier Email address(Vendor)", "")
# # # # #                         email     = str(email_raw) if pd.notna(email_raw) else "—"
# # # # #                         if mat_row["repl_triggered"]:
# # # # #                             if not any(s["supplier"] == str(sup_raw).strip() for s in external_suppliers):
# # # # #                                 external_suppliers.append({"supplier": str(sup_raw).strip(), "email": email})

# # # # #                 if external_suppliers and st.button("📧 Draft Supplier Order Emails", key="email_btn"):
# # # # #                     for sup_info in external_suppliers[:3]:
# # # # #                         with st.spinner(f"Drafting email to {sup_info['supplier']}…"):
# # # # #                             email_txt = draft_supplier_email(
# # # # #                                 st.session_state.azure_client, AZURE_DEPLOYMENT,
# # # # #                                 sup_info["supplier"], sup_info["email"],
# # # # #                                 [{"name": sel_name, "quantity": mat_row["repl_quantity"], "lot_size": mat_row["lot_size"]}],
# # # # #                             )
# # # # #                         st.markdown(
# # # # #                             f"<div style='background:#EFF6FF;border:1px solid #BFDBFE;border-radius:var(--r);"
# # # # #                             f"padding:12px 14px;margin-top:8px;'>"
# # # # #                             f"<div style='font-size:10px;font-weight:700;color:#1d4ed8;margin-bottom:4px;'>"
# # # # #                             f"📧 Draft email to {sup_info['supplier']} ({sup_info['email']})</div>"
# # # # #                             f"<pre style='font-size:11px;white-space:pre-wrap;color:#1e293b;margin:0;'>{email_txt}</pre>"
# # # # #                             f"</div>",
# # # # #                             unsafe_allow_html=True,
# # # # #                         )

# # # # #     # ── Supplier Consolidation ────────────────────────────────────────────────
# # # # #     consol   = get_supplier_consolidation(data, summary)
# # # # #     relevant = consol[
# # # # #         consol.material_list.apply(lambda x: sel_mat in x)
# # # # #         & (consol.finished_goods_supplied > 1)
# # # # #     ]
# # # # #     if len(relevant) > 0:
# # # # #         sec("Supplier Consolidation Opportunities")
# # # # #         note("These suppliers also supply other finished goods. If ordering from them for this material, consider consolidating orders.")
# # # # #         for _, r in relevant.iterrows():
# # # # #             other_mats  = [m for m in r["material_list"] if m != sel_mat]
# # # # #             other_names = [MATERIAL_LABELS.get(m, m)[:20] for m in other_mats]
# # # # #             needs_order = r["consolidation_opportunity"]
# # # # #             bc          = "#22C55E" if not needs_order else "#F47B25"
# # # # #             st.markdown(
# # # # #                 f"<div class='prow'><div style='font-size:14px;'>🏭</div>"
# # # # #                 f"<div style='flex:1;'>"
# # # # #                 f"<div style='font-size:12px;font-weight:800;color:var(--t);'>{r['supplier']}</div>"
# # # # #                 f"<div style='font-size:10px;color:var(--t3);'>{r['city']} · {r['email']}</div>"
# # # # #                 f"<div style='font-size:10px;color:var(--t2);margin-top:2px;'>Also supplies: {', '.join(other_names[:4])}</div>"
# # # # #                 f"</div>"
# # # # #                 f"<div style='font-size:10px;font-weight:700;color:{bc};text-align:right;'>"
# # # # #                 f"{'⚡ Consolidation opportunity' if needs_order else 'No other orders needed'}"
# # # # #                 f"</div></div>",
# # # # #                 unsafe_allow_html=True,
# # # # #             )

# # # # #     st.markdown('<div class="pfooter">🔬 Powered by <strong>MResult</strong></div>', unsafe_allow_html=True)

# # # # """
# # # # tabs/material_intelligence.py
# # # # Material Intelligence tab: agentic analysis, Monte Carlo simulation,
# # # # stock trajectory, safety stock audit, BOM components, supplier email draft,
# # # # and consolidation opportunities.
# # # # """

# # # # import streamlit as st
# # # # import pandas as pd
# # # # import plotly.graph_objects as go
# # # # from st_aggrid import AgGrid, GridOptionsBuilder, JsCode

# # # # from utils.helpers import ct, fmt_p, sbadge, sec, note, ORANGE, AZURE_DEPLOYMENT
# # # # from data_loader import (
# # # #     get_stock_history, get_demand_history, get_bom_components,
# # # #     get_material_context, get_supplier_consolidation,
# # # # )
# # # # from agent import analyse_material, chat_with_data, run_monte_carlo, draft_supplier_email

# # # # _AGGRID_CSS = {
# # # #     ".ag-root-wrapper": {"border": "1px solid #E2E8F0!important", "border-radius": "12px!important"},
# # # #     ".ag-header":       {"background": "#F8FAFE!important"},
# # # #     ".ag-row-even":     {"background": "#FFFFFF!important"},
# # # #     ".ag-row-odd":      {"background": "#F8FAFE!important"},
# # # # }


# # # # def render():
# # # #     data           = st.session_state.data
# # # #     summary        = st.session_state.summary
# # # #     MATERIAL_LABELS = st.session_state.material_labels

# # # #     mat_opts = {row["name"]: row["material"] for _, row in summary.iterrows()}
# # # #     sel_name = st.selectbox("Select Material", list(mat_opts.keys()), key="mi_mat",
# # # #                             help="Select a finished good to analyse")
# # # #     sel_mat  = mat_opts[sel_name]
# # # #     mat_row  = summary[summary.material == sel_mat].iloc[0]
# # # #     risk     = mat_row["risk"]

# # # #     # ── Insufficient data guard ───────────────────────────────────────────────
# # # #     if risk == "INSUFFICIENT_DATA":
# # # #         reasons = []
# # # #         if mat_row["nonzero_demand_months"] < 3:
# # # #             reasons.append(f"Only {mat_row['nonzero_demand_months']} months demand (min 6)")
# # # #         if mat_row["zero_periods"] > 10:
# # # #             reasons.append(f"Zero stock in {mat_row['zero_periods']}/{mat_row['total_periods']} periods")
# # # #         if sel_mat == "3515-0010":
# # # #             reasons.append("Marked inactive in sales history")
# # # #         r_html = "".join(f'<div style="font-size:11px;color:var(--t3);margin:3px 0;">• {r}</div>' for r in reasons)
# # # #         st.markdown(
# # # #             f"<div style='display:flex;align-items:center;gap:12px;margin-bottom:16px;'>"
# # # #             f"<div style='font-size:18px;font-weight:800;'>{sel_name}</div>{sbadge(risk)}</div>"
# # # #             f"<div class='flag-box' style='max-width:520px;'>"
# # # #             f"<div style='font-size:22px;margin-bottom:8px;'>◌</div>"
# # # #             f"<div style='font-size:14px;font-weight:800;color:var(--t2);margin-bottom:5px;'>Insufficient Data for ARIA Analysis</div>"
# # # #             f"<div style='font-size:12px;color:var(--t3);margin-bottom:8px;'>Requires 6+ months confirmed demand history.</div>"
# # # #             f"{r_html}</div>",
# # # #             unsafe_allow_html=True,
# # # #         )
# # # #         st.stop()

# # # #     # ── Header ────────────────────────────────────────────────────────────────
# # # #     h1c, h2c = st.columns([5, 1])
# # # #     with h1c:
# # # #         dq_flags   = mat_row.get("data_quality_flags", [])
# # # #         flags_html = "".join(
# # # #             f'<span class="chip" style="margin-right:4px;color:#F59E0B;border-color:#F59E0B40;">⚠ {f}</span>'
# # # #             for f in dq_flags[:2]
# # # #         ) if dq_flags else ""
# # # #         st.markdown(
# # # #             f"<div style='display:flex;align-items:center;flex-wrap:wrap;gap:8px;margin-bottom:6px;'>"
# # # #             f"<div style='font-size:18px;font-weight:900;'>{sel_name}</div>"
# # # #             f"{sbadge(risk)}<div class='chip'>{sel_mat}</div>{flags_html}</div>",
# # # #             unsafe_allow_html=True,
# # # #         )
# # # #     with h2c:
# # # #         run_an = st.button("◈ Analyse", use_container_width=True, key=f"analyse_btn_{sel_mat}")

# # # #     # ── ARIA Analysis ─────────────────────────────────────────────────────────
# # # #     analysis = st.session_state.agent_cache.get(sel_mat)
# # # #     if run_an:
# # # #         if st.session_state.azure_client:
# # # #             with st.spinner("ARIA investigating…"):
# # # #                 ctx      = get_material_context(data, sel_mat, summary)
# # # #                 analysis = analyse_material(st.session_state.azure_client, AZURE_DEPLOYMENT, ctx)
# # # #                 st.session_state.agent_cache[sel_mat]  = analysis
# # # #                 st.session_state.last_analysed_mat     = sel_mat
# # # #         else:
# # # #             st.markdown(
# # # #                 "<div style='padding:9px 12px;background:var(--ob);border:1px solid var(--obr);"
# # # #                 "border-radius:9px;font-size:12px;color:var(--or);'>"
# # # #                 "Enter Azure API key in sidebar to enable ARIA analysis.</div>",
# # # #                 unsafe_allow_html=True,
# # # #             )

# # # #     if analysis and st.session_state.agent_cache.get(sel_mat):
# # # #         # Key findings
# # # #         key_findings = analysis.get("key_findings", [])
# # # #         if not isinstance(key_findings, list):
# # # #             key_findings = [str(key_findings)]
# # # #         else:
# # # #             key_findings = [str(f) for f in key_findings]
# # # #         fh = "".join(f'<div class="iff"><div class="ifd"></div><div>{f}</div></div>' for f in key_findings)

# # # #         # Confidence
# # # #         conf       = str(analysis.get("data_confidence", "MEDIUM"))
# # # #         conf_clean = conf.split("—")[0].split("-")[0].strip().upper()[:6]
# # # #         cc         = "#22C55E" if "HIGH" in conf_clean else "#F59E0B" if "MEDIUM" in conf_clean else "#EF4444"

# # # #         # Data quality flags
# # # #         dq      = analysis.get("data_quality_flags", [])
# # # #         dq_html = (
# # # #             "<div style='margin-top:10px;padding-top:8px;border-top:1px solid var(--bl);'>"
# # # #             + "".join(f'<div style="font-size:10px;color:#F59E0B;margin:2px 0;">⚠ {f}</div>' for f in dq)
# # # #             + "</div>"
# # # #         ) if dq else ""

# # # #         # Display ARIA Intelligence box
# # # #         st.markdown(
# # # #             f"<div class='ic'><div class='il'>◈ ARIA Intelligence</div>"
# # # #             f"<div class='ih'>{analysis.get('headline', '')}</div>"
# # # #             f"<div class='ib'>{analysis.get('executive_summary', '')}</div>"
# # # #             f"<div style='margin-top:10px;border-top:1px solid var(--bl);padding-top:10px;'>"
# # # #             f"<div style='font-size:9px;font-weight:700;color:var(--or);text-transform:uppercase;letter-spacing:1px;margin-bottom:6px;'>Key Findings</div>"
# # # #             f"{fh}{dq_html}</div>"
# # # #             f"<div style='margin-top:8px;font-size:10px;color:var(--t3);'>"
# # # #             f"Confidence: <span style='color:{cc};font-weight:700;'>{conf_clean}</span>"
# # # #             f"</div></div>",
# # # #             unsafe_allow_html=True,
# # # #         )

# # # #         # SAP Gap and ARIA Recommendation (Fix #3: clean bullet list for recommendation)
# # # #         ca, cb = st.columns(2)
# # # #         sap_gap = analysis.get("sap_gap", "")
# # # #         if not isinstance(sap_gap, str):
# # # #             sap_gap = str(sap_gap)
# # # #         recom_raw = analysis.get("recommendation", "")
# # # #         # If recommendation is a dict, convert to readable bullet list
# # # #         if isinstance(recom_raw, dict):
# # # #             recom_lines = []
# # # #             for k, v in recom_raw.items():
# # # #                 if k.lower() == "reason":
# # # #                     recom_lines.append(f"<strong>Reason:</strong> {v}")
# # # #                 else:
# # # #                     recom_lines.append(f"<strong>{k}:</strong> {v}")
# # # #             recom = "<ul style='margin:0; padding-left:16px; font-size:11px; color:#14532d;'>" + "".join(f"<li>{line}</li>" for line in recom_lines) + "</ul>"
# # # #         else:
# # # #             recom = str(recom_raw)
# # # #             # Fallback: if it's a string but contains a dict representation, try to parse
# # # #             if recom.startswith("{") and "SKU" in recom:
# # # #                 try:
# # # #                     import ast
# # # #                     d = ast.literal_eval(recom)
# # # #                     if isinstance(d, dict):
# # # #                         recom_lines = [f"<strong>{k}:</strong> {v}" for k, v in d.items()]
# # # #                         recom = "<ul style='margin:0; padding-left:16px; font-size:11px; color:#14532d;'>" + "".join(f"<li>{line}</li>" for line in recom_lines) + "</ul>"
# # # #                 except:
# # # #                     pass

# # # #         if "Unable to parse" in sap_gap:
# # # #             sap_gap = (f"SAP Safety Stock: {mat_row['safety_stock']:.0f} units. "
# # # #                        f"ARIA recommends: {mat_row['rec_safety_stock']:.0f} units. "
# # # #                        f"Gap: {mat_row['rec_safety_stock'] - mat_row['safety_stock']:.0f} units.")
# # # #         if "No replenishment triggered" in str(recom_raw) and mat_row["repl_triggered"]:
# # # #             recom = (f"<strong>Order {int(mat_row['repl_quantity'])} units immediately.</strong><br>"
# # # #                      f"Stock-in-Hand ({mat_row['sih']:.0f}) below SAP SS ({mat_row['safety_stock']:.0f}).<br>"
# # # #                      f"Lead time: {mat_row['lead_time']:.0f}d. Formula: {mat_row['repl_formula']}")

# # # #         with ca:
# # # #             st.markdown(f"<div class='sap-box'><div class='sap-lbl'>SAP Gap Assessment</div>{sap_gap}</div>", unsafe_allow_html=True)
# # # #         with cb:
# # # #             st.markdown(
# # # #                 f"<div class='rec-box'><div class='rec-lbl'>ARIA Recommendation</div>"
# # # #                 f"{recom}"
# # # #                 f"<div style='margin-top:8px;font-size:10px;opacity:0.75;'>If ignored: {analysis.get('risk_if_ignored', '')}</div></div>",
# # # #                 unsafe_allow_html=True,
# # # #             )

# # # #         # Supplier action
# # # #         sup_action = analysis.get("supplier_action")
# # # #         if sup_action:
# # # #             st.markdown(
# # # #                 f"<div style='padding:8px 12px;background:rgba(59,130,246,0.06);"
# # # #                 f"border:1px solid rgba(59,130,246,0.2);border-radius:8px;font-size:11px;color:#1d4ed8;margin-top:8px;'>"
# # # #                 f"📧 <strong>Supplier Action:</strong> {sup_action}</div>",
# # # #                 unsafe_allow_html=True,
# # # #             )
# # # #     elif not run_an:
# # # #         st.markdown(
# # # #             "<div style='padding:12px 14px;background:var(--s2);border:1px solid var(--bl);"
# # # #             "border-radius:var(--r);font-size:12px;color:var(--t3);text-align:center;'>"
# # # #             "Click <strong style='color:var(--or);'>◈ Analyse</strong> above to run ARIA intelligence on this material.</div>",
# # # #             unsafe_allow_html=True,
# # # #         )

# # # #     # ── Monte Carlo Risk Simulation (Fix #4: add explanation expander) ─────────
# # # #     sec("Monte Carlo Risk Simulation — 1,000 Demand Scenarios")
# # # #     note("Runs 1,000 simulations of 6-month demand using historical mean & std deviation. "
# # # #          "Shows probability of stockout and range of outcomes.")
# # # #     avg_d = mat_row["avg_monthly_demand"]
# # # #     std_d = mat_row["std_demand"]
# # # #     ss_v  = mat_row["safety_stock"]
# # # #     rec   = mat_row["rec_safety_stock"]
# # # #     lt_v  = mat_row["lead_time"]

# # # #     if avg_d > 0 and std_d > 0:
# # # #         mc = run_monte_carlo(mat_row["sih"], ss_v, avg_d, std_d, lt_v, months=6, n_sims=1000)
# # # #         risk_color = {"HIGH RISK": "#EF4444", "MODERATE RISK": "#F59E0B",
# # # #                       "LOW RISK": "#22C55E", "VERY LOW RISK": "#22C55E"}.get(mc["verdict"], ORANGE)

# # # #         mc_col1, mc_col2, mc_col3 = st.columns(3)
# # # #         with mc_col1:
# # # #             st.markdown(
# # # #                 f"<div class='sc' style='flex-direction:column;align-items:center;padding:16px;'>"
# # # #                 f"<div style='font-size:28px;font-weight:900;color:{risk_color};'>{mc['probability_breach_pct']}%</div>"
# # # #                 f"<div style='font-size:11px;color:var(--t3);text-align:center;'>Probability of stockout<br>in next 6 months</div>"
# # # #                 f"<div style='font-size:12px;font-weight:700;color:{risk_color};margin-top:4px;'>{mc['verdict']}</div>"
# # # #                 f"</div>",
# # # #                 unsafe_allow_html=True,
# # # #             )
# # # #         with mc_col2:
# # # #             st.markdown(
# # # #                 f"<div class='sc' style='flex-direction:column;gap:0;'>"
# # # #                 f"<div style='font-size:10px;color:var(--t3);margin-bottom:8px;font-weight:600;'>OUTCOME RANGE (6mo)</div>"
# # # #                 f"<div style='display:flex;justify-content:space-between;margin-bottom:4px;'>"
# # # #                 f"<span style='font-size:10px;color:var(--t3);'>Pessimistic (P10)</span>"
# # # #                 f"<span style='font-size:12px;font-weight:700;color:#EF4444;'>{int(mc['p10_end_stock'])} units</span></div>"
# # # #                 f"<div style='display:flex;justify-content:space-between;margin-bottom:4px;'>"
# # # #                 f"<span style='font-size:10px;color:var(--t3);'>Median (P50)</span>"
# # # #                 f"<span style='font-size:12px;font-weight:700;color:{ORANGE};'>{int(mc['p50_end_stock'])} units</span></div>"
# # # #                 f"<div style='display:flex;justify-content:space-between;'>"
# # # #                 f"<span style='font-size:10px;color:var(--t3);'>Optimistic (P90)</span>"
# # # #                 f"<span style='font-size:12px;font-weight:700;color:#22C55E;'>{int(mc['p90_end_stock'])} units</span></div>"
# # # #                 f"</div>",
# # # #                 unsafe_allow_html=True,
# # # #             )
# # # #         with mc_col3:
# # # #             if mc["avg_breach_month"]:
# # # #                 st.markdown(
# # # #                     f"<div class='sc' style='flex-direction:column;align-items:center;padding:16px;'>"
# # # #                     f"<div style='font-size:28px;font-weight:900;color:#EF4444;'>M{mc['avg_breach_month']}</div>"
# # # #                     f"<div style='font-size:11px;color:var(--t3);text-align:center;'>Average month when<br>stockout occurs</div>"
# # # #                     f"<div style='font-size:10px;color:var(--t3);margin-top:4px;'>Based on breach scenarios</div>"
# # # #                     f"</div>",
# # # #                     unsafe_allow_html=True,
# # # #                 )
# # # #             else:
# # # #                 st.markdown(
# # # #                     f"<div class='sc' style='flex-direction:column;align-items:center;padding:16px;'>"
# # # #                     f"<div style='font-size:28px;font-weight:900;color:#22C55E;'>✓</div>"
# # # #                     f"<div style='font-size:11px;color:var(--t3);text-align:center;'>No stockout in most<br>simulated scenarios</div>"
# # # #                     f"</div>",
# # # #                     unsafe_allow_html=True,
# # # #                 )

# # # #         # Distribution chart
# # # #         if mc["end_stock_distribution"]:
# # # #             dist   = mc["end_stock_distribution"]
# # # #             fig_mc = go.Figure()
# # # #             fig_mc.add_trace(go.Histogram(x=dist, nbinsx=20, name="End Stock",
# # # #                                           marker_color=ORANGE, marker_line_width=0, opacity=0.7))
# # # #             if ss_v > 0:
# # # #                 fig_mc.add_vline(x=ss_v, line_color="#EF4444", line_dash="dot", line_width=1.5,
# # # #                                  annotation_text=f"Safety Stock {round(ss_v)}",
# # # #                                  annotation_font_color="#EF4444", annotation_font_size=9)
# # # #             ct(fig_mc, 180)
# # # #             fig_mc.update_layout(showlegend=False, xaxis_title="End Stock (units)", yaxis_title="Frequency",
# # # #                                  margin=dict(l=8, r=8, t=16, b=8))
# # # #             st.plotly_chart(fig_mc, use_container_width=True)

# # # #         # Fix #4: Monte Carlo explanation expander
# # # #         with st.expander("📖 What is Monte Carlo simulation?"):
# # # #             st.markdown("""
# # # #             - **Monte Carlo simulation** runs 1,000 possible future demand scenarios based on historical mean and standard deviation.
# # # #             - The **probability of stockout** shows the percentage of scenarios where stock falls below the safety stock in the next 6 months.
# # # #             - The **outcome range** (P10, P50, P90) shows the possible ending stock levels under pessimistic, median, and optimistic conditions.
# # # #             - The **histogram** visualises the distribution of possible ending stock levels.
# # # #             """)

# # # #     # ── Stock Trajectory ──────────────────────────────────────────────────────
# # # #     sec("Stock Trajectory")
# # # #     note("Stock from Inventory extract. Demand from Sales file (includes write-offs, internal consumption). "
# # # #          "Safety Stock from Material Master. Lead time max(Planned Delivery, Inhouse Production).")

# # # #     month_filter = st.slider("Show last N months", 6, 60, 25, step=1, key="mi_months")
# # # #     sh = get_stock_history(data, sel_mat).tail(month_filter)
# # # #     dh = get_demand_history(data, sel_mat).tail(month_filter)

# # # #     fig = go.Figure()
# # # #     fig.add_trace(go.Scatter(x=sh["label"], y=sh["Gross Stock"], mode="lines+markers", name="Stock",
# # # #                              line=dict(color=ORANGE, width=2.5), marker=dict(size=4, color=ORANGE),
# # # #                              fill="tozeroy", fillcolor="rgba(244,123,37,0.07)", yaxis="y1",
# # # #                              hovertemplate="<b>%{x}</b><br>Stock: %{y} units<extra></extra>"))
# # # #     if ss_v > 0:
# # # #         fig.add_trace(go.Scatter(x=sh["label"], y=[ss_v] * len(sh), mode="lines",
# # # #                                  name=f"SAP SS ({round(ss_v)})", yaxis="y1",
# # # #                                  line=dict(color="#EF4444", width=1.5, dash="dot")))
# # # #     if rec > ss_v:
# # # #         fig.add_trace(go.Scatter(x=sh["label"], y=[rec] * len(sh), mode="lines",
# # # #                                  name=f"ARIA SS ({round(rec)})", yaxis="y1",
# # # #                                  line=dict(color="#22C55E", width=1.5, dash="dash")))
# # # #     if len(dh) > 0:
# # # #         dh_aligned = dh[dh.label.isin(sh["label"].tolist())]
# # # #         if len(dh_aligned) > 0:
# # # #             fig.add_trace(go.Bar(x=dh_aligned["label"], y=dh_aligned["demand"], name="Demand/mo",
# # # #                                  marker_color="rgba(148,163,184,0.3)", marker_line_width=0, yaxis="y2",
# # # #                                  hovertemplate="<b>%{x}</b><br>Demand: %{y} units<extra></extra>"))
# # # #     ct(fig, 320)
# # # #     fig.update_layout(
# # # #         yaxis=dict(title="Stock (units)", gridcolor="#F0F4F9"),
# # # #         yaxis2=dict(title="Demand/mo", overlaying="y", side="right", showgrid=False),
# # # #         xaxis=dict(tickangle=-35), margin=dict(l=8, r=50, t=32, b=8),
# # # #     )
# # # #     st.plotly_chart(fig, use_container_width=True)

# # # #     # ── Safety Stock Audit ────────────────────────────────────────────────────
# # # #     ss_col, repl_col = st.columns(2)
# # # #     with ss_col:
# # # #         sec("Safety Stock Audit")
# # # #         note("SAP SS: Material Master → Safety Stock column. "
# # # #              "ARIA SS: 1.65 × σ_demand × √(lead_time/30) at 95% service level. "
# # # #              "Current Inventory SS = 0 for all SKUs (known data gap).")
# # # #         gap = rec - ss_v
# # # #         gp  = (gap / ss_v * 100) if ss_v > 0 else 100
# # # #         if gap > 10:
# # # #             gi, gc, gm = "⚠", "#F59E0B", f"SAP SS of {round(ss_v)} is {round(gp)}% below ARIA recommended {round(rec)}."
# # # #         else:
# # # #             gi, gc, gm = "✓", "#22C55E", f"SAP SS of {round(ss_v)} is adequately calibrated."
# # # #         st.markdown(
# # # #             f"<div class='sc' style='flex-direction:column;align-items:stretch;gap:0;'>"
# # # #             f"<div style='display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:10px;'>"
# # # #             f"<div><div style='font-size:9px;color:var(--t3);text-transform:uppercase;letter-spacing:0.8px;'>SAP SS (Material Master)</div>"
# # # #             f"<div style='font-size:20px;font-weight:900;color:var(--rd);'>{round(ss_v)}</div></div>"
# # # #             f"<div><div style='font-size:9px;color:var(--t3);text-transform:uppercase;letter-spacing:0.8px;'>ARIA Recommended (95% SL)</div>"
# # # #             f"<div style='font-size:20px;font-weight:900;color:var(--gr);'>{round(rec)}</div></div></div>"
# # # #             f"<div style='background:var(--s3);border-radius:8px;padding:8px 10px;font-size:11px;color:var(--t2);'>"
# # # #             f"<span style='color:{gc};font-weight:700;'>{gi} </span>{gm}</div>"
# # # #             f"</div>",
# # # #             unsafe_allow_html=True,
# # # #         )

# # # #         # Fix #5: Change button to "Explain ARIA SS Recommendation"
# # # #         if st.session_state.azure_client and analysis:
# # # #             if st.button("◈ Explain ARIA SS Recommendation", key="ss_rec"):
# # # #                 with st.spinner("ARIA analysing safety stock…"):
# # # #                     ss_ctx  = (f"Material: {sel_name}, SAP SS: {ss_v:.0f}, ARIA SS: {rec:.0f}, "
# # # #                                f"Lead time: {lt_v:.0f}d, Avg demand: {avg_d:.0f}/mo, Std: {std_d:.0f}, "
# # # #                                f"Current stock: {mat_row['sih']:.0f}, Breach count: {mat_row['breach_count']}, "
# # # #                                f"Monte Carlo breach probability: "
# # # #                                f"{run_monte_carlo(mat_row['sih'], ss_v, avg_d, std_d, lt_v)['probability_breach_pct']}%")
# # # #                     rec_txt = chat_with_data(
# # # #                         st.session_state.azure_client, AZURE_DEPLOYMENT,
# # # #                         f"Explain why the recommended safety stock for {sel_name} is {rec:.0f} units, based on the formula 1.65 × σ_demand × √(lead_time/30). Justify this value with the data provided.",
# # # #                         ss_ctx,
# # # #                     )
# # # #                 st.markdown(
# # # #                     f"<div class='ic' style='margin-top:8px;'><div class='il'>◈ ARIA SS Explanation</div>"
# # # #                     f"<div class='ib' style='margin-top:4px;'>{rec_txt}</div></div>",
# # # #                     unsafe_allow_html=True,
# # # #                 )

# # # #     with repl_col:
# # # #         sec("Replenishment Details")
# # # #         repl_t = mat_row["repl_triggered"]
# # # #         repl_q = int(mat_row["repl_quantity"])
# # # #         repl_s = int(mat_row["repl_shortfall"])
# # # #         repl_f = mat_row["repl_formula"]
# # # #         if repl_t:
# # # #             st.markdown(
# # # #                 f"<div style='background:#FEF2F2;border:1px solid rgba(239,68,68,0.2);"
# # # #                 f"border-left:3px solid #EF4444;border-radius:var(--r);padding:12px 14px;'>"
# # # #                 f"<div style='font-size:10px;font-weight:800;color:#EF4444;margin-bottom:6px;'>IMMEDIATE ORDER REQUIRED</div>"
# # # #                 f"<table style='font-size:11px;width:100%;border-collapse:collapse;'>"
# # # #                 f"<tr><td style='color:#475569;padding:2px 0;'>Stock-in-Hand</td><td style='font-weight:700;text-align:right;'>{round(mat_row['sih'])} units</td></tr>"
# # # #                 f"<tr><td style='color:#475569;padding:2px 0;'>Safety Stock (MM)</td><td style='font-weight:700;text-align:right;'>{round(ss_v)} units</td></tr>"
# # # #                 f"<tr><td style='color:#475569;padding:2px 0;'>Shortfall</td><td style='font-weight:700;color:#EF4444;text-align:right;'>{repl_s} units</td></tr>"
# # # #                 f"<tr><td style='color:#475569;padding:2px 0;'>Lead Time (MM)</td><td style='font-weight:700;text-align:right;'>{round(lt_v)}d</td></tr>"
# # # #                 f"<tr><td style='color:#475569;padding:2px 0;'>Lot Size (Curr Inv)</td><td style='font-weight:700;text-align:right;'>{round(mat_row['lot_size'])} units</td></tr>"
# # # #                 f"<tr style='border-top:1px solid #E2E8F0;'><td style='color:#EF4444;font-weight:800;padding:4px 0;'>Order Quantity</td><td style='font-weight:900;font-size:15px;color:#EF4444;text-align:right;'>{repl_q} units</td></tr>"
# # # #                 f"<tr><td colspan='2' style='font-size:9px;color:#94A3B8;padding-top:3px;'>{repl_f}</td></tr>"
# # # #                 f"</table></div>",
# # # #                 unsafe_allow_html=True,
# # # #             )
# # # #         else:
# # # #             st.markdown(
# # # #                 f"<div style='background:#F0FDF4;border:1px solid rgba(34,197,94,0.2);"
# # # #                 f"border-radius:var(--r);padding:12px 14px;font-size:12px;color:#14532d;'>"
# # # #                 f"✓ No replenishment triggered — stock above safety stock.<br>"
# # # #                 f"<span style='font-size:10px;color:#94A3B8;'>SIH={round(mat_row['sih'])} | SS={round(ss_v)}</span>"
# # # #                 f"</div>",
# # # #                 unsafe_allow_html=True,
# # # #             )

# # # #     # ── BOM Components ─────────────────────────────────────────────────────────
# # # #     bom = get_bom_components(data, sel_mat)
# # # #     if len(bom) > 0:
# # # #         sec("BOM Components &amp; Supplier Intelligence")
# # # #         lvl = bom[bom["Level"].str.contains("Level 03|Level 02|Level 1", na=False, regex=True)]
# # # #         if len(lvl) > 0:
# # # #             bom_display = []
# # # #             for _, b in lvl.iterrows():
# # # #                 fq  = ("✓ Fixed=1" if b.get("Fixed Qty Flag", False)
# # # #                        else str(round(float(b["Comp. Qty (CUn)"]), 3)) if pd.notna(b["Comp. Qty (CUn)"]) else "—")
# # # #                 sup = b.get("Supplier Display", "—")
# # # #                 loc = b.get("Supplier Location", "—")
# # # #                 transit = b.get("Transit Days", None)
# # # #                 bom_display.append({
# # # #                     "Material": str(b["Material"]),
# # # #                     "Description": str(b["Material Description"])[:36] if pd.notna(b["Material Description"]) else "—",
# # # #                     "Qty": fq, "Unit": str(b["Component unit"]) if pd.notna(b["Component unit"]) else "—",
# # # #                     "Procurement": b.get("Procurement Label", "—"),
# # # #                     "Supplier": sup, "Location": loc,
# # # #                     "Transit": f"{transit}d" if transit is not None else "—",
# # # #                 })
# # # #             df_bom_disp = pd.DataFrame(bom_display)
# # # #             sup_r2 = JsCode("""class R{init(p){const v=p.value||'';this.e=document.createElement('span');if(v.startsWith('⚠')){this.e.style.cssText='background:#FEF3C7;color:#F59E0B;padding:2px 6px;border-radius:4px;font-size:10px;font-weight:600;';this.e.innerText=v;}else if(v==='Revvity Inhouse'){this.e.style.cssText='background:#DCFCE7;color:#16a34a;padding:2px 6px;border-radius:4px;font-size:10px;';this.e.innerText=v;}else{this.e.style.cssText='background:#EFF6FF;color:#2563EB;padding:2px 6px;border-radius:4px;font-size:10px;';this.e.innerText=v;};}getGui(){return this.e;}}""")
# # # #             gb3 = GridOptionsBuilder.from_dataframe(df_bom_disp)
# # # #             gb3.configure_column("Material",    width=85)
# # # #             gb3.configure_column("Description", width=220)
# # # #             gb3.configure_column("Qty",         width=78)
# # # #             gb3.configure_column("Unit",        width=52)
# # # #             gb3.configure_column("Procurement", width=110)
# # # #             gb3.configure_column("Supplier",    width=175, cellRenderer=sup_r2)
# # # #             gb3.configure_column("Location",    width=130)
# # # #             gb3.configure_column("Transit",     width=62)
# # # #             gb3.configure_grid_options(rowHeight=36, headerHeight=32)
# # # #             gb3.configure_default_column(resizable=True, sortable=True, filter=False)
# # # #             AgGrid(df_bom_disp, gridOptions=gb3.build(), height=290,
# # # #                    allow_unsafe_jscode=True, theme="alpine", custom_css=_AGGRID_CSS)

# # # #             # Supplier email draft
# # # #             if st.session_state.azure_client:
# # # #                 external_suppliers = []
# # # #                 for _, b in lvl.iterrows():
# # # #                     sup_raw = b.get("Supplier Name(Vendor)", "")
# # # #                     if pd.notna(sup_raw) and str(sup_raw).strip() and b.get("Procurement Label", "") == "External":
# # # #                         email_raw = b.get("Supplier Email address(Vendor)", "")
# # # #                         email     = str(email_raw) if pd.notna(email_raw) else "—"
# # # #                         if mat_row["repl_triggered"]:
# # # #                             if not any(s["supplier"] == str(sup_raw).strip() for s in external_suppliers):
# # # #                                 external_suppliers.append({"supplier": str(sup_raw).strip(), "email": email})

# # # #                 if external_suppliers and st.button("📧 Draft Supplier Order Emails", key="email_btn"):
# # # #                     for sup_info in external_suppliers[:3]:
# # # #                         with st.spinner(f"Drafting email to {sup_info['supplier']}…"):
# # # #                             email_txt = draft_supplier_email(
# # # #                                 st.session_state.azure_client, AZURE_DEPLOYMENT,
# # # #                                 sup_info["supplier"], sup_info["email"],
# # # #                                 [{"name": sel_name, "quantity": mat_row["repl_quantity"], "lot_size": mat_row["lot_size"]}],
# # # #                             )
# # # #                         st.markdown(
# # # #                             f"<div style='background:#EFF6FF;border:1px solid #BFDBFE;border-radius:var(--r);"
# # # #                             f"padding:12px 14px;margin-top:8px;'>"
# # # #                             f"<div style='font-size:10px;font-weight:700;color:#1d4ed8;margin-bottom:4px;'>"
# # # #                             f"📧 Draft email to {sup_info['supplier']} ({sup_info['email']})</div>"
# # # #                             f"<pre style='font-size:11px;white-space:pre-wrap;color:#1e293b;margin:0;'>{email_txt}</pre>"
# # # #                             f"</div>",
# # # #                             unsafe_allow_html=True,
# # # #                         )

# # # #     # ── Supplier Consolidation (Fix #6: add source note) ──────────────────────
# # # #     consol   = get_supplier_consolidation(data, summary)
# # # #     relevant = consol[
# # # #         consol.material_list.apply(lambda x: sel_mat in x)
# # # #         & (consol.finished_goods_supplied > 1)
# # # #     ]
# # # #     if len(relevant) > 0:
# # # #         sec("Supplier Consolidation Opportunities")
# # # #         note("Data source: BOM file (Supplier Name column).")   # Fix #6
# # # #         note("These suppliers also supply other finished goods. If ordering from them for this material, consider consolidating orders.")
# # # #         for _, r in relevant.iterrows():
# # # #             other_mats  = [m for m in r["material_list"] if m != sel_mat]
# # # #             other_names = [MATERIAL_LABELS.get(m, m)[:20] for m in other_mats]
# # # #             needs_order = r["consolidation_opportunity"]
# # # #             bc          = "#22C55E" if not needs_order else "#F47B25"
# # # #             st.markdown(
# # # #                 f"<div class='prow'><div style='font-size:14px;'>🏭</div>"
# # # #                 f"<div style='flex:1;'>"
# # # #                 f"<div style='font-size:12px;font-weight:800;color:var(--t);'>{r['supplier']}</div>"
# # # #                 f"<div style='font-size:10px;color:var(--t3);'>{r['city']} · {r['email']}</div>"
# # # #                 f"<div style='font-size:10px;color:var(--t2);margin-top:2px;'>Also supplies: {', '.join(other_names[:4])}</div>"
# # # #                 f"</div>"
# # # #                 f"<div style='font-size:10px;font-weight:700;color:{bc};text-align:right;'>"
# # # #                 f"{'⚡ Consolidation opportunity' if needs_order else 'No other orders needed'}"
# # # #                 f"</div></div>",
# # # #                 unsafe_allow_html=True,
# # # #             )

# # # #     st.markdown('<div class="pfooter">🔬 Powered by <strong>MResult</strong></div>', unsafe_allow_html=True)

# # # """
# # # tabs/material_intelligence.py
# # # Material Intelligence tab: agentic analysis, Monte Carlo simulation,
# # # stock trajectory, safety stock audit, BOM components, supplier email draft,
# # # and consolidation opportunities.
# # # """

# # # import streamlit as st
# # # import pandas as pd
# # # import plotly.graph_objects as go
# # # from st_aggrid import AgGrid, GridOptionsBuilder, JsCode

# # # from utils.helpers import ct, fmt_p, sbadge, sec, note, ORANGE, AZURE_DEPLOYMENT
# # # from data_loader import (
# # #     get_stock_history, get_demand_history, get_bom_components,
# # #     get_material_context, get_supplier_consolidation,
# # # )
# # # from agent import analyse_material, chat_with_data, run_monte_carlo, draft_supplier_email

# # # _AGGRID_CSS = {
# # #     ".ag-root-wrapper": {"border": "1px solid #E2E8F0!important", "border-radius": "12px!important"},
# # #     ".ag-header":       {"background": "#F8FAFE!important"},
# # #     ".ag-row-even":     {"background": "#FFFFFF!important"},
# # #     ".ag-row-odd":      {"background": "#F8FAFE!important"},
# # # }


# # # def render():
# # #     data           = st.session_state.data
# # #     summary        = st.session_state.summary
# # #     MATERIAL_LABELS = st.session_state.material_labels

# # #     mat_opts = {row["name"]: row["material"] for _, row in summary.iterrows()}
# # #     sel_name = st.selectbox("Select Material", list(mat_opts.keys()), key="mi_mat",
# # #                             help="Select a finished good to analyse")
# # #     sel_mat  = mat_opts[sel_name]
# # #     mat_row  = summary[summary.material == sel_mat].iloc[0]
# # #     risk     = mat_row["risk"]

# # #     # ── Insufficient data guard ───────────────────────────────────────────────
# # #     if risk == "INSUFFICIENT_DATA":
# # #         reasons = []
# # #         if mat_row["nonzero_demand_months"] < 3:
# # #             reasons.append(f"Only {mat_row['nonzero_demand_months']} months demand (min 6)")
# # #         if mat_row["zero_periods"] > 10:
# # #             reasons.append(f"Zero stock in {mat_row['zero_periods']}/{mat_row['total_periods']} periods")
# # #         if sel_mat == "3515-0010":
# # #             reasons.append("Marked inactive in sales history")
# # #         r_html = "".join(f'<div style="font-size:11px;color:var(--t3);margin:3px 0;">• {r}</div>' for r in reasons)
# # #         st.markdown(
# # #             f"<div style='display:flex;align-items:center;gap:12px;margin-bottom:16px;'>"
# # #             f"<div style='font-size:18px;font-weight:800;'>{sel_name}</div>{sbadge(risk)}</div>"
# # #             f"<div class='flag-box' style='max-width:520px;'>"
# # #             f"<div style='font-size:22px;margin-bottom:8px;'>◌</div>"
# # #             f"<div style='font-size:14px;font-weight:800;color:var(--t2);margin-bottom:5px;'>Insufficient Data for ARIA Analysis</div>"
# # #             f"<div style='font-size:12px;color:var(--t3);margin-bottom:8px;'>Requires 6+ months confirmed demand history.</div>"
# # #             f"{r_html}</div>",
# # #             unsafe_allow_html=True,
# # #         )
# # #         st.stop()

# # #     # ── Header ────────────────────────────────────────────────────────────────
# # #     h1c, h2c = st.columns([5, 1])
# # #     with h1c:
# # #         dq_flags   = mat_row.get("data_quality_flags", [])
# # #         flags_html = "".join(
# # #             f'<span class="chip" style="margin-right:4px;color:#F59E0B;border-color:#F59E0B40;">⚠ {f}</span>'
# # #             for f in dq_flags[:2]
# # #         ) if dq_flags else ""
# # #         st.markdown(
# # #             f"<div style='display:flex;align-items:center;flex-wrap:wrap;gap:8px;margin-bottom:6px;'>"
# # #             f"<div style='font-size:18px;font-weight:900;'>{sel_name}</div>"
# # #             f"{sbadge(risk)}<div class='chip'>{sel_mat}</div>{flags_html}</div>",
# # #             unsafe_allow_html=True,
# # #         )
# # #     with h2c:
# # #         run_an = st.button("◈ Analyse", use_container_width=True, key=f"analyse_btn_{sel_mat}")

# # #     # ── ARIA Analysis ─────────────────────────────────────────────────────────
# # #     analysis = st.session_state.agent_cache.get(sel_mat)
# # #     if run_an:
# # #         if st.session_state.azure_client:
# # #             with st.spinner("ARIA investigating…"):
# # #                 ctx      = get_material_context(data, sel_mat, summary)
# # #                 analysis = analyse_material(st.session_state.azure_client, AZURE_DEPLOYMENT, ctx)
# # #                 st.session_state.agent_cache[sel_mat]  = analysis
# # #                 st.session_state.last_analysed_mat     = sel_mat
# # #         else:
# # #             st.markdown(
# # #                 "<div style='padding:9px 12px;background:var(--ob);border:1px solid var(--obr);"
# # #                 "border-radius:9px;font-size:12px;color:var(--or);'>"
# # #                 "Enter Azure API key in sidebar to enable ARIA analysis.</div>",
# # #                 unsafe_allow_html=True,
# # #             )

# # #     if analysis and st.session_state.agent_cache.get(sel_mat):
# # #         # Key findings
# # #         key_findings = analysis.get("key_findings", [])
# # #         if not isinstance(key_findings, list):
# # #             key_findings = [str(key_findings)]
# # #         else:
# # #             key_findings = [str(f) for f in key_findings]
# # #         fh = "".join(f'<div class="iff"><div class="ifd"></div><div>{f}</div></div>' for f in key_findings)

# # #         # Confidence
# # #         conf       = str(analysis.get("data_confidence", "MEDIUM"))
# # #         conf_clean = conf.split("—")[0].split("-")[0].strip().upper()[:6]
# # #         cc         = "#22C55E" if "HIGH" in conf_clean else "#F59E0B" if "MEDIUM" in conf_clean else "#EF4444"

# # #         # Data quality flags
# # #         dq      = analysis.get("data_quality_flags", [])
# # #         dq_html = (
# # #             "<div style='margin-top:10px;padding-top:8px;border-top:1px solid var(--bl);'>"
# # #             + "".join(f'<div style="font-size:10px;color:#F59E0B;margin:2px 0;">⚠ {f}</div>' for f in dq)
# # #             + "</div>"
# # #         ) if dq else ""

# # #         # Display ARIA Intelligence box
# # #         st.markdown(
# # #             f"<div class='ic'><div class='il'>◈ ARIA Intelligence</div>"
# # #             f"<div class='ih'>{analysis.get('headline', '')}</div>"
# # #             f"<div class='ib'>{analysis.get('executive_summary', '')}</div>"
# # #             f"<div style='margin-top:10px;border-top:1px solid var(--bl);padding-top:10px;'>"
# # #             f"<div style='font-size:9px;font-weight:700;color:var(--or);text-transform:uppercase;letter-spacing:1px;margin-bottom:6px;'>Key Findings</div>"
# # #             f"{fh}{dq_html}</div>"
# # #             f"<div style='margin-top:8px;font-size:10px;color:var(--t3);'>"
# # #             f"Confidence: <span style='color:{cc};font-weight:700;'>{conf_clean}</span>"
# # #             f"</div></div>",
# # #             unsafe_allow_html=True,
# # #         )

# # #         # SAP Gap and ARIA Recommendation (Fix #3: clean bullet list)
# # #         ca, cb = st.columns(2)
# # #         sap_gap = analysis.get("sap_gap", "")
# # #         if not isinstance(sap_gap, str):
# # #             sap_gap = str(sap_gap)
# # #         recom_raw = analysis.get("recommendation", "")
        
# # #         # Convert recommendation to a clean bullet list if it's a dict or dict-like string
# # #         if isinstance(recom_raw, dict):
# # #             recom_lines = []
# # #             for k, v in recom_raw.items():
# # #                 if k.lower() == "reason":
# # #                     recom_lines.append(f"<strong>Reason:</strong> {v}")
# # #                 else:
# # #                     recom_lines.append(f"<strong>{k}:</strong> {v}")
# # #             recom = "<ul style='margin:0; padding-left:16px; font-size:11px; color:#14532d;'>" + "".join(f"<li>{line}</li>" for line in recom_lines) + "</ul>"
# # #         else:
# # #             recom = str(recom_raw)
# # #             # Try to parse if it looks like a dictionary string
# # #             if recom.startswith("{") and "SKU" in recom:
# # #                 try:
# # #                     import ast
# # #                     d = ast.literal_eval(recom)
# # #                     if isinstance(d, dict):
# # #                         recom_lines = [f"<strong>{k}:</strong> {v}" for k, v in d.items()]
# # #                         recom = "<ul style='margin:0; padding-left:16px; font-size:11px; color:#14532d;'>" + "".join(f"<li>{line}</li>" for line in recom_lines) + "</ul>"
# # #                 except:
# # #                     pass

# # #         if "Unable to parse" in sap_gap:
# # #             sap_gap = (f"SAP Safety Stock: {mat_row['safety_stock']:.0f} units. "
# # #                        f"ARIA recommends: {mat_row['rec_safety_stock']:.0f} units. "
# # #                        f"Gap: {mat_row['rec_safety_stock'] - mat_row['safety_stock']:.0f} units.")
# # #         if "No replenishment triggered" in str(recom_raw) and mat_row["repl_triggered"]:
# # #             recom = (f"<strong>Order {int(mat_row['repl_quantity'])} units immediately.</strong><br>"
# # #                      f"Stock-in-Hand ({mat_row['sih']:.0f}) below SAP SS ({mat_row['safety_stock']:.0f}).<br>"
# # #                      f"Lead time: {mat_row['lead_time']:.0f}d. Formula: {mat_row['repl_formula']}")

# # #         with ca:
# # #             st.markdown(f"<div class='sap-box'><div class='sap-lbl'>SAP Gap Assessment</div>{sap_gap}</div>", unsafe_allow_html=True)
# # #         with cb:
# # #             st.markdown(
# # #                 f"<div class='rec-box'><div class='rec-lbl'>ARIA Recommendation</div>"
# # #                 f"{recom}"
# # #                 f"<div style='margin-top:8px;font-size:10px;opacity:0.75;'>If ignored: {analysis.get('risk_if_ignored', '')}</div></div>",
# # #                 unsafe_allow_html=True,
# # #             )

# # #         # Supplier action
# # #         sup_action = analysis.get("supplier_action")
# # #         if sup_action:
# # #             st.markdown(
# # #                 f"<div style='padding:8px 12px;background:rgba(59,130,246,0.06);"
# # #                 f"border:1px solid rgba(59,130,246,0.2);border-radius:8px;font-size:11px;color:#1d4ed8;margin-top:8px;'>"
# # #                 f"📧 <strong>Supplier Action:</strong> {sup_action}</div>",
# # #                 unsafe_allow_html=True,
# # #             )
# # #     elif not run_an:
# # #         st.markdown(
# # #             "<div style='padding:12px 14px;background:var(--s2);border:1px solid var(--bl);"
# # #             "border-radius:var(--r);font-size:12px;color:var(--t3);text-align:center;'>"
# # #             "Click <strong style='color:var(--or);'>◈ Analyse</strong> above to run ARIA intelligence on this material.</div>",
# # #             unsafe_allow_html=True,
# # #         )

# # #     # ── Monte Carlo Risk Simulation (Fix #4: add explanation expander) ─────────
# # #     sec("Monte Carlo Risk Simulation — 1,000 Demand Scenarios")
# # #     note("Runs 1,000 simulations of 6-month demand using historical mean & std deviation. "
# # #          "Shows probability of stockout and range of outcomes.")
# # #     avg_d = mat_row["avg_monthly_demand"]
# # #     std_d = mat_row["std_demand"]
# # #     ss_v  = mat_row["safety_stock"]
# # #     rec   = mat_row["rec_safety_stock"]
# # #     lt_v  = mat_row["lead_time"]

# # #     if avg_d > 0 and std_d > 0:
# # #         mc = run_monte_carlo(mat_row["sih"], ss_v, avg_d, std_d, lt_v, months=6, n_sims=1000)
# # #         risk_color = {"HIGH RISK": "#EF4444", "MODERATE RISK": "#F59E0B",
# # #                       "LOW RISK": "#22C55E", "VERY LOW RISK": "#22C55E"}.get(mc["verdict"], ORANGE)

# # #         mc_col1, mc_col2, mc_col3 = st.columns(3)
# # #         with mc_col1:
# # #             st.markdown(
# # #                 f"<div class='sc' style='flex-direction:column;align-items:center;padding:16px;'>"
# # #                 f"<div style='font-size:28px;font-weight:900;color:{risk_color};'>{mc['probability_breach_pct']}%</div>"
# # #                 f"<div style='font-size:11px;color:var(--t3);text-align:center;'>Probability of stockout<br>in next 6 months</div>"
# # #                 f"<div style='font-size:12px;font-weight:700;color:{risk_color};margin-top:4px;'>{mc['verdict']}</div>"
# # #                 f"</div>",
# # #                 unsafe_allow_html=True,
# # #             )
# # #         with mc_col2:
# # #             st.markdown(
# # #                 f"<div class='sc' style='flex-direction:column;gap:0;'>"
# # #                 f"<div style='font-size:10px;color:var(--t3);margin-bottom:8px;font-weight:600;'>OUTCOME RANGE (6mo)</div>"
# # #                 f"<div style='display:flex;justify-content:space-between;margin-bottom:4px;'>"
# # #                 f"<span style='font-size:10px;color:var(--t3);'>Pessimistic (P10)</span>"
# # #                 f"<span style='font-size:12px;font-weight:700;color:#EF4444;'>{int(mc['p10_end_stock'])} units</span></div>"
# # #                 f"<div style='display:flex;justify-content:space-between;margin-bottom:4px;'>"
# # #                 f"<span style='font-size:10px;color:var(--t3);'>Median (P50)</span>"
# # #                 f"<span style='font-size:12px;font-weight:700;color:{ORANGE};'>{int(mc['p50_end_stock'])} units</span></div>"
# # #                 f"<div style='display:flex;justify-content:space-between;'>"
# # #                 f"<span style='font-size:10px;color:var(--t3);'>Optimistic (P90)</span>"
# # #                 f"<span style='font-size:12px;font-weight:700;color:#22C55E;'>{int(mc['p90_end_stock'])} units</span></div>"
# # #                 f"</div>",
# # #                 unsafe_allow_html=True,
# # #             )
# # #         with mc_col3:
# # #             if mc["avg_breach_month"]:
# # #                 st.markdown(
# # #                     f"<div class='sc' style='flex-direction:column;align-items:center;padding:16px;'>"
# # #                     f"<div style='font-size:28px;font-weight:900;color:#EF4444;'>M{mc['avg_breach_month']}</div>"
# # #                     f"<div style='font-size:11px;color:var(--t3);text-align:center;'>Average month when<br>stockout occurs</div>"
# # #                     f"<div style='font-size:10px;color:var(--t3);margin-top:4px;'>Based on breach scenarios</div>"
# # #                     f"</div>",
# # #                     unsafe_allow_html=True,
# # #                 )
# # #             else:
# # #                 st.markdown(
# # #                     f"<div class='sc' style='flex-direction:column;align-items:center;padding:16px;'>"
# # #                     f"<div style='font-size:28px;font-weight:900;color:#22C55E;'>✓</div>"
# # #                     f"<div style='font-size:11px;color:var(--t3);text-align:center;'>No stockout in most<br>simulated scenarios</div>"
# # #                     f"</div>",
# # #                     unsafe_allow_html=True,
# # #                 )

# # #         # Distribution chart
# # #         if mc["end_stock_distribution"]:
# # #             dist   = mc["end_stock_distribution"]
# # #             fig_mc = go.Figure()
# # #             fig_mc.add_trace(go.Histogram(x=dist, nbinsx=20, name="End Stock",
# # #                                           marker_color=ORANGE, marker_line_width=0, opacity=0.7))
# # #             if ss_v > 0:
# # #                 fig_mc.add_vline(x=ss_v, line_color="#EF4444", line_dash="dot", line_width=1.5,
# # #                                  annotation_text=f"Safety Stock {round(ss_v)}",
# # #                                  annotation_font_color="#EF4444", annotation_font_size=9)
# # #             ct(fig_mc, 180)
# # #             fig_mc.update_layout(showlegend=False, xaxis_title="End Stock (units)", yaxis_title="Frequency",
# # #                                  margin=dict(l=8, r=8, t=16, b=8))
# # #             st.plotly_chart(fig_mc, use_container_width=True)

# # #         # Fix #4: Monte Carlo explanation expander
# # #         with st.expander("📖 What is Monte Carlo simulation?"):
# # #             st.markdown("""
# # #             - **Monte Carlo simulation** runs 1,000 possible future demand scenarios based on historical mean and standard deviation.
# # #             - The **probability of stockout** shows the percentage of scenarios where stock falls below the safety stock in the next 6 months.
# # #             - The **outcome range** (P10, P50, P90) shows the possible ending stock levels under pessimistic, median, and optimistic conditions.
# # #             - The **histogram** visualises the distribution of possible ending stock levels.
# # #             """)

# # #     # ── Stock Trajectory ──────────────────────────────────────────────────────
# # #     sec("Stock Trajectory")
# # #     note("Stock from Inventory extract. Demand from Sales file (includes write-offs, internal consumption). "
# # #          "Safety Stock from Material Master. Lead time max(Planned Delivery, Inhouse Production).")

# # #     month_filter = st.slider("Show last N months", 6, 60, 25, step=1, key="mi_months")
# # #     sh = get_stock_history(data, sel_mat).tail(month_filter)
# # #     dh = get_demand_history(data, sel_mat).tail(month_filter)

# # #     fig = go.Figure()
# # #     fig.add_trace(go.Scatter(x=sh["label"], y=sh["Gross Stock"], mode="lines+markers", name="Stock",
# # #                              line=dict(color=ORANGE, width=2.5), marker=dict(size=4, color=ORANGE),
# # #                              fill="tozeroy", fillcolor="rgba(244,123,37,0.07)", yaxis="y1",
# # #                              hovertemplate="<b>%{x}</b><br>Stock: %{y} units<extra></extra>"))
# # #     if ss_v > 0:
# # #         fig.add_trace(go.Scatter(x=sh["label"], y=[ss_v] * len(sh), mode="lines",
# # #                                  name=f"SAP SS ({round(ss_v)})", yaxis="y1",
# # #                                  line=dict(color="#EF4444", width=1.5, dash="dot")))
# # #     if rec > ss_v:
# # #         fig.add_trace(go.Scatter(x=sh["label"], y=[rec] * len(sh), mode="lines",
# # #                                  name=f"ARIA SS ({round(rec)})", yaxis="y1",
# # #                                  line=dict(color="#22C55E", width=1.5, dash="dash")))
# # #     if len(dh) > 0:
# # #         dh_aligned = dh[dh.label.isin(sh["label"].tolist())]
# # #         if len(dh_aligned) > 0:
# # #             fig.add_trace(go.Bar(x=dh_aligned["label"], y=dh_aligned["demand"], name="Demand/mo",
# # #                                  marker_color="rgba(148,163,184,0.3)", marker_line_width=0, yaxis="y2",
# # #                                  hovertemplate="<b>%{x}</b><br>Demand: %{y} units<extra></extra>"))
# # #     ct(fig, 320)
# # #     fig.update_layout(
# # #         yaxis=dict(title="Stock (units)", gridcolor="#F0F4F9"),
# # #         yaxis2=dict(title="Demand/mo", overlaying="y", side="right", showgrid=False),
# # #         xaxis=dict(tickangle=-35), margin=dict(l=8, r=50, t=32, b=8),
# # #     )
# # #     st.plotly_chart(fig, use_container_width=True)

# # #     # ── Safety Stock Audit (Fix #5: button label and prompt changed) ──────────
# # #     ss_col, repl_col = st.columns(2)
# # #     with ss_col:
# # #         sec("Safety Stock Audit")
# # #         note("SAP SS: Material Master → Safety Stock column. "
# # #              "ARIA SS: 1.65 × σ_demand × √(lead_time/30) at 95% service level. "
# # #              "Current Inventory SS = 0 for all SKUs (known data gap).")
# # #         gap = rec - ss_v
# # #         gp  = (gap / ss_v * 100) if ss_v > 0 else 100
# # #         if gap > 10:
# # #             gi, gc, gm = "⚠", "#F59E0B", f"SAP SS of {round(ss_v)} is {round(gp)}% below ARIA recommended {round(rec)}."
# # #         else:
# # #             gi, gc, gm = "✓", "#22C55E", f"SAP SS of {round(ss_v)} is adequately calibrated."
# # #         st.markdown(
# # #             f"<div class='sc' style='flex-direction:column;align-items:stretch;gap:0;'>"
# # #             f"<div style='display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:10px;'>"
# # #             f"<div><div style='font-size:9px;color:var(--t3);text-transform:uppercase;letter-spacing:0.8px;'>SAP SS (Material Master)</div>"
# # #             f"<div style='font-size:20px;font-weight:900;color:var(--rd);'>{round(ss_v)}</div></div>"
# # #             f"<div><div style='font-size:9px;color:var(--t3);text-transform:uppercase;letter-spacing:0.8px;'>ARIA Recommended (95% SL)</div>"
# # #             f"<div style='font-size:20px;font-weight:900;color:var(--gr);'>{round(rec)}</div></div></div>"
# # #             f"<div style='background:var(--s3);border-radius:8px;padding:8px 10px;font-size:11px;color:var(--t2);'>"
# # #             f"<span style='color:{gc};font-weight:700;'>{gi} </span>{gm}</div>"
# # #             f"</div>",
# # #             unsafe_allow_html=True,
# # #         )

# # #         # Fix #5: Change button label and prompt
# # #         if st.session_state.azure_client and analysis:
# # #             if st.button("◈ Explain ARIA SS Recommendation", key="ss_rec"):
# # #                 with st.spinner("ARIA analysing safety stock…"):
# # #                     ss_ctx = (f"Material: {sel_name}, SAP SS: {ss_v:.0f}, ARIA SS: {rec:.0f}, "
# # #                               f"Lead time: {lt_v:.0f}d, Avg demand: {avg_d:.0f}/mo, Std: {std_d:.0f}, "
# # #                               f"Current stock: {mat_row['sih']:.0f}, Breach count: {mat_row['breach_count']}, "
# # #                               f"Monte Carlo breach probability: "
# # #                               f"{run_monte_carlo(mat_row['sih'], ss_v, avg_d, std_d, lt_v)['probability_breach_pct']}%")
# # #                     rec_txt = chat_with_data(
# # #                         st.session_state.azure_client, AZURE_DEPLOYMENT,
# # #                         f"Explain why the recommended safety stock for {sel_name} is {rec:.0f} units, based on the formula 1.65 × σ_demand × √(lead_time/30). Justify this value with the data provided.",
# # #                         ss_ctx,
# # #                     )
# # #                 st.markdown(
# # #                     f"<div class='ic' style='margin-top:8px;'><div class='il'>◈ ARIA SS Explanation</div>"
# # #                     f"<div class='ib' style='margin-top:4px;'>{rec_txt}</div></div>",
# # #                     unsafe_allow_html=True,
# # #                 )

# # #     with repl_col:
# # #         sec("Replenishment Details")
# # #         repl_t = mat_row["repl_triggered"]
# # #         repl_q = int(mat_row["repl_quantity"])
# # #         repl_s = int(mat_row["repl_shortfall"])
# # #         repl_f = mat_row["repl_formula"]
# # #         if repl_t:
# # #             st.markdown(
# # #                 f"<div style='background:#FEF2F2;border:1px solid rgba(239,68,68,0.2);"
# # #                 f"border-left:3px solid #EF4444;border-radius:var(--r);padding:12px 14px;'>"
# # #                 f"<div style='font-size:10px;font-weight:800;color:#EF4444;margin-bottom:6px;'>IMMEDIATE ORDER REQUIRED</div>"
# # #                 f"<table style='font-size:11px;width:100%;border-collapse:collapse;'>"
# # #                 f"<tr><td style='color:#475569;padding:2px 0;'>Stock-in-Hand</td><td style='font-weight:700;text-align:right;'>{round(mat_row['sih'])} units</td></tr>"
# # #                 f"<tr><td style='color:#475569;padding:2px 0;'>Safety Stock (MM)</td><td style='font-weight:700;text-align:right;'>{round(ss_v)} units</td></tr>"
# # #                 f"<tr><td style='color:#475569;padding:2px 0;'>Shortfall</td><td style='font-weight:700;color:#EF4444;text-align:right;'>{repl_s} units</td></tr>"
# # #                 f"<tr><td style='color:#475569;padding:2px 0;'>Lead Time (MM)</td><td style='font-weight:700;text-align:right;'>{round(lt_v)}d</td></tr>"
# # #                 f"<tr><td style='color:#475569;padding:2px 0;'>Lot Size (Curr Inv)</td><td style='font-weight:700;text-align:right;'>{round(mat_row['lot_size'])} units</td></tr>"
# # #                 f"<tr style='border-top:1px solid #E2E8F0;'><td style='color:#EF4444;font-weight:800;padding:4px 0;'>Order Quantity</td><td style='font-weight:900;font-size:15px;color:#EF4444;text-align:right;'>{repl_q} units</td></tr>"
# # #                 f"<tr><td colspan='2' style='font-size:9px;color:#94A3B8;padding-top:3px;'>{repl_f}</td></tr>"
# # #                 f"</table></div>",
# # #                 unsafe_allow_html=True,
# # #             )
# # #         else:
# # #             st.markdown(
# # #                 f"<div style='background:#F0FDF4;border:1px solid rgba(34,197,94,0.2);"
# # #                 f"border-radius:var(--r);padding:12px 14px;font-size:12px;color:#14532d;'>"
# # #                 f"✓ No replenishment triggered — stock above safety stock.<br>"
# # #                 f"<span style='font-size:10px;color:#94A3B8;'>SIH={round(mat_row['sih'])} | SS={round(ss_v)}</span>"
# # #                 f"</div>",
# # #                 unsafe_allow_html=True,
# # #             )

# # #     # ── BOM Components ─────────────────────────────────────────────────────────
# # #     bom = get_bom_components(data, sel_mat)
# # #     if len(bom) > 0:
# # #         sec("BOM Components &amp; Supplier Intelligence")
# # #         lvl = bom[bom["Level"].str.contains("Level 03|Level 02|Level 1", na=False, regex=True)]
# # #         if len(lvl) > 0:
# # #             bom_display = []
# # #             for _, b in lvl.iterrows():
# # #                 fq  = ("✓ Fixed=1" if b.get("Fixed Qty Flag", False)
# # #                        else str(round(float(b["Comp. Qty (CUn)"]), 3)) if pd.notna(b["Comp. Qty (CUn)"]) else "—")
# # #                 sup = b.get("Supplier Display", "—")
# # #                 loc = b.get("Supplier Location", "—")
# # #                 transit = b.get("Transit Days", None)
# # #                 bom_display.append({
# # #                     "Material": str(b["Material"]),
# # #                     "Description": str(b["Material Description"])[:36] if pd.notna(b["Material Description"]) else "—",
# # #                     "Qty": fq, "Unit": str(b["Component unit"]) if pd.notna(b["Component unit"]) else "—",
# # #                     "Procurement": b.get("Procurement Label", "—"),
# # #                     "Supplier": sup, "Location": loc,
# # #                     "Transit": f"{transit}d" if transit is not None else "—",
# # #                 })
# # #             df_bom_disp = pd.DataFrame(bom_display)
# # #             sup_r2 = JsCode("""class R{init(p){const v=p.value||'';this.e=document.createElement('span');if(v.startsWith('⚠')){this.e.style.cssText='background:#FEF3C7;color:#F59E0B;padding:2px 6px;border-radius:4px;font-size:10px;font-weight:600;';this.e.innerText=v;}else if(v==='Revvity Inhouse'){this.e.style.cssText='background:#DCFCE7;color:#16a34a;padding:2px 6px;border-radius:4px;font-size:10px;';this.e.innerText=v;}else{this.e.style.cssText='background:#EFF6FF;color:#2563EB;padding:2px 6px;border-radius:4px;font-size:10px;';this.e.innerText=v;};}getGui(){return this.e;}}""")
# # #             gb3 = GridOptionsBuilder.from_dataframe(df_bom_disp)
# # #             gb3.configure_column("Material",    width=85)
# # #             gb3.configure_column("Description", width=220)
# # #             gb3.configure_column("Qty",         width=78)
# # #             gb3.configure_column("Unit",        width=52)
# # #             gb3.configure_column("Procurement", width=110)
# # #             gb3.configure_column("Supplier",    width=175, cellRenderer=sup_r2)
# # #             gb3.configure_column("Location",    width=130)
# # #             gb3.configure_column("Transit",     width=62)
# # #             gb3.configure_grid_options(rowHeight=36, headerHeight=32)
# # #             gb3.configure_default_column(resizable=True, sortable=True, filter=False)
# # #             AgGrid(df_bom_disp, gridOptions=gb3.build(), height=290,
# # #                    allow_unsafe_jscode=True, theme="alpine", custom_css=_AGGRID_CSS)

# # #             # Supplier email draft
# # #             if st.session_state.azure_client:
# # #                 external_suppliers = []
# # #                 for _, b in lvl.iterrows():
# # #                     sup_raw = b.get("Supplier Name(Vendor)", "")
# # #                     if pd.notna(sup_raw) and str(sup_raw).strip() and b.get("Procurement Label", "") == "External":
# # #                         email_raw = b.get("Supplier Email address(Vendor)", "")
# # #                         email     = str(email_raw) if pd.notna(email_raw) else "—"
# # #                         if mat_row["repl_triggered"]:
# # #                             if not any(s["supplier"] == str(sup_raw).strip() for s in external_suppliers):
# # #                                 external_suppliers.append({"supplier": str(sup_raw).strip(), "email": email})

# # #                 if external_suppliers and st.button("📧 Draft Supplier Order Emails", key="email_btn"):
# # #                     for sup_info in external_suppliers[:3]:
# # #                         with st.spinner(f"Drafting email to {sup_info['supplier']}…"):
# # #                             email_txt = draft_supplier_email(
# # #                                 st.session_state.azure_client, AZURE_DEPLOYMENT,
# # #                                 sup_info["supplier"], sup_info["email"],
# # #                                 [{"name": sel_name, "quantity": mat_row["repl_quantity"], "lot_size": mat_row["lot_size"]}],
# # #                             )
# # #                         st.markdown(
# # #                             f"<div style='background:#EFF6FF;border:1px solid #BFDBFE;border-radius:var(--r);"
# # #                             f"padding:12px 14px;margin-top:8px;'>"
# # #                             f"<div style='font-size:10px;font-weight:700;color:#1d4ed8;margin-bottom:4px;'>"
# # #                             f"📧 Draft email to {sup_info['supplier']} ({sup_info['email']})</div>"
# # #                             f"<pre style='font-size:11px;white-space:pre-wrap;color:#1e293b;margin:0;'>{email_txt}</pre>"
# # #                             f"</div>",
# # #                             unsafe_allow_html=True,
# # #                         )

# # #     # ── Supplier Consolidation (Fix #6: add source note) ──────────────────────
# # #     consol   = get_supplier_consolidation(data, summary)
# # #     relevant = consol[
# # #         consol.material_list.apply(lambda x: sel_mat in x)
# # #         & (consol.finished_goods_supplied > 1)
# # #     ]
# # #     if len(relevant) > 0:
# # #         sec("Supplier Consolidation Opportunities")
# # #         # Fix #6: Add source note
# # #         note("Data source: BOM file (Supplier Name column).")
# # #         note("These suppliers also supply other finished goods. If ordering from them for this material, consider consolidating orders.")
# # #         for _, r in relevant.iterrows():
# # #             other_mats  = [m for m in r["material_list"] if m != sel_mat]
# # #             other_names = [MATERIAL_LABELS.get(m, m)[:20] for m in other_mats]
# # #             needs_order = r["consolidation_opportunity"]
# # #             bc          = "#22C55E" if not needs_order else "#F47B25"
# # #             st.markdown(
# # #                 f"<div class='prow'><div style='font-size:14px;'>🏭</div>"
# # #                 f"<div style='flex:1;'>"
# # #                 f"<div style='font-size:12px;font-weight:800;color:var(--t);'>{r['supplier']}</div>"
# # #                 f"<div style='font-size:10px;color:var(--t3);'>{r['city']} · {r['email']}</div>"
# # #                 f"<div style='font-size:10px;color:var(--t2);margin-top:2px;'>Also supplies: {', '.join(other_names[:4])}</div>"
# # #                 f"</div>"
# # #                 f"<div style='font-size:10px;font-weight:700;color:{bc};text-align:right;'>"
# # #                 f"{'⚡ Consolidation opportunity' if needs_order else 'No other orders needed'}"
# # #                 f"</div></div>",
# # #                 unsafe_allow_html=True,
# # #             )

# # #     st.markdown('<div class="pfooter">🔬 Powered by <strong>MResult</strong></div>', unsafe_allow_html=True)

# # """
# # tabs/material_intelligence.py
# # Material Intelligence tab: agentic analysis, Monte Carlo simulation,
# # stock trajectory, safety stock audit, BOM components, supplier email draft,
# # and consolidation opportunities.
# # """

# # import streamlit as st
# # import pandas as pd
# # import plotly.graph_objects as go
# # from st_aggrid import AgGrid, GridOptionsBuilder, JsCode

# # from utils.helpers import ct, fmt_p, sbadge, sec, note, ORANGE, AZURE_DEPLOYMENT
# # from data_loader import (
# #     get_stock_history, get_demand_history, get_bom_components,
# #     get_material_context, get_supplier_consolidation,
# # )
# # from agent import analyse_material, chat_with_data, run_monte_carlo, draft_supplier_email

# # _AGGRID_CSS = {
# #     ".ag-root-wrapper": {"border": "1px solid #E2E8F0!important", "border-radius": "12px!important"},
# #     ".ag-header":       {"background": "#F8FAFE!important"},
# #     ".ag-row-even":     {"background": "#FFFFFF!important"},
# #     ".ag-row-odd":      {"background": "#F8FAFE!important"},
# # }


# # def render():
# #     data           = st.session_state.data
# #     summary        = st.session_state.summary
# #     MATERIAL_LABELS = st.session_state.material_labels

# #     mat_opts = {row["name"]: row["material"] for _, row in summary.iterrows()}
# #     sel_name = st.selectbox("Select Material", list(mat_opts.keys()), key="mi_mat",
# #                             help="Select a finished good to analyse")
# #     sel_mat  = mat_opts[sel_name]
# #     mat_row  = summary[summary.material == sel_mat].iloc[0]
# #     risk     = mat_row["risk"]

# #     # ── Insufficient data guard ───────────────────────────────────────────────
# #     if risk == "INSUFFICIENT_DATA":
# #         reasons = []
# #         if mat_row["nonzero_demand_months"] < 3:
# #             reasons.append(f"Only {mat_row['nonzero_demand_months']} months demand (min 6)")
# #         if mat_row["zero_periods"] > 10:
# #             reasons.append(f"Zero stock in {mat_row['zero_periods']}/{mat_row['total_periods']} periods")
# #         if sel_mat == "3515-0010":
# #             reasons.append("Marked inactive in sales history")
# #         r_html = "".join(f'<div style="font-size:11px;color:var(--t3);margin:3px 0;">• {r}</div>' for r in reasons)
# #         st.markdown(
# #             f"<div style='display:flex;align-items:center;gap:12px;margin-bottom:16px;'>"
# #             f"<div style='font-size:18px;font-weight:800;'>{sel_name}</div>{sbadge(risk)}</div>"
# #             f"<div class='flag-box' style='max-width:520px;'>"
# #             f"<div style='font-size:22px;margin-bottom:8px;'>◌</div>"
# #             f"<div style='font-size:14px;font-weight:800;color:var(--t2);margin-bottom:5px;'>Insufficient Data for ARIA Analysis</div>"
# #             f"<div style='font-size:12px;color:var(--t3);margin-bottom:8px;'>Requires 6+ months confirmed demand history.</div>"
# #             f"{r_html}</div>",
# #             unsafe_allow_html=True,
# #         )
# #         st.stop()

# #     # ── Header ────────────────────────────────────────────────────────────────
# #     h1c, h2c = st.columns([5, 1])
# #     with h1c:
# #         dq_flags   = mat_row.get("data_quality_flags", [])
# #         flags_html = "".join(
# #             f'<span class="chip" style="margin-right:4px;color:#F59E0B;border-color:#F59E0B40;">⚠ {f}</span>'
# #             for f in dq_flags[:2]
# #         ) if dq_flags else ""
# #         st.markdown(
# #             f"<div style='display:flex;align-items:center;flex-wrap:wrap;gap:8px;margin-bottom:6px;'>"
# #             f"<div style='font-size:18px;font-weight:900;'>{sel_name}</div>"
# #             f"{sbadge(risk)}<div class='chip'>{sel_mat}</div>{flags_html}</div>",
# #             unsafe_allow_html=True,
# #         )
# #     with h2c:
# #         run_an = st.button("◈ Analyse", use_container_width=True, key=f"analyse_btn_{sel_mat}")

# #     # ── ARIA Analysis ─────────────────────────────────────────────────────────
# #     analysis = st.session_state.agent_cache.get(sel_mat)
# #     if run_an:
# #         if st.session_state.azure_client:
# #             with st.spinner("ARIA investigating…"):
# #                 ctx      = get_material_context(data, sel_mat, summary)
# #                 analysis = analyse_material(st.session_state.azure_client, AZURE_DEPLOYMENT, ctx)
# #                 st.session_state.agent_cache[sel_mat]  = analysis
# #                 st.session_state.last_analysed_mat     = sel_mat
# #         else:
# #             st.markdown(
# #                 "<div style='padding:9px 12px;background:var(--ob);border:1px solid var(--obr);"
# #                 "border-radius:9px;font-size:12px;color:var(--or);'>"
# #                 "Enter Azure API key in sidebar to enable ARIA analysis.</div>",
# #                 unsafe_allow_html=True,
# #             )

# #     if analysis and st.session_state.agent_cache.get(sel_mat):
# #         # Key findings
# #         key_findings = analysis.get("key_findings", [])
# #         if not isinstance(key_findings, list):
# #             key_findings = [str(key_findings)]
# #         else:
# #             key_findings = [str(f) for f in key_findings]
# #         fh = "".join(f'<div class="iff"><div class="ifd"></div><div>{f}</div></div>' for f in key_findings)

# #         # Confidence
# #         conf       = str(analysis.get("data_confidence", "MEDIUM"))
# #         conf_clean = conf.split("—")[0].split("-")[0].strip().upper()[:6]
# #         cc         = "#22C55E" if "HIGH" in conf_clean else "#F59E0B" if "MEDIUM" in conf_clean else "#EF4444"

# #         # Data quality flags
# #         dq      = analysis.get("data_quality_flags", [])
# #         dq_html = (
# #             "<div style='margin-top:10px;padding-top:8px;border-top:1px solid var(--bl);'>"
# #             + "".join(f'<div style="font-size:10px;color:#F59E0B;margin:2px 0;">⚠ {f}</div>' for f in dq)
# #             + "</div>"
# #         ) if dq else ""

# #         # Display ARIA Intelligence box
# #         st.markdown(
# #             f"<div class='ic'><div class='il'>◈ ARIA Intelligence</div>"
# #             f"<div class='ih'>{analysis.get('headline', '')}</div>"
# #             f"<div class='ib'>{analysis.get('executive_summary', '')}</div>"
# #             f"<div style='margin-top:10px;border-top:1px solid var(--bl);padding-top:10px;'>"
# #             f"<div style='font-size:9px;font-weight:700;color:var(--or);text-transform:uppercase;letter-spacing:1px;margin-bottom:6px;'>Key Findings</div>"
# #             f"{fh}{dq_html}</div>"
# #             f"<div style='margin-top:8px;font-size:10px;color:var(--t3);'>"
# #             f"Confidence: <span style='color:{cc};font-weight:700;'>{conf_clean}</span>"
# #             f"</div></div>",
# #             unsafe_allow_html=True,
# #         )

# #         # SAP Gap and ARIA Recommendation (clean bullet list)
# #         ca, cb = st.columns(2)
# #         sap_gap = analysis.get("sap_gap", "")
# #         if not isinstance(sap_gap, str):
# #             sap_gap = str(sap_gap)
# #         recom_raw = analysis.get("recommendation", "")
        
# #         # Convert recommendation to a clean bullet list if it's a dict or dict-like string
# #         if isinstance(recom_raw, dict):
# #             recom_lines = []
# #             for k, v in recom_raw.items():
# #                 if k.lower() == "reason":
# #                     recom_lines.append(f"<strong>Reason:</strong> {v}")
# #                 else:
# #                     recom_lines.append(f"<strong>{k}:</strong> {v}")
# #             recom = "<ul style='margin:0; padding-left:16px; font-size:11px; color:#14532d;'>" + "".join(f"<li>{line}</li>" for line in recom_lines) + "</ul>"
# #         else:
# #             recom = str(recom_raw)
# #             # Try to parse if it looks like a dictionary string
# #             if recom.startswith("{") and "SKU" in recom:
# #                 try:
# #                     import ast
# #                     d = ast.literal_eval(recom)
# #                     if isinstance(d, dict):
# #                         recom_lines = [f"<strong>{k}:</strong> {v}" for k, v in d.items()]
# #                         recom = "<ul style='margin:0; padding-left:16px; font-size:11px; color:#14532d;'>" + "".join(f"<li>{line}</li>" for line in recom_lines) + "</ul>"
# #                 except:
# #                     pass

# #         if "Unable to parse" in sap_gap:
# #             sap_gap = (f"SAP Safety Stock: {mat_row['safety_stock']:.0f} units. "
# #                        f"ARIA recommends: {mat_row['rec_safety_stock']:.0f} units. "
# #                        f"Gap: {mat_row['rec_safety_stock'] - mat_row['safety_stock']:.0f} units.")
# #         if "No replenishment triggered" in str(recom_raw) and mat_row["repl_triggered"]:
# #             recom = (f"<strong>Order {int(mat_row['repl_quantity'])} units immediately.</strong><br>"
# #                      f"Stock-in-Hand ({mat_row['sih']:.0f}) below SAP SS ({mat_row['safety_stock']:.0f}).<br>"
# #                      f"Lead time: {mat_row['lead_time']:.0f}d. Formula: {mat_row['repl_formula']}")

# #         with ca:
# #             st.markdown(f"<div class='sap-box'><div class='sap-lbl'>SAP Gap Assessment</div>{sap_gap}</div>", unsafe_allow_html=True)
# #         with cb:
# #             st.markdown(
# #                 f"<div class='rec-box'><div class='rec-lbl'>ARIA Recommendation</div>"
# #                 f"{recom}"
# #                 f"<div style='margin-top:8px;font-size:10px;opacity:0.75;'>If ignored: {analysis.get('risk_if_ignored', '')}</div></div>",
# #                 unsafe_allow_html=True,
# #             )

# #         # Supplier action
# #         sup_action = analysis.get("supplier_action")
# #         if sup_action:
# #             st.markdown(
# #                 f"<div style='padding:8px 12px;background:rgba(59,130,246,0.06);"
# #                 f"border:1px solid rgba(59,130,246,0.2);border-radius:8px;font-size:11px;color:#1d4ed8;margin-top:8px;'>"
# #                 f"📧 <strong>Supplier Action:</strong> {sup_action}</div>",
# #                 unsafe_allow_html=True,
# #             )
# #     elif not run_an:
# #         st.markdown(
# #             "<div style='padding:12px 14px;background:var(--s2);border:1px solid var(--bl);"
# #             "border-radius:var(--r);font-size:12px;color:var(--t3);text-align:center;'>"
# #             "Click <strong style='color:var(--or);'>◈ Analyse</strong> above to run ARIA intelligence on this material.</div>",
# #             unsafe_allow_html=True,
# #         )

# #     # ── Monte Carlo Risk Simulation (with note() instead of expander) ─────────
# #     sec("Monte Carlo Risk Simulation — 1,000 Demand Scenarios")
# #     note("Runs 1,000 simulations of 6-month demand using historical mean & std deviation. "
# #          "Shows probability of stockout and range of outcomes.")
# #     avg_d = mat_row["avg_monthly_demand"]
# #     std_d = mat_row["std_demand"]
# #     ss_v  = mat_row["safety_stock"]
# #     rec   = mat_row["rec_safety_stock"]
# #     lt_v  = mat_row["lead_time"]

# #     if avg_d > 0 and std_d > 0:
# #         mc = run_monte_carlo(mat_row["sih"], ss_v, avg_d, std_d, lt_v, months=6, n_sims=1000)
# #         risk_color = {"HIGH RISK": "#EF4444", "MODERATE RISK": "#F59E0B",
# #                       "LOW RISK": "#22C55E", "VERY LOW RISK": "#22C55E"}.get(mc["verdict"], ORANGE)

# #         mc_col1, mc_col2, mc_col3 = st.columns(3)
# #         with mc_col1:
# #             st.markdown(
# #                 f"<div class='sc' style='flex-direction:column;align-items:center;padding:16px;'>"
# #                 f"<div style='font-size:28px;font-weight:900;color:{risk_color};'>{mc['probability_breach_pct']}%</div>"
# #                 f"<div style='font-size:11px;color:var(--t3);text-align:center;'>Probability of stockout<br>in next 6 months</div>"
# #                 f"<div style='font-size:12px;font-weight:700;color:{risk_color};margin-top:4px;'>{mc['verdict']}</div>"
# #                 f"</div>",
# #                 unsafe_allow_html=True,
# #             )
# #         with mc_col2:
# #             st.markdown(
# #                 f"<div class='sc' style='flex-direction:column;gap:0;'>"
# #                 f"<div style='font-size:10px;color:var(--t3);margin-bottom:8px;font-weight:600;'>OUTCOME RANGE (6mo)</div>"
# #                 f"<div style='display:flex;justify-content:space-between;margin-bottom:4px;'>"
# #                 f"<span style='font-size:10px;color:var(--t3);'>Pessimistic (P10)</span>"
# #                 f"<span style='font-size:12px;font-weight:700;color:#EF4444;'>{int(mc['p10_end_stock'])} units</span></div>"
# #                 f"<div style='display:flex;justify-content:space-between;margin-bottom:4px;'>"
# #                 f"<span style='font-size:10px;color:var(--t3);'>Median (P50)</span>"
# #                 f"<span style='font-size:12px;font-weight:700;color:{ORANGE};'>{int(mc['p50_end_stock'])} units</span></div>"
# #                 f"<div style='display:flex;justify-content:space-between;'>"
# #                 f"<span style='font-size:10px;color:var(--t3);'>Optimistic (P90)</span>"
# #                 f"<span style='font-size:12px;font-weight:700;color:#22C55E;'>{int(mc['p90_end_stock'])} units</span></div>"
# #                 f"</div>",
# #                 unsafe_allow_html=True,
# #             )
# #         with mc_col3:
# #             if mc["avg_breach_month"]:
# #                 st.markdown(
# #                     f"<div class='sc' style='flex-direction:column;align-items:center;padding:16px;'>"
# #                     f"<div style='font-size:28px;font-weight:900;color:#EF4444;'>M{mc['avg_breach_month']}</div>"
# #                     f"<div style='font-size:11px;color:var(--t3);text-align:center;'>Average month when<br>stockout occurs</div>"
# #                     f"<div style='font-size:10px;color:var(--t3);margin-top:4px;'>Based on breach scenarios</div>"
# #                     f"</div>",
# #                     unsafe_allow_html=True,
# #                 )
# #             else:
# #                 st.markdown(
# #                     f"<div class='sc' style='flex-direction:column;align-items:center;padding:16px;'>"
# #                     f"<div style='font-size:28px;font-weight:900;color:#22C55E;'>✓</div>"
# #                     f"<div style='font-size:11px;color:var(--t3);text-align:center;'>No stockout in most<br>simulated scenarios</div>"
# #                     f"</div>",
# #                     unsafe_allow_html=True,
# #                 )

# #         # Distribution chart
# #         if mc["end_stock_distribution"]:
# #             dist   = mc["end_stock_distribution"]
# #             fig_mc = go.Figure()
# #             fig_mc.add_trace(go.Histogram(x=dist, nbinsx=20, name="End Stock",
# #                                           marker_color=ORANGE, marker_line_width=0, opacity=0.7))
# #             if ss_v > 0:
# #                 fig_mc.add_vline(x=ss_v, line_color="#EF4444", line_dash="dot", line_width=1.5,
# #                                  annotation_text=f"Safety Stock {round(ss_v)}",
# #                                  annotation_font_color="#EF4444", annotation_font_size=9)
# #             ct(fig_mc, 180)
# #             fig_mc.update_layout(showlegend=False, xaxis_title="End Stock (units)", yaxis_title="Frequency",
# #                                  margin=dict(l=8, r=8, t=16, b=8))
# #             st.plotly_chart(fig_mc, use_container_width=True)

# #         # REPLACED: Monte Carlo explanation with note() instead of st.expander
# #         # ── Monte Carlo explanation with bold heading and bullet list ──────────
# #         st.markdown("""
# # <div class='note-box'>
# # <p style='margin:0 0 8px 0; font-weight:700;'>What is Monte Carlo simulation?</p>
# # <ul style='margin:0; padding-left:20px;'>
# # <li>Runs 1,000 possible future demand scenarios based on historical mean and standard deviation.</li>
# # <li>The <strong>probability of stockout</strong> shows the percentage of scenarios where stock falls below safety stock in the next 6 months.</li>
# # <li>The <strong>outcome range</strong> (P10, P50, P90) shows possible ending stock levels under pessimistic, median, and optimistic conditions.</li>
# # <li>The <strong>histogram</strong> visualises the distribution of possible ending stock levels.</li>
# # </ul>
# # </div>
# # """, unsafe_allow_html=True)

# #     # ── Stock Trajectory ──────────────────────────────────────────────────────
# #     sec("Stock Trajectory")
# #     note("Stock from Inventory extract. Demand from Sales file (includes write-offs, internal consumption). "
# #          "Safety Stock from Material Master. Lead time max(Planned Delivery, Inhouse Production).")

# #     month_filter = st.slider("Show last N months", 6, 60, 25, step=1, key="mi_months")
# #     sh = get_stock_history(data, sel_mat).tail(month_filter)
# #     dh = get_demand_history(data, sel_mat).tail(month_filter)

# #     fig = go.Figure()
# #     fig.add_trace(go.Scatter(x=sh["label"], y=sh["Gross Stock"], mode="lines+markers", name="Stock",
# #                              line=dict(color=ORANGE, width=2.5), marker=dict(size=4, color=ORANGE),
# #                              fill="tozeroy", fillcolor="rgba(244,123,37,0.07)", yaxis="y1",
# #                              hovertemplate="<b>%{x}</b><br>Stock: %{y} units<extra></extra>"))
# #     if ss_v > 0:
# #         fig.add_trace(go.Scatter(x=sh["label"], y=[ss_v] * len(sh), mode="lines",
# #                                  name=f"SAP SS ({round(ss_v)})", yaxis="y1",
# #                                  line=dict(color="#EF4444", width=1.5, dash="dot")))
# #     if rec > ss_v:
# #         fig.add_trace(go.Scatter(x=sh["label"], y=[rec] * len(sh), mode="lines",
# #                                  name=f"ARIA SS ({round(rec)})", yaxis="y1",
# #                                  line=dict(color="#22C55E", width=1.5, dash="dash")))
# #     if len(dh) > 0:
# #         dh_aligned = dh[dh.label.isin(sh["label"].tolist())]
# #         if len(dh_aligned) > 0:
# #             fig.add_trace(go.Bar(x=dh_aligned["label"], y=dh_aligned["demand"], name="Demand/mo",
# #                                  marker_color="rgba(148,163,184,0.3)", marker_line_width=0, yaxis="y2",
# #                                  hovertemplate="<b>%{x}</b><br>Demand: %{y} units<extra></extra>"))
# #     ct(fig, 320)
# #     fig.update_layout(
# #         yaxis=dict(title="Stock (units)", gridcolor="#F0F4F9"),
# #         yaxis2=dict(title="Demand/mo", overlaying="y", side="right", showgrid=False),
# #         xaxis=dict(tickangle=-35), margin=dict(l=8, r=50, t=32, b=8),
# #     )
# #     st.plotly_chart(fig, use_container_width=True)

# #     # ── Safety Stock Audit (button changed to "Explain ARIA SS Recommendation") ─
# #     ss_col, repl_col = st.columns(2)
# #     with ss_col:
# #         sec("Safety Stock Audit")
# #         note("SAP SS: Material Master → Safety Stock column. "
# #              "ARIA SS: 1.65 × σ_demand × √(lead_time/30) at 95% service level. "
# #              "Current Inventory SS = 0 for all SKUs (known data gap).")
# #         gap = rec - ss_v
# #         gp  = (gap / ss_v * 100) if ss_v > 0 else 100
# #         if gap > 10:
# #             gi, gc, gm = "⚠", "#F59E0B", f"SAP SS of {round(ss_v)} is {round(gp)}% below ARIA recommended {round(rec)}."
# #         else:
# #             gi, gc, gm = "✓", "#22C55E", f"SAP SS of {round(ss_v)} is adequately calibrated."
# #         st.markdown(
# #             f"<div class='sc' style='flex-direction:column;align-items:stretch;gap:0;'>"
# #             f"<div style='display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:10px;'>"
# #             f"<div><div style='font-size:9px;color:var(--t3);text-transform:uppercase;letter-spacing:0.8px;'>SAP SS (Material Master)</div>"
# #             f"<div style='font-size:20px;font-weight:900;color:var(--rd);'>{round(ss_v)}</div></div>"
# #             f"<div><div style='font-size:9px;color:var(--t3);text-transform:uppercase;letter-spacing:0.8px;'>ARIA Recommended (95% SL)</div>"
# #             f"<div style='font-size:20px;font-weight:900;color:var(--gr);'>{round(rec)}</div></div></div>"
# #             f"<div style='background:var(--s3);border-radius:8px;padding:8px 10px;font-size:11px;color:var(--t2);'>"
# #             f"<span style='color:{gc};font-weight:700;'>{gi} </span>{gm}</div>"
# #             f"</div>",
# #             unsafe_allow_html=True,
# #         )

# #         # Fix #5: Button label changed and prompt modified to explain rather than suggest
# #         if st.session_state.azure_client and analysis:
# #             if st.button("◈ Explain ARIA SS Recommendation", key="ss_rec"):
# #                 with st.spinner("ARIA analysing safety stock…"):
# #                     ss_ctx = (f"Material: {sel_name}, SAP SS: {ss_v:.0f}, ARIA SS: {rec:.0f}, "
# #                               f"Lead time: {lt_v:.0f}d, Avg demand: {avg_d:.0f}/mo, Std: {std_d:.0f}, "
# #                               f"Current stock: {mat_row['sih']:.0f}, Breach count: {mat_row['breach_count']}, "
# #                               f"Monte Carlo breach probability: "
# #                               f"{run_monte_carlo(mat_row['sih'], ss_v, avg_d, std_d, lt_v)['probability_breach_pct']}%")
# #                     rec_txt = chat_with_data(
# #                         st.session_state.azure_client, AZURE_DEPLOYMENT,
# #                         f"Explain why the recommended safety stock for {sel_name} is {rec:.0f} units, based on the formula 1.65 × σ_demand × √(lead_time/30). Justify this value with the data provided.",
# #                         ss_ctx,
# #                     )
# #                 st.markdown(
# #                     f"<div class='ic' style='margin-top:8px;'><div class='il'>◈ ARIA SS Explanation</div>"
# #                     f"<div class='ib' style='margin-top:4px;'>{rec_txt}</div></div>",
# #                     unsafe_allow_html=True,
# #                 )

# #     with repl_col:
# #         sec("Replenishment Details")
# #         repl_t = mat_row["repl_triggered"]
# #         repl_q = int(mat_row["repl_quantity"])
# #         repl_s = int(mat_row["repl_shortfall"])
# #         repl_f = mat_row["repl_formula"]
# #         if repl_t:
# #             st.markdown(
# #                 f"<div style='background:#FEF2F2;border:1px solid rgba(239,68,68,0.2);"
# #                 f"border-left:3px solid #EF4444;border-radius:var(--r);padding:12px 14px;'>"
# #                 f"<div style='font-size:10px;font-weight:800;color:#EF4444;margin-bottom:6px;'>IMMEDIATE ORDER REQUIRED</div>"
# #                 f"<table style='font-size:11px;width:100%;border-collapse:collapse;'>"
# #                 f"<tr><td style='color:#475569;padding:2px 0;'>Stock-in-Hand</td><td style='font-weight:700;text-align:right;'>{round(mat_row['sih'])} units</td></tr>"
# #                 f"<tr><td style='color:#475569;padding:2px 0;'>Safety Stock (MM)</td><td style='font-weight:700;text-align:right;'>{round(ss_v)} units</td></tr>"
# #                 f"<tr><td style='color:#475569;padding:2px 0;'>Shortfall</td><td style='font-weight:700;color:#EF4444;text-align:right;'>{repl_s} units</td></tr>"
# #                 f"<tr><td style='color:#475569;padding:2px 0;'>Lead Time (MM)</td><td style='font-weight:700;text-align:right;'>{round(lt_v)}d</td><tr>"
# #                 f"<tr><td style='color:#475569;padding:2px 0;'>Lot Size (Curr Inv)</td><td style='font-weight:700;text-align:right;'>{round(mat_row['lot_size'])} units</td></tr>"
# #                 f"<tr style='border-top:1px solid #E2E8F0;'><td style='color:#EF4444;font-weight:800;padding:4px 0;'>Order Quantity</td><td style='font-weight:900;font-size:15px;color:#EF4444;text-align:right;'>{repl_q} units</td></tr>"
# #                 f"<tr><td colspan='2' style='font-size:9px;color:#94A3B8;padding-top:3px;'>{repl_f}</td></tr>"
# #                 f"</tr></div>",
# #                 unsafe_allow_html=True,
# #             )
# #         else:
# #             st.markdown(
# #                 f"<div style='background:#F0FDF4;border:1px solid rgba(34,197,94,0.2);"
# #                 f"border-radius:var(--r);padding:12px 14px;font-size:12px;color:#14532d;'>"
# #                 f"✓ No replenishment triggered — stock above safety stock.<br>"
# #                 f"<span style='font-size:10px;color:#94A3B8;'>SIH={round(mat_row['sih'])} | SS={round(ss_v)}</span>"
# #                 f"</div>",
# #                 unsafe_allow_html=True,
# #             )

# #     # ── BOM Components ─────────────────────────────────────────────────────────
# #     bom = get_bom_components(data, sel_mat)
# #     if len(bom) > 0:
# #         sec("BOM Components &amp; Supplier Intelligence")
# #         lvl = bom[bom["Level"].str.contains("Level 03|Level 02|Level 1", na=False, regex=True)]
# #         if len(lvl) > 0:
# #             bom_display = []
# #             for _, b in lvl.iterrows():
# #                 fq  = ("✓ Fixed=1" if b.get("Fixed Qty Flag", False)
# #                        else str(round(float(b["Comp. Qty (CUn)"]), 3)) if pd.notna(b["Comp. Qty (CUn)"]) else "—")
# #                 sup = b.get("Supplier Display", "—")
# #                 loc = b.get("Supplier Location", "—")
# #                 transit = b.get("Transit Days", None)
# #                 bom_display.append({
# #                     "Material": str(b["Material"]),
# #                     "Description": str(b["Material Description"])[:36] if pd.notna(b["Material Description"]) else "—",
# #                     "Qty": fq, "Unit": str(b["Component unit"]) if pd.notna(b["Component unit"]) else "—",
# #                     "Procurement": b.get("Procurement Label", "—"),
# #                     "Supplier": sup, "Location": loc,
# #                     "Transit": f"{transit}d" if transit is not None else "—",
# #                 })
# #             df_bom_disp = pd.DataFrame(bom_display)
# #             sup_r2 = JsCode("""class R{init(p){const v=p.value||'';this.e=document.createElement('span');if(v.startsWith('⚠')){this.e.style.cssText='background:#FEF3C7;color:#F59E0B;padding:2px 6px;border-radius:4px;font-size:10px;font-weight:600;';this.e.innerText=v;}else if(v==='Revvity Inhouse'){this.e.style.cssText='background:#DCFCE7;color:#16a34a;padding:2px 6px;border-radius:4px;font-size:10px;';this.e.innerText=v;}else{this.e.style.cssText='background:#EFF6FF;color:#2563EB;padding:2px 6px;border-radius:4px;font-size:10px;';this.e.innerText=v;};}getGui(){return this.e;}}""")
# #             gb3 = GridOptionsBuilder.from_dataframe(df_bom_disp)
# #             gb3.configure_column("Material",    width=85)
# #             gb3.configure_column("Description", width=220)
# #             gb3.configure_column("Qty",         width=78)
# #             gb3.configure_column("Unit",        width=52)
# #             gb3.configure_column("Procurement", width=110)
# #             gb3.configure_column("Supplier",    width=175, cellRenderer=sup_r2)
# #             gb3.configure_column("Location",    width=130)
# #             gb3.configure_column("Transit",     width=62)
# #             gb3.configure_grid_options(rowHeight=36, headerHeight=32)
# #             gb3.configure_default_column(resizable=True, sortable=True, filter=False)
# #             AgGrid(df_bom_disp, gridOptions=gb3.build(), height=290,
# #                    allow_unsafe_jscode=True, theme="alpine", custom_css=_AGGRID_CSS)

# #             # Supplier email draft
# #             if st.session_state.azure_client:
# #                 external_suppliers = []
# #                 for _, b in lvl.iterrows():
# #                     sup_raw = b.get("Supplier Name(Vendor)", "")
# #                     if pd.notna(sup_raw) and str(sup_raw).strip() and b.get("Procurement Label", "") == "External":
# #                         email_raw = b.get("Supplier Email address(Vendor)", "")
# #                         email     = str(email_raw) if pd.notna(email_raw) else "—"
# #                         if mat_row["repl_triggered"]:
# #                             if not any(s["supplier"] == str(sup_raw).strip() for s in external_suppliers):
# #                                 external_suppliers.append({"supplier": str(sup_raw).strip(), "email": email})

# #                 if external_suppliers and st.button("📧 Draft Supplier Order Emails", key="email_btn"):
# #                     for sup_info in external_suppliers[:3]:
# #                         with st.spinner(f"Drafting email to {sup_info['supplier']}…"):
# #                             email_txt = draft_supplier_email(
# #                                 st.session_state.azure_client, AZURE_DEPLOYMENT,
# #                                 sup_info["supplier"], sup_info["email"],
# #                                 [{"name": sel_name, "quantity": mat_row["repl_quantity"], "lot_size": mat_row["lot_size"]}],
# #                             )
# #                         st.markdown(
# #                             f"<div style='background:#EFF6FF;border:1px solid #BFDBFE;border-radius:var(--r);"
# #                             f"padding:12px 14px;margin-top:8px;'>"
# #                             f"<div style='font-size:10px;font-weight:700;color:#1d4ed8;margin-bottom:4px;'>"
# #                             f"📧 Draft email to {sup_info['supplier']} ({sup_info['email']})</div>"
# #                             f"<pre style='font-size:11px;white-space:pre-wrap;color:#1e293b;margin:0;'>{email_txt}</pre>"
# #                             f"</div>",
# #                             unsafe_allow_html=True,
# #                         )

# #     # ── Supplier Consolidation (Fix #6: add source note) ──────────────────────
# #     consol   = get_supplier_consolidation(data, summary)
# #     relevant = consol[
# #         consol.material_list.apply(lambda x: sel_mat in x)
# #         & (consol.finished_goods_supplied > 1)
# #     ]
# #     if len(relevant) > 0:
# #         sec("Supplier Consolidation Opportunities")
# #         # Fix #6: Add source note
# #         note("Data source: BOM file (Supplier Name column).")
# #         note("These suppliers also supply other finished goods. If ordering from them for this material, consider consolidating orders.")
# #         for _, r in relevant.iterrows():
# #             other_mats  = [m for m in r["material_list"] if m != sel_mat]
# #             other_names = [MATERIAL_LABELS.get(m, m)[:20] for m in other_mats]
# #             needs_order = r["consolidation_opportunity"]
# #             bc          = "#22C55E" if not needs_order else "#F47B25"
# #             st.markdown(
# #                 f"<div class='prow'><div style='font-size:14px;'>🏭</div>"
# #                 f"<div style='flex:1;'>"
# #                 f"<div style='font-size:12px;font-weight:800;color:var(--t);'>{r['supplier']}</div>"
# #                 f"<div style='font-size:10px;color:var(--t3);'>{r['city']} · {r['email']}</div>"
# #                 f"<div style='font-size:10px;color:var(--t2);margin-top:2px;'>Also supplies: {', '.join(other_names[:4])}</div>"
# #                 f"</div>"
# #                 f"<div style='font-size:10px;font-weight:700;color:{bc};text-align:right;'>"
# #                 f"{'⚡ Consolidation opportunity' if needs_order else 'No other orders needed'}"
# #                 f"</div></div>",
# #                 unsafe_allow_html=True,
# #             )

# #     st.markdown('<div class="pfooter">🔬 Powered by <strong>MResult</strong></div>', unsafe_allow_html=True)
