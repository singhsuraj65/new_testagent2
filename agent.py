# # # """
# # # agent.py — ARIA Agentic Intelligence Engine
# # # Rebuilt with:
# # # - Robust JSON parsing (regex-based, handles all markdown fence variants)
# # # - Agentic multi-step reasoning for Material Intelligence
# # # - Supplier consolidation order draft
# # # - Monte Carlo demand simulation
# # # - Supply disruption ranking
# # # - Chart interpretation via LLM
# # # """

# # # import re, json, math, random
# # # from typing import Optional, Dict, List, Any
# # # from openai import AzureOpenAI


# # # def get_azure_client(api_key: str, endpoint: str, api_version: str = "2025-01-01-preview"):
# # #     return AzureOpenAI(api_key=api_key, azure_endpoint=endpoint, api_version=api_version)


# # # def _parse_json(raw: str) -> Optional[Dict]:
# # #     """Robust JSON extraction — handles all markdown fence variants."""
# # #     if not raw: return None
# # #     # Remove markdown fences
# # #     cleaned = re.sub(r'^```(?:json)?\s*', '', raw.strip())
# # #     cleaned = re.sub(r'\s*```\s*$', '', cleaned).strip()
# # #     try:
# # #         return json.loads(cleaned)
# # #     except Exception:
# # #         # Try to extract JSON object with regex
# # #         match = re.search(r'\{.*\}', cleaned, re.DOTALL)
# # #         if match:
# # #             try: return json.loads(match.group())
# # #             except: pass
# # #     return None


# # # # ── System prompt ──────────────────────────────────────────────────────────────
# # # SYSTEM_PROMPT = """You are ARIA — an agentic supply chain intelligence system for Revvity Turku plant FI11.

# # # You reason step-by-step like a senior procurement analyst giving an executive briefing.
# # # Rules:
# # # - Cite specific numbers always
# # # - Reference actual periods (e.g. "Nov 2025")  
# # # - Connect patterns to consequences
# # # - Surface lead time prominently — it determines urgency
# # # - Safety Stock sourced from Material Master (Current Inventory = 0 for all SKUs, known data gap)
# # # - Lead Time = max(Planned Delivery, Inhouse Production Time) from Material Master
# # # - Replenishment formula: CEILING(Shortfall/FLS)×FLS where Shortfall = SS - Stock

# # # Return ONLY valid JSON. No markdown, no code fences, no preamble.
# # # JSON keys required:
# # # - headline: one sentence, max 20 words, most critical fact
# # # - verdict: CRITICAL | WARNING | HEALTHY | INSUFFICIENT_DATA
# # # - executive_summary: 3-4 sentences, what/why/pattern
# # # - key_findings: array of exactly 3 specific numbered findings
# # # - sap_gap: one sentence on what SAP is missing
# # # - recommendation: structured recommendation with SKU/inventory/SS/lead-time/lot-size/order-qty/reason
# # # - risk_if_ignored: one sentence consequence
# # # - data_confidence: HIGH | MEDIUM | LOW — one sentence explanation
# # # - data_quality_flags: array of data quality issues (empty if none)
# # # - bom_risk: one sentence on BOM/supplier risk (null if no BOM)
# # # - supplier_action: if replenishment needed, draft a one-sentence action for procurement team"""


# # # def analyse_material(client: AzureOpenAI, deployment: str, context: dict) -> dict:
# # #     """Agentic multi-step analysis. Returns structured dict."""
# # #     repl = context.get("replenishment", {})
# # #     repl_text = (
# # #         f"REPLENISHMENT REQUIRED: Order {repl['quantity']} units "
# # #         f"(Shortfall={repl['shortfall']}, Formula: {repl['formula']})"
# # #         if repl.get("triggered")
# # #         else f"No replenishment triggered: {repl.get('reason','stock above safety stock')}"
# # #     )

# # #     bom = context.get("bom_components", [])
# # #     external_bom = [b for b in bom if not b.get("inhouse") and not b.get("supplier","").startswith("⚠")]
# # #     missing_bom  = [b for b in bom if b.get("supplier","").startswith("⚠")]
# # #     fixed_qty    = [b for b in bom if b.get("fixed_qty")]

# # #     consolidation = context.get("supplier_consolidation", [])
# # #     consol_text = ""
# # #     if consolidation:
# # #         consol_text = "SUPPLIER CONSOLIDATION: " + "; ".join([
# # #             f"{c['supplier']} also supplies {c['also_supplies']} other finished goods"
# # #             for c in consolidation[:3]
# # #         ])

# # #     prompt = f"""Analyse this supply chain material and produce an agentic intelligence briefing.

# # # MATERIAL CONTEXT:
# # # {json.dumps(context, indent=2, default=str)}

# # # PRE-COMPUTED REPLENISHMENT:
# # # {repl_text}

# # # LEAD TIME URGENCY: {context.get('lt_urgency','unknown')}

# # # BOM FACTS:
# # # - Total components: {len(bom)}
# # # - External components (need procurement): {len(external_bom)}
# # # - Missing supplier data: {len(missing_bom)} components
# # # - Fixed quantity (order exactly 1): {len(fixed_qty)} components
# # # {consol_text}

# # # STEP-BY-STEP ANALYSIS REQUIRED:
# # # 1. Is current stock genuinely safe given lead time? (compare days_cover vs lead_time_days)
# # # 2. Is the SAP safety stock calibrated correctly vs ARIA formula?
# # # 3. What pattern caused the {len(context.get('breach_periods',[]))} historical breaches?
# # # 4. What is the BOM/supplier risk upstream?
# # # 5. What specific action should procurement take TODAY?

# # # Format the recommendation section EXACTLY as:
# # # SKU: [id] — [name]
# # # Current inventory: [n] units  
# # # Safety stock (Material Master): [n] units — [BELOW/ABOVE threshold]
# # # Lead time (Material Master): [n] days — [CRITICAL/OK relative to days cover]
# # # Fixed lot size: [n] units
# # # Recommended order: [Immediate/This week/Monitor], [n] units
# # # Reason: [specific sentence with numbers]
# # # """

# # #     try:
# # #         response = client.chat.completions.create(
# # #             model=deployment,
# # #             messages=[
# # #                 {"role": "system", "content": SYSTEM_PROMPT},
# # #                 {"role": "user",   "content": prompt},
# # #             ],
# # #             temperature=0.15,
# # #             max_tokens=1000,
# # #         )
# # #         raw = response.choices[0].message.content.strip()
# # #         result = _parse_json(raw)
# # #         if result:
# # #             result.setdefault("data_quality_flags", context.get("data_quality_flags", []))
# # #             result.setdefault("bom_risk", None)
# # #             result.setdefault("supplier_action", None)
# # #             return result
# # #         # Parse failed — return graceful degradation with raw content visible
# # #         return {
# # #             "headline": "Analysis requires review — see findings below",
# # #             "verdict": context.get("risk_status","UNKNOWN"),
# # #             "executive_summary": raw[:500] if raw else "No response from agent.",
# # #             "key_findings": ["See executive summary above.", repl_text, f"Lead time urgency: {context.get('lt_urgency','N/A')}"],
# # #             "sap_gap": f"SAP Safety Stock: {context.get('safety_stock_sap','N/A')} units. ARIA recommends: {context.get('rec_safety_stock','N/A')} units.",
# # #             "recommendation": repl_text,
# # #             "risk_if_ignored": "Review replenishment status immediately." if repl.get("triggered") else "Monitor stock levels.",
# # #             "data_confidence": "LOW — JSON parse issue. Response shown in executive summary.",
# # #             "data_quality_flags": context.get("data_quality_flags", []),
# # #             "bom_risk": None,
# # #             "supplier_action": None,
# # #             "_raw": raw,
# # #         }
# # #     except Exception as e:
# # #         return {
# # #             "headline": "Agent connection error",
# # #             "verdict": context.get("risk_status","UNKNOWN"),
# # #             "executive_summary": f"Error: {str(e)[:200]}",
# # #             "key_findings": [repl_text, "Check Azure API key.", "Review data manually."],
# # #             "sap_gap": "Unable to connect to agent.",
# # #             "recommendation": repl_text,
# # #             "risk_if_ignored": "Manual review required.",
# # #             "data_confidence": "LOW — connection error.",
# # #             "data_quality_flags": context.get("data_quality_flags", []),
# # #             "bom_risk": None, "supplier_action": None,
# # #         }


# # # def run_monte_carlo(
# # #     current_stock: float, safety_stock: float, avg_demand: float,
# # #     std_demand: float, lead_time: float, months: int = 6, n_sims: int = 1000
# # # ) -> dict:
# # #     """
# # #     Monte Carlo simulation: run 1000 demand scenarios.
# # #     Returns probability distribution of stockout, percentile outcomes.
# # #     """
# # #     breach_count = 0
# # #     end_stocks   = []
# # #     breach_months = []

