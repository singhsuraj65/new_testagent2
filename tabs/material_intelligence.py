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
# # #         key_findings = analysis.get("key_findings", [])
# # #         if not isinstance(key_findings, list):
# # #             key_findings = [str(key_findings)]
# # #         else:
# # #             key_findings = [str(f) for f in key_findings]
# # #         fh = "".join(f'<div class="iff"><div class="ifd"></div><div>{f}</div></div>' for f in key_findings)

# # #         conf       = str(analysis.get("data_confidence", "MEDIUM"))
# # #         conf_clean = conf.split("—")[0].split("-")[0].strip().upper()[:6]
# # #         cc         = "#22C55E" if "HIGH" in conf_clean else "#F59E0B" if "MEDIUM" in conf_clean else "#EF4444"

# # #         dq      = analysis.get("data_quality_flags", [])
# # #         dq_html = (
# # #             "<div style='margin-top:10px;padding-top:8px;border-top:1px solid var(--bl);'>"
# # #             + "".join(f'<div style="font-size:10px;color:#F59E0B;margin:2px 0;">⚠ {f}</div>' for f in dq)
# # #             + "</div>"
# # #         ) if dq else ""

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

# # #         ca, cb = st.columns(2)
# # #         sap_gap = analysis.get("sap_gap", "")
# # #         if not isinstance(sap_gap, str):
# # #             sap_gap = str(sap_gap)
# # #         recom = analysis.get("recommendation", "")
# # #         if not isinstance(recom, str):
# # #             recom = str(recom)

# # #         if "Unable to parse" in sap_gap:
# # #             sap_gap = (f"SAP Safety Stock: {mat_row['safety_stock']:.0f} units. "
# # #                        f"ARIA recommends: {mat_row['rec_safety_stock']:.0f} units. "
# # #                        f"Gap: {mat_row['rec_safety_stock'] - mat_row['safety_stock']:.0f} units.")
# # #         if "No replenishment triggered" in recom and mat_row["repl_triggered"]:
# # #             recom = (f"Order {int(mat_row['repl_quantity'])} units immediately. "
# # #                      f"Stock-in-Hand ({mat_row['sih']:.0f}) below SAP SS ({mat_row['safety_stock']:.0f}). "
# # #                      f"Lead time: {mat_row['lead_time']:.0f}d. Formula: {mat_row['repl_formula']}")
# # #         with ca:
# # #             st.markdown(f"<div class='sap-box'><div class='sap-lbl'>SAP Gap Assessment</div>{sap_gap}</div>", unsafe_allow_html=True)
# # #         with cb:
# # #             st.markdown(
# # #                 f"<div class='rec-box'><div class='rec-lbl'>ARIA Recommendation</div>"
# # #                 f"<pre style='font-size:11px;white-space:pre-wrap;margin:0;color:#14532d;'>{recom}</pre>"
# # #                 f"<div style='margin-top:5px;font-size:10px;opacity:0.75;'>If ignored: {analysis.get('risk_if_ignored', '')}</div></div>",
# # #                 unsafe_allow_html=True,
# # #             )

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

# # #     # ── Monte Carlo ───────────────────────────────────────────────────────────
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

# # #     # ── Safety Stock Audit + Replenishment ────────────────────────────────────
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

# # #         if st.session_state.azure_client and analysis:
# # #             if st.button("◈ Get SS Recommendation", key="ss_rec"):
# # #                 with st.spinner("ARIA analysing safety stock…"):
# # #                     ss_ctx  = (f"Material: {sel_name}, SAP SS: {ss_v:.0f}, ARIA SS: {rec:.0f}, "
# # #                                f"Lead time: {lt_v:.0f}d, Avg demand: {avg_d:.0f}/mo, Std: {std_d:.0f}, "
# # #                                f"Current stock: {mat_row['sih']:.0f}, Breach count: {mat_row['breach_count']}, "
# # #                                f"Monte Carlo breach probability: "
# # #                                f"{run_monte_carlo(mat_row['sih'], ss_v, avg_d, std_d, lt_v)['probability_breach_pct']}%")
# # #                     rec_txt = chat_with_data(
# # #                         st.session_state.azure_client, AZURE_DEPLOYMENT,
# # #                         "Should the safety stock be adjusted? Give a specific recommendation with reasoning and the recommended value.",
# # #                         ss_ctx,
# # #                     )
# # #                 st.markdown(
# # #                     f"<div class='ic' style='margin-top:8px;'><div class='il'>◈ SS Recommendation</div>"
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

# # #     # ── Supplier Consolidation ────────────────────────────────────────────────
# # #     consol   = get_supplier_consolidation(data, summary)
# # #     relevant = consol[
# # #         consol.material_list.apply(lambda x: sel_mat in x)
# # #         & (consol.finished_goods_supplied > 1)
# # #     ]
# # #     if len(relevant) > 0:
# # #         sec("Supplier Consolidation Opportunities")
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

