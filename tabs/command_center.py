# # # # """
# # # # tabs/command_center.py
# # # # Command Center tab: KPI cards, Material Health Board, Intelligence Feed,
# # # # analytics charts, and product deep-dive.
# # # # """

# # # # import streamlit as st
# # # # import pandas as pd
# # # # import plotly.graph_objects as go
# # # # from st_aggrid import AgGrid, GridOptionsBuilder, JsCode, GridUpdateMode

# # # # from utils.helpers import ct, fmt_p, sbadge, sec, note, ORANGE, AZURE_DEPLOYMENT
# # # # from data_loader import get_stock_history, get_demand_history
# # # # from agent import chat_with_data


# # # # # ── KPI card renderer ─────────────────────────────────────────────────────────
# # # # _SVG = {
# # # #     "tot":  '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="8" r="4"/><path d="M4 20c0-4 3.6-7 8-7s8 3 8 7"/></svg>',
# # # #     "crit": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>',
# # # #     "insuf":'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>',
# # # #     "ok":   '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>',
# # # # }


# # # # def _kpi(col, svg, si, val, vc, lbl, dlt=None, dc="sdu"):
# # # #     dh = (f'<span class="sdt {dc}">{dlt}</span>') if dlt else ""
# # # #     with col:
# # # #         st.markdown(
# # # #             f"<div class='sc'><div class='si {si}'>{svg}</div>"
# # # #             f"<div style='flex:1;'><div class='sv' style='color:{vc};'>{val}</div>"
# # # #             f"<div class='sl'>{lbl}</div></div>{dh}</div>",
# # # #             unsafe_allow_html=True,
# # # #         )


# # # # # ── AgGrid JS renderers ────────────────────────────────────────────────────────
# # # # _STATUS_R = JsCode("""class R{init(p){const m={'CRITICAL':['#FEE2E2','#EF4444','⛔ Critical'],'WARNING':['#FEF3C7','#F59E0B','⚠ Warning'],'HEALTHY':['#DCFCE7','#22C55E','✓ Healthy'],'INSUFFICIENT_DATA':['#F1F5F9','#94A3B8','◌ No Data']};const[bg,c,l]=m[p.value]||m.INSUFFICIENT_DATA;this.e=document.createElement('span');this.e.style.cssText=`background:${bg};color:${c};border:1px solid ${c}44;padding:2px 7px;border-radius:20px;font-size:9px;font-weight:700;white-space:nowrap;`;this.e.innerText=l;}getGui(){return this.e;}}""")
# # # # _SPARK_R   = JsCode("""class R{init(p){const raw=(p.value||'').split(',').map(Number).filter(n=>!isNaN(n));const w=72,h=22,pad=3;this.e=document.createElement('div');if(!raw.length){this.e.innerText='—';return;}const mn=Math.min(...raw),mx=Math.max(...raw),rng=mx-mn||1;const pts=raw.map((v,i)=>{const x=pad+i*(w-2*pad)/(raw.length-1||1);const y=h-pad-(v-mn)/rng*(h-2*pad);return x+','+y;}).join(' ');const l=raw[raw.length-1],f=raw[0];const t=l>f?'#22C55E':l<f?'#EF4444':'#F47B25';this.e.innerHTML=`<svg width="${w}" height="${h}"><polyline points="${pts}" fill="none" stroke="${t}" stroke-width="1.8" stroke-linejoin="round" stroke-linecap="round"/><circle cx="${pts.split(' ').pop().split(',')[0]}" cy="${pts.split(' ').pop().split(',')[1]}" r="2" fill="${t}"/></svg>`;}getGui(){return this.e;}}""")
# # # # _COVER_R   = JsCode("""class R{init(p){const v=p.value||0;const pct=Math.min(v/180*100,100);const c=v<15?'#EF4444':v<30?'#F59E0B':'#22C55E';this.e=document.createElement('div');this.e.style.cssText='display:flex;align-items:center;gap:4px;width:100%;';this.e.innerHTML=`<div style="flex:1;height:5px;background:#F0F4F9;border-radius:3px;overflow:hidden;"><div style="width:${pct}%;height:100%;background:${c};border-radius:3px;"></div></div><span style="font-size:10px;font-weight:700;color:${c};min-width:28px;">${v}d</span>`;}getGui(){return this.e;}}""")
# # # # _ORDER_R   = JsCode("""class R{init(p){const v=p.value||0;this.e=document.createElement('span');if(v>0){this.e.style.cssText='background:#FEE2E2;color:#EF4444;border:1px solid #EF444440;padding:2px 7px;border-radius:5px;font-size:10px;font-weight:700;';this.e.innerText=v+' units';}else{this.e.style.cssText='background:#F0F4F9;color:#94A3B8;padding:2px 7px;border-radius:5px;font-size:10px;';this.e.innerText='—';};}getGui(){return this.e;}}""")
# # # # _ROW_STYLE = JsCode("""function(p){if(p.data.Risk==='CRITICAL')return{'background':'rgba(239,68,68,0.03)','border-left':'3px solid #EF4444'};if(p.data.Risk==='WARNING')return{'background':'rgba(245,158,11,0.02)','border-left':'3px solid #F59E0B'};if(p.data.Risk==='INSUFFICIENT_DATA')return{'color':'#94A3B8'};return{};}""")

# # # # _AGGRID_CSS = {
# # # #     ".ag-root-wrapper": {"border": "1px solid #E2E8F0!important", "border-radius": "14px!important", "overflow": "hidden"},
# # # #     ".ag-header":       {"background": "#F8FAFE!important"},
# # # #     ".ag-row-even":     {"background": "#FFFFFF!important"},
# # # #     ".ag-row-odd":      {"background": "#F8FAFE!important"},
# # # #     ".ag-cell":         {"border-right": "1px solid #F0F4F9!important"},
# # # # }


# # # # def render():
# # # #     data    = st.session_state.data
# # # #     summary = st.session_state.summary

# # # #     # ── KPI Row ───────────────────────────────────────────────────────────────
# # # #     total   = len(summary)
# # # #     crit_n  = int((summary.risk == "CRITICAL").sum())
# # # #     insuf_n = int((summary.risk == "INSUFFICIENT_DATA").sum())
# # # #     ok_n    = int((summary.risk == "HEALTHY").sum())

# # # #     k1, k2, k3, k4 = st.columns(4)
# # # #     _kpi(k1, _SVG["tot"],   "sio", total,   "#1E293B", "Total Materials")
# # # #     _kpi(k2, _SVG["crit"],  "sir", crit_n,  "#EF4444", "Critical Alerts",
# # # #          "⛔ Action required" if crit_n > 0 else "✓ None",
# # # #          "sdc" if crit_n > 0 else "sdu")
# # # #     _kpi(k3, _SVG["insuf"], "six", insuf_n, "#94A3B8", "Insufficient Data",
# # # #          str(insuf_n) + " SKUs", "sdw" if insuf_n > 0 else "sdu")
# # # #     _kpi(k4, _SVG["ok"],    "sig", ok_n,    "#22C55E", "Healthy", "↑ Operating", "sdu")

# # # #     # ── Main Row: Health Board + Intelligence Feed ────────────────────────────
# # # #     st.markdown("<div style='height:14px;'></div>", unsafe_allow_html=True)
# # # #     board_col, feed_col = st.columns([3, 2], gap="medium")

# # # #     with board_col:
# # # #         st.markdown(
# # # #             "<div style='font-size:13px;font-weight:800;color:var(--t);margin-bottom:8px;'>"
# # # #             "Material Health Board"
# # # #             "<span style='font-size:11px;font-weight:400;color:var(--t3);margin-left:8px;'>Sortable · Click to inspect</span>"
# # # #             "</div>",
# # # #             unsafe_allow_html=True,
# # # #         )
# # # #         grid_rows = []
# # # #         for _, row in summary.iterrows():
# # # #             sh2 = get_stock_history(data, row["material"])
# # # #             dh2 = get_demand_history(data, row["material"])
# # # #             nz  = dh2[dh2.demand > 0]
# # # #             avg = float(nz.demand.mean()) if len(nz) > 0 else 0
# # # #             ss  = row["safety_stock"]
# # # #             br  = sh2[sh2["Gross Stock"] < max(ss, 1)] if ss > 0 else pd.DataFrame()
# # # #             lb  = fmt_p(br["Fiscal Period"].iloc[-1]) if len(br) > 0 else "—"
# # # #             spark = sh2["Gross Stock"].tail(8).tolist()
# # # #             dc  = row["days_cover"]
# # # #             grid_rows.append({
# # # #                 "Risk": row["risk"], "Material": row["name"],
# # # #                 "Stock": int(row["sih"]), "SAP SS": int(ss), "ARIA SS": int(row["rec_safety_stock"]),
# # # #                 "Days Cover": int(dc) if dc < 999 else 0,
# # # #                 "Demand/mo": round(avg, 0), "Trend": row["trend"],
# # # #                 "Breaches": int(row["breach_count"]), "Last Breach": lb,
# # # #                 "Order Now": int(row["repl_quantity"]),
# # # #                 "Spark": (",".join([str(round(v)) for v in spark])),
# # # #             })
# # # #         df_grid = pd.DataFrame(grid_rows)

# # # #         gb = GridOptionsBuilder.from_dataframe(df_grid)
# # # #         gb.configure_column("Risk",       cellRenderer=_STATUS_R, width=110, minWidth=110, maxWidth=110, pinned="left")
# # # #         gb.configure_column("Material",   width=170, minWidth=170, maxWidth=170, pinned="left")
# # # #         gb.configure_column("Stock",      width=62,  minWidth=62,  maxWidth=62,  type=["numericColumn"])
# # # #         gb.configure_column("SAP SS",     width=62,  minWidth=62,  maxWidth=62,  type=["numericColumn"])
# # # #         gb.configure_column("ARIA SS",    width=66,  minWidth=66,  maxWidth=66,  type=["numericColumn"])
# # # #         gb.configure_column("Days Cover", width=120, minWidth=120, maxWidth=120, cellRenderer=_COVER_R)
# # # #         gb.configure_column("Demand/mo",  width=78,  minWidth=78,  maxWidth=78,  type=["numericColumn"])
# # # #         gb.configure_column("Trend",      width=68,  minWidth=68,  maxWidth=68)
# # # #         gb.configure_column("Breaches",   width=66,  minWidth=66,  maxWidth=66,  type=["numericColumn"])
# # # #         gb.configure_column("Last Breach",width=82,  minWidth=82,  maxWidth=82)
# # # #         gb.configure_column("Order Now",  width=82,  minWidth=82,  maxWidth=82,  cellRenderer=_ORDER_R)
# # # #         gb.configure_column("Spark",      width=90,  minWidth=90,  maxWidth=90,  cellRenderer=_SPARK_R, headerName="8m Trend")
# # # #         gb.configure_grid_options(rowHeight=42, headerHeight=34, getRowStyle=_ROW_STYLE,
# # # #                                    suppressMovableColumns=True, suppressColumnVirtualisation=True)
# # # #         gb.configure_selection("single", use_checkbox=False)
# # # #         gb.configure_default_column(resizable=False, sortable=True, filter=False)

# # # #         AgGrid(df_grid, gridOptions=gb.build(), height=340, allow_unsafe_jscode=True,
# # # #                update_mode=GridUpdateMode.SELECTION_CHANGED, theme="alpine",
# # # #                custom_css=_AGGRID_CSS)

# # # #     with feed_col:
# # # #         st.markdown(
# # # #             "<div style='font-size:13px;font-weight:800;color:var(--t);margin-bottom:8px;'>Intelligence Feed</div>",
# # # #             unsafe_allow_html=True,
# # # #         )
# # # #         feed_items = []
# # # #         for _, row in summary[summary.risk == "CRITICAL"].iterrows():
# # # #             repl_q = int(row["repl_quantity"])
# # # #             feed_items.append({
# # # #                 "dot": "#EF4444", "type": "crit", "time": "Now",
# # # #                 "msg": "<span>⛔ " + row["name"] + "</span>",
# # # #                 "sub": str(round(row["sih"])) + " units stock · " + str(round(row["days_cover"])) + "d cover · SS=" + str(round(row["safety_stock"]))
# # # #                        + (" · ORDER " + str(repl_q) + " units NOW" if repl_q > 0 else ""),
# # # #             })
# # # #         for _, row in summary[summary.risk == "WARNING"].iterrows():
# # # #             feed_items.append({
# # # #                 "dot": ORANGE, "type": "warn", "time": "Live",
# # # #                 "msg": "<span>⚠ " + row["name"] + "</span>",
# # # #                 "sub": str(round(row["days_cover"])) + "d cover remaining · Approaching safety stock threshold",
# # # #             })
# # # #         ss_gap = summary[(summary.safety_stock < summary.rec_safety_stock) & (summary.risk != "INSUFFICIENT_DATA")]
# # # #         for _, row in ss_gap.sort_values("breach_count", ascending=False).head(2).iterrows():
# # # #             g = round(row["rec_safety_stock"] - row["safety_stock"])
# # # #             if g > 0:
# # # #                 feed_items.append({
# # # #                     "dot": "#F59E0B", "type": "warn", "time": "Audit",
# # # #                     "msg": "<span>SAP SS Under-configured</span> — " + row["name"][:20],
# # # #                     "sub": "SAP: " + str(round(row["safety_stock"])) + " units · ARIA recommends: "
# # # #                            + str(round(row["rec_safety_stock"])) + " · Gap: " + str(g) + " units",
# # # #                 })
# # # #         top_b = summary[(summary.breach_count > 0) & (summary.risk != "INSUFFICIENT_DATA")].sort_values("breach_count", ascending=False)
# # # #         if len(top_b) > 0:
# # # #             r = top_b.iloc[0]
# # # #             feed_items.append({
# # # #                 "dot": ORANGE, "type": "info", "time": "History",
# # # #                 "msg": "<span>" + r["name"] + "</span> — " + str(r["breach_count"]) + " stockout events",
# # # #                 "sub": "Worst performer over 25 months · " + str(round(r["breach_count"])) + " periods below safety stock",
# # # #             })
# # # #         lt_critical = summary[(summary.days_cover < summary.lead_time) & (summary.risk != "INSUFFICIENT_DATA")]
# # # #         for _, row in lt_critical.iterrows():
# # # #             feed_items.append({
# # # #                 "dot": "#EF4444", "type": "crit", "time": "Urgent",
# # # #                 "msg": "<span>Lead Time Exceeds Cover</span> — " + row["name"][:22],
# # # #                 "sub": "Cover=" + str(round(row["days_cover"])) + "d but Lead Time=" + str(round(row["lead_time"])) + "d · Order immediately",
# # # #             })
# # # #         feed_items.append({
# # # #             "dot": "#22C55E", "type": "ok", "time": "System",
# # # #             "msg": "<span>ARIA</span> — Safety stock models updated",
# # # #             "sub": "Formula: CEILING(Shortfall/FLS)×FLS · Source: Material Master",
# # # #         })

# # # #         tag_map = {"crit": "ftc", "warn": "ftw", "ok": "fto", "info": "fti"}
# # # #         tag_lbl = {"crit": "Critical", "warn": "Warning", "ok": "Healthy", "info": "Update"}
# # # #         items_html = ""
# # # #         for i, item in enumerate(feed_items[:9]):
# # # #             line     = "" if i >= 8 else "<div class='fi-line'></div>"
# # # #             sub_html = (f"<div class='fi-sub'>{item.get('sub','')}</div>") if item.get("sub") else ""
# # # #             items_html += (
# # # #                 f"<div class='fi'><div class='fi-dc'>"
# # # #                 f"<div class='fi-dot' style='background:{item['dot']};'></div>{line}</div>"
# # # #                 f"<div style='flex:1;min-width:0;'>"
# # # #                 f"<div class='fi-msg'>{item['msg']}</div>"
# # # #                 + sub_html +
# # # #                 f"<div style='display:flex;align-items:center;gap:6px;margin-top:2px;'>"
# # # #                 f"<div class='fi-time'>{item['time']}</div>"
# # # #                 f"<span class='fi-tag {tag_map[item['type']]}'>{tag_lbl[item['type']]}</span>"
# # # #                 f"</div></div></div>"
# # # #             )
# # # #         st.markdown(
# # # #             "<div class='fc' style='height:340px;overflow-y:auto;'>"
# # # #             "<div class='fh'><div class='fht'>Intelligence Feed</div>"
# # # #             "<div class='flv'><div class='dot dot-g'></div>Live</div>"
# # # #             "</div>" + items_html + "</div>",
# # # #             unsafe_allow_html=True,
# # # #         )

# # # #     # ── Analytics ─────────────────────────────────────────────────────────────
# # # #     st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)
# # # #     sec("Supply Chain Analytics")
# # # #     c1, c2 = st.columns(2, gap="medium")