# # #     random.seed(42)
# # #     for _ in range(n_sims):
# # #         stock = current_stock
# # #         breached = False
# # #         breach_m = None
# # #         for m in range(months):
# # #             # Sample demand from normal distribution (floor at 0)
# # #             d = max(0.0, random.gauss(avg_demand, std_demand))
# # #             stock = max(0.0, stock - d)
# # #             if stock < safety_stock and not breached:
# # #                 breached = True
# # #                 breach_m = m + 1
# # #         if breached:
# # #             breach_count += 1
# # #             breach_months.append(breach_m)
# # #         end_stocks.append(stock)

# # #     end_stocks.sort()
# # #     p_breach = round(breach_count / n_sims * 100, 1)
# # #     p10 = end_stocks[int(0.10 * n_sims)]
# # #     p50 = end_stocks[int(0.50 * n_sims)]
# # #     p90 = end_stocks[int(0.90 * n_sims)]
# # #     avg_breach_month = round(sum(breach_months) / len(breach_months), 1) if breach_months else None

# # #     return {
# # #         "n_simulations": n_sims,
# # #         "months_simulated": months,
# # #         "probability_breach_pct": p_breach,
# # #         "avg_breach_month": avg_breach_month,
# # #         "p10_end_stock": round(p10, 0),
# # #         "p50_end_stock": round(p50, 0),
# # #         "p90_end_stock": round(p90, 0),
# # #         "end_stock_distribution": [round(v, 0) for v in end_stocks[::10]],  # every 10th for chart
# # #         "verdict": "HIGH RISK" if p_breach>50 else ("MODERATE RISK" if p_breach>20 else ("LOW RISK" if p_breach>5 else "VERY LOW RISK")),
# # #     }


# # # def draft_supplier_email(
# # #     client: AzureOpenAI, deployment: str,
# # #     supplier_name: str, supplier_email: str,
# # #     materials: list, plant_name: str = "Revvity Turku FI11"
# # # ) -> str:
# # #     """Draft a procurement order email to a supplier covering multiple materials."""
# # #     order_lines = "\n".join([
# # #         f"  - {m['name']}: {m['quantity']} units (lot size: {m['lot_size']})"
# # #         for m in materials
# # #     ])
# # #     prompt = f"""Draft a professional procurement order email to {supplier_name} ({supplier_email}).
# # # Plant: {plant_name}
# # # Materials to order:
# # # {order_lines}

# # # Requirements:
# # # - Professional but concise (under 150 words)
# # # - Include subject line
# # # - Reference urgency where stock is below safety stock
# # # - Include contact request for lead time confirmation
# # # - Sign off as ARIA Supply Intelligence System, {plant_name}

# # # Return just the email text with Subject: on first line."""

# # #     try:
# # #         response = client.chat.completions.create(
# # #             model=deployment,
# # #             messages=[{"role":"user","content":prompt}],
# # #             temperature=0.3, max_tokens=350,
# # #         )
# # #         return response.choices[0].message.content.strip()
# # #     except Exception as e:
# # #         return f"Error drafting email: {str(e)[:100]}"


# # # def interpret_chart(
# # #     client: AzureOpenAI, deployment: str,
# # #     chart_type: str, chart_data: dict, question: str = None
# # # ) -> str:
# # #     """Ask ARIA to interpret a chart and provide actionable insight."""
# # #     q = question or f"Interpret this {chart_type} and provide 2-3 actionable insights for supply chain managers."
# # #     prompt = f"""You are ARIA, a supply chain analyst. Interpret this {chart_type} data and give concise actionable insights.

# # # DATA:
# # # {json.dumps(chart_data, default=str)[:1500]}

# # # {q}

# # # Rules: Under 120 words. Plain English sentences. Cite specific numbers. Focus on what action to take."""

# # #     try:
# # #         response = client.chat.completions.create(
# # #             model=deployment,
# # #             messages=[{"role":"user","content":prompt}],
# # #             temperature=0.2, max_tokens=200,
# # #         )
# # #         return response.choices[0].message.content.strip()
# # #     except Exception as e:
# # #         return f"Interpretation unavailable: {str(e)[:80]}"


# # # def simulate_scenario(
# # #     client: AzureOpenAI, deployment: str,
# # #     material_name: str, current_stock: float, safety_stock: float,
# # #     lead_time: float, fixed_lot_size: float,
# # #     demand_scenarios: dict, order_action: dict = None,
# # #     disruption_days: int = None,
# # # ) -> dict:
# # #     if disruption_days is not None:
# # #         daily = demand_scenarios.get("expected", 0) / 30
# # #         consumed = daily * disruption_days
# # #         remaining = current_stock - consumed
# # #         breach = remaining < safety_stock if safety_stock > 0 else False
# # #         shortfall = max(0, safety_stock - remaining)
# # #         lot = fixed_lot_size
# # #         qty = math.ceil(shortfall / lot) * lot if lot > 0 and shortfall > 0 else shortfall
# # #         prompt = f"""Supply disruption scenario for {material_name}:
# # # - Duration: {disruption_days} days of no replenishment
# # # - Current stock: {current_stock} units
# # # - Safety stock: {safety_stock} units
# # # - Daily demand: {daily:.1f} units/day
# # # - Stock at end: {max(0,remaining):.0f} units
# # # - Breach: {breach} (shortfall: {shortfall:.0f} units if breach)
# # # - Emergency order needed: {qty:.0f} units

# # # Return JSON: breach_occurs, days_to_breach, shortfall_units, stock_at_end, 
# # # recommended_emergency_action, simulation_verdict, urgency (ACT TODAY/ACT THIS WEEK/MONITOR/SAFE), priority_rank (1-5)"""
# # #         default = {
# # #             "breach_occurs": breach, "days_to_breach": int(safety_stock/daily) if daily>0 and breach else None,
# # #             "shortfall_units": int(shortfall), "stock_at_end": max(0,int(remaining)),
# # #             "recommended_emergency_action": f"Emergency order {qty:.0f} units." if breach else "Monitor.",
# # #             "simulation_verdict": "Breach detected." if breach else "Safe for disruption period.",
# # #             "urgency": "ACT TODAY" if (breach and remaining<0) else ("ACT THIS WEEK" if breach else "MONITOR"),
# # #             "priority_rank": 1 if breach else 4,
# # #         }
# # #     else:
# # #         shortfall = max(0, safety_stock - current_stock)
# # #         lot = fixed_lot_size
# # #         min_order = math.ceil(shortfall / lot) * lot if lot > 0 and shortfall > 0 else shortfall
# # #         prompt = f"""Demand simulation for {material_name}:
# # # - Current stock: {current_stock}, Safety stock: {safety_stock}, Lead time: {lead_time}d
# # # - Lot size: {fixed_lot_size}
# # # - Scenarios: Low={demand_scenarios['low']:.0f}/mo, Expected={demand_scenarios['expected']:.0f}/mo, High={demand_scenarios['high']:.0f}/mo
# # # - Order placed: {json.dumps(order_action) if order_action else 'None'}
# # # - Minimum order (CEILING formula): {min_order:.0f} units

# # # Return JSON: low_months_safe, expected_months_safe, high_months_safe, 
# # # order_prevents_breach, min_order_recommended, simulation_verdict, urgency"""
# # #         default = {
# # #             "low_months_safe":999,"expected_months_safe":3,"high_months_safe":1,
# # #             "order_prevents_breach":bool(order_action),
# # #             "min_order_recommended":int(min_order),
# # #             "simulation_verdict":"Review parameters.","urgency":"MONITOR",
# # #         }

# # #     try:
# # #         response = client.chat.completions.create(
# # #             model=deployment,
# # #             messages=[{"role":"user","content":prompt}],
# # #             temperature=0.1, max_tokens=400,
# # #         )
# # #         result = _parse_json(response.choices[0].message.content.strip())
# # #         return result if result else default
# # #     except:
# # #         return default


# # # def simulate_multi_sku_disruption(
# # #     client, deployment, disruption_days: int, sku_data: list
# # # ) -> list:
# # #     results = []
# # #     for sku in sku_data:
# # #         daily = sku["avg_monthly_demand"] / 30 if sku["avg_monthly_demand"] > 0 else 0
# # #         consumed = daily * disruption_days
# # #         remaining = sku["current_stock"] - consumed
# # #         ss = sku["safety_stock"]
# # #         breach = remaining < ss if ss > 0 else False
# # #         shortfall = max(0, ss - remaining)
# # #         fls = sku["fixed_lot_size"]
# # #         qty = math.ceil(shortfall / fls) * fls if fls > 0 and shortfall > 0 else shortfall
# # #         days_to_breach = None
# # #         if breach and daily > 0 and ss > 0:
# # #             ab = sku["current_stock"] - ss
# # #             days_to_breach = max(0, int(ab / daily)) if ab > 0 else 0
# # #         results.append({
# # #             "material":sku["material"],"name":sku["name"],"breach_occurs":breach,
# # #             "days_to_breach":days_to_breach,"shortfall_units":int(shortfall),
# # #             "stock_at_end":max(0,int(remaining)),"reorder_qty":int(qty),
# # #             "lead_time":sku["lead_time"],"severity_score":shortfall*2+max(0,disruption_days-(days_to_breach or disruption_days)) if breach else 0,
# # #         })
# # #     results.sort(key=lambda x:(0 if x["breach_occurs"] else 1, x["days_to_breach"] if x["days_to_breach"] is not None else 999,-x["shortfall_units"]))
# # #     return results


