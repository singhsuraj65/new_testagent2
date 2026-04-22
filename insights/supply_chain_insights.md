# ARIA Supply Chain Intelligence — FI11 Turku Knowledge Base

> **Generated:** 21 April 2026 18:34  
> **Plant:** FI11 Turku (Revvity)  
> **Data period:** up to Apr 2026  
> **Purpose:** Grounded context for the ARIA chatbot assistant

---

## Plant Snapshot

| Metric | Value |
|--------|-------|
| Total Materials Tracked | 7 |
| 🔴 Critical | 1 |
| 🟡 Warning | 0 |
| 🟢 Healthy | 3 |
| ⚪ Insufficient Data | 3 |
| SKUs Needing Immediate Order | 1 |
| Total Units Required (all replenishments) | 400 |
| Most Urgent Material | **SARS-CoV-2 Plus Kit** — 0.0 days cover |


## Critical Materials — Immediate Action Required

### 🔴 DELFIA Wash Concentrate `3014-0010`

| Field | Value |
|-------|-------|
| Stock-in-Hand (SIH) | **22 units** |
| SAP Safety Stock | 150 units |
| ARIA Recommended SS | 64 units |
| Days of Cover | **1.9 days** |
| Lead Time | 3 days |
| Avg Monthly Demand | 352.3 units |
| Demand Std Dev | 123.3 units |
| Lot Size | 400 units |
| Trend | Declining |
| ABCDE Category | A |
| Temp Condition | Z3 |

**⛔ Replenishment Required:** Order **400 units** immediately.
*Formula: CEILING(128/400)×400 = 400*

**Historical breaches:** Jul 2024, Aug 2025, Jan 2026, Feb 2026, Mar 2026, Apr 2026 (7 total breach periods)  

**External suppliers:** ISP chemicals LLC, VWR INTERNATIONAL OY, ROCHE DIAGNOSTICS DEUTSCHLAND GMBH, GRAHAM PACKAGING COMPANY OY  

---


## Warning Materials — Monitor Closely

*No warning materials at this time.*


## Healthy Materials

- 🟢 **DELFIA Assay Buffer** — 101 units stock | 694.7d cover | Demand 4.4/mo | Trend: Rising
- 🟢 **Microplate Deep Well (LSD)** — 826 units stock | 424.6d cover | Demand 58.4/mo | Trend: Rising
- 🟢 **DELFIA Enhancement Solution** — 55 units stock | 177.1d cover | Demand 9.3/mo | Trend: Rising


## Safety Stock Analysis

ARIA calculates recommended safety stock at 95% service level: `1.65 × σ_demand × √(lead_time/30)`
SAP safety stock is sourced from Material Master. Current Inventory SS = 0 for all SKUs (known data gap).

| Material | SAP SS | ARIA SS | Gap | Risk |
|----------|--------|---------|-----|------|
| Microplate Deep Well (LSD) | 0 | 19 | **+19** | 🟢 |
| DELFIA Assay Buffer | 5 | 2 | **-3** | 🟢 |
| DELFIA Enhancement Solution | 10 | 6 | **-4** | 🟢 |
| DELFIA Wash Concentrate | 150 | 64 | **-86** | 🔴 |


## Historical Stockout & Breach Summary

A 'breach' = a period where Gross Stock fell below the SAP Safety Stock.

| Material | Total Breaches | Risk | Trend |
|----------|---------------|------|-------|
| DELFIA Wash Concentrate | 7 | 🔴 CRITICAL | Declining |
| DELFIA Assay Buffer | 2 | 🟢 HEALTHY | Rising |
| DELFIA Enhancement Solution | 1 | 🟢 HEALTHY | Rising |
| Microplate Deep Well (LSD) | 0 | 🟢 HEALTHY | Rising |


## Immediate Replenishment Action List

**1 SKUs require orders totalling 400 units.**

