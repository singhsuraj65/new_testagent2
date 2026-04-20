# # """
# # ARIA Supply Intelligence · MResult
# # app.py — entry point: page config, global CSS, sidebar, topbar, navigation, routing.
# # """

# # import streamlit as st
# # from streamlit_option_menu import option_menu

# # from utils.state import init_session_state, auto_load_data
# # from components.sidebar import render_sidebar
# # import tabs.command_center       as tab_cc
# # import tabs.material_intelligence as tab_mi
# # import tabs.risk_radar            as tab_rr
# # import tabs.scenario_engine       as tab_se
# # import tabs.supply_network        as tab_sn

# # # ── Page config ────────────────────────────────────────────────────────────────
# # st.set_page_config(
# #     page_title="ARIA · MResult", page_icon="◈",
# #     layout="wide", initial_sidebar_state="expanded",
# # )

# # # ── Global CSS ─────────────────────────────────────────────────────────────────
# # st.markdown("""
# # <style>
# # @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');
# # :root{
# #   --bg:#F5F7FB;--sf:#FFFFFF;--s2:#F8FAFE;--s3:#F0F4F9;--s4:#E9EFF5;
# #   --or:#F47B25;--olt:#FF9F50;--odk:#C45D0A;
# #   --og:rgba(244,123,37,0.12);--ob:rgba(244,123,37,0.07);--obr:rgba(244,123,37,0.25);
# #   --bl:#E2E8F0;--t:#1E293B;--t2:#475569;--t3:#94A3B8;
# #   --gr:#22C55E;--gbg:rgba(34,197,94,0.10);
# #   --am:#F59E0B;--abg:rgba(245,158,11,0.10);
# #   --rd:#EF4444;--rbg:rgba(239,68,68,0.08);
# #   --r:12px;--rl:16px;
# #   --fn:'Inter',system-ui,sans-serif;
# #   --tr:0.2s cubic-bezier(0.4,0,0.2,1);
# #   --sh:0 1px 3px rgba(0,0,0,0.04);--shm:0 6px 14px -4px rgba(0,0,0,0.10);
# # }
# # *{box-sizing:border-box;}
# # html,body,[class*="css"]{font-family:var(--fn);color:var(--t);}
# # .stApp{background:var(--bg);}
# # #MainMenu,footer,header{visibility:hidden;}
# # .block-container{padding:0!important;}

# # /* SIDEBAR */
# # section[data-testid="stSidebar"]{background:var(--sf)!important;border-right:1px solid var(--bl)!important;overflow:hidden!important;min-width:220px!important;max-width:220px!important;}
# # section[data-testid="stSidebar"]>div{padding:0!important;overflow:hidden!important;}
# # section[data-testid="stSidebar"]::-webkit-scrollbar{display:none!important;}
# # section[data-testid="stSidebar"] *{color:var(--t2)!important;}
# # section[data-testid="stSidebar"] .stTextInput>div>div{background:rgba(244,123,37,0.04)!important;border:1px solid var(--obr)!important;border-radius:9px!important;font-size:12px!important;color:var(--t3)!important;}

# # /* MAIN panel gap from sidebar */
# # .main .block-container{margin-left:24px!important;margin-right:16px!important;}

# # /* SHIMMER */
# # .accent-bar{height:3px;background:linear-gradient(90deg,var(--odk),var(--or),var(--olt),var(--or));background-size:200%;animation:shimmer 3s linear infinite;width:100%;}
# # @keyframes shimmer{0%{background-position:200%}100%{background-position:-200%}}
# # @keyframes pdot{0%{box-shadow:0 0 0 0 rgba(34,197,94,0.5)}50%{box-shadow:0 0 0 5px rgba(34,197,94,0)}}
# # .ldot{width:7px;height:7px;border-radius:50%;background:var(--gr);animation:pdot 2s infinite;display:inline-block;}

# # /* TOPBAR */
# # .topbar{height:52px;background:var(--sf);border-bottom:1px solid var(--bl);display:flex;align-items:center;padding:0 20px;gap:12px;}
# # .tt{font-size:14px;font-weight:700;color:var(--t);}
# # .tt span{color:var(--t3);font-weight:400;}
# # .tbadge{background:var(--ob);border:1px solid var(--obr);color:var(--or);font-size:10px;font-weight:700;padding:2px 8px;border-radius:20px;}

# # /* STAT CARDS */
# # .sc{background:var(--sf);border:1px solid var(--bl);border-radius:var(--rl);padding:14px 16px;display:flex;align-items:center;gap:12px;box-shadow:var(--sh);transition:all var(--tr);}
# # .sc:hover{transform:translateY(-1px);box-shadow:var(--shm);}
# # .si{width:40px;height:40px;border-radius:10px;display:flex;align-items:center;justify-content:center;flex-shrink:0;}
# # .si svg{width:18px;height:18px;}
# # .sio{background:var(--ob);border:1px solid var(--obr);}
# # .sir{background:var(--rbg);border:1px solid rgba(239,68,68,0.2);}
# # .sia{background:var(--abg);border:1px solid rgba(245,158,11,0.2);}
# # .sig{background:var(--gbg);border:1px solid rgba(34,197,94,0.2);}
# # .six{background:rgba(100,116,139,0.08);border:1px solid rgba(100,116,139,0.15);}
# # .sv{font-size:24px;font-weight:900;color:var(--t);letter-spacing:-1px;line-height:1;}
# # .sl{font-size:10px;color:var(--t2);margin-top:3px;}
# # .sdt{font-size:10px;padding:2px 7px;border-radius:20px;font-weight:600;margin-left:auto;white-space:nowrap;}
# # .sdu{background:var(--gbg);color:var(--gr);}
# # .sdw{background:var(--abg);color:var(--am);}
# # .sdc{background:var(--rbg);color:var(--rd);}

# # /* BADGES */
# # .sb{display:inline-flex;align-items:center;gap:4px;font-size:10px;font-weight:700;padding:3px 8px;border-radius:20px;}
# # .sbc{background:var(--rbg);color:var(--rd);border:1px solid rgba(239,68,68,0.2);}
# # .sbw{background:var(--abg);color:var(--am);border:1px solid rgba(245,158,11,0.2);}
# # .sbh{background:var(--gbg);color:var(--gr);border:1px solid rgba(34,197,94,0.2);}
# # .sbn{background:rgba(100,116,139,0.08);color:var(--t2);border:1px solid var(--bl);}
# # .dot{width:6px;height:6px;border-radius:50%;display:inline-block;}
# # .dot-r{background:var(--rd);}.dot-a{background:var(--am);}.dot-g{background:var(--gr);animation:pdot 2s infinite;}.dot-n{background:var(--t3);}

