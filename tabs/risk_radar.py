# # # # """
# # # # tabs/risk_radar.py
# # # # Risk Radar tab: replenishment priority queue, historical breach timeline,
# # # # safety stock coverage gap analysis.
# # # # """

# # # # import streamlit as st
# # # # import pandas as pd
# # # # import plotly.graph_objects as go

# # # # from utils.helpers import ct, fmt_p, sbadge, sec, note, ORANGE, AZURE_DEPLOYMENT
# # # # from data_loader import get_stock_history
# # # # from agent import interpret_chart, chat_with_data


# # # # def render():
# # # #     data    = st.session_state.data
# # # #     summary = st.session_state.summary

# # # #     st.markdown(
# # # #         "<div style='font-size:15px;font-weight:800;margin-bottom:4px;'>Risk Radar</div>"
# # # #         "<div style='font-size:12px;color:var(--t3);margin-bottom:14px;'>"
# # # #         "Replenishment priority · Breach timeline · Coverage gap analysis · LLM interpretation</div>",
# # # #         unsafe_allow_html=True,
# # # #     )

# # # #     active_m = summary[summary.risk != "INSUFFICIENT_DATA"]
# # # #     note("Only 1 plant in data: FI11 Turku. Safety Stock from Material Master. Lead Time from Material Master.")

# # # #     # ── Replenishment Priority Queue ──────────────────────────────────────────
# # # #     sec("Replenishment Priority Queue")
# # # #     note("Replenishment = CEILING(Shortfall/FLS)×FLS where Shortfall = SAP SS − Stock-in-Hand. Lead time shown for urgency context.")

# # # #     for _, row in active_m.sort_values("days_cover").iterrows():
# # # #         risk = row["risk"]
# # # #         if risk not in ["CRITICAL", "WARNING", "HEALTHY"]:
# # # #             continue
# # # #         brd    = "#EF4444" if risk == "CRITICAL" else "#F59E0B" if risk == "WARNING" else "#E2E8F0"
# # # #         bgc    = "rgba(239,68,68,0.03)" if risk == "CRITICAL" else "rgba(245,158,11,0.02)" if risk == "WARNING" else "#FFFFFF"
# # # #         repl_q = int(row.get("repl_quantity", 0))
# # # #         lt     = round(row["lead_time"])
# # # #         dc     = round(row["days_cover"])
# # # #         stock  = round(row["sih"])
# # # #         ss     = round(row["safety_stock"])

# # # #         if repl_q > 0:
# # # #             action_html = (
# # # #                 f"<div style='background:#FEE2E2;border-radius:6px;padding:6px 10px;margin-top:8px;font-size:11px;'>"
# # # #                 f"<strong style='color:#EF4444;'>ORDER {repl_q} units</strong>"
# # # #                 f" <span style='color:#475569;'>| Lead time: {lt}d | Formula: {row['repl_formula']}</span>"
# # # #                 f"</div>"
# # # #             )
# # # #         else:
# # # #             action_html = (
# # # #                 f"<div style='background:#F0FDF4;border-radius:6px;padding:5px 10px;margin-top:8px;"
# # # #                 f"font-size:10px;color:#14532d;'>✓ Stock above safety stock — {dc}d cover remaining</div>"
# # # #             )

# # # #         metric_cells = ""
# # # #         for val, lbl, vc in [
# # # #             (str(stock), "SIH",       "#EF4444" if stock < ss else "#1E293B"),
# # # #             (str(ss),    "SAP SS",    "#1E293B"),
# # # #             (f"{dc}d",   "Cover",     "#EF4444" if dc < 15 else "#F59E0B" if dc < 30 else "#22C55E"),
# # # #             (f"{lt}d",   "Lead Time", "#EF4444" if dc < lt else "#1E293B"),
# # # #         ]:
# # # #             metric_cells += (
# # # #                 f"<div style='background:var(--s3);border-radius:6px;padding:4px;'>"
# # # #                 f"<div style='font-size:12px;font-weight:900;color:{vc};'>{val}</div>"
# # # #                 f"<div style='font-size:8px;color:var(--t3);'>{lbl}</div></div>"
# # # #             )

# # # #         st.markdown(
# # # #             f"<div class='prow' style='border-left:3px solid {brd};background:{bgc};'>"
# # # #             f"{sbadge(risk)}"
# # # #             f"<div style='flex:1;margin-left:8px;'>"
# # # #             f"<div style='font-size:12px;font-weight:800;color:var(--t);'>{row['name']}</div>"
# # # #             f"<div style='font-size:10px;color:var(--t3);'>{row['material']}</div>"
# # # #             f"</div>"
# # # #             f"<div style='display:grid;grid-template-columns:repeat(4,68px);gap:4px;text-align:center;'>"
# # # #             + metric_cells +
# # # #             f"</div></div>{action_html}",
# # # #             unsafe_allow_html=True,
# # # #         )

# # # #     # ── Historical Breach Timeline ────────────────────────────────────────────
# # # #     sec("Historical Breach Timeline")
# # # #     note("Red = stock below SAP Safety Stock (breach). Amber = warning zone (stock < SS × 1.5). Each row = one material.")

# # # #     breach_events = []
# # # #     for _, row in active_m.iterrows():
# # # #         sh_r = get_stock_history(data, row["material"])
# # # #         ss   = row["safety_stock"]
# # # #         if ss <= 0:
# # # #             continue
# # # #         for _, sr in sh_r.iterrows():
# # # #             s = 0
# # # #             if sr["Gross Stock"] < ss:
# # # #                 s = 2
# # # #             elif sr["Gross Stock"] < ss * 1.5:
# # # #                 s = 1
# # # #             breach_events.append({
# # # #                 "Material": row["name"][:22], "Period": sr["label"],
# # # #                 "period_raw": sr["Fiscal Period"], "Status": s,
# # # #             })

# # # #     if breach_events:
# # # #         df_be = pd.DataFrame(breach_events)
# # # #         ap    = df_be.drop_duplicates("period_raw").sort_values("period_raw")
# # # #         sc_   = [fmt_p(p) for p in ap["period_raw"].tolist()]
# # # #         pv    = df_be.pivot_table(index="Material", columns="Period", values="Status", aggfunc="first").fillna(0)
# # # #         pv    = pv[[c for c in sc_ if c in pv.columns]]

# # # #         fig_bt = go.Figure(data=go.Heatmap(
# # # #             z=pv.values, x=pv.columns.tolist(), y=pv.index.tolist(),
# # # #             colorscale=[
# # # #                 [0, "#F8FAFE"], [0.49, "#F8FAFE"],
# # # #                 [0.5, "rgba(245,158,11,0.35)"], [0.99, "rgba(245,158,11,0.35)"],
# # # #                 [1, "rgba(239,68,68,0.55)"],
# # # #             ],
# # # #             showscale=True,
# # # #             colorbar=dict(title="", tickvals=[0, 1, 2], ticktext=["Safe", "Warning", "Breach"],
# # # #                           thickness=10, len=0.6, tickfont=dict(size=9)),
# # # #             hovertemplate="<b>%{y}</b><br>%{x}<extra></extra>",
# # # #             zmin=0, zmax=2,
# # # #         ))
# # # #         ct(fig_bt, 230, margin=dict(l=10, r=80, t=20, b=60))
# # # #         fig_bt.update_layout(
# # # #             xaxis=dict(tickangle=-40, tickfont=dict(size=9)),
# # # #             yaxis=dict(tickfont=dict(size=10)),
# # # #         )
# # # #         st.plotly_chart(fig_bt, use_container_width=True)