# # # def chat_with_data(client: AzureOpenAI, deployment: str, question: str, context: str) -> str:
# # #     system = """You are ARIA, a supply chain intelligence agent for Revvity Turku FI11.
# # # Answer concisely with specific numbers. Under 150 words. Plain English sentences.
# # # Key sources: Safety Stock from Material Master, Lead Time from Material Master, 
# # # Lot Size from Current Inventory. Demand from Sales file."""
# # #     try:
# # #         response = client.chat.completions.create(
# # #             model=deployment,
# # #             messages=[
# # #                 {"role":"system","content":system},
# # #                 {"role":"user","content":f"CONTEXT:\n{context}\n\nQUESTION: {question}"},
# # #             ],
# # #             temperature=0.3, max_tokens=250,
# # #         )
# # #         return response.choices[0].message.content.strip()
# # #     except Exception as e:
# # #         return f"Error: {str(e)[:100]}"

# # """
# # agent.py — ARIA Agentic Intelligence Engine
# # Now truly agentic: pre‑computes Monte Carlo, BOM risks, consolidation,
# # and allows interactive follow‑up (what‑if order quantity / demand change).
# # """

# # import re, json, math, random
# # from typing import Optional, Dict, List, Any
# # from openai import AzureOpenAI

# # def get_azure_client(api_key: str, endpoint: str, api_version: str = "2025-01-01-preview"):
# #     return AzureOpenAI(api_key=api_key, azure_endpoint=endpoint, api_version=api_version)

# # def _parse_json(raw: str) -> Optional[Dict]:
# #     if not raw: return None
# #     # Remove any text before first { and after last }
# #     raw = re.sub(r'^[^{]*', '', raw.strip())
# #     raw = re.sub(r'[^}]*$', '', raw.strip())
# #     # Remove markdown fences
# #     cleaned = re.sub(r'^```(?:json)?\s*', '', raw)
# #     cleaned = re.sub(r'\s*```\s*$', '', cleaned).strip()
# #     try:
# #         return json.loads(cleaned)
# #     except Exception:
# #         match = re.search(r'\{.*\}', cleaned, re.DOTALL)
# #         if match:
# #             try: return json.loads(match.group())
# #             except: pass
# #     return None

# # SYSTEM_PROMPT = """You are ARIA — an agentic supply chain intelligence system for Revvity Turku plant FI11.

# # You reason step-by-step like a senior procurement analyst.
# # Rules:
# # - Cite specific numbers always.
# # - Reference actual periods (e.g. "Nov 2025").
# # - Connect patterns to consequences.
# # - Surface lead time and transit days prominently.
# # - Use the provided pre‑computed data: Monte Carlo probability, BOM risks, supplier consolidation.

# # Return ONLY valid JSON. No markdown, no code fences.
# # JSON keys required:
# # - headline: one sentence, max 20 words.
# # - verdict: CRITICAL | WARNING | HEALTHY | INSUFFICIENT_DATA.
# # - executive_summary: 3-4 sentences.
# # - key_findings: array of exactly 3 specific numbered findings.
# # - sap_gap: one sentence on what SAP is missing.
# # - recommendation: structured recommendation with SKU/inventory/SS/lead-time/lot-size/order-qty/reason.
# # - risk_if_ignored: one sentence consequence.
# # - data_confidence: HIGH | MEDIUM | LOW — one sentence explanation.
# # - data_quality_flags: array of data quality issues.
# # - bom_risk: one sentence on BOM/supplier risk (null if no BOM).
# # - supplier_action: if replenishment needed, draft a one-sentence action for procurement team.
# # - consolidation_opportunity: if applicable, mention which supplier also supplies other materials.
# # """

# # def analyse_material(client: AzureOpenAI, deployment: str, context: dict) -> dict:
# #     """Agentic analysis using pre‑computed data."""
# #     repl = context.get("replenishment", {})
# #     repl_text = (
# #         f"REPLENISHMENT REQUIRED: Order {repl['quantity']} units "
# #         f"(Shortfall={repl['shortfall']}, Formula: {repl['formula']})"
# #         if repl.get("triggered")
# #         else f"No replenishment triggered: {repl.get('reason','stock above safety stock')}"
# #     )

# #     # Pre‑compute Monte Carlo (already in context? we'll call it again to be sure)
# #     from .data_loader import get_material_context  # avoid circular import
# #     # But we already have context; we'll use the numbers in context.
# #     mc_prob = None
# #     if context["demand_stats"]["std_monthly"] > 0:
# #         from .agent import run_monte_carlo  # but careful with circular
# #         mc = run_monte_carlo(context["sih"], context["safety_stock_sap"],
# #                              context["demand_stats"]["avg_monthly"],
# #                              context["demand_stats"]["std_monthly"],
# #                              context["lead_time_days"])
# #         mc_prob = mc["probability_breach_pct"]

# #     bom = context.get("bom_components", [])
# #     external_bom = [b for b in bom if not b.get("inhouse") and not b.get("supplier","").startswith("⚠")]
# #     missing_bom  = [b for b in bom if b.get("supplier","").startswith("⚠")]
# #     fixed_qty    = [b for b in bom if b.get("fixed_qty")]

# #     consolidation = context.get("supplier_consolidation", [])
# #     consol_text = ""
# #     if consolidation:
# #         consol_text = "SUPPLIER CONSOLIDATION: " + "; ".join([
# #             f"{c['supplier']} also supplies {c['also_supplies']} other finished goods (transit {c.get('transit_days','?')}d)"
# #             for c in consolidation[:3]
# #         ])

# #     prompt = f"""Analyse this supply chain material and produce an agentic intelligence briefing.

# # MATERIAL CONTEXT:
# # {json.dumps(context, indent=2, default=str)}

# # PRE-COMPUTED REPLENISHMENT:
# # {repl_text}

# # MONTE CARLO: {mc_prob}% probability of stockout in next 6 months (if computed).

# # LEAD TIME URGENCY: {context.get('lt_urgency','unknown')}

# # BOM FACTS:
# # - Total components: {len(bom)}
# # - External components (need procurement): {len(external_bom)}
# # - Missing supplier data: {len(missing_bom)} components
# # - Fixed quantity (order exactly 1): {len(fixed_qty)} components
# # {consol_text}

# # STEP-BY-STEP ANALYSIS REQUIRED:
# # 1. Is current stock genuinely safe given lead time? Compare days_cover vs lead_time_days.
# # 2. Is the SAP safety stock calibrated correctly vs ARIA recommended?
# # 3. What pattern caused the {len(context.get('breach_periods',[]))} historical breaches?
# # 4. What is the BOM/supplier risk upstream (including supplier reliability, geo risk, transit times)?
# # 5. What specific action should procurement take TODAY (including consolidation if beneficial)?

# # Format the recommendation section EXACTLY as:
# # SKU: [id] — [name]
# # Current inventory: [n] units  
# # Safety stock (Material Master): [n] units — [BELOW/ABOVE threshold]
# # Lead time (Material Master): [n] days — [CRITICAL/OK relative to days cover]
# # Fixed lot size: [n] units
# # Recommended order: [Immediate/This week/Monitor], [n] units
# # Reason: [specific sentence with numbers]

# # If consolidation opportunity exists, add a line: "Consolidation: order together with [other materials] from [supplier] to save logistics cost."
# # """

