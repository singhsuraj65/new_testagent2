# # """
# # data_loader.py — ARIA Supply Intelligence
# # Updated with:
# # - New replenishment formula: CEILING(Shortfall / FLS) × FLS
# # - Supplier location data (enriched with coordinates)
# # - BOM procurement type logic: E=Inhouse(Revvity), F=External
# # - Fixed Quantity X handling
# # - Supplier cross-material consolidation analysis
# # """

# # import os, math
# # import pandas as pd
# # import numpy as np
# # import warnings
# # warnings.filterwarnings("ignore")

# # _BASE = os.path.dirname(os.path.abspath(__file__))

# # def _resolve(filename: str) -> str:
# #     local = os.path.join(_BASE, "data", filename)
# #     if os.path.exists(local): return local
# #     upload = os.path.join("/mnt/user-data/uploads", filename)
# #     if os.path.exists(upload): return upload
# #     raise FileNotFoundError(f"Cannot find '{filename}' in data/ or uploads/")

# # DATA_FILES = {
# #     "sales":      "Sales_HistoricalData_Structured.xlsx",
# #     "inv_lt":     "Inventory_Extract_and_Lead_Time.xlsx",
# #     "bom":        "Fi11_BOM_MResult_v2.xlsx",
# #     "mat_master": "Material_master_data_with_planning_parameters__Turku___Boston_.xlsx",
# #     "curr_inv":   "Current_Inventory___planning_parameters__Turku_and_Boston_.xlsx",
# # }

# # MATERIAL_LABELS = {
# #     "1244-104":  "DELFIA Enhancement Solution",
# #     "1244-106":  "DELFIA Assay Buffer",
# #     "13804314":  "Europium Solution 200ml",
# #     "13807866":  "Anti-AFP AF5/A2 Antibody",
# #     "13808190":  "Microplate Deep Well (LSD)",
# #     "3014-0010": "DELFIA Wash Concentrate",
# #     "3515-0010": "SARS-CoV-2 Plus Kit",
# # }

# # RISK_COLORS = {
# #     "CRITICAL":          "#EF4444",
# #     "WARNING":           "#F59E0B",
# #     "HEALTHY":           "#22C55E",
# #     "INSUFFICIENT_DATA": "#94A3B8",
# # }

# # # ── Supplier enrichment: locations + coordinates ───────────────────────────────
# # SUPPLIER_LOCATIONS = {
# #     "Merck Life Science Oy":              {"city":"Helsinki, Finland","country":"FI","lat":60.1699,"lon":24.9384,"est_transit_days":1},
# #     "Anora Group Oyj":                    {"city":"Helsinki, Finland","country":"FI","lat":60.1699,"lon":24.9384,"est_transit_days":1},
# #     "GRAHAM PACKAGING COMPANY OY":        {"city":"Hyvinkää, Finland","country":"FI","lat":60.6300,"lon":24.8600,"est_transit_days":1},
# #     "TARRAX OY":                          {"city":"Tampere, Finland","country":"FI","lat":61.4978,"lon":23.7610,"est_transit_days":1},
# #     "VWR INTERNATIONAL OY":               {"city":"Espoo, Finland","country":"FI","lat":60.2055,"lon":24.6559,"est_transit_days":1},
# #     "ROCHE DIAGNOSTICS DEUTSCHLAND GMBH": {"city":"Mannheim, Germany","country":"DE","lat":49.4875,"lon":8.4660,"est_transit_days":3},
# #     "ISP chemicals LLC":                  {"city":"Wayne, NJ, USA","country":"US","lat":40.9282,"lon":-74.2793,"est_transit_days":10},
# #     "Getra Oy":                           {"city":"Turku, Finland","country":"FI","lat":60.4518,"lon":22.2666,"est_transit_days":0},
# #     "Grano Oy":                           {"city":"Helsinki, Finland","country":"FI","lat":60.1699,"lon":24.9384,"est_transit_days":1},
# #     "STORAENSO PACKAGING OY":             {"city":"Helsinki, Finland","country":"FI","lat":60.1699,"lon":24.9384,"est_transit_days":1},
# #     "EMBALLATOR VAXJOPLAST":              {"city":"Växjö, Sweden","country":"SE","lat":56.8777,"lon":14.8091,"est_transit_days":2},
# #     "INFORMA OY":                         {"city":"Turku, Finland","country":"FI","lat":60.4518,"lon":22.2666,"est_transit_days":0},
# # }

# # PLANT_LOCATION = {"name":"Revvity FI11","city":"Turku, Finland","lat":60.4518,"lon":22.2666}


# # def calc_replenishment(ss: float, sih: float, fls: float, mls: float) -> dict:
# #     """
# #     Stakeholder-specified replenishment formula:
# #     Shortfall = SS - SIH
# #     If Shortfall <= 0 -> Order = 0
# #     If FLS > 0       -> CEILING(Shortfall / FLS) × FLS
# #     Elif MLS > 0     -> max(Shortfall, MLS)
# #     Else             -> Shortfall
# #     """
# #     shortfall = ss - sih
# #     if shortfall <= 0:
# #         return {"triggered": False, "quantity": 0, "shortfall": 0,
# #                 "reason": "Stock above safety stock", "formula_used": "No order"}
# #     if fls > 0:
# #         qty = math.ceil(shortfall / fls) * fls
# #         formula = f"CEILING({shortfall:.0f}/{fls:.0f})×{fls:.0f} = {qty:.0f}"
# #     elif mls > 0:
# #         qty = max(shortfall, mls)
# #         formula = f"max(shortfall={shortfall:.0f}, MLS={mls:.0f}) = {qty:.0f}"
# #     else:
# #         qty = shortfall
# #         formula = f"shortfall = {qty:.0f}"
# #     return {"triggered": True, "quantity": int(qty), "shortfall": int(shortfall),
# #             "reason": formula, "formula_used": formula}


# # def load_all() -> dict:
# #     df_sales = pd.read_excel(_resolve(DATA_FILES["sales"]), sheet_name="Export")
# #     df_sales = df_sales.dropna(subset=["material"])
# #     df_sales = df_sales[~df_sales["material"].astype(str).str.contains("Applied", na=False)]
# #     df_sales["ym"] = df_sales["calendar_year_period"].apply(
# #         lambda x: str(int(x))[:6] if pd.notna(x) else None)
# #     df_sales["calendar_date"] = pd.to_datetime(df_sales["calendar_date"], errors="coerce")

# #     df_lt = pd.read_excel(_resolve(DATA_FILES["inv_lt"]))
# #     df_lt = df_lt.dropna(subset=["Material"])
# #     df_lt = df_lt[df_lt["Fiscal Period"].astype(str).str.match(r"^\d{6}$")]
# #     df_lt = df_lt.sort_values("Fiscal Period")

# #     df_bom = pd.read_excel(_resolve(DATA_FILES["bom"]))

# #     df_mm = pd.read_excel(_resolve(DATA_FILES["mat_master"]))
# #     df_mm = df_mm.dropna(subset=["Material"])

# #     df_inv = pd.read_excel(_resolve(DATA_FILES["curr_inv"]))
# #     df_inv = df_inv.dropna(subset=["Material"])
# #     df_inv = df_inv[~df_inv["Material"].astype(str).str.contains("Applied", na=False)]

# #     return {"sales":df_sales,"inv_lt":df_lt,"bom":df_bom,"mat_master":df_mm,"curr_inv":df_inv}


# # def build_material_summary(data: dict) -> pd.DataFrame:
# #     df_lt=data["inv_lt"]; df_mm=data["mat_master"]; df_sales=data["sales"]
# #     ci=data["curr_inv"]

# #     monthly_demand=(
# #         df_sales.groupby(["material","ym"])["original_confirmed_qty"]
# #         .sum().reset_index())
# #     monthly_demand.columns=["material","period","demand"]

# #     rows=[]
# #     for mat in df_lt["Material"].unique():
# #         lt_sub=df_lt[df_lt.Material==mat].sort_values("Fiscal Period")
# #         mm_row=df_mm[df_mm.Material==mat]
# #         ci_row=ci[ci.Material.astype(str)==str(mat)]
# #         dem_sub=monthly_demand[monthly_demand.material==mat]

# #         current_stock  = float(lt_sub["Gross Stock"].iloc[-1]) if len(lt_sub)>0 else 0
# #         latest_period  = lt_sub["Fiscal Period"].iloc[-1] if len(lt_sub)>0 else "N/A"
# #         mat_name       = MATERIAL_LABELS.get(mat, lt_sub["Material Name"].iloc[0] if len(lt_sub)>0 else mat)
# #         ss_mm          = float(mm_row["Safety Stock"].values[0]) if len(mm_row)>0 else 0
# #         lead_time      = float(mm_row["Lead Time"].values[0]) if len(mm_row)>0 else 0
# #         inhouse_time   = float(mm_row["Inhouse production time"].values[0]) if len(mm_row)>0 else 0
# #         planned_lt     = float(mm_row["Planned delivery time in days"].values[0]) if len(mm_row)>0 else 0
# #         temp_cond      = mm_row["Temp. Conditions"].values[0] if len(mm_row)>0 else ""
# #         abcde          = mm_row["ABCDE Category"].values[0] if len(mm_row)>0 else ""
# #         lot_size       = float(mm_row["Fixed Lot Size"].values[0]) if len(mm_row)>0 else 0