# # /* FEED */
# # .fc{background:var(--sf);border:1px solid var(--bl);border-radius:var(--rl);overflow:hidden;box-shadow:var(--sh);}
# # .fh{padding:10px 14px;border-bottom:1px solid var(--bl);display:flex;align-items:center;justify-content:space-between;}
# # .fht{font-size:12px;font-weight:700;color:var(--t);}
# # .flv{background:var(--gbg);border-radius:20px;padding:2px 7px;font-size:9px;color:var(--gr);display:flex;align-items:center;gap:4px;}
# # .fi{display:flex;gap:9px;padding:9px 14px;border-bottom:1px solid var(--bl);transition:background var(--tr);}
# # .fi:last-child{border-bottom:none;}.fi:hover{background:var(--s2);}
# # .fi-dc{display:flex;flex-direction:column;align-items:center;padding-top:4px;}
# # .fi-dot{width:7px;height:7px;border-radius:50%;flex-shrink:0;}
# # .fi-line{width:1px;flex:1;background:var(--bl);min-height:12px;margin-top:3px;}
# # .fi-msg{font-size:11px;font-weight:500;color:var(--t);line-height:1.45;}
# # .fi-msg span{color:var(--or);font-weight:700;}
# # .fi-sub{font-size:10px;color:var(--t3);margin-top:2px;line-height:1.35;}
# # .fi-tag{font-size:8px;padding:2px 5px;border-radius:4px;margin-top:2px;display:inline-block;font-weight:700;}
# # .ftc{background:var(--rbg);color:var(--rd);}.ftw{background:var(--abg);color:var(--am);}
# # .fto{background:var(--gbg);color:var(--gr);}.fti{background:var(--ob);color:var(--or);}

# # /* INTEL */
# # .ic{background:var(--sf);border:1px solid var(--obr);border-radius:var(--rl);padding:18px 20px;margin:12px 0;box-shadow:0 0 0 3px var(--og);position:relative;}
# # .il{position:absolute;top:-10px;left:14px;background:var(--or);color:#fff;font-size:9px;font-weight:800;letter-spacing:1.2px;text-transform:uppercase;padding:2px 10px;border-radius:20px;}
# # .ih{font-size:15px;font-weight:800;color:var(--t);margin-bottom:8px;line-height:1.4;}
# # .ib{font-size:12px;color:var(--t2);line-height:1.8;}
# # .iff{display:flex;gap:8px;align-items:flex-start;margin:6px 0;font-size:11px;color:var(--t2);}
# # .ifd{width:5px;height:5px;border-radius:50%;background:var(--or);margin-top:5px;flex-shrink:0;}

# # /* BOX */
# # .sap-box{background:var(--abg);border:1px solid rgba(245,158,11,0.2);border-radius:var(--r);padding:12px 14px;font-size:12px;color:#78350f;}
# # .sap-lbl{font-size:9px;font-weight:800;letter-spacing:1px;color:#92400e;margin-bottom:4px;text-transform:uppercase;}
# # .rec-box{background:var(--gbg);border:1px solid rgba(34,197,94,0.2);border-radius:var(--r);padding:12px 14px;font-size:12px;color:#14532d;}
# # .rec-lbl{font-size:9px;font-weight:800;letter-spacing:1px;color:#166534;margin-bottom:4px;text-transform:uppercase;}
# # .flag-box{background:var(--s2);border:1px dashed rgba(0,0,0,0.10);border-radius:var(--rl);padding:24px;text-align:center;color:var(--t3);font-size:13px;}
# # .chip{display:inline-flex;align-items:center;padding:2px 8px;border-radius:6px;background:var(--s3);border:1px solid var(--bl);font-size:10px;color:var(--t2);font-weight:500;}
# # .note-box{background:rgba(244,123,37,0.04);border-left:3px solid var(--or);border-radius:0 8px 8px 0;padding:7px 11px;font-size:10px;color:var(--t2);margin:6px 0;}
# # .sdv{font-size:10px;font-weight:700;letter-spacing:1.2px;text-transform:uppercase;color:var(--t3);margin:16px 0 8px;padding-bottom:6px;border-bottom:1px solid var(--bl);}
# # .pfooter{text-align:center;margin-top:24px;padding:12px 0 4px;border-top:1px solid var(--bl);font-size:11px;color:var(--t3);}
# # .pfooter strong{color:var(--or);}
# # .mc{background:var(--sf);border:1px solid var(--bl);border-radius:var(--rl);padding:16px 18px;box-shadow:var(--sh);}
# # .mc:hover{border-color:var(--obr);transform:translateY(-1px);box-shadow:var(--shm);}

# # /* PRIORITY ROW */
# # .prow{display:flex;align-items:center;gap:10px;padding:10px 12px;border-radius:var(--r);margin-bottom:6px;border:1px solid var(--bl);background:var(--sf);transition:all var(--tr);}
# # .prow:hover{box-shadow:var(--sh);border-color:var(--obr);}

# # /* BUTTONS */
# # .stButton>button{background:var(--or);color:#fff;border:none;border-radius:var(--r);font-family:var(--fn);font-size:13px;font-weight:700;padding:8px 16px;transition:all var(--tr);box-shadow:0 2px 8px rgba(244,123,37,0.2);}
# # .stButton>button:hover{background:var(--odk);border:none;transform:translateY(-1px);}

# # /* INPUTS */
# # .stSelectbox>div>div,.stTextInput>div>div{background:var(--s2)!important;border:1px solid var(--bl)!important;border-radius:var(--r)!important;font-size:13px!important;color:var(--t)!important;}

# # /* NAV */
# # .nav-link{color:var(--t2)!important;background:transparent!important;border-radius:9px!important;font-size:12px!important;font-weight:500!important;}
# # .nav-link:hover{background:var(--s3)!important;color:var(--t)!important;}
# # .nav-link-selected{background:var(--ob)!important;color:var(--or)!important;border:1px solid var(--obr)!important;font-weight:600!important;}
# # .nav-link .icon{color:inherit!important;}

