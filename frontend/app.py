import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
import time
import json
import os
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="BizIntel Command", layout="wide", initial_sidebar_state="expanded")

API_BASE = "http://localhost:8080"
SECURE_KEY = os.getenv("INGEST_API_KEY")
HEADERS = {"X-API-Key": SECURE_KEY}

def fetch_api(endpoint):
    try:
        res = requests.get(f"{API_BASE}/{endpoint}", headers=HEADERS)
        if res.status_code == 200: 
            return res.json().get("data", [])
    except Exception as e: 
        pass
    return []

def submit_label(anomaly_id, is_true):
    try:
        res = requests.post(
            f"{API_BASE}/label/{anomaly_id}", 
            json={"is_true_anomaly": is_true},
            headers=HEADERS
        )
        if res.status_code == 200:
            st.toast(f"Labeled Anomaly #{anomaly_id}", icon="✅")
        else:
            st.error("Failed to submit feedback. Check API logs.")
    except Exception as e: 
        st.error(f"Connection error: {e}")

with st.sidebar:
    st.title("⚡ BizIntel System")
    st.markdown("### 🧠 AI Analyst Insights")
    insights = fetch_api("insights")
    if insights:
        for i in insights:
            anomaly_id = i.get('anomaly_id', 'N/A')
            verdict = i.get('verdict', 'UNKNOWN').upper()
            hypothesis = i.get('root_cause_hypothesis', 'Awaiting hypothesis...')
            action = i.get('recommended_action', 'Awaiting action...')
            
            with st.expander(f"Anomaly #{anomaly_id} | {verdict}", expanded=True):
                st.write(f"**Hypothesis:** {hypothesis}")
                st.caption(f"**Action:** {action}")
    else:
        st.info("AI Reasoner listening for anomalies...")

# --- MAIN DASHBOARD ---
st.title("📊 Enterprise MLOps Platform")

tab1, tab2 = st.tabs(["📡 Live Telemetry & Inference", "⚙️ Model Registry & AutoML Forge"])

history = fetch_api("dashboard/history")
forecasts = fetch_api("dashboard/forecast")
registry = fetch_api("registry")

with tab1:
    if history:
        df_hist = pd.DataFrame(history)
        
        # Action Center (Review Queue)
        unreviewed = df_hist[(df_hist["is_anomaly"] == True) & (df_hist["is_true_anomaly"].isnull())]
        if not unreviewed.empty:
            st.error(f"⚠️ **ACTION REQUIRED:** {len(unreviewed)} Unreviewed Anomalies")
            cols = st.columns(min(len(unreviewed), 4))
            for idx, row in unreviewed.head(4).reset_index().iterrows():
                with cols[idx]:
                    st.markdown(f"**ID #{row['anomaly_id']}** | ${row['revenue']:.2f}")
                    c1, c2 = st.columns(2)
                    if c1.button("✅ True", key=f"t_{row['anomaly_id']}", use_container_width=True):
                        submit_label(row['anomaly_id'], True)
                        time.sleep(0.5) 
                        st.rerun() 
                    if c2.button("❌ False", key=f"f_{row['anomaly_id']}", use_container_width=True):
                        submit_label(row['anomaly_id'], False)
                        time.sleep(0.5) 
                        st.rerun() 
        
        # Master Chart
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df_hist["timestamp"], y=df_hist["revenue"], mode='lines', name='Actual Revenue', line=dict(color='#2E86C1', width=3)))
        
        for _, row in df_hist[df_hist["is_anomaly"] == True].iterrows():
            color = 'red' if row.get("is_true_anomaly") is not False else 'grey'
            fig.add_trace(go.Scatter(x=[row["timestamp"]], y=[row["revenue"]], mode='markers', name='Anomaly', marker=dict(color=color, size=12, symbol='x'), showlegend=False))

        if forecasts:
            df_fore = pd.DataFrame(forecasts)
            fig.add_trace(go.Scatter(x=df_fore["timestamp"], y=df_fore["predicted_revenue"], mode='lines', name='Forecast', line=dict(color='#27AE60', dash='dot', width=3)))

        fig.update_layout(height=500, margin=dict(l=0, r=0, t=30, b=0), hovermode="x unified")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Waiting for telemetry data...")

with tab2:
    st.markdown("### 🏆 Champion-Challenger Registry")
    st.markdown("Tracks models trained dynamically by the Optuna AutoML Forge in response to data drift.")
    
    if registry:
        df_reg = pd.DataFrame(registry)
        champion_df = df_reg[df_reg["status"] == "CHAMPION"]
        challenger_df = df_reg[df_reg["status"] == "CHALLENGER"]
        col1, col2 = st.columns(2)
        
        with col1:
            if not champion_df.empty:
                champion = champion_df.iloc[0]
                st.success(f"### 👑 ACTIVE CHAMPION (v{champion['version']})")
                # Handle parameters whether they arrive as a string or a dict
                params = champion.get("parameters", "{}")
                if isinstance(params, str):
                    try: params = json.loads(params)
                    except: pass
                st.code(json.dumps(params, indent=2), language="json")
            else:
                st.warning("No Champion deployed. Awaiting seed.")
                
        with col2:
            if not challenger_df.empty:
                challenger = challenger_df.iloc[0]
                st.info(f"### 🥷 SHADOW CHALLENGER (v{challenger['version']})")
                st.markdown("*Running silently in background to calculate shadow F1 score against human labels.*")
                
                params = challenger.get("parameters", "{}")
                if isinstance(params, str):
                    try: params = json.loads(params)
                    except: pass
                st.code(json.dumps(params, indent=2), language="json")
            else:
                st.info("No Challenger active. Pipeline stable.")
        
        st.divider()
        st.markdown("#### Deployment History")
        st.dataframe(df_reg[["version", "status", "created_at"]], use_container_width=True, hide_index=True)
    else:
        st.info("Model Registry is currently empty.")

time.sleep(3)
st.rerun()