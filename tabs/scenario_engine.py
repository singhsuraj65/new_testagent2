# # """
# # tabs/scenario_engine.py
# # Scenario Engine tab: Demand Shock simulation, Supply Disruption simulation,
# # and Historical Replay.
# # """

# # import math
# # import streamlit as st
# # import plotly.graph_objects as go

# # from utils.helpers import ct, sec, note, ORANGE, AZURE_DEPLOYMENT
# # from data_loader import get_stock_history
# # from agent import simulate_scenario, simulate_multi_sku_disruption, chat_with_data


# # def render():
# #     summary = st.session_state.summary

# #     st.markdown(
# #         "<div style='font-size:15px;font-weight:800;margin-bottom:4px;'>Scenario Engine</div>"
# #         "<div style='font-size:12px;color:var(--t3);margin-bottom:14px;'>"
# #         "Forward simulation · Supply disruption · Historical replay · LLM interpretation</div>",
# #         unsafe_allow_html=True,
# #     )

# #     sim_tab, dis_tab, rep_tab = st.tabs(["📈  Demand Shock", "🔴  Supply Disruption", "↺  Historical Replay"])

# #     # ── Demand Shock ──────────────────────────────────────────────────────────
# #     with sim_tab:
# #         st.markdown(
# #             "<div style='padding:8px 0;font-size:12px;color:var(--t2);'>"
# #             "<strong>Demand Shock</strong> simulates how different demand levels affect your stock over 6 months. "
# #             "Use the shock month/multiplier to model sudden demand spikes (e.g. seasonal peak or unexpected order).</div>",
# #             unsafe_allow_html=True,
# #         )
# #         cc2, rc = st.columns([1, 2])
# #         with cc2:
# #             sec("Controls")
# #             sim_opts = {r["name"]: r["material"] for _, r in summary[summary.risk != "INSUFFICIENT_DATA"].iterrows()}
# #             sn       = st.selectbox("Material", list(sim_opts.keys()), key="sm")
# #             sid      = sim_opts[sn]
# #             sr       = summary[summary.material == sid].iloc[0]
# #             ad       = sr["avg_monthly_demand"]
# #             ss_sim   = sr["safety_stock"]
# #             lot_sim  = sr["lot_size"]
# #             lt_sim   = sr["lead_time"]
# #             st.markdown(
# #                 f'<div class="chip" style="margin-bottom:8px;font-size:10px;">'
# #                 f'SIH: {round(sr["sih"])} · SS: {round(ss_sim)} · LT: {round(lt_sim)}d · Lot: {round(lot_sim)}</div>',
# #                 unsafe_allow_html=True,
# #             )
# #             st.markdown("<div style='font-size:10px;color:var(--t3);margin-bottom:4px;'>Expected demand/month</div>", unsafe_allow_html=True)
# #             ed  = st.slider("ed", int(ad * 0.3), int(ad * 3 + 50), int(ad), step=5, label_visibility="collapsed")
# #             son = st.toggle("Add demand shock", False, key="son", help="Simulates a sudden spike in one specific month")
# #             smo = smx = None
# #             if son:
# #                 st.markdown("<div style='font-size:10px;color:var(--t3);'>Shock month: which month the spike occurs</div>", unsafe_allow_html=True)
# #                 smo = st.slider("Shock month", 1, 6, 2, key="smo")
# #                 st.markdown("<div style='font-size:10px;color:var(--t3);'>Multiplier: how many times the normal demand</div>", unsafe_allow_html=True)
# #                 smx = st.slider("Multiplier", 1.5, 5.0, 2.5, step=0.5, key="smx")
# #             oon = st.toggle("Place order", False, key="oon", help="Simulates placing an emergency order that arrives after the lead time")
# #             oq = ot = None
# #             if oon:
# #                 repl_default = max(
# #                     int(max(ss_sim - sr["sih"], 0) / max(lot_sim, 1)) * int(lot_sim) if lot_sim > 0 else int(max(ss_sim - sr["sih"], 0)),
# #                     100,
# #                 )
# #                 oq = st.slider("Order qty",       50, 2000, repl_default, step=50)
# #                 ot = st.slider("Arrives (days)", 1, 60, int(lt_sim))
# #             rsim = st.button("▶  Run Demand Simulation", use_container_width=True)

# #         with rc:
# #             sec("6-Month Projection")
# #             if rsim or st.session_state.get("sim_ran"):
# #                 mos  = 6
# #                 stk  = sr["sih"]
# #                 ss   = ss_sim
# #                 scns = {"Low (−40%)": [ed * 0.6] * mos, "Expected": [ed] * mos, "High (+60%)": [ed * 1.6] * mos}
# #                 if son and smo and smx:
# #                     for k in scns:
# #                         if k != "Low (−40%)":
# #                             scns[k][smo - 1] = ed * smx
# #                 oa  = int(ot / 30) if oon and ot else None
# #                 fs  = go.Figure()
# #                 scc = {"Low (−40%)": "#22C55E", "Expected": ORANGE, "High (+60%)": "#EF4444"}
# #                 bi  = {}
# #                 for sc_k, dems in scns.items():
# #                     proj = []
# #                     s    = stk
# #                     for m, d in enumerate(dems):
# #                         if oon and oq and m == oa:
# #                             s += oq
# #                         s = max(0.0, s - d)
# #                         proj.append(s)
# #                     bi[sc_k] = next((m + 1 for m, sp in enumerate(proj) if sp < max(ss, 1)), None)
# #                     fs.add_trace(go.Scatter(
# #                         x=[f"M{i+1}" for i in range(mos)], y=proj, mode="lines+markers", name=sc_k,
# #                         line=dict(color=scc[sc_k], width=2.5), marker=dict(size=5, color=scc[sc_k]),
# #                     ))
# #                 if ss > 0:
# #                     fs.add_hline(y=ss, line_color="#EF4444", line_dash="dot", line_width=1.5,
# #                                  annotation_text=f"SAP SS ({round(ss)})",
# #                                  annotation_font_color="#EF4444", annotation_font_size=9)
# #                 ct(fs, 270)
# #                 st.plotly_chart(fs, use_container_width=True)
# #                 st.session_state["sim_ran"] = True

