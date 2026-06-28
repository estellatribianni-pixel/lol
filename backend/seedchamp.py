import joblib
import os
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from db.db import SessionLocal
from db.models import ModelRegistry

db = SessionLocal()

os.makedirs("model_artifacts", exist_ok=True)

df = pd.DataFrame({"revenue": [100]*10, "visitors": [10]*10, "marketing": [5]*10, "hour_sin": [0]*10, "hour_cos": [1]*10, "is_weekend": [0]*10})

scaler = StandardScaler()
scaler.fit(df)
joblib.dump(scaler, "model_artifacts/scaler_v1.pkl")

baseline = IsolationForest(contamination=0.02, random_state=42)
baseline.fit(df)
joblib.dump(baseline, "model_artifacts/isoforest_v1.pkl")

if not db.query(ModelRegistry).first():
    db.add(ModelRegistry(model_name="isoforest", version=1, status="champion", parameters="{}"))
    db.commit()
    print("[+] Initial Champion v1 & Scaler seeded successfully.")
else:
    print("[+] Files updated. Registry already has Champion.")