# # /* AGGRID */
# # .ag-root-wrapper{border:1px solid var(--bl)!important;border-radius:var(--rl)!important;overflow:hidden;box-shadow:var(--sh);}
# # .ag-header{background:#F8FAFE!important;border-bottom:1px solid var(--bl)!important;}
# # .ag-header-cell-label{font-size:10px!important;font-weight:700!important;color:#475569!important;text-transform:uppercase;}
# # .ag-row-even{background:#FFFFFF!important;}.ag-row-odd{background:#F8FAFE!important;}
# # .ag-row:hover{background:rgba(244,123,37,0.03)!important;}
# # .ag-cell{display:flex;align-items:center;border-right:1px solid #F0F4F9!important;}

# # /* SCROLLBAR */
# # ::-webkit-scrollbar{width:4px;height:4px;}
# # ::-webkit-scrollbar-track{background:transparent;}
# # ::-webkit-scrollbar-thumb{background:#E2E8F0;border-radius:2px;}

# # /* Sidebar logo size */
# # section[data-testid="stSidebar"] img{max-height:80px!important;width:auto!important;margin:10px auto;}
# # button[kind="header"]{visibility:visible!important;}
# # [data-tooltip]{position:relative;cursor:help;border-bottom:1px dotted #94A3B8;}
# # [data-tooltip]:before{content:attr(data-tooltip);position:absolute;bottom:100%;left:0;background:#1E293B;color:white;padding:4px 8px;border-radius:6px;font-size:10px;white-space:nowrap;display:none;z-index:1000;}
# # [data-tooltip]:hover:before{display:block;}
# # </style>
# # """, unsafe_allow_html=True)

# # # ── Session state + data load ──────────────────────────────────────────────────
# # init_session_state()
# # auto_load_data()

# # # ── Sidebar ────────────────────────────────────────────────────────────────────
# # render_sidebar()

# # # ── Data load guards ───────────────────────────────────────────────────────────
# # if st.session_state.data_error:
# #     st.error("Data load failed: " + st.session_state.data_error)
# #     st.stop()
# # if st.session_state.data is None:
# #     st.info("Loading data…")
# #     st.stop()

# # # ── Topbar ─────────────────────────────────────────────────────────────────────
# # st.markdown('<div class="accent-bar"></div>', unsafe_allow_html=True)
# # st.markdown(
# #     "<div class='topbar'>"
# #     "<div class='tt'>Supply Intelligence <span>/ FI11 Turku · Apr 2026</span></div>"
# #     "<div class='tbadge'>◈ Live</div>"
# #     "<div style='margin-left:auto;display:flex;align-items:center;gap:8px;'>"
# #     "<span class='ldot'></span>"
# #     "<span style='font-size:10px;color:var(--t3);'>Real-time</span>"
# #     "<div style='width:28px;height:28px;border-radius:7px;"
# #     "background:linear-gradient(135deg,var(--odk),var(--or));"
# #     "display:flex;align-items:center;justify-content:center;"
# #     "font-size:11px;font-weight:800;color:#fff;'>AI</div>"
# #     "</div></div>",
# #     unsafe_allow_html=True,
# # )

# # # ── Navigation ─────────────────────────────────────────────────────────────────
# # selected = option_menu(
# #     menu_title=None,
# #     options=["Command Center", "Material Intelligence", "Risk Radar", "Scenario Engine", "Supply Network"],
# #     icons=["grid", "search", "broadcast", "lightning", "diagram-3"],
# #     orientation="horizontal",
# #     styles={
# #         "container":       {"padding": "5px 20px", "background-color": "#FFFFFF", "border-bottom": "1px solid #E2E8F0"},
# #         "nav-link":        {"font-family": "Inter", "font-size": "12px", "font-weight": "500", "color": "#475569",
# #                             "padding": "6px 12px", "border-radius": "9px", "margin": "0 2px", "--hover-color": "#F0F4F9"},
# #         "nav-link-selected": {"background-color": "rgba(244,123,37,0.07)", "color": "#F47B25",
# #                               "border": "1px solid rgba(244,123,37,0.25)", "font-weight": "600"},
# #         "icon": {"font-size": "12px"},
# #     },
# # )

# # st.markdown('<div style="padding:16px 20px;">', unsafe_allow_html=True)

# # # ── Tab routing ────────────────────────────────────────────────────────────────
# # if   selected == "Command Center":        tab_cc.render()
# # elif selected == "Material Intelligence": tab_mi.render()
# # elif selected == "Risk Radar":            tab_rr.render()
# # elif selected == "Scenario Engine":       tab_se.render()
# # elif selected == "Supply Network":        tab_sn.render()

# # st.markdown('</div>', unsafe_allow_html=True)

# """
# ARIA Supply Intelligence · MResult
# app.py — entry point: page config, global CSS, sidebar, topbar, navigation, routing.
# """

# import streamlit as st
# from streamlit_option_menu import option_menu

# from utils.state import init_session_state, auto_load_data
# from components.sidebar import render_sidebar
# import tabs.command_center       as tab_cc
# import tabs.material_intelligence as tab_mi
# import tabs.risk_radar            as tab_rr
# import tabs.scenario_engine       as tab_se
# import tabs.supply_network        as tab_sn

# # ── Page config ────────────────────────────────────────────────────────────────
# st.set_page_config(
#     page_title="ARIA · MResult", page_icon="◈",
#     layout="wide", initial_sidebar_state="expanded",
# )

# # ── Global CSS (includes sidebar toggle fix) ───────────────────────────────────
# st.markdown("""
# <style>
# @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');
# :root{
#   --bg:#F5F7FB;--sf:#FFFFFF;--s2:#F8FAFE;--s3:#F0F4F9;--s4:#E9EFF5;
#   --or:#F47B25;--olt:#FF9F50;--odk:#C45D0A;
#   --og:rgba(244,123,37,0.12);--ob:rgba(244,123,37,0.07);--obr:rgba(244,123,37,0.25);
#   --bl:#E2E8F0;--t:#1E293B;--t2:#475569;--t3:#94A3B8;
#   --gr:#22C55E;--gbg:rgba(34,197,94,0.10);
#   --am:#F59E0B;--abg:rgba(245,158,11,0.10);
#   --rd:#EF4444;--rbg:rgba(239,68,68,0.08);
#   --r:12px;--rl:16px;
#   --fn:'Inter',system-ui,sans-serif;
#   --tr:0.2s cubic-bezier(0.4,0,0.2,1);
#   --sh:0 1px 3px rgba(0,0,0,0.04);--shm:0 6px 14px -4px rgba(0,0,0,0.10);
# }
# *{box-sizing:border-box;}
# html,body,[class*="css"]{font-family:var(--fn);color:var(--t);}
# .stApp{background:var(--bg);}
# #MainMenu,footer,header{visibility:hidden;}
# .block-container{padding:0!important;}