# #                 vc = st.columns(3)
# #                 for col, (sc_k, br) in zip(vc, bi.items()):
# #                     cl  = "#EF4444" if br else "#22C55E"
# #                     bg  = "#FEF2F2" if br else "#F0FDF4"
# #                     txt = f"⛔ Breach M{br}" if br else "✓ Safe 6mo"
# #                     with col:
# #                         st.markdown(
# #                             f"<div class='sc' style='padding:9px 11px;flex-direction:column;gap:2px;'>"
# #                             f"<div style='font-size:9px;color:var(--t3);'>{sc_k}</div>"
# #                             f"<div style='font-size:12px;font-weight:800;color:{cl};background:{bg};padding:3px 7px;border-radius:6px;'>{txt}</div>"
# #                             f"</div>",
# #                             unsafe_allow_html=True,
# #                         )

# #                 note(
# #                     f"Replenishment qty: CEILING(max(0,SS−SIH)/FLS)×FLS = "
# #                     f"{int(math.ceil(max(0, ss - stk) / lot_sim) * lot_sim) if lot_sim > 0 else 0} units"
# #                 )

# #                 if st.session_state.azure_client and rsim:
# #                     with st.spinner("ARIA evaluating…"):
# #                         sv = simulate_scenario(
# #                             st.session_state.azure_client, AZURE_DEPLOYMENT,
# #                             sn, stk, ss, lt_sim, lot_sim,
# #                             {"low": ed * 0.6, "expected": ed, "high": ed * 1.6},
# #                             {"quantity": oq, "timing_days": ot} if oon else None,
# #                         )
# #                     urg  = sv.get("urgency", "MONITOR")
# #                     uc   = {"ACT TODAY": "#EF4444", "ACT THIS WEEK": "#F59E0B", "MONITOR": ORANGE, "SAFE": "#22C55E"}.get(urg, ORANGE)
# #                     st.markdown(
# #                         f"<div class='ic' style='margin-top:10px;'><div class='il'>◈ ARIA Verdict</div>"
# #                         f"<div style='display:flex;align-items:center;gap:8px;margin-bottom:6px;'>"
# #                         f"<span style='font-size:12px;font-weight:800;color:{uc};'>{urg}</span>"
# #                         f"<span class='chip'>Min order: {sv.get('min_order_recommended', '—')} units</span></div>"
# #                         f"<div class='ib'>{sv.get('simulation_verdict', '')}</div></div>",
# #                         unsafe_allow_html=True,
# #                     )

# #     # ── Supply Disruption ─────────────────────────────────────────────────────
# #     with dis_tab:
# #         st.markdown(
# #             "<div style='padding:8px 0 10px;font-size:12px;color:var(--t2);'>"
# #             "<strong>Supply Disruption</strong> simulates a freeze in replenishment across selected materials. "
# #             "This models scenarios like supplier insolvency, geopolitical disruption, or production shutdown. "
# #             "ARIA ranks which SKUs breach safety stock first and by how much.</div>",
# #             unsafe_allow_html=True,
# #         )
# #         note("Formula: daily consumption × disruption days = stock consumed. "
# #              "Breach = remaining stock < Safety Stock. Emergency order = CEILING(Shortfall/FLS)×FLS.")
# #         dc2, dr = st.columns([1, 2])
# #         with dc2:
# #             sec("Disruption Parameters")
# #             st.markdown("<div style='font-size:10px;color:var(--t3);margin-bottom:3px;'>Duration of supply freeze</div>", unsafe_allow_html=True)
# #             disruption_days = st.slider("days", 7, 90, 30, step=7, label_visibility="collapsed", key="dis_days")
# #             affected        = st.multiselect(
# #                 "Affected materials (blank=all)",
# #                 [r["name"] for _, r in summary[summary.risk != "INSUFFICIENT_DATA"].iterrows()],
# #                 key="dis_mats",
# #             )
# #             run_dis = st.button("🔴  Run Disruption", use_container_width=True)

# #         with dr:
# #             sec("Impact — Ranked by Severity")
# #             if run_dis or st.session_state.get("dis_ran"):
# #                 adis = summary[summary.risk != "INSUFFICIENT_DATA"]
# #                 if affected:
# #                     adis = adis[adis.name.isin(affected)]
# #                 sku_data = [{
# #                     "material": r["material"], "name": r["name"],
# #                     "current_stock": r["sih"], "safety_stock": r["safety_stock"],
# #                     "lead_time": r["lead_time"], "fixed_lot_size": r["lot_size"],
# #                     "avg_monthly_demand": r["avg_monthly_demand"], "risk": r["risk"],
# #                 } for _, r in adis.iterrows()]
# #                 results = simulate_multi_sku_disruption(None, None, disruption_days, sku_data)
# #                 st.session_state["dis_ran"] = True