# # # #     with c1:
# # # #         st.markdown(
# # # #             "<div style='font-size:11px;font-weight:700;color:var(--t2);margin-bottom:5px;'>"
# # # #             "Historical Stockout Events by Month &amp; Product</div>",
# # # #             unsafe_allow_html=True,
# # # #         )
# # # #         all_breaches = []
# # # #         for _, row in summary[summary.breach_count > 0].iterrows():
# # # #             sh3 = get_stock_history(data, row["material"])
# # # #             ss  = row["safety_stock"]
# # # #             if ss <= 0:
# # # #                 continue
# # # #             b = sh3[sh3["Gross Stock"] < ss]
# # # #             for _, br in b.iterrows():
# # # #                 all_breaches.append({"label": fmt_p(br["Fiscal Period"]), "period": br["Fiscal Period"], "material": row["name"][:16]})

# # # #         if all_breaches:
# # # #             df_br = pd.DataFrame(all_breaches)
# # # #             pivot = df_br.groupby(["period", "label", "material"]).size().reset_index(name="count")
# # # #             pivot = pivot.sort_values("period")
# # # #             recent_periods = pivot["period"].unique()[-14:]
# # # #             pivot = pivot[pivot["period"].isin(recent_periods)]
# # # #             colors = ["#EF4444", "#F59E0B", "#8B5CF6", "#EC4899", "#06B6D4"]
# # # #             fig1   = go.Figure()
# # # #             for i, mat in enumerate(pivot["material"].unique()):
# # # #                 md     = pivot[pivot.material == mat]
# # # #                 periods_all = pivot["label"].unique().tolist()
# # # #                 counts = [md[md.label == p]["count"].sum() if p in md["label"].values else 0 for p in periods_all]
# # # #                 fig1.add_trace(go.Bar(
# # # #                     name=mat, x=periods_all, y=counts,
# # # #                     marker_color=colors[i % len(colors)], marker_line_width=0,
# # # #                     hovertemplate="<b>%{x}</b><br>" + mat + ": %{y} breach(es)<extra></extra>",
# # # #                 ))
# # # #             ct(fig1, 210)
# # # #             fig1.update_layout(barmode="stack", showlegend=True,
# # # #                                legend=dict(font_size=9, orientation="h", y=1.12),
# # # #                                xaxis_tickangle=-40, yaxis=dict(dtick=1, title="Breaches"))
# # # #             st.plotly_chart(fig1, use_container_width=True)
# # # #         else:
# # # #             st.markdown(
# # # #                 "<div style='height:210px;display:flex;align-items:center;justify-content:center;"
# # # #                 "color:var(--t3);font-size:12px;border:1px solid var(--bl);border-radius:var(--r);'>"
# # # #                 "No breach events recorded</div>",
# # # #                 unsafe_allow_html=True,
# # # #             )

# # # #     with c2:
# # # #         st.markdown(
# # # #             "<div style='font-size:11px;font-weight:700;color:var(--t2);margin-bottom:5px;'>Days of Cover per SKU</div>",
# # # #             unsafe_allow_html=True,
# # # #         )
# # # #         act2  = summary[summary.risk.isin(["CRITICAL", "WARNING", "HEALTHY"])].sort_values("days_cover")
# # # #         clrs2 = ["#EF4444" if r == "CRITICAL" else "#F59E0B" if r == "WARNING" else "#22C55E" for r in act2["risk"]]
# # # #         cap   = [min(float(v), 300) for v in act2["days_cover"]]
# # # #         fig2  = go.Figure()
# # # #         fig2.add_trace(go.Bar(
# # # #             y=act2["name"].str[:22].tolist(), x=cap, orientation="h",
# # # #             marker_color=clrs2, marker_opacity=0.85, marker_line_width=0,
# # # #             text=[(str(round(v)) + "d") for v in cap],
# # # #             textposition="outside", textfont=dict(size=9, color="#475569"),
# # # #             hovertemplate="<b>%{y}</b><br>Days cover: %{x:.0f}d<extra></extra>",
# # # #         ))
# # # #         fig2.add_vline(x=30, line_color="#EF4444", line_dash="dot", line_width=1.5,
# # # #                        annotation_text="30d min", annotation_font_color="#EF4444", annotation_font_size=9)
# # # #         ct(fig2, 210)
# # # #         fig2.update_layout(showlegend=False, xaxis_title="Days", margin=dict(l=8, r=48, t=28, b=8))
# # # #         st.plotly_chart(fig2, use_container_width=True)

# # # #     # ── ARIA LLM Insight ──────────────────────────────────────────────────────
# # # #     if st.session_state.azure_client:
# # # #         ai2, rb2 = st.columns([10, 1])
# # # #         with rb2:
# # # #             if st.button("↺", key="ref_cc", help="Refresh ARIA overview"):
# # # #                 st.session_state.cc_insight = None
# # # #         if st.session_state.cc_insight is None:
# # # #             crit_mat = summary[summary.risk == "CRITICAL"]
# # # #             ctx_str  = (
# # # #                 f"Plant FI11 Turku: {total} materials. Critical: {crit_n}"
# # # #                 + (f" ({', '.join(crit_mat['name'].tolist())})" if len(crit_mat) > 0 else "")
# # # #                 + f". Insufficient data: {insuf_n}. Healthy: {ok_n}. "
# # # #                 + f"Most critical: {summary.sort_values('days_cover').iloc[0]['name']} "
# # # #                 + f"with {summary.sort_values('days_cover').iloc[0]['days_cover']:.1f}d cover, "
# # # #                 + f"stock={summary.sort_values('days_cover').iloc[0]['sih']:.0f} "
# # # #                 + f"vs SS={summary.sort_values('days_cover').iloc[0]['safety_stock']:.0f}."
# # # #             )
# # # #             try:
# # # #                 insight = chat_with_data(
# # # #                     st.session_state.azure_client, AZURE_DEPLOYMENT,
# # # #                     "Give a 2-sentence executive briefing on the current supply chain health. "
# # # #                     "Identify the single biggest risk and one specific action.",
# # # #                     ctx_str,
# # # #                 )
# # # #                 st.session_state.cc_insight = insight
# # # #             except Exception:
# # # #                 st.session_state.cc_insight = None
# # # #         if st.session_state.cc_insight:
# # # #             st.markdown(
# # # #                 "<div class='ic' style='margin:10px 0;'>"
# # # #                 "<div class='il'>◈ ARIA PLANT INTELLIGENCE</div>"
# # # #                 f"<div class='ib' style='margin-top:4px;'>{st.session_state.cc_insight}</div>"
# # # #                 "</div>",
# # # #                 unsafe_allow_html=True,
# # # #             )

# # # #     # ── Product Deep-Dive ─────────────────────────────────────────────────────
# # # #     sec("Product Deep-Dive")
# # # #     note("Days cover = SIH (Stock-in-Hand from Current Inventory) ÷ avg daily demand (from Sales file). Safety Stock from Material Master.")

# # # #     pd_col1, pd_col2 = st.columns([2, 1])
# # # #     with pd_col1:
# # # #         prod_opts = [r["name"] for _, r in summary[summary.risk != "INSUFFICIENT_DATA"].iterrows()]
# # # #         sel_prod  = st.selectbox("Select product", prod_opts, key="cc_prod")
# # # #     with pd_col2:
# # # #         month_range = st.slider("Show last N months", 6, 60, 24, step=6, key="cc_months")

# # # #     sel_mat_id  = summary[summary.name == sel_prod]["material"].values[0]
# # # #     dh_cc       = get_demand_history(data, sel_mat_id)
# # # #     sh_cc       = get_stock_history(data, sel_mat_id)
# # # #     mat_row_cc  = summary[summary.material == sel_mat_id].iloc[0]
# # # #     ss_cc       = mat_row_cc["safety_stock"]
# # # #     repl_cc     = int(mat_row_cc["repl_quantity"])
# # # #     lt_cc       = float(mat_row_cc["lead_time"])
# # # #     lot_cc      = float(mat_row_cc["lot_size"])
# # # #     sih_cc      = float(mat_row_cc["sih"])

# # # #     sh_cc   = sh_cc.tail(month_range)
# # # #     dh_cc_f = dh_cc.tail(month_range)

# # # #     if len(sh_cc) > 0:
# # # #         fig_dd  = go.Figure()
# # # #         avg_d   = float(dh_cc_f[dh_cc_f.demand > 0]["demand"].mean()) if len(dh_cc_f[dh_cc_f.demand > 0]) > 0 else 0
# # # #         fig_dd.add_trace(go.Scatter(
# # # #             x=sh_cc["label"], y=sh_cc["Gross Stock"], mode="lines+markers", name="Stock (units)",
# # # #             line=dict(color=ORANGE, width=2.5), marker=dict(size=4, color=ORANGE),
# # # #             fill="tozeroy", fillcolor="rgba(244,123,37,0.08)", yaxis="y1",
# # # #             hovertemplate="<b>%{x}</b><br>Stock: %{y} units<extra></extra>",
# # # #         ))
# # # #         dem_aligned = dh_cc_f[dh_cc_f.label.isin(sh_cc["label"].tolist())]
# # # #         if len(dem_aligned) > 0:
# # # #             fig_dd.add_trace(go.Bar(
# # # #                 x=dem_aligned["label"], y=dem_aligned["demand"], name="Demand/mo",
# # # #                 marker_color="rgba(148,163,184,0.3)", marker_line_width=0, yaxis="y2",
# # # #                 hovertemplate="<b>%{x}</b><br>Demand: %{y} units<extra></extra>",
# # # #             ))
# # # #         if ss_cc > 0:
# # # #             fig_dd.add_hline(y=ss_cc, line_color="#EF4444", line_dash="dot", line_width=1.5,
# # # #                              annotation_text="SAP SS " + str(round(ss_cc)) + "u",
# # # #                              annotation_font_color="#EF4444", annotation_font_size=9)
# # # #         ct(fig_dd, 240)
# # # #         fig_dd.update_layout(
# # # #             title=dict(text=sel_prod + " — Stock vs Demand (last " + str(month_range) + "mo)",
# # # #                        font=dict(size=11, color="#475569"), x=0),
# # # #             xaxis=dict(tickangle=-35),
# # # #             yaxis=dict(title="Stock (units)", gridcolor="#F0F4F9"),
# # # #             yaxis2=dict(title="Demand/mo", overlaying="y", side="right", showgrid=False),
# # # #             legend=dict(orientation="h", y=1.1),
# # # #             margin=dict(l=8, r=50, t=44, b=8),
# # # #         )
# # # #         st.plotly_chart(fig_dd, use_container_width=True)

# # # #     if repl_cc > 0:
# # # #         st.markdown(
# # # #             "<div class='prow' style='border-left:3px solid #EF4444;background:#FEF2F2;'>"
# # # #             "<div style='font-size:16px;'>⛔</div>"
# # # #             "<div style='flex:1;'>"
# # # #             "<div style='font-size:12px;font-weight:800;color:#EF4444;'>Replenishment Required</div>"
# # # #             "<div style='font-size:11px;color:#475569;margin-top:2px;'>"
# # # #             f"Stock-in-Hand: <strong>{round(sih_cc)}</strong> · SAP SS: <strong>{round(ss_cc)}</strong> · "
# # # #             f"Lead time: <strong>{round(lt_cc)}d</strong> (Material Master) · "
# # # #             f"Lot size: <strong>{round(lot_cc)}</strong>"
# # # #             "</div></div>"
# # # #             "<div style='text-align:right;'>"
# # # #             f"<div style='font-size:22px;font-weight:900;color:#EF4444;'>{repl_cc} units</div>"
# # # #             f"<div style='font-size:9px;color:#EF4444;'>CEILING({round(ss_cc-sih_cc)}/{round(lot_cc)})×{round(lot_cc)}</div>"
# # # #             "</div></div>",
# # # #             unsafe_allow_html=True,
# # # #         )

# # # #     st.markdown('<div class="pfooter">⚡ Powered by <strong>MResult</strong></div>', unsafe_allow_html=True)

# # # """
# # # tabs/command_center.py
# # # Command Center tab: KPI cards, Material Health Board, Intelligence Feed,
# # # analytics charts, and product deep-dive.
# # # """

# # # import streamlit as st
# # # import pandas as pd
# # # import plotly.graph_objects as go
# # # from st_aggrid import AgGrid, GridOptionsBuilder, JsCode, GridUpdateMode

# # # from utils.helpers import ct, fmt_p, sbadge, sec, note, ORANGE, AZURE_DEPLOYMENT
# # # from data_loader import get_stock_history, get_demand_history
# # # from agent import chat_with_data


# # # # ── KPI card renderer ─────────────────────────────────────────────────────────
# # # _SVG = {
# # #     "tot":  '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="8" r="4"/><path d="M4 20c0-4 3.6-7 8-7s8 3 8 7"/></svg>',
# # #     "crit": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>',
# # #     "insuf":'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>',
# # #     "ok":   '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>',
# # # }


# # # def _kpi(col, svg, si, val, vc, lbl, dlt=None, dc="sdu"):
# # #     dh = (f'<span class="sdt {dc}">{dlt}</span>') if dlt else ""
# # #     with col:
# # #         st.markdown(
# # #             f"<div class='sc'><div class='si {si}'>{svg}</div>"
# # #             f"<div style='flex:1;'><div class='sv' style='color:{vc};'>{val}</div>"
# # #             f"<div class='sl'>{lbl}</div></div>{dh}</div>",
# # #             unsafe_allow_html=True,
# # #         )


# # # # ── AgGrid JS renderers ────────────────────────────────────────────────────────
# # # _STATUS_R = JsCode("""class R{init(p){const m={'CRITICAL':['#FEE2E2','#EF4444','⛔ Critical'],'WARNING':['#FEF3C7','#F59E0B','⚠ Warning'],'HEALTHY':['#DCFCE7','#22C55E','✓ Healthy'],'INSUFFICIENT_DATA':['#F1F5F9','#94A3B8','◌ No Data']};const[bg,c,l]=m[p.value]||m.INSUFFICIENT_DATA;this.e=document.createElement('span');this.e.style.cssText=`background:${bg};color:${c};border:1px solid ${c}44;padding:2px 7px;border-radius:20px;font-size:9px;font-weight:700;white-space:nowrap;`;this.e.innerText=l;}getGui(){return this.e;}}""")
# # # _SPARK_R   = JsCode("""class R{init(p){const raw=(p.value||'').split(',').map(Number).filter(n=>!isNaN(n));const w=72,h=22,pad=3;this.e=document.createElement('div');if(!raw.length){this.e.innerText='—';return;}const mn=Math.min(...raw),mx=Math.max(...raw),rng=mx-mn||1;const pts=raw.map((v,i)=>{const x=pad+i*(w-2*pad)/(raw.length-1||1);const y=h-pad-(v-mn)/rng*(h-2*pad);return x+','+y;}).join(' ');const l=raw[raw.length-1],f=raw[0];const t=l>f?'#22C55E':l<f?'#EF4444':'#F47B25';this.e.innerHTML=`<svg width="${w}" height="${h}"><polyline points="${pts}" fill="none" stroke="${t}" stroke-width="1.8" stroke-linejoin="round" stroke-linecap="round"/><circle cx="${pts.split(' ').pop().split(',')[0]}" cy="${pts.split(' ').pop().split(',')[1]}" r="2" fill="${t}"/></svg>`;}getGui(){return this.e;}}""")
# # # _COVER_R   = JsCode("""class R{init(p){const v=p.value||0;const pct=Math.min(v/180*100,100);const c=v<15?'#EF4444':v<30?'#F59E0B':'#22C55E';this.e=document.createElement('div');this.e.style.cssText='display:flex;align-items:center;gap:4px;width:100%;';this.e.innerHTML=`<div style="flex:1;height:5px;background:#F0F4F9;border-radius:3px;overflow:hidden;"><div style="width:${pct}%;height:100%;background:${c};border-radius:3px;"></div></div><span style="font-size:10px;font-weight:700;color:${c};min-width:28px;">${v}d</span>`;}getGui(){return this.e;}}""")
# # # _ORDER_R   = JsCode("""class R{init(p){const v=p.value||0;this.e=document.createElement('span');if(v>0){this.e.style.cssText='background:#FEE2E2;color:#EF4444;border:1px solid #EF444440;padding:2px 7px;border-radius:5px;font-size:10px;font-weight:700;';this.e.innerText=v+' units';}else{this.e.style.cssText='background:#F0F4F9;color:#94A3B8;padding:2px 7px;border-radius:5px;font-size:10px;';this.e.innerText='—';};}getGui(){return this.e;}}""")
# # # _ROW_STYLE = JsCode("""function(p){if(p.data.Risk==='CRITICAL')return{'background':'rgba(239,68,68,0.03)','border-left':'3px solid #EF4444'};if(p.data.Risk==='WARNING')return{'background':'rgba(245,158,11,0.02)','border-left':'3px solid #F59E0B'};if(p.data.Risk==='INSUFFICIENT_DATA')return{'color':'#94A3B8'};return{};}""")

# # # _AGGRID_CSS = {
# # #     ".ag-root-wrapper": {"border": "1px solid #E2E8F0!important", "border-radius": "14px!important", "overflow": "hidden"},
# # #     ".ag-header":       {"background": "#F8FAFE!important"},
# # #     ".ag-row-even":     {"background": "#FFFFFF!important"},
# # #     ".ag-row-odd":      {"background": "#F8FAFE!important"},
# # #     ".ag-cell":         {"border-right": "1px solid #F0F4F9!important"},
# # # }