# /* SIDEBAR */
# section[data-testid="stSidebar"]{background:var(--sf)!important;border-right:1px solid var(--bl)!important;overflow:hidden!important;min-width:220px!important;max-width:220px!important;}
# section[data-testid="stSidebar"]>div{padding:0!important;overflow:hidden!important;}
# section[data-testid="stSidebar"]::-webkit-scrollbar{display:none!important;}
# section[data-testid="stSidebar"] *{color:var(--t2)!important;}
# section[data-testid="stSidebar"] .stTextInput>div>div{background:rgba(244,123,37,0.04)!important;border:1px solid var(--obr)!important;border-radius:9px!important;font-size:12px!important;color:var(--t3)!important;}

# /* MAIN panel gap from sidebar */
# .main .block-container{margin-left:24px!important;margin-right:16px!important;}

# /* SHIMMER */
# .accent-bar{height:3px;background:linear-gradient(90deg,var(--odk),var(--or),var(--olt),var(--or));background-size:200%;animation:shimmer 3s linear infinite;width:100%;}
# @keyframes shimmer{0%{background-position:200%}100%{background-position:-200%}}
# @keyframes pdot{0%{box-shadow:0 0 0 0 rgba(34,197,94,0.5)}50%{box-shadow:0 0 0 5px rgba(34,197,94,0)}}
# .ldot{width:7px;height:7px;border-radius:50%;background:var(--gr);animation:pdot 2s infinite;display:inline-block;}

# /* TOPBAR */
# .topbar{height:52px;background:var(--sf);border-bottom:1px solid var(--bl);display:flex;align-items:center;padding:0 20px;gap:12px;}
# .tt{font-size:14px;font-weight:700;color:var(--t);}
# .tt span{color:var(--t3);font-weight:400;}
# .tbadge{background:var(--ob);border:1px solid var(--obr);color:var(--or);font-size:10px;font-weight:700;padding:2px 8px;border-radius:20px;}

# /* STAT CARDS */
# .sc{background:var(--sf);border:1px solid var(--bl);border-radius:var(--rl);padding:14px 16px;display:flex;align-items:center;gap:12px;box-shadow:var(--sh);transition:all var(--tr);}
# .sc:hover{transform:translateY(-1px);box-shadow:var(--shm);}
# .si{width:40px;height:40px;border-radius:10px;display:flex;align-items:center;justify-content:center;flex-shrink:0;}
# .si svg{width:18px;height:18px;}
# .sio{background:var(--ob);border:1px solid var(--obr);}
# .sir{background:var(--rbg);border:1px solid rgba(239,68,68,0.2);}
# .sia{background:var(--abg);border:1px solid rgba(245,158,11,0.2);}
# .sig{background:var(--gbg);border:1px solid rgba(34,197,94,0.2);}
# .six{background:rgba(100,116,139,0.08);border:1px solid rgba(100,116,139,0.15);}
# .sv{font-size:24px;font-weight:900;color:var(--t);letter-spacing:-1px;line-height:1;}
# .sl{font-size:10px;color:var(--t2);margin-top:3px;}
# .sdt{font-size:10px;padding:2px 7px;border-radius:20px;font-weight:600;margin-left:auto;white-space:nowrap;}
# .sdu{background:var(--gbg);color:var(--gr);}
# .sdw{background:var(--abg);color:var(--am);}
# .sdc{background:var(--rbg);color:var(--rd);}

# /* BADGES */
# .sb{display:inline-flex;align-items:center;gap:4px;font-size:10px;font-weight:700;padding:3px 8px;border-radius:20px;}
# .sbc{background:var(--rbg);color:var(--rd);border:1px solid rgba(239,68,68,0.2);}
# .sbw{background:var(--abg);color:var(--am);border:1px solid rgba(245,158,11,0.2);}
# .sbh{background:var(--gbg);color:var(--gr);border:1px solid rgba(34,197,94,0.2);}
# .sbn{background:rgba(100,116,139,0.08);color:var(--t2);border:1px solid var(--bl);}
# .dot{width:6px;height:6px;border-radius:50%;display:inline-block;}
# .dot-r{background:var(--rd);}.dot-a{background:var(--am);}.dot-g{background:var(--gr);animation:pdot 2s infinite;}.dot-n{background:var(--t3);}

# /* FEED */
# .fc{background:var(--sf);border:1px solid var(--bl);border-radius:var(--rl);overflow:hidden;box-shadow:var(--sh);}
# .fh{padding:10px 14px;border-bottom:1px solid var(--bl);display:flex;align-items:center;justify-content:space-between;}
# .fht{font-size:12px;font-weight:700;color:var(--t);}
# .flv{background:var(--gbg);border-radius:20px;padding:2px 7px;font-size:9px;color:var(--gr);display:flex;align-items:center;gap:4px;}
# .fi{display:flex;gap:9px;padding:9px 14px;border-bottom:1px solid var(--bl);transition:background var(--tr);}
# .fi:last-child{border-bottom:none;}.fi:hover{background:var(--s2);}
# .fi-dc{display:flex;flex-direction:column;align-items:center;padding-top:4px;}
# .fi-dot{width:7px;height:7px;border-radius:50%;flex-shrink:0;}
# .fi-line{width:1px;flex:1;background:var(--bl);min-height:12px;margin-top:3px;}
# .fi-msg{font-size:11px;font-weight:500;color:var(--t);line-height:1.45;}
# .fi-msg span{color:var(--or);font-weight:700;}
# .fi-sub{font-size:10px;color:var(--t3);margin-top:2px;line-height:1.35;}
# .fi-tag{font-size:8px;padding:2px 5px;border-radius:4px;margin-top:2px;display:inline-block;font-weight:700;}
# .ftc{background:var(--rbg);color:var(--rd);}.ftw{background:var(--abg);color:var(--am);}
# .fto{background:var(--gbg);color:var(--gr);}.fti{background:var(--ob);color:var(--or);}