# # # #         if st.session_state.azure_client:
# # # #             if st.button("◈ Interpret Breach Timeline", key="interp_breach"):
# # # #                 with st.spinner("ARIA interpreting…"):
# # # #                     chart_data = {
# # # #                         "total_breach_events":    int(summary["breach_count"].sum()),
# # # #                         "materials_with_breaches": summary[summary.breach_count > 0]["name"].tolist(),
# # # #                         "worst_material":          summary.sort_values("breach_count", ascending=False).iloc[0]["name"],
# # # #                         "worst_count":             int(summary["breach_count"].max()),
# # # #                     }
# # # #                     interp = interpret_chart(st.session_state.azure_client, AZURE_DEPLOYMENT,
# # # #                                              "Historical Breach Timeline heatmap", chart_data)
# # # #                 st.markdown(
# # # #                     f"<div class='ic' style='margin-top:8px;'><div class='il'>◈ ARIA Interpretation</div>"
# # # #                     f"<div class='ib' style='margin-top:4px;'>{interp}</div></div>",
# # # #                     unsafe_allow_html=True,
# # # #                 )

# # # #     # ── Safety Stock Coverage Gap ─────────────────────────────────────────────
# # # #     sec("Safety Stock Coverage Gap Analysis")
# # # #     gap_data = active_m.copy()
# # # #     gap_data["ss_gap"] = gap_data["rec_safety_stock"] - gap_data["safety_stock"]
# # # #     gap_data = gap_data.sort_values("ss_gap", ascending=True)

# # # #     fig_gap = go.Figure()
# # # #     fig_gap.add_trace(go.Bar(
# # # #         y=gap_data["name"].str[:22], x=gap_data["safety_stock"], orientation="h",
# # # #         name="SAP Safety Stock", marker_color="rgba(239,68,68,0.5)", marker_line_width=0,
# # # #     ))
# # # #     fig_gap.add_trace(go.Bar(
# # # #         y=gap_data["name"].str[:22], x=gap_data["rec_safety_stock"], orientation="h",
# # # #         name="ARIA Recommended (95% SL)", marker_color="rgba(34,197,94,0.5)", marker_line_width=0,
# # # #     ))
# # # #     fig_gap.add_trace(go.Scatter(
# # # #         y=gap_data["name"].str[:22], x=gap_data["sih"], mode="markers",
# # # #         name="Current Stock (SIH)",
# # # #         marker=dict(symbol="diamond", size=10, color=ORANGE, line=dict(width=1.5, color="white")),
# # # #     ))
# # # #     ct(fig_gap, 240)
# # # #     fig_gap.update_layout(barmode="overlay", xaxis_title="Units",
# # # #                            legend=dict(font_size=9, y=1.12), margin=dict(l=10, r=40, t=32, b=8))
# # # #     st.plotly_chart(fig_gap, use_container_width=True)

# # # #     note("Orange diamond = current stock. Where diamond is LEFT of red bar = stock below SAP Safety Stock. "
# # # #          "ARIA SS = 1.65 × σ_demand × √(lead_time/30). SAP SS from Material Master.")

# # # #     if st.session_state.azure_client:
# # # #         if st.button("◈ Interpret Coverage Gap", key="interp_gap"):
# # # #             with st.spinner("ARIA interpreting…"):
# # # #                 cd      = {"materials": gap_data[["name", "safety_stock", "rec_safety_stock", "sih", "ss_gap"]].to_dict("records")}
# # # #                 interp2 = interpret_chart(
# # # #                     st.session_state.azure_client, AZURE_DEPLOYMENT,
# # # #                     "Safety Stock Coverage Gap chart", cd,
# # # #                     "Which materials have the most concerning safety stock gaps and what should procurement prioritise?",
# # # #                 )
# # # #             st.markdown(
# # # #                 f"<div class='ic' style='margin-top:8px;'><div class='il'>◈ ARIA Interpretation</div>"
# # # #                 f"<div class='ib' style='margin-top:4px;'>{interp2}</div></div>",
# # # #                 unsafe_allow_html=True,
# # # #             )

# # # #     st.markdown('<div class="pfooter">📡 Powered by <strong>MResult</strong></div>', unsafe_allow_html=True)

# # # """
# # # tabs/risk_radar.py
# # # Risk Radar tab: replenishment priority queue, historical breach timeline,
# # # safety stock coverage gap analysis.
# # # """

# # # import streamlit as st
# # # import pandas as pd
# # # import plotly.graph_objects as go

# # # from utils.helpers import ct, fmt_p, sbadge, sec, note, ORANGE, AZURE_DEPLOYMENT
# # # from data_loader import get_stock_history
# # # from agent import interpret_chart, chat_with_data


# # # def render():
# # #     data    = st.session_state.data
# # #     summary = st.session_state.summary

# # #     st.markdown(
# # #         "<div style='font-size:15px;font-weight:800;margin-bottom:4px;'>Risk Radar</div>"
# # #         "<div style='font-size:12px;color:var(--t3);margin-bottom:14px;'>"
# # #         "Replenishment priority · Breach timeline · Coverage gap analysis · LLM interpretation</div>",
# # #         unsafe_allow_html=True,
# # #     )

# # #     active_m = summary[summary.risk != "INSUFFICIENT_DATA"]
# # #     note("Only 1 plant in data: FI11 Turku. Safety Stock from Material Master. Lead Time from Material Master.")

# # #     # ── Replenishment Priority Queue ──────────────────────────────────────────
# # #     sec("Replenishment Priority Queue")
# # #     note("Replenishment = CEILING(Shortfall/FLS)×FLS where Shortfall = SAP SS − Stock-in-Hand. Lead time shown for urgency context.")

# # #     for _, row in active_m.sort_values("days_cover").iterrows():
# # #         risk = row["risk"]
# # #         if risk not in ["CRITICAL", "WARNING", "HEALTHY"]:
# # #             continue
# # #         brd    = "#EF4444" if risk == "CRITICAL" else "#F59E0B" if risk == "WARNING" else "#E2E8F0"
# # #         bgc    = "rgba(239,68,68,0.03)" if risk == "CRITICAL" else "rgba(245,158,11,0.02)" if risk == "WARNING" else "#FFFFFF"
# # #         repl_q = int(row.get("repl_quantity", 0))
# # #         lt     = round(row["lead_time"])
# # #         dc     = round(row["days_cover"])
# # #         stock  = round(row["sih"])
# # #         ss     = round(row["safety_stock"])