# # # def render():
# # #     data    = st.session_state.data
# # #     summary = st.session_state.summary

# # #     # ── KPI Row ───────────────────────────────────────────────────────────────
# # #     total   = len(summary)
# # #     crit_n  = int((summary.risk == "CRITICAL").sum())
# # #     insuf_n = int((summary.risk == "INSUFFICIENT_DATA").sum())
# # #     ok_n    = int((summary.risk == "HEALTHY").sum())

# # #     k1, k2, k3, k4 = st.columns(4)
# # #     _kpi(k1, _SVG["tot"],   "sio", total,   "#1E293B", "Total Materials")
# # #     _kpi(k2, _SVG["crit"],  "sir", crit_n,  "#EF4444", "Critical Alerts",
# # #          "⛔ Action required" if crit_n > 0 else "✓ None",
# # #          "sdc" if crit_n > 0 else "sdu")
# # #     _kpi(k3, _SVG["insuf"], "six", insuf_n, "#94A3B8", "Insufficient Data",
# # #          str(insuf_n) + " SKUs", "sdw" if insuf_n > 0 else "sdu")
# # #     _kpi(k4, _SVG["ok"],    "sig", ok_n,    "#22C55E", "Healthy", "↑ Operating", "sdu")

# # #     # ── Main Row: Health Board + Intelligence Feed ────────────────────────────
# # #     st.markdown("<div style='height:14px;'></div>", unsafe_allow_html=True)
# # #     board_col, feed_col = st.columns([3, 2], gap="medium")

# # #     with board_col:
# # #         st.markdown(
# # #             "<div style='font-size:13px;font-weight:800;color:var(--t);margin-bottom:8px;'>"
# # #             "Material Health Board"
# # #             "<span style='font-size:11px;font-weight:400;color:var(--t3);margin-left:8px;'>Sortable · Click to inspect</span>"
# # #             "</div>",
# # #             unsafe_allow_html=True,
# # #         )
# # #         grid_rows = []
# # #         for _, row in summary.iterrows():
# # #             sh2 = get_stock_history(data, row["material"])
# # #             dh2 = get_demand_history(data, row["material"])
# # #             nz  = dh2[dh2.demand > 0]
# # #             avg = float(nz.demand.mean()) if len(nz) > 0 else 0
# # #             ss  = row["safety_stock"]
# # #             br  = sh2[sh2["Gross Stock"] < max(ss, 1)] if ss > 0 else pd.DataFrame()
# # #             lb  = fmt_p(br["Fiscal Period"].iloc[-1]) if len(br) > 0 else "—"
# # #             spark = sh2["Gross Stock"].tail(8).tolist()
# # #             dc  = row["days_cover"]
# # #             grid_rows.append({
# # #                 "Risk": row["risk"], "Material": row["name"],
# # #                 "Stock": int(row["sih"]), "SAP SS": int(ss), "ARIA SS": int(row["rec_safety_stock"]),
# # #                 "Days Cover": int(dc) if dc < 999 else 0,
# # #                 "Demand/mo": round(avg, 0), "Trend": row["trend"],
# # #                 "Breaches": int(row["breach_count"]), "Last Breach": lb,
# # #                 "Order Now": int(row["repl_quantity"]),
# # #                 "Spark": (",".join([str(round(v)) for v in spark])),
# # #             })
# # #         df_grid = pd.DataFrame(grid_rows)

# # #         gb = GridOptionsBuilder.from_dataframe(df_grid)
# # #         gb.configure_column("Risk",       cellRenderer=_STATUS_R, width=110, minWidth=110, maxWidth=110, pinned="left")
# # #         gb.configure_column("Material",   width=170, minWidth=170, maxWidth=170, pinned="left")
# # #         gb.configure_column("Stock",      width=62,  minWidth=62,  maxWidth=62,  type=["numericColumn"])
# # #         gb.configure_column("SAP SS",     width=62,  minWidth=62,  maxWidth=62,  type=["numericColumn"])
# # #         gb.configure_column("ARIA SS",    width=66,  minWidth=66,  maxWidth=66,  type=["numericColumn"])
# # #         gb.configure_column("Days Cover", width=120, minWidth=120, maxWidth=120, cellRenderer=_COVER_R)
# # #         gb.configure_column("Demand/mo",  width=78,  minWidth=78,  maxWidth=78,  type=["numericColumn"])
# # #         gb.configure_column("Trend",      width=68,  minWidth=68,  maxWidth=68)
# # #         gb.configure_column("Breaches",   width=66,  minWidth=66,  maxWidth=66,  type=["numericColumn"])
# # #         gb.configure_column("Last Breach",width=82,  minWidth=82,  maxWidth=82)
# # #         gb.configure_column("Order Now",  width=82,  minWidth=82,  maxWidth=82,  cellRenderer=_ORDER_R)
# # #         gb.configure_column("Spark",      width=90,  minWidth=90,  maxWidth=90,  cellRenderer=_SPARK_R, headerName="8m Trend")
# # #         gb.configure_grid_options(rowHeight=42, headerHeight=34, getRowStyle=_ROW_STYLE,
# # #                                    suppressMovableColumns=True, suppressColumnVirtualisation=True)
# # #         gb.configure_selection("single", use_checkbox=False)
# # #         gb.configure_default_column(resizable=False, sortable=True, filter=False)

# # #         AgGrid(df_grid, gridOptions=gb.build(), height=340, allow_unsafe_jscode=True,
# # #                update_mode=GridUpdateMode.SELECTION_CHANGED, theme="alpine",
# # #                custom_css=_AGGRID_CSS)

# # #     with feed_col:
# # #         st.markdown(
# # #             "<div style='font-size:13px;font-weight:800;color:var(--t);margin-bottom:8px;'>Intelligence Feed</div>",
# # #             unsafe_allow_html=True,
# # #         )
# # #         feed_items = []
# # #         for _, row in summary[summary.risk == "CRITICAL"].iterrows():
# # #             repl_q = int(row["repl_quantity"])
# # #             feed_items.append({
# # #                 "dot": "#EF4444", "type": "crit", "time": "Now",
# # #                 "msg": "<span>⛔ " + row["name"] + "</span>",
# # #                 "sub": str(round(row["sih"])) + " units stock · " + str(round(row["days_cover"])) + "d cover · SS=" + str(round(row["safety_stock"]))
# # #                        + (" · ORDER " + str(repl_q) + " units NOW" if repl_q > 0 else ""),
# # #             })
# # #         for _, row in summary[summary.risk == "WARNING"].iterrows():
# # #             feed_items.append({
# # #                 "dot": ORANGE, "type": "warn", "time": "Live",
# # #                 "msg": "<span>⚠ " + row["name"] + "</span>",
# # #                 "sub": str(round(row["days_cover"])) + "d cover remaining · Approaching safety stock threshold",
# # #             })
# # #         ss_gap = summary[(summary.safety_stock < summary.rec_safety_stock) & (summary.risk != "INSUFFICIENT_DATA")]
# # #         for _, row in ss_gap.sort_values("breach_count", ascending=False).head(2).iterrows():
# # #             g = round(row["rec_safety_stock"] - row["safety_stock"])
# # #             if g > 0:
# # #                 feed_items.append({
# # #                     "dot": "#F59E0B", "type": "warn", "time": "Audit",
# # #                     "msg": "<span>SAP SS Under-configured</span> — " + row["name"][:20],
# # #                     "sub": "SAP: " + str(round(row["safety_stock"])) + " units · ARIA recommends: "
# # #                            + str(round(row["rec_safety_stock"])) + " · Gap: " + str(g) + " units",
# # #                 })
# # #         top_b = summary[(summary.breach_count > 0) & (summary.risk != "INSUFFICIENT_DATA")].sort_values("breach_count", ascending=False)
# # #         if len(top_b) > 0:
# # #             r = top_b.iloc[0]
# # #             feed_items.append({
# # #                 "dot": ORANGE, "type": "info", "time": "History",
# # #                 "msg": "<span>" + r["name"] + "</span> — " + str(r["breach_count"]) + " stockout events",
# # #                 "sub": "Worst performer over 25 months · " + str(round(r["breach_count"])) + " periods below safety stock",
# # #             })
# # #         lt_critical = summary[(summary.days_cover < summary.lead_time) & (summary.risk != "INSUFFICIENT_DATA")]
# # #         for _, row in lt_critical.iterrows():
# # #             feed_items.append({
# # #                 "dot": "#EF4444", "type": "crit", "time": "Urgent",
# # #                 "msg": "<span>Lead Time Exceeds Cover</span> — " + row["name"][:22],
# # #                 "sub": "Cover=" + str(round(row["days_cover"])) + "d but Lead Time=" + str(round(row["lead_time"])) + "d · Order immediately",
# # #             })
# # #         feed_items.append({
# # #             "dot": "#22C55E", "type": "ok", "time": "System",
# # #             "msg": "<span>ARIA</span> — Safety stock models updated",
# # #             "sub": "Formula: CEILING(Shortfall/FLS)×FLS · Source: Material Master",
# # #         })

# # #         tag_map = {"crit": "ftc", "warn": "ftw", "ok": "fto", "info": "fti"}
# # #         tag_lbl = {"crit": "Critical", "warn": "Warning", "ok": "Healthy", "info": "Update"}
# # #         items_html = ""
# # #         for i, item in enumerate(feed_items[:9]):
# # #             line     = "" if i >= 8 else "<div class='fi-line'></div>"
# # #             sub_html = (f"<div class='fi-sub'>{item.get('sub','')}</div>") if item.get("sub") else ""
# # #             items_html += (
# # #                 f"<div class='fi'><div class='fi-dc'>"
# # #                 f"<div class='fi-dot' style='background:{item['dot']};'></div>{line}</div>"
# # #                 f"<div style='flex:1;min-width:0;'>"
# # #                 f"<div class='fi-msg'>{item['msg']}</div>"
# # #                 + sub_html +
# # #                 f"<div style='display:flex;align-items:center;gap:6px;margin-top:2px;'>"
# # #                 f"<div class='fi-time'>{item['time']}</div>"
# # #                 f"<span class='fi-tag {tag_map[item['type']]}'>{tag_lbl[item['type']]}</span>"
# # #                 f"</div></div></div>"
# # #             )
# # #         st.markdown(
# # #             "<div class='fc' style='height:340px;overflow-y:auto;'>"
# # #             "<div class='fh'><div class='fht'>Intelligence Feed</div>"
# # #             "<div class='flv'><div class='dot dot-g'></div>Live</div>"
# # #             "</div>" + items_html + "</div>",
# # #             unsafe_allow_html=True,
# # #         )

# # #     # ── Analytics ─────────────────────────────────────────────────────────────
# # #     st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)
# # #     sec("Supply Chain Analytics")
# # #     c1, c2 = st.columns(2, gap="medium")

# # #     with c1:
# # #         st.markdown(
# # #             "<div style='font-size:11px;font-weight:700;color:var(--t2);margin-bottom:5px;'>"
# # #             "Historical Stockout Events by Month &amp; Product</div>",
# # #             unsafe_allow_html=True,
# # #         )
# # #         all_breaches = []
# # #         for _, row in summary[summary.breach_count > 0].iterrows():
# # #             sh3 = get_stock_history(data, row["material"])
# # #             ss  = row["safety_stock"]
# # #             if ss <= 0:
# # #                 continue
# # #             b = sh3[sh3["Gross Stock"] < ss]
# # #             for _, br in b.iterrows():
# # #                 all_breaches.append({"label": fmt_p(br["Fiscal Period"]), "period": br["Fiscal Period"], "material": row["name"][:16]})

# # #         if all_breaches:
# # #             df_br = pd.DataFrame(all_breaches)
# # #             pivot = df_br.groupby(["period", "label", "material"]).size().reset_index(name="count")
# # #             pivot = pivot.sort_values("period")
# # #             recent_periods = pivot["period"].unique()[-14:]
# # #             pivot = pivot[pivot["period"].isin(recent_periods)]
# # #             colors = ["#EF4444", "#F59E0B", "#8B5CF6", "#EC4899", "#06B6D4"]
# # #             fig1   = go.Figure()
# # #             for i, mat in enumerate(pivot["material"].unique()):
# # #                 md     = pivot[pivot.material == mat]
# # #                 periods_all = pivot["label"].unique().tolist()
# # #                 counts = [md[md.label == p]["count"].sum() if p in md["label"].values else 0 for p in periods_all]
# # #                 fig1.add_trace(go.Bar(
# # #                     name=mat, x=periods_all, y=counts,
# # #                     marker_color=colors[i % len(colors)], marker_line_width=0,
# # #                     hovertemplate="<b>%{x}</b><br>" + mat + ": %{y} breach(es)<extra></extra>",
# # #                 ))
# # #             ct(fig1, 210)
# # #             fig1.update_layout(barmode="stack", showlegend=True,
# # #                                legend=dict(font_size=9, orientation="h", y=1.12),
# # #                                xaxis_tickangle=-40, yaxis=dict(dtick=1, title="Breaches"))
# # #             st.plotly_chart(fig1, use_container_width=True)
# # #         else:
# # #             st.markdown(
# # #                 "<div style='height:210px;display:flex;align-items:center;justify-content:center;"
# # #                 "color:var(--t3);font-size:12px;border:1px solid var(--bl);border-radius:var(--r);'>"
# # #                 "No breach events recorded</div>",
# # #                 unsafe_allow_html=True,
# # #             )

# # #     with c2:
# # #         st.markdown(
# # #             "<div style='font-size:11px;font-weight:700;color:var(--t2);margin-bottom:5px;'>Days of Cover per SKU</div>",
# # #             unsafe_allow_html=True,
# # #         )
# # #         act2  = summary[summary.risk.isin(["CRITICAL", "WARNING", "HEALTHY"])].sort_values("days_cover")
# # #         clrs2 = ["#EF4444" if r == "CRITICAL" else "#F59E0B" if r == "WARNING" else "#22C55E" for r in act2["risk"]]
# # #         cap   = [min(float(v), 300) for v in act2["days_cover"]]
# # #         fig2  = go.Figure()
# # #         fig2.add_trace(go.Bar(
# # #             y=act2["name"].str[:22].tolist(), x=cap, orientation="h",
# # #             marker_color=clrs2, marker_opacity=0.85, marker_line_width=0,
# # #             text=[(str(round(v)) + "d") for v in cap],
# # #             textposition="outside", textfont=dict(size=9, color="#475569"),
# # #             hovertemplate="<b>%{y}</b><br>Days cover: %{x:.0f}d<extra></extra>",
# # #         ))
# # #         fig2.add_vline(x=30, line_color="#EF4444", line_dash="dot", line_width=1.5,
# # #                        annotation_text="30d min", annotation_font_color="#EF4444", annotation_font_size=9)
# # #         ct(fig2, 210)
# # #         fig2.update_layout(showlegend=False, xaxis_title="Days", margin=dict(l=8, r=48, t=28, b=8))
# # #         st.plotly_chart(fig2, use_container_width=True)

# # #     # ── ARIA LLM Insight (FIX #1: Skip INSUFFICIENT_DATA materials) ────────────
# # #     if st.session_state.azure_client:
# # #         ai2, rb2 = st.columns([10, 1])
# # #         with rb2:
# # #             if st.button("↺", key="ref_cc", help="Refresh ARIA overview"):
# # #                 st.session_state.cc_insight = None
# # #         if st.session_state.cc_insight is None:
# # #             # ========== FIX: Exclude insufficient data materials ==========
# # #             valid_materials = summary[summary.risk != "INSUFFICIENT_DATA"]
# # #             if len(valid_materials) > 0:
# # #                 most_critical = valid_materials.sort_values('days_cover').iloc[0]
# # #                 ctx_str = (
# # #                     f"Plant FI11 Turku: {total} materials. Critical: {crit_n}"
# # #                     + (f" ({', '.join(valid_materials[valid_materials.risk == 'CRITICAL']['name'].tolist())})" if crit_n > 0 else "")
# # #                     + f". Insufficient data: {insuf_n}. Healthy: {ok_n}. "
# # #                     + f"Most critical: {most_critical['name']} "
# # #                     + f"with {most_critical['days_cover']:.1f}d cover, "
# # #                     + f"stock={most_critical['sih']:.0f} vs SS={most_critical['safety_stock']:.0f}."
# # #                 )
# # #             else:
# # #                 ctx_str = f"Plant FI11 Turku: {total} materials. Critical: 0. All materials have insufficient data."
# # #             # ================================================================
# # #             try:
# # #                 insight = chat_with_data(
# # #                     st.session_state.azure_client, AZURE_DEPLOYMENT,
# # #                     "Give a 2-sentence executive briefing on the current supply chain health. "
# # #                     "Identify the single biggest risk and one specific action.",
# # #                     ctx_str,
# # #                 )
# # #                 st.session_state.cc_insight = insight
# # #             except Exception:
# # #                 st.session_state.cc_insight = None
# # #         if st.session_state.cc_insight:
# # #             st.markdown(
# # #                 "<div class='ic' style='margin:10px 0;'>"
# # #                 "<div class='il'>◈ ARIA PLANT INTELLIGENCE</div>"
# # #                 f"<div class='ib' style='margin-top:4px;'>{st.session_state.cc_insight}</div>"
# # #                 "</div>",
# # #                 unsafe_allow_html=True,
# # #             )