# #                 for i, r in enumerate(results):
# #                     bc   = r["breach_occurs"]
# #                     brd  = "#EF4444" if bc else "#22C55E"
# #                     bgc  = "rgba(239,68,68,0.03)" if bc else "#FFFFFF"
# #                     days_txt = (f"Breach Day {r['days_to_breach']}" if bc and r["days_to_breach"] is not None
# #                                 else ("Already breached" if bc else f"Safe for {disruption_days}d"))
# #                     metric_cells = ""
# #                     for val, lbl, c in [
# #                         (str(r["stock_at_end"]), "End",   "#EF4444" if r["shortfall_units"] > 0 else "#22C55E"),
# #                         (str(r["shortfall_units"]), "Short", "#EF4444" if r["shortfall_units"] > 0 else "#94A3B8"),
# #                         (f"{r['lead_time']}d", "LT",   "#1E293B"),
# #                         (str(r["reorder_qty"]), "Order", "#EF4444" if r["reorder_qty"] > 0 else "#94A3B8"),
# #                     ]:
# #                         metric_cells += (
# #                             f"<div style='background:var(--s3);border-radius:5px;padding:4px;'>"
# #                             f"<div style='font-size:11px;font-weight:800;color:{c};'>{val}</div>"
# #                             f"<div style='font-size:8px;color:var(--t3);'>{lbl}</div></div>"
# #                         )
# #                     st.markdown(
# #                         f"<div class='prow' style='border-left:3px solid {brd};background:{bgc};margin-bottom:6px;'>"
# #                         f"<div style='min-width:22px;font-size:13px;font-weight:900;color:{brd};'>{i+1}</div>"
# #                         f"<div style='font-size:16px;'>{'⛔' if bc else '✓'}</div>"
# #                         f"<div style='flex:1;'>"
# #                         f"<div style='font-size:12px;font-weight:800;color:var(--t);'>{r['name']}</div>"
# #                         f"<div style='font-size:10px;color:{brd};font-weight:600;margin-top:1px;'>{days_txt}</div>"
# #                         f"</div>"
# #                         f"<div style='display:grid;grid-template-columns:repeat(4,62px);gap:4px;text-align:center;'>"
# #                         + metric_cells +
# #                         f"</div></div>",
# #                         unsafe_allow_html=True,
# #                     )

# #                 if st.session_state.azure_client and run_dis:
# #                     breached = [r for r in results if r["breach_occurs"]]
# #                     if breached:
# #                         ctx_dis = (f"Disruption: {disruption_days}d freeze. "
# #                                    f"Breaches: {', '.join([r['name'] for r in breached])}. "
# #                                    f"Worst: {breached[0]['name']} on day {breached[0]['days_to_breach'] or 0}.")
# #                         with st.spinner("ARIA evaluating…"):
# #                             dv = chat_with_data(
# #                                 st.session_state.azure_client, AZURE_DEPLOYMENT,
# #                                 "2-sentence executive verdict on this supply disruption. What is most critical?",
# #                                 ctx_dis,
# #                             )
# #                         st.markdown(
# #                             f"<div class='ic' style='margin-top:10px;'>"
# #                             f"<div class='il'>◈ ARIA DISRUPTION VERDICT</div>"
# #                             f"<div class='ib' style='margin-top:4px;'>{dv}</div></div>",
# #                             unsafe_allow_html=True,
# #                         )

# #     # ── Historical Replay ──────────────────────────────────────────────────────
# #     with rep_tab:
# #         st.markdown(
# #             "<div style='padding:8px 0 10px;font-size:12px;color:var(--t2);'>"
# #             "<strong>Historical Replay</strong> shows what actually happened in a past period and reconstructs "
# #             "when ARIA would have triggered an order signal — demonstrating the value of predictive replenishment.</div>",
# #             unsafe_allow_html=True,
# #         )
# #         rp_opts = {r["name"]: r["material"] for _, r in summary[summary.risk != "INSUFFICIENT_DATA"].iterrows()}
# #         rp_sn   = st.selectbox("Material", list(rp_opts.keys()), key="rp_mat")
# #         rp_sid  = rp_opts[rp_sn]
# #         rp_sr   = summary[summary.material == rp_sid].iloc[0]
# #         shrp    = get_stock_history(st.session_state.data, rp_sid)
# #         pds_lbl = shrp["label"].tolist()