# #         # SAP Gap and ARIA Recommendation (Fix #3: clean bullet list for recommendation)
# #         ca, cb = st.columns(2)
# #         sap_gap = analysis.get("sap_gap", "")
# #         if not isinstance(sap_gap, str):
# #             sap_gap = str(sap_gap)
# #         recom_raw = analysis.get("recommendation", "")
# #         # If recommendation is a dict, convert to readable bullet list
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
# #             # Fallback: if it's a string but contains a dict representation, try to parse
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

# #     # ── Monte Carlo Risk Simulation (Fix #4: add explanation expander) ─────────
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

# #         # Fix #4: Monte Carlo explanation expander
# #         with st.expander("📖 What is Monte Carlo simulation?"):
# #             st.markdown("""
# #             - **Monte Carlo simulation** runs 1,000 possible future demand scenarios based on historical mean and standard deviation.
# #             - The **probability of stockout** shows the percentage of scenarios where stock falls below the safety stock in the next 6 months.
# #             - The **outcome range** (P10, P50, P90) shows the possible ending stock levels under pessimistic, median, and optimistic conditions.
# #             - The **histogram** visualises the distribution of possible ending stock levels.
# #             """)

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

# #     # ── Safety Stock Audit ────────────────────────────────────────────────────
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

# #         # Fix #5: Change button to "Explain ARIA SS Recommendation"
# #         if st.session_state.azure_client and analysis:
# #             if st.button("◈ Explain ARIA SS Recommendation", key="ss_rec"):
# #                 with st.spinner("ARIA analysing safety stock…"):
# #                     ss_ctx  = (f"Material: {sel_name}, SAP SS: {ss_v:.0f}, ARIA SS: {rec:.0f}, "
# #                                f"Lead time: {lt_v:.0f}d, Avg demand: {avg_d:.0f}/mo, Std: {std_d:.0f}, "
# #                                f"Current stock: {mat_row['sih']:.0f}, Breach count: {mat_row['breach_count']}, "
# #                                f"Monte Carlo breach probability: "
# #                                f"{run_monte_carlo(mat_row['sih'], ss_v, avg_d, std_d, lt_v)['probability_breach_pct']}%")
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
# #                 f"<tr><td style='color:#475569;padding:2px 0;'>Lead Time (MM)</td><td style='font-weight:700;text-align:right;'>{round(lt_v)}d</td></tr>"
# #                 f"<tr><td style='color:#475569;padding:2px 0;'>Lot Size (Curr Inv)</td><td style='font-weight:700;text-align:right;'>{round(mat_row['lot_size'])} units</td></tr>"
# #                 f"<tr style='border-top:1px solid #E2E8F0;'><td style='color:#EF4444;font-weight:800;padding:4px 0;'>Order Quantity</td><td style='font-weight:900;font-size:15px;color:#EF4444;text-align:right;'>{repl_q} units</td></tr>"
# #                 f"<tr><td colspan='2' style='font-size:9px;color:#94A3B8;padding-top:3px;'>{repl_f}</td></tr>"
# #                 f"</table></div>",
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
# #         note("Data source: BOM file (Supplier Name column).")   # Fix #6
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

#         # SAP Gap and ARIA Recommendation (Fix #3: clean bullet list)
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

#     # ── Monte Carlo Risk Simulation (Fix #4: add explanation expander) ─────────
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

#         # Fix #4: Monte Carlo explanation expander
#         with st.expander("📖 What is Monte Carlo simulation?"):
#             st.markdown("""
#             - **Monte Carlo simulation** runs 1,000 possible future demand scenarios based on historical mean and standard deviation.
#             - The **probability of stockout** shows the percentage of scenarios where stock falls below the safety stock in the next 6 months.
#             - The **outcome range** (P10, P50, P90) shows the possible ending stock levels under pessimistic, median, and optimistic conditions.
#             - The **histogram** visualises the distribution of possible ending stock levels.
#             """)

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

#     # ── Safety Stock Audit (Fix #5: button label and prompt changed) ──────────
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

#         # Fix #5: Change button label and prompt
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
#         # Fix #6: Add source note
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

