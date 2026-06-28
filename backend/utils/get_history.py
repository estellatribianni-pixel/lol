
from datetime import datetime,timezone
from db.models import AnomalyLog,DailyMetric

def get_history(db):
    metrics = db.query(DailyMetric).order_by(DailyMetric.timestamp.desc()).limit(50).all()
    
    results = []
    for m in metrics:
        anomaly = db.query(AnomalyLog).filter(AnomalyLog.metric_id == m.id).first()
        results.append({
            "id": m.id,
            "timestamp": m.timestamp.isoformat(),
            "revenue": float(m.revenue),
            "visitors": m.website_visitors,
            "is_anomaly": anomaly.is_anomaly if anomaly else False,
            "anomaly_id": anomaly.id if anomaly else None,
            "is_true_anomaly": anomaly.is_true_anomaly if anomaly else None
        })
    results.reverse()
    return {"data": results}