# #         if len(pds_lbl) > 4:
# #             rps = st.selectbox("Replay from period", pds_lbl[:-3],
# #                                index=min(8, len(pds_lbl) - 4), key="rps")
# #             if st.button("↺  Replay this period", key="rpb"):
# #                 idx = pds_lbl.index(rps)
# #                 rd  = shrp.iloc[idx:idx + 6]
# #                 ssr = rp_sr["safety_stock"]
# #                 fr  = go.Figure()
# #                 fr.add_trace(go.Scatter(
# #                     x=rd["label"], y=rd["Gross Stock"], mode="lines+markers", name="Actual Stock",
# #                     line=dict(color=ORANGE, width=2.5), marker=dict(size=7, color=ORANGE),
# #                     fill="tozeroy", fillcolor="rgba(244,123,37,0.07)",
# #                     hovertemplate="<b>%{x}</b><br>%{y} units<extra></extra>",
# #                 ))
# #                 if ssr > 0:
# #                     fr.add_hline(y=ssr, line_color="#EF4444", line_dash="dot",
# #                                  annotation_text=f"SAP SS {round(ssr)}", annotation_font_color="#EF4444")
# #                 br2 = rd[rd["Gross Stock"] < max(ssr, 1)]
# #                 if len(br2) > 0:
# #                     bp       = br2.iloc[0]["label"]
# #                     prev_idx = max(0, rd.index.tolist().index(br2.index[0]) - 1)
# #                     fr.add_vline(x=bp, line_color="#EF4444", line_dash="dash",
# #                                  annotation_text="⛔ Breach", annotation_font_color="#EF4444")
# #                     fr.add_vline(x=rd.iloc[prev_idx]["label"], line_color="#22C55E", line_dash="dash",
# #                                  annotation_text="◈ ARIA signal", annotation_font_color="#22C55E")
# #                 ct(fr, 260)
# #                 st.plotly_chart(fr, use_container_width=True)
# #                 msg = ("⛔ Breach detected. ARIA would have signalled an order one period earlier."
# #                        if len(br2) > 0 else
# #                        "✓ No breach in this period — stock remained above safety stock.")
# #                 mc2 = "#EF4444" if len(br2) > 0 else "#22C55E"
# #                 mb2 = "#FEF2F2" if len(br2) > 0 else "#F0FDF4"
# #                 st.markdown(
# #                     f"<div style='font-size:11px;color:{mc2};padding:7px 11px;background:{mb2};border-radius:8px;'>{msg}</div>",
# #                     unsafe_allow_html=True,
# #                 )

# #     st.markdown('<div class="pfooter">⚡ Powered by <strong>MResult</strong></div>', unsafe_allow_html=True)

# """
# tabs/scenario_engine.py
# Scenario Engine tab: Demand Shock simulation, Supply Disruption simulation,
# and Historical Replay.
# """

# import math
# import streamlit as st
# import plotly.graph_objects as go

# from utils.helpers import ct, sec, note, ORANGE, AZURE_DEPLOYMENT
# from data_loader import get_stock_history
# from agent import simulate_scenario, simulate_multi_sku_disruption, chat_with_data


# def render():
#     summary = st.session_state.summary

#     st.markdown(
#         "<div style='font-size:15px;font-weight:800;margin-bottom:4px;'>Scenario Engine</div>"
#         "<div style='font-size:12px;color:var(--t3);margin-bottom:14px;'>"
#         "Forward simulation · Supply disruption · Historical replay · LLM interpretation</div>",
#         unsafe_allow_html=True,
#     )

#     sim_tab, dis_tab, rep_tab = st.tabs(["📈  Demand Shock", "🔴  Supply Disruption", "↺  Historical Replay"])

#     # ── Demand Shock ──────────────────────────────────────────────────────────
#     with sim_tab:
#         st.markdown(
#             "<div style='padding:8px 0;font-size:12px;color:var(--t2);'>"
#             "<strong>Demand Shock</strong> simulates how different demand levels affect your stock over 6 months. "
#             "Use the shock month/multiplier to model sudden demand spikes (e.g. seasonal peak or unexpected order).</div>",
#             unsafe_allow_html=True,
#         )
#         cc2, rc = st.columns([1, 2])
#         with cc2:
#             sec("Controls")
#             sim_opts = {r["name"]: r["material"] for _, r in summary[summary.risk != "INSUFFICIENT_DATA"].iterrows()}
#             sn       = st.selectbox("Material", list(sim_opts.keys()), key="sm")
#             sid      = sim_opts[sn]
#             sr       = summary[summary.material == sid].iloc[0]
#             ad       = sr["avg_monthly_demand"]
#             ss_sim   = sr["safety_stock"]
#             lot_sim  = sr["lot_size"]
#             lt_sim   = sr["lead_time"]
#             st.markdown(
#                 f'<div class="chip" style="margin-bottom:8px;font-size:10px;">'
#                 f'SIH: {round(sr["sih"])} · SS: {round(ss_sim)} · LT: {round(lt_sim)}d · Lot: {round(lot_sim)}</div>',
#                 unsafe_allow_html=True,
#             )
#             st.markdown("<div style='font-size:10px;color:var(--t3);margin-bottom:4px;'>Expected demand/month</div>", unsafe_allow_html=True)
#             # Fix #15: Replace slider with number_input for granular control
#             ed  = st.number_input("Expected demand/month", min_value=int(ad * 0.3), max_value=int(ad * 3 + 50), value=int(ad), step=1, label_visibility="collapsed", key="exp_demand")
#             son = st.toggle("Add demand shock", False, key="son", help="Simulates a sudden spike in one specific month")
#             smo = smx = None
#             if son:
#                 st.markdown("<div style='font-size:10px;color:var(--t3);'>Shock month: which month the spike occurs</div>", unsafe_allow_html=True)
#                 smo = st.slider("Shock month", 1, 6, 2, key="smo")
#                 st.markdown("<div style='font-size:10px;color:var(--t3);'>Multiplier: how many times the normal demand</div>", unsafe_allow_html=True)
#                 smx = st.slider("Multiplier", 1.5, 5.0, 2.5, step=0.5, key="smx")
#             oon = st.toggle("Place order", False, key="oon", help="Simulates placing an emergency order that arrives after the lead time")
#             oq = ot = None
#             if oon:
#                 repl_default = max(
#                     int(max(ss_sim - sr["sih"], 0) / max(lot_sim, 1)) * int(lot_sim) if lot_sim > 0 else int(max(ss_sim - sr["sih"], 0)),
#                     100,
#                 )
#                 oq = st.slider("Order qty",       50, 2000, repl_default, step=50)
#                 ot = st.slider("Arrives (days)", 1, 60, int(lt_sim))
#             rsim = st.button("▶  Run Demand Simulation", use_container_width=True)

