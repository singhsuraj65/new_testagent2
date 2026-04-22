"""
insights/generate_insights.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Standalone script — run once (or whenever data changes).

Reads all source data via data_loader, builds a rich Markdown
knowledge document, and saves it to:
  • insights/supply_chain_insights.md   ← human-readable
  • insights/supply_chain_insights.json ← used by chatbot

Usage:
    cd aria_app
    python insights/generate_insights.py

The chatbot app loads supply_chain_insights.json at startup and
injects it into every LLM system prompt as grounded context.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import os
import sys
import json
import math
import textwrap
from datetime import datetime

import pandas as pd
import numpy as np

# ── ensure aria_app root is on the path ───────────────────────────────────────
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from data_loader import (
    load_all, build_material_summary,
    get_stock_history, get_demand_history,
    get_bom_components, get_supplier_consolidation,
)

OUT_DIR = os.path.dirname(os.path.abspath(__file__))
MD_PATH  = os.path.join(OUT_DIR, "supply_chain_insights.md")
JSON_PATH = os.path.join(OUT_DIR, "supply_chain_insights.json")


# ─────────────────────────────────────────────────────────────────────────────
# Helper utilities
# ─────────────────────────────────────────────────────────────────────────────

def fmt_p(p) -> str:
    try:
        return pd.to_datetime(str(p), format="%Y%m").strftime("%b %Y")
    except Exception:
        return str(p)


def risk_icon(risk: str) -> str:
    return {"CRITICAL": "🔴", "WARNING": "🟡", "HEALTHY": "🟢",
            "INSUFFICIENT_DATA": "⚪"}.get(risk, "⚪")


def section(title: str, level: int = 2) -> str:
    prefix = "#" * level
    return f"\n{prefix} {title}\n"


# ─────────────────────────────────────────────────────────────────────────────
# Main builder
# ─────────────────────────────────────────────────────────────────────────────

def build_insights() -> dict:
    print("Loading data …")
    data    = load_all()
    summary = build_material_summary(data)

    active  = summary[summary.risk != "INSUFFICIENT_DATA"]
    insuf   = summary[summary.risk == "INSUFFICIENT_DATA"]
    crit    = summary[summary.risk == "CRITICAL"]
    warn    = summary[summary.risk == "WARNING"]
    healthy = summary[summary.risk == "HEALTHY"]

    # ── Collect supplier consolidation once ───────────────────────────────────
    consolidation = get_supplier_consolidation(data, summary)

    lines = []  # markdown lines
    meta  = {}  # structured JSON payload

    # ─────────────────────────────────────────────────────────────────────────
    # 1. DOCUMENT HEADER
    # ─────────────────────────────────────────────────────────────────────────
    generated_at = datetime.now().strftime("%d %B %Y %H:%M")
    lines += [
        "# ARIA Supply Chain Intelligence — FI11 Turku Knowledge Base",
        "",
        f"> **Generated:** {generated_at}  ",
        f"> **Plant:** FI11 Turku (Revvity)  ",
        f"> **Data period:** up to Apr 2026  ",
        f"> **Purpose:** Grounded context for the ARIA chatbot assistant",
        "",
        "---",
    ]

    # ─────────────────────────────────────────────────────────────────────────
    # 2. PLANT SNAPSHOT
    # ─────────────────────────────────────────────────────────────────────────
    lines += [section("Plant Snapshot")]

    total_repl_units = int(summary["repl_quantity"].sum())
    total_repl_skus  = int((summary["repl_quantity"] > 0).sum())
    worst_mat        = summary.sort_values("days_cover").iloc[0]

    snapshot = {
        "total_materials":       len(summary),
        "critical_count":        len(crit),
        "warning_count":         len(warn),
        "healthy_count":         len(healthy),
        "insufficient_data_count": len(insuf),
        "total_replenishment_units_needed": total_repl_units,
        "skus_needing_immediate_order":     total_repl_skus,
        "lowest_cover_material":  worst_mat["name"],
        "lowest_cover_days":      round(worst_mat["days_cover"], 1),
        "generated_at":           generated_at,
    }
    meta["plant_snapshot"] = snapshot

    lines += [
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Total Materials Tracked | {len(summary)} |",
        f"| 🔴 Critical | {len(crit)} |",
        f"| 🟡 Warning | {len(warn)} |",
        f"| 🟢 Healthy | {len(healthy)} |",
        f"| ⚪ Insufficient Data | {len(insuf)} |",
        f"| SKUs Needing Immediate Order | {total_repl_skus} |",
        f"| Total Units Required (all replenishments) | {total_repl_units:,} |",
        f"| Most Urgent Material | **{worst_mat['name']}** — {round(worst_mat['days_cover'], 1)} days cover |",
        "",
    ]

    # ─────────────────────────────────────────────────────────────────────────
    # 3. CRITICAL MATERIALS — full detail
    # ─────────────────────────────────────────────────────────────────────────
    lines += [section("Critical Materials — Immediate Action Required")]
    meta["critical_materials"] = []

    if len(crit) == 0:
        lines += ["*No critical materials at this time.*", ""]
    else:
        for _, row in crit.sort_values("days_cover").iterrows():
            sh   = get_stock_history(data, row["material"])
            dh   = get_demand_history(data, row["material"])
            bom  = get_bom_components(data, row["material"])

            # Breach history
            ss = row["safety_stock"]
            breaches_recent = []
            if ss > 0 and len(sh) > 0:
                br = sh[sh["Gross Stock"] < ss].tail(6)
                breaches_recent = [fmt_p(p) for p in br["Fiscal Period"].tolist()]

            # Supplier list
            suppliers = []
            if len(bom) > 0:
                ext = bom[bom["Procurement type"] == "F"]
                suppliers = ext["Supplier Name(Vendor)"].dropna().unique().tolist()[:4]

            entry = {
                "material_id":      row["material"],
                "name":             row["name"],
                "risk":             "CRITICAL",
                "stock_in_hand":    round(row["sih"]),
                "safety_stock_sap": round(ss),
                "safety_stock_aria_recommended": round(row["rec_safety_stock"]),
                "days_cover":       round(row["days_cover"], 1),
                "lead_time_days":   round(row["lead_time"]),
                "avg_monthly_demand": round(row["avg_monthly_demand"], 1),
                "std_demand":       round(row["std_demand"], 1),
                "lot_size":         round(row["lot_size"]),
                "order_quantity_required": int(row["repl_quantity"]),
                "replenishment_formula":   row["repl_formula"],
                "breach_count_total":      int(row["breach_count"]),
                "recent_breach_periods":   breaches_recent,
                "trend":            row["trend"],
                "lt_urgency":       row["lt_urgency"],
                "abcde_category":   row["abcde"],
                "temp_condition":   row["temp_cond"],
                "external_suppliers": suppliers,
                "data_quality_flags": row["data_quality_flags"],
            }
            meta["critical_materials"].append(entry)

            lines += [
                f"### {risk_icon('CRITICAL')} {row['name']} `{row['material']}`",
                "",
                f"| Field | Value |",
                f"|-------|-------|",
                f"| Stock-in-Hand (SIH) | **{round(row['sih'])} units** |",
                f"| SAP Safety Stock | {round(ss)} units |",
                f"| ARIA Recommended SS | {round(row['rec_safety_stock'])} units |",
                f"| Days of Cover | **{round(row['days_cover'], 1)} days** |",
                f"| Lead Time | {round(row['lead_time'])} days |",
                f"| Avg Monthly Demand | {round(row['avg_monthly_demand'], 1)} units |",
                f"| Demand Std Dev | {round(row['std_demand'], 1)} units |",
                f"| Lot Size | {round(row['lot_size'])} units |",
                f"| Trend | {row['trend']} |",
                f"| ABCDE Category | {row['abcde']} |",
                f"| Temp Condition | {row['temp_cond']} |",
                "",
                f"**⛔ Replenishment Required:** Order **{int(row['repl_quantity'])} units** immediately.",
                f"*Formula: {row['repl_formula']}*",
                "",
            ]
            if breaches_recent:
                lines += [f"**Historical breaches:** {', '.join(breaches_recent)} ({int(row['breach_count'])} total breach periods)  ", ""]
            if suppliers:
                lines += [f"**External suppliers:** {', '.join(suppliers)}  ", ""]
            if row["data_quality_flags"]:
                lines += [f"**Data quality flags:** {'; '.join(row['data_quality_flags'])}  ", ""]
            lines += ["---", ""]

    # ─────────────────────────────────────────────────────────────────────────
    # 4. WARNING MATERIALS
    # ─────────────────────────────────────────────────────────────────────────
    lines += [section("Warning Materials — Monitor Closely")]
    meta["warning_materials"] = []

    if len(warn) == 0:
        lines += ["*No warning materials at this time.*", ""]
    else:
        for _, row in warn.sort_values("days_cover").iterrows():
            entry = {
                "material_id":      row["material"],
                "name":             row["name"],
                "risk":             "WARNING",
                "stock_in_hand":    round(row["sih"]),
                "safety_stock_sap": round(row["safety_stock"]),
                "days_cover":       round(row["days_cover"], 1),
                "lead_time_days":   round(row["lead_time"]),
                "avg_monthly_demand": round(row["avg_monthly_demand"], 1),
                "order_quantity_required": int(row["repl_quantity"]),
                "breach_count_total": int(row["breach_count"]),
                "trend":            row["trend"],
                "lt_urgency":       row["lt_urgency"],
            }
            meta["warning_materials"].append(entry)
            lines += [
                f"### {risk_icon('WARNING')} {row['name']} `{row['material']}`",
                f"- Stock: {round(row['sih'])} units | SAP SS: {round(row['safety_stock'])} | "
                f"Days cover: **{round(row['days_cover'], 1)}d** | Lead time: {round(row['lead_time'])}d | "
                f"Demand: {round(row['avg_monthly_demand'], 1)}/mo | Trend: {row['trend']}",
            ]
            if int(row["repl_quantity"]) > 0:
                lines += [f"  - ⚠ Order {int(row['repl_quantity'])} units — approaching safety stock threshold"]
            lines += [""]

    # ─────────────────────────────────────────────────────────────────────────
    # 5. HEALTHY MATERIALS
    # ─────────────────────────────────────────────────────────────────────────
    lines += [section("Healthy Materials")]
    meta["healthy_materials"] = []

    for _, row in healthy.sort_values("days_cover", ascending=False).iterrows():
        entry = {
            "material_id":      row["material"],
            "name":             row["name"],
            "risk":             "HEALTHY",
            "stock_in_hand":    round(row["sih"]),
            "safety_stock_sap": round(row["safety_stock"]),
            "days_cover":       round(row["days_cover"], 1),
            "lead_time_days":   round(row["lead_time"]),
            "avg_monthly_demand": round(row["avg_monthly_demand"], 1),
            "breach_count_total": int(row["breach_count"]),
            "trend":            row["trend"],
        }
        meta["healthy_materials"].append(entry)
        lines += [
            f"- {risk_icon('HEALTHY')} **{row['name']}** — "
            f"{round(row['sih'])} units stock | {round(row['days_cover'], 1)}d cover | "
            f"Demand {round(row['avg_monthly_demand'], 1)}/mo | Trend: {row['trend']}"
        ]
    lines += [""]

    # ─────────────────────────────────────────────────────────────────────────
    # 6. SAFETY STOCK ANALYSIS
    # ─────────────────────────────────────────────────────────────────────────
    lines += [section("Safety Stock Analysis")]
    meta["safety_stock_analysis"] = []

    act = summary[summary.risk != "INSUFFICIENT_DATA"].copy()
    act["ss_gap"] = act["rec_safety_stock"] - act["safety_stock"]
    act_sorted = act.sort_values("ss_gap", ascending=False)

    lines += [
        "ARIA calculates recommended safety stock at 95% service level: `1.65 × σ_demand × √(lead_time/30)`",
        "SAP safety stock is sourced from Material Master. Current Inventory SS = 0 for all SKUs (known data gap).",
        "",
        "| Material | SAP SS | ARIA SS | Gap | Risk |",
        "|----------|--------|---------|-----|------|",
    ]
    for _, row in act_sorted.iterrows():
        gap  = int(row["rec_safety_stock"] - row["safety_stock"])
        icon = risk_icon(row["risk"])
        lines += [
            f"| {row['name']} | {int(row['safety_stock'])} | "
            f"{int(row['rec_safety_stock'])} | **{gap:+d}** | {icon} |"
        ]
        meta["safety_stock_analysis"].append({
            "name":         row["name"],
            "sap_ss":       int(row["safety_stock"]),
            "aria_ss":      int(row["rec_safety_stock"]),
            "gap":          gap,
            "risk":         row["risk"],
            "lead_time":    round(row["lead_time"]),
            "std_demand":   round(row["std_demand"], 1),
        })
    lines += [""]

    # ─────────────────────────────────────────────────────────────────────────
    # 7. HISTORICAL BREACH SUMMARY
    # ─────────────────────────────────────────────────────────────────────────
    lines += [section("Historical Stockout & Breach Summary")]
    meta["breach_summary"] = []

    breach_mats = act.sort_values("breach_count", ascending=False)
    lines += [
        "A 'breach' = a period where Gross Stock fell below the SAP Safety Stock.",
        "",
        "| Material | Total Breaches | Risk | Trend |",
        "|----------|---------------|------|-------|",
    ]
    for _, row in breach_mats.iterrows():
        lines += [
            f"| {row['name']} | {int(row['breach_count'])} | "
            f"{risk_icon(row['risk'])} {row['risk']} | {row['trend']} |"
        ]
        meta["breach_summary"].append({
            "name":          row["name"],
            "breach_count":  int(row["breach_count"]),
            "risk":          row["risk"],
            "trend":         row["trend"],
            "days_cover":    round(row["days_cover"], 1),
        })
    lines += [""]

    # ─────────────────────────────────────────────────────────────────────────
    # 8. REPLENISHMENT ACTION LIST
    # ─────────────────────────────────────────────────────────────────────────
    needs_repl = summary[summary.repl_quantity > 0].sort_values("days_cover")
    lines += [section("Immediate Replenishment Action List")]
    meta["replenishment_actions"] = []

    if len(needs_repl) == 0:
        lines += ["*No replenishment orders required at this time.*", ""]
    else:
        lines += [
            f"**{len(needs_repl)} SKUs require orders totalling {total_repl_units:,} units.**",
            "",
            "| # | Material | Order Qty | Days Cover | Lead Time | Formula |",
            "|---|----------|-----------|------------|-----------|---------|",
        ]
        for i, (_, row) in enumerate(needs_repl.iterrows(), 1):
            lines += [
                f"| {i} | **{row['name']}** | {int(row['repl_quantity'])} units | "
                f"{round(row['days_cover'], 1)}d | {round(row['lead_time'])}d | "
                f"`{row['repl_formula']}` |"
            ]
            meta["replenishment_actions"].append({
                "rank":       i,
                "name":       row["name"],
                "material_id": row["material"],
                "order_qty":  int(row["repl_quantity"]),
                "days_cover": round(row["days_cover"], 1),
                "lead_time":  round(row["lead_time"]),
                "formula":    row["repl_formula"],
            })
        lines += [""]

    # ─────────────────────────────────────────────────────────────────────────
    # 9. SUPPLIER CONSOLIDATION OPPORTUNITIES
    # ─────────────────────────────────────────────────────────────────────────
    lines += [section("Supplier Consolidation Opportunities")]
    meta["supplier_consolidation"] = []

    opps = consolidation[consolidation.consolidation_opportunity]
    if len(opps) == 0:
        lines += ["*No consolidation opportunities identified.*", ""]
    else:
        lines += [
            f"**{len(opps)} suppliers supply multiple finished goods with pending orders — "
            f"consolidating reduces procurement overhead.**",
            "",
        ]
        for _, r in opps.iterrows():
            ml = r.get("material_list", [])
            mat_names = summary[summary.material.isin(ml)]["name"].tolist()
            lines += [
                f"- **{r['supplier']}** ({r.get('city', '—')}) — "
                f"Email: `{r.get('email', '—')}` | "
                f"Supplies: {', '.join(mat_names[:4])}"
            ]
            meta["supplier_consolidation"].append({
                "supplier":  r["supplier"],
                "city":      r.get("city", ""),
                "email":     r.get("email", ""),
                "materials": mat_names,
            })
        lines += [""]

    # ─────────────────────────────────────────────────────────────────────────
    # 10. BOM OVERVIEW PER MATERIAL
    # ─────────────────────────────────────────────────────────────────────────
    lines += [section("BOM & Supplier Overview (per Finished Good)")]
    meta["bom_overview"] = []

    for _, row in active.iterrows():
        bom = get_bom_components(data, row["material"])
        if len(bom) == 0:
            continue
        tc         = len(bom)
        inhouse_n  = int((bom["Procurement type"] == "E").sum())
        external_n = int((bom["Procurement type"] == "F").sum())
        missing_n  = int(bom["Supplier Display"].str.startswith("⚠", na=False).sum())
        suppliers  = bom[bom["Procurement type"] == "F"]["Supplier Name(Vendor)"].dropna().unique().tolist()[:5]

        lines += [
            f"**{row['name']}** ({row['material']}) — "
            f"{tc} components: {inhouse_n} inhouse, {external_n} external, {missing_n} missing supplier info",
        ]
        if suppliers:
            lines += [f"  - External suppliers: {', '.join(suppliers)}"]
        lines += [""]

        meta["bom_overview"].append({
            "material":           row["material"],
            "name":               row["name"],
            "total_components":   tc,
            "inhouse":            inhouse_n,
            "external":           external_n,
            "missing_supplier":   missing_n,
            "external_suppliers": suppliers,
        })

    # ─────────────────────────────────────────────────────────────────────────
    # 11. DOMAIN KNOWLEDGE — supply chain concepts for this plant
    # ─────────────────────────────────────────────────────────────────────────
    lines += [section("Supply Chain Domain Knowledge")]
    lines += [textwrap.dedent("""
    ### Key Concepts Used in This System

    **Safety Stock (SS)**
    Buffer inventory protecting against demand variability and supply delays.
    - SAP SS: manually set in Material Master (known to be outdated/zero for several SKUs)
    - ARIA SS: statistically computed at 95% service level — `1.65 × σ_demand × √(lead_time/30)`

    **Days of Cover**
    How many days of demand current stock can cover.
    - Formula: `Stock-in-Hand ÷ (Avg Monthly Demand ÷ 30)`
    - Critical threshold: <15 days. Warning: 15–30 days.

    **Replenishment Quantity**
    Order quantity when stock falls below safety stock.
    - Formula: `CEILING(Shortfall / Fixed Lot Size) × Fixed Lot Size`
    - Shortfall = `SAP Safety Stock − Stock-in-Hand`
    - Fixed Lot Size (FLS) sourced from Current Inventory planning parameters.

    **Lead Time**
    Maximum of: Planned Delivery Time, Inhouse Production Time (from Material Master).
    - If lead time > days of cover: immediate order required regardless of SS status.

    **ABCDE Classification**
    - A/B: High-value, high-priority materials. Closest monitoring.
    - C/D/E: Lower value but still tracked for continuity.

    **Temperature Conditions**
    Relevant for cold-chain materials requiring special handling and storage constraints.

    **BOM (Bill of Materials)**
    - E = Inhouse/Revvity produced component
    - F = External supplier component
    - Fixed Qty = component quantity is independent of finished good batch size

    **Stockout/Breach**
    A period where Gross Stock < Safety Stock. Each month of breach = risk of production halt.

    **Supplier Consolidation**
    When the same external supplier provides components for multiple finished goods,
    combining purchase orders reduces lead times, logistics cost, and relationship overhead.

    ### Plant Context
    - **Plant:** FI11, Turku, Finland (Revvity diagnostics)
    - **Data sources:** Material Master (SAP), Inventory Extract, Sales History, BOM
    - **Reporting currency:** Units (each material measured in its own unit of measure)
    - **Planning horizon:** Monthly periods (YYYYMM format)
    - **Sales data:** Includes customer orders, internal consumption, write-offs
    """).strip()]
    lines += [""]

    # ─────────────────────────────────────────────────────────────────────────
    # 12. KEY RISKS & EXECUTIVE SUMMARY
    # ─────────────────────────────────────────────────────────────────────────
    lines += [section("Key Risks & Executive Observations")]

    exec_risks = []
    # Risk: coverage < lead time
    lt_critical = active[active["days_cover"] < active["lead_time"]]
    if len(lt_critical) > 0:
        mats_lt = lt_critical.sort_values("days_cover")["name"].tolist()
        exec_risks.append(
            f"**Lead Time Risk:** {len(lt_critical)} material(s) have days of cover less than their lead time "
            f"— meaning even if ordered today, stock may run out before delivery: "
            f"{', '.join(mats_lt[:4])}."
        )

    # Risk: SS gaps
    large_gap = act[act["ss_gap"] > 100].sort_values("ss_gap", ascending=False)
    if len(large_gap) > 0:
        exec_risks.append(
            f"**Safety Stock Under-Configuration:** {len(large_gap)} SKU(s) have SAP SS more than 100 units "
            f"below ARIA's 95% recommendation: {', '.join(large_gap['name'].tolist()[:3])}. "
            f"SAP Material Master should be updated."
        )

    # Risk: high breach count
    high_breach = act[act["breach_count"] > 5].sort_values("breach_count", ascending=False)
    if len(high_breach) > 0:
        worst = high_breach.iloc[0]
        exec_risks.append(
            f"**Chronic Stockout Pattern:** {worst['name']} has experienced {int(worst['breach_count'])} "
            f"breach periods — the worst in the plant. Structural replenishment review required."
        )

    # Risk: declining trend + critical
    declining_crit = crit[crit["trend"] == "Declining"]
    if len(declining_crit) > 0:
        exec_risks.append(
            f"**Declining Stock Trend + Critical Status:** "
            f"{', '.join(declining_crit['name'].tolist())} are both critical AND on a declining trend."
        )

    meta["executive_risks"] = exec_risks

    for risk_txt in exec_risks:
        lines += [f"- {risk_txt}", ""]

    if not exec_risks:
        lines += ["*No elevated systemic risks identified beyond individual SKU alerts.*", ""]

    # ─────────────────────────────────────────────────────────────────────────
    # FINALISE
    # ─────────────────────────────────────────────────────────────────────────
    md_content = "\n".join(lines)
    meta["full_markdown"] = md_content
    meta["domain_knowledge"] = lines[lines.index("### Key Concepts Used in This System")
                                      if "### Key Concepts Used in This System" in lines
                                      else -1:]

    return md_content, meta


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    md_content, meta = build_insights()

    # Write Markdown
    with open(MD_PATH, "w", encoding="utf-8") as f:
        f.write(md_content)
    print(f"✅ Markdown written → {MD_PATH}  ({len(md_content):,} chars)")

    # Write JSON
    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)
    print(f"✅ JSON written     → {JSON_PATH}  ({os.path.getsize(JSON_PATH):,} bytes)")

    # Quick summary
    print("\n─── Snapshot ─────────────────────────")
    print(f"  Total materials : {meta['plant_snapshot']['total_materials']}")
    print(f"  Critical        : {meta['plant_snapshot']['critical_count']}")
    print(f"  Warning         : {meta['plant_snapshot']['warning_count']}")
    print(f"  Healthy         : {meta['plant_snapshot']['healthy_count']}")
    print(f"  Units to order  : {meta['plant_snapshot']['total_replenishment_units_needed']:,}")
    print(f"  Executive risks : {len(meta['executive_risks'])}")
    print("──────────────────────────────────────")