# # #     # ── Product Deep-Dive ─────────────────────────────────────────────────────
# # #     sec("Product Deep-Dive")
# # #     note("Days cover = SIH (Stock-in-Hand from Current Inventory) ÷ avg daily demand (from Sales file). Safety Stock from Material Master.")

# # #     pd_col1, pd_col2 = st.columns([2, 1])
# # #     with pd_col1:
# # #         prod_opts = [r["name"] for _, r in summary[summary.risk != "INSUFFICIENT_DATA"].iterrows()]
# # #         sel_prod  = st.selectbox("Select product", prod_opts, key="cc_prod")
# # #     with pd_col2:
# # #         month_range = st.slider("Show last N months", 6, 60, 24, step=6, key="cc_months")

# # #     sel_mat_id  = summary[summary.name == sel_prod]["material"].values[0]
# # #     dh_cc       = get_demand_history(data, sel_mat_id)
# # #     sh_cc       = get_stock_history(data, sel_mat_id)
# # #     mat_row_cc  = summary[summary.material == sel_mat_id].iloc[0]
# # #     ss_cc       = mat_row_cc["safety_stock"]
# # #     repl_cc     = int(mat_row_cc["repl_quantity"])
# # #     lt_cc       = float(mat_row_cc["lead_time"])
# # #     lot_cc      = float(mat_row_cc["lot_size"])
# # #     sih_cc      = float(mat_row_cc["sih"])

# # #     sh_cc   = sh_cc.tail(month_range)
# # #     dh_cc_f = dh_cc.tail(month_range)

# # #     if len(sh_cc) > 0:
# # #         fig_dd  = go.Figure()
# # #         avg_d   = float(dh_cc_f[dh_cc_f.demand > 0]["demand"].mean()) if len(dh_cc_f[dh_cc_f.demand > 0]) > 0 else 0
# # #         fig_dd.add_trace(go.Scatter(
# # #             x=sh_cc["label"], y=sh_cc["Gross Stock"], mode="lines+markers", name="Stock (units)",
# # #             line=dict(color=ORANGE, width=2.5), marker=dict(size=4, color=ORANGE),
# # #             fill="tozeroy", fillcolor="rgba(244,123,37,0.08)", yaxis="y1",
# # #             hovertemplate="<b>%{x}</b><br>Stock: %{y} units<extra></extra>",
# # #         ))
# # #         dem_aligned = dh_cc_f[dh_cc_f.label.isin(sh_cc["label"].tolist())]
# # #         if len(dem_aligned) > 0:
# # #             fig_dd.add_trace(go.Bar(
# # #                 x=dem_aligned["label"], y=dem_aligned["demand"], name="Demand/mo",
# # #                 marker_color="rgba(148,163,184,0.3)", marker_line_width=0, yaxis="y2",
# # #                 hovertemplate="<b>%{x}</b><br>Demand: %{y} units<extra></extra>",
# # #             ))
# # #         if ss_cc > 0:
# # #             fig_dd.add_hline(y=ss_cc, line_color="#EF4444", line_dash="dot", line_width=1.5,
# # #                              annotation_text="SAP SS " + str(round(ss_cc)) + "u",
# # #                              annotation_font_color="#EF4444", annotation_font_size=9)
# # #         ct(fig_dd, 240)
# # #         fig_dd.update_layout(
# # #             title=dict(text=sel_prod + " — Stock vs Demand (last " + str(month_range) + "mo)",
# # #                        font=dict(size=11, color="#475569"), x=0),
# # #             xaxis=dict(tickangle=-35),
# # #             yaxis=dict(title="Stock (units)", gridcolor="#F0F4F9"),
# # #             yaxis2=dict(title="Demand/mo", overlaying="y", side="right", showgrid=False),
# # #             legend=dict(orientation="h", y=1.1),
# # #             margin=dict(l=8, r=50, t=44, b=8),
# # #         )
# # #         st.plotly_chart(fig_dd, use_container_width=True)

# # #     if repl_cc > 0:
# # #         st.markdown(
# # #             "<div class='prow' style='border-left:3px solid #EF4444;background:#FEF2F2;'>"
# # #             "<div style='font-size:16px;'>⛔</div>"
# # #             "<div style='flex:1;'>"
# # #             "<div style='font-size:12px;font-weight:800;color:#EF4444;'>Replenishment Required</div>"
# # #             "<div style='font-size:11px;color:#475569;margin-top:2px;'>"
# # #             f"Stock-in-Hand: <strong>{round(sih_cc)}</strong> · SAP SS: <strong>{round(ss_cc)}</strong> · "
# # #             f"Lead time: <strong>{round(lt_cc)}d</strong> (Material Master) · "
# # #             f"Lot size: <strong>{round(lot_cc)}</strong>"
# # #             "</div></div>"
# # #             "<div style='text-align:right;'>"
# # #             f"<div style='font-size:22px;font-weight:900;color:#EF4444;'>{repl_cc} units</div>"
# # #             f"<div style='font-size:9px;color:#EF4444;'>CEILING({round(ss_cc-sih_cc)}/{round(lot_cc)})×{round(lot_cc)}</div>"
# # #             "</div></div>",
# # #             unsafe_allow_html=True,
# # #         )

# # #     st.markdown('<div class="pfooter">⚡ Powered by <strong>MResult</strong></div>', unsafe_allow_html=True)



# # """
# # tabs/command_center.py
# # Command Center tab: KPI cards, Material Health Board, Intelligence Feed,
# # analytics charts, and product deep-dive.
# # """

# # import streamlit as st
# # import pandas as pd
# # import plotly.graph_objects as go
# # from st_aggrid import AgGrid, GridOptionsBuilder, JsCode, GridUpdateMode

# # from utils.helpers import ct, fmt_p, sbadge, sec, note, ORANGE, AZURE_DEPLOYMENT
# # from data_loader import get_stock_history, get_demand_history
# # from agent import chat_with_data


# # # ── KPI card renderer ─────────────────────────────────────────────────────────
# # _SVG = {
# #     "tot":  '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="8" r="4"/><path d="M4 20c0-4 3.6-7 8-7s8 3 8 7"/></svg>',
# #     "crit": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>',
# #     "insuf":'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>',
# #     "ok":   '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>',
# # }


# # def _kpi(col, svg, si, val, vc, lbl, dlt=None, dc="sdu"):
# #     dh = (f'<span class="sdt {dc}">{dlt}</span>') if dlt else ""
# #     with col:
# #         st.markdown(
# #             f"<div class='sc'><div class='si {si}'>{svg}</div>"
# #             f"<div style='flex:1;'><div class='sv' style='color:{vc};'>{val}</div>"
# #             f"<div class='sl'>{lbl}</div></div>{dh}</div>",
# #             unsafe_allow_html=True,
# #         )


# # # ── AgGrid JS renderers ────────────────────────────────────────────────────────
# # _STATUS_R = JsCode("""class R{init(p){const m={'CRITICAL':['#FEE2E2','#EF4444','⛔ Critical'],'WARNING':['#FEF3C7','#F59E0B','⚠ Warning'],'HEALTHY':['#DCFCE7','#22C55E','✓ Healthy'],'INSUFFICIENT_DATA':['#F1F5F9','#94A3B8','◌ No Data']};const[bg,c,l]=m[p.value]||m.INSUFFICIENT_DATA;this.e=document.createElement('span');this.e.style.cssText=`background:${bg};color:${c};border:1px solid ${c}44;padding:2px 7px;border-radius:20px;font-size:9px;font-weight:700;white-space:nowrap;`;this.e.innerText=l;}getGui(){return this.e;}}""")
# # _SPARK_R   = JsCode("""class R{init(p){const raw=(p.value||'').split(',').map(Number).filter(n=>!isNaN(n));const w=72,h=22,pad=3;this.e=document.createElement('div');if(!raw.length){this.e.innerText='—';return;}const mn=Math.min(...raw),mx=Math.max(...raw),rng=mx-mn||1;const pts=raw.map((v,i)=>{const x=pad+i*(w-2*pad)/(raw.length-1||1);const y=h-pad-(v-mn)/rng*(h-2*pad);return x+','+y;}).join(' ');const l=raw[raw.length-1],f=raw[0];const t=l>f?'#22C55E':l<f?'#EF4444':'#F47B25';this.e.innerHTML=`<svg width="${w}" height="${h}"><polyline points="${pts}" fill="none" stroke="${t}" stroke-width="1.8" stroke-linejoin="round" stroke-linecap="round"/><circle cx="${pts.split(' ').pop().split(',')[0]}" cy="${pts.split(' ').pop().split(',')[1]}" r="2" fill="${t}"/></svg>`;}getGui(){return this.e;}}""")
# # _COVER_R   = JsCode("""class R{init(p){const v=p.value||0;const pct=Math.min(v/180*100,100);const c=v<15?'#EF4444':v<30?'#F59E0B':'#22C55E';this.e=document.createElement('div');this.e.style.cssText='display:flex;align-items:center;gap:4px;width:100%;';this.e.innerHTML=`<div style="flex:1;height:5px;background:#F0F4F9;border-radius:3px;overflow:hidden;"><div style="width:${pct}%;height:100%;background:${c};border-radius:3px;"></div></div><span style="font-size:10px;font-weight:700;color:${c};min-width:28px;">${v}d</span>`;}getGui(){return this.e;}}""")
# # _ORDER_R   = JsCode("""class R{init(p){const v=p.value||0;this.e=document.createElement('span');if(v>0){this.e.style.cssText='background:#FEE2E2;color:#EF4444;border:1px solid #EF444440;padding:2px 7px;border-radius:5px;font-size:10px;font-weight:700;';this.e.innerText=v+' units';}else{this.e.style.cssText='background:#F0F4F9;color:#94A3B8;padding:2px 7px;border-radius:5px;font-size:10px;';this.e.innerText='—';};}getGui(){return this.e;}}""")
# # _ROW_STYLE = JsCode("""function(p){if(p.data.Risk==='CRITICAL')return{'background':'rgba(239,68,68,0.03)','border-left':'3px solid #EF4444'};if(p.data.Risk==='WARNING')return{'background':'rgba(245,158,11,0.02)','border-left':'3px solid #F59E0B'};if(p.data.Risk==='INSUFFICIENT_DATA')return{'color':'#94A3B8'};return{};}""")

# # _AGGRID_CSS = {
# #     ".ag-root-wrapper": {"border": "1px solid #E2E8F0!important", "border-radius": "14px!important", "overflow": "auto !important"},
# #     ".ag-header":       {"background": "#F8FAFE!important"},
# #     ".ag-row-even":     {"background": "#FFFFFF!important"},
# #     ".ag-row-odd":      {"background": "#F8FAFE!important"},
# #     ".ag-cell":         {"border-right": "1px solid #F0F4F9!important", "white-space": "normal !important", "word-break": "break-word !important"},
# #     ".ag-cell-wrapper": {"white-space": "normal !important"},
# # }


# # def render():
# #     data    = st.session_state.data
# #     summary = st.session_state.summary

# #     # ── KPI Row ───────────────────────────────────────────────────────────────
# #     total   = len(summary)
# #     crit_n  = int((summary.risk == "CRITICAL").sum())
# #     insuf_n = int((summary.risk == "INSUFFICIENT_DATA").sum())
# #     ok_n    = int((summary.risk == "HEALTHY").sum())

# #     k1, k2, k3, k4 = st.columns(4)
# #     _kpi(k1, _SVG["tot"],   "sio", total,   "#1E293B", "Total Materials")
# #     _kpi(k2, _SVG["crit"],  "sir", crit_n,  "#EF4444", "Critical Alerts",
# #          "⛔ Action required" if crit_n > 0 else "✓ None",
# #          "sdc" if crit_n > 0 else "sdu")
# #     _kpi(k3, _SVG["insuf"], "six", insuf_n, "#94A3B8", "Insufficient Data",
# #          str(insuf_n) + " SKUs", "sdw" if insuf_n > 0 else "sdu")
# #     _kpi(k4, _SVG["ok"],    "sig", ok_n,    "#22C55E", "Healthy", "↑ Operating", "sdu")

# #     # ── Main Row: Health Board + Intelligence Feed ────────────────────────────
# #     st.markdown("<div style='height:14px;'></div>", unsafe_allow_html=True)
# #     board_col, feed_col = st.columns([3, 2], gap="medium")

# #     with board_col:
# #         st.markdown(
# #             "<div style='font-size:13px;font-weight:800;color:var(--t);margin-bottom:8px;'>"
# #             "Material Health Board"
# #             "<span style='font-size:11px;font-weight:400;color:var(--t3);margin-left:8px;'>Sortable · Horizontal scroll</span>"
# #             "</div>",
# #             unsafe_allow_html=True,
# #         )
# #         grid_rows = []
# #         for _, row in summary.iterrows():
# #             sh2 = get_stock_history(data, row["material"])
# #             dh2 = get_demand_history(data, row["material"])
# #             nz  = dh2[dh2.demand > 0]
# #             avg = float(nz.demand.mean()) if len(nz) > 0 else 0
# #             ss  = row["safety_stock"]
# #             br  = sh2[sh2["Gross Stock"] < max(ss, 1)] if ss > 0 else pd.DataFrame()
# #             lb  = fmt_p(br["Fiscal Period"].iloc[-1]) if len(br) > 0 else "—"
# #             spark = sh2["Gross Stock"].tail(8).tolist()
# #             dc  = row["days_cover"]
# #             grid_rows.append({
# #                 "Risk": row["risk"], "Material": row["name"],
# #                 "Stock": int(row["sih"]), "SAP SS": int(ss), "ARIA SS": int(row["rec_safety_stock"]),
# #                 "Days Cover": int(dc) if dc < 999 else 0,
# #                 "Demand/mo": round(avg, 0), "Trend": row["trend"],
# #                 "Breaches": int(row["breach_count"]), "Last Breach": lb,
# #                 "Order Now": int(row["repl_quantity"]),
# #                 "Spark": (",".join([str(round(v)) for v in spark])),
# #             })
# #         df_grid = pd.DataFrame(grid_rows)

# #         gb = GridOptionsBuilder.from_dataframe(df_grid)
# #         # Adjusted column widths for better readability
# #         gb.configure_column("Risk",       cellRenderer=_STATUS_R, width=120, minWidth=120, maxWidth=120, pinned="left")
# #         gb.configure_column("Material",   width=200, minWidth=200, maxWidth=200, pinned="left")
# #         gb.configure_column("Stock",      width=80,  minWidth=80,  maxWidth=80,  type=["numericColumn"])
# #         gb.configure_column("SAP SS",     width=80,  minWidth=80,  maxWidth=80,  type=["numericColumn"])
# #         gb.configure_column("ARIA SS",    width=85,  minWidth=85,  maxWidth=85,  type=["numericColumn"])
# #         gb.configure_column("Days Cover", width=130, minWidth=130, maxWidth=130, cellRenderer=_COVER_R)
# #         gb.configure_column("Demand/mo",  width=95,  minWidth=95,  maxWidth=95,  type=["numericColumn"])
# #         gb.configure_column("Trend",      width=85,  minWidth=85,  maxWidth=85)
# #         gb.configure_column("Breaches",   width=85,  minWidth=85,  maxWidth=85,  type=["numericColumn"])
# #         gb.configure_column("Last Breach",width=100, minWidth=100, maxWidth=100)
# #         gb.configure_column("Order Now",  width=100, minWidth=100, maxWidth=100, cellRenderer=_ORDER_R)
# #         gb.configure_column("Spark",      width=100, minWidth=100, maxWidth=100, cellRenderer=_SPARK_R, headerName="8m Trend")
# #         gb.configure_grid_options(rowHeight=42, headerHeight=34, getRowStyle=_ROW_STYLE,
# #                                    suppressMovableColumns=True, suppressColumnVirtualisation=False)
# #         gb.configure_selection("single", use_checkbox=False)
# #         gb.configure_default_column(resizable=True, sortable=True, filter=False, wrapText=True, autoHeight=True)

# #         AgGrid(df_grid, gridOptions=gb.build(), height=380, allow_unsafe_jscode=True,
# #                update_mode=GridUpdateMode.SELECTION_CHANGED, theme="alpine",
# #                custom_css=_AGGRID_CSS)