#         with rc:
#             sec("6-Month Projection")
#             if rsim or st.session_state.get("sim_ran"):
#                 mos  = 6
#                 stk  = sr["sih"]
#                 ss   = ss_sim
#                 scns = {"Low (−40%)": [ed * 0.6] * mos, "Expected": [ed] * mos, "High (+60%)": [ed * 1.6] * mos}
#                 if son and smo and smx:
#                     for k in scns:
#                         if k != "Low (−40%)":
#                             scns[k][smo - 1] = ed * smx
#                 oa  = int(ot / 30) if oon and ot else None
#                 fs  = go.Figure()
#                 scc = {"Low (−40%)": "#22C55E", "Expected": ORANGE, "High (+60%)": "#EF4444"}
#                 bi  = {}
#                 for sc_k, dems in scns.items():
#                     proj = []
#                     s    = stk
#                     for m, d in enumerate(dems):
#                         if oon and oq and m == oa:
#                             s += oq
#                         s = max(0.0, s - d)
#                         proj.append(s)
#                     bi[sc_k] = next((m + 1 for m, sp in enumerate(proj) if sp < max(ss, 1)), None)
#                     fs.add_trace(go.Scatter(
#                         x=[f"M{i+1}" for i in range(mos)], y=proj, mode="lines+markers", name=sc_k,
#                         line=dict(color=scc[sc_k], width=2.5), marker=dict(size=5, color=scc[sc_k]),
#                     ))
#                 if ss > 0:
#                     fs.add_hline(y=ss, line_color="#EF4444", line_dash="dot", line_width=1.5,
#                                  annotation_text=f"SAP SS ({round(ss)})",
#                                  annotation_font_color="#EF4444", annotation_font_size=9)
#                 ct(fs, 270)
#                 st.plotly_chart(fs, use_container_width=True)
#                 st.session_state["sim_ran"] = True

#                 vc = st.columns(3)
#                 for col, (sc_k, br) in zip(vc, bi.items()):
#                     cl  = "#EF4444" if br else "#22C55E"
#                     bg  = "#FEF2F2" if br else "#F0FDF4"
#                     txt = f"⛔ Breach M{br}" if br else "✓ Safe 6mo"
#                     with col:
#                         st.markdown(
#                             f"<div class='sc' style='padding:9px 11px;flex-direction:column;gap:2px;'>"
#                             f"<div style='font-size:9px;color:var(--t3);'>{sc_k}</div>"
#                             f"<div style='font-size:12px;font-weight:800;color:{cl};background:{bg};padding:3px 7px;border-radius:6px;'>{txt}</div>"
#                             f"</div>",
#                             unsafe_allow_html=True,
#                         )

#                 # Fix #16: Simplify replenishment formula note
#                 order_qty = int(math.ceil(max(0, ss - stk) / lot_sim) * lot_sim) if lot_sim > 0 else 0
#                 note(f"**Order quantity:** {order_qty} units (calculated as CEILING(shortfall / lot size) × lot size).")

#                 if st.session_state.azure_client and rsim:
#                     with st.spinner("ARIA evaluating…"):
#                         sv = simulate_scenario(
#                             st.session_state.azure_client, AZURE_DEPLOYMENT,
#                             sn, stk, ss, lt_sim, lot_sim,
#                             {"low": ed * 0.6, "expected": ed, "high": ed * 1.6},
#                             {"quantity": oq, "timing_days": ot} if oon else None,
#                         )
#                     urg  = sv.get("urgency", "MONITOR")
#                     uc   = {"ACT TODAY": "#EF4444", "ACT THIS WEEK": "#F59E0B", "MONITOR": ORANGE, "SAFE": "#22C55E"}.get(urg, ORANGE)
#                     st.markdown(
#                         f"<div class='ic' style='margin-top:10px;'><div class='il'>◈ ARIA Verdict</div>"
#                         f"<div style='display:flex;align-items:center;gap:8px;margin-bottom:6px;'>"
#                         f"<span style='font-size:12px;font-weight:800;color:{uc};'>{urg}</span>"
#                         f"<span class='chip'>Min order: {sv.get('min_order_recommended', '—')} units</span></div>"
#                         f"<div class='ib'>{sv.get('simulation_verdict', '')}</div></div>",
#                         unsafe_allow_html=True,
#                     )

#     # ── Supply Disruption ─────────────────────────────────────────────────────
#     with dis_tab:
#         st.markdown(
#             "<div style='padding:8px 0 10px;font-size:12px;color:var(--t2);'>"
#             "<strong>Supply Disruption</strong> simulates a freeze in replenishment across selected materials. "
#             "This models scenarios like supplier insolvency, geopolitical disruption, or production shutdown. "
#             "ARIA ranks which SKUs breach safety stock first and by how much.</div>",
#             unsafe_allow_html=True,
#         )
#         note("Formula: daily consumption × disruption days = stock consumed. "
#              "Breach = remaining stock < Safety Stock. Emergency order = CEILING(Shortfall/FLS)×FLS.")
#         dc2, dr = st.columns([1, 2])
#         with dc2:
#             sec("Disruption Parameters")
#             st.markdown("<div style='font-size:10px;color:var(--t3);margin-bottom:3px;'>Duration of supply freeze</div>", unsafe_allow_html=True)
#             disruption_days = st.slider("days", 7, 90, 30, step=7, label_visibility="collapsed", key="dis_days")
#             affected        = st.multiselect(
#                 "Affected materials (blank=all)",
#                 [r["name"] for _, r in summary[summary.risk != "INSUFFICIENT_DATA"].iterrows()],
#                 key="dis_mats",
#             )
#             run_dis = st.button("🔴  Run Disruption", use_container_width=True)

