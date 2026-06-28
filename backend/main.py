# from dotenv import load_dotenv
# load_dotenv()        FOR uvicorn main:app --reload (locally running db)

from fastapi import FastAPI, HTTPException ,Depends,Security
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session

from db.db import engine, get_db, base
from db.models import RawIncomingEvent,AnomalyLog,CognitiveInsight,ModelRegistry
from db.schemas import IncomingEvent,LabelRequest
import os
from contextlib import asynccontextmanager
from utils.dashboard import get_dashboard
from utils.label_anomaly import get_label_anomaly
from utils.get_forecast import get_forecast
from utils.get_history import get_history
from utils.get_insights import get_insights

@asynccontextmanager
async def lifespan(app:FastAPI):
    base.metadata.create_all(bind=engine)
    print("[*] Database schema initialized")
    yield
    print("[*] Terminating server...")
    
from db.models import ModelRegistry

app=FastAPI(title="bizintel",lifespan=lifespan)

api_key_header = APIKeyHeader(name="X-API-Key",auto_error=True)

def verify_api_key(api_key: str = Security(api_key_header)):
    expected_key = os.getenv("INGEST_API_KEY")
    if api_key != expected_key:
        raise HTTPException(status_code=403, detail="Could not validate API Key")
    return api_key

@app.get("/registry")
def get_registry(db: Session = Depends(get_db)):
    models = db.query(ModelRegistry).order_by(ModelRegistry.version.desc()).limit(10).all()
    return {"data": [{
        "version": m.version,
        "status": m.status.upper(),
        "parameters": m.parameters,
        "created_at": m.created_at.isoformat() if m.created_at else None
    } for m in models]}
    
@app.post("/ingest", dependencies=[Depends(verify_api_key)])
def ingest_live(event :IncomingEvent,db: Session = Depends(get_db)):
    try:
        raw_event = RawIncomingEvent(
         order_id=event.order_id,
            order_status=event.order_status,
            payment_value=event.payment_value,
            event_timestamp=event.timestamp
        )
        db.add(raw_event)
        db.commit() 
        print(f"[Vault ->] Captured: ${event.order_id} | Status: {event.order_status}")
        return {"status": "success"}
    except Exception as e:
        db.rollback() # If something crashes, undo the database transaction
        print(f"[!] Database Error: {e}")
        raise HTTPException(status_code=500, detail="Database write failed")
    
@app.get("/dashboard/live")
def get_live_dashboard(db:Session = Depends(get_db)):
    return get_dashboard(db)


@app.post("/label/{anomaly_id}")
def label_anomaly(anomaly_id :int , request : LabelRequest , db:Session = Depends(get_db)):
    return get_label_anomaly(anomaly_id,request,db)

@app.get("/dashboard/history")
def history(db: Session = Depends(get_db)):
    return get_history(db)

@app.get("/dashboard/forecast")
def forecast(db: Session = Depends(get_db)):
    return get_forecast(db)    

@app.get("/insights")
def insights(db: Session = Depends(get_db)):
    return get_insights(db)