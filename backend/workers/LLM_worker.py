import json
import os
from sqlalchemy.orm import Session
from datetime import timedelta
from groq import Groq

from db.db import SessionLocal
from db.models import AnomalyLog, DriftEvent, CognitiveInsight, DailyMetric

GROQAPI = os.getenv("GROQAPI")

def generate_hypothesis():
    if not GROQAPI:
        print("[!] Groq API Key missing. Cognitive Agent offline.")
        return

    client = Groq(api_key=GROQAPI)
    db: Session = SessionLocal()
    try:
        analyzed_anomaly_ids = [row[0] for row in db.query(CognitiveInsight.anomaly_id).filter(CognitiveInsight.anomaly_id.isnot(None)).all()]
        
        unexplained_anomaly = db.query(AnomalyLog)\
            .filter(~AnomalyLog.id.in_(analyzed_anomaly_ids))\
            .order_by(AnomalyLog.detected_at.desc()).first()

        if not unexplained_anomaly:
            return 
        
        metric = db.query(DailyMetric).filter(DailyMetric.id == unexplained_anomaly.metric_id).first()
        
        recent_drift = db.query(DriftEvent)\
            .filter(DriftEvent.timestamp >= unexplained_anomaly.detected_at - timedelta(hours=1))\
            .order_by(DriftEvent.timestamp.desc()).first()

        drift_context = recent_drift.drift_context if recent_drift else "No recent mathematical drift detected."
        
        system_prompt = """You are an elite MLOps AI Analyst. Your job is to read system telemetry and output a strict JSON hypothesis for why an anomaly occurred.
        You must reply with ONLY a valid JSON object matching this schema:
        {
            "verdict": "bot_traffic | pipeline_error | organic_spike | seasonal_drop | unknown",
            "root_cause_hypothesis": "A 2-sentence explanation of what mathematically broke and what likely caused it in the real world.",
            "recommended_action": "A 1-sentence instruction for the engineering or business team."
        }
        """

        user_prompt = f"""
        ANOMALY DETECTED:
        - Score: {unexplained_anomaly.anomaly_score}
        - Time: {unexplained_anomaly.detected_at}
        
        METRIC STATE DURING ANOMALY:
        - Revenue: ${metric.revenue}
        - Visitors: {metric.website_visitors}
        - Marketing Spend: ${metric.marketing_spend}
        
        RECENT SYSTEM DRIFT SIGNALS:
        {drift_context}
        """
        
        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            model="llama-3.1-8b-instant", 
            response_format={"type": "json_object"}
        )

        result = json.loads(response.choices[0].message.content)
        
        insight = CognitiveInsight(
            anomaly_id=unexplained_anomaly.id,
            drift_id=recent_drift.id if recent_drift else None,
            verdict=result.get("verdict", "unknown"),
            root_cause_hypothesis=result.get("root_cause_hypothesis", "Unable to parse hypothesis."),
            recommended_action=result.get("recommended_action", "Investigate manually.")
        )
        db.add(insight)
        db.commit()
        print(f"[🧠 AI Insight Generated] Anomaly #{unexplained_anomaly.id} | Verdict: {insight.verdict.upper()}")

    except Exception as e:
        db.rollback()
        print(f"[!] Cognitive Agent Error: {e}")
    finally:
        db.close()