#         with dr:
#             sec("Impact — Ranked by Severity")
#             if run_dis or st.session_state.get("dis_ran"):
#                 adis = summary[summary.risk != "INSUFFICIENT_DATA"]
#                 if affected:
#                     adis = adis[adis.name.isin(affected)]
#                 sku_data = [{
#                     "material": r["material"], "name": r["name"],
#                     "current_stock": r["sih"], "safety_stock": r["safety_stock"],
#                     "lead_time": r["lead_time"], "fixed_lot_size": r["lot_size"],
#                     "avg_monthly_demand": r["avg_monthly_demand"], "risk": r["risk"],
#                 } for _, r in adis.iterrows()]
#                 results = simulate_multi_sku_disruption(None, None, disruption_days, sku_data)
#                 st.session_state["dis_ran"] = True

#                 for i, r in enumerate(results):
#                     bc   = r["breach_occurs"]
#                     brd  = "#EF4444" if bc else "#22C55E"
#                     bgc  = "rgba(239,68,68,0.03)" if bc else "#FFFFFF"
#                     days_txt = (f"Breach Day {r['days_to_breach']}" if bc and r["days_to_breach"] is not None
#                                 else ("Already breached" if bc else f"Safe for {disruption_days}d"))
#                     metric_cells = ""
#                     for val, lbl, c in [
#                         (str(r["stock_at_end"]), "End",   "#EF4444" if r["shortfall_units"] > 0 else "#22C55E"),
#                         (str(r["shortfall_units"]), "Short", "#EF4444" if r["shortfall_units"] > 0 else "#94A3B8"),
#                         (f"{r['lead_time']}d", "LT",   "#1E293B"),
#                         (str(r["reorder_qty"]), "Order", "#EF4444" if r["reorder_qty"] > 0 else "#94A3B8"),
#                     ]:
#                         metric_cells += (
#                             f"<div style='background:var(--s3);border-radius:5px;padding:4px;'>"
#                             f"<div style='font-size:11px;font-weight:800;color:{c};'>{val}</div>"
#                             f"<div style='font-size:8px;color:var(--t3);'>{lbl}</div></div>"
#                         )
#                     st.markdown(
#                         f"<div class='prow' style='border-left:3px solid {brd};background:{bgc};margin-bottom:6px;'>"
#                         f"<div style='min-width:22px;font-size:13px;font-weight:900;color:{brd};'>{i+1}</div>"
#                         f"<div style='font-size:16px;'>{'⛔' if bc else '✓'}</div>"
#                         f"<div style='flex:1;'>"
#                         f"<div style='font-size:12px;font-weight:800;color:var(--t);'>{r['name']}</div>"
#                         f"<div style='font-size:10px;color:{brd};font-weight:600;margin-top:1px;'>{days_txt}</div>"
#                         f"</div>"
#                         f"<div style='display:grid;grid-template-columns:repeat(4,62px);gap:4px;text-align:center;'>"
#                         + metric_cells +
#                         f"</div></div>",
#                         unsafe_allow_html=True,
#                     )

#                 if st.session_state.azure_client and run_dis:
#                     breached = [r for r in results if r["breach_occurs"]]
#                     if breached:
#                         ctx_dis = (f"Disruption: {disruption_days}d freeze. "
#                                    f"Breaches: {', '.join([r['name'] for r in breached])}. "
#                                    f"Worst: {breached[0]['name']} on day {breached[0]['days_to_breach'] or 0}.")
#                         with st.spinner("ARIA evaluating…"):
#                             dv = chat_with_data(
#                                 st.session_state.azure_client, AZURE_DEPLOYMENT,
#                                 "2-sentence executive verdict on this supply disruption. What is most critical?",
#                                 ctx_dis,
#                             )
#                         st.markdown(
#                             f"<div class='ic' style='margin-top:10px;'>"
#                             f"<div class='il'>◈ ARIA DISRUPTION VERDICT</div>"
#                             f"<div class='ib' style='margin-top:4px;'>{dv}</div></div>",
#                             unsafe_allow_html=True,
#                         )

#     # ── Historical Replay ──────────────────────────────────────────────────────
#     with rep_tab:
#         st.markdown(
#             "<div style='padding:8px 0 10px;font-size:12px;color:var(--t2);'>"
#             "<strong>Historical Replay</strong> shows what actually happened in a past period and reconstructs "
#             "when ARIA would have triggered an order signal — demonstrating the value of predictive replenishment.</div>",
#             unsafe_allow_html=True,
#         )
#         rp_opts = {r["name"]: r["material"] for _, r in summary[summary.risk != "INSUFFICIENT_DATA"].iterrows()}
#         rp_sn   = st.selectbox("Material", list(rp_opts.keys()), key="rp_mat")
#         rp_sid  = rp_opts[rp_sn]
#         rp_sr   = summary[summary.material == rp_sid].iloc[0]
#         shrp    = get_stock_history(st.session_state.data, rp_sid)
#         pds_lbl = shrp["label"].tolist()