# #         # Current inventory fields
# #         sih            = float(ci_row["Stock In Hand"].values[0]) if len(ci_row)>0 and pd.notna(ci_row["Stock In Hand"].values[0]) else current_stock
# #         fls_ci         = float(ci_row["Fixed Lot Size"].values[0]) if len(ci_row)>0 else lot_size
# #         mls_ci         = float(ci_row["Minimum Lot Size"].values[0]) if len(ci_row)>0 else 0
# #         reorder_pt     = float(ci_row["Reorder Point"].values[0]) if len(ci_row)>0 else 0

# #         nonzero_dem    = dem_sub[dem_sub.demand>0]
# #         avg_demand     = float(nonzero_dem.demand.mean()) if len(nonzero_dem)>0 else 0
# #         std_demand     = float(nonzero_dem.demand.std()) if len(nonzero_dem)>1 else 0
# #         total_periods  = len(lt_sub)
# #         zero_periods   = int((lt_sub["Gross Stock"]==0).sum())

# #         daily_demand   = avg_demand/30.0 if avg_demand>0 else 0
# #         # Use SIH for days cover calculation (consistent with replenishment)
# #         days_cover     = sih/daily_demand if daily_demand>0 else 999

# #         effective_lt   = max(lead_time, inhouse_time, planned_lt, 1)
# #         rec_ss         = round(1.65*std_demand*np.sqrt(effective_lt/30),0) if std_demand>0 else ss_mm

# #         breach_count   = int((lt_sub["Gross Stock"]<max(ss_mm,1)).sum()) if ss_mm>0 else 0

# #         if len(lt_sub)>=4:
# #             recent=lt_sub["Gross Stock"].tail(4).values
# #             td=float(recent[-1]-recent[0])
# #             trend_label="Declining" if td<-20 else ("Rising" if td>20 else "Stable")
# #         else:
# #             td=0; trend_label="Stable"

# #         # Replenishment (new formula)
# #         repl=calc_replenishment(ss_mm, sih, fls_ci, mls_ci)

# #         # Lead time urgency
# #         if days_cover<effective_lt:
# #             lt_urgency="CRITICAL - Cover < Lead Time"
# #         elif days_cover<effective_lt*2:
# #             lt_urgency="WARNING - Cover < 2× Lead Time"
# #         else:
# #             lt_urgency="OK"

# #         # Data quality flags
# #         dq_flags=[]
# #         if ss_mm==0: dq_flags.append("Safety stock = 0 in Material Master")
# #         if effective_lt<=1 and lead_time==0: dq_flags.append("Lead time = 0 (data gap)")
# #         if fls_ci==0 and mls_ci==0: dq_flags.append("No lot size configured")
# #         if len(nonzero_dem)<6: dq_flags.append(f"Only {len(nonzero_dem)} months demand data")
# #         if zero_periods>15: dq_flags.append(f"Zero stock in {zero_periods}/{total_periods} periods")

# #         if zero_periods>15 or len(nonzero_dem)<3 or mat=="3515-0010":
# #             risk="INSUFFICIENT_DATA"
# #         elif current_stock<ss_mm or days_cover<10:
# #             risk="CRITICAL"
# #         elif current_stock<ss_mm*1.5 or days_cover<30:
# #             risk="WARNING"
# #         else:
# #             risk="HEALTHY"

# #         rows.append({
# #             "material":mat,"name":mat_name,"current_stock":current_stock,
# #             "sih":sih,"safety_stock":ss_mm,"rec_safety_stock":rec_ss,
# #             "lead_time":effective_lt,"planned_lt":planned_lt,
# #             "avg_monthly_demand":round(avg_demand,1),"std_demand":round(std_demand,1),
# #             "days_cover":round(days_cover,1),"risk":risk,"trend":trend_label,
# #             "trend_delta":td,"zero_periods":zero_periods,"total_periods":total_periods,
# #             "breach_count":breach_count,"nonzero_demand_months":len(nonzero_dem),
# #             "temp_cond":str(temp_cond),"abcde":str(abcde),
# #             "lot_size":fls_ci,"min_lot_size":mls_ci,"reorder_point":reorder_pt,
# #             "latest_period":latest_period,"data_quality_flags":dq_flags,
# #             "repl_triggered":repl["triggered"],"repl_quantity":repl["quantity"],
# #             "repl_shortfall":repl["shortfall"],"repl_formula":repl["formula_used"],
# #             "lt_urgency":lt_urgency,
# #         })
# #     return pd.DataFrame(rows)


# # def get_stock_history(data: dict, material: str) -> pd.DataFrame:
# #     df=data["inv_lt"][data["inv_lt"].Material==material].copy()
# #     df=df.sort_values("Fiscal Period")
# #     df["period_dt"]=pd.to_datetime(df["Fiscal Period"],format="%Y%m")
# #     df["label"]=df["period_dt"].dt.strftime("%b '%y")
# #     return df[["Fiscal Period","period_dt","label","Gross Stock","Safety Stock",
# #                "Plan DelivTime","Inhouse Production"]].reset_index(drop=True)


# # def get_demand_history(data: dict, material: str) -> pd.DataFrame:
# #     df=data["sales"][data["sales"].material==material].copy()
# #     monthly=df.groupby("ym")["original_confirmed_qty"].sum().reset_index()
# #     monthly.columns=["period","demand"]
# #     monthly=monthly[monthly.period.notna()].sort_values("period")
# #     monthly["period_dt"]=pd.to_datetime(monthly["period"],format="%Y%m")
# #     monthly["label"]=monthly["period_dt"].dt.strftime("%b '%y")
# #     return monthly.reset_index(drop=True)


# # def get_bom_components(data: dict, material: str) -> pd.DataFrame:
# #     df=data["bom"][data["bom"]["Origin Material"]==material].copy()
# #     # Enrich procurement type: E=Inhouse(Revvity), F=External
# #     def get_supplier_display(row):
# #         proc=str(row.get("Procurement type","")).strip()
# #         sup=row.get("Supplier Name(Vendor)","")
# #         if proc=="E":
# #             return "Revvity Inhouse"
# #         elif proc=="F":
# #             if pd.notna(sup) and str(sup).strip():
# #                 return str(sup).strip()
# #             return "⚠ Not specified (External)"
# #         return str(sup) if pd.notna(sup) else "—"
# #     df["Supplier Display"]=df.apply(get_supplier_display, axis=1)
# #     df["Procurement Label"]=df["Procurement type"].apply(
# #         lambda x: "Inhouse (Revvity)" if str(x).strip()=="E" else ("External" if str(x).strip()=="F" else str(x)))
# #     # Fixed Quantity handling
# #     df["Fixed Qty Flag"]=df["Fixed quantity"].apply(lambda x: str(x).strip()=="X" if pd.notna(x) else False)
# #     df["Effective Order Qty"]=df.apply(
# #         lambda r: 1 if r["Fixed Qty Flag"] else r["Comp. Qty (CUn)"], axis=1)
# #     # Supplier location enrichment
# #     df["Supplier Location"]=df["Supplier Name(Vendor)"].apply(
# #         lambda s: SUPPLIER_LOCATIONS.get(str(s).strip(),{}).get("city","Unknown") if pd.notna(s) else "—")
# #     df["Supplier Lat"]=df["Supplier Name(Vendor)"].apply(
# #         lambda s: SUPPLIER_LOCATIONS.get(str(s).strip(),{}).get("lat",None) if pd.notna(s) else None)
# #     df["Supplier Lon"]=df["Supplier Name(Vendor)"].apply(
# #         lambda s: SUPPLIER_LOCATIONS.get(str(s).strip(),{}).get("lon",None) if pd.notna(s) else None)
# #     df["Transit Days"]=df["Supplier Name(Vendor)"].apply(
# #         lambda s: SUPPLIER_LOCATIONS.get(str(s).strip(),{}).get("est_transit_days",None) if pd.notna(s) else None)
# #     return df


