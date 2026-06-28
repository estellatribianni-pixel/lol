
from datetime import datetime,timezone
from db.models import ForecastResult

def get_forecast(db):
    now = datetime.now(timezone.utc)
    forecasts = db.query(ForecastResult).filter(ForecastResult.target_timestamp > now).order_by(ForecastResult.target_timestamp.asc()).limit(12).all()
    
    results = [{
        "timestamp": f.target_timestamp.isoformat(),
        "predicted_revenue": float(f.predicted_revenue),
        "lower_bound": float(f.lower_bound),
        "upper_bound": float(f.upper_bound)
    } for f in forecasts]
    
    return {"data": results}