#         if len(pds_lbl) > 4:
#             rps = st.selectbox("Replay from period", pds_lbl[:-3],
#                                index=min(8, len(pds_lbl) - 4), key="rps")
#             if st.button("↺  Replay this period", key="rpb"):
#                 idx = pds_lbl.index(rps)
#                 rd  = shrp.iloc[idx:idx + 6]
#                 ssr = rp_sr["safety_stock"]
#                 fr  = go.Figure()
#                 fr.add_trace(go.Scatter(
#                     x=rd["label"], y=rd["Gross Stock"], mode="lines+markers", name="Actual Stock",
#                     line=dict(color=ORANGE, width=2.5), marker=dict(size=7, color=ORANGE),
#                     fill="tozeroy", fillcolor="rgba(244,123,37,0.07)",
#                     hovertemplate="<b>%{x}</b><br>%{y} units<extra></extra>",
#                 ))
#                 if ssr > 0:
#                     fr.add_hline(y=ssr, line_color="#EF4444", line_dash="dot",
#                                  annotation_text=f"SAP SS {round(ssr)}", annotation_font_color="#EF4444")
#                 br2 = rd[rd["Gross Stock"] < max(ssr, 1)]
#                 if len(br2) > 0:
#                     bp       = br2.iloc[0]["label"]
#                     current_idx = rd.index.tolist().index(br2.index[0])
#                     prev_idx = max(0, current_idx - 1)  # Fix #9: prevent negative index
#                     fr.add_vline(x=bp, line_color="#EF4444", line_dash="dash",
#                                  annotation_text="⛔ Breach", annotation_font_color="#EF4444")
#                     fr.add_vline(x=rd.iloc[prev_idx]["label"], line_color="#22C55E", line_dash="dash",
#                                  annotation_text="◈ ARIA signal", annotation_font_color="#22C55E")
#                 ct(fr, 260)
#                 st.plotly_chart(fr, use_container_width=True)
#                 msg = ("⛔ Breach detected. ARIA would have signalled an order one period earlier."
#                        if len(br2) > 0 else
#                        "✓ No breach in this period — stock remained above safety stock.")
#                 mc2 = "#EF4444" if len(br2) > 0 else "#22C55E"
#                 mb2 = "#FEF2F2" if len(br2) > 0 else "#F0FDF4"
#                 st.markdown(
#                     f"<div style='font-size:11px;color:{mc2};padding:7px 11px;background:{mb2};border-radius:8px;'>{msg}</div>",
#                     unsafe_allow_html=True,
#                 )