# # def get_supplier_consolidation(data: dict, summary_df: pd.DataFrame) -> pd.DataFrame:
# #     """
# #     Key agentic insight: which suppliers supply multiple finished goods,
# #     and can we consolidate orders to the same supplier?
# #     """
# #     bom=data["bom"]
# #     bom_named=bom[bom["Supplier Name(Vendor)"].notna()].copy()
# #     rows=[]
# #     for sup, grp in bom_named.groupby("Supplier Name(Vendor)"):
# #         mats=grp["Origin Material"].unique().tolist()
# #         mat_names=[MATERIAL_LABELS.get(m,m) for m in mats]
# #         mats_needing_order=[m for m in mats
# #                             if len(summary_df[summary_df.material==m])>0
# #                             and summary_df[summary_df.material==m]["repl_triggered"].values[0]]
# #         total_order_value=sum([
# #             summary_df[summary_df.material==m]["repl_quantity"].values[0]
# #             if len(summary_df[summary_df.material==m])>0 else 0
# #             for m in mats_needing_order])
# #         loc=SUPPLIER_LOCATIONS.get(str(sup).strip(),{})
# #         email=grp["Supplier Email address(Vendor)"].dropna().iloc[0] if len(grp["Supplier Email address(Vendor)"].dropna())>0 else "—"
# #         phone=grp["Supplier contact phone number(Vendor)"].dropna().iloc[0] if len(grp["Supplier contact phone number(Vendor)"].dropna())>0 else "—"
# #         rows.append({
# #             "supplier":str(sup),"city":loc.get("city","Unknown"),
# #             "lat":loc.get("lat",None),"lon":loc.get("lon",None),
# #             "transit_days":loc.get("est_transit_days",None),
# #             "finished_goods_supplied":len(mats),
# #             "material_list":mats,"material_names":mat_names,
# #             "materials_needing_order":mats_needing_order,
# #             "consolidation_opportunity":len(mats_needing_order)>0,
# #             "email":email,"phone":str(phone),
# #         })
# #     return pd.DataFrame(rows).sort_values("finished_goods_supplied",ascending=False).reset_index(drop=True)


# # def get_material_context(data: dict, material: str, summary_df: pd.DataFrame) -> dict:
# #     stock_hist=get_stock_history(data, material)
# #     demand_hist=get_demand_history(data, material)
# #     bom=get_bom_components(data, material)
# #     mat_row=summary_df[summary_df.material==material]
# #     if len(mat_row)==0: return {}
# #     row=mat_row.iloc[0]

# #     ss=row["safety_stock"]
# #     breach_periods=stock_hist[stock_hist["Gross Stock"]<max(ss,1)]["Fiscal Period"].tolist() if ss>0 else []

# #     bom_summary=[]
# #     missing_sup=[]
# #     for _,b in bom.iterrows():
# #         sup_display=b.get("Supplier Display","—")
# #         is_inhouse=str(b.get("Procurement type","")).strip()=="E"
# #         is_missing=str(sup_display).startswith("⚠")
# #         if is_missing: missing_sup.append(str(b["Material Description"])[:30] if pd.notna(b["Material Description"]) else str(b["Material"]))
# #         bom_summary.append({
# #             "component":b["Material"],"description":str(b["Material Description"])[:40] if pd.notna(b["Material Description"]) else "—",
# #             "level":str(b["Level"])[:25] if pd.notna(b["Level"]) else "—",
# #             "qty":b["Effective Order Qty"] if "Effective Order Qty" in b else b["Comp. Qty (CUn)"],
# #             "fixed_qty":b.get("Fixed Qty Flag",False),
# #             "unit":b["Component unit"] if pd.notna(b["Component unit"]) else "—",
# #             "supplier":sup_display,"inhouse":is_inhouse,
# #             "location":b.get("Supplier Location","—"),
# #             "transit_days":b.get("Transit Days",None),
# #         })

# #     nonzero=demand_hist[demand_hist.demand>0]
# #     avg=round(float(nonzero.demand.mean()),1) if len(nonzero)>0 else 0
# #     spikes=demand_hist[demand_hist.demand>avg*2][["period","demand"]].to_dict("records") if avg>0 else []

# #     # Supplier consolidation for this material
# #     consolidation=get_supplier_consolidation(data, summary_df)
# #     relevant_consolidation=[]
# #     for _,sc_row in consolidation.iterrows():
# #         if material in sc_row["material_list"] and sc_row["finished_goods_supplied"]>1:
# #             relevant_consolidation.append({
# #                 "supplier":sc_row["supplier"],
# #                 "also_supplies":len(sc_row["material_list"])-1,
# #                 "consolidation_opportunity":sc_row["consolidation_opportunity"],
# #             })

# #     return {
# #         "material_id":material,"material_name":row["name"],
# #         "current_stock":row["current_stock"],"sih":row["sih"],
# #         "safety_stock_sap":row["safety_stock"],"rec_safety_stock":row["rec_safety_stock"],
# #         "lead_time_days":row["lead_time"],"lot_size":row["lot_size"],
# #         "min_lot_size":row["min_lot_size"],"risk_status":row["risk"],
# #         "trend":row["trend"],"days_cover":row["days_cover"],
# #         "lt_urgency":row["lt_urgency"],"temp_conditions":row["temp_cond"],
# #         "abcde_category":row["abcde"],
# #         "replenishment":{"triggered":row["repl_triggered"],"quantity":row["repl_quantity"],
# #                          "shortfall":row["repl_shortfall"],"formula":row["repl_formula"]},
# #         "breach_periods":breach_periods,
# #         "demand_stats":{"avg_monthly":avg,"max_monthly":round(float(nonzero.demand.max()),1) if len(nonzero)>0 else 0,
# #                         "std_monthly":round(float(nonzero.demand.std()),1) if len(nonzero)>1 else 0,
# #                         "nonzero_months":len(nonzero),"total_months":len(demand_hist),
# #                         "recent_6m":demand_hist["demand"].tail(6).tolist()},
# #         "spike_events":spikes,
# #         "bom_components":bom_summary,"total_bom_components":len(bom_summary),
# #         "missing_supplier_count":len(missing_sup),"missing_supplier_components":missing_sup,
# #         "supplier_consolidation":relevant_consolidation,
# #         "data_quality_flags":row["data_quality_flags"],
# #         "parameter_sources":{
# #             "safety_stock":"Material Master (Current Inventory = 0 for all SKUs)",
# #             "lead_time":"max(Lead Time, Inhouse Production Time, Planned Delivery Time)",
# #             "lot_size":"Current Inventory: Fixed Lot Size",
# #             "demand":"Sales file (includes write-offs, internal consumption)"},
# #     }

# """
# data_loader.py — ARIA Supply Intelligence
# Enhanced with:
# - Supplier reliability scores, geopolitical risk, alternative suppliers (dummy)
# - Transit days based on actual locations
# - Fixed replenishment formula
# - Consistent days cover calculation
# """

# import os, math, random
# import pandas as pd
# import numpy as np
# import warnings
# warnings.filterwarnings("ignore")

# _BASE = os.path.dirname(os.path.abspath(__file__))

# def _resolve(filename: str) -> str:
#     local = os.path.join(_BASE, "data", filename)
#     if os.path.exists(local): return local
#     upload = os.path.join("/mnt/user-data/uploads", filename)
#     if os.path.exists(upload): return upload
#     raise FileNotFoundError(f"Cannot find '{filename}' in data/ or uploads/")

# DATA_FILES = {
#     "sales":      "Sales_HistoricalData_Structured.xlsx",
#     "inv_lt":     "Inventory_Extract_and_Lead_Time.xlsx",
#     "bom":        "Fi11_BOM_MResult_v2.xlsx",
#     "mat_master": "Material_master_data_with_planning_parameters__Turku___Boston_.xlsx",
#     "curr_inv":   "Current_Inventory___planning_parameters__Turku_and_Boston_.xlsx",
# }

# MATERIAL_LABELS = {
#     "1244-104":  "DELFIA Enhancement Solution",
#     "1244-106":  "DELFIA Assay Buffer",
#     "13804314":  "Europium Solution 200ml",
#     "13807866":  "Anti-AFP AF5/A2 Antibody",
#     "13808190":  "Microplate Deep Well (LSD)",
#     "3014-0010": "DELFIA Wash Concentrate",
#     "3515-0010": "SARS-CoV-2 Plus Kit",
# }

# RISK_COLORS = {
#     "CRITICAL":          "#EF4444",
#     "WARNING":           "#F59E0B",
#     "HEALTHY":           "#22C55E",
#     "INSUFFICIENT_DATA": "#94A3B8",
# }