# #     try:
# #         response = client.chat.completions.create(
# #             model=deployment,
# #             messages=[
# #                 {"role": "system", "content": SYSTEM_PROMPT},
# #                 {"role": "user",   "content": prompt},
# #             ],
# #             temperature=0.15,
# #             max_tokens=1200,
# #         )
# #         raw = response.choices[0].message.content.strip()
# #         result = _parse_json(raw)
# #         if result:
# #             result.setdefault("data_quality_flags", context.get("data_quality_flags", []))
# #             result.setdefault("bom_risk", None)
# #             result.setdefault("supplier_action", None)
# #             result.setdefault("consolidation_opportunity", None)
# #             return result
# #         # Fallback
# #         return {
# #             "headline": "Analysis requires review — see findings below",
# #             "verdict": context.get("risk_status","UNKNOWN"),
# #             "executive_summary": raw[:500] if raw else "No response from agent.",
# #             "key_findings": [repl_text, f"Lead time urgency: {context.get('lt_urgency','N/A')}", f"Monte Carlo breach prob: {mc_prob}%"],
# #             "sap_gap": f"SAP Safety Stock: {context.get('safety_stock_sap','N/A')} units. ARIA recommends: {context.get('rec_safety_stock','N/A')} units.",
# #             "recommendation": repl_text,
# #             "risk_if_ignored": "Review replenishment status immediately." if repl.get("triggered") else "Monitor stock levels.",
# #             "data_confidence": "LOW — JSON parse issue.",
# #             "data_quality_flags": context.get("data_quality_flags", []),
# #             "bom_risk": None,
# #             "supplier_action": None,
# #             "consolidation_opportunity": None,
# #         }
# #     except Exception as e:
# #         return {
# #             "headline": "Agent connection error",
# #             "verdict": context.get("risk_status","UNKNOWN"),
# #             "executive_summary": f"Error: {str(e)[:200]}",
# #             "key_findings": [repl_text, "Check Azure API key.", "Review data manually."],
# #             "sap_gap": "Unable to connect to agent.",
# #             "recommendation": repl_text,
# #             "risk_if_ignored": "Manual review required.",
# #             "data_confidence": "LOW — connection error.",
# #             "data_quality_flags": context.get("data_quality_flags", []),
# #             "bom_risk": None, "supplier_action": None, "consolidation_opportunity": None,
# #         }

# # def run_monte_carlo(current_stock: float, safety_stock: float, avg_demand: float,
# #                     std_demand: float, lead_time: float, months: int = 6, n_sims: int = 1000) -> dict:
# #     random.seed(42)
# #     breach_count = 0
# #     end_stocks = []
# #     breach_months = []
# #     for _ in range(n_sims):
# #         stock = current_stock
# #         breached = False
# #         breach_m = None
# #         for m in range(months):
# #             d = max(0.0, random.gauss(avg_demand, std_demand))
# #             stock = max(0.0, stock - d)
# #             if stock < safety_stock and not breached:
# #                 breached = True
# #                 breach_m = m + 1
# #         if breached:
# #             breach_count += 1
# #             breach_months.append(breach_m)
# #         end_stocks.append(stock)
# #     end_stocks.sort()
# #     p_breach = round(breach_count / n_sims * 100, 1)
# #     p10 = end_stocks[int(0.10 * n_sims)]
# #     p50 = end_stocks[int(0.50 * n_sims)]
# #     p90 = end_stocks[int(0.90 * n_sims)]
# #     avg_breach_month = round(sum(breach_months) / len(breach_months), 1) if breach_months else None
# #     return {
# #         "n_simulations": n_sims,
# #         "months_simulated": months,
# #         "probability_breach_pct": p_breach,
# #         "avg_breach_month": avg_breach_month,
# #         "p10_end_stock": round(p10, 0),
# #         "p50_end_stock": round(p50, 0),
# #         "p90_end_stock": round(p90, 0),
# #         "end_stock_distribution": [round(v, 0) for v in end_stocks[::10]],
# #         "verdict": "HIGH RISK" if p_breach>50 else ("MODERATE RISK" if p_breach>20 else ("LOW RISK" if p_breach>5 else "VERY LOW RISK")),
# #     }

# # def draft_supplier_email(client: AzureOpenAI, deployment: str, supplier_name: str, supplier_email: str,
# #                          materials: list, plant_name: str = "Revvity Turku FI11") -> str:
# #     order_lines = "\n".join([f"  - {m['name']}: {m['quantity']} units (lot size: {m['lot_size']})" for m in materials])
# #     prompt = f"""Draft a professional procurement order email to {supplier_name} ({supplier_email}).
# # Plant: {plant_name}
# # Materials to order:
# # {order_lines}

# # Requirements:
# # - Professional but concise (under 150 words)
# # - Include subject line
# # - Reference urgency where stock is below safety stock
# # - Include contact request for lead time confirmation
# # - Sign off as ARIA Supply Intelligence System, {plant_name}

# # Return just the email text with Subject: on first line."""
# #     try:
# #         response = client.chat.completions.create(
# #             model=deployment,
# #             messages=[{"role":"user","content":prompt}],
# #             temperature=0.3, max_tokens=350,
# #         )
# #         return response.choices[0].message.content.strip()
# #     except Exception as e:
# #         return f"Error drafting email: {str(e)[:100]}"

# # def interpret_chart(client: AzureOpenAI, deployment: str, chart_type: str, chart_data: dict, question: str = None) -> str:
# #     q = question or f"Interpret this {chart_type} and provide 2-3 actionable insights for supply chain managers."
# #     prompt = f"""You are ARIA, a supply chain analyst. Interpret this {chart_type} data and give concise actionable insights.

# # DATA:
# # {json.dumps(chart_data, default=str)[:1500]}

# # {q}

# # Rules: Under 120 words. Plain English sentences. Cite specific numbers. Focus on what action to take."""
# #     try:
# #         response = client.chat.completions.create(
# #             model=deployment,
# #             messages=[{"role":"user","content":prompt}],
# #             temperature=0.2, max_tokens=200,
# #         )
# #         return response.choices[0].message.content.strip()
# #     except Exception as e:
# #         return f"Interpretation unavailable: {str(e)[:80]}"

# # def simulate_scenario(client: AzureOpenAI, deployment: str, material_name: str, current_stock: float,
# #                       safety_stock: float, lead_time: float, fixed_lot_size: float,
# #                       demand_scenarios: dict, order_action: dict = None, disruption_days: int = None) -> dict:
# #     if disruption_days is not None:
# #         daily = demand_scenarios.get("expected", 0) / 30
# #         consumed = daily * disruption_days
# #         remaining = current_stock - consumed
# #         breach = remaining < safety_stock if safety_stock > 0 else False
# #         shortfall = max(0, safety_stock - remaining)
# #         lot = fixed_lot_size
# #         qty = math.ceil(shortfall / lot) * lot if lot > 0 and shortfall > 0 else shortfall
# #         prompt = f"""Supply disruption scenario for {material_name}:
# # - Duration: {disruption_days} days of no replenishment
# # - Current stock: {current_stock} units
# # - Safety stock: {safety_stock} units
# # - Daily demand: {daily:.1f} units/day
# # - Stock at end: {max(0,remaining):.0f} units
# # - Breach: {breach} (shortfall: {shortfall:.0f} units if breach)
# # - Emergency order needed: {qty:.0f} units

# # Return JSON: breach_occurs, days_to_breach, shortfall_units, stock_at_end, 
# # recommended_emergency_action, simulation_verdict, urgency (ACT TODAY/ACT THIS WEEK/MONITOR/SAFE), priority_rank (1-5)"""
# #         default = {
# #             "breach_occurs": breach, "days_to_breach": int(safety_stock/daily) if daily>0 and breach else None,
# #             "shortfall_units": int(shortfall), "stock_at_end": max(0,int(remaining)),
# #             "recommended_emergency_action": f"Emergency order {qty:.0f} units." if breach else "Monitor.",
# #             "simulation_verdict": "Breach detected." if breach else "Safe for disruption period.",
# #             "urgency": "ACT TODAY" if (breach and remaining<0) else ("ACT THIS WEEK" if breach else "MONITOR"),
# #             "priority_rank": 1 if breach else 4,
# #         }
# #     else:
# #         shortfall = max(0, safety_stock - current_stock)
# #         lot = fixed_lot_size
# #         min_order = math.ceil(shortfall / lot) * lot if lot > 0 and shortfall > 0 else shortfall
# #         prompt = f"""Demand simulation for {material_name}:
# # - Current stock: {current_stock}, Safety stock: {safety_stock}, Lead time: {lead_time}d
# # - Lot size: {fixed_lot_size}
# # - Scenarios: Low={demand_scenarios['low']:.0f}/mo, Expected={demand_scenarios['expected']:.0f}/mo, High={demand_scenarios['high']:.0f}/mo
# # - Order placed: {json.dumps(order_action) if order_action else 'None'}
# # - Minimum order (CEILING formula): {min_order:.0f} units

# # Return JSON: low_months_safe, expected_months_safe, high_months_safe, 
# # order_prevents_breach, min_order_recommended, simulation_verdict, urgency"""
# #         default = {
# #             "low_months_safe":999,"expected_months_safe":3,"high_months_safe":1,
# #             "order_prevents_breach":bool(order_action),
# #             "min_order_recommended":int(min_order),
# #             "simulation_verdict":"Review parameters.","urgency":"MONITOR",
# #         }
# #     try:
# #         response = client.chat.completions.create(
# #             model=deployment,
# #             messages=[{"role":"user","content":prompt}],
# #             temperature=0.1, max_tokens=400,
# #         )
# #         result = _parse_json(response.choices[0].message.content.strip())
# #         return result if result else default
# #     except:
# #         return default