"""
tabs/material_intelligence.py
Material Intelligence tab: agentic analysis, Monte Carlo simulation,
stock trajectory, safety stock audit, BOM components, supplier email draft,
and consolidation opportunities.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode

from utils.helpers import ct, fmt_p, sbadge, sec, note, ORANGE, AZURE_DEPLOYMENT
from data_loader import (
    get_stock_history, get_demand_history, get_bom_components,
    get_material_context, get_supplier_consolidation,
)
from agent import analyse_material, chat_with_data, run_monte_carlo, draft_supplier_email

_AGGRID_CSS = {
    ".ag-root-wrapper": {"border": "1px solid #E2E8F0!important", "border-radius": "12px!important"},
    ".ag-header":       {"background": "#F8FAFE!important"},
    ".ag-row-even":     {"background": "#FFFFFF!important"},
    ".ag-row-odd":      {"background": "#F8FAFE!important"},
}


def render():
    data           = st.session_state.data
    summary        = st.session_state.summary
    MATERIAL_LABELS = st.session_state.material_labels

    mat_opts = {row["name"]: row["material"] for _, row in summary.iterrows()}
    sel_name = st.selectbox("Select Material", list(mat_opts.keys()), key="mi_mat",
                            help="Select a finished good to analyse")
    sel_mat  = mat_opts[sel_name]
    mat_row  = summary[summary.material == sel_mat].iloc[0]
    risk     = mat_row["risk"]

    # ── Insufficient data guard ───────────────────────────────────────────────
    if risk == "INSUFFICIENT_DATA":
        reasons = []
        if mat_row["nonzero_demand_months"] < 3:
            reasons.append(f"Only {mat_row['nonzero_demand_months']} months demand (min 6)")
        if mat_row["zero_periods"] > 10:
            reasons.append(f"Zero stock in {mat_row['zero_periods']}/{mat_row['total_periods']} periods")
        if sel_mat == "3515-0010":
            reasons.append("Marked inactive in sales history")
        r_html = "".join(f'<div style="font-size:11px;color:var(--t3);margin:3px 0;">• {r}</div>' for r in reasons)
        st.markdown(
            f"<div style='display:flex;align-items:center;gap:12px;margin-bottom:16px;'>"
            f"<div style='font-size:18px;font-weight:800;'>{sel_name}</div>{sbadge(risk)}</div>"
            f"<div class='flag-box' style='max-width:520px;'>"
            f"<div style='font-size:22px;margin-bottom:8px;'>◌</div>"
            f"<div style='font-size:14px;font-weight:800;color:var(--t2);margin-bottom:5px;'>Insufficient Data for ARIA Analysis</div>"
            f"<div style='font-size:12px;color:var(--t3);margin-bottom:8px;'>Requires 6+ months confirmed demand history.</div>"
            f"{r_html}</div>",
            unsafe_allow_html=True,
        )
        st.stop()

    # ── Header ────────────────────────────────────────────────────────────────
    h1c, h2c = st.columns([5, 1])
    with h1c:
        dq_flags   = mat_row.get("data_quality_flags", [])
        flags_html = "".join(
            f'<span class="chip" style="margin-right:4px;color:#F59E0B;border-color:#F59E0B40;">⚠ {f}</span>'
            for f in dq_flags[:2]
        ) if dq_flags else ""
        st.markdown(
            f"<div style='display:flex;align-items:center;flex-wrap:wrap;gap:8px;margin-bottom:6px;'>"
            f"<div style='font-size:18px;font-weight:900;'>{sel_name}</div>"
            f"{sbadge(risk)}<div class='chip'>{sel_mat}</div>{flags_html}</div>",
            unsafe_allow_html=True,
        )
    with h2c:
        run_an = st.button("◈ Analyse", use_container_width=True, key=f"analyse_btn_{sel_mat}")

    # ── ARIA Analysis ─────────────────────────────────────────────────────────
    analysis = st.session_state.agent_cache.get(sel_mat)
    if run_an:
        if st.session_state.azure_client:
            with st.spinner("ARIA investigating…"):
                ctx      = get_material_context(data, sel_mat, summary)
                analysis = analyse_material(st.session_state.azure_client, AZURE_DEPLOYMENT, ctx)
                st.session_state.agent_cache[sel_mat]  = analysis
                st.session_state.last_analysed_mat     = sel_mat
        else:
            st.markdown(
                "<div style='padding:9px 12px;background:var(--ob);border:1px solid var(--obr);"
                "border-radius:9px;font-size:12px;color:var(--or);'>"
                "Enter Azure API key in sidebar to enable ARIA analysis.</div>",
                unsafe_allow_html=True,
            )

    if analysis and st.session_state.agent_cache.get(sel_mat):
        # Key findings
        key_findings = analysis.get("key_findings", [])
        if not isinstance(key_findings, list):
            key_findings = [str(key_findings)]
        else:
            key_findings = [str(f) for f in key_findings]
        fh = "".join(f'<div class="iff"><div class="ifd"></div><div>{f}</div></div>' for f in key_findings)

        # Confidence
        conf       = str(analysis.get("data_confidence", "MEDIUM"))
        conf_clean = conf.split("—")[0].split("-")[0].strip().upper()[:6]
        cc         = "#22C55E" if "HIGH" in conf_clean else "#F59E0B" if "MEDIUM" in conf_clean else "#EF4444"

        # Data quality flags
        dq      = analysis.get("data_quality_flags", [])
        dq_html = (
            "<div style='margin-top:10px;padding-top:8px;border-top:1px solid var(--bl);'>"
            + "".join(f'<div style="font-size:10px;color:#F59E0B;margin:2px 0;">⚠ {f}</div>' for f in dq)
            + "</div>"
        ) if dq else ""

        # Display ARIA Intelligence box
        st.markdown(
            f"<div class='ic'><div class='il'>◈ ARIA Intelligence</div>"
            f"<div class='ih'>{analysis.get('headline', '')}</div>"
            f"<div class='ib'>{analysis.get('executive_summary', '')}</div>"
            f"<div style='margin-top:10px;border-top:1px solid var(--bl);padding-top:10px;'>"
            f"<div style='font-size:9px;font-weight:700;color:var(--or);text-transform:uppercase;letter-spacing:1px;margin-bottom:6px;'>Key Findings</div>"
            f"{fh}{dq_html}</div>"
            f"<div style='margin-top:8px;font-size:10px;color:var(--t3);'>"
            f"Confidence: <span style='color:{cc};font-weight:700;'>{conf_clean}</span>"
            f"</div></div>",
            unsafe_allow_html=True,
        )

        # SAP Gap and ARIA Recommendation (clean bullet list)
        ca, cb = st.columns(2)
        sap_gap = analysis.get("sap_gap", "")
        if not isinstance(sap_gap, str):
            sap_gap = str(sap_gap)
        recom_raw = analysis.get("recommendation", "")
        
        # Convert recommendation to a clean bullet list if it's a dict or dict-like string
        if isinstance(recom_raw, dict):
            recom_lines = []
            for k, v in recom_raw.items():
                if k.lower() == "reason":
                    recom_lines.append(f"<strong>Reason:</strong> {v}")
                else:
                    recom_lines.append(f"<strong>{k}:</strong> {v}")
            recom = "<ul style='margin:0; padding-left:16px; font-size:11px; color:#14532d;'>" + "".join(f"<li>{line}</li>" for line in recom_lines) + "</ul>"
        else:
            recom = str(recom_raw)
            # Try to parse if it looks like a dictionary string
            if recom.startswith("{") and "SKU" in recom:
                try:
                    import ast
                    d = ast.literal_eval(recom)
                    if isinstance(d, dict):
                        recom_lines = [f"<strong>{k}:</strong> {v}" for k, v in d.items()]
                        recom = "<ul style='margin:0; padding-left:16px; font-size:11px; color:#14532d;'>" + "".join(f"<li>{line}</li>" for line in recom_lines) + "</ul>"
                except:
                    pass

        if "Unable to parse" in sap_gap:
            sap_gap = (f"SAP Safety Stock: {mat_row['safety_stock']:.0f} units. "
                       f"ARIA recommends: {mat_row['rec_safety_stock']:.0f} units. "
                       f"Gap: {mat_row['rec_safety_stock'] - mat_row['safety_stock']:.0f} units.")
        if "No replenishment triggered" in str(recom_raw) and mat_row["repl_triggered"]:
            recom = (f"<strong>Order {int(mat_row['repl_quantity'])} units immediately.</strong><br>"
                     f"Stock-in-Hand ({mat_row['sih']:.0f}) below SAP SS ({mat_row['safety_stock']:.0f}).<br>"
                     f"Lead time: {mat_row['lead_time']:.0f}d. Formula: {mat_row['repl_formula']}")

        with ca:
            st.markdown(f"<div class='sap-box'><div class='sap-lbl'>SAP Gap Assessment</div>{sap_gap}</div>", unsafe_allow_html=True)
        with cb:
            st.markdown(
                f"<div class='rec-box'><div class='rec-lbl'>ARIA Recommendation</div>"
                f"{recom}"
                f"<div style='margin-top:8px;font-size:10px;opacity:0.75;'>If ignored: {analysis.get('risk_if_ignored', '')}</div></div>",
                unsafe_allow_html=True,
            )

        # Supplier action
        sup_action = analysis.get("supplier_action")
        if sup_action:
            st.markdown(
                f"<div style='padding:8px 12px;background:rgba(59,130,246,0.06);"
                f"border:1px solid rgba(59,130,246,0.2);border-radius:8px;font-size:11px;color:#1d4ed8;margin-top:8px;'>"
                f"📧 <strong>Supplier Action:</strong> {sup_action}</div>",
                unsafe_allow_html=True,
            )
    elif not run_an:
        st.markdown(
            "<div style='padding:12px 14px;background:var(--s2);border:1px solid var(--bl);"
            "border-radius:var(--r);font-size:12px;color:var(--t3);text-align:center;'>"
            "Click <strong style='color:var(--or);'>◈ Analyse</strong> above to run ARIA intelligence on this material.</div>",
            unsafe_allow_html=True,
        )

    # ── Monte Carlo Risk Simulation (with note() instead of expander) ─────────
    sec("Monte Carlo Risk Simulation — 1,000 Demand Scenarios")
    note("Runs 1,000 simulations of 6-month demand using historical mean & std deviation. "
         "Shows probability of stockout and range of outcomes.")
    avg_d = mat_row["avg_monthly_demand"]
    std_d = mat_row["std_demand"]
    ss_v  = mat_row["safety_stock"]
    rec   = mat_row["rec_safety_stock"]
    lt_v  = mat_row["lead_time"]

    if avg_d > 0 and std_d > 0:
        mc = run_monte_carlo(mat_row["sih"], ss_v, avg_d, std_d, lt_v, months=6, n_sims=1000)
        risk_color = {"HIGH RISK": "#EF4444", "MODERATE RISK": "#F59E0B",
                      "LOW RISK": "#22C55E", "VERY LOW RISK": "#22C55E"}.get(mc["verdict"], ORANGE)

        mc_col1, mc_col2, mc_col3 = st.columns(3)
        with mc_col1:
            st.markdown(
                f"<div class='sc' style='flex-direction:column;align-items:center;padding:16px;'>"
                f"<div style='font-size:28px;font-weight:900;color:{risk_color};'>{mc['probability_breach_pct']}%</div>"
                f"<div style='font-size:11px;color:var(--t3);text-align:center;'>Probability of stockout<br>in next 6 months</div>"
                f"<div style='font-size:12px;font-weight:700;color:{risk_color};margin-top:4px;'>{mc['verdict']}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )
        with mc_col2:
            st.markdown(
                f"<div class='sc' style='flex-direction:column;gap:0;'>"
                f"<div style='font-size:10px;color:var(--t3);margin-bottom:8px;font-weight:600;'>OUTCOME RANGE (6mo)</div>"
                f"<div style='display:flex;justify-content:space-between;margin-bottom:4px;'>"
                f"<span style='font-size:10px;color:var(--t3);'>Pessimistic (P10)</span>"
                f"<span style='font-size:12px;font-weight:700;color:#EF4444;'>{int(mc['p10_end_stock'])} units</span></div>"
                f"<div style='display:flex;justify-content:space-between;margin-bottom:4px;'>"
                f"<span style='font-size:10px;color:var(--t3);'>Median (P50)</span>"
                f"<span style='font-size:12px;font-weight:700;color:{ORANGE};'>{int(mc['p50_end_stock'])} units</span></div>"
                f"<div style='display:flex;justify-content:space-between;'>"
                f"<span style='font-size:10px;color:var(--t3);'>Optimistic (P90)</span>"
                f"<span style='font-size:12px;font-weight:700;color:#22C55E;'>{int(mc['p90_end_stock'])} units</span></div>"
                f"</div>",
                unsafe_allow_html=True,
            )
        with mc_col3:
            if mc["avg_breach_month"]:
                st.markdown(
                    f"<div class='sc' style='flex-direction:column;align-items:center;padding:16px;'>"
                    f"<div style='font-size:28px;font-weight:900;color:#EF4444;'>M{mc['avg_breach_month']}</div>"
                    f"<div style='font-size:11px;color:var(--t3);text-align:center;'>Average month when<br>stockout occurs</div>"
                    f"<div style='font-size:10px;color:var(--t3);margin-top:4px;'>Based on breach scenarios</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f"<div class='sc' style='flex-direction:column;align-items:center;padding:16px;'>"
                    f"<div style='font-size:28px;font-weight:900;color:#22C55E;'>✓</div>"
                    f"<div style='font-size:11px;color:var(--t3);text-align:center;'>No stockout in most<br>simulated scenarios</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

        # Distribution chart
        if mc["end_stock_distribution"]:
            dist   = mc["end_stock_distribution"]
            fig_mc = go.Figure()
            fig_mc.add_trace(go.Histogram(x=dist, nbinsx=20, name="End Stock",
                                          marker_color=ORANGE, marker_line_width=0, opacity=0.7))
            if ss_v > 0:
                fig_mc.add_vline(x=ss_v, line_color="#EF4444", line_dash="dot", line_width=1.5,
                                 annotation_text=f"Safety Stock {round(ss_v)}",
                                 annotation_font_color="#EF4444", annotation_font_size=9)
            ct(fig_mc, 180)
            fig_mc.update_layout(showlegend=False, xaxis_title="End Stock (units)", yaxis_title="Frequency",
                                 margin=dict(l=8, r=8, t=16, b=8))
            st.plotly_chart(fig_mc, use_container_width=True)

        # REPLACED: Monte Carlo explanation with note() instead of st.expander
        st.markdown("""