# # Enriched supplier data with dummy reliability and risk
# SUPPLIER_LOCATIONS = {
#     "Merck Life Science Oy":              {"city":"Helsinki, Finland","country":"FI","lat":60.1699,"lon":24.9384,"est_transit_days":1,"reliability":0.92,"geo_risk":0.05},
#     "Anora Group Oyj":                    {"city":"Helsinki, Finland","country":"FI","lat":60.1699,"lon":24.9384,"est_transit_days":1,"reliability":0.88,"geo_risk":0.05},
#     "GRAHAM PACKAGING COMPANY OY":        {"city":"Hyvinkää, Finland","country":"FI","lat":60.6300,"lon":24.8600,"est_transit_days":1,"reliability":0.85,"geo_risk":0.05},
#     "TARRAX OY":                          {"city":"Tampere, Finland","country":"FI","lat":61.4978,"lon":23.7610,"est_transit_days":1,"reliability":0.90,"geo_risk":0.05},
#     "VWR INTERNATIONAL OY":               {"city":"Espoo, Finland","country":"FI","lat":60.2055,"lon":24.6559,"est_transit_days":1,"reliability":0.91,"geo_risk":0.05},
#     "ROCHE DIAGNOSTICS DEUTSCHLAND GMBH": {"city":"Mannheim, Germany","country":"DE","lat":49.4875,"lon":8.4660,"est_transit_days":3,"reliability":0.95,"geo_risk":0.10},
#     "ISP chemicals LLC":                  {"city":"Wayne, NJ, USA","country":"US","lat":40.9282,"lon":-74.2793,"est_transit_days":10,"reliability":0.82,"geo_risk":0.25},
#     "Getra Oy":                           {"city":"Turku, Finland","country":"FI","lat":60.4518,"lon":22.2666,"est_transit_days":0,"reliability":0.96,"geo_risk":0.05},
#     "Grano Oy":                           {"city":"Helsinki, Finland","country":"FI","lat":60.1699,"lon":24.9384,"est_transit_days":1,"reliability":0.89,"geo_risk":0.05},
#     "STORAENSO PACKAGING OY":             {"city":"Helsinki, Finland","country":"FI","lat":60.1699,"lon":24.9384,"est_transit_days":1,"reliability":0.87,"geo_risk":0.05},
#     "EMBALLATOR VAXJOPLAST":              {"city":"Växjö, Sweden","country":"SE","lat":56.8777,"lon":14.8091,"est_transit_days":2,"reliability":0.93,"geo_risk":0.05},
#     "INFORMA OY":                         {"city":"Turku, Finland","country":"FI","lat":60.4518,"lon":22.2666,"est_transit_days":0,"reliability":0.94,"geo_risk":0.05},
# }

# # Add alternative suppliers (dummy)
# ALTERNATIVE_SUPPLIERS = {
#     "ISP chemicals LLC": ["Sigma-Aldrich USA", "Thermo Fisher USA"],
#     "ROCHE DIAGNOSTICS DEUTSCHLAND GMBH": ["Siemens Healthineers DE", "Abbott DE"],
#     "Merck Life Science Oy": ["Thermo Fisher FI", "VWR FI"],
# }

# PLANT_LOCATION = {"name":"Revvity FI11","city":"Turku, Finland","lat":60.4518,"lon":22.2666}

# def calc_replenishment(ss: float, sih: float, fls: float, mls: float) -> dict:
#     """Stakeholder-specified replenishment formula."""
#     shortfall = ss - sih
#     if shortfall <= 0:
#         return {"triggered": False, "quantity": 0, "shortfall": 0,
#                 "reason": "Stock above safety stock", "formula_used": "No order"}
#     if fls > 0:
#         qty = math.ceil(shortfall / fls) * fls
#         formula = f"CEILING({shortfall:.0f}/{fls:.0f})×{fls:.0f} = {qty:.0f}"
#     elif mls > 0:
#         qty = max(shortfall, mls)
#         formula = f"max(shortfall={shortfall:.0f}, MLS={mls:.0f}) = {qty:.0f}"
#     else:
#         qty = shortfall
#         formula = f"shortfall = {qty:.0f}"
#     return {"triggered": True, "quantity": int(qty), "shortfall": int(shortfall),
#             "reason": formula, "formula_used": formula}

# def load_all() -> dict:
#     df_sales = pd.read_excel(_resolve(DATA_FILES["sales"]), sheet_name="Export")
#     df_sales = df_sales.dropna(subset=["material"])
#     df_sales = df_sales[~df_sales["material"].astype(str).str.contains("Applied", na=False)]
#     df_sales["ym"] = df_sales["calendar_year_period"].apply(
#         lambda x: str(int(x))[:6] if pd.notna(x) else None)
#     df_sales["calendar_date"] = pd.to_datetime(df_sales["calendar_date"], errors="coerce")

#     df_lt = pd.read_excel(_resolve(DATA_FILES["inv_lt"]))
#     df_lt = df_lt.dropna(subset=["Material"])
#     df_lt = df_lt[df_lt["Fiscal Period"].astype(str).str.match(r"^\d{6}$")]
#     df_lt = df_lt.sort_values("Fiscal Period")

#     df_bom = pd.read_excel(_resolve(DATA_FILES["bom"]))

#     df_mm = pd.read_excel(_resolve(DATA_FILES["mat_master"]))
#     df_mm = df_mm.dropna(subset=["Material"])

#     df_inv = pd.read_excel(_resolve(DATA_FILES["curr_inv"]))
#     df_inv = df_inv.dropna(subset=["Material"])
#     df_inv = df_inv[~df_inv["Material"].astype(str).str.contains("Applied", na=False)]

#     return {"sales":df_sales,"inv_lt":df_lt,"bom":df_bom,"mat_master":df_mm,"curr_inv":df_inv}

# def build_material_summary(data: dict) -> pd.DataFrame:
#     df_lt=data["inv_lt"]; df_mm=data["mat_master"]; df_sales=data["sales"]
#     ci=data["curr_inv"]

#     monthly_demand=(
#         df_sales.groupby(["material","ym"])["original_confirmed_qty"]
#         .sum().reset_index())
#     monthly_demand.columns=["material","period","demand"]

#     rows=[]
#     for mat in df_lt["Material"].unique():
#         lt_sub=df_lt[df_lt.Material==mat].sort_values("Fiscal Period")
#         mm_row=df_mm[df_mm.Material==mat]
#         ci_row=ci[ci.Material.astype(str)==str(mat)]
#         dem_sub=monthly_demand[monthly_demand.material==mat]

#         current_stock  = float(lt_sub["Gross Stock"].iloc[-1]) if len(lt_sub)>0 else 0
#         latest_period  = lt_sub["Fiscal Period"].iloc[-1] if len(lt_sub)>0 else "N/A"
#         mat_name       = MATERIAL_LABELS.get(mat, lt_sub["Material Name"].iloc[0] if len(lt_sub)>0 else mat)
#         ss_mm          = float(mm_row["Safety Stock"].values[0]) if len(mm_row)>0 else 0
#         lead_time      = float(mm_row["Lead Time"].values[0]) if len(mm_row)>0 else 0
#         inhouse_time   = float(mm_row["Inhouse production time"].values[0]) if len(mm_row)>0 else 0
#         planned_lt     = float(mm_row["Planned delivery time in days"].values[0]) if len(mm_row)>0 else 0
#         temp_cond      = mm_row["Temp. Conditions"].values[0] if len(mm_row)>0 else ""
#         abcde          = mm_row["ABCDE Category"].values[0] if len(mm_row)>0 else ""
#         lot_size       = float(mm_row["Fixed Lot Size"].values[0]) if len(mm_row)>0 else 0

#         sih            = float(ci_row["Stock In Hand"].values[0]) if len(ci_row)>0 and pd.notna(ci_row["Stock In Hand"].values[0]) else current_stock
#         fls_ci         = float(ci_row["Fixed Lot Size"].values[0]) if len(ci_row)>0 else lot_size
#         mls_ci         = float(ci_row["Minimum Lot Size"].values[0]) if len(ci_row)>0 else 0
#         reorder_pt     = float(ci_row["Reorder Point"].values[0]) if len(ci_row)>0 else 0

#         nonzero_dem    = dem_sub[dem_sub.demand>0]
#         avg_demand     = float(nonzero_dem.demand.mean()) if len(nonzero_dem)>0 else 0
#         std_demand     = float(nonzero_dem.demand.std()) if len(nonzero_dem)>1 else 0
#         total_periods  = len(lt_sub)
#         zero_periods   = int((lt_sub["Gross Stock"]==0).sum())

#         daily_demand   = avg_demand/30.0 if avg_demand>0 else 0
#         days_cover     = sih/daily_demand if daily_demand>0 else 999

#         effective_lt   = max(lead_time, inhouse_time, planned_lt, 1)
#         rec_ss         = round(1.65*std_demand*np.sqrt(effective_lt/30),0) if std_demand>0 else ss_mm

#         breach_count   = int((lt_sub["Gross Stock"]<max(ss_mm,1)).sum()) if ss_mm>0 else 0

#         if len(lt_sub)>=4:
#             recent=lt_sub["Gross Stock"].tail(4).values
#             td=float(recent[-1]-recent[0])
#             trend_label="Declining" if td<-20 else ("Rising" if td>20 else "Stable")
#         else:
#             td=0; trend_label="Stable"

#         repl=calc_replenishment(ss_mm, sih, fls_ci, mls_ci)

#         if days_cover<effective_lt:
#             lt_urgency="CRITICAL - Cover < Lead Time"
#         elif days_cover<effective_lt*2:
#             lt_urgency="WARNING - Cover < 2× Lead Time"
#         else:
#             lt_urgency="OK"

#         dq_flags=[]
#         if ss_mm==0: dq_flags.append("Safety stock = 0 in Material Master")
#         if effective_lt<=1 and lead_time==0: dq_flags.append("Lead time = 0 (data gap)")
#         if fls_ci==0 and mls_ci==0: dq_flags.append("No lot size configured")
#         if len(nonzero_dem)<6: dq_flags.append(f"Only {len(nonzero_dem)} months demand data")
#         if zero_periods>15: dq_flags.append(f"Zero stock in {zero_periods}/{total_periods} periods")