# /* INTEL */
# .ic{background:var(--sf);border:1px solid var(--obr);border-radius:var(--rl);padding:18px 20px;margin:12px 0;box-shadow:0 0 0 3px var(--og);position:relative;}
# .il{position:absolute;top:-10px;left:14px;background:var(--or);color:#fff;font-size:9px;font-weight:800;letter-spacing:1.2px;text-transform:uppercase;padding:2px 10px;border-radius:20px;}
# .ih{font-size:15px;font-weight:800;color:var(--t);margin-bottom:8px;line-height:1.4;}
# .ib{font-size:12px;color:var(--t2);line-height:1.8;}
# .iff{display:flex;gap:8px;align-items:flex-start;margin:6px 0;font-size:11px;color:var(--t2);}
# .ifd{width:5px;height:5px;border-radius:50%;background:var(--or);margin-top:5px;flex-shrink:0;}

# /* BOX */
# .sap-box{background:var(--abg);border:1px solid rgba(245,158,11,0.2);border-radius:var(--r);padding:12px 14px;font-size:12px;color:#78350f;}
# .sap-lbl{font-size:9px;font-weight:800;letter-spacing:1px;color:#92400e;margin-bottom:4px;text-transform:uppercase;}
# .rec-box{background:var(--gbg);border:1px solid rgba(34,197,94,0.2);border-radius:var(--r);padding:12px 14px;font-size:12px;color:#14532d;}
# .rec-lbl{font-size:9px;font-weight:800;letter-spacing:1px;color:#166534;margin-bottom:4px;text-transform:uppercase;}
# .flag-box{background:var(--s2);border:1px dashed rgba(0,0,0,0.10);border-radius:var(--rl);padding:24px;text-align:center;color:var(--t3);font-size:13px;}
# .chip{display:inline-flex;align-items:center;padding:2px 8px;border-radius:6px;background:var(--s3);border:1px solid var(--bl);font-size:10px;color:var(--t2);font-weight:500;}
# .note-box{background:rgba(244,123,37,0.04);border-left:3px solid var(--or);border-radius:0 8px 8px 0;padding:7px 11px;font-size:10px;color:var(--t2);margin:6px 0;}
# .sdv{font-size:10px;font-weight:700;letter-spacing:1.2px;text-transform:uppercase;color:var(--t3);margin:16px 0 8px;padding-bottom:6px;border-bottom:1px solid var(--bl);}
# .pfooter{text-align:center;margin-top:24px;padding:12px 0 4px;border-top:1px solid var(--bl);font-size:11px;color:var(--t3);}
# .pfooter strong{color:var(--or);}
# .mc{background:var(--sf);border:1px solid var(--bl);border-radius:var(--rl);padding:16px 18px;box-shadow:var(--sh);}
# .mc:hover{border-color:var(--obr);transform:translateY(-1px);box-shadow:var(--shm);}

# /* PRIORITY ROW */
# .prow{display:flex;align-items:center;gap:10px;padding:10px 12px;border-radius:var(--r);margin-bottom:6px;border:1px solid var(--bl);background:var(--sf);transition:all var(--tr);}
# .prow:hover{box-shadow:var(--sh);border-color:var(--obr);}

# /* BUTTONS */
# .stButton>button{background:var(--or);color:#fff;border:none;border-radius:var(--r);font-family:var(--fn);font-size:13px;font-weight:700;padding:8px 16px;transition:all var(--tr);box-shadow:0 2px 8px rgba(244,123,37,0.2);}
# .stButton>button:hover{background:var(--odk);border:none;transform:translateY(-1px);}

# /* INPUTS */
# .stSelectbox>div>div,.stTextInput>div>div{background:var(--s2)!important;border:1px solid var(--bl)!important;border-radius:var(--r)!important;font-size:13px!important;color:var(--t)!important;}

# /* NAV */
# .nav-link{color:var(--t2)!important;background:transparent!important;border-radius:9px!important;font-size:12px!important;font-weight:500!important;}
# .nav-link:hover{background:var(--s3)!important;color:var(--t)!important;}
# .nav-link-selected{background:var(--ob)!important;color:var(--or)!important;border:1px solid var(--obr)!important;font-weight:600!important;}
# .nav-link .icon{color:inherit!important;}

# /* AGGRID */
# .ag-root-wrapper{border:1px solid var(--bl)!important;border-radius:var(--rl)!important;overflow:hidden;box-shadow:var(--sh);}
# .ag-header{background:#F8FAFE!important;border-bottom:1px solid var(--bl)!important;}
# .ag-header-cell-label{font-size:10px!important;font-weight:700!important;color:#475569!important;text-transform:uppercase;}
# .ag-row-even{background:#FFFFFF!important;}.ag-row-odd{background:#F8FAFE!important;}
# .ag-row:hover{background:rgba(244,123,37,0.03)!important;}
# .ag-cell{display:flex;align-items:center;border-right:1px solid #F0F4F9!important;}

# /* SCROLLBAR */
# ::-webkit-scrollbar{width:4px;height:4px;}
# ::-webkit-scrollbar-track{background:transparent;}
# ::-webkit-scrollbar-thumb{background:#E2E8F0;border-radius:2px;}

# /* Sidebar logo size */
# section[data-testid="stSidebar"] img{max-height:80px!important;width:auto!important;margin:10px auto;}

# /* Tooltip style */
# [data-tooltip]{position:relative;cursor:help;border-bottom:1px dotted #94A3B8;}
# [data-tooltip]:before{content:attr(data-tooltip);position:absolute;bottom:100%;left:0;background:#1E293B;color:white;padding:4px 8px;border-radius:6px;font-size:10px;white-space:nowrap;display:none;z-index:1000;}
# [data-tooltip]:hover:before{display:block;}

# /* ── SIDEBAR TOGGLE FIX ───────────────────────────────────────────────── */
# button[kind="header"] {
#     visibility: visible !important;
#     opacity: 1 !important;
#     pointer-events: auto !important;
#     z-index: 999 !important;
#     background: transparent !important;
#     border: none !important;
#     cursor: pointer !important;
# }
# section[data-testid="stSidebar"] {
#     transition: margin-left 0.3s ease !important;
# }
# header {
#     visibility: visible !important;
#     background: transparent !important;
# }
# /* MAIN panel gap from sidebar – increased for more space */
# .main .block-container {
#     margin-left: 32px !important;
#     margin-right: 16px !important;
# }
# </style>
# """, unsafe_allow_html=True)

# # ── Session state + data load ──────────────────────────────────────────────────
# init_session_state()
# auto_load_data()

# # ── Sidebar ────────────────────────────────────────────────────────────────────
# render_sidebar()