# #     with feed_col:
# #         st.markdown(
# #             "<div style='font-size:13px;font-weight:800;color:var(--t);margin-bottom:8px;'>Intelligence Feed</div>",
# #             unsafe_allow_html=True,
# #         )
# #         feed_items = []
# #         for _, row in summary[summary.risk == "CRITICAL"].iterrows():
# #             repl_q = int(row["repl_quantity"])
# #             feed_items.append({
# #                 "dot": "#EF4444", "type": "crit", "time": "Now",
# #                 "msg": "<span>⛔ " + row["name"] + "</span>",
# #                 "sub": str(round(row["sih"])) + " units stock · " + str(round(row["days_cover"])) + "d cover · SS=" + str(round(row["safety_stock"]))
# #                        + (" · ORDER " + str(repl_q) + " units NOW" if repl_q > 0 else ""),
# #             })
# #         for _, row in summary[summary.risk == "WARNING"].iterrows():
# #             feed_items.append({
# #                 "dot": ORANGE, "type": "warn", "time": "Live",
# #                 "msg": "<span>⚠ " + row["name"] + "</span>",
# #                 "sub": str(round(row["days_cover"])) + "d cover remaining · Approaching safety stock threshold",
# #             })
# #         ss_gap = summary[(summary.safety_stock < summary.rec_safety_stock) & (summary.risk != "INSUFFICIENT_DATA")]
# #         for _, row in ss_gap.sort_values("breach_count", ascending=False).head(2).iterrows():
# #             g = round(row["rec_safety_stock"] - row["safety_stock"])
# #             if g > 0:
# #                 feed_items.append({
# #                     "dot": "#F59E0B", "type": "warn", "time": "Audit",
# #                     "msg": "<span>SAP SS Under-configured</span> — " + row["name"][:20],
# #                     "sub": "SAP: " + str(round(row["safety_stock"])) + " units · ARIA recommends: "
# #                            + str(round(row["rec_safety_stock"])) + " · Gap: " + str(g) + " units",
# #                 })
# #         top_b = summary[(summary.breach_count > 0) & (summary.risk != "INSUFFICIENT_DATA")].sort_values("breach_count", ascending=False)
# #         if len(top_b) > 0:
# #             r = top_b.iloc[0]
# #             feed_items.append({
# #                 "dot": ORANGE, "type": "info", "time": "History",
# #                 "msg": "<span>" + r["name"] + "</span> — " + str(r["breach_count"]) + " stockout events",
# #                 "sub": "Worst performer over 25 months · " + str(round(r["breach_count"])) + " periods below safety stock",
# #             })
# #         lt_critical = summary[(summary.days_cover < summary.lead_time) & (summary.risk != "INSUFFICIENT_DATA")]
# #         for _, row in lt_critical.iterrows():
# #             feed_items.append({
# #                 "dot": "#EF4444", "type": "crit", "time": "Urgent",
# #                 "msg": "<span>Lead Time Exceeds Cover</span> — " + row["name"][:22],
# #                 "sub": "Cover=" + str(round(row["days_cover"])) + "d but Lead Time=" + str(round(row["lead_time"])) + "d · Order immediately",
# #             })
# #         feed_items.append({
# #             "dot": "#22C55E", "type": "ok", "time": "System",
# #             "msg": "<span>ARIA</span> — Safety stock models updated",
# #             "sub": "Formula: CEILING(Shortfall/FLS)×FLS · Source: Material Master",
# #         })

# #         tag_map = {"crit": "ftc", "warn": "ftw", "ok": "fto", "info": "fti"}
# #         tag_lbl = {"crit": "Critical", "warn": "Warning", "ok": "Healthy", "info": "Update"}
# #         items_html = ""
# #         for i, item in enumerate(feed_items[:9]):
# #             line     = "" if i >= 8 else "<div class='fi-line'></div>"
# #             sub_html = (f"<div class='fi-sub'>{item.get('sub','')}</div>") if item.get("sub") else ""
# #             items_html += (
# #                 f"<div class='fi'><div class='fi-dc'>"
# #                 f"<div class='fi-dot' style='background:{item['dot']};'></div>{line}</div>"
# #                 f"<div style='flex:1;min-width:0;'>"
# #                 f"<div class='fi-msg'>{item['msg']}</div>"
# #                 + sub_html +
# #                 f"<div style='display:flex;align-items:center;gap:6px;margin-top:2px;'>"
# #                 f"<div class='fi-time'>{item['time']}</div>"
# #                 f"<span class='fi-tag {tag_map[item['type']]}'>{tag_lbl[item['type']]}</span>"
# #                 f"</div></div></div>"
# #             )
# #         st.markdown(
# #             "<div class='fc' style='height:380px;overflow-y:auto;'>"
# #             "<div class='fh'><div class='fht'>Intelligence Feed</div>"
# #             "<div class='flv'><div class='dot dot-g'></div>Live</div>"
# #             "</div>" + items_html + "</div>",
# #             unsafe_allow_html=True,
# #         )

# #     # ── Analytics ─────────────────────────────────────────────────────────────
# #     st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)
# #     sec("Supply Chain Analytics")
# #     c1, c2 = st.columns(2, gap="medium")

# #     with c1:
# #         st.markdown(
# #             "<div style='font-size:11px;font-weight:700;color:var(--t2);margin-bottom:5px;'>"
# #             "Historical Stockout Events by Month &amp; Product</div>",
# #             unsafe_allow_html=True,
# #         )
# #         all_breaches = []
# #         for _, row in summary[summary.breach_count > 0].iterrows():
# #             sh3 = get_stock_history(data, row["material"])
# #             ss  = row["safety_stock"]
# #             if ss <= 0:
# #                 continue
# #             b = sh3[sh3["Gross Stock"] < ss]
# #             for _, br in b.iterrows():
# #                 all_breaches.append({"label": fmt_p(br["Fiscal Period"]), "period": br["Fiscal Period"], "material": row["name"][:16]})

# #         if all_breaches:
# #             df_br = pd.DataFrame(all_breaches)
# #             pivot = df_br.groupby(["period", "label", "material"]).size().reset_index(name="count")
# #             pivot = pivot.sort_values("period")
# #             recent_periods = pivot["period"].unique()[-14:]
# #             pivot = pivot[pivot["period"].isin(recent_periods)]
# #             colors = ["#EF4444", "#F59E0B", "#8B5CF6", "#EC4899", "#06B6D4"]
# #             fig1   = go.Figure()
# #             for i, mat in enumerate(pivot["material"].unique()):
# #                 md     = pivot[pivot.material == mat]
# #                 periods_all = pivot["label"].unique().tolist()
# #                 counts = [md[md.label == p]["count"].sum() if p in md["label"].values else 0 for p in periods_all]
# #                 fig1.add_trace(go.Bar(
# #                     name=mat, x=periods_all, y=counts,
# #                     marker_color=colors[i % len(colors)], marker_line_width=0,
# #                     hovertemplate="<b>%{x}</b><br>" + mat + ": %{y} breach(es)<extra></extra>",
# #                 ))
# #             ct(fig1, 210)
# #             fig1.update_layout(barmode="stack", showlegend=True,
# #                                legend=dict(font_size=9, orientation="h", y=1.12),
# #                                xaxis_tickangle=-40, yaxis=dict(dtick=1, title="Breaches"))
# #             st.plotly_chart(fig1, use_container_width=True)
# #         else:
# #             st.markdown(
# #                 "<div style='height:210px;display:flex;align-items:center;justify-content:center;"
# #                 "color:var(--t3);font-size:12px;border:1px solid var(--bl);border-radius:var(--r);'>"
# #                 "No breach events recorded</div>",
# #                 unsafe_allow_html=True,
# #             )

# #     with c2:
# #         st.markdown(
# #             "<div style='font-size:11px;font-weight:700;color:var(--t2);margin-bottom:5px;'>Days of Cover per SKU</div>",
# #             unsafe_allow_html=True,
# #         )
# #         act2  = summary[summary.risk.isin(["CRITICAL", "WARNING", "HEALTHY"])].sort_values("days_cover")
# #         clrs2 = ["#EF4444" if r == "CRITICAL" else "#F59E0B" if r == "WARNING" else "#22C55E" for r in act2["risk"]]
# #         cap   = [min(float(v), 300) for v in act2["days_cover"]]
# #         fig2  = go.Figure()
# #         fig2.add_trace(go.Bar(
# #             y=act2["name"].str[:22].tolist(), x=cap, orientation="h",
# #             marker_color=clrs2, marker_opacity=0.85, marker_line_width=0,
# #             text=[(str(round(v)) + "d") for v in cap],
# #             textposition="outside", textfont=dict(size=9, color="#475569"),
# #             hovertemplate="<b>%{y}</b><br>Days cover: %{x:.0f}d<extra></extra>",
# #         ))
# #         fig2.add_vline(x=30, line_color="#EF4444", line_dash="dot", line_width=1.5,
# #                        annotation_text="30d min", annotation_font_color="#EF4444", annotation_font_size=9)
# #         ct(fig2, 210)
# #         fig2.update_layout(showlegend=False, xaxis_title="Days", margin=dict(l=8, r=48, t=28, b=8))
# #         st.plotly_chart(fig2, use_container_width=True)

# #     # ── ARIA LLM Insight (skip INSUFFICIENT_DATA) ────────────────────────────
# #     if st.session_state.azure_client:
# #         ai2, rb2 = st.columns([10, 1])
# #         with rb2:
# #             if st.button("↺", key="ref_cc", help="Refresh ARIA overview"):
# #                 st.session_state.cc_insight = None
# #         if st.session_state.cc_insight is None:
# #             valid_materials = summary[summary.risk != "INSUFFICIENT_DATA"]
# #             if len(valid_materials) > 0:
# #                 most_critical = valid_materials.sort_values('days_cover').iloc[0]
# #                 ctx_str = (
# #                     f"Plant FI11 Turku: {total} materials. Critical: {crit_n}"
# #                     + (f" ({', '.join(valid_materials[valid_materials.risk == 'CRITICAL']['name'].tolist())})" if crit_n > 0 else "")
# #                     + f". Insufficient data: {insuf_n}. Healthy: {ok_n}. "
# #                     + f"Most critical: {most_critical['name']} "
# #                     + f"with {most_critical['days_cover']:.1f}d cover, "
# #                     + f"stock={most_critical['sih']:.0f} vs SS={most_critical['safety_stock']:.0f}."
# #                 )
# #             else:
# #                 ctx_str = f"Plant FI11 Turku: {total} materials. Critical: 0. All materials have insufficient data."
# #             try:
# #                 insight = chat_with_data(
# #                     st.session_state.azure_client, AZURE_DEPLOYMENT,
# #                     "Give a 2-sentence executive briefing on the current supply chain health. "
# #                     "Identify the single biggest risk and one specific action.",
# #                     ctx_str,
# #                 )
# #                 st.session_state.cc_insight = insight
# #             except Exception:
# #                 st.session_state.cc_insight = None
# #         if st.session_state.cc_insight:
# #             st.markdown(
# #                 "<div class='ic' style='margin:10px 0;'>"
# #                 "<div class='il'>◈ ARIA PLANT INTELLIGENCE</div>"
# #                 f"<div class='ib' style='margin-top:4px;'>{st.session_state.cc_insight}</div>"
# #                 "</div>",
# #                 unsafe_allow_html=True,
# #             )

# #     # ── Product Deep-Dive ─────────────────────────────────────────────────────
# #     sec("Product Deep-Dive")
# #     note("Days cover = SIH (Stock-in-Hand from Current Inventory) ÷ avg daily demand (from Sales file). Safety Stock from Material Master.")

# #     pd_col1, pd_col2 = st.columns([2, 1])
# #     with pd_col1:
# #         prod_opts = [r["name"] for _, r in summary[summary.risk != "INSUFFICIENT_DATA"].iterrows()]
# #         sel_prod  = st.selectbox("Select product", prod_opts, key="cc_prod")
# #     with pd_col2:
# #         month_range = st.slider("Show last N months", 6, 60, 24, step=6, key="cc_months")

# #     sel_mat_id  = summary[summary.name == sel_prod]["material"].values[0]
# #     dh_cc       = get_demand_history(data, sel_mat_id)
# #     sh_cc       = get_stock_history(data, sel_mat_id)
# #     mat_row_cc  = summary[summary.material == sel_mat_id].iloc[0]
# #     ss_cc       = mat_row_cc["safety_stock"]
# #     repl_cc     = int(mat_row_cc["repl_quantity"])
# #     lt_cc       = float(mat_row_cc["lead_time"])
# #     lot_cc      = float(mat_row_cc["lot_size"])
# #     sih_cc      = float(mat_row_cc["sih"])

# #     sh_cc   = sh_cc.tail(month_range)
# #     dh_cc_f = dh_cc.tail(month_range)

# #     if len(sh_cc) > 0:
# #         fig_dd  = go.Figure()
# #         avg_d   = float(dh_cc_f[dh_cc_f.demand > 0]["demand"].mean()) if len(dh_cc_f[dh_cc_f.demand > 0]) > 0 else 0
# #         fig_dd.add_trace(go.Scatter(
# #             x=sh_cc["label"], y=sh_cc["Gross Stock"], mode="lines+markers", name="Stock (units)",
# #             line=dict(color=ORANGE, width=2.5), marker=dict(size=4, color=ORANGE),
# #             fill="tozeroy", fillcolor="rgba(244,123,37,0.08)", yaxis="y1",
# #             hovertemplate="<b>%{x}</b><br>Stock: %{y} units<extra></extra>",
# #         ))
# #         dem_aligned = dh_cc_f[dh_cc_f.label.isin(sh_cc["label"].tolist())]
# #         if len(dem_aligned) > 0:
# #             fig_dd.add_trace(go.Bar(
# #                 x=dem_aligned["label"], y=dem_aligned["demand"], name="Demand/mo",
# #                 marker_color="rgba(148,163,184,0.3)", marker_line_width=0, yaxis="y2",
# #                 hovertemplate="<b>%{x}</b><br>Demand: %{y} units<extra></extra>",
# #             ))
# #         if ss_cc > 0:
# #             fig_dd.add_hline(y=ss_cc, line_color="#EF4444", line_dash="dot", line_width=1.5,
# #                              annotation_text="SAP SS " + str(round(ss_cc)) + "u",
# #                              annotation_font_color="#EF4444", annotation_font_size=9)
# #         ct(fig_dd, 240)
# #         fig_dd.update_layout(
# #             title=dict(text=sel_prod + " — Stock vs Demand (last " + str(month_range) + "mo)",
# #                        font=dict(size=11, color="#475569"), x=0),
# #             xaxis=dict(tickangle=-35),
# #             yaxis=dict(title="Stock (units)", gridcolor="#F0F4F9"),
# #             yaxis2=dict(title="Demand/mo", overlaying="y", side="right", showgrid=False),
# #             legend=dict(orientation="h", y=1.1),
# #             margin=dict(l=8, r=50, t=44, b=8),
# #         )
# #         st.plotly_chart(fig_dd, use_container_width=True)

# #     if repl_cc > 0:
# #         st.markdown(
# #             "<div class='prow' style='border-left:3px solid #EF4444;background:#FEF2F2;'>"
# #             "<div style='font-size:16px;'>⛔</div>"
# #             "<div style='flex:1;'>"
# #             "<div style='font-size:12px;font-weight:800;color:#EF4444;'>Replenishment Required</div>"
# #             "<div style='font-size:11px;color:#475569;margin-top:2px;'>"
# #             f"Stock-in-Hand: <strong>{round(sih_cc)}</strong> · SAP SS: <strong>{round(ss_cc)}</strong> · "
# #             f"Lead time: <strong>{round(lt_cc)}d</strong> (Material Master) · "
# #             f"Lot size: <strong>{round(lot_cc)}</strong>"
# #             "</div></div>"
# #             "<div style='text-align:right;'>"
# #             f"<div style='font-size:22px;font-weight:900;color:#EF4444;'>{repl_cc} units</div>"
# #             f"<div style='font-size:9px;color:#EF4444;'>CEILING({round(ss_cc-sih_cc)}/{round(lot_cc)})×{round(lot_cc)}</div>"
# #             "</div></div>",
# #             unsafe_allow_html=True,
# #         )

# #     st.markdown('<div class="pfooter">⚡ Powered by <strong>MResult</strong></div>', unsafe_allow_html=True)

# """
# tabs/command_center.py
# Command Center tab: KPI cards, Material Health Board, Intelligence Feed (with timestamps),
# analytics charts, and product deep-dive.
# """

# import streamlit as st
# import pandas as pd
# import plotly.graph_objects as go
# from st_aggrid import AgGrid, GridOptionsBuilder, JsCode, GridUpdateMode

# from utils.helpers import ct, fmt_p, sbadge, sec, note, ORANGE, AZURE_DEPLOYMENT
# from data_loader import get_stock_history, get_demand_history
# from agent import chat_with_data


# # ── KPI card renderer ─────────────────────────────────────────────────────────
# _SVG = {
#     "tot":  '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="8" r="4"/><path d="M4 20c0-4 3.6-7 8-7s8 3 8 7"/></svg>',
#     "crit": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>',
#     "insuf":'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>',
#     "ok":   '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>',
# }


# def _kpi(col, svg, si, val, vc, lbl, dlt=None, dc="sdu"):
#     dh = (f'<span class="sdt {dc}">{dlt}</span>') if dlt else ""
#     with col:
#         st.markdown(
#             f"<div class='sc'><div class='si {si}'>{svg}</div>"
#             f"<div style='flex:1;'><div class='sv' style='color:{vc};'>{val}</div>"
#             f"<div class='sl'>{lbl}</div></div>{dh}</div>",
#             unsafe_allow_html=True,
#         )