#         if zero_periods>15 or len(nonzero_dem)<3 or mat=="3515-0010":
#             risk="INSUFFICIENT_DATA"
#         elif current_stock<ss_mm or days_cover<10:
#             risk="CRITICAL"
#         elif current_stock<ss_mm*1.5 or days_cover<30:
#             risk="WARNING"
#         else:
#             risk="HEALTHY"

#         rows.append({
#             "material":mat,"name":mat_name,"current_stock":current_stock,
#             "sih":sih,"safety_stock":ss_mm,"rec_safety_stock":rec_ss,
#             "lead_time":effective_lt,"planned_lt":planned_lt,
#             "avg_monthly_demand":round(avg_demand,1),"std_demand":round(std_demand,1),
#             "days_cover":round(days_cover,1),"risk":risk,"trend":trend_label,
#             "trend_delta":td,"zero_periods":zero_periods,"total_periods":total_periods,
#             "breach_count":breach_count,"nonzero_demand_months":len(nonzero_dem),
#             "temp_cond":str(temp_cond),"abcde":str(abcde),
#             "lot_size":fls_ci,"min_lot_size":mls_ci,"reorder_point":reorder_pt,
#             "latest_period":latest_period,"data_quality_flags":dq_flags,
#             "repl_triggered":repl["triggered"],"repl_quantity":repl["quantity"],
#             "repl_shortfall":repl["shortfall"],"repl_formula":repl["formula_used"],
#             "lt_urgency":lt_urgency,
#         })
#     return pd.DataFrame(rows)

# def get_stock_history(data: dict, material: str) -> pd.DataFrame:
#     df=data["inv_lt"][data["inv_lt"].Material==material].copy()
#     df=df.sort_values("Fiscal Period")
#     df["period_dt"]=pd.to_datetime(df["Fiscal Period"],format="%Y%m")
#     df["label"]=df["period_dt"].dt.strftime("%b '%y")
#     return df[["Fiscal Period","period_dt","label","Gross Stock","Safety Stock",
#                "Plan DelivTime","Inhouse Production"]].reset_index(drop=True)

# def get_demand_history(data: dict, material: str) -> pd.DataFrame:
#     df=data["sales"][data["sales"].material==material].copy()
#     monthly=df.groupby("ym")["original_confirmed_qty"].sum().reset_index()
#     monthly.columns=["period","demand"]
#     monthly=monthly[monthly.period.notna()].sort_values("period")
#     monthly["period_dt"]=pd.to_datetime(monthly["period"],format="%Y%m")
#     monthly["label"]=monthly["period_dt"].dt.strftime("%b '%y")
#     return monthly.reset_index(drop=True)

# def get_bom_components(data: dict, material: str) -> pd.DataFrame:
#     df=data["bom"][data["bom"]["Origin Material"]==material].copy()
#     def get_supplier_display(row):
#         proc=str(row.get("Procurement type","")).strip()
#         sup=row.get("Supplier Name(Vendor)","")
#         if proc=="E":
#             return "Revvity Inhouse"
#         elif proc=="F":
#             if pd.notna(sup) and str(sup).strip():
#                 return str(sup).strip()
#             return "⚠ Not specified (External)"
#         return str(sup) if pd.notna(sup) else "—"
#     df["Supplier Display"]=df.apply(get_supplier_display, axis=1)
#     df["Procurement Label"]=df["Procurement type"].apply(
#         lambda x: "Inhouse (Revvity)" if str(x).strip()=="E" else ("External" if str(x).strip()=="F" else str(x)))
#     df["Fixed Qty Flag"]=df["Fixed quantity"].apply(lambda x: str(x).strip()=="X" if pd.notna(x) else False)
#     df["Effective Order Qty"]=df.apply(
#         lambda r: 1 if r["Fixed Qty Flag"] else r["Comp. Qty (CUn)"], axis=1)
#     # Enrich supplier data
#     df["Supplier Location"]=df["Supplier Name(Vendor)"].apply(
#         lambda s: SUPPLIER_LOCATIONS.get(str(s).strip(),{}).get("city","Unknown") if pd.notna(s) else "—")
#     df["Supplier Lat"]=df["Supplier Name(Vendor)"].apply(
#         lambda s: SUPPLIER_LOCATIONS.get(str(s).strip(),{}).get("lat",None) if pd.notna(s) else None)
#     df["Supplier Lon"]=df["Supplier Name(Vendor)"].apply(
#         lambda s: SUPPLIER_LOCATIONS.get(str(s).strip(),{}).get("lon",None) if pd.notna(s) else None)
#     df["Transit Days"]=df["Supplier Name(Vendor)"].apply(
#         lambda s: SUPPLIER_LOCATIONS.get(str(s).strip(),{}).get("est_transit_days",None) if pd.notna(s) else None)
#     df["Supplier Reliability"]=df["Supplier Name(Vendor)"].apply(
#         lambda s: SUPPLIER_LOCATIONS.get(str(s).strip(),{}).get("reliability",0.8) if pd.notna(s) else None)
#     df["Geo Risk Score"]=df["Supplier Name(Vendor)"].apply(
#         lambda s: SUPPLIER_LOCATIONS.get(str(s).strip(),{}).get("geo_risk",0.1) if pd.notna(s) else None)
#     df["Alternative Suppliers"]=df["Supplier Name(Vendor)"].apply(
#         lambda s: ", ".join(ALTERNATIVE_SUPPLIERS.get(str(s).strip(), [])) if pd.notna(s) else "—")
#     return df

# def get_supplier_consolidation(data: dict, summary_df: pd.DataFrame) -> pd.DataFrame:
#     bom=data["bom"]
#     bom_named=bom[bom["Supplier Name(Vendor)"].notna()].copy()
#     rows=[]
#     for sup, grp in bom_named.groupby("Supplier Name(Vendor)"):
#         mats=grp["Origin Material"].unique().tolist()
#         mat_names=[MATERIAL_LABELS.get(m,m) for m in mats]
#         mats_needing_order=[m for m in mats
#                             if len(summary_df[summary_df.material==m])>0
#                             and summary_df[summary_df.material==m]["repl_triggered"].values[0]]
#         total_order_value=sum([
#             summary_df[summary_df.material==m]["repl_quantity"].values[0]
#             if len(summary_df[summary_df.material==m])>0 else 0
#             for m in mats_needing_order])
#         loc=SUPPLIER_LOCATIONS.get(str(sup).strip(),{})
#         email=grp["Supplier Email address(Vendor)"].dropna().iloc[0] if len(grp["Supplier Email address(Vendor)"].dropna())>0 else "—"
#         phone=grp["Supplier contact phone number(Vendor)"].dropna().iloc[0] if len(grp["Supplier contact phone number(Vendor)"].dropna())>0 else "—"
#         rows.append({
#             "supplier":str(sup),"city":loc.get("city","Unknown"),
#             "lat":loc.get("lat",None),"lon":loc.get("lon",None),
#             "transit_days":loc.get("est_transit_days",None),
#             "reliability":loc.get("reliability",0.8),
#             "geo_risk":loc.get("geo_risk",0.1),
#             "finished_goods_supplied":len(mats),
#             "material_list":mats,"material_names":mat_names,
#             "materials_needing_order":mats_needing_order,
#             "consolidation_opportunity":len(mats_needing_order)>0,
#             "email":email,"phone":str(phone),
#         })
#     return pd.DataFrame(rows).sort_values("finished_goods_supplied",ascending=False).reset_index(drop=True)

# def get_material_context(data: dict, material: str, summary_df: pd.DataFrame) -> dict:
#     stock_hist=get_stock_history(data, material)
#     demand_hist=get_demand_history(data, material)
#     bom=get_bom_components(data, material)
#     mat_row=summary_df[summary_df.material==material]
#     if len(mat_row)==0: return {}
#     row=mat_row.iloc[0]

#     ss=row["safety_stock"]
#     breach_periods=stock_hist[stock_hist["Gross Stock"]<max(ss,1)]["Fiscal Period"].tolist() if ss>0 else []

#     bom_summary=[]
#     missing_sup=[]
#     for _,b in bom.iterrows():
#         sup_display=b.get("Supplier Display","—")
#         is_inhouse=str(b.get("Procurement type","")).strip()=="E"
#         is_missing=str(sup_display).startswith("⚠")
#         if is_missing: missing_sup.append(str(b["Material Description"])[:30] if pd.notna(b["Material Description"]) else str(b["Material"]))
#         bom_summary.append({
#             "component":b["Material"],"description":str(b["Material Description"])[:40] if pd.notna(b["Material Description"]) else "—",
#             "level":str(b["Level"])[:25] if pd.notna(b["Level"]) else "—",
#             "qty":b["Effective Order Qty"] if "Effective Order Qty" in b else b["Comp. Qty (CUn)"],
#             "fixed_qty":b.get("Fixed Qty Flag",False),
#             "unit":b["Component unit"] if pd.notna(b["Component unit"]) else "—",
#             "supplier":sup_display,"inhouse":is_inhouse,
#             "location":b.get("Supplier Location","—"),
#             "transit_days":b.get("Transit Days",None),
#             "reliability":b.get("Supplier Reliability",None),
#             "geo_risk":b.get("Geo Risk Score",None),
#             "alternatives":b.get("Alternative Suppliers","—"),
#         })