# # ── Data load guards ───────────────────────────────────────────────────────────
# if st.session_state.data_error:
#     st.error("Data load failed: " + st.session_state.data_error)
#     st.stop()
# if st.session_state.data is None:
#     st.info("Loading data…")
#     st.stop()

# # ── Topbar ─────────────────────────────────────────────────────────────────────
# st.markdown('<div class="accent-bar"></div>', unsafe_allow_html=True)
# st.markdown(
#     "<div class='topbar'>"
#     "<div class='tt'>Supply Intelligence <span>/ FI11 Turku · Apr 2026</span></div>"
#     "<div class='tbadge'>◈ Live</div>"
#     "<div style='margin-left:auto;display:flex;align-items:center;gap:8px;'>"
#     "<span class='ldot'></span>"
#     "<span style='font-size:10px;color:var(--t3);'>Real-time</span>"
#     "<div style='width:28px;height:28px;border-radius:7px;"
#     "background:linear-gradient(135deg,var(--odk),var(--or));"
#     "display:flex;align-items:center;justify-content:center;"
#     "font-size:11px;font-weight:800;color:#fff;'>AI</div>"
#     "</div></div>",
#     unsafe_allow_html=True,
# )

# # ── Navigation ─────────────────────────────────────────────────────────────────
# selected = option_menu(
#     menu_title=None,
#     options=["Command Center", "Material Intelligence", "Risk Radar", "Scenario Engine", "Supply Network"],
#     icons=["grid", "search", "broadcast", "lightning", "diagram-3"],
#     orientation="horizontal",
#     styles={
#         "container":       {"padding": "5px 20px", "background-color": "#FFFFFF", "border-bottom": "1px solid #E2E8F0"},
#         "nav-link":        {"font-family": "Inter", "font-size": "12px", "font-weight": "500", "color": "#475569",
#                             "padding": "6px 12px", "border-radius": "9px", "margin": "0 2px", "--hover-color": "#F0F4F9"},
#         "nav-link-selected": {"background-color": "rgba(244,123,37,0.07)", "color": "#F47B25",
#                               "border": "1px solid rgba(244,123,37,0.25)", "font-weight": "600"},
#         "icon": {"font-size": "12px"},
#     },
# )

# st.markdown('<div style="padding:16px 20px;">', unsafe_allow_html=True)

# # ── Tab routing ────────────────────────────────────────────────────────────────
# if   selected == "Command Center":        tab_cc.render()
# elif selected == "Material Intelligence": tab_mi.render()
# elif selected == "Risk Radar":            tab_rr.render()
# elif selected == "Scenario Engine":       tab_se.render()
# elif selected == "Supply Network":        tab_sn.render()

# st.markdown('</div>', unsafe_allow_html=True)

"""
ARIA Supply Intelligence · MResult
app.py — entry point: page config, global CSS, sidebar, topbar, navigation, routing.
"""

import streamlit as st
from streamlit_option_menu import option_menu

from utils.state import init_session_state, auto_load_data
from components.sidebar import render_sidebar
import tabs.command_center       as tab_cc
import tabs.material_intelligence as tab_mi
import tabs.risk_radar            as tab_rr
import tabs.scenario_engine       as tab_se
import tabs.supply_network        as tab_sn

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="ARIA · MResult", page_icon="◈",
    layout="wide", initial_sidebar_state="expanded",
)

# ── Global CSS (includes sidebar toggle fix & increased main panel margin) ───
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');
:root{
  --bg:#F5F7FB;--sf:#FFFFFF;--s2:#F8FAFE;--s3:#F0F4F9;--s4:#E9EFF5;
  --or:#F47B25;--olt:#FF9F50;--odk:#C45D0A;
  --og:rgba(244,123,37,0.12);--ob:rgba(244,123,37,0.07);--obr:rgba(244,123,37,0.25);
  --bl:#E2E8F0;--t:#1E293B;--t2:#475569;--t3:#94A3B8;
  --gr:#22C55E;--gbg:rgba(34,197,94,0.10);
  --am:#F59E0B;--abg:rgba(245,158,11,0.10);
  --rd:#EF4444;--rbg:rgba(239,68,68,0.08);
  --r:12px;--rl:16px;
  --fn:'Inter',system-ui,sans-serif;
  --tr:0.2s cubic-bezier(0.4,0,0.2,1);
  --sh:0 1px 3px rgba(0,0,0,0.04);--shm:0 6px 14px -4px rgba(0,0,0,0.10);
}
*{box-sizing:border-box;}
html,body,[class*="css"]{font-family:var(--fn);color:var(--t);}
.stApp{background:var(--bg);}
#MainMenu,footer,header{visibility:hidden;}
.block-container{padding:0!important;}

/* SIDEBAR */
section[data-testid="stSidebar"]{background:var(--sf)!important;border-right:1px solid var(--bl)!important;overflow:hidden!important;min-width:220px!important;max-width:220px!important;}
section[data-testid="stSidebar"]>div{padding:0!important;overflow:hidden!important;}
section[data-testid="stSidebar"]::-webkit-scrollbar{display:none!important;}
section[data-testid="stSidebar"] *{color:var(--t2)!important;}
section[data-testid="stSidebar"] .stTextInput>div>div{background:rgba(244,123,37,0.04)!important;border:1px solid var(--obr)!important;border-radius:9px!important;font-size:12px!important;color:var(--t3)!important;}

/* SHIMMER */
.accent-bar{height:3px;background:linear-gradient(90deg,var(--odk),var(--or),var(--olt),var(--or));background-size:200%;animation:shimmer 3s linear infinite;width:100%;}
@keyframes shimmer{0%{background-position:200%}100%{background-position:-200%}}
@keyframes pdot{0%{box-shadow:0 0 0 0 rgba(34,197,94,0.5)}50%{box-shadow:0 0 0 5px rgba(34,197,94,0)}}
.ldot{width:7px;height:7px;border-radius:50%;background:var(--gr);animation:pdot 2s infinite;display:inline-block;}

/* TOPBAR */
.topbar{height:52px;background:var(--sf);border-bottom:1px solid var(--bl);display:flex;align-items:center;padding:0 20px;gap:12px;}
.tt{font-size:14px;font-weight:700;color:var(--t);}
.tt span{color:var(--t3);font-weight:400;}
.tbadge{background:var(--ob);border:1px solid var(--obr);color:var(--or);font-size:10px;font-weight:700;padding:2px 8px;border-radius:20px;}

