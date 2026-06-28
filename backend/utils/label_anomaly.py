
from db.models import AnomalyLog
from fastapi import HTTPException
from datetime import datetime,timezone

def get_label_anomaly(anomaly_id,req,db):
    anomaly=db.query(AnomalyLog).filter(AnomalyLog.id==anomaly_id).first()
    if not anomaly: raise HTTPException(status_code=404,detail="Anomaly not found")
    try:
        anomaly.is_true_anomaly=req.is_true_anomaly
        anomaly.reviewed_at=datetime.now(timezone.utc)
        
        db.commit()
        
        status_msg = "Confirmed as True Anomaly" if req.is_true_anomaly else "Rejected as False Positive"
        print(f"[Feedback] Anomaly {anomaly_id} reviewed: {status_msg}")
        
        return {"status": "success", "message": status_msg}

    except Exception as e:
        db.rollback()
        print(f"[!] Labeling Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to save human feedback")