| # | Material | Order Qty | Days Cover | Lead Time | Formula |
|---|----------|-----------|------------|-----------|---------|
| 1 | **DELFIA Wash Concentrate** | 400 units | 1.9d | 3d | `CEILING(128/400)×400 = 400` |


## Supplier Consolidation Opportunities

**8 suppliers supply multiple finished goods with pending orders — consolidating reduces procurement overhead.**

- **TARRAX OY** (Tampere, Finland) — Email: `asiakaspalvelu@tarrax.fi` | Supplies: DELFIA Enhancement Solution, DELFIA Assay Buffer, Europium Solution 200ml, Microplate Deep Well (LSD)
- **INFORMA OY** (Turku, Finland) — Email: `sapostotilaukset@revvity.com` | Supplies: Microplate Deep Well (LSD), Anti-AFP AF5/A2 Antibody, DELFIA Wash Concentrate, SARS-CoV-2 Plus Kit
- **GRAHAM PACKAGING COMPANY OY** (Hyvinkää, Finland) — Email: `Anne.Montonen@grahampackaging.com` | Supplies: DELFIA Enhancement Solution, DELFIA Assay Buffer, Europium Solution 200ml, DELFIA Wash Concentrate
- **Getra Oy** (Turku, Finland) — Email: `sales@getra.fi` | Supplies: DELFIA Enhancement Solution, DELFIA Assay Buffer, DELFIA Wash Concentrate
- **ROCHE DIAGNOSTICS DEUTSCHLAND GMBH** (Mannheim, Germany) — Email: `hanna.metzger@roche.com` | Supplies: DELFIA Assay Buffer, Anti-AFP AF5/A2 Antibody, DELFIA Wash Concentrate
- **STORAENSO PACKAGING OY** (Helsinki, Finland) — Email: `Seija.boren@storaenso.com` | Supplies: DELFIA Wash Concentrate, SARS-CoV-2 Plus Kit
- **ISP chemicals LLC** (Wayne, NJ, USA) — Email: `BMcJury@ashland.com` | Supplies: DELFIA Wash Concentrate
- **VWR INTERNATIONAL OY** (Espoo, Finland) — Email: `anni.karsma@avantorsciences.com` | Supplies: DELFIA Wash Concentrate


## BOM & Supplier Overview (per Finished Good)

**DELFIA Enhancement Solution** (1244-104) — 22 components: 3 inhouse, 19 external, 9 missing supplier info
  - External suppliers: Merck Life Science Oy, Anora Group Oyj, EMBALLATOR VAXJOPLAST, GRAHAM PACKAGING COMPANY OY, TARRAX OY

**DELFIA Assay Buffer** (1244-106) — 19 components: 2 inhouse, 17 external, 7 missing supplier info
  - External suppliers: ROCHE DIAGNOSTICS DEUTSCHLAND GMBH, Merck Life Science Oy, GRAHAM PACKAGING COMPANY OY, TARRAX OY, Getra Oy

**Microplate Deep Well (LSD)** (13808190) — 3 components: 0 inhouse, 3 external, 0 missing supplier info
  - External suppliers: Thermo Electron LED GmbH, TARRAX OY, INFORMA OY

**DELFIA Wash Concentrate** (3014-0010) — 18 components: 2 inhouse, 16 external, 3 missing supplier info
  - External suppliers: ISP chemicals LLC, VWR INTERNATIONAL OY, ROCHE DIAGNOSTICS DEUTSCHLAND GMBH, GRAHAM PACKAGING COMPANY OY, TARRAX OY


## Supply Chain Domain Knowledge

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


## Key Risks & Executive Observations

- **Lead Time Risk:** 1 material(s) have days of cover less than their lead time — meaning even if ordered today, stock may run out before delivery: DELFIA Wash Concentrate.

- **Chronic Stockout Pattern:** DELFIA Wash Concentrate has experienced 7 breach periods — the worst in the plant. Structural replenishment review required.

- **Declining Stock Trend + Critical Status:** DELFIA Wash Concentrate are both critical AND on a declining trend.