#     nonzero=demand_hist[demand_hist.demand>0]
#     avg=round(float(nonzero.demand.mean()),1) if len(nonzero)>0 else 0
#     spikes=demand_hist[demand_hist.demand>avg*2][["period","demand"]].to_dict("records") if avg>0 else []

#     consolidation=get_supplier_consolidation(data, summary_df)
#     relevant_consolidation=[]
#     for _,sc_row in consolidation.iterrows():
#         if material in sc_row["material_list"] and sc_row["finished_goods_supplied"]>1:
#             relevant_consolidation.append({
#                 "supplier":sc_row["supplier"],
#                 "also_supplies":len(sc_row["material_list"])-1,
#                 "consolidation_opportunity":sc_row["consolidation_opportunity"],
#                 "transit_days":sc_row["transit_days"],
#                 "reliability":sc_row["reliability"],
#             })

#     return {
#         "material_id":material,"material_name":row["name"],
#         "current_stock":row["current_stock"],"sih":row["sih"],
#         "safety_stock_sap":row["safety_stock"],"rec_safety_stock":row["rec_safety_stock"],
#         "lead_time_days":row["lead_time"],"lot_size":row["lot_size"],
#         "min_lot_size":row["min_lot_size"],"risk_status":row["risk"],
#         "trend":row["trend"],"days_cover":row["days_cover"],
#         "lt_urgency":row["lt_urgency"],"temp_conditions":row["temp_cond"],
#         "abcde_category":row["abcde"],
#         "replenishment":{"triggered":row["repl_triggered"],"quantity":row["repl_quantity"],
#                          "shortfall":row["repl_shortfall"],"formula":row["repl_formula"]},
#         "breach_periods":breach_periods,
#         "demand_stats":{"avg_monthly":avg,"max_monthly":round(float(nonzero.demand.max()),1) if len(nonzero)>0 else 0,
#                         "std_monthly":round(float(nonzero.demand.std()),1) if len(nonzero)>1 else 0,
#                         "nonzero_months":len(nonzero),"total_months":len(demand_hist),
#                         "recent_6m":demand_hist["demand"].tail(6).tolist()},
#         "spike_events":spikes,
#         "bom_components":bom_summary,"total_bom_components":len(bom_summary),
#         "missing_supplier_count":len(missing_sup),"missing_supplier_components":missing_sup,
#         "supplier_consolidation":relevant_consolidation,
#         "data_quality_flags":row["data_quality_flags"],
#         "parameter_sources":{
#             "safety_stock":"Material Master (Current Inventory = 0 for all SKUs)",
#             "lead_time":"max(Lead Time, Inhouse Production Time, Planned Delivery Time)",
#             "lot_size":"Current Inventory: Fixed Lot Size",
#             "demand":"Sales file (includes write-offs, internal consumption)"},
#     }

"""
data_loader.py — ARIA Supply Intelligence
Enhanced with:
- Supplier reliability scores, geopolitical risk, alternative suppliers (dummy)
- Transit days based on actual locations
- Fixed replenishment formula
- Consistent days cover calculation
- Lead time correction: prioritise inhouse_time (correct for DELFIA Enhancement Solution)
"""

import os, math, random
import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings("ignore")

_BASE = os.path.dirname(os.path.abspath(__file__))

def _resolve(filename: str) -> str:
    local = os.path.join(_BASE, "data", filename)
    if os.path.exists(local): return local
    upload = os.path.join("/mnt/user-data/uploads", filename)
    if os.path.exists(upload): return upload
    raise FileNotFoundError(f"Cannot find '{filename}' in data/ or uploads/")

DATA_FILES = {
    "sales":      "Sales_HistoricalData_Structured.xlsx",
    "inv_lt":     "Inventory_Extract_and_Lead_Time.xlsx",
    "bom":        "Fi11_BOM_MResult_v2.xlsx",
    "mat_master": "Material_master_data_with_planning_parameters__Turku___Boston_.xlsx",
    "curr_inv":   "Current_Inventory___planning_parameters__Turku_and_Boston_.xlsx",
}

MATERIAL_LABELS = {
    "1244-104":  "DELFIA Enhancement Solution",
    "1244-106":  "DELFIA Assay Buffer",
    "13804314":  "Europium Solution 200ml",
    "13807866":  "Anti-AFP AF5/A2 Antibody",
    "13808190":  "Microplate Deep Well (LSD)",
    "3014-0010": "DELFIA Wash Concentrate",
    "3515-0010": "SARS-CoV-2 Plus Kit",
}

RISK_COLORS = {
    "CRITICAL":          "#EF4444",
    "WARNING":           "#F59E0B",
    "HEALTHY":           "#22C55E",
    "INSUFFICIENT_DATA": "#94A3B8",
}

# Enriched supplier data with dummy reliability and risk
SUPPLIER_LOCATIONS = {
    "Merck Life Science Oy":              {"city":"Helsinki, Finland","country":"FI","lat":60.1699,"lon":24.9384,"est_transit_days":1,"reliability":0.92,"geo_risk":0.05},
    "Anora Group Oyj":                    {"city":"Helsinki, Finland","country":"FI","lat":60.1699,"lon":24.9384,"est_transit_days":1,"reliability":0.88,"geo_risk":0.05},
    "GRAHAM PACKAGING COMPANY OY":        {"city":"Hyvinkää, Finland","country":"FI","lat":60.6300,"lon":24.8600,"est_transit_days":1,"reliability":0.85,"geo_risk":0.05},
    "TARRAX OY":                          {"city":"Tampere, Finland","country":"FI","lat":61.4978,"lon":23.7610,"est_transit_days":1,"reliability":0.90,"geo_risk":0.05},
    "VWR INTERNATIONAL OY":               {"city":"Espoo, Finland","country":"FI","lat":60.2055,"lon":24.6559,"est_transit_days":1,"reliability":0.91,"geo_risk":0.05},
    "ROCHE DIAGNOSTICS DEUTSCHLAND GMBH": {"city":"Mannheim, Germany","country":"DE","lat":49.4875,"lon":8.4660,"est_transit_days":3,"reliability":0.95,"geo_risk":0.10},
    "ISP chemicals LLC":                  {"city":"Wayne, NJ, USA","country":"US","lat":40.9282,"lon":-74.2793,"est_transit_days":10,"reliability":0.82,"geo_risk":0.25},
    "Getra Oy":                           {"city":"Turku, Finland","country":"FI","lat":60.4518,"lon":22.2666,"est_transit_days":0,"reliability":0.96,"geo_risk":0.05},
    "Grano Oy":                           {"city":"Helsinki, Finland","country":"FI","lat":60.1699,"lon":24.9384,"est_transit_days":1,"reliability":0.89,"geo_risk":0.05},
    "STORAENSO PACKAGING OY":             {"city":"Helsinki, Finland","country":"FI","lat":60.1699,"lon":24.9384,"est_transit_days":1,"reliability":0.87,"geo_risk":0.05},
    "EMBALLATOR VAXJOPLAST":              {"city":"Växjö, Sweden","country":"SE","lat":56.8777,"lon":14.8091,"est_transit_days":2,"reliability":0.93,"geo_risk":0.05},
    "INFORMA OY":                         {"city":"Turku, Finland","country":"FI","lat":60.4518,"lon":22.2666,"est_transit_days":0,"reliability":0.94,"geo_risk":0.05},
}

# Add alternative suppliers (dummy)
ALTERNATIVE_SUPPLIERS = {
    "ISP chemicals LLC": ["Sigma-Aldrich USA", "Thermo Fisher USA"],
    "ROCHE DIAGNOSTICS DEUTSCHLAND GMBH": ["Siemens Healthineers DE", "Abbott DE"],
    "Merck Life Science Oy": ["Thermo Fisher FI", "VWR FI"],
}

PLANT_LOCATION = {"name":"Revvity FI11","city":"Turku, Finland","lat":60.4518,"lon":22.2666}

def calc_replenishment(ss: float, sih: float, fls: float, mls: float) -> dict:
    """Stakeholder-specified replenishment formula."""
    shortfall = ss - sih
    if shortfall <= 0:
        return {"triggered": False, "quantity": 0, "shortfall": 0,
                "reason": "Stock above safety stock", "formula_used": "No order"}
    if fls > 0:
        qty = math.ceil(shortfall / fls) * fls
        formula = f"CEILING({shortfall:.0f}/{fls:.0f})×{fls:.0f} = {qty:.0f}"
    elif mls > 0:
        qty = max(shortfall, mls)
        formula = f"max(shortfall={shortfall:.0f}, MLS={mls:.0f}) = {qty:.0f}"
    else:
        qty = shortfall
        formula = f"shortfall = {qty:.0f}"
    return {"triggered": True, "quantity": int(qty), "shortfall": int(shortfall),
            "reason": formula, "formula_used": formula}