# # ── AgGrid JS renderers ────────────────────────────────────────────────────────
# _STATUS_R = JsCode("""class R{init(p){const m={'CRITICAL':['#FEE2E2','#EF4444','⛔ Critical'],'WARNING':['#FEF3C7','#F59E0B','⚠ Warning'],'HEALTHY':['#DCFCE7','#22C55E','✓ Healthy'],'INSUFFICIENT_DATA':['#F1F5F9','#94A3B8','◌ No Data']};const[bg,c,l]=m[p.value]||m.INSUFFICIENT_DATA;this.e=document.createElement('span');this.e.style.cssText=`background:${bg};color:${c};border:1px solid ${c}44;padding:2px 7px;border-radius:20px;font-size:9px;font-weight:700;white-space:nowrap;`;this.e.innerText=l;}getGui(){return this.e;}}""")
# _SPARK_R   = JsCode("""class R{init(p){const raw=(p.value||'').split(',').map(Number).filter(n=>!isNaN(n));const w=72,h=22,pad=3;this.e=document.createElement('div');if(!raw.length){this.e.innerText='—';return;}const mn=Math.min(...raw),mx=Math.max(...raw),rng=mx-mn||1;const pts=raw.map((v,i)=>{const x=pad+i*(w-2*pad)/(raw.length-1||1);const y=h-pad-(v-mn)/rng*(h-2*pad);return x+','+y;}).join(' ');const l=raw[raw.length-1],f=raw[0];const t=l>f?'#22C55E':l<f?'#EF4444':'#F47B25';this.e.innerHTML=`<svg width="${w}" height="${h}"><polyline points="${pts}" fill="none" stroke="${t}" stroke-width="1.8" stroke-linejoin="round" stroke-linecap="round"/><circle cx="${pts.split(' ').pop().split(',')[0]}" cy="${pts.split(' ').pop().split(',')[1]}" r="2" fill="${t}"/></svg>`;}getGui(){return this.e;}}""")
# _COVER_R   = JsCode("""class R{init(p){const v=p.value||0;const pct=Math.min(v/180*100,100);const c=v<15?'#EF4444':v<30?'#F59E0B':'#22C55E';this.e=document.createElement('div');this.e.style.cssText='display:flex;align-items:center;gap:4px;width:100%;';this.e.innerHTML=`<div style="flex:1;height:5px;background:#F0F4F9;border-radius:3px;overflow:hidden;"><div style="width:${pct}%;height:100%;background:${c};border-radius:3px;"></div></div><span style="font-size:10px;font-weight:700;color:${c};min-width:28px;">${v}d</span>`;}getGui(){return this.e;}}""")
# _ORDER_R   = JsCode("""class R{init(p){const v=p.value||0;this.e=document.createElement('span');if(v>0){this.e.style.cssText='background:#FEE2E2;color:#EF4444;border:1px solid #EF444440;padding:2px 7px;border-radius:5px;font-size:10px;font-weight:700;';this.e.innerText=v+' units';}else{this.e.style.cssText='background:#F0F4F9;color:#94A3B8;padding:2px 7px;border-radius:5px;font-size:10px;';this.e.innerText='—';};}getGui(){return this.e;}}""")
# _ROW_STYLE = JsCode("""function(p){if(p.data.Risk==='CRITICAL')return{'background':'rgba(239,68,68,0.03)','border-left':'3px solid #EF4444'};if(p.data.Risk==='WARNING')return{'background':'rgba(245,158,11,0.02)','border-left':'3px solid #F59E0B'};if(p.data.Risk==='INSUFFICIENT_DATA')return{'color':'#94A3B8'};return{};}""")

# _AGGRID_CSS = {
#     ".ag-root-wrapper": {"border": "1px solid #E2E8F0!important", "border-radius": "14px!important", "overflow": "auto !important"},
#     ".ag-header":       {"background": "#F8FAFE!important"},
#     ".ag-row-even":     {"background": "#FFFFFF!important"},
#     ".ag-row-odd":      {"background": "#F8FAFE!important"},
#     ".ag-cell":         {"border-right": "1px solid #F0F4F9!important", "white-space": "normal !important", "word-break": "break-word !important"},
#     ".ag-cell-wrapper": {"white-space": "normal !important"},
# }


# def render():
#     data    = st.session_state.data
#     summary = st.session_state.summary

#     # ── KPI Row ───────────────────────────────────────────────────────────────
#     total   = len(summary)
#     crit_n  = int((summary.risk == "CRITICAL").sum())
#     insuf_n = int((summary.risk == "INSUFFICIENT_DATA").sum())
#     ok_n    = int((summary.risk == "HEALTHY").sum())

#     k1, k2, k3, k4 = st.columns(4)
#     _kpi(k1, _SVG["tot"],   "sio", total,   "#1E293B", "Total Materials")
#     _kpi(k2, _SVG["crit"],  "sir", crit_n,  "#EF4444", "Critical Alerts",
#          "⛔ Action required" if crit_n > 0 else "✓ None",
#          "sdc" if crit_n > 0 else "sdu")
#     _kpi(k3, _SVG["insuf"], "six", insuf_n, "#94A3B8", "Insufficient Data",
#          str(insuf_n) + " SKUs", "sdw" if insuf_n > 0 else "sdu")
#     _kpi(k4, _SVG["ok"],    "sig", ok_n,    "#22C55E", "Healthy", "↑ Operating", "sdu")

#     # ── Main Row: Health Board + Intelligence Feed ────────────────────────────
#     st.markdown("<div style='height:14px;'></div>", unsafe_allow_html=True)
#     board_col, feed_col = st.columns([3, 2], gap="medium")

#     with board_col:
#         st.markdown(
#             "<div style='font-size:13px;font-weight:800;color:var(--t);margin-bottom:8px;'>"
#             "Material Health Board"
#             "<span style='font-size:11px;font-weight:400;color:var(--t3);margin-left:8px;'>Sortable · Horizontal scroll</span>"
#             "</div>",
#             unsafe_allow_html=True,
#         )
#         grid_rows = []
#         for _, row in summary.iterrows():
#             sh2 = get_stock_history(data, row["material"])
#             dh2 = get_demand_history(data, row["material"])
#             nz  = dh2[dh2.demand > 0]
#             avg = float(nz.demand.mean()) if len(nz) > 0 else 0
#             ss  = row["safety_stock"]
#             br  = sh2[sh2["Gross Stock"] < max(ss, 1)] if ss > 0 else pd.DataFrame()
#             lb  = fmt_p(br["Fiscal Period"].iloc[-1]) if len(br) > 0 else "—"
#             spark = sh2["Gross Stock"].tail(8).tolist()
#             dc  = row["days_cover"]
#             grid_rows.append({
#                 "Risk": row["risk"], "Material": row["name"],
#                 "Stock": int(row["sih"]), "SAP SS": int(ss), "ARIA SS": int(row["rec_safety_stock"]),
#                 "Days Cover": int(dc) if dc < 999 else 0,
#                 "Demand/mo": round(avg, 0), "Trend": row["trend"],
#                 "Breaches": int(row["breach_count"]), "Last Breach": lb,
#                 "Order Now": int(row["repl_quantity"]),
#                 "Spark": (",".join([str(round(v)) for v in spark])),
#             })
#         df_grid = pd.DataFrame(grid_rows)

#         gb = GridOptionsBuilder.from_dataframe(df_grid)
#         gb.configure_column("Risk",       cellRenderer=_STATUS_R, width=120, minWidth=120, maxWidth=120, pinned="left")
#         gb.configure_column("Material",   width=200, minWidth=200, maxWidth=200, pinned="left")
#         gb.configure_column("Stock",      width=80,  minWidth=80,  maxWidth=80,  type=["numericColumn"])
#         gb.configure_column("SAP SS",     width=80,  minWidth=80,  maxWidth=80,  type=["numericColumn"])
#         gb.configure_column("ARIA SS",    width=85,  minWidth=85,  maxWidth=85,  type=["numericColumn"])
#         gb.configure_column("Days Cover", width=130, minWidth=130, maxWidth=130, cellRenderer=_COVER_R)
#         gb.configure_column("Demand/mo",  width=95,  minWidth=95,  maxWidth=95,  type=["numericColumn"])
#         gb.configure_column("Trend",      width=85,  minWidth=85,  maxWidth=85)
#         gb.configure_column("Breaches",   width=85,  minWidth=85,  maxWidth=85,  type=["numericColumn"])
#         gb.configure_column("Last Breach",width=100, minWidth=100, maxWidth=100)
#         gb.configure_column("Order Now",  width=100, minWidth=100, maxWidth=100, cellRenderer=_ORDER_R)
#         gb.configure_column("Spark",      width=100, minWidth=100, maxWidth=100, cellRenderer=_SPARK_R, headerName="8m Trend")
#         gb.configure_grid_options(rowHeight=42, headerHeight=34, getRowStyle=_ROW_STYLE,
#                                    suppressMovableColumns=True, suppressColumnVirtualisation=False)
#         gb.configure_selection("single", use_checkbox=False)
#         gb.configure_default_column(resizable=True, sortable=True, filter=False, wrapText=True, autoHeight=True)

#         AgGrid(df_grid, gridOptions=gb.build(), height=380, allow_unsafe_jscode=True,
#                update_mode=GridUpdateMode.SELECTION_CHANGED, theme="alpine",
#                custom_css=_AGGRID_CSS)

#     # ── RIGHT: Intelligence Feed (with timestamps) ─────────────────────────────
#     with feed_col:
#         st.markdown(
#             "<div style='font-size:13px;font-weight:800;color:var(--t);margin-bottom:8px;'>Intelligence Feed</div>",
#             unsafe_allow_html=True,
#         )
#         feed_items = []
#         now_str = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M")
        
#         # Critical materials with rich detail
#         for _, row in summary[summary.risk == "CRITICAL"].iterrows():
#             repl_q = int(row["repl_quantity"])
#             feed_items.append({
#                 "dot": "#EF4444", "type": "crit", 
#                 "time": now_str,
#                 "msg": f"<span>⛔ {row['name']}</span>",
#                 "sub": f"{round(row['sih'])} units stock · {round(row['days_cover'])}d cover · SS={round(row['safety_stock'])}" +
#                        (f" · ORDER {repl_q} units NOW" if repl_q > 0 else "")
#             })
#         # Warning
#         for _, row in summary[summary.risk == "WARNING"].iterrows():
#             feed_items.append({
#                 "dot": ORANGE, "type": "warn", "time": now_str,
#                 "msg": f"<span>⚠ {row['name']}</span>",
#                 "sub": f"{round(row['days_cover'])}d cover remaining · Approaching safety stock threshold"
#             })
#         # SS gaps with numbers
#         ss_gap = summary[(summary.safety_stock < summary.rec_safety_stock) & (summary.risk != "INSUFFICIENT_DATA")]
#         for _, row in ss_gap.sort_values("breach_count", ascending=False).head(2).iterrows():
#             g = round(row["rec_safety_stock"] - row["safety_stock"])
#             if g > 0:
#                 feed_items.append({
#                     "dot": "#F59E0B", "type": "warn", "time": now_str,
#                     "msg": f"<span>SAP SS Under-configured</span> — {row['name'][:20]}",
#                     "sub": f"SAP: {round(row['safety_stock'])} units · ARIA recommends: {round(row['rec_safety_stock'])} · Gap: {g} units"
#                 })
#         # Historical breaches – use the actual period of the last breach
#         top_b = summary[(summary.breach_count > 0) & (summary.risk != "INSUFFICIENT_DATA")].sort_values("breach_count", ascending=False)
#         if len(top_b) > 0:
#             r = top_b.iloc[0]
#             # Get the last breach period for this material
#             sh_hist = get_stock_history(data, r["material"])
#             ss = r["safety_stock"]
#             if ss > 0:
#                 breaches = sh_hist[sh_hist["Gross Stock"] < ss]
#                 if len(breaches) > 0:
#                     last_breach_period = fmt_p(breaches["Fiscal Period"].iloc[-1])
#                 else:
#                     last_breach_period = "Past"
#             else:
#                 last_breach_period = "Past"
#             feed_items.append({
#                 "dot": ORANGE, "type": "info", "time": last_breach_period,
#                 "msg": f"<span>{r['name']}</span> — {r['breach_count']} stockout events",
#                 "sub": f"Worst performer over 25 months · {r['breach_count']} periods below safety stock"
#             })
#         # Lead time urgency
#         lt_critical = summary[(summary.days_cover < summary.lead_time) & (summary.risk != "INSUFFICIENT_DATA")]
#         for _, row in lt_critical.iterrows():
#             feed_items.append({
#                 "dot": "#EF4444", "type": "crit", "time": now_str,
#                 "msg": f"<span>Lead Time Exceeds Cover</span> — {row['name'][:22]}",
#                 "sub": f"Cover={round(row['days_cover'])}d but Lead Time={round(row['lead_time'])}d · Order immediately"
#             })
#         # System health
#         feed_items.append({
#             "dot": "#22C55E", "type": "ok", "time": now_str,
#             "msg": "<span>ARIA</span> — Safety stock models updated",
#             "sub": "Formula: CEILING(Shortfall/FLS)×FLS · Source: Material Master"
#         })

#         tag_map = {"crit": "ftc", "warn": "ftw", "ok": "fto", "info": "fti"}
#         tag_lbl = {"crit": "Critical", "warn": "Warning", "ok": "Healthy", "info": "Update"}
#         items_html = ""
#         for i, item in enumerate(feed_items[:12]):  # show up to 12 items
#             line     = "" if i >= 11 else "<div class='fi-line'></div>"
#             sub_html = (f"<div class='fi-sub'>{item.get('sub','')}</div>") if item.get("sub") else ""
#             items_html += (
#                 f"<div class='fi'><div class='fi-dc'>"
#                 f"<div class='fi-dot' style='background:{item['dot']};'></div>{line}</div>"
#                 f"<div style='flex:1;min-width:0;'>"
#                 f"<div class='fi-msg'>{item['msg']}</div>"
#                 + sub_html +
#                 f"<div style='display:flex;align-items:center;gap:6px;margin-top:2px;'>"
#                 f"<div class='fi-time'>{item['time']}</div>"
#                 f"<span class='fi-tag {tag_map[item['type']]}'>{tag_lbl[item['type']]}</span>"
#                 f"</div></div></div>"
#             )
#         st.markdown(
#             "<div class='fc' style='height:380px;overflow-y:auto;'>"
#             "<div class='fh'><div class='fht'>Intelligence Feed</div>"
#             "<div class='flv'><div class='dot dot-g'></div>Live</div>"
#             "</div>" + items_html + "</div>",
#             unsafe_allow_html=True,
#         )

#     # ── Analytics ─────────────────────────────────────────────────────────────
#     st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)
#     sec("Supply Chain Analytics")
#     c1, c2 = st.columns(2, gap="medium")

#     with c1:
#         st.markdown(
#             "<div style='font-size:11px;font-weight:700;color:var(--t2);margin-bottom:5px;'>"
#             "Historical Stockout Events by Month &amp; Product</div>",
#             unsafe_allow_html=True,
#         )
#         all_breaches = []
#         for _, row in summary[summary.breach_count > 0].iterrows():
#             sh3 = get_stock_history(data, row["material"])
#             ss  = row["safety_stock"]
#             if ss <= 0:
#                 continue
#             b = sh3[sh3["Gross Stock"] < ss]
#             for _, br in b.iterrows():
#                 all_breaches.append({"label": fmt_p(br["Fiscal Period"]), "period": br["Fiscal Period"], "material": row["name"][:16]})

#         if all_breaches:
#             df_br = pd.DataFrame(all_breaches)
#             pivot = df_br.groupby(["period", "label", "material"]).size().reset_index(name="count")
#             pivot = pivot.sort_values("period")
#             recent_periods = pivot["period"].unique()[-14:]
#             pivot = pivot[pivot["period"].isin(recent_periods)]
#             colors = ["#EF4444", "#F59E0B", "#8B5CF6", "#EC4899", "#06B6D4"]
#             fig1   = go.Figure()
#             for i, mat in enumerate(pivot["material"].unique()):
#                 md     = pivot[pivot.material == mat]
#                 periods_all = pivot["label"].unique().tolist()
#                 counts = [md[md.label == p]["count"].sum() if p in md["label"].values else 0 for p in periods_all]
#                 fig1.add_trace(go.Bar(
#                     name=mat, x=periods_all, y=counts,
#                     marker_color=colors[i % len(colors)], marker_line_width=0,
#                     hovertemplate="<b>%{x}</b><br>" + mat + ": %{y} breach(es)<extra></extra>",
#                 ))
#             ct(fig1, 210)
#             fig1.update_layout(barmode="stack", showlegend=True,
#                                legend=dict(font_size=9, orientation="h", y=1.12),
#                                xaxis_tickangle=-40, yaxis=dict(dtick=1, title="Breaches"))
#             st.plotly_chart(fig1, use_container_width=True)
#         else:
#             st.markdown(
#                 "<div style='height:210px;display:flex;align-items:center;justify-content:center;"
#                 "color:var(--t3);font-size:12px;border:1px solid var(--bl);border-radius:var(--r);'>"
#                 "No breach events recorded</div>",
#                 unsafe_allow_html=True,
#             )

