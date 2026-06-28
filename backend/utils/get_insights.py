
from db.models import CognitiveInsight
def get_insights(db):
    insights = db.query(CognitiveInsight).order_by(CognitiveInsight.created_at.desc()).limit(10).all()
    return {"data": [{
        "anomaly_id": i.anomaly_id,
        "verdict": i.verdict,
        "hypothesis": i.root_cause_hypothesis,
        "action": i.recommended_action
        # "created_at": i.created_at.isoformat() if i.created_at else None
    } for i in insights]}