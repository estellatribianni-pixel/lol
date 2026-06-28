import pandas as pd
import numpy as np
from db.db import SessionLocal
from db.models import DailyMetric, AnomalyLog, ModelRegistry, ShadowAnomalyLog
import time
import os
import joblib
from sqlalchemy.orm import Session
from sqlalchemy import func

MODEL_DIR = "model_artifacts"

def execute_ml():
    db: Session = SessionLocal()

    try:
        champion_meta = db.query(ModelRegistry).filter(
            func.lower(ModelRegistry.status) == "champion", 
            ModelRegistry.model_name == "isoforest"
        ).first()
        
        challenger_meta = db.query(ModelRegistry).filter(
            func.lower(ModelRegistry.status) == "challenger", 
            ModelRegistry.model_name == "isoforest"
        ).first()

        if not champion_meta:
            return 
        
        records = db.query(DailyMetric).order_by(DailyMetric.id.desc()).limit(100).all()
        if len(records) < 10:
            print(f"[Watchdog] Insufficient data window (< 10 rows). Current rows: {len(records)}")
            return
        
        records.reverse()    
        data = [{
            "id": r.id, 
            "revenue": float(r.revenue), 
            "visitors": r.website_visitors, 
            "marketing": float(r.marketing_spend),
            "timestamp": r.timestamp
        } for r in records]
        
        df = pd.DataFrame(data)

        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df["hour_sin"] = np.sin(2 * np.pi * df["timestamp"].dt.hour / 24.0)
        df["hour_cos"] = np.cos(2 * np.pi * df["timestamp"].dt.hour / 24.0)
        df["is_weekend"] = (df["timestamp"].dt.dayofweek >= 5).astype(int)
        
        features = df[["revenue", "visitors", "marketing", "hour_sin", "hour_cos", "is_weekend"]]
        
        champ_model_path = f"{MODEL_DIR}/isoforest_v{champion_meta.version}.pkl"
        champ_scaler_path = f"{MODEL_DIR}/scaler_v{champion_meta.version}.pkl"
        
        if os.path.exists(champ_model_path) and os.path.exists(champ_scaler_path):
            champion_model = joblib.load(champ_model_path)
            champion_scaler = joblib.load(champ_scaler_path)
            
            champ_scaled = champion_scaler.transform(features)
            
            df["champ_score"] = champion_model.decision_function(champ_scaled)
            df["champ_anomaly"] = champion_model.predict(champ_scaled) == -1
            anomalies_found = 0
            
            for _, row in df[df["champ_anomaly"] == True].iterrows():
                exists = db.query(AnomalyLog).filter(AnomalyLog.metric_id == int(row["id"])).first()
                if not exists:
                    log = AnomalyLog(
                        metric_id=int(row["id"]),
                        anomaly_score=float(row["champ_score"]), # FIX 3: Map to champ_score
                        is_anomaly=True
                    )
                    db.add(log)
                    anomalies_found += 1
            if anomalies_found > 0:
                print(f"[Champion v{champion_meta.version}] Logged {anomalies_found} live anomalies.")
                
            db.commit()
    except Exception as e:
        db.rollback()
        print(f"[Watchdog CRASH] Operational failure during ML calculation: {e}")
    finally:
        db.close()