def load_all() -> dict:
    df_sales = pd.read_excel(_resolve(DATA_FILES["sales"]), sheet_name="Export")
    df_sales = df_sales.dropna(subset=["material"])
    df_sales = df_sales[~df_sales["material"].astype(str).str.contains("Applied", na=False)]
    df_sales["ym"] = df_sales["calendar_year_period"].apply(
        lambda x: str(int(x))[:6] if pd.notna(x) else None)
    df_sales["calendar_date"] = pd.to_datetime(df_sales["calendar_date"], errors="coerce")

    df_lt = pd.read_excel(_resolve(DATA_FILES["inv_lt"]))
    df_lt = df_lt.dropna(subset=["Material"])
    df_lt = df_lt[df_lt["Fiscal Period"].astype(str).str.match(r"^\d{6}$")]
    df_lt = df_lt.sort_values("Fiscal Period")

    df_bom = pd.read_excel(_resolve(DATA_FILES["bom"]))

    df_mm = pd.read_excel(_resolve(DATA_FILES["mat_master"]))
    df_mm = df_mm.dropna(subset=["Material"])

    df_inv = pd.read_excel(_resolve(DATA_FILES["curr_inv"]))
    df_inv = df_inv.dropna(subset=["Material"])
    df_inv = df_inv[~df_inv["Material"].astype(str).str.contains("Applied", na=False)]

    return {"sales":df_sales,"inv_lt":df_lt,"bom":df_bom,"mat_master":df_mm,"curr_inv":df_inv}

def build_material_summary(data: dict) -> pd.DataFrame:
    df_lt=data["inv_lt"]; df_mm=data["mat_master"]; df_sales=data["sales"]
    ci=data["curr_inv"]

    monthly_demand=(
        df_sales.groupby(["material","ym"])["original_confirmed_qty"]
        .sum().reset_index())
    monthly_demand.columns=["material","period","demand"]

    rows=[]
    for mat in df_lt["Material"].unique():
        lt_sub=df_lt[df_lt.Material==mat].sort_values("Fiscal Period")
        mm_row=df_mm[df_mm.Material==mat]
        ci_row=ci[ci.Material.astype(str)==str(mat)]
        dem_sub=monthly_demand[monthly_demand.material==mat]

        current_stock  = float(lt_sub["Gross Stock"].iloc[-1]) if len(lt_sub)>0 else 0
        latest_period  = lt_sub["Fiscal Period"].iloc[-1] if len(lt_sub)>0 else "N/A"
        mat_name       = MATERIAL_LABELS.get(mat, lt_sub["Material Name"].iloc[0] if len(lt_sub)>0 else mat)
        ss_mm          = float(mm_row["Safety Stock"].values[0]) if len(mm_row)>0 else 0
        lead_time      = float(mm_row["Lead Time"].values[0]) if len(mm_row)>0 else 0
        inhouse_time   = float(mm_row["Inhouse production time"].values[0]) if len(mm_row)>0 else 0
        planned_lt     = float(mm_row["Planned delivery time in days"].values[0]) if len(mm_row)>0 else 0
        temp_cond      = mm_row["Temp. Conditions"].values[0] if len(mm_row)>0 else ""
        abcde          = mm_row["ABCDE Category"].values[0] if len(mm_row)>0 else ""
        lot_size       = float(mm_row["Fixed Lot Size"].values[0]) if len(mm_row)>0 else 0

        sih            = float(ci_row["Stock In Hand"].values[0]) if len(ci_row)>0 and pd.notna(ci_row["Stock In Hand"].values[0]) else current_stock
        fls_ci         = float(ci_row["Fixed Lot Size"].values[0]) if len(ci_row)>0 else lot_size
        mls_ci         = float(ci_row["Minimum Lot Size"].values[0]) if len(ci_row)>0 else 0
        reorder_pt     = float(ci_row["Reorder Point"].values[0]) if len(ci_row)>0 else 0

        nonzero_dem    = dem_sub[dem_sub.demand>0]
        avg_demand     = float(nonzero_dem.demand.mean()) if len(nonzero_dem)>0 else 0
        std_demand     = float(nonzero_dem.demand.std()) if len(nonzero_dem)>1 else 0
        total_periods  = len(lt_sub)
        zero_periods   = int((lt_sub["Gross Stock"]==0).sum())

        daily_demand   = avg_demand/30.0 if avg_demand>0 else 0
        days_cover     = sih/daily_demand if daily_demand>0 else 999

        # ========== FIX #2: Lead time correction – prioritise inhouse_time ==========
        if inhouse_time > 0:
            effective_lt = inhouse_time
        elif planned_lt > 0:
            effective_lt = planned_lt
        elif lead_time > 0:
            effective_lt = lead_time
        else:
            effective_lt = 1
        # ==========================================================================

        rec_ss         = round(1.65*std_demand*np.sqrt(effective_lt/30),0) if std_demand>0 else ss_mm

        breach_count   = int((lt_sub["Gross Stock"]<max(ss_mm,1)).sum()) if ss_mm>0 else 0

        if len(lt_sub)>=4:
            recent=lt_sub["Gross Stock"].tail(4).values
            td=float(recent[-1]-recent[0])
            trend_label="Declining" if td<-20 else ("Rising" if td>20 else "Stable")
        else:
            td=0; trend_label="Stable"

        repl=calc_replenishment(ss_mm, sih, fls_ci, mls_ci)

        if days_cover<effective_lt:
            lt_urgency="CRITICAL - Cover < Lead Time"
        elif days_cover<effective_lt*2:
            lt_urgency="WARNING - Cover < 2× Lead Time"
        else:
            lt_urgency="OK"

        dq_flags=[]
        if ss_mm==0: dq_flags.append("Safety stock = 0 in Material Master")
        if effective_lt<=1 and lead_time==0: dq_flags.append("Lead time = 0 (data gap)")
        if fls_ci==0 and mls_ci==0: dq_flags.append("No lot size configured")
        if len(nonzero_dem)<6: dq_flags.append(f"Only {len(nonzero_dem)} months demand data")
        if zero_periods>15: dq_flags.append(f"Zero stock in {zero_periods}/{total_periods} periods")

        if zero_periods>15 or len(nonzero_dem)<3 or mat=="3515-0010":
            risk="INSUFFICIENT_DATA"
        elif current_stock<ss_mm or days_cover<10:
            risk="CRITICAL"
        elif current_stock<ss_mm*1.5 or days_cover<30:
            risk="WARNING"
        else:
            risk="HEALTHY"

        rows.append({
            "material":mat,"name":mat_name,"current_stock":current_stock,
            "sih":sih,"safety_stock":ss_mm,"rec_safety_stock":rec_ss,
            "lead_time":effective_lt,"planned_lt":planned_lt,
            "avg_monthly_demand":round(avg_demand,1),"std_demand":round(std_demand,1),
            "days_cover":round(days_cover,1),"risk":risk,"trend":trend_label,
            "trend_delta":td,"zero_periods":zero_periods,"total_periods":total_periods,
            "breach_count":breach_count,"nonzero_demand_months":len(nonzero_dem),
            "temp_cond":str(temp_cond),"abcde":str(abcde),
            "lot_size":fls_ci,"min_lot_size":mls_ci,"reorder_point":reorder_pt,
            "latest_period":latest_period,"data_quality_flags":dq_flags,
            "repl_triggered":repl["triggered"],"repl_quantity":repl["quantity"],
            "repl_shortfall":repl["shortfall"],"repl_formula":repl["formula_used"],
            "lt_urgency":lt_urgency,
        })
    return pd.DataFrame(rows)

def get_stock_history(data: dict, material: str) -> pd.DataFrame:
    df=data["inv_lt"][data["inv_lt"].Material==material].copy()
    df=df.sort_values("Fiscal Period")
    df["period_dt"]=pd.to_datetime(df["Fiscal Period"],format="%Y%m")
    df["label"]=df["period_dt"].dt.strftime("%b '%y")
    return df[["Fiscal Period","period_dt","label","Gross Stock","Safety Stock",
               "Plan DelivTime","Inhouse Production"]].reset_index(drop=True)

def get_demand_history(data: dict, material: str) -> pd.DataFrame:
    df=data["sales"][data["sales"].material==material].copy()
    monthly=df.groupby("ym")["original_confirmed_qty"].sum().reset_index()
    monthly.columns=["period","demand"]
    monthly=monthly[monthly.period.notna()].sort_values("period")
    monthly["period_dt"]=pd.to_datetime(monthly["period"],format="%Y%m")
    monthly["label"]=monthly["period_dt"].dt.strftime("%b '%y")
    return monthly.reset_index(drop=True)