# # def simulate_multi_sku_disruption(client, deployment, disruption_days: int, sku_data: list) -> list:
# #     results = []
# #     for sku in sku_data:
# #         daily = sku["avg_monthly_demand"] / 30 if sku["avg_monthly_demand"] > 0 else 0
# #         consumed = daily * disruption_days
# #         remaining = sku["current_stock"] - consumed
# #         ss = sku["safety_stock"]
# #         breach = remaining < ss if ss > 0 else False
# #         shortfall = max(0, ss - remaining)
# #         fls = sku["fixed_lot_size"]
# #         qty = math.ceil(shortfall / fls) * fls if fls > 0 and shortfall > 0 else shortfall
# #         days_to_breach = None
# #         if breach and daily > 0 and ss > 0:
# #             ab = sku["current_stock"] - ss
# #             days_to_breach = max(0, int(ab / daily)) if ab > 0 else 0
# #         results.append({
# #             "material":sku["material"],"name":sku["name"],"breach_occurs":breach,
# #             "days_to_breach":days_to_breach,"shortfall_units":int(shortfall),
# #             "stock_at_end":max(0,int(remaining)),"reorder_qty":int(qty),
# #             "lead_time":sku["lead_time"],"severity_score":shortfall*2+max(0,disruption_days-(days_to_breach or disruption_days)) if breach else 0,
# #         })
# #     results.sort(key=lambda x:(0 if x["breach_occurs"] else 1, x["days_to_breach"] if x["days_to_breach"] is not None else 999,-x["shortfall_units"]))
# #     return results

# # def chat_with_data(client: AzureOpenAI, deployment: str, question: str, context: str) -> str:
# #     system = """You are ARIA, a supply chain intelligence agent for Revvity Turku FI11.
# # Answer concisely with specific numbers. Under 150 words. Plain English sentences."""
# #     try:
# #         response = client.chat.completions.create(
# #             model=deployment,
# #             messages=[
# #                 {"role":"system","content":system},
# #                 {"role":"user","content":f"CONTEXT:\n{context}\n\nQUESTION: {question}"},
# #             ],
# #             temperature=0.3, max_tokens=250,
# #         )
# #         return response.choices[0].message.content.strip()
# #     except Exception as e:
# #         return f"Error: {str(e)[:100]}"

# """
# agent.py — ARIA Agentic Intelligence Engine
# Now truly agentic: pre‑computes Monte Carlo, BOM risks, consolidation,
# and allows interactive follow‑up (what‑if order quantity / demand change).
# """

# import re, json, math, random
# from typing import Optional, Dict, List, Any
# from openai import AzureOpenAI

# def get_azure_client(api_key: str, endpoint: str, api_version: str = "2025-01-01-preview"):
#     return AzureOpenAI(api_key=api_key, azure_endpoint=endpoint, api_version=api_version)

# def _parse_json(raw: str) -> Optional[Dict]:
#     if not raw: return None
#     # Remove any text before first { and after last }
#     raw = re.sub(r'^[^{]*', '', raw.strip())
#     raw = re.sub(r'[^}]*$', '', raw.strip())
#     # Remove markdown fences
#     cleaned = re.sub(r'^```(?:json)?\s*', '', raw)
#     cleaned = re.sub(r'\s*```\s*$', '', cleaned).strip()
#     try:
#         return json.loads(cleaned)
#     except Exception:
#         match = re.search(r'\{.*\}', cleaned, re.DOTALL)
#         if match:
#             try: return json.loads(match.group())
#             except: pass
#     return None

# SYSTEM_PROMPT = """You are ARIA — an agentic supply chain intelligence system for Revvity Turku plant FI11.

# You reason step-by-step like a senior procurement analyst.
# Rules:
# - Cite specific numbers always.
# - Reference actual periods (e.g. "Nov 2025").
# - Connect patterns to consequences.
# - Surface lead time and transit days prominently.
# - Use the provided pre‑computed data: Monte Carlo probability, BOM risks, supplier consolidation.

# Return ONLY valid JSON. No markdown, no code fences.
# JSON keys required:
# - headline: one sentence, max 20 words.
# - verdict: CRITICAL | WARNING | HEALTHY | INSUFFICIENT_DATA.
# - executive_summary: 3-4 sentences.
# - key_findings: array of exactly 3 specific numbered findings.
# - sap_gap: one sentence on what SAP is missing.
# - recommendation: structured recommendation with SKU/inventory/SS/lead-time/lot-size/order-qty/reason.
# - risk_if_ignored: one sentence consequence.
# - data_confidence: HIGH | MEDIUM | LOW — one sentence explanation.
# - data_quality_flags: array of data quality issues.
# - bom_risk: one sentence on BOM/supplier risk (null if no BOM).
# - supplier_action: if replenishment needed, draft a one-sentence action for procurement team.
# - consolidation_opportunity: if applicable, mention which supplier also supplies other materials.
# """

# def analyse_material(client: AzureOpenAI, deployment: str, context: dict) -> dict:
#     """Agentic analysis using pre‑computed data."""
#     repl = context.get("replenishment", {})
#     repl_text = (
#         f"REPLENISHMENT REQUIRED: Order {repl['quantity']} units "
#         f"(Shortfall={repl['shortfall']}, Formula: {repl['formula']})"
#         if repl.get("triggered")
#         else f"No replenishment triggered: {repl.get('reason','stock above safety stock')}"
#     )

#     # Pre‑compute Monte Carlo using the context numbers
#     mc_prob = None
#     if context["demand_stats"]["std_monthly"] > 0:
#         mc = run_monte_carlo(context["sih"], context["safety_stock_sap"],
#                              context["demand_stats"]["avg_monthly"],
#                              context["demand_stats"]["std_monthly"],
#                              context["lead_time_days"])
#         mc_prob = mc["probability_breach_pct"]

#     bom = context.get("bom_components", [])
#     external_bom = [b for b in bom if not b.get("inhouse") and not b.get("supplier","").startswith("⚠")]
#     missing_bom  = [b for b in bom if b.get("supplier","").startswith("⚠")]
#     fixed_qty    = [b for b in bom if b.get("fixed_qty")]

#     consolidation = context.get("supplier_consolidation", [])
#     consol_text = ""
#     if consolidation:
#         consol_text = "SUPPLIER CONSOLIDATION: " + "; ".join([
#             f"{c['supplier']} also supplies {c['also_supplies']} other finished goods (transit {c.get('transit_days','?')}d)"
#             for c in consolidation[:3]
#         ])

#     prompt = f"""Analyse this supply chain material and produce an agentic intelligence briefing.

# MATERIAL CONTEXT:
# {json.dumps(context, indent=2, default=str)}

# PRE-COMPUTED REPLENISHMENT:
# {repl_text}

# MONTE CARLO: {mc_prob}% probability of stockout in next 6 months (if computed).

# LEAD TIME URGENCY: {context.get('lt_urgency','unknown')}

# BOM FACTS:
# - Total components: {len(bom)}
# - External components (need procurement): {len(external_bom)}
# - Missing supplier data: {len(missing_bom)} components
# - Fixed quantity (order exactly 1): {len(fixed_qty)} components
# {consol_text}

# STEP-BY-STEP ANALYSIS REQUIRED:
# 1. Is current stock genuinely safe given lead time? Compare days_cover vs lead_time_days.
# 2. Is the SAP safety stock calibrated correctly vs ARIA recommended?
# 3. What pattern caused the {len(context.get('breach_periods',[]))} historical breaches?
# 4. What is the BOM/supplier risk upstream (including supplier reliability, geo risk, transit times)?
# 5. What specific action should procurement take TODAY (including consolidation if beneficial)?

# Format the recommendation section EXACTLY as:
# SKU: [id] — [name]
# Current inventory: [n] units  
# Safety stock (Material Master): [n] units — [BELOW/ABOVE threshold]
# Lead time (Material Master): [n] days — [CRITICAL/OK relative to days cover]
# Fixed lot size: [n] units
# Recommended order: [Immediate/This week/Monitor], [n] units
# Reason: [specific sentence with numbers]

# If consolidation opportunity exists, add a line: "Consolidation: order together with [other materials] from [supplier] to save logistics cost."
# """