# # #         if repl_q > 0:
# # #             action_html = (
# # #                 f"<div style='background:#FEE2E2;border-radius:6px;padding:6px 10px;margin-top:8px;font-size:11px;'>"
# # #                 f"<strong style='color:#EF4444;'>ORDER {repl_q} units</strong>"
# # #                 f" <span style='color:#475569;'>| Lead time: {lt}d | Formula: {row['repl_formula']}</span>"
# # #                 f"</div>"
# # #             )
# # #         else:
# # #             action_html = (
# # #                 f"<div style='background:#F0FDF4;border-radius:6px;padding:5px 10px;margin-top:8px;"
# # #                 f"font-size:10px;color:#14532d;'>✓ Stock above safety stock — {dc}d cover remaining</div>"
# # #             )

# # #         metric_cells = ""
# # #         for val, lbl, vc in [
# # #             (str(stock), "SIH",       "#EF4444" if stock < ss else "#1E293B"),
# # #             (str(ss),    "SAP SS",    "#1E293B"),
# # #             (f"{dc}d",   "Cover",     "#EF4444" if dc < 15 else "#F59E0B" if dc < 30 else "#22C55E"),
# # #             (f"{lt}d",   "Lead Time", "#EF4444" if dc < lt else "#1E293B"),
# # #         ]:
# # #             metric_cells += (
# # #                 f"<div style='background:var(--s3);border-radius:6px;padding:4px;'>"
# # #                 f"<div style='font-size:12px;font-weight:900;color:{vc};'>{val}</div>"
# # #                 f"<div style='font-size:8px;color:var(--t3);'>{lbl}</div></div>"
# # #             )

# # #         st.markdown(
# # #             f"<div class='prow' style='border-left:3px solid {brd};background:{bgc};'>"
# # #             f"{sbadge(risk)}"
# # #             f"<div style='flex:1;margin-left:8px;'>"
# # #             f"<div style='font-size:12px;font-weight:800;color:var(--t);'>{row['name']}</div>"
# # #             f"<div style='font-size:10px;color:var(--t3);'>{row['material']}</div>"
# # #             f"</div>"
# # #             f"<div style='display:grid;grid-template-columns:repeat(4,68px);gap:4px;text-align:center;'>"
# # #             + metric_cells +
# # #             f"</div></div>{action_html}",
# # #             unsafe_allow_html=True,
# # #         )

# # #     # ── Historical Breach Timeline ────────────────────────────────────────────
# # #     sec("Historical Breach Timeline")
# # #     note("Red = stock below SAP Safety Stock (breach). Amber = warning zone (stock < SS × 1.5). Each row = one material.")
# # #     # Fix #8: Add note about omitted materials
# # #     note("Materials with insufficient data are omitted from the heatmap.")

# # #     breach_events = []
# # #     for _, row in active_m.iterrows():
# # #         sh_r = get_stock_history(data, row["material"])
# # #         ss   = row["safety_stock"]
# # #         if ss <= 0:
# # #             continue
# # #         for _, sr in sh_r.iterrows():
# # #             s = 0
# # #             if sr["Gross Stock"] < ss:
# # #                 s = 2
# # #             elif sr["Gross Stock"] < ss * 1.5:
# # #                 s = 1
# # #             breach_events.append({
# # #                 "Material": row["name"][:22], "Period": sr["label"],
# # #                 "period_raw": sr["Fiscal Period"], "Status": s,
# # #             })

# # #     if breach_events:
# # #         df_be = pd.DataFrame(breach_events)
# # #         ap    = df_be.drop_duplicates("period_raw").sort_values("period_raw")
# # #         sc_   = [fmt_p(p) for p in ap["period_raw"].tolist()]
# # #         pv    = df_be.pivot_table(index="Material", columns="Period", values="Status", aggfunc="first").fillna(0)
# # #         pv    = pv[[c for c in sc_ if c in pv.columns]]

# # #         fig_bt = go.Figure(data=go.Heatmap(
# # #             z=pv.values, x=pv.columns.tolist(), y=pv.index.tolist(),
# # #             colorscale=[
# # #                 [0, "#F8FAFE"], [0.49, "#F8FAFE"],
# # #                 [0.5, "rgba(245,158,11,0.35)"], [0.99, "rgba(245,158,11,0.35)"],
# # #                 [1, "rgba(239,68,68,0.55)"],
# # #             ],
# # #             showscale=True,
# # #             colorbar=dict(title="Risk Level", tickvals=[0, 1, 2], ticktext=["Safe", "Warning", "Breach"],
# # #                           thickness=10, len=0.6, tickfont=dict(size=9)),
# # #             hovertemplate="<b>%{y}</b><br>%{x}<extra></extra>",
# # #             zmin=0, zmax=2,
# # #         ))
# # #         ct(fig_bt, 230, margin=dict(l=10, r=80, t=20, b=60))
# # #         fig_bt.update_layout(
# # #             xaxis=dict(tickangle=-40, tickfont=dict(size=9)),
# # #             yaxis=dict(tickfont=dict(size=10)),
# # #         )
# # #         st.plotly_chart(fig_bt, use_container_width=True)

# # #         if st.session_state.azure_client:
# # #             if st.button("◈ Interpret Breach Timeline", key="interp_breach"):
# # #                 with st.spinner("ARIA interpreting…"):
# # #                     chart_data = {
# # #                         "total_breach_events":    int(summary["breach_count"].sum()),
# # #                         "materials_with_breaches": summary[summary.breach_count > 0]["name"].tolist(),
# # #                         "worst_material":          summary.sort_values("breach_count", ascending=False).iloc[0]["name"],
# # #                         "worst_count":             int(summary["breach_count"].max()),
# # #                     }
# # #                     interp = interpret_chart(st.session_state.azure_client, AZURE_DEPLOYMENT,
# # #                                              "Historical Breach Timeline heatmap", chart_data)
# # #                 st.markdown(
# # #                     f"<div class='ic' style='margin-top:8px;'><div class='il'>◈ ARIA Interpretation</div>"
# # #                     f"<div class='ib' style='margin-top:4px;'>{interp}</div></div>",
# # #                     unsafe_allow_html=True,
# # #                 )

# # #     # ── Safety Stock Coverage Gap ─────────────────────────────────────────────
# # #     sec("Safety Stock Coverage Gap Analysis")
# # #     gap_data = active_m.copy()
# # #     gap_data["ss_gap"] = gap_data["rec_safety_stock"] - gap_data["safety_stock"]
# # #     gap_data = gap_data.sort_values("ss_gap", ascending=True)

# # #     fig_gap = go.Figure()
# # #     fig_gap.add_trace(go.Bar(
# # #         y=gap_data["name"].str[:22], x=gap_data["safety_stock"], orientation="h",
# # #         name="SAP Safety Stock", marker_color="rgba(239,68,68,0.5)", marker_line_width=0,
# # #     ))
# # #     fig_gap.add_trace(go.Bar(
# # #         y=gap_data["name"].str[:22], x=gap_data["rec_safety_stock"], orientation="h",
# # #         name="ARIA Recommended (95% SL)", marker_color="rgba(34,197,94,0.5)", marker_line_width=0,
# # #     ))
# # #     fig_gap.add_trace(go.Scatter(
# # #         y=gap_data["name"].str[:22], x=gap_data["sih"], mode="markers",
# # #         name="Current Stock (SIH)",
# # #         marker=dict(symbol="diamond", size=10, color=ORANGE, line=dict(width=1.5, color="white")),
# # #     ))
# # #     ct(fig_gap, 240)
# # #     fig_gap.update_layout(barmode="overlay", xaxis_title="Units",
# # #                            legend=dict(font_size=9, y=1.12), margin=dict(l=10, r=40, t=32, b=8))
# # #     st.plotly_chart(fig_gap, use_container_width=True)