#     st.markdown('<div class="pfooter">⚡ Powered by <strong>MResult</strong></div>', unsafe_allow_html=True)

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
            # Fix #15: number input for granular control
            ed  = st.number_input("Expected demand/month", min_value=int(ad * 0.3), max_value=int(ad * 3 + 50), value=int(ad), step=1, label_visibility="collapsed", key="exp_demand")
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
                oq = st.slider("Order qty",       50, 2000, repl_default, step=50)
                ot = st.slider("Arrives (days)", 1, 60, int(lt_sim))
            rsim = st.button("▶  Run Demand Simulation", use_container_width=True)

        with rc:
            sec("6-Month Projection")
            if rsim or st.session_state.get("sim_ran"):
                mos  = 6
                stk  = sr["sih"]
                ss   = ss_sim
                scns = {"Low (−40%)": [ed * 0.6] * mos, "Expected": [ed] * mos, "High (+60%)": [ed * 1.6] * mos}
                if son and smo and smx:
                    for k in scns:
                        if k != "Low (−40%)":
                            scns[k][smo - 1] = ed * smx
                oa  = int(ot / 30) if oon and ot else None
                fs  = go.Figure()
                scc = {"Low (−40%)": "#22C55E", "Expected": ORANGE, "High (+60%)": "#EF4444"}
                bi  = {}  # breach months for each scenario
                for sc_k, dems in scns.items():
                    proj = []
                    s    = stk
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
                    cl  = "#EF4444" if br else "#22C55E"
                    bg  = "#FEF2F2" if br else "#F0FDF4"
                    txt = f"⛔ Breach M{br}" if br else "✓ Safe 6mo"
                    with col:
                        st.markdown(
                            f"<div class='sc' style='padding:9px 11px;flex-direction:column;gap:2px;'>"
                            f"<div style='font-size:9px;color:var(--t3);'>{sc_k}</div>"
                            f"<div style='font-size:12px;font-weight:800;color:{cl};background:{bg};padding:3px 7px;border-radius:6px;'>{txt}</div>"
                            f"</div>",
                            unsafe_allow_html=True,
                        )

                # Fix #16: Simplified replenishment note
                order_qty = int(math.ceil(max(0, ss - stk) / lot_sim) * lot_sim) if lot_sim > 0 else 0
                note(f"**Order quantity:** {order_qty} units (calculated as CEILING(shortfall / lot size) × lot size).")

                # Fix #4a: Manual fallback explanation for ARIA Verdict
                manual_explanation = ""
                if bi.get("Expected") is not None:
                    manual_explanation = f"In the Expected demand scenario, a stockout would occur in month {bi['Expected']}. "
                else:
                    manual_explanation = "In the Expected demand scenario, stock remains above safety stock for 6 months. "
                if bi.get("Low (−40%)") is not None:
                    manual_explanation += f"Under Low demand, stockout in month {bi['Low (−40%)']}. "
                else:
                    manual_explanation += "Under Low demand, no stockout. "
                if bi.get("High (+60%)") is not None:
                    manual_explanation += f"Under High demand, stockout in month {bi['High (+60%)']}."

                if st.session_state.azure_client and rsim:
                    with st.spinner("ARIA evaluating…"):
                        sv = simulate_scenario(
                            st.session_state.azure_client, AZURE_DEPLOYMENT,
                            sn, stk, ss, lt_sim, lot_sim,
                            {"low": ed * 0.6, "expected": ed, "high": ed * 1.6},
                            {"quantity": oq, "timing_days": ot} if oon else None,
                        )
                    # Replace the generic LLM failure message with manual explanation
                    if sv.get("simulation_verdict") == "Simulation completed, but ARIA could not generate a verdict. Please review the graph manually.":
                        sv["simulation_verdict"] = manual_explanation
                    urg  = sv.get("urgency", "MONITOR")
                    uc   = {"ACT TODAY": "#EF4444", "ACT THIS WEEK": "#F59E0B", "MONITOR": ORANGE, "SAFE": "#22C55E"}.get(urg, ORANGE)
                    st.markdown(
                        f"<div class='ic' style='margin-top:10px;'><div class='il'>◈ ARIA Verdict</div>"
                        f"<div style='display:flex;align-items:center;gap:8px;margin-bottom:6px;'>"
                        f"<span style='font-size:12px;font-weight:800;color:{uc};'>{urg}</span>"
                        f"<span class='chip'>Min order: {sv.get('min_order_recommended', '—')} units</span></div>"
                        f"<div class='ib'>{sv.get('simulation_verdict', '')}</div></div>",
                        unsafe_allow_html=True,
                    )
                elif rsim and not st.session_state.azure_client:
                    # No Azure client – just show manual explanation
                    st.markdown(
                        f"<div class='ic' style='margin-top:10px;'><div class='il'>◈ ARIA Verdict (Manual)</div>"
                        f"<div class='ib'>{manual_explanation}</div></div>",
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
            affected        = st.multiselect(
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

                for i, r in enumerate(results):
                    bc   = r["breach_occurs"]
                    brd  = "#EF4444" if bc else "#22C55E"
                    bgc  = "rgba(239,68,68,0.03)" if bc else "#FFFFFF"
                    days_txt = (f"Breach Day {r['days_to_breach']}" if bc and r["days_to_breach"] is not None
                                else ("Already breached" if bc else f"Safe for {disruption_days}d"))
                    metric_cells = ""
                    for val, lbl, c in [
                        (str(r["stock_at_end"]), "End",   "#EF4444" if r["shortfall_units"] > 0 else "#22C55E"),
                        (str(r["shortfall_units"]), "Short", "#EF4444" if r["shortfall_units"] > 0 else "#94A3B8"),
                        (f"{r['lead_time']}d", "LT",   "#1E293B"),
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
                        st.markdown(
                            f"<div class='ic' style='margin-top:10px;'>"
                            f"<div class='il'>◈ ARIA DISRUPTION VERDICT</div>"
                            f"<div class='ib' style='margin-top:4px;'>{dv}</div></div>",
                            unsafe_allow_html=True,
                        )

    # ── Historical Replay (Fix #4b: prev_idx bounds) ──────────────────────────
    with rep_tab:
        st.markdown(
            "<div style='padding:8px 0 10px;font-size:12px;color:var(--t2);'>"
            "<strong>Historical Replay</strong> shows what actually happened in a past period and reconstructs "
            "when ARIA would have triggered an order signal — demonstrating the value of predictive replenishment.</div>",
            unsafe_allow_html=True,
        )
        rp_opts = {r["name"]: r["material"] for _, r in summary[summary.risk != "INSUFFICIENT_DATA"].iterrows()}
        rp_sn   = st.selectbox("Material", list(rp_opts.keys()), key="rp_mat")
        rp_sid  = rp_opts[rp_sn]
        rp_sr   = summary[summary.material == rp_sid].iloc[0]
        shrp    = get_stock_history(st.session_state.data, rp_sid)
        pds_lbl = shrp["label"].tolist()

        if len(pds_lbl) > 4:
            rps = st.selectbox("Replay from period", pds_lbl[:-3],
                               index=min(8, len(pds_lbl) - 4), key="rps")
            if st.button("↺  Replay this period", key="rpb"):
                idx = pds_lbl.index(rps)
                rd  = shrp.iloc[idx:idx + 6]
                ssr = rp_sr["safety_stock"]
                fr  = go.Figure()
                fr.add_trace(go.Scatter(
                    x=rd["label"], y=rd["Gross Stock"], mode="lines+markers", name="Actual Stock",
                    line=dict(color=ORANGE, width=2.5), marker=dict(size=7, color=ORANGE),
                    fill="tozeroy", fillcolor="rgba(244,123,37,0.07)",
                    hovertemplate="<b>%{x}</b><br>%{y} units<extra></extra>",
                ))
                if ssr > 0:
                    fr.add_hline(y=ssr, line_color="#EF4444", line_dash="dot",
                                 annotation_text=f"SAP SS {round(ssr)}", annotation_font_color="#EF4444")
                br2 = rd[rd["Gross Stock"] < max(ssr, 1)]
                if len(br2) > 0:
                    bp       = br2.iloc[0]["label"]
                    current_idx = rd.index.tolist().index(br2.index[0])
                    # Fix #4b: prevent negative index
                    prev_idx = max(0, current_idx - 1)
                    fr.add_vline(x=bp, line_color="#EF4444", line_dash="dash",
                                 annotation_text="⛔ Breach", annotation_font_color="#EF4444")
                    fr.add_vline(x=rd.iloc[prev_idx]["label"], line_color="#22C55E", line_dash="dash",
                                 annotation_text="◈ ARIA signal", annotation_font_color="#22C55E")
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