#     with c2:
#         st.markdown(
#             "<div style='font-size:11px;font-weight:700;color:var(--t2);margin-bottom:5px;'>Days of Cover per SKU</div>",
#             unsafe_allow_html=True,
#         )
#         act2  = summary[summary.risk.isin(["CRITICAL", "WARNING", "HEALTHY"])].sort_values("days_cover")
#         clrs2 = ["#EF4444" if r == "CRITICAL" else "#F59E0B" if r == "WARNING" else "#22C55E" for r in act2["risk"]]
#         cap   = [min(float(v), 300) for v in act2["days_cover"]]
#         fig2  = go.Figure()
#         fig2.add_trace(go.Bar(
#             y=act2["name"].str[:22].tolist(), x=cap, orientation="h",
#             marker_color=clrs2, marker_opacity=0.85, marker_line_width=0,
#             text=[(str(round(v)) + "d") for v in cap],
#             textposition="outside", textfont=dict(size=9, color="#475569"),
#             hovertemplate="<b>%{y}</b><br>Days cover: %{x:.0f}d<extra></extra>",
#         ))
#         fig2.add_vline(x=30, line_color="#EF4444", line_dash="dot", line_width=1.5,
#                        annotation_text="30d min", annotation_font_color="#EF4444", annotation_font_size=9)
#         ct(fig2, 210)
#         fig2.update_layout(showlegend=False, xaxis_title="Days", margin=dict(l=8, r=48, t=28, b=8))
#         st.plotly_chart(fig2, use_container_width=True)

#     # ── ARIA LLM Insight (skip INSUFFICIENT_DATA) ────────────────────────────
#     if st.session_state.azure_client:
#         ai2, rb2 = st.columns([10, 1])
#         with rb2:
#             if st.button("↺", key="ref_cc", help="Refresh ARIA overview"):
#                 st.session_state.cc_insight = None
#         if st.session_state.cc_insight is None:
#             valid_materials = summary[summary.risk != "INSUFFICIENT_DATA"]
#             if len(valid_materials) > 0:
#                 most_critical = valid_materials.sort_values('days_cover').iloc[0]
#                 ctx_str = (
#                     f"Plant FI11 Turku: {total} materials. Critical: {crit_n}"
#                     + (f" ({', '.join(valid_materials[valid_materials.risk == 'CRITICAL']['name'].tolist())})" if crit_n > 0 else "")
#                     + f". Insufficient data: {insuf_n}. Healthy: {ok_n}. "
#                     + f"Most critical: {most_critical['name']} "
#                     + f"with {most_critical['days_cover']:.1f}d cover, "
#                     + f"stock={most_critical['sih']:.0f} vs SS={most_critical['safety_stock']:.0f}."
#                 )
#             else:
#                 ctx_str = f"Plant FI11 Turku: {total} materials. Critical: 0. All materials have insufficient data."
#             try:
#                 insight = chat_with_data(
#                     st.session_state.azure_client, AZURE_DEPLOYMENT,
#                     "Give a 2-sentence executive briefing on the current supply chain health. "
#                     "Identify the single biggest risk and one specific action.",
#                     ctx_str,
#                 )
#                 st.session_state.cc_insight = insight
#             except Exception:
#                 st.session_state.cc_insight = None
#         if st.session_state.cc_insight:
#             st.markdown(
#                 "<div class='ic' style='margin:10px 0;'>"
#                 "<div class='il'>◈ ARIA PLANT INTELLIGENCE</div>"
#                 f"<div class='ib' style='margin-top:4px;'>{st.session_state.cc_insight}</div>"
#                 "</div>",
#                 unsafe_allow_html=True,
#             )

#     # ── Product Deep-Dive ─────────────────────────────────────────────────────
#     sec("Product Deep-Dive")
#     note("Days cover = SIH (Stock-in-Hand from Current Inventory) ÷ avg daily demand (from Sales file). Safety Stock from Material Master.")

#     pd_col1, pd_col2 = st.columns([2, 1])
#     with pd_col1:
#         prod_opts = [r["name"] for _, r in summary[summary.risk != "INSUFFICIENT_DATA"].iterrows()]
#         sel_prod  = st.selectbox("Select product", prod_opts, key="cc_prod")
#     with pd_col2:
#         month_range = st.slider("Show last N months", 6, 60, 24, step=6, key="cc_months")

#     sel_mat_id  = summary[summary.name == sel_prod]["material"].values[0]
#     dh_cc       = get_demand_history(data, sel_mat_id)
#     sh_cc       = get_stock_history(data, sel_mat_id)
#     mat_row_cc  = summary[summary.material == sel_mat_id].iloc[0]
#     ss_cc       = mat_row_cc["safety_stock"]
#     repl_cc     = int(mat_row_cc["repl_quantity"])
#     lt_cc       = float(mat_row_cc["lead_time"])
#     lot_cc      = float(mat_row_cc["lot_size"])
#     sih_cc      = float(mat_row_cc["sih"])

#     sh_cc   = sh_cc.tail(month_range)
#     dh_cc_f = dh_cc.tail(month_range)

#     if len(sh_cc) > 0:
#         fig_dd  = go.Figure()
#         avg_d   = float(dh_cc_f[dh_cc_f.demand > 0]["demand"].mean()) if len(dh_cc_f[dh_cc_f.demand > 0]) > 0 else 0
#         fig_dd.add_trace(go.Scatter(
#             x=sh_cc["label"], y=sh_cc["Gross Stock"], mode="lines+markers", name="Stock (units)",
#             line=dict(color=ORANGE, width=2.5), marker=dict(size=4, color=ORANGE),
#             fill="tozeroy", fillcolor="rgba(244,123,37,0.08)", yaxis="y1",
#             hovertemplate="<b>%{x}</b><br>Stock: %{y} units<extra></extra>",
#         ))
#         dem_aligned = dh_cc_f[dh_cc_f.label.isin(sh_cc["label"].tolist())]
#         if len(dem_aligned) > 0:
#             fig_dd.add_trace(go.Bar(
#                 x=dem_aligned["label"], y=dem_aligned["demand"], name="Demand/mo",
#                 marker_color="rgba(148,163,184,0.3)", marker_line_width=0, yaxis="y2",
#                 hovertemplate="<b>%{x}</b><br>Demand: %{y} units<extra></extra>",
#             ))
#         if ss_cc > 0:
#             fig_dd.add_hline(y=ss_cc, line_color="#EF4444", line_dash="dot", line_width=1.5,
#                              annotation_text="SAP SS " + str(round(ss_cc)) + "u",
#                              annotation_font_color="#EF4444", annotation_font_size=9)
#         ct(fig_dd, 240)
#         fig_dd.update_layout(
#             title=dict(text=sel_prod + " — Stock vs Demand (last " + str(month_range) + "mo)",
#                        font=dict(size=11, color="#475569"), x=0),
#             xaxis=dict(tickangle=-35),
#             yaxis=dict(title="Stock (units)", gridcolor="#F0F4F9"),
#             yaxis2=dict(title="Demand/mo", overlaying="y", side="right", showgrid=False),
#             legend=dict(orientation="h", y=1.1),
#             margin=dict(l=8, r=50, t=44, b=8),
#         )
#         st.plotly_chart(fig_dd, use_container_width=True)

#     if repl_cc > 0:
#         st.markdown(
#             "<div class='prow' style='border-left:3px solid #EF4444;background:#FEF2F2;'>"
#             "<div style='font-size:16px;'>⛔</div>"
#             "<div style='flex:1;'>"
#             "<div style='font-size:12px;font-weight:800;color:#EF4444;'>Replenishment Required</div>"
#             "<div style='font-size:11px;color:#475569;margin-top:2px;'>"
#             f"Stock-in-Hand: <strong>{round(sih_cc)}</strong> · SAP SS: <strong>{round(ss_cc)}</strong> · "
#             f"Lead time: <strong>{round(lt_cc)}d</strong> (Material Master) · "
#             f"Lot size: <strong>{round(lot_cc)}</strong>"
#             "</div></div>"
#             "<div style='text-align:right;'>"
#             f"<div style='font-size:22px;font-weight:900;color:#EF4444;'>{repl_cc} units</div>"
#             f"<div style='font-size:9px;color:#EF4444;'>CEILING({round(ss_cc-sih_cc)}/{round(lot_cc)})×{round(lot_cc)}</div>"
#             "</div></div>",
#             unsafe_allow_html=True,
#         )

#     st.markdown('<div class="pfooter">⚡ Powered by <strong>MResult</strong></div>', unsafe_allow_html=True)