# # #     note("Orange diamond = current stock. Where diamond is LEFT of red bar = stock below SAP Safety Stock. "
# # #          "ARIA SS = 1.65 × σ_demand × √(lead_time/30). SAP SS from Material Master.")

# # #     if st.session_state.azure_client:
# # #         if st.button("◈ Interpret Coverage Gap", key="interp_gap"):
# # #             with st.spinner("ARIA interpreting…"):
# # #                 cd      = {"materials": gap_data[["name", "safety_stock", "rec_safety_stock", "sih", "ss_gap"]].to_dict("records")}
# # #                 interp2 = interpret_chart(
# # #                     st.session_state.azure_client, AZURE_DEPLOYMENT,
# # #                     "Safety Stock Coverage Gap chart", cd,
# # #                     "Which materials have the most concerning safety stock gaps and what should procurement prioritise?",
# # #                 )
# # #             st.markdown(
# # #                 f"<div class='ic' style='margin-top:8px;'><div class='il'>◈ ARIA Interpretation</div>"
# # #                 f"<div class='ib' style='margin-top:4px;'>{interp2}</div></div>",
# # #                 unsafe_allow_html=True,
# # #             )

# # #     st.markdown('<div class="pfooter">📡 Powered by <strong>MResult</strong></div>', unsafe_allow_html=True)

# # """
# # tabs/risk_radar.py
# # Risk Radar tab: replenishment priority queue, historical breach timeline,
# # safety stock coverage gap analysis.
# # """

# # import streamlit as st
# # import pandas as pd
# # import plotly.graph_objects as go

# # from utils.helpers import ct, fmt_p, sbadge, sec, note, ORANGE, AZURE_DEPLOYMENT
# # from data_loader import get_stock_history
# # from agent import interpret_chart, chat_with_data


# # def render():
# #     data    = st.session_state.data
# #     summary = st.session_state.summary

# #     st.markdown(
# #         "<div style='font-size:15px;font-weight:800;margin-bottom:4px;'>Risk Radar</div>"
# #         "<div style='font-size:12px;color:var(--t3);margin-bottom:14px;'>"
# #         "Replenishment priority · Breach timeline · Coverage gap analysis · LLM interpretation</div>",
# #         unsafe_allow_html=True,
# #     )

# #     active_m = summary[summary.risk != "INSUFFICIENT_DATA"]
# #     note("Only 1 plant in data: FI11 Turku. Safety Stock from Material Master. Lead Time from Material Master.")

# #     # ── Replenishment Priority Queue ──────────────────────────────────────────
# #     sec("Replenishment Priority Queue")
# #     note("Replenishment = CEILING(Shortfall/FLS)×FLS where Shortfall = SAP SS − Stock-in-Hand. Lead time shown for urgency context.")

# #     for _, row in active_m.sort_values("days_cover").iterrows():
# #         risk = row["risk"]
# #         if risk not in ["CRITICAL", "WARNING", "HEALTHY"]:
# #             continue
# #         brd    = "#EF4444" if risk == "CRITICAL" else "#F59E0B" if risk == "WARNING" else "#E2E8F0"
# #         bgc    = "rgba(239,68,68,0.03)" if risk == "CRITICAL" else "rgba(245,158,11,0.02)" if risk == "WARNING" else "#FFFFFF"
# #         repl_q = int(row.get("repl_quantity", 0))
# #         lt     = round(row["lead_time"])
# #         dc     = round(row["days_cover"])
# #         stock  = round(row["sih"])
# #         ss     = round(row["safety_stock"])

# #         if repl_q > 0:
# #             action_html = (
# #                 f"<div style='background:#FEE2E2;border-radius:6px;padding:6px 10px;margin-top:8px;font-size:11px;'>"
# #                 f"<strong style='color:#EF4444;'>ORDER {repl_q} units</strong>"
# #                 f" <span style='color:#475569;'>| Lead time: {lt}d | Formula: {row['repl_formula']}</span>"
# #                 f"</div>"
# #             )
# #         else:
# #             action_html = (
# #                 f"<div style='background:#F0FDF4;border-radius:6px;padding:5px 10px;margin-top:8px;"
# #                 f"font-size:10px;color:#14532d;'>✓ Stock above safety stock — {dc}d cover remaining</div>"
# #             )

# #         metric_cells = ""
# #         for val, lbl, vc in [
# #             (str(stock), "SIH",       "#EF4444" if stock < ss else "#1E293B"),
# #             (str(ss),    "SAP SS",    "#1E293B"),
# #             (f"{dc}d",   "Cover",     "#EF4444" if dc < 15 else "#F59E0B" if dc < 30 else "#22C55E"),
# #             (f"{lt}d",   "Lead Time", "#EF4444" if dc < lt else "#1E293B"),
# #         ]:
# #             metric_cells += (
# #                 f"<div style='background:var(--s3);border-radius:6px;padding:4px;'>"
# #                 f"<div style='font-size:12px;font-weight:900;color:{vc};'>{val}</div>"
# #                 f"<div style='font-size:8px;color:var(--t3);'>{lbl}</div></div>"
# #             )

# #         st.markdown(
# #             f"<div class='prow' style='border-left:3px solid {brd};background:{bgc};'>"
# #             f"{sbadge(risk)}"
# #             f"<div style='flex:1;margin-left:8px;'>"
# #             f"<div style='font-size:12px;font-weight:800;color:var(--t);'>{row['name']}</div>"
# #             f"<div style='font-size:10px;color:var(--t3);'>{row['material']}</div>"
# #             f"</div>"
# #             f"<div style='display:grid;grid-template-columns:repeat(4,68px);gap:4px;text-align:center;'>"
# #             + metric_cells +
# #             f"</div></div>{action_html}",
# #             unsafe_allow_html=True,
# #         )

# #     # ── Historical Breach Timeline (Fix #3a + #3b) ────────────────────────────
# #     sec("Historical Breach Timeline")
# #     note("Red = stock below SAP Safety Stock (breach). Amber = warning zone (stock < SS × 1.5). Each row = one material.")
# #     note("Materials with insufficient data are omitted from the heatmap.")

# #     breach_events = []
# #     for _, row in active_m.iterrows():
# #         sh_r = get_stock_history(data, row["material"])
# #         ss   = row["safety_stock"]
# #         # Fix #3b: Use effective_ss = max(ss, 1) to include zero safety stock materials
# #         effective_ss = max(ss, 1)
# #         for _, sr in sh_r.iterrows():
# #             s = 0
# #             if sr["Gross Stock"] < effective_ss:
# #                 s = 2
# #             elif sr["Gross Stock"] < effective_ss * 1.5:
# #                 s = 1
# #             breach_events.append({
# #                 "Material": row["name"][:22],
# #                 "Period": sr["label"],
# #                 "period_raw": sr["Fiscal Period"],
# #                 "Status": s,
# #             })

