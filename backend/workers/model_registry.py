import optuna
import joblib
import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
import time

from db.db import SessionLocal
from db.models import DailyMetric, DriftEvent, ModelRegistry, AnomalyLog, ShadowAnomalyLog

import os
import json
from sklearn.preprocessing import StandardScaler

MODEL_DIR = "model_artifacts"
os.makedirs(MODEL_DIR, exist_ok=True)


def train_w_optuna(db):
    records=db.query(DailyMetric).order_by(DailyMetric.timestamp.asc()).limit(200).all()
    if len(records)<50: return

    df = pd.DataFrame([{
        "revenue": r.revenue, 
        "visitors": r.website_visitors, 
        "marketing": r.marketing_spend,
        "timestamp": r.timestamp
    } for r in records])
    
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df["hour_sin"] = np.sin(2 * np.pi * df["timestamp"].dt.hour / 24.0)
    df["hour_cos"] = np.cos(2 * np.pi * df["timestamp"].dt.hour / 24.0)
    df["is_weekend"] = (df["timestamp"].dt.dayofweek >= 5).astype(int)
    
    features = df[["revenue", "visitors", "marketing", "hour_sin", "hour_cos", "is_weekend"]]

    scaler = StandardScaler()
    scaled_features = scaler.fit_transform(features)
        
    def objective(trial):
        contaminate=trial.suggest_float("contamination",.01,.1)
        max_samples=trial.suggest_float("max_samples",.5,1)
        
        model=IsolationForest(contamination=contaminate,max_samples=max_samples,random_state=42)
        model.fit(scaled_features)
        
        score=model.decision_function(scaled_features)
        return score.mean()
    
    print("[*] Forge: Optuna is searching for the optimal model configuration...")
    study = optuna.create_study(direction="maximize")
    study.optimize(objective, n_trials=20)
    best_params = study.best_params
    print(f"[+] Forge: Optimal parameters found: {best_params}")

    challenger = IsolationForest(**best_params, random_state=42)
    challenger.fit(scaled_features)

    latest = db.query(ModelRegistry).filter(ModelRegistry.model_name == "isoforest").count() + 1
    model_path = f"{MODEL_DIR}/isoforest_v{latest}.pkl"
    scaler_path = f"{MODEL_DIR}/scaler_v{latest}.pkl"
    joblib.dump(challenger, model_path)
    joblib.dump(scaler, scaler_path)

    new_registry = ModelRegistry(
        model_name="isoforest",
        version=latest,
        status="challenger",
        parameters=json.dumps(best_params)
    )
    db.add(new_registry)
    db.commit()
    print(f"[+] Registry: Challenger v{latest} deployed to Shadow Mode.")

def eval_promote(db):
    champion = db.query(ModelRegistry).filter(ModelRegistry.status == "champion").first()
    challenger = db.query(ModelRegistry).filter(ModelRegistry.status == "challenger").first()

    if not champion or not challenger: return

    labeled_anomalies = db.query(AnomalyLog).filter(AnomalyLog.is_true_anomaly.isnot(None)).order_by(AnomalyLog.id.desc()).limit(100).all()
    if len(labeled_anomalies) < 10: return

    champ_correct = 0
    challenger_correct = 0
    for anomaly in labeled_anomalies:
        if anomaly.is_anomaly == anomaly.is_true_anomaly: champ_correct += 1

        shadow = db.query(ShadowAnomalyLog).filter(ShadowAnomalyLog.metric_id == anomaly.metric_id).first()
        if shadow and shadow.is_anomaly == anomaly.is_true_anomaly:
            challenger_correct += 1

    champ_accuracy = champ_correct / len(labeled_anomalies)
    challenger_accuracy = challenger_correct / len(labeled_anomalies)

    if challenger_accuracy > champ_accuracy:
        print(f" Challenger (v{challenger.version}) beat Champion (v{champion.version}). Accuracy: {challenger_accuracy:.2%} > {champ_accuracy:.2%}")
        champion.status = "retired"
        challenger.status = "champion"
        db.commit()

def run_registry(db):
    try:
        drift=db.query(DriftEvent).filter(DriftEvent.severity=='CRITICAL').order_by(DriftEvent.timestamp.desc()).first()
        challenger=db.query(ModelRegistry).filter(ModelRegistry.status=="challenger").first()
        
        if drift and not challenger:
            train_w_optuna(db)
            
        if challenger: eval_promote(db)
    except Exception as e:
        db.rollback()
        print(f"[!] Registry Error: {e}")
    finally:
        db.close()
        
def execute_registry_worker():
    db = SessionLocal()
    try:
        run_registry(db)
    finally:
        db.close()
    