<div class='note-box'>
<ul>
<li><strong>What is Monte Carlo simulation?</strong> Runs 1,000 possible future demand scenarios based on historical mean and standard deviation.</li>
<li>The <strong>probability of stockout</strong> shows the percentage of scenarios where stock falls below safety stock in the next 6 months.</li>
<li>The <strong>outcome range</strong> (P10, P50, P90) shows possible ending stock levels under pessimistic, median, and optimistic conditions.</li>
<li>The <strong>histogram</strong> visualises the distribution of possible ending stock levels.</li>
</ul>
</div>
""", unsafe_allow_html=True)

    # ── Stock Trajectory ──────────────────────────────────────────────────────
    sec("Stock Trajectory")
    note("Stock from Inventory extract. Demand from Sales file (includes write-offs, internal consumption). "
         "Safety Stock from Material Master. Lead time max(Planned Delivery, Inhouse Production).")

    month_filter = st.slider("Show last N months", 6, 60, 25, step=1, key="mi_months")
    sh = get_stock_history(data, sel_mat).tail(month_filter)
    dh = get_demand_history(data, sel_mat).tail(month_filter)

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=sh["label"], y=sh["Gross Stock"], mode="lines+markers", name="Stock",
                             line=dict(color=ORANGE, width=2.5), marker=dict(size=4, color=ORANGE),
                             fill="tozeroy", fillcolor="rgba(244,123,37,0.07)", yaxis="y1",
                             hovertemplate="<b>%{x}</b><br>Stock: %{y} units<extra></extra>"))
    if ss_v > 0:
        fig.add_trace(go.Scatter(x=sh["label"], y=[ss_v] * len(sh), mode="lines",
                                 name=f"SAP SS ({round(ss_v)})", yaxis="y1",
                                 line=dict(color="#EF4444", width=1.5, dash="dot")))
    if rec > ss_v:
        fig.add_trace(go.Scatter(x=sh["label"], y=[rec] * len(sh), mode="lines",
                                 name=f"ARIA SS ({round(rec)})", yaxis="y1",
                                 line=dict(color="#22C55E", width=1.5, dash="dash")))
    if len(dh) > 0:
        dh_aligned = dh[dh.label.isin(sh["label"].tolist())]
        if len(dh_aligned) > 0:
            fig.add_trace(go.Bar(x=dh_aligned["label"], y=dh_aligned["demand"], name="Demand/mo",
                                 marker_color="rgba(148,163,184,0.3)", marker_line_width=0, yaxis="y2",
                                 hovertemplate="<b>%{x}</b><br>Demand: %{y} units<extra></extra>"))
    ct(fig, 320)
    fig.update_layout(
        yaxis=dict(title="Stock (units)", gridcolor="#F0F4F9"),
        yaxis2=dict(title="Demand/mo", overlaying="y", side="right", showgrid=False),
        xaxis=dict(tickangle=-35), margin=dict(l=8, r=50, t=32, b=8),
    )
    st.plotly_chart(fig, use_container_width=True)

    # ── Safety Stock Audit (button changed to "Explain ARIA SS Recommendation") ─
    ss_col, repl_col = st.columns(2)
    with ss_col:
        sec("Safety Stock Audit")
        note("SAP SS: Material Master → Safety Stock column. "
             "ARIA SS: 1.65 × σ_demand × √(lead_time/30) at 95% service level. "
             "Current Inventory SS = 0 for all SKUs (known data gap).")
        gap = rec - ss_v
        gp  = (gap / ss_v * 100) if ss_v > 0 else 100
        if gap > 10:
            gi, gc, gm = "⚠", "#F59E0B", f"SAP SS of {round(ss_v)} is {round(gp)}% below ARIA recommended {round(rec)}."
        else:
            gi, gc, gm = "✓", "#22C55E", f"SAP SS of {round(ss_v)} is adequately calibrated."
        st.markdown(
            f"<div class='sc' style='flex-direction:column;align-items:stretch;gap:0;'>"
            f"<div style='display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:10px;'>"
            f"<div><div style='font-size:9px;color:var(--t3);text-transform:uppercase;letter-spacing:0.8px;'>SAP SS (Material Master)</div>"
            f"<div style='font-size:20px;font-weight:900;color:var(--rd);'>{round(ss_v)}</div></div>"
            f"<div><div style='font-size:9px;color:var(--t3);text-transform:uppercase;letter-spacing:0.8px;'>ARIA Recommended (95% SL)</div>"
            f"<div style='font-size:20px;font-weight:900;color:var(--gr);'>{round(rec)}</div></div></div>"
            f"<div style='background:var(--s3);border-radius:8px;padding:8px 10px;font-size:11px;color:var(--t2);'>"
            f"<span style='color:{gc};font-weight:700;'>{gi} </span>{gm}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

        # Fix #5: Button label changed and prompt modified to explain rather than suggest
        if st.session_state.azure_client and analysis:
            if st.button("◈ Explain ARIA SS Recommendation", key="ss_rec"):
                with st.spinner("ARIA analysing safety stock…"):
                    ss_ctx = (f"Material: {sel_name}, SAP SS: {ss_v:.0f}, ARIA SS: {rec:.0f}, "
                              f"Lead time: {lt_v:.0f}d, Avg demand: {avg_d:.0f}/mo, Std: {std_d:.0f}, "
                              f"Current stock: {mat_row['sih']:.0f}, Breach count: {mat_row['breach_count']}, "
                              f"Monte Carlo breach probability: "
                              f"{run_monte_carlo(mat_row['sih'], ss_v, avg_d, std_d, lt_v)['probability_breach_pct']}%")
                    rec_txt = chat_with_data(
                        st.session_state.azure_client, AZURE_DEPLOYMENT,
                        f"Explain why the recommended safety stock for {sel_name} is {rec:.0f} units, based on the formula 1.65 × σ_demand × √(lead_time/30). Justify this value with the data provided.",
                        ss_ctx,
                    )
                st.markdown(
                    f"<div class='ic' style='margin-top:8px;'><div class='il'>◈ ARIA SS Explanation</div>"
                    f"<div class='ib' style='margin-top:4px;'>{rec_txt}</div></div>",
                    unsafe_allow_html=True,
                )

    with repl_col:
        sec("Replenishment Details")
        repl_t = mat_row["repl_triggered"]
        repl_q = int(mat_row["repl_quantity"])
        repl_s = int(mat_row["repl_shortfall"])
        repl_f = mat_row["repl_formula"]
        if repl_t:
            st.markdown(
                f"<div style='background:#FEF2F2;border:1px solid rgba(239,68,68,0.2);"
                f"border-left:3px solid #EF4444;border-radius:var(--r);padding:12px 14px;'>"
                f"<div style='font-size:10px;font-weight:800;color:#EF4444;margin-bottom:6px;'>IMMEDIATE ORDER REQUIRED</div>"
                f"<table style='font-size:11px;width:100%;border-collapse:collapse;'>"
                f"<tr><td style='color:#475569;padding:2px 0;'>Stock-in-Hand</td><td style='font-weight:700;text-align:right;'>{round(mat_row['sih'])} units</td></tr>"
                f"<tr><td style='color:#475569;padding:2px 0;'>Safety Stock (MM)</td><td style='font-weight:700;text-align:right;'>{round(ss_v)} units</td></tr>"
                f"<tr><td style='color:#475569;padding:2px 0;'>Shortfall</td><td style='font-weight:700;color:#EF4444;text-align:right;'>{repl_s} units</td></tr>"
                f"<tr><td style='color:#475569;padding:2px 0;'>Lead Time (MM)</td><td style='font-weight:700;text-align:right;'>{round(lt_v)}d</td><tr>"
                f"<tr><td style='color:#475569;padding:2px 0;'>Lot Size (Curr Inv)</td><td style='font-weight:700;text-align:right;'>{round(mat_row['lot_size'])} units</td></tr>"
                f"<tr style='border-top:1px solid #E2E8F0;'><td style='color:#EF4444;font-weight:800;padding:4px 0;'>Order Quantity</td><td style='font-weight:900;font-size:15px;color:#EF4444;text-align:right;'>{repl_q} units</td></tr>"
                f"<tr><td colspan='2' style='font-size:9px;color:#94A3B8;padding-top:3px;'>{repl_f}</td></tr>"
                f"</tr></div>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"<div style='background:#F0FDF4;border:1px solid rgba(34,197,94,0.2);"
                f"border-radius:var(--r);padding:12px 14px;font-size:12px;color:#14532d;'>"
                f"✓ No replenishment triggered — stock above safety stock.<br>"
                f"<span style='font-size:10px;color:#94A3B8;'>SIH={round(mat_row['sih'])} | SS={round(ss_v)}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )

    # ── BOM Components ─────────────────────────────────────────────────────────
    bom = get_bom_components(data, sel_mat)
    if len(bom) > 0:
        sec("BOM Components &amp; Supplier Intelligence")
        lvl = bom[bom["Level"].str.contains("Level 03|Level 02|Level 1", na=False, regex=True)]
        if len(lvl) > 0:
            bom_display = []
            for _, b in lvl.iterrows():
                fq  = ("✓ Fixed=1" if b.get("Fixed Qty Flag", False)
                       else str(round(float(b["Comp. Qty (CUn)"]), 3)) if pd.notna(b["Comp. Qty (CUn)"]) else "—")
                sup = b.get("Supplier Display", "—")
                loc = b.get("Supplier Location", "—")
                transit = b.get("Transit Days", None)
                bom_display.append({
                    "Material": str(b["Material"]),
                    "Description": str(b["Material Description"])[:36] if pd.notna(b["Material Description"]) else "—",
                    "Qty": fq, "Unit": str(b["Component unit"]) if pd.notna(b["Component unit"]) else "—",
                    "Procurement": b.get("Procurement Label", "—"),
                    "Supplier": sup, "Location": loc,
                    "Transit": f"{transit}d" if transit is not None else "—",
                })
            df_bom_disp = pd.DataFrame(bom_display)
            sup_r2 = JsCode("""class R{init(p){const v=p.value||'';this.e=document.createElement('span');if(v.startsWith('⚠')){this.e.style.cssText='background:#FEF3C7;color:#F59E0B;padding:2px 6px;border-radius:4px;font-size:10px;font-weight:600;';this.e.innerText=v;}else if(v==='Revvity Inhouse'){this.e.style.cssText='background:#DCFCE7;color:#16a34a;padding:2px 6px;border-radius:4px;font-size:10px;';this.e.innerText=v;}else{this.e.style.cssText='background:#EFF6FF;color:#2563EB;padding:2px 6px;border-radius:4px;font-size:10px;';this.e.innerText=v;};}getGui(){return this.e;}}""")
            gb3 = GridOptionsBuilder.from_dataframe(df_bom_disp)
            gb3.configure_column("Material",    width=85)
            gb3.configure_column("Description", width=220)
            gb3.configure_column("Qty",         width=78)
            gb3.configure_column("Unit",        width=52)
            gb3.configure_column("Procurement", width=110)
            gb3.configure_column("Supplier",    width=175, cellRenderer=sup_r2)
            gb3.configure_column("Location",    width=130)
            gb3.configure_column("Transit",     width=62)
            gb3.configure_grid_options(rowHeight=36, headerHeight=32)
            gb3.configure_default_column(resizable=True, sortable=True, filter=False)
            AgGrid(df_bom_disp, gridOptions=gb3.build(), height=290,
                   allow_unsafe_jscode=True, theme="alpine", custom_css=_AGGRID_CSS)

            # Supplier email draft
            if st.session_state.azure_client:
                external_suppliers = []
                for _, b in lvl.iterrows():
                    sup_raw = b.get("Supplier Name(Vendor)", "")
                    if pd.notna(sup_raw) and str(sup_raw).strip() and b.get("Procurement Label", "") == "External":
                        email_raw = b.get("Supplier Email address(Vendor)", "")
                        email     = str(email_raw) if pd.notna(email_raw) else "—"
                        if mat_row["repl_triggered"]:
                            if not any(s["supplier"] == str(sup_raw).strip() for s in external_suppliers):
                                external_suppliers.append({"supplier": str(sup_raw).strip(), "email": email})

                if external_suppliers and st.button("📧 Draft Supplier Order Emails", key="email_btn"):
                    for sup_info in external_suppliers[:3]:
                        with st.spinner(f"Drafting email to {sup_info['supplier']}…"):
                            email_txt = draft_supplier_email(
                                st.session_state.azure_client, AZURE_DEPLOYMENT,
                                sup_info["supplier"], sup_info["email"],
                                [{"name": sel_name, "quantity": mat_row["repl_quantity"], "lot_size": mat_row["lot_size"]}],
                            )
                        st.markdown(
                            f"<div style='background:#EFF6FF;border:1px solid #BFDBFE;border-radius:var(--r);"
                            f"padding:12px 14px;margin-top:8px;'>"
                            f"<div style='font-size:10px;font-weight:700;color:#1d4ed8;margin-bottom:4px;'>"
                            f"📧 Draft email to {sup_info['supplier']} ({sup_info['email']})</div>"
                            f"<pre style='font-size:11px;white-space:pre-wrap;color:#1e293b;margin:0;'>{email_txt}</pre>"
                            f"</div>",
                            unsafe_allow_html=True,
                        )

    # ── Supplier Consolidation (Fix #6: add source note) ──────────────────────
    consol   = get_supplier_consolidation(data, summary)
    relevant = consol[
        consol.material_list.apply(lambda x: sel_mat in x)
        & (consol.finished_goods_supplied > 1)
    ]
    if len(relevant) > 0:
        sec("Supplier Consolidation Opportunities")
        # Fix #6: Add source note
        note("Data source: BOM file (Supplier Name column).")
        note("These suppliers also supply other finished goods. If ordering from them for this material, consider consolidating orders.")
        for _, r in relevant.iterrows():
            other_mats  = [m for m in r["material_list"] if m != sel_mat]
            other_names = [MATERIAL_LABELS.get(m, m)[:20] for m in other_mats]
            needs_order = r["consolidation_opportunity"]
            bc          = "#22C55E" if not needs_order else "#F47B25"
            st.markdown(
                f"<div class='prow'><div style='font-size:14px;'>🏭</div>"
                f"<div style='flex:1;'>"
                f"<div style='font-size:12px;font-weight:800;color:var(--t);'>{r['supplier']}</div>"
                f"<div style='font-size:10px;color:var(--t3);'>{r['city']} · {r['email']}</div>"
                f"<div style='font-size:10px;color:var(--t2);margin-top:2px;'>Also supplies: {', '.join(other_names[:4])}</div>"
                f"</div>"
                f"<div style='font-size:10px;font-weight:700;color:{bc};text-align:right;'>"
                f"{'⚡ Consolidation opportunity' if needs_order else 'No other orders needed'}"
                f"</div></div>",
                unsafe_allow_html=True,
            )

    st.markdown('<div class="pfooter">🔬 Powered by <strong>MResult</strong></div>', unsafe_allow_html=True)
