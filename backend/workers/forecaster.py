import asyncio
import pandas as pd
import numpy as np
import xgboost as xgb
from sqlalchemy.orm import Session

from db.db import SessionLocal
from db.models import DailyMetric, ForecastResult

from datetime import timedelta,datetime,timezone
import time
def xgb_worker():
    db:Session = SessionLocal()
    try:
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=14)
        records = db.query(DailyMetric).filter(
            DailyMetric.timestamp >= cutoff_date
        ).order_by(DailyMetric.timestamp.asc()).all()
        
        if len(records) < 24:
            print(f"[Forecaster] Insufficient data ({len(records)}). Need at least 24 rows for lag features. Waiting...")
            return

        df = pd.DataFrame([{
            "timestamp": r.timestamp,
            "revenue": float(r.revenue),
            "visitors": r.website_visitors,
            "marketing": float(r.marketing_spend)
        } for r in records])
        
        df = df.set_index("timestamp")
        df["hour"] = df.index.hour
        df["day_of_week"] = df.index.dayofweek
        
        df["hour_sin"]= np.sin(2 * np.pi *df["hour"] / 24.0)
        df["hour_cos"] = np.cos(2 * np.pi * df["hour"] / 24.0)
        df["is_weekend"] = (df["day_of_week"] >= 5).astype(int)
        
        df["lag_1h_revenue"] = df["revenue"].shift(1)
        df["lag_24h_revenue"] = df["revenue"].shift(24)
        
        df["rolling_6h_mean"] = df["revenue"].rolling(window=6).mean()

        df = df.bfill().fillna(0)

        features = ["hour_sin","hour_cos","is_weekend", "day_of_week", "lag_1h_revenue", "lag_24h_revenue", "rolling_6h_mean"]
        target = "revenue"

        X = df[features]
        y = df[target]

        model = xgb.XGBRegressor(n_estimators=100, learning_rate=0.05, max_depth=4, random_state=42)
        model.fit(X, y)

        last_known_time = df.index[-1]
        future_times = [last_known_time + timedelta(hours=i) for i in range(1, 13)]
        
        revenue_history = df["revenue"].tolist()
        
        for i, target_time in enumerate(future_times):
            h_sin, h_cos, is_wknd = get_cyclical_time(target_time)
            dow=target_time.dayofweek
            lag_1h = revenue_history[-1]
            lag_24h = revenue_history[-24] if len(revenue_history) >= 24 else np.mean(revenue_history)
            rolling_6h = np.mean(revenue_history[-6:])
            
            # Create a single-row DataFrame for the prediction
            pred_df = pd.DataFrame([[
                h_sin, h_cos,is_wknd, dow,  lag_1h, lag_24h, rolling_6h
            ]], columns=features)
            
            pred_revenue = float(model.predict(pred_df)[0])
            
            revenue_history.append(pred_revenue)
            lower = pred_revenue * 0.85
            upper = pred_revenue * 1.15

            existing = db.query(ForecastResult).filter(ForecastResult.target_timestamp == target_time).first()
            if existing:
                existing.predicted_revenue = pred_revenue
                existing.lower_bound = lower
                existing.upper_bound = upper
            else:
                forecast = ForecastResult(
                    target_timestamp=target_time,
                    predicted_revenue=pred_revenue,
                    lower_bound=lower,
                    upper_bound=upper
                )
                db.add(forecast)
                
        db.commit()
        print(f"[+] Forcaster: Trained new XGBoost model. Generated {len(future_times)} future hourly predictions.")

    except Exception as e:
        db.rollback()
        print(f"[!] Forcaster Pipeline Failed: {e}")
    finally:
        db.close()
        
def get_cyclical_time(dt_obj):
    hour_sin = np.sin(2 * np.pi * dt_obj.hour / 24.0)
    hour_cos = np.cos(2 * np.pi * dt_obj.hour / 24.0)
    is_weekend = int(dt_obj.dayofweek >= 5)
    return hour_sin, hour_cos, is_weekend