# #     if breach_events:
# #         df_be = pd.DataFrame(breach_events)
# #         ap    = df_be.drop_duplicates("period_raw").sort_values("period_raw")
# #         sc_   = [fmt_p(p) for p in ap["period_raw"].tolist()]
# #         pv    = df_be.pivot_table(index="Material", columns="Period", values="Status", aggfunc="first").fillna(0)
# #         pv    = pv[[c for c in sc_ if c in pv.columns]]

# #         fig_bt = go.Figure(data=go.Heatmap(
# #             z=pv.values, x=pv.columns.tolist(), y=pv.index.tolist(),
# #             colorscale=[
# #                 [0, "#F8FAFE"], [0.49, "#F8FAFE"],
# #                 [0.5, "rgba(245,158,11,0.35)"], [0.99, "rgba(245,158,11,0.35)"],
# #                 [1, "rgba(239,68,68,0.55)"],
# #             ],
# #             showscale=True,
# #             colorbar=dict(title="Risk Level", tickvals=[0, 1, 2], ticktext=["Safe", "Warning", "Breach"],
# #                           thickness=10, len=0.6, tickfont=dict(size=9)),
# #             hovertemplate="<b>%{y}</b><br>%{x}<extra></extra>",
# #             zmin=0, zmax=2,
# #         ))
# #         ct(fig_bt, 230, margin=dict(l=10, r=80, t=20, b=60))
# #         # Fix #3a: Explicitly set colorbar title and ticks (already done, but ensure it's applied)
# #         fig_bt.update_layout(
# #             xaxis=dict(tickangle=-40, tickfont=dict(size=9)),
# #             yaxis=dict(tickfont=dict(size=10)),
# #         )
# #         st.plotly_chart(fig_bt, use_container_width=True)

# #         if st.session_state.azure_client:
# #             if st.button("◈ Interpret Breach Timeline", key="interp_breach"):
# #                 with st.spinner("ARIA interpreting…"):
# #                     chart_data = {
# #                         "total_breach_events":    int(summary["breach_count"].sum()),
# #                         "materials_with_breaches": summary[summary.breach_count > 0]["name"].tolist(),
# #                         "worst_material":          summary.sort_values("breach_count", ascending=False).iloc[0]["name"],
# #                         "worst_count":             int(summary["breach_count"].max()),
# #                     }
# #                     interp = interpret_chart(st.session_state.azure_client, AZURE_DEPLOYMENT,
# #                                              "Historical Breach Timeline heatmap", chart_data)
# #                 st.markdown(
# #                     f"<div class='ic' style='margin-top:8px;'><div class='il'>◈ ARIA Interpretation</div>"
# #                     f"<div class='ib' style='margin-top:4px;'>{interp}</div></div>",
# #                     unsafe_allow_html=True,
# #                 )

# #     # ── Safety Stock Coverage Gap ─────────────────────────────────────────────
# #     sec("Safety Stock Coverage Gap Analysis")
# #     gap_data = active_m.copy()
# #     gap_data["ss_gap"] = gap_data["rec_safety_stock"] - gap_data["safety_stock"]
# #     gap_data = gap_data.sort_values("ss_gap", ascending=True)

# #     fig_gap = go.Figure()
# #     fig_gap.add_trace(go.Bar(
# #         y=gap_data["name"].str[:22], x=gap_data["safety_stock"], orientation="h",
# #         name="SAP Safety Stock", marker_color="rgba(239,68,68,0.5)", marker_line_width=0,
# #     ))
# #     fig_gap.add_trace(go.Bar(
# #         y=gap_data["name"].str[:22], x=gap_data["rec_safety_stock"], orientation="h",
# #         name="ARIA Recommended (95% SL)", marker_color="rgba(34,197,94,0.5)", marker_line_width=0,
# #     ))
# #     fig_gap.add_trace(go.Scatter(
# #         y=gap_data["name"].str[:22], x=gap_data["sih"], mode="markers",
# #         name="Current Stock (SIH)",
# #         marker=dict(symbol="diamond", size=10, color=ORANGE, line=dict(width=1.5, color="white")),
# #     ))
# #     ct(fig_gap, 240)
# #     fig_gap.update_layout(barmode="overlay", xaxis_title="Units",
# #                            legend=dict(font_size=9, y=1.12), margin=dict(l=10, r=40, t=32, b=8))
# #     st.plotly_chart(fig_gap, use_container_width=True)

# #     note("Orange diamond = current stock. Where diamond is LEFT of red bar = stock below SAP Safety Stock. "
# #          "ARIA SS = 1.65 × σ_demand × √(lead_time/30). SAP SS from Material Master.")

# #     if st.session_state.azure_client:
# #         if st.button("◈ Interpret Coverage Gap", key="interp_gap"):
# #             with st.spinner("ARIA interpreting…"):
# #                 cd      = {"materials": gap_data[["name", "safety_stock", "rec_safety_stock", "sih", "ss_gap"]].to_dict("records")}
# #                 interp2 = interpret_chart(
# #                     st.session_state.azure_client, AZURE_DEPLOYMENT,
# #                     "Safety Stock Coverage Gap chart", cd,
# #                     "Which materials have the most concerning safety stock gaps and what should procurement prioritise?",
# #                 )
# #             st.markdown(
# #                 f"<div class='ic' style='margin-top:8px;'><div class='il'>◈ ARIA Interpretation</div>"
# #                 f"<div class='ib' style='margin-top:4px;'>{interp2}</div></div>",
# #                 unsafe_allow_html=True,
# #             )

# #     st.markdown('<div class="pfooter">📡 Powered by <strong>MResult</strong></div>', unsafe_allow_html=True)

# """
# tabs/risk_radar.py
# Risk Radar tab: replenishment priority queue, historical breach timeline,
# safety stock coverage gap analysis.
# """

# import streamlit as st
# import pandas as pd
# import plotly.graph_objects as go

# from utils.helpers import ct, fmt_p, sbadge, sec, note, ORANGE, AZURE_DEPLOYMENT
# from data_loader import get_stock_history
# from agent import interpret_chart, chat_with_data


# def render():
#     data    = st.session_state.data
#     summary = st.session_state.summary

#     st.markdown(
#         "<div style='font-size:15px;font-weight:800;margin-bottom:4px;'>Risk Radar</div>"
#         "<div style='font-size:12px;color:var(--t3);margin-bottom:14px;'>"
#         "Replenishment priority · Breach timeline · Coverage gap analysis · LLM interpretation</div>",
#         unsafe_allow_html=True,
#     )

#     active_m = summary[summary.risk != "INSUFFICIENT_DATA"]
#     note("Only 1 plant in data: FI11 Turku. Safety Stock from Material Master. Lead Time from Material Master.")

