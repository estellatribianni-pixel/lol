from sqlalchemy import Column, Integer, Float, DateTime , ForeignKey , Boolean,String
from sqlalchemy.sql import func
from db.db import base 

class RawIncomingEvent(base):
    __tablename__ = "raw_events"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(String, index=True)
    order_status = Column(String)
    payment_value = Column(Float, nullable=False)
    event_timestamp = Column(DateTime(timezone=True), nullable=False)
    ingested_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # revenue = Column(Float, nullable=False)
    # visitors = Column(Integer, nullable=False)
    # marketing_spend = Column(Float, nullable=False)
    
    # ELT pipeline
    is_processed = Column(Boolean, default=False, index=True)
class DailyMetric(base):
    __tablename__ = "daily_metrics"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    revenue = Column(Float, nullable=False)
    website_visitors = Column(Integer, nullable=False)
    marketing_spend = Column(Float, nullable=False)

class AnomalyLog(base):
    __tablename__ = "anomaly_logs"

    id = Column(Integer, primary_key=True, index=True)
    metric_id = Column(Integer, ForeignKey("daily_metrics.id", ondelete="CASCADE"), nullable=False)
    anomaly_score = Column(Float, nullable=False)
    is_anomaly = Column(Boolean, nullable=False, index=True)
    detected_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    # Validation
    is_true_anomaly = Column(Boolean, nullable=True) 
    reviewed_at = Column(DateTime(timezone=True), nullable=True)

class ForecastResult(base):
    __tablename__ = "forecast_results"

    id = Column(Integer, primary_key=True, index=True)
    target_timestamp = Column(DateTime(timezone=True), index=True, nullable=False)
    predicted_revenue = Column(Float, nullable=False)
    lower_bound = Column(Float, nullable=True) 
    upper_bound = Column(Float, nullable=True)
    generated_at = Column(DateTime(timezone=True), server_default=func.now())
    
class DriftEvent(base):
    __tablename__ = "drift_events"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    psi_score = Column(Float, nullable=False)
    covariance_delta = Column(Float, nullable=False)
    severity = Column(String, nullable=False) 
    drift_context = Column(String, nullable=False) # for the LLM to read later
    
class CognitiveInsight(base):
    __tablename__ = "cognitive_insights"

    id = Column(Integer, primary_key=True, index=True)
    anomaly_id = Column(Integer, ForeignKey("anomaly_logs.id", ondelete="CASCADE"), nullable=True)
    drift_id = Column(Integer, ForeignKey("drift_events.id", ondelete="CASCADE"), nullable=True)
    # The LLM's structured output
    verdict = Column(String, nullable=False) # e.g., "bot_traffic", "organic_spike", "data_pipeline_error"
    root_cause_hypothesis = Column(String, nullable=False)
    recommended_action = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
class ModelRegistry(base):
    """Tracks the lifecycle of ML models in production."""
    __tablename__ = "model_registry"

    id = Column(Integer, primary_key=True, index=True)
    model_name = Column(String, nullable=False)
    version = Column(Integer, nullable=False)
    # "champion", "challenger", or "retired"
    status = Column(String, nullable=False) 
    parameters = Column(String, nullable=True) 
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class ShadowAnomalyLog(base):
    """Stores the hidden predictions of the Challenger model."""
    __tablename__ = "shadow_anomaly_logs"

    id = Column(Integer, primary_key=True, index=True)
    metric_id = Column(Integer, ForeignKey("daily_metrics.id", ondelete="CASCADE"))
    model_id = Column(Integer, ForeignKey("model_registry.id", ondelete="CASCADE"))
    anomaly_score = Column(Float, nullable=False)
    is_anomaly = Column(Boolean, nullable=False)
    detected_at = Column(DateTime(timezone=True), server_default=func.now())