/* STAT CARDS */
.sc{background:var(--sf);border:1px solid var(--bl);border-radius:var(--rl);padding:14px 16px;display:flex;align-items:center;gap:12px;box-shadow:var(--sh);transition:all var(--tr);}
.sc:hover{transform:translateY(-1px);box-shadow:var(--shm);}
.si{width:40px;height:40px;border-radius:10px;display:flex;align-items:center;justify-content:center;flex-shrink:0;}
.si svg{width:18px;height:18px;}
.sio{background:var(--ob);border:1px solid var(--obr);}
.sir{background:var(--rbg);border:1px solid rgba(239,68,68,0.2);}
.sia{background:var(--abg);border:1px solid rgba(245,158,11,0.2);}
.sig{background:var(--gbg);border:1px solid rgba(34,197,94,0.2);}
.six{background:rgba(100,116,139,0.08);border:1px solid rgba(100,116,139,0.15);}
.sv{font-size:24px;font-weight:900;color:var(--t);letter-spacing:-1px;line-height:1;}
.sl{font-size:10px;color:var(--t2);margin-top:3px;}
.sdt{font-size:10px;padding:2px 7px;border-radius:20px;font-weight:600;margin-left:auto;white-space:nowrap;}
.sdu{background:var(--gbg);color:var(--gr);}
.sdw{background:var(--abg);color:var(--am);}
.sdc{background:var(--rbg);color:var(--rd);}

/* BADGES */
.sb{display:inline-flex;align-items:center;gap:4px;font-size:10px;font-weight:700;padding:3px 8px;border-radius:20px;}
.sbc{background:var(--rbg);color:var(--rd);border:1px solid rgba(239,68,68,0.2);}
.sbw{background:var(--abg);color:var(--am);border:1px solid rgba(245,158,11,0.2);}
.sbh{background:var(--gbg);color:var(--gr);border:1px solid rgba(34,197,94,0.2);}
.sbn{background:rgba(100,116,139,0.08);color:var(--t2);border:1px solid var(--bl);}
.dot{width:6px;height:6px;border-radius:50%;display:inline-block;}
.dot-r{background:var(--rd);}.dot-a{background:var(--am);}.dot-g{background:var(--gr);animation:pdot 2s infinite;}.dot-n{background:var(--t3);}

/* FEED */
.fc{background:var(--sf);border:1px solid var(--bl);border-radius:var(--rl);overflow:hidden;box-shadow:var(--sh);}
.fh{padding:10px 14px;border-bottom:1px solid var(--bl);display:flex;align-items:center;justify-content:space-between;}
.fht{font-size:12px;font-weight:700;color:var(--t);}
.flv{background:var(--gbg);border-radius:20px;padding:2px 7px;font-size:9px;color:var(--gr);display:flex;align-items:center;gap:4px;}
.fi{display:flex;gap:9px;padding:9px 14px;border-bottom:1px solid var(--bl);transition:background var(--tr);}
.fi:last-child{border-bottom:none;}.fi:hover{background:var(--s2);}
.fi-dc{display:flex;flex-direction:column;align-items:center;padding-top:4px;}
.fi-dot{width:7px;height:7px;border-radius:50%;flex-shrink:0;}
.fi-line{width:1px;flex:1;background:var(--bl);min-height:12px;margin-top:3px;}
.fi-msg{font-size:11px;font-weight:500;color:var(--t);line-height:1.45;}
.fi-msg span{color:var(--or);font-weight:700;}
.fi-sub{font-size:10px;color:var(--t3);margin-top:2px;line-height:1.35;}
.fi-tag{font-size:8px;padding:2px 5px;border-radius:4px;margin-top:2px;display:inline-block;font-weight:700;}
.ftc{background:var(--rbg);color:var(--rd);}.ftw{background:var(--abg);color:var(--am);}
.fto{background:var(--gbg);color:var(--gr);}.fti{background:var(--ob);color:var(--or);}