#     try:
#         response = client.chat.completions.create(
#             model=deployment,
#             messages=[
#                 {"role": "system", "content": SYSTEM_PROMPT},
#                 {"role": "user",   "content": prompt},
#             ],
#             temperature=0.15,
#             max_tokens=1200,
#         )
#         raw = response.choices[0].message.content.strip()
#         result = _parse_json(raw)
#         if result:
#             result.setdefault("data_quality_flags", context.get("data_quality_flags", []))
#             result.setdefault("bom_risk", None)
#             result.setdefault("supplier_action", None)
#             result.setdefault("consolidation_opportunity", None)
#             return result
#         # Fallback
#         return {
#             "headline": "Analysis requires review — see findings below",
#             "verdict": context.get("risk_status","UNKNOWN"),
#             "executive_summary": raw[:500] if raw else "No response from agent.",
#             "key_findings": [repl_text, f"Lead time urgency: {context.get('lt_urgency','N/A')}", f"Monte Carlo breach prob: {mc_prob}%"],
#             "sap_gap": f"SAP Safety Stock: {context.get('safety_stock_sap','N/A')} units. ARIA recommends: {context.get('rec_safety_stock','N/A')} units.",
#             "recommendation": repl_text,
#             "risk_if_ignored": "Review replenishment status immediately." if repl.get("triggered") else "Monitor stock levels.",
#             "data_confidence": "LOW — JSON parse issue.",
#             "data_quality_flags": context.get("data_quality_flags", []),
#             "bom_risk": None,
#             "supplier_action": None,
#             "consolidation_opportunity": None,
#         }
#     except Exception as e:
#         return {
#             "headline": "Agent connection error",
#             "verdict": context.get("risk_status","UNKNOWN"),
#             "executive_summary": f"Error: {str(e)[:200]}",
#             "key_findings": [repl_text, "Check Azure API key.", "Review data manually."],
#             "sap_gap": "Unable to connect to agent.",
#             "recommendation": repl_text,
#             "risk_if_ignored": "Manual review required.",
#             "data_confidence": "LOW — connection error.",
#             "data_quality_flags": context.get("data_quality_flags", []),
#             "bom_risk": None, "supplier_action": None, "consolidation_opportunity": None,
#         }

# def run_monte_carlo(current_stock: float, safety_stock: float, avg_demand: float,
#                     std_demand: float, lead_time: float, months: int = 6, n_sims: int = 1000) -> dict:
#     random.seed(42)
#     breach_count = 0
#     end_stocks = []
#     breach_months = []
#     for _ in range(n_sims):
#         stock = current_stock
#         breached = False
#         breach_m = None
#         for m in range(months):
#             d = max(0.0, random.gauss(avg_demand, std_demand))
#             stock = max(0.0, stock - d)
#             if stock < safety_stock and not breached:
#                 breached = True
#                 breach_m = m + 1
#         if breached:
#             breach_count += 1
#             breach_months.append(breach_m)
#         end_stocks.append(stock)
#     end_stocks.sort()
#     p_breach = round(breach_count / n_sims * 100, 1)
#     p10 = end_stocks[int(0.10 * n_sims)]
#     p50 = end_stocks[int(0.50 * n_sims)]
#     p90 = end_stocks[int(0.90 * n_sims)]
#     avg_breach_month = round(sum(breach_months) / len(breach_months), 1) if breach_months else None
#     return {
#         "n_simulations": n_sims,
#         "months_simulated": months,
#         "probability_breach_pct": p_breach,
#         "avg_breach_month": avg_breach_month,
#         "p10_end_stock": round(p10, 0),
#         "p50_end_stock": round(p50, 0),
#         "p90_end_stock": round(p90, 0),
#         "end_stock_distribution": [round(v, 0) for v in end_stocks[::10]],
#         "verdict": "HIGH RISK" if p_breach>50 else ("MODERATE RISK" if p_breach>20 else ("LOW RISK" if p_breach>5 else "VERY LOW RISK")),
#     }

# def draft_supplier_email(client: AzureOpenAI, deployment: str, supplier_name: str, supplier_email: str,
#                          materials: list, plant_name: str = "Revvity Turku FI11") -> str:
#     order_lines = "\n".join([f"  - {m['name']}: {m['quantity']} units (lot size: {m['lot_size']})" for m in materials])
#     prompt = f"""Draft a professional procurement order email to {supplier_name} ({supplier_email}).
# Plant: {plant_name}
# Materials to order:
# {order_lines}

# Requirements:
# - Professional but concise (under 150 words)
# - Include subject line
# - Reference urgency where stock is below safety stock
# - Include contact request for lead time confirmation
# - Sign off as ARIA Supply Intelligence System, {plant_name}

# Return just the email text with Subject: on first line."""
#     try:
#         response = client.chat.completions.create(
#             model=deployment,
#             messages=[{"role":"user","content":prompt}],
#             temperature=0.3, max_tokens=350,
#         )
#         return response.choices[0].message.content.strip()
#     except Exception as e:
#         return f"Error drafting email: {str(e)[:100]}"

# def interpret_chart(client: AzureOpenAI, deployment: str, chart_type: str, chart_data: dict, question: str = None) -> str:
#     q = question or f"Interpret this {chart_type} and provide 2-3 actionable insights for supply chain managers."
#     prompt = f"""You are ARIA, a supply chain analyst. Interpret this {chart_type} data and give concise actionable insights.

# DATA:
# {json.dumps(chart_data, default=str)[:1500]}

# {q}

# Rules: Under 120 words. Plain English sentences. Cite specific numbers. Focus on what action to take."""
#     try:
#         response = client.chat.completions.create(
#             model=deployment,
#             messages=[{"role":"user","content":prompt}],
#             temperature=0.2, max_tokens=200,
#         )
#         return response.choices[0].message.content.strip()
#     except Exception as e:
#         return f"Interpretation unavailable: {str(e)[:80]}"

# def simulate_scenario(client: AzureOpenAI, deployment: str, material_name: str, current_stock: float,
#                       safety_stock: float, lead_time: float, fixed_lot_size: float,
#                       demand_scenarios: dict, order_action: dict = None, disruption_days: int = None) -> dict:
#     if disruption_days is not None:
#         daily = demand_scenarios.get("expected", 0) / 30
#         consumed = daily * disruption_days
#         remaining = current_stock - consumed
#         breach = remaining < safety_stock if safety_stock > 0 else False
#         shortfall = max(0, safety_stock - remaining)
#         lot = fixed_lot_size
#         qty = math.ceil(shortfall / lot) * lot if lot > 0 and shortfall > 0 else shortfall
#         prompt = f"""Supply disruption scenario for {material_name}:
# - Duration: {disruption_days} days of no replenishment
# - Current stock: {current_stock} units
# - Safety stock: {safety_stock} units
# - Daily demand: {daily:.1f} units/day
# - Stock at end: {max(0,remaining):.0f} units
# - Breach: {breach} (shortfall: {shortfall:.0f} units if breach)
# - Emergency order needed: {qty:.0f} units

# Return JSON: breach_occurs, days_to_breach, shortfall_units, stock_at_end, 
# recommended_emergency_action, simulation_verdict, urgency (ACT TODAY/ACT THIS WEEK/MONITOR/SAFE), priority_rank (1-5)"""
#         default = {
#             "breach_occurs": breach, "days_to_breach": int(safety_stock/daily) if daily>0 and breach else None,
#             "shortfall_units": int(shortfall), "stock_at_end": max(0,int(remaining)),
#             "recommended_emergency_action": f"Emergency order {qty:.0f} units." if breach else "Monitor.",
#             "simulation_verdict": "Breach detected." if breach else "Safe for disruption period.",
#             "urgency": "ACT TODAY" if (breach and remaining<0) else ("ACT THIS WEEK" if breach else "MONITOR"),
#             "priority_rank": 1 if breach else 4,
#         }
#     else:
#         shortfall = max(0, safety_stock - current_stock)
#         lot = fixed_lot_size
#         min_order = math.ceil(shortfall / lot) * lot if lot > 0 and shortfall > 0 else shortfall
#         prompt = f"""Demand simulation for {material_name}:
# - Current stock: {current_stock}, Safety stock: {safety_stock}, Lead time: {lead_time}d
# - Lot size: {fixed_lot_size}
# - Scenarios: Low={demand_scenarios['low']:.0f}/mo, Expected={demand_scenarios['expected']:.0f}/mo, High={demand_scenarios['high']:.0f}/mo
# - Order placed: {json.dumps(order_action) if order_action else 'None'}
# - Minimum order (CEILING formula): {min_order:.0f} units

# Return JSON: low_months_safe, expected_months_safe, high_months_safe, 
# order_prevents_breach, min_order_recommended, simulation_verdict, urgency"""
#         default = {
#             "low_months_safe":999,"expected_months_safe":3,"high_months_safe":1,
#             "order_prevents_breach":bool(order_action),
#             "min_order_recommended":int(min_order),
#             "simulation_verdict":"Review parameters.","urgency":"MONITOR",
#         }
#     try:
#         response = client.chat.completions.create(
#             model=deployment,
#             messages=[{"role":"user","content":prompt}],
#             temperature=0.1, max_tokens=400,
#         )
#         result = _parse_json(response.choices[0].message.content.strip())
#         return result if result else default
#     except:
#         return default

