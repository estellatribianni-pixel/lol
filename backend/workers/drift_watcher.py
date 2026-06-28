import pandas as pd
import numpy as np
import json
import time
from sqlalchemy.orm import Session
from datetime import datetime,timedelta,timezone
from db.db import SessionLocal
from db.models import DailyMetric,DriftEvent

def calculate_psi(expected,actual,buckets):
    breakpoints = np.percentile(expected, np.linspace(0, 100, buckets + 1))
    breakpoints = np.unique(breakpoints)
    
    if len(breakpoints) < 2: 
        return 0.0 
        
    expected_percents = np.histogram(expected, bins=breakpoints)[0] / len(expected)
    actual_percents = np.histogram(actual, bins=breakpoints)[0] / len(actual)
    
    expected_percents = np.where(expected_percents == 0, 0.0001, expected_percents)
    actual_percents = np.where(actual_percents == 0, 0.0001, actual_percents)
    
    psi = np.sum((actual_percents - expected_percents) * np.log(actual_percents / expected_percents))
    return float(psi)


def calc_covariance_shift(df_ref,df_cur):
    
    cov_ref = df_ref.cov().fillna(0).values
    cov_cur = df_cur.cov().fillna(0).values
    
    diff_norm = np.linalg.norm(cov_ref - cov_cur, ord='fro')
    ref_norm = np.linalg.norm(cov_ref, ord='fro') + 1e-5
    
    return float(diff_norm / ref_norm)

def drift_check():
    db=SessionLocal()
    
    try:
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=60)
        records = db.query(DailyMetric).filter(DailyMetric.timestamp >= cutoff_date).order_by(DailyMetric.timestamp.asc()).all()
        if len(records) < 150:
            print("[Observatory] Insufficient data to calculate drift matrix (< 150 hours).")
            return
            
        df = pd.DataFrame([{
            "revenue": float(r.revenue),
            "visitors": r.website_visitors,
            "marketing": float(r.marketing_spend)
        } for r in records])
        
        midpoint = len(df) // 2
        df_ref=df.iloc[:midpoint]
        df_cur=df.iloc[midpoint:]
        
        psi_rev=calculate_psi(df_ref["revenue"].values, df_cur["revenue"].values,10)
        
        cov_shift=calc_covariance_shift(df_ref[["revenue", "visitors", "marketing"]], 
                                               df_cur[["revenue", "visitors", "marketing"]])
        
        
        severity=None
        if psi_rev > 0.25 or cov_shift > 0.6:
            severity = "CRITICAL"
        elif psi_rev > 0.1 or cov_shift > 0.3:
            severity = "WARNING"
        
        
        if severity:
            last_event = db.query(DriftEvent).order_by(DriftEvent.timestamp.desc()).first()
            if last_event:
                time_since = datetime.now(timezone.utc) - last_event.timestamp.replace(tzinfo=timezone.utc)
                if time_since.total_seconds() < 900:
                    return
                    
            context = {
                "psi_revenue": round(psi_rev, 4),
                "covariance_shift_ratio": round(cov_shift, 4),
                "baseline_mean_revenue": float(df_ref["revenue"].mean()),
                "current_mean_revenue": float(df_cur["revenue"].mean())
            }
            
            drift_log = DriftEvent(
                psi_score=float(psi_rev),
                covariance_delta=float(cov_shift),
                severity=severity,
                drift_context=json.dumps(context)
            )
            db.add(drift_log)
            db.commit()
            print(f"[DRIFT DETECTED] Severity: {severity} | PSI: {psi_rev:.3f} | Covariance Shift: {cov_shift:.2%}")
    
    except Exception as e:
        db.rollback()
        print(f"[!] Drift Observatory Failed: {e}")
    finally:
        db.close()

        
        