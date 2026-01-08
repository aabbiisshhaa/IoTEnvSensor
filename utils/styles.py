import streamlit as st

# --- AESTHETICS ---
def apply_styles():  
    st.markdown("""
    <style>
        .card {padding: 20px; border-radius: 14px; box-shadow: 0px 3px 8px rgba(0,0,0,0.1); text-align: left; margin: 10px 0px; }
        .card-temp {background-color: #e8f5e9;}
        .card-hum {background-color: #e3f2fd;}
        .card-motion {background-color: #fff3e0;}
        .card-battery {background-color: #f1f8e9;}
        .metric-value {font-size: 28px; font-weight: bold; margin: 5px 0px; color: #2e7d32; }
        .metric-label {font-size: 14px; color: #555; }
        .icon {width: 26px; height: 26px; vertical-align: middle; margin-right: 8px; }
        .status-good {color: #4caf50; }
        .status-warning {color: #ff9800; }

    </style>
    """, unsafe_allow_html=True)

# --- SVG ICONS ---
time_icon = """<svg xmlns="http://www.w3.org/2000/svg" fill="#ffb300" class="icon" viewBox="0 0 24 24"><path d="M12 1a11 11 0 1011 11A11.013 11.013 0 0012 1zm0 20a9 9 0 119-9 9.01 9.01 0 01-9 9zm.5-13h-1v6l5.25 3.15.5-.86-4.75-2.79z"/></svg>"""
therm_icon = """<svg xmlns"http://www.w3.org/2000/svg" fill="#e53935" class="icon" viewBox="0 0 24 24"><path d="M14 14.76V5a2 2 0 10-4 0v9.76a5 5 0 104 0z"/></svg>"""
hum_icon = """<svg xmlns="http://www.w3.org/2000/svg" fill="#1e88e5" class="icon" viewBox="0 0 24 24"><path d="M12 2.69L17.66 9a7 7 0 11-11.32 0L12 2.69z"/></svg>"""
batt_icon = """<svg xmlns="http://www.w3.org/2000/svg" fill="#4caf50" class="icon" viewBox="0 0 24 24"><path d="M15.67 4H14V2h-4v2H8.33C7.6 4 7 4.6 7 5.33v15.33C7 21.4 7.6 22 8.33 22h7.33c.74 0 .74-.6 .74-1.33V5.33C17 .6 .6 .6 .6 .6V5.33C-.8 .8 -8 -8 -8 -8z"/></svg>"""
motion_icon = """<svg xmlns="http://www.w3.org/2000/svg" fill="#fb8c00" class="icon" viewBox="0 0 24 24"><path d="M12 4a8 8 0 108 8 8.009 8.009 0 00-8-8zm0 14a6 6 0 116-6 6.007 6.007 0 01-6 6zm0-10a4 4 0 104 4 4.005 4.005 0 00-4-4z"/></svg>"""
sig_icon = """<svg xmlns="http://www.w3.org/2000/svg" fill="#ff9800" class="icon" viewBox="0 0 24 24"><path d="M1 9l2 2c4.97-4.97 13.03-4.97 18 0l2-2C16.93 2.93 7.07 2.93 1 9z"/></svg>"""

