from sqlalchemy.orm import Session 
from db.models import DailyMetric,AnomalyLog
from fastapi import HTTPException


def get_dashboard(db:Session):
    try:
        metrics = db.query(DailyMetric).order_by(DailyMetric.id.desc()).limit(50).all()
        
        results = []
        for m in metrics:
            anomaly = db.query(AnomalyLog).filter(AnomalyLog.metric_id == m.id).first()
            
            results.append({
                "id": m.id,
                "timestamp": m.timestamp.isoformat(),
                "revenue": float(m.revenue),
                "visitors": m.website_visitors,
                "is_anomaly": anomaly.is_anomaly if anomaly else False,
                "anomaly_score": anomaly.anomaly_score if anomaly else None
            })
            
        # Reverse the list so the oldest is first (better for graphing left-to-right)
        results.reverse()
        return {"data": results}
        
    except Exception as e:
        print(f"[!] Dashboard read error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch live data")