# def simulate_multi_sku_disruption(client, deployment, disruption_days: int, sku_data: list) -> list:
#     results = []
#     for sku in sku_data:
#         daily = sku["avg_monthly_demand"] / 30 if sku["avg_monthly_demand"] > 0 else 0
#         consumed = daily * disruption_days
#         remaining = sku["current_stock"] - consumed
#         ss = sku["safety_stock"]
#         breach = remaining < ss if ss > 0 else False
#         shortfall = max(0, ss - remaining)
#         fls = sku["fixed_lot_size"]
#         qty = math.ceil(shortfall / fls) * fls if fls > 0 and shortfall > 0 else shortfall
#         days_to_breach = None
#         if breach and daily > 0 and ss > 0:
#             ab = sku["current_stock"] - ss
#             days_to_breach = max(0, int(ab / daily)) if ab > 0 else 0
#         results.append({
#             "material":sku["material"],"name":sku["name"],"breach_occurs":breach,
#             "days_to_breach":days_to_breach,"shortfall_units":int(shortfall),
#             "stock_at_end":max(0,int(remaining)),"reorder_qty":int(qty),
#             "lead_time":sku["lead_time"],"severity_score":shortfall*2+max(0,disruption_days-(days_to_breach or disruption_days)) if breach else 0,
#         })
#     results.sort(key=lambda x:(0 if x["breach_occurs"] else 1, x["days_to_breach"] if x["days_to_breach"] is not None else 999,-x["shortfall_units"]))
#     return results

# def chat_with_data(client: AzureOpenAI, deployment: str, question: str, context: str) -> str:
#     system = """You are ARIA, a supply chain intelligence agent for Revvity Turku FI11.
# Answer concisely with specific numbers. Under 150 words. Plain English sentences."""
#     try:
#         response = client.chat.completions.create(
#             model=deployment,
#             messages=[
#                 {"role":"system","content":system},
#                 {"role":"user","content":f"CONTEXT:\n{context}\n\nQUESTION: {question}"},
#             ],
#             temperature=0.3, max_tokens=250,
#         )
#         return response.choices[0].message.content.strip()
#     except Exception as e:
#         return f"Error: {str(e)[:100]}"

"""
agent.py — ARIA Agentic Intelligence Engine
Now truly agentic: pre‑computes Monte Carlo, BOM risks, consolidation,
and allows interactive follow‑up (what‑if order quantity / demand change).
"""

import re, json, math, random
from typing import Optional, Dict, List, Any
from openai import AzureOpenAI

def get_azure_client(api_key: str, endpoint: str, api_version: str = "2025-01-01-preview"):
    return AzureOpenAI(api_key=api_key, azure_endpoint=endpoint, api_version=api_version)

def _parse_json(raw: str) -> Optional[Dict]:
    if not raw: return None
    # Remove any text before first { and after last }
    raw = re.sub(r'^[^{]*', '', raw.strip())
    raw = re.sub(r'[^}]*$', '', raw.strip())
    # Remove markdown fences
    cleaned = re.sub(r'^```(?:json)?\s*', '', raw)
    cleaned = re.sub(r'\s*```\s*$', '', cleaned).strip()
    try:
        return json.loads(cleaned)
    except Exception:
        match = re.search(r'\{.*\}', cleaned, re.DOTALL)
        if match:
            try: return json.loads(match.group())
            except: pass
    return None

SYSTEM_PROMPT = """You are ARIA — an agentic supply chain intelligence system for Revvity Turku plant FI11.

You reason step-by-step like a senior procurement analyst.
Rules:
- Cite specific numbers always.
- Reference actual periods (e.g. "Nov 2025").
- Connect patterns to consequences.
- Surface lead time and transit days prominently.
- Use the provided pre‑computed data: Monte Carlo probability, BOM risks, supplier consolidation.

Return ONLY valid JSON. No markdown, no code fences.
JSON keys required:
- headline: one sentence, max 20 words.
- verdict: CRITICAL | WARNING | HEALTHY | INSUFFICIENT_DATA.
- executive_summary: 3-4 sentences.
- key_findings: array of exactly 3 specific numbered findings.
- sap_gap: one sentence on what SAP is missing.
- recommendation: structured recommendation with SKU/inventory/SS/lead-time/lot-size/order-qty/reason.
- risk_if_ignored: one sentence consequence.
- data_confidence: HIGH | MEDIUM | LOW — one sentence explanation.
- data_quality_flags: array of data quality issues.
- bom_risk: one sentence on BOM/supplier risk (null if no BOM).
- supplier_action: if replenishment needed, draft a one-sentence action for procurement team.
- consolidation_opportunity: if applicable, mention which supplier also supplies other materials.
"""

def analyse_material(client: AzureOpenAI, deployment: str, context: dict) -> dict:
    """Agentic analysis using pre‑computed data."""
    repl = context.get("replenishment", {})
    repl_text = (
        f"REPLENISHMENT REQUIRED: Order {repl['quantity']} units "
        f"(Shortfall={repl['shortfall']}, Formula: {repl['formula']})"
        if repl.get("triggered")
        else f"No replenishment triggered: {repl.get('reason','stock above safety stock')}"
    )

    # Pre‑compute Monte Carlo using the context numbers
    mc_prob = None
    if context["demand_stats"]["std_monthly"] > 0:
        mc = run_monte_carlo(context["sih"], context["safety_stock_sap"],
                             context["demand_stats"]["avg_monthly"],
                             context["demand_stats"]["std_monthly"],
                             context["lead_time_days"])
        mc_prob = mc["probability_breach_pct"]

    bom = context.get("bom_components", [])
    external_bom = [b for b in bom if not b.get("inhouse") and not b.get("supplier","").startswith("⚠")]
    missing_bom  = [b for b in bom if b.get("supplier","").startswith("⚠")]
    fixed_qty    = [b for b in bom if b.get("fixed_qty")]

    consolidation = context.get("supplier_consolidation", [])
    consol_text = ""
    if consolidation:
        consol_text = "SUPPLIER CONSOLIDATION: " + "; ".join([
            f"{c['supplier']} also supplies {c['also_supplies']} other finished goods (transit {c.get('transit_days','?')}d)"
            for c in consolidation[:3]
        ])

    prompt = f"""Analyse this supply chain material and produce an agentic intelligence briefing.

MATERIAL CONTEXT:
{json.dumps(context, indent=2, default=str)}

PRE-COMPUTED REPLENISHMENT:
{repl_text}

MONTE CARLO: {mc_prob}% probability of stockout in next 6 months (if computed).

LEAD TIME URGENCY: {context.get('lt_urgency','unknown')}

BOM FACTS:
- Total components: {len(bom)}
- External components (need procurement): {len(external_bom)}
- Missing supplier data: {len(missing_bom)} components
- Fixed quantity (order exactly 1): {len(fixed_qty)} components
{consol_text}

STEP-BY-STEP ANALYSIS REQUIRED:
1. Is current stock genuinely safe given lead time? Compare days_cover vs lead_time_days.
2. Is the SAP safety stock calibrated correctly vs ARIA recommended?
3. What pattern caused the {len(context.get('breach_periods',[]))} historical breaches?
4. What is the BOM/supplier risk upstream (including supplier reliability, geo risk, transit times)?
5. What specific action should procurement take TODAY (including consolidation if beneficial)?

Format the recommendation section EXACTLY as:
SKU: [id] — [name]
Current inventory: [n] units  
Safety stock (Material Master): [n] units — [BELOW/ABOVE threshold]
Lead time (Material Master): [n] days — [CRITICAL/OK relative to days cover]
Fixed lot size: [n] units
Recommended order: [Immediate/This week/Monitor], [n] units
Reason: [specific sentence with numbers]

If consolidation opportunity exists, add a line: "Consolidation: order together with [other materials] from [supplier] to save logistics cost."
"""

    try:
        response = client.chat.completions.create(
            model=deployment,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": prompt},
            ],
            temperature=0.15,
            max_tokens=1200,
        )
        raw = response.choices[0].message.content.strip()
        result = _parse_json(raw)
        if result:
            result.setdefault("data_quality_flags", context.get("data_quality_flags", []))
            result.setdefault("bom_risk", None)
            result.setdefault("supplier_action", None)
            result.setdefault("consolidation_opportunity", None)
            return result
        # Fallback
        return {
            "headline": "Analysis requires review — see findings below",
            "verdict": context.get("risk_status","UNKNOWN"),
            "executive_summary": raw[:500] if raw else "No response from agent.",
            "key_findings": [repl_text, f"Lead time urgency: {context.get('lt_urgency','N/A')}", f"Monte Carlo breach prob: {mc_prob}%"],
            "sap_gap": f"SAP Safety Stock: {context.get('safety_stock_sap','N/A')} units. ARIA recommends: {context.get('rec_safety_stock','N/A')} units.",
            "recommendation": repl_text,
            "risk_if_ignored": "Review replenishment status immediately." if repl.get("triggered") else "Monitor stock levels.",
            "data_confidence": "LOW — JSON parse issue.",
            "data_quality_flags": context.get("data_quality_flags", []),
            "bom_risk": None,
            "supplier_action": None,
            "consolidation_opportunity": None,
        }
    except Exception as e:
        return {
            "headline": "Agent connection error",
            "verdict": context.get("risk_status","UNKNOWN"),
            "executive_summary": f"Error: {str(e)[:200]}",
            "key_findings": [repl_text, "Check Azure API key.", "Review data manually."],
            "sap_gap": "Unable to connect to agent.",
            "recommendation": repl_text,
            "risk_if_ignored": "Manual review required.",
            "data_confidence": "LOW — connection error.",
            "data_quality_flags": context.get("data_quality_flags", []),
            "bom_risk": None, "supplier_action": None, "consolidation_opportunity": None,
        }