"""
tabs/command_center.py
Command Center tab: KPI cards, Material Health Board, Intelligence Feed (with timestamps),
analytics charts, and product deep-dive.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode, GridUpdateMode

from utils.helpers import ct, fmt_p, sbadge, sec, note, ORANGE, AZURE_DEPLOYMENT
from data_loader import get_stock_history, get_demand_history
from agent import chat_with_data


# ── KPI card renderer ─────────────────────────────────────────────────────────
_SVG = {
    "tot":  '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="8" r="4"/><path d="M4 20c0-4 3.6-7 8-7s8 3 8 7"/></svg>',
    "crit": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>',
    "insuf":'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>',
    "ok":   '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>',
}


def _kpi(col, svg, si, val, vc, lbl, dlt=None, dc="sdu"):
    dh = (f'<span class="sdt {dc}">{dlt}</span>') if dlt else ""
    with col:
        st.markdown(
            f"<div class='sc'><div class='si {si}'>{svg}</div>"
            f"<div style='flex:1;'><div class='sv' style='color:{vc};'>{val}</div>"
            f"<div class='sl'>{lbl}</div></div>{dh}</div>",
            unsafe_allow_html=True,
        )


# ── AgGrid JS renderers ────────────────────────────────────────────────────────
_STATUS_R = JsCode("""class R{init(p){const m={'CRITICAL':['#FEE2E2','#EF4444','⛔ Critical'],'WARNING':['#FEF3C7','#F59E0B','⚠ Warning'],'HEALTHY':['#DCFCE7','#22C55E','✓ Healthy'],'INSUFFICIENT_DATA':['#F1F5F9','#94A3B8','◌ No Data']};const[bg,c,l]=m[p.value]||m.INSUFFICIENT_DATA;this.e=document.createElement('span');this.e.style.cssText=`background:${bg};color:${c};border:1px solid ${c}44;padding:2px 7px;border-radius:20px;font-size:9px;font-weight:700;white-space:nowrap;`;this.e.innerText=l;}getGui(){return this.e;}}""")
_SPARK_R   = JsCode("""class R{init(p){const raw=(p.value||'').split(',').map(Number).filter(n=>!isNaN(n));const w=72,h=22,pad=3;this.e=document.createElement('div');if(!raw.length){this.e.innerText='—';return;}const mn=Math.min(...raw),mx=Math.max(...raw),rng=mx-mn||1;const pts=raw.map((v,i)=>{const x=pad+i*(w-2*pad)/(raw.length-1||1);const y=h-pad-(v-mn)/rng*(h-2*pad);return x+','+y;}).join(' ');const l=raw[raw.length-1],f=raw[0];const t=l>f?'#22C55E':l<f?'#EF4444':'#F47B25';this.e.innerHTML=`<svg width="${w}" height="${h}"><polyline points="${pts}" fill="none" stroke="${t}" stroke-width="1.8" stroke-linejoin="round" stroke-linecap="round"/><circle cx="${pts.split(' ').pop().split(',')[0]}" cy="${pts.split(' ').pop().split(',')[1]}" r="2" fill="${t}"/></svg>`;}getGui(){return this.e;}}""")
_COVER_R   = JsCode("""class R{init(p){const v=p.value||0;const pct=Math.min(v/180*100,100);const c=v<15?'#EF4444':v<30?'#F59E0B':'#22C55E';this.e=document.createElement('div');this.e.style.cssText='display:flex;align-items:center;gap:4px;width:100%;';this.e.innerHTML=`<div style="flex:1;height:5px;background:#F0F4F9;border-radius:3px;overflow:hidden;"><div style="width:${pct}%;height:100%;background:${c};border-radius:3px;"></div></div><span style="font-size:10px;font-weight:700;color:${c};min-width:28px;">${v}d</span>`;}getGui(){return this.e;}}""")
_ORDER_R   = JsCode("""class R{init(p){const v=p.value||0;this.e=document.createElement('span');if(v>0){this.e.style.cssText='background:#FEE2E2;color:#EF4444;border:1px solid #EF444440;padding:2px 7px;border-radius:5px;font-size:10px;font-weight:700;';this.e.innerText=v+' units';}else{this.e.style.cssText='background:#F0F4F9;color:#94A3B8;padding:2px 7px;border-radius:5px;font-size:10px;';this.e.innerText='—';};}getGui(){return this.e;}}""")
_ROW_STYLE = JsCode("""function(p){if(p.data.Risk==='CRITICAL')return{'background':'rgba(239,68,68,0.03)','border-left':'3px solid #EF4444'};if(p.data.Risk==='WARNING')return{'background':'rgba(245,158,11,0.02)','border-left':'3px solid #F59E0B'};if(p.data.Risk==='INSUFFICIENT_DATA')return{'color':'#94A3B8'};return{};}""")

_AGGRID_CSS = {
    ".ag-root-wrapper": {"border": "1px solid #E2E8F0!important", "border-radius": "14px!important", "overflow": "auto !important"},
    ".ag-header":       {"background": "#F8FAFE!important"},
    ".ag-row-even":     {"background": "#FFFFFF!important"},
    ".ag-row-odd":      {"background": "#F8FAFE!important"},
    ".ag-cell":         {"border-right": "1px solid #F0F4F9!important", "white-space": "normal !important", "word-break": "break-word !important"},
    ".ag-cell-wrapper": {"white-space": "normal !important"},
}


def render():
    data    = st.session_state.data
    summary = st.session_state.summary

    # ── KPI Row ───────────────────────────────────────────────────────────────
    total   = len(summary)
    crit_n  = int((summary.risk == "CRITICAL").sum())
    insuf_n = int((summary.risk == "INSUFFICIENT_DATA").sum())
    ok_n    = int((summary.risk == "HEALTHY").sum())

    k1, k2, k3, k4 = st.columns(4)
    _kpi(k1, _SVG["tot"],   "sio", total,   "#1E293B", "Total Materials")
    _kpi(k2, _SVG["crit"],  "sir", crit_n,  "#EF4444", "Critical Alerts",
         "⛔ Action required" if crit_n > 0 else "✓ None",
         "sdc" if crit_n > 0 else "sdu")
    _kpi(k3, _SVG["insuf"], "six", insuf_n, "#94A3B8", "Insufficient Data",
         str(insuf_n) + " SKUs", "sdw" if insuf_n > 0 else "sdu")
    _kpi(k4, _SVG["ok"],    "sig", ok_n,    "#22C55E", "Healthy", "↑ Operating", "sdu")

    # ── Main Row: Health Board + Intelligence Feed ────────────────────────────
    st.markdown("<div style='height:14px;'></div>", unsafe_allow_html=True)
    board_col, feed_col = st.columns([3, 2], gap="medium")

    with board_col:
        st.markdown(
            "<div style='font-size:13px;font-weight:800;color:var(--t);margin-bottom:8px;'>"
            "Material Health Board"
            "<span style='font-size:11px;font-weight:400;color:var(--t3);margin-left:8px;'>Sortable · Horizontal scroll</span>"
            "</div>",
            unsafe_allow_html=True,
        )
        grid_rows = []
        for _, row in summary.iterrows():
            sh2 = get_stock_history(data, row["material"])
            dh2 = get_demand_history(data, row["material"])
            nz  = dh2[dh2.demand > 0]
            avg = float(nz.demand.mean()) if len(nz) > 0 else 0
            ss  = row["safety_stock"]
            br  = sh2[sh2["Gross Stock"] < max(ss, 1)] if ss > 0 else pd.DataFrame()
            lb  = fmt_p(br["Fiscal Period"].iloc[-1]) if len(br) > 0 else "—"
            spark = sh2["Gross Stock"].tail(8).tolist()
            dc  = row["days_cover"]
            grid_rows.append({
                "Risk": row["risk"], "Material": row["name"],
                "Stock": int(row["sih"]), "SAP SS": int(ss), "ARIA SS": int(row["rec_safety_stock"]),
                "Days Cover": int(dc) if dc < 999 else 0,
                "Demand/mo": round(avg, 0), "Trend": row["trend"],
                "Breaches": int(row["breach_count"]), "Last Breach": lb,
                "Order Now": int(row["repl_quantity"]),
                "Spark": (",".join([str(round(v)) for v in spark])),
            })
        df_grid = pd.DataFrame(grid_rows)

        gb = GridOptionsBuilder.from_dataframe(df_grid)
        gb.configure_column("Risk",       cellRenderer=_STATUS_R, width=120, minWidth=120, maxWidth=120, pinned="left")
        gb.configure_column("Material",   width=200, minWidth=200, maxWidth=200, pinned="left")
        gb.configure_column("Stock",      width=80,  minWidth=80,  maxWidth=80,  type=["numericColumn"])
        gb.configure_column("SAP SS",     width=80,  minWidth=80,  maxWidth=80,  type=["numericColumn"])
        gb.configure_column("ARIA SS",    width=85,  minWidth=85,  maxWidth=85,  type=["numericColumn"])
        gb.configure_column("Days Cover", width=130, minWidth=130, maxWidth=130, cellRenderer=_COVER_R)
        gb.configure_column("Demand/mo",  width=95,  minWidth=95,  maxWidth=95,  type=["numericColumn"])
        gb.configure_column("Trend",      width=85,  minWidth=85,  maxWidth=85)
        gb.configure_column("Breaches",   width=85,  minWidth=85,  maxWidth=85,  type=["numericColumn"])
        gb.configure_column("Last Breach",width=100, minWidth=100, maxWidth=100)
        gb.configure_column("Order Now",  width=100, minWidth=100, maxWidth=100, cellRenderer=_ORDER_R)
        gb.configure_column("Spark",      width=100, minWidth=100, maxWidth=100, cellRenderer=_SPARK_R, headerName="8m Trend")
        gb.configure_grid_options(rowHeight=42, headerHeight=34, getRowStyle=_ROW_STYLE,
                                   suppressMovableColumns=True, suppressColumnVirtualisation=False)
        gb.configure_selection("single", use_checkbox=False)
        gb.configure_default_column(resizable=True, sortable=True, filter=False, wrapText=True, autoHeight=True)

        AgGrid(df_grid, gridOptions=gb.build(), height=380, allow_unsafe_jscode=True,
               update_mode=GridUpdateMode.SELECTION_CHANGED, theme="alpine",
               custom_css=_AGGRID_CSS)

    # ── RIGHT: Intelligence Feed (with timestamps) ─────────────────────────────
    with feed_col:
        st.markdown(
            "<div style='font-size:13px;font-weight:800;color:var(--t);margin-bottom:8px;'>Intelligence Feed</div>",
            unsafe_allow_html=True,
        )
        feed_items = []
        now_str = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M")
        
        # Critical materials with rich detail
        for _, row in summary[summary.risk == "CRITICAL"].iterrows():
            repl_q = int(row["repl_quantity"])
            feed_items.append({
                "dot": "#EF4444", "type": "crit", 
                "time": now_str,
                "msg": f"<span>⛔ {row['name']}</span>",
                "sub": f"{round(row['sih'])} units stock · {round(row['days_cover'])}d cover · SS={round(row['safety_stock'])}" +
                       (f" · ORDER {repl_q} units NOW" if repl_q > 0 else "")
            })
        # Warning
        for _, row in summary[summary.risk == "WARNING"].iterrows():
            feed_items.append({
                "dot": ORANGE, "type": "warn", "time": now_str,
                "msg": f"<span>⚠ {row['name']}</span>",
                "sub": f"{round(row['days_cover'])}d cover remaining · Approaching safety stock threshold"
            })
        # SS gaps with numbers
        ss_gap = summary[(summary.safety_stock < summary.rec_safety_stock) & (summary.risk != "INSUFFICIENT_DATA")]
        for _, row in ss_gap.sort_values("breach_count", ascending=False).head(2).iterrows():
            g = round(row["rec_safety_stock"] - row["safety_stock"])
            if g > 0:
                feed_items.append({
                    "dot": "#F59E0B", "type": "warn", "time": now_str,
                    "msg": f"<span>SAP SS Under-configured</span> — {row['name'][:20]}",
                    "sub": f"SAP: {round(row['safety_stock'])} units · ARIA recommends: {round(row['rec_safety_stock'])} · Gap: {g} units"
                })
        # Historical breaches – use the actual period of the last breach
        top_b = summary[(summary.breach_count > 0) & (summary.risk != "INSUFFICIENT_DATA")].sort_values("breach_count", ascending=False)
        if len(top_b) > 0:
            r = top_b.iloc[0]
            # Get the last breach period for this material
            sh_hist = get_stock_history(data, r["material"])
            ss = r["safety_stock"]
            if ss > 0:
                breaches = sh_hist[sh_hist["Gross Stock"] < ss]
                if len(breaches) > 0:
                    last_breach_period = fmt_p(breaches["Fiscal Period"].iloc[-1])
                else:
                    last_breach_period = "Past"
            else:
                last_breach_period = "Past"
            feed_items.append({
                "dot": ORANGE, "type": "info", "time": last_breach_period,
                "msg": f"<span>{r['name']}</span> — {r['breach_count']} stockout events",
                "sub": f"Worst performer over 25 months · {r['breach_count']} periods below safety stock"
            })
        # Lead time urgency
        lt_critical = summary[(summary.days_cover < summary.lead_time) & (summary.risk != "INSUFFICIENT_DATA")]
        for _, row in lt_critical.iterrows():
            feed_items.append({
                "dot": "#EF4444", "type": "crit", "time": now_str,
                "msg": f"<span>Lead Time Exceeds Cover</span> — {row['name'][:22]}",
                "sub": f"Cover={round(row['days_cover'])}d but Lead Time={round(row['lead_time'])}d · Order immediately"
            })
        # System health
        feed_items.append({
            "dot": "#22C55E", "type": "ok", "time": now_str,
            "msg": "<span>ARIA</span> — Safety stock models updated",
            "sub": "Formula: CEILING(Shortfall/FLS)×FLS · Source: Material Master"
        })

        tag_map = {"crit": "ftc", "warn": "ftw", "ok": "fto", "info": "fti"}
        tag_lbl = {"crit": "Critical", "warn": "Warning", "ok": "Healthy", "info": "Update"}
        items_html = ""
        for i, item in enumerate(feed_items[:12]):  # show up to 12 items
            line     = "" if i >= 11 else "<div class='fi-line'></div>"
            sub_html = (f"<div class='fi-sub'>{item.get('sub','')}</div>") if item.get("sub") else ""
            items_html += (
                f"<div class='fi'><div class='fi-dc'>"
                f"<div class='fi-dot' style='background:{item['dot']};'></div>{line}</div>"
                f"<div style='flex:1;min-width:0;'>"
                f"<div class='fi-msg'>{item['msg']}</div>"
                + sub_html +
                f"<div style='display:flex;align-items:center;gap:6px;margin-top:2px;'>"
                f"<div class='fi-time'>{item['time']}</div>"
                f"<span class='fi-tag {tag_map[item['type']]}'>{tag_lbl[item['type']]}</span>"
                f"</div></div></div>"
            )
        st.markdown(
            "<div class='fc' style='height:380px;overflow-y:auto;'>"
            "<div class='fh'><div class='fht'>Intelligence Feed</div>"
            "<div class='flv'><div class='dot dot-g'></div>Live</div>"
            "</div>" + items_html + "</div>",
            unsafe_allow_html=True,
        )

    # ── Analytics ─────────────────────────────────────────────────────────────
    st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)
    sec("Supply Chain Analytics")
    c1, c2 = st.columns(2, gap="medium")

    with c1:
        # FIX: Changed title from "Historical Stockout Events" to "Historical Safety Stock Breaches"
        st.markdown(
            "<div style='font-size:11px;font-weight:700;color:var(--t2);margin-bottom:5px;'>"
            "Historical Safety Stock Breaches by Month & Product &amp; Product</div>",
            unsafe_allow_html=True,
        )
        all_breaches = []
        for _, row in summary[summary.breach_count > 0].iterrows():
            sh3 = get_stock_history(data, row["material"])
            ss  = row["safety_stock"]
            if ss <= 0:
                continue
            b = sh3[sh3["Gross Stock"] < ss]
            for _, br in b.iterrows():
                all_breaches.append({"label": fmt_p(br["Fiscal Period"]), "period": br["Fiscal Period"], "material": row["name"][:16]})

        if all_breaches:
            df_br = pd.DataFrame(all_breaches)
            pivot = df_br.groupby(["period", "label", "material"]).size().reset_index(name="count")
            pivot = pivot.sort_values("period")
            recent_periods = pivot["period"].unique()[-14:]
            pivot = pivot[pivot["period"].isin(recent_periods)]
            colors = ["#EF4444", "#F59E0B", "#8B5CF6", "#EC4899", "#06B6D4"]
            fig1   = go.Figure()
            for i, mat in enumerate(pivot["material"].unique()):
                md     = pivot[pivot.material == mat]
                periods_all = pivot["label"].unique().tolist()
                counts = [md[md.label == p]["count"].sum() if p in md["label"].values else 0 for p in periods_all]
                fig1.add_trace(go.Bar(
                    name=mat, x=periods_all, y=counts,
                    marker_color=colors[i % len(colors)], marker_line_width=0,
                    hovertemplate="<b>%{x}</b><br>" + mat + ": %{y} breach(es)<extra></extra>",
                ))
            ct(fig1, 210)
            fig1.update_layout(barmode="stack", showlegend=True,
                               legend=dict(font_size=9, orientation="h", y=1.12),
                               xaxis_tickangle=-40, yaxis=dict(dtick=1, title="Breaches"))
            st.plotly_chart(fig1, use_container_width=True)
        else:
            st.markdown(
                "<div style='height:210px;display:flex;align-items:center;justify-content:center;"
                "color:var(--t3);font-size:12px;border:1px solid var(--bl);border-radius:var(--r);'>"
                "No breach events recorded</div>",
                unsafe_allow_html=True,
            )

    with c2:
        st.markdown(
            "<div style='font-size:11px;font-weight:700;color:var(--t2);margin-bottom:5px;'>Days of Cover per SKU</div>",
            unsafe_allow_html=True,
        )
        act2  = summary[summary.risk.isin(["CRITICAL", "WARNING", "HEALTHY"])].sort_values("days_cover")
        clrs2 = ["#EF4444" if r == "CRITICAL" else "#F59E0B" if r == "WARNING" else "#22C55E" for r in act2["risk"]]
        cap   = [min(float(v), 300) for v in act2["days_cover"]]
        fig2  = go.Figure()
        fig2.add_trace(go.Bar(
            y=act2["name"].str[:22].tolist(), x=cap, orientation="h",
            marker_color=clrs2, marker_opacity=0.85, marker_line_width=0,
            text=[(str(round(v)) + "d") for v in cap],
            textposition="outside", textfont=dict(size=9, color="#475569"),
            hovertemplate="<b>%{y}</b><br>Days cover: %{x:.0f}d<extra></extra>",
        ))
        fig2.add_vline(x=30, line_color="#EF4444", line_dash="dot", line_width=1.5,
                       annotation_text="30d min", annotation_font_color="#EF4444", annotation_font_size=9)
        ct(fig2, 210)
        fig2.update_layout(showlegend=False, xaxis_title="Days", margin=dict(l=8, r=48, t=28, b=8))
        st.plotly_chart(fig2, use_container_width=True)

    # ── ARIA LLM Insight (skip INSUFFICIENT_DATA) ────────────────────────────
    if st.session_state.azure_client:
        ai2, rb2 = st.columns([10, 1])
        with rb2:
            if st.button("↺", key="ref_cc", help="Refresh ARIA overview"):
                st.session_state.cc_insight = None
        if st.session_state.cc_insight is None:
            valid_materials = summary[summary.risk != "INSUFFICIENT_DATA"]
            if len(valid_materials) > 0:
                most_critical = valid_materials.sort_values('days_cover').iloc[0]
                ctx_str = (
                    f"Plant FI11 Turku: {total} materials. Critical: {crit_n}"
                    + (f" ({', '.join(valid_materials[valid_materials.risk == 'CRITICAL']['name'].tolist())})" if crit_n > 0 else "")
                    + f". Insufficient data: {insuf_n}. Healthy: {ok_n}. "
                    + f"Most critical: {most_critical['name']} "
                    + f"with {most_critical['days_cover']:.1f}d cover, "
                    + f"stock={most_critical['sih']:.0f} vs SS={most_critical['safety_stock']:.0f}."
                )
            else:
                ctx_str = f"Plant FI11 Turku: {total} materials. Critical: 0. All materials have insufficient data."
            try:
                insight = chat_with_data(
                    st.session_state.azure_client, AZURE_DEPLOYMENT,
                    "Give a 2-sentence executive briefing on the current supply chain health. "
                    "Identify the single biggest risk and one specific action.",
                    ctx_str,
                )
                st.session_state.cc_insight = insight
            except Exception:
                st.session_state.cc_insight = None
        if st.session_state.cc_insight:
            st.markdown(
                "<div class='ic' style='margin:10px 0;'>"
                "<div class='il'>◈ ARIA PLANT INTELLIGENCE</div>"
                f"<div class='ib' style='margin-top:4px;'>{st.session_state.cc_insight}</div>"
                "</div>",
                unsafe_allow_html=True,
            )

    # ── Product Deep-Dive ─────────────────────────────────────────────────────
    sec("Product Deep-Dive")
    note("Days cover = SIH (Stock-in-Hand from Current Inventory) ÷ avg daily demand (from Sales file). Safety Stock from Material Master.")

    pd_col1, pd_col2 = st.columns([2, 1])
    with pd_col1:
        prod_opts = [r["name"] for _, r in summary[summary.risk != "INSUFFICIENT_DATA"].iterrows()]
        sel_prod  = st.selectbox("Select product", prod_opts, key="cc_prod")
    with pd_col2:
        month_range = st.slider("Show last N months", 6, 60, 24, step=6, key="cc_months")

    sel_mat_id  = summary[summary.name == sel_prod]["material"].values[0]
    dh_cc       = get_demand_history(data, sel_mat_id)
    sh_cc       = get_stock_history(data, sel_mat_id)
    mat_row_cc  = summary[summary.material == sel_mat_id].iloc[0]
    ss_cc       = mat_row_cc["safety_stock"]
    repl_cc     = int(mat_row_cc["repl_quantity"])
    lt_cc       = float(mat_row_cc["lead_time"])
    lot_cc      = float(mat_row_cc["lot_size"])
    sih_cc      = float(mat_row_cc["sih"])

    sh_cc   = sh_cc.tail(month_range)
    dh_cc_f = dh_cc.tail(month_range)

    if len(sh_cc) > 0:
        fig_dd  = go.Figure()
        avg_d   = float(dh_cc_f[dh_cc_f.demand > 0]["demand"].mean()) if len(dh_cc_f[dh_cc_f.demand > 0]) > 0 else 0
        fig_dd.add_trace(go.Scatter(
            x=sh_cc["label"], y=sh_cc["Gross Stock"], mode="lines+markers", name="Stock (units)",
            line=dict(color=ORANGE, width=2.5), marker=dict(size=4, color=ORANGE),
            fill="tozeroy", fillcolor="rgba(244,123,37,0.08)", yaxis="y1",
            hovertemplate="<b>%{x}</b><br>Stock: %{y} units<extra></extra>",
        ))
        dem_aligned = dh_cc_f[dh_cc_f.label.isin(sh_cc["label"].tolist())]
        if len(dem_aligned) > 0:
            fig_dd.add_trace(go.Bar(
                x=dem_aligned["label"], y=dem_aligned["demand"], name="Demand/mo",
                marker_color="rgba(148,163,184,0.3)", marker_line_width=0, yaxis="y2",
                hovertemplate="<b>%{x}</b><br>Demand: %{y} units<extra></extra>",
            ))
        if ss_cc > 0:
            fig_dd.add_hline(y=ss_cc, line_color="#EF4444", line_dash="dot", line_width=1.5,
                             annotation_text="SAP SS " + str(round(ss_cc)) + "u",
                             annotation_font_color="#EF4444", annotation_font_size=9)
        ct(fig_dd, 240)
        fig_dd.update_layout(
            title=dict(text=sel_prod + " — Stock vs Demand (last " + str(month_range) + "mo)",
                       font=dict(size=11, color="#475569"), x=0),
            xaxis=dict(tickangle=-35),
            yaxis=dict(title="Stock (units)", gridcolor="#F0F4F9"),
            yaxis2=dict(title="Demand/mo", overlaying="y", side="right", showgrid=False),
            legend=dict(orientation="h", y=1.1),
            margin=dict(l=8, r=50, t=44, b=8),
        )
        st.plotly_chart(fig_dd, use_container_width=True)

    if repl_cc > 0:
        st.markdown(
            "<div class='prow' style='border-left:3px solid #EF4444;background:#FEF2F2;'>"
            "<div style='font-size:16px;'>⛔</div>"
            "<div style='flex:1;'>"
            "<div style='font-size:12px;font-weight:800;color:#EF4444;'>Replenishment Required</div>"
            "<div style='font-size:11px;color:#475569;margin-top:2px;'>"
            f"Stock-in-Hand: <strong>{round(sih_cc)}</strong> · SAP SS: <strong>{round(ss_cc)}</strong> · "
            f"Lead time: <strong>{round(lt_cc)}d</strong> (Material Master) · "
            f"Lot size: <strong>{round(lot_cc)}</strong>"
            "</div></div>"
            "<div style='text-align:right;'>"
            f"<div style='font-size:22px;font-weight:900;color:#EF4444;'>{repl_cc} units</div>"
            f"<div style='font-size:9px;color:#EF4444;'>CEILING({round(ss_cc-sih_cc)}/{round(lot_cc)})×{round(lot_cc)}</div>"
            "</div></div>",
            unsafe_allow_html=True,
        )

    st.markdown('<div class="pfooter">⚡ Powered by <strong>MResult</strong></div>', unsafe_allow_html=True)