#     # ── Replenishment Priority Queue ──────────────────────────────────────────
#     sec("Replenishment Priority Queue")
#     note("Replenishment = CEILING(Shortfall/FLS)×FLS where Shortfall = SAP SS − Stock-in-Hand. Lead time shown for urgency context.")

#     for _, row in active_m.sort_values("days_cover").iterrows():
#         risk = row["risk"]
#         if risk not in ["CRITICAL", "WARNING", "HEALTHY"]:
#             continue
#         brd    = "#EF4444" if risk == "CRITICAL" else "#F59E0B" if risk == "WARNING" else "#E2E8F0"
#         bgc    = "rgba(239,68,68,0.03)" if risk == "CRITICAL" else "rgba(245,158,11,0.02)" if risk == "WARNING" else "#FFFFFF"
#         repl_q = int(row.get("repl_quantity", 0))
#         lt     = round(row["lead_time"])
#         dc     = round(row["days_cover"])
#         stock  = round(row["sih"])
#         ss     = round(row["safety_stock"])

#         if repl_q > 0:
#             action_html = (
#                 f"<div style='background:#FEE2E2;border-radius:6px;padding:6px 10px;margin-top:8px;font-size:11px;'>"
#                 f"<strong style='color:#EF4444;'>ORDER {repl_q} units</strong>"
#                 f" <span style='color:#475569;'>| Lead time: {lt}d | Formula: {row['repl_formula']}</span>"
#                 f"</div>"
#             )
#         else:
#             action_html = (
#                 f"<div style='background:#F0FDF4;border-radius:6px;padding:5px 10px;margin-top:8px;"
#                 f"font-size:10px;color:#14532d;'>✓ Stock above safety stock — {dc}d cover remaining</div>"
#             )

#         metric_cells = ""
#         for val, lbl, vc in [
#             (str(stock), "SIH",       "#EF4444" if stock < ss else "#1E293B"),
#             (str(ss),    "SAP SS",    "#1E293B"),
#             (f"{dc}d",   "Cover",     "#EF4444" if dc < 15 else "#F59E0B" if dc < 30 else "#22C55E"),
#             (f"{lt}d",   "Lead Time", "#EF4444" if dc < lt else "#1E293B"),
#         ]:
#             metric_cells += (
#                 f"<div style='background:var(--s3);border-radius:6px;padding:4px;'>"
#                 f"<div style='font-size:12px;font-weight:900;color:{vc};'>{val}</div>"
#                 f"<div style='font-size:8px;color:var(--t3);'>{lbl}</div></div>"
#             )

#         st.markdown(
#             f"<div class='prow' style='border-left:3px solid {brd};background:{bgc};'>"
#             f"{sbadge(risk)}"
#             f"<div style='flex:1;margin-left:8px;'>"
#             f"<div style='font-size:12px;font-weight:800;color:var(--t);'>{row['name']}</div>"
#             f"<div style='font-size:10px;color:var(--t3);'>{row['material']}</div>"
#             f"</div>"
#             f"<div style='display:grid;grid-template-columns:repeat(4,68px);gap:4px;text-align:center;'>"
#             + metric_cells +
#             f"</div></div>{action_html}",
#             unsafe_allow_html=True,
#         )

#     # ── Historical Breach Timeline (includes all materials, even with zero breaches) ──
#     sec("Historical Breach Timeline")
#     note("Red = stock below SAP Safety Stock (breach). Amber = warning zone (stock < SS × 1.5). Each row = one material.")
#     note("Materials with insufficient data are omitted from the heatmap.")

#     breach_events = []
#     all_periods = set()

#     # First pass: collect events and also track all periods
#     for _, row in active_m.iterrows():
#         sh_r = get_stock_history(data, row["material"])
#         ss   = row["safety_stock"]
#         effective_ss = max(ss, 1)
#         for _, sr in sh_r.iterrows():
#             period_raw = sr["Fiscal Period"]
#             period_label = sr["label"]
#             all_periods.add((period_raw, period_label))
#             s = 0
#             if sr["Gross Stock"] < effective_ss:
#                 s = 2
#             elif sr["Gross Stock"] < effective_ss * 1.5:
#                 s = 1
#             if s > 0:  # only store if breach or warning to avoid huge data
#                 breach_events.append({
#                     "Material": row["name"][:22],
#                     "Period": period_label,
#                     "period_raw": period_raw,
#                     "Status": s,
#                 })

#     # Ensure every material in active_m appears at least once (with status 0) to create a row
#     materials_in_events = {e["Material"] for e in breach_events}
#     for _, row in active_m.iterrows():
#         mat_name = row["name"][:22]
#         if mat_name not in materials_in_events and len(all_periods) > 0:
#             # Add a dummy safe event for the earliest period
#             earliest_period = min(all_periods, key=lambda x: x[0])
#             breach_events.append({
#                 "Material": mat_name,
#                 "Period": earliest_period[1],
#                 "period_raw": earliest_period[0],
#                 "Status": 0,
#             })

#     if breach_events:
#         df_be = pd.DataFrame(breach_events)
#         ap    = df_be.drop_duplicates("period_raw").sort_values("period_raw")
#         sc_   = [fmt_p(p) for p in ap["period_raw"].tolist()]
#         pv    = df_be.pivot_table(index="Material", columns="Period", values="Status", aggfunc="first").fillna(0)
#         pv    = pv[[c for c in sc_ if c in pv.columns]]

#         fig_bt = go.Figure(data=go.Heatmap(
#             z=pv.values, x=pv.columns.tolist(), y=pv.index.tolist(),
#             colorscale=[
#                 [0, "#F8FAFE"], [0.49, "#F8FAFE"],
#                 [0.5, "rgba(245,158,11,0.35)"], [0.99, "rgba(245,158,11,0.35)"],
#                 [1, "rgba(239,68,68,0.55)"],
#             ],
#             showscale=True,
#             colorbar=dict(title="Risk Level", tickvals=[0, 1, 2], ticktext=["Safe", "Warning", "Breach"],
#                           thickness=10, len=0.6, tickfont=dict(size=9)),
#             hovertemplate="<b>%{y}</b><br>%{x}<extra></extra>",
#             zmin=0, zmax=2,
#         ))
#         ct(fig_bt, 230, margin=dict(l=10, r=80, t=20, b=60))
#         fig_bt.update_layout(
#             xaxis=dict(tickangle=-40, tickfont=dict(size=9)),
#             yaxis=dict(tickfont=dict(size=10)),
#         )
#         st.plotly_chart(fig_bt, use_container_width=True)

#         if st.session_state.azure_client:
#             if st.button("◈ Interpret Breach Timeline", key="interp_breach"):
#                 with st.spinner("ARIA interpreting…"):
#                     chart_data = {
#                         "total_breach_events":    int(summary["breach_count"].sum()),
#                         "materials_with_breaches": summary[summary.breach_count > 0]["name"].tolist(),
#                         "worst_material":          summary.sort_values("breach_count", ascending=False).iloc[0]["name"],
#                         "worst_count":             int(summary["breach_count"].max()),
#                     }
#                     interp = interpret_chart(st.session_state.azure_client, AZURE_DEPLOYMENT,
#                                              "Historical Breach Timeline heatmap", chart_data)
#                 st.markdown(
#                     f"<div class='ic' style='margin-top:8px;'><div class='il'>◈ ARIA Interpretation</div>"
#                     f"<div class='ib' style='margin-top:4px;'>{interp}</div></div>",
#                     unsafe_allow_html=True,
#                 )