def run_monte_carlo(current_stock: float, safety_stock: float, avg_demand: float,
                    std_demand: float, lead_time: float, months: int = 6, n_sims: int = 1000) -> dict:
    random.seed(42)
    breach_count = 0
    end_stocks = []
    breach_months = []
    for _ in range(n_sims):
        stock = current_stock
        breached = False
        breach_m = None
        for m in range(months):
            d = max(0.0, random.gauss(avg_demand, std_demand))
            stock = max(0.0, stock - d)
            if stock < safety_stock and not breached:
                breached = True
                breach_m = m + 1
        if breached:
            breach_count += 1
            breach_months.append(breach_m)
        end_stocks.append(stock)
    end_stocks.sort()
    p_breach = round(breach_count / n_sims * 100, 1)
    p10 = end_stocks[int(0.10 * n_sims)]
    p50 = end_stocks[int(0.50 * n_sims)]
    p90 = end_stocks[int(0.90 * n_sims)]
    avg_breach_month = round(sum(breach_months) / len(breach_months), 1) if breach_months else None
    return {
        "n_simulations": n_sims,
        "months_simulated": months,
        "probability_breach_pct": p_breach,
        "avg_breach_month": avg_breach_month,
        "p10_end_stock": round(p10, 0),
        "p50_end_stock": round(p50, 0),
        "p90_end_stock": round(p90, 0),
        "end_stock_distribution": [round(v, 0) for v in end_stocks[::10]],
        "verdict": "HIGH RISK" if p_breach>50 else ("MODERATE RISK" if p_breach>20 else ("LOW RISK" if p_breach>5 else "VERY LOW RISK")),
    }

def draft_supplier_email(client: AzureOpenAI, deployment: str, supplier_name: str, supplier_email: str,
                         materials: list, plant_name: str = "Revvity Turku FI11") -> str:
    order_lines = "\n".join([f"  - {m['name']}: {m['quantity']} units (lot size: {m['lot_size']})" for m in materials])
    prompt = f"""Draft a professional procurement order email to {supplier_name} ({supplier_email}).
Plant: {plant_name}
Materials to order:
{order_lines}

Requirements:
- Professional but concise (under 150 words)
- Include subject line
- Reference urgency where stock is below safety stock
- Include contact request for lead time confirmation
- Sign off as ARIA Supply Intelligence System, {plant_name}

Return just the email text with Subject: on first line."""
    try:
        response = client.chat.completions.create(
            model=deployment,
            messages=[{"role":"user","content":prompt}],
            temperature=0.3, max_tokens=350,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Error drafting email: {str(e)[:100]}"

def interpret_chart(client: AzureOpenAI, deployment: str, chart_type: str, chart_data: dict, question: str = None) -> str:
    q = question or f"Interpret this {chart_type} and provide 2-3 actionable insights for supply chain managers."
    prompt = f"""You are ARIA, a supply chain analyst. Interpret this {chart_type} data and give concise actionable insights.

DATA:
{json.dumps(chart_data, default=str)[:1500]}

{q}

Rules: Under 120 words. Plain English sentences. Cite specific numbers. Focus on what action to take."""
    try:
        response = client.chat.completions.create(
            model=deployment,
            messages=[{"role":"user","content":prompt}],
            temperature=0.2, max_tokens=200,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Interpretation unavailable: {str(e)[:80]}"

def simulate_scenario(client: AzureOpenAI, deployment: str, material_name: str, current_stock: float,
                      safety_stock: float, lead_time: float, fixed_lot_size: float,
                      demand_scenarios: dict, order_action: dict = None, disruption_days: int = None) -> dict:
    if disruption_days is not None:
        daily = demand_scenarios.get("expected", 0) / 30
        consumed = daily * disruption_days
        remaining = current_stock - consumed
        breach = remaining < safety_stock if safety_stock > 0 else False
        shortfall = max(0, safety_stock - remaining)
        lot = fixed_lot_size
        qty = math.ceil(shortfall / lot) * lot if lot > 0 and shortfall > 0 else shortfall
        prompt = f"""Supply disruption scenario for {material_name}:
- Duration: {disruption_days} days of no replenishment
- Current stock: {current_stock} units
- Safety stock: {safety_stock} units
- Daily demand: {daily:.1f} units/day
- Stock at end: {max(0,remaining):.0f} units
- Breach: {breach} (shortfall: {shortfall:.0f} units if breach)
- Emergency order needed: {qty:.0f} units

Return JSON: breach_occurs, days_to_breach, shortfall_units, stock_at_end, 
recommended_emergency_action, simulation_verdict, urgency (ACT TODAY/ACT THIS WEEK/MONITOR/SAFE), priority_rank (1-5)"""
        default = {
            "breach_occurs": breach, "days_to_breach": int(safety_stock/daily) if daily>0 and breach else None,
            "shortfall_units": int(shortfall), "stock_at_end": max(0,int(remaining)),
            "recommended_emergency_action": f"Emergency order {qty:.0f} units." if breach else "Monitor.",
            "simulation_verdict": "Breach detected." if breach else "Safe for disruption period.",
            "urgency": "ACT TODAY" if (breach and remaining<0) else ("ACT THIS WEEK" if breach else "MONITOR"),
            "priority_rank": 1 if breach else 4,
        }
    else:
        shortfall = max(0, safety_stock - current_stock)
        lot = fixed_lot_size
        min_order = math.ceil(shortfall / lot) * lot if lot > 0 and shortfall > 0 else shortfall
        prompt = f"""Demand simulation for {material_name}:
- Current stock: {current_stock}, Safety stock: {safety_stock}, Lead time: {lead_time}d
- Lot size: {fixed_lot_size}
- Scenarios: Low={demand_scenarios['low']:.0f}/mo, Expected={demand_scenarios['expected']:.0f}/mo, High={demand_scenarios['high']:.0f}/mo
- Order placed: {json.dumps(order_action) if order_action else 'None'}
- Minimum order (CEILING formula): {min_order:.0f} units

Return JSON: low_months_safe, expected_months_safe, high_months_safe, 
order_prevents_breach, min_order_recommended, simulation_verdict, urgency"""
        default = {
            "low_months_safe":999,"expected_months_safe":3,"high_months_safe":1,
            "order_prevents_breach":bool(order_action),
            "min_order_recommended":int(min_order),
            # Fix #17: Friendlier message when LLM verdict is unavailable
            "simulation_verdict": "Simulation completed, but ARIA could not generate a verdict. Please review the graph manually.",
            "urgency":"MONITOR",
        }
    try:
        response = client.chat.completions.create(
            model=deployment,
            messages=[{"role":"user","content":prompt}],
            temperature=0.1, max_tokens=400,
        )
        result = _parse_json(response.choices[0].message.content.strip())
        return result if result else default
    except:
        return default

def simulate_multi_sku_disruption(client, deployment, disruption_days: int, sku_data: list) -> list:
    results = []
    for sku in sku_data:
        daily = sku["avg_monthly_demand"] / 30 if sku["avg_monthly_demand"] > 0 else 0
        consumed = daily * disruption_days
        remaining = sku["current_stock"] - consumed
        ss = sku["safety_stock"]
        breach = remaining < ss if ss > 0 else False
        shortfall = max(0, ss - remaining)
        fls = sku["fixed_lot_size"]
        qty = math.ceil(shortfall / fls) * fls if fls > 0 and shortfall > 0 else shortfall
        days_to_breach = None
        if breach and daily > 0 and ss > 0:
            ab = sku["current_stock"] - ss
            days_to_breach = max(0, int(ab / daily)) if ab > 0 else 0
        results.append({
            "material":sku["material"],"name":sku["name"],"breach_occurs":breach,
            "days_to_breach":days_to_breach,"shortfall_units":int(shortfall),
            "stock_at_end":max(0,int(remaining)),"reorder_qty":int(qty),
            "lead_time":sku["lead_time"],"severity_score":shortfall*2+max(0,disruption_days-(days_to_breach or disruption_days)) if breach else 0,
        })
    results.sort(key=lambda x:(0 if x["breach_occurs"] else 1, x["days_to_breach"] if x["days_to_breach"] is not None else 999,-x["shortfall_units"]))
    return results

def chat_with_data(client: AzureOpenAI, deployment: str, question: str, context: str) -> str:
    system = """You are ARIA, a supply chain intelligence agent for Revvity Turku FI11.
Answer concisely with specific numbers. Under 150 words. Plain English sentences."""
    try:
        response = client.chat.completions.create(
            model=deployment,
            messages=[
                {"role":"system","content":system},
                {"role":"user","content":f"CONTEXT:\n{context}\n\nQUESTION: {question}"},
            ],
            temperature=0.3, max_tokens=250,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Error: {str(e)[:100]}"