def get_bom_components(data: dict, material: str) -> pd.DataFrame:
    df=data["bom"][data["bom"]["Origin Material"]==material].copy()
    def get_supplier_display(row):
        proc=str(row.get("Procurement type","")).strip()
        sup=row.get("Supplier Name(Vendor)","")
        if proc=="E":
            return "Revvity Inhouse"
        elif proc=="F":
            if pd.notna(sup) and str(sup).strip():
                return str(sup).strip()
            return "⚠ Not specified (External)"
        return str(sup) if pd.notna(sup) else "—"
    df["Supplier Display"]=df.apply(get_supplier_display, axis=1)
    df["Procurement Label"]=df["Procurement type"].apply(
        lambda x: "Inhouse (Revvity)" if str(x).strip()=="E" else ("External" if str(x).strip()=="F" else str(x)))
    df["Fixed Qty Flag"]=df["Fixed quantity"].apply(lambda x: str(x).strip()=="X" if pd.notna(x) else False)
    df["Effective Order Qty"]=df.apply(
        lambda r: 1 if r["Fixed Qty Flag"] else r["Comp. Qty (CUn)"], axis=1)
    # Enrich supplier data
    df["Supplier Location"]=df["Supplier Name(Vendor)"].apply(
        lambda s: SUPPLIER_LOCATIONS.get(str(s).strip(),{}).get("city","Unknown") if pd.notna(s) else "—")
    df["Supplier Lat"]=df["Supplier Name(Vendor)"].apply(
        lambda s: SUPPLIER_LOCATIONS.get(str(s).strip(),{}).get("lat",None) if pd.notna(s) else None)
    df["Supplier Lon"]=df["Supplier Name(Vendor)"].apply(
        lambda s: SUPPLIER_LOCATIONS.get(str(s).strip(),{}).get("lon",None) if pd.notna(s) else None)
    df["Transit Days"]=df["Supplier Name(Vendor)"].apply(
        lambda s: SUPPLIER_LOCATIONS.get(str(s).strip(),{}).get("est_transit_days",None) if pd.notna(s) else None)
    df["Supplier Reliability"]=df["Supplier Name(Vendor)"].apply(
        lambda s: SUPPLIER_LOCATIONS.get(str(s).strip(),{}).get("reliability",0.8) if pd.notna(s) else None)
    df["Geo Risk Score"]=df["Supplier Name(Vendor)"].apply(
        lambda s: SUPPLIER_LOCATIONS.get(str(s).strip(),{}).get("geo_risk",0.1) if pd.notna(s) else None)
    df["Alternative Suppliers"]=df["Supplier Name(Vendor)"].apply(
        lambda s: ", ".join(ALTERNATIVE_SUPPLIERS.get(str(s).strip(), [])) if pd.notna(s) else "—")
    return df

def get_supplier_consolidation(data: dict, summary_df: pd.DataFrame) -> pd.DataFrame:
    bom=data["bom"]
    bom_named=bom[bom["Supplier Name(Vendor)"].notna()].copy()
    rows=[]
    for sup, grp in bom_named.groupby("Supplier Name(Vendor)"):
        mats=grp["Origin Material"].unique().tolist()
        mat_names=[MATERIAL_LABELS.get(m,m) for m in mats]
        mats_needing_order=[m for m in mats
                            if len(summary_df[summary_df.material==m])>0
                            and summary_df[summary_df.material==m]["repl_triggered"].values[0]]
        total_order_value=sum([
            summary_df[summary_df.material==m]["repl_quantity"].values[0]
            if len(summary_df[summary_df.material==m])>0 else 0
            for m in mats_needing_order])
        loc=SUPPLIER_LOCATIONS.get(str(sup).strip(),{})
        email=grp["Supplier Email address(Vendor)"].dropna().iloc[0] if len(grp["Supplier Email address(Vendor)"].dropna())>0 else "—"
        phone=grp["Supplier contact phone number(Vendor)"].dropna().iloc[0] if len(grp["Supplier contact phone number(Vendor)"].dropna())>0 else "—"
        rows.append({
            "supplier":str(sup),"city":loc.get("city","Unknown"),
            "lat":loc.get("lat",None),"lon":loc.get("lon",None),
            "transit_days":loc.get("est_transit_days",None),
            "reliability":loc.get("reliability",0.8),
            "geo_risk":loc.get("geo_risk",0.1),
            "finished_goods_supplied":len(mats),
            "material_list":mats,"material_names":mat_names,
            "materials_needing_order":mats_needing_order,
            "consolidation_opportunity":len(mats_needing_order)>0,
            "email":email,"phone":str(phone),
        })
    return pd.DataFrame(rows).sort_values("finished_goods_supplied",ascending=False).reset_index(drop=True)

def get_material_context(data: dict, material: str, summary_df: pd.DataFrame) -> dict:
    stock_hist=get_stock_history(data, material)
    demand_hist=get_demand_history(data, material)
    bom=get_bom_components(data, material)
    mat_row=summary_df[summary_df.material==material]
    if len(mat_row)==0: return {}
    row=mat_row.iloc[0]

    ss=row["safety_stock"]
    breach_periods=stock_hist[stock_hist["Gross Stock"]<max(ss,1)]["Fiscal Period"].tolist() if ss>0 else []

    bom_summary=[]
    missing_sup=[]
    for _,b in bom.iterrows():
        sup_display=b.get("Supplier Display","—")
        is_inhouse=str(b.get("Procurement type","")).strip()=="E"
        is_missing=str(sup_display).startswith("⚠")
        if is_missing: missing_sup.append(str(b["Material Description"])[:30] if pd.notna(b["Material Description"]) else str(b["Material"]))
        bom_summary.append({
            "component":b["Material"],"description":str(b["Material Description"])[:40] if pd.notna(b["Material Description"]) else "—",
            "level":str(b["Level"])[:25] if pd.notna(b["Level"]) else "—",
            "qty":b["Effective Order Qty"] if "Effective Order Qty" in b else b["Comp. Qty (CUn)"],
            "fixed_qty":b.get("Fixed Qty Flag",False),
            "unit":b["Component unit"] if pd.notna(b["Component unit"]) else "—",
            "supplier":sup_display,"inhouse":is_inhouse,
            "location":b.get("Supplier Location","—"),
            "transit_days":b.get("Transit Days",None),
            "reliability":b.get("Supplier Reliability",None),
            "geo_risk":b.get("Geo Risk Score",None),
            "alternatives":b.get("Alternative Suppliers","—"),
        })

    nonzero=demand_hist[demand_hist.demand>0]
    avg=round(float(nonzero.demand.mean()),1) if len(nonzero)>0 else 0
    spikes=demand_hist[demand_hist.demand>avg*2][["period","demand"]].to_dict("records") if avg>0 else []

    consolidation=get_supplier_consolidation(data, summary_df)
    relevant_consolidation=[]
    for _,sc_row in consolidation.iterrows():
        if material in sc_row["material_list"] and sc_row["finished_goods_supplied"]>1:
            relevant_consolidation.append({
                "supplier":sc_row["supplier"],
                "also_supplies":len(sc_row["material_list"])-1,
                "consolidation_opportunity":sc_row["consolidation_opportunity"],
                "transit_days":sc_row["transit_days"],
                "reliability":sc_row["reliability"],
            })

    return {
        "material_id":material,"material_name":row["name"],
        "current_stock":row["current_stock"],"sih":row["sih"],
        "safety_stock_sap":row["safety_stock"],"rec_safety_stock":row["rec_safety_stock"],
        "lead_time_days":row["lead_time"],"lot_size":row["lot_size"],
        "min_lot_size":row["min_lot_size"],"risk_status":row["risk"],
        "trend":row["trend"],"days_cover":row["days_cover"],
        "lt_urgency":row["lt_urgency"],"temp_conditions":row["temp_cond"],
        "abcde_category":row["abcde"],
        "replenishment":{"triggered":row["repl_triggered"],"quantity":row["repl_quantity"],
                         "shortfall":row["repl_shortfall"],"formula":row["repl_formula"]},
        "breach_periods":breach_periods,
        "demand_stats":{"avg_monthly":avg,"max_monthly":round(float(nonzero.demand.max()),1) if len(nonzero)>0 else 0,
                        "std_monthly":round(float(nonzero.demand.std()),1) if len(nonzero)>1 else 0,
                        "nonzero_months":len(nonzero),"total_months":len(demand_hist),
                        "recent_6m":demand_hist["demand"].tail(6).tolist()},
        "spike_events":spikes,
        "bom_components":bom_summary,"total_bom_components":len(bom_summary),
        "missing_supplier_count":len(missing_sup),"missing_supplier_components":missing_sup,
        "supplier_consolidation":relevant_consolidation,
        "data_quality_flags":row["data_quality_flags"],
        "parameter_sources":{
            "safety_stock":"Material Master (Current Inventory = 0 for all SKUs)",
            "lead_time":"max(Lead Time, Inhouse Production Time, Planned Delivery Time)",
            "lot_size":"Current Inventory: Fixed Lot Size",
            "demand":"Sales file (includes write-offs, internal consumption)"},
    }