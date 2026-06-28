from pydantic import BaseModel, ConfigDict,Field
from datetime import datetime
from typing import Optional

class IncomingEvent(BaseModel):
    order_id: str = Field(..., description="Olist Order ID")
    order_status: str = Field(..., description="e.g., delivered, canceled")
    payment_value: float = Field(..., description="Total payment value", ge=0)
    timestamp: datetime = Field(..., description="Order purchase timestamp")

class DailyMetricResponse(BaseModel):
    id: int
    revenue: float
    website_visitors: int
    marketing_spend: float
    timestamp: datetime

    class Config:
        from_attributes = True 

        
class AnomalyLogResponse(BaseModel):
    """Validation schema for exposing anomaly outputs to the dashboard."""
    id: int
    metric_id: int
    anomaly_score: float
    is_anomaly: bool
    detected_at: datetime

    model_config = ConfigDict(from_attributes=True)
    
class ForecastResponse(BaseModel):
    target_timestamp: datetime
    predicted_revenue: float
    lower_bound: float
    upper_bound: float
    
    model_config = ConfigDict(from_attributes=True)

class LabelRequest(BaseModel):
    is_true_anomaly: bool = Field(..., description="Validation of the anomaly")