/* INTEL */
.ic{background:var(--sf);border:1px solid var(--obr);border-radius:var(--rl);padding:18px 20px;margin:12px 0;box-shadow:0 0 0 3px var(--og);position:relative;}
.il{position:absolute;top:-10px;left:14px;background:var(--or);color:#fff;font-size:9px;font-weight:800;letter-spacing:1.2px;text-transform:uppercase;padding:2px 10px;border-radius:20px;}
.ih{font-size:15px;font-weight:800;color:var(--t);margin-bottom:8px;line-height:1.4;}
.ib{font-size:12px;color:var(--t2);line-height:1.8;}
.iff{display:flex;gap:8px;align-items:flex-start;margin:6px 0;font-size:11px;color:var(--t2);}
.ifd{width:5px;height:5px;border-radius:50%;background:var(--or);margin-top:5px;flex-shrink:0;}

/* BOX */
.sap-box{background:var(--abg);border:1px solid rgba(245,158,11,0.2);border-radius:var(--r);padding:12px 14px;font-size:12px;color:#78350f;}
.sap-lbl{font-size:9px;font-weight:800;letter-spacing:1px;color:#92400e;margin-bottom:4px;text-transform:uppercase;}
.rec-box{background:var(--gbg);border:1px solid rgba(34,197,94,0.2);border-radius:var(--r);padding:12px 14px;font-size:12px;color:#14532d;}
.rec-lbl{font-size:9px;font-weight:800;letter-spacing:1px;color:#166534;margin-bottom:4px;text-transform:uppercase;}
.flag-box{background:var(--s2);border:1px dashed rgba(0,0,0,0.10);border-radius:var(--rl);padding:24px;text-align:center;color:var(--t3);font-size:13px;}
.chip{display:inline-flex;align-items:center;padding:2px 8px;border-radius:6px;background:var(--s3);border:1px solid var(--bl);font-size:10px;color:var(--t2);font-weight:500;}
.note-box{background:rgba(244,123,37,0.04);border-left:3px solid var(--or);border-radius:0 8px 8px 0;padding:7px 11px;font-size:10px;color:var(--t2);margin:6px 0;}
.sdv{font-size:10px;font-weight:700;letter-spacing:1.2px;text-transform:uppercase;color:var(--t3);margin:16px 0 8px;padding-bottom:6px;border-bottom:1px solid var(--bl);}
.pfooter{text-align:center;margin-top:24px;padding:12px 0 4px;border-top:1px solid var(--bl);font-size:11px;color:var(--t3);}
.pfooter strong{color:var(--or);}
.mc{background:var(--sf);border:1px solid var(--bl);border-radius:var(--rl);padding:16px 18px;box-shadow:var(--sh);}
.mc:hover{border-color:var(--obr);transform:translateY(-1px);box-shadow:var(--shm);}

/* PRIORITY ROW */
.prow{display:flex;align-items:center;gap:10px;padding:10px 12px;border-radius:var(--r);margin-bottom:6px;border:1px solid var(--bl);background:var(--sf);transition:all var(--tr);}
.prow:hover{box-shadow:var(--sh);border-color:var(--obr);}

/* BUTTONS */
.stButton>button{background:var(--or);color:#fff;border:none;border-radius:var(--r);font-family:var(--fn);font-size:13px;font-weight:700;padding:8px 16px;transition:all var(--tr);box-shadow:0 2px 8px rgba(244,123,37,0.2);}
.stButton>button:hover{background:var(--odk);border:none;transform:translateY(-1px);}

/* INPUTS */
.stSelectbox>div>div,.stTextInput>div>div{background:var(--s2)!important;border:1px solid var(--bl)!important;border-radius:var(--r)!important;font-size:13px!important;color:var(--t)!important;}

/* NAV */
.nav-link{color:var(--t2)!important;background:transparent!important;border-radius:9px!important;font-size:12px!important;font-weight:500!important;}
.nav-link:hover{background:var(--s3)!important;color:var(--t)!important;}
.nav-link-selected{background:var(--ob)!important;color:var(--or)!important;border:1px solid var(--obr)!important;font-weight:600!important;}
.nav-link .icon{color:inherit!important;}

/* AGGRID */
.ag-root-wrapper{border:1px solid var(--bl)!important;border-radius:var(--rl)!important;overflow:hidden;box-shadow:var(--sh);}
.ag-header{background:#F8FAFE!important;border-bottom:1px solid var(--bl)!important;}
.ag-header-cell-label{font-size:10px!important;font-weight:700!important;color:#475569!important;text-transform:uppercase;}
.ag-row-even{background:#FFFFFF!important;}.ag-row-odd{background:#F8FAFE!important;}
.ag-row:hover{background:rgba(244,123,37,0.03)!important;}
.ag-cell{display:flex;align-items:center;border-right:1px solid #F0F4F9!important;}

/* SCROLLBAR */
::-webkit-scrollbar{width:4px;height:4px;}
::-webkit-scrollbar-track{background:transparent;}
::-webkit-scrollbar-thumb{background:#E2E8F0;border-radius:2px;}

/* Sidebar logo size */
section[data-testid="stSidebar"] img{max-height:80px!important;width:auto!important;margin:10px auto;}

/* Tooltip style */
[data-tooltip]{position:relative;cursor:help;border-bottom:1px dotted #94A3B8;}
[data-tooltip]:before{content:attr(data-tooltip);position:absolute;bottom:100%;left:0;background:#1E293B;color:white;padding:4px 8px;border-radius:6px;font-size:10px;white-space:nowrap;display:none;z-index:1000;}
[data-tooltip]:hover:before{display:block;}

/* ── SIDEBAR TOGGLE FIX ───────────────────────────────────────────────── */
button[kind="header"] {
    visibility: visible !important;
    opacity: 1 !important;
    pointer-events: auto !important;
    z-index: 999 !important;
    background: transparent !important;
    border: none !important;
    cursor: pointer !important;
}
section[data-testid="stSidebar"] {
    transition: margin-left 0.3s ease !important;
}
header {
    visibility: visible !important;
    background: transparent !important;
}
/* MAIN panel gap from sidebar – increased for more space */
.main .block-container {
    margin-left: 40px !important;
    margin-right: 16px !important;
}
</style>
""", unsafe_allow_html=True)

# ── Session state + data load ──────────────────────────────────────────────────
init_session_state()
auto_load_data()

# ── Sidebar ────────────────────────────────────────────────────────────────────
render_sidebar()

# ── Data load guards ───────────────────────────────────────────────────────────
if st.session_state.data_error:
    st.error("Data load failed: " + st.session_state.data_error)
    st.stop()
if st.session_state.data is None:
    st.info("Loading data…")
    st.stop()

# ── Topbar ─────────────────────────────────────────────────────────────────────
st.markdown('<div class="accent-bar"></div>', unsafe_allow_html=True)
st.markdown(
    "<div class='topbar'>"
    "<div class='tt'>Supply Intelligence <span>/ FI11 Turku · Apr 2026</span></div>"
    "<div class='tbadge'>◈ Live</div>"
    "<div style='margin-left:auto;display:flex;align-items:center;gap:8px;'>"
    "<span class='ldot'></span>"
    "<span style='font-size:10px;color:var(--t3);'>Real-time</span>"
    "<div style='width:28px;height:28px;border-radius:7px;"
    "background:linear-gradient(135deg,var(--odk),var(--or));"
    "display:flex;align-items:center;justify-content:center;"
    "font-size:11px;font-weight:800;color:#fff;'>AI</div>"
    "</div></div>",
    unsafe_allow_html=True,
)

# ── Navigation ─────────────────────────────────────────────────────────────────
selected = option_menu(
    menu_title=None,
    options=["Command Center", "Material Intelligence", "Risk Radar", "Scenario Engine", "Supply Network"],
    icons=["grid", "search", "broadcast", "lightning", "diagram-3"],
    orientation="horizontal",
    styles={
        "container":       {"padding": "5px 20px", "background-color": "#FFFFFF", "border-bottom": "1px solid #E2E8F0"},
        "nav-link":        {"font-family": "Inter", "font-size": "12px", "font-weight": "500", "color": "#475569",
                            "padding": "6px 12px", "border-radius": "9px", "margin": "0 2px", "--hover-color": "#F0F4F9"},
        "nav-link-selected": {"background-color": "rgba(244,123,37,0.07)", "color": "#F47B25",
                              "border": "1px solid rgba(244,123,37,0.25)", "font-weight": "600"},
        "icon": {"font-size": "12px"},
    },
)

st.markdown('<div style="padding:16px 20px;">', unsafe_allow_html=True)

# ── Tab routing ────────────────────────────────────────────────────────────────
if   selected == "Command Center":        tab_cc.render()
elif selected == "Material Intelligence": tab_mi.render()
elif selected == "Risk Radar":            tab_rr.render()
elif selected == "Scenario Engine":       tab_se.render()
elif selected == "Supply Network":        tab_sn.render()

st.markdown('</div>', unsafe_allow_html=True)