#     # ── Safety Stock Coverage Gap ─────────────────────────────────────────────
#     sec("Safety Stock Coverage Gap Analysis")
#     gap_data = active_m.copy()
#     gap_data["ss_gap"] = gap_data["rec_safety_stock"] - gap_data["safety_stock"]
#     gap_data = gap_data.sort_values("ss_gap", ascending=True)

#     fig_gap = go.Figure()
#     fig_gap.add_trace(go.Bar(
#         y=gap_data["name"].str[:22], x=gap_data["safety_stock"], orientation="h",
#         name="SAP Safety Stock", marker_color="rgba(239,68,68,0.5)", marker_line_width=0,
#     ))
#     fig_gap.add_trace(go.Bar(
#         y=gap_data["name"].str[:22], x=gap_data["rec_safety_stock"], orientation="h",
#         name="ARIA Recommended (95% SL)", marker_color="rgba(34,197,94,0.5)", marker_line_width=0,
#     ))
#     fig_gap.add_trace(go.Scatter(
#         y=gap_data["name"].str[:22], x=gap_data["sih"], mode="markers",
#         name="Current Stock (SIH)",
#         marker=dict(symbol="diamond", size=10, color=ORANGE, line=dict(width=1.5, color="white")),
#     ))
#     ct(fig_gap, 240)
#     fig_gap.update_layout(barmode="overlay", xaxis_title="Units",
#                            legend=dict(font_size=9, y=1.12), margin=dict(l=10, r=40, t=32, b=8))
#     st.plotly_chart(fig_gap, use_container_width=True)

#     note("Orange diamond = current stock. Where diamond is LEFT of red bar = stock below SAP Safety Stock. "
#          "ARIA SS = 1.65 × σ_demand × √(lead_time/30). SAP SS from Material Master.")

#     if st.session_state.azure_client:
#         if st.button("◈ Interpret Coverage Gap", key="interp_gap"):
#             with st.spinner("ARIA interpreting…"):
#                 cd      = {"materials": gap_data[["name", "safety_stock", "rec_safety_stock", "sih", "ss_gap"]].to_dict("records")}
#                 interp2 = interpret_chart(
#                     st.session_state.azure_client, AZURE_DEPLOYMENT,
#                     "Safety Stock Coverage Gap chart", cd,
#                     "Which materials have the most concerning safety stock gaps and what should procurement prioritise?",
#                 )
#             st.markdown(
#                 f"<div class='ic' style='margin-top:8px;'><div class='il'>◈ ARIA Interpretation</div>"
#                 f"<div class='ib' style='margin-top:4px;'>{interp2}</div></div>",
#                 unsafe_allow_html=True,
#             )

#     st.markdown('<div class="pfooter">📡 Powered by <strong>MResult</strong></div>', unsafe_allow_html=True)

"""
tabs/risk_radar.py
Risk Radar tab: replenishment priority queue, historical breach timeline,
safety stock coverage gap analysis.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from utils.helpers import ct, fmt_p, sbadge, sec, note, ORANGE, AZURE_DEPLOYMENT
from data_loader import get_stock_history
from agent import interpret_chart, chat_with_data


def render():
    data    = st.session_state.data
    summary = st.session_state.summary

    st.markdown(
        "<div style='font-size:15px;font-weight:800;margin-bottom:4px;'>Risk Radar</div>"
        "<div style='font-size:12px;color:var(--t3);margin-bottom:14px;'>"
        "Replenishment priority · Breach timeline · Coverage gap analysis · LLM interpretation</div>",
        unsafe_allow_html=True,
    )

    active_m = summary[summary.risk != "INSUFFICIENT_DATA"]
    note("Only 1 plant in data: FI11 Turku. Safety Stock from Material Master. Lead Time from Material Master.")

    # ── Replenishment Priority Queue ──────────────────────────────────────────
    sec("Replenishment Priority Queue")
    note("Replenishment = CEILING(Shortfall/FLS)×FLS where Shortfall = SAP SS − Stock-in-Hand. Lead time shown for urgency context.")

    for _, row in active_m.sort_values("days_cover").iterrows():
        risk = row["risk"]
        if risk not in ["CRITICAL", "WARNING", "HEALTHY"]:
            continue
        brd    = "#EF4444" if risk == "CRITICAL" else "#F59E0B" if risk == "WARNING" else "#E2E8F0"
        bgc    = "rgba(239,68,68,0.03)" if risk == "CRITICAL" else "rgba(245,158,11,0.02)" if risk == "WARNING" else "#FFFFFF"
        repl_q = int(row.get("repl_quantity", 0))
        lt     = round(row["lead_time"])
        dc     = round(row["days_cover"])
        stock  = round(row["sih"])
        ss     = round(row["safety_stock"])

        if repl_q > 0:
            action_html = (
                f"<div style='background:#FEE2E2;border-radius:6px;padding:6px 10px;margin-top:8px;font-size:11px;'>"
                f"<strong style='color:#EF4444;'>ORDER {repl_q} units</strong>"
                f" <span style='color:#475569;'>| Lead time: {lt}d | Formula: {row['repl_formula']}</span>"
                f"</div>"
            )
        else:
            action_html = (
                f"<div style='background:#F0FDF4;border-radius:6px;padding:5px 10px;margin-top:8px;"
                f"font-size:10px;color:#14532d;'>✓ Stock above safety stock — {dc}d cover remaining</div>"
            )

        metric_cells = ""
        for val, lbl, vc in [
            (str(stock), "SIH",       "#EF4444" if stock < ss else "#1E293B"),
            (str(ss),    "SAP SS",    "#1E293B"),
            (f"{dc}d",   "Cover",     "#EF4444" if dc < 15 else "#F59E0B" if dc < 30 else "#22C55E"),
            (f"{lt}d",   "Lead Time", "#EF4444" if dc < lt else "#1E293B"),
        ]:
            metric_cells += (
                f"<div style='background:var(--s3);border-radius:6px;padding:4px;'>"
                f"<div style='font-size:12px;font-weight:900;color:{vc};'>{val}</div>"
                f"<div style='font-size:8px;color:var(--t3);'>{lbl}</div></div>"
            )

        st.markdown(
            f"<div class='prow' style='border-left:3px solid {brd};background:{bgc};'>"
            f"{sbadge(risk)}"
            f"<div style='flex:1;margin-left:8px;'>"
            f"<div style='font-size:12px;font-weight:800;color:var(--t);'>{row['name']}</div>"
            f"<div style='font-size:10px;color:var(--t3);'>{row['material']}</div>"
            f"</div>"
            f"<div style='display:grid;grid-template-columns:repeat(4,68px);gap:4px;text-align:center;'>"
            + metric_cells +
            f"</div></div>{action_html}",
            unsafe_allow_html=True,
        )

    # ── Historical Breach Timeline (with improved legend colors) ──────────────
    sec("Historical Breach Timeline")
    note("Red = stock below SAP Safety Stock (breach). Amber = warning zone (stock < SS × 1.5). Each row = one material.")
    note("Materials with insufficient data are omitted from the heatmap.")

    breach_events = []
    all_periods = set()

    # First pass: collect events and track all periods
    for _, row in active_m.iterrows():
        sh_r = get_stock_history(data, row["material"])
        ss   = row["safety_stock"]
        effective_ss = max(ss, 1)
        for _, sr in sh_r.iterrows():
            period_raw = sr["Fiscal Period"]
            period_label = sr["label"]
            all_periods.add((period_raw, period_label))
            s = 0
            if sr["Gross Stock"] < effective_ss:
                s = 2
            elif sr["Gross Stock"] < effective_ss * 1.5:
                s = 1
            if s > 0:  # only store if breach or warning to avoid huge data
                breach_events.append({
                    "Material": row["name"][:22],
                    "Period": period_label,
                    "period_raw": period_raw,
                    "Status": s,
                })

    # Ensure every material in active_m appears at least once (with status 0) to create a row
    materials_in_events = {e["Material"] for e in breach_events}
    for _, row in active_m.iterrows():
        mat_name = row["name"][:22]
        if mat_name not in materials_in_events and len(all_periods) > 0:
            # Add a dummy safe event for the earliest period
            earliest_period = min(all_periods, key=lambda x: x[0])
            breach_events.append({
                "Material": mat_name,
                "Period": earliest_period[1],
                "period_raw": earliest_period[0],
                "Status": 0,
            })

    if breach_events:
        df_be = pd.DataFrame(breach_events)
        ap    = df_be.drop_duplicates("period_raw").sort_values("period_raw")
        sc_   = [fmt_p(p) for p in ap["period_raw"].tolist()]
        pv    = df_be.pivot_table(index="Material", columns="Period", values="Status", aggfunc="first").fillna(0)
        pv    = pv[[c for c in sc_ if c in pv.columns]]

        # Improved discrete colorscale: safe (gray), warning (amber), breach (red)
        colorscale = [
            [0, "#E2E8F0"], [0.333, "#E2E8F0"],    # safe
            [0.334, "#F59E0B"], [0.666, "#F59E0B"], # warning
            [0.667, "#EF4444"], [1, "#EF4444"],     # breach
        ]

        fig_bt = go.Figure(data=go.Heatmap(
            z=pv.values, x=pv.columns.tolist(), y=pv.index.tolist(),
            colorscale=colorscale,
            showscale=True,
            colorbar=dict(
                title="Risk Level",
                tickvals=[0.1665, 0.5, 0.8335],  # centers of each band
                ticktext=["Safe", "Warning", "Breach"],
                thickness=15,
                len=0.6,
                tickfont=dict(size=9, color="#1E293B"),
                title_font=dict(size=10, color="#1E293B"),
            ),
            hovertemplate="<b>%{y}</b><br>%{x}<extra></extra>",
            zmin=0, zmax=2,
        ))
        ct(fig_bt, 230, margin=dict(l=10, r=80, t=20, b=60))
        fig_bt.update_layout(
            xaxis=dict(tickangle=-40, tickfont=dict(size=9)),
            yaxis=dict(tickfont=dict(size=10)),
        )
        st.plotly_chart(fig_bt, use_container_width=True)

        if st.session_state.azure_client:
            if st.button("◈ Interpret Breach Timeline", key="interp_breach"):
                with st.spinner("ARIA interpreting…"):
                    chart_data = {
                        "total_breach_events":    int(summary["breach_count"].sum()),
                        "materials_with_breaches": summary[summary.breach_count > 0]["name"].tolist(),
                        "worst_material":          summary.sort_values("breach_count", ascending=False).iloc[0]["name"],
                        "worst_count":             int(summary["breach_count"].max()),
                    }
                    interp = interpret_chart(st.session_state.azure_client, AZURE_DEPLOYMENT,
                                             "Historical Breach Timeline heatmap", chart_data)
                st.markdown(
                    f"<div class='ic' style='margin-top:8px;'><div class='il'>◈ ARIA Interpretation</div>"
                    f"<div class='ib' style='margin-top:4px;'>{interp}</div></div>",
                    unsafe_allow_html=True,
                )

    # ── Safety Stock Coverage Gap ─────────────────────────────────────────────
    sec("Safety Stock Coverage Gap Analysis")
    gap_data = active_m.copy()
    gap_data["ss_gap"] = gap_data["rec_safety_stock"] - gap_data["safety_stock"]
    gap_data = gap_data.sort_values("ss_gap", ascending=True)

    fig_gap = go.Figure()
    fig_gap.add_trace(go.Bar(
        y=gap_data["name"].str[:22], x=gap_data["safety_stock"], orientation="h",
        name="SAP Safety Stock", marker_color="rgba(239,68,68,0.5)", marker_line_width=0,
    ))
    fig_gap.add_trace(go.Bar(
        y=gap_data["name"].str[:22], x=gap_data["rec_safety_stock"], orientation="h",
        name="ARIA Recommended (95% SL)", marker_color="rgba(34,197,94,0.5)", marker_line_width=0,
    ))
    fig_gap.add_trace(go.Scatter(
        y=gap_data["name"].str[:22], x=gap_data["sih"], mode="markers",
        name="Current Stock (SIH)",
        marker=dict(symbol="diamond", size=10, color=ORANGE, line=dict(width=1.5, color="white")),
    ))
    ct(fig_gap, 240)
    fig_gap.update_layout(barmode="overlay", xaxis_title="Units",
                           legend=dict(font_size=9, y=1.12), margin=dict(l=10, r=40, t=32, b=8))
    st.plotly_chart(fig_gap, use_container_width=True)

    note("Orange diamond = current stock. Where diamond is LEFT of red bar = stock below SAP Safety Stock. "
         "ARIA SS = 1.65 × σ_demand × √(lead_time/30). SAP SS from Material Master.")

    if st.session_state.azure_client:
        if st.button("◈ Interpret Coverage Gap", key="interp_gap"):
            with st.spinner("ARIA interpreting…"):
                cd      = {"materials": gap_data[["name", "safety_stock", "rec_safety_stock", "sih", "ss_gap"]].to_dict("records")}
                interp2 = interpret_chart(
                    st.session_state.azure_client, AZURE_DEPLOYMENT,
                    "Safety Stock Coverage Gap chart", cd,
                    "Which materials have the most concerning safety stock gaps and what should procurement prioritise?",
                )
            st.markdown(
                f"<div class='ic' style='margin-top:8px;'><div class='il'>◈ ARIA Interpretation</div>"
                f"<div class='ib' style='margin-top:4px;'>{interp2}</div></div>",
                unsafe_allow_html=True,
            )

    st.markdown('<div class="pfooter">📡 Powered by <strong>MResult</strong></div>', unsafe_allow_html=True)
