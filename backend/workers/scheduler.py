import os
import sys
import logging
from apscheduler.schedulers.blocking import BlockingScheduler

from pipeline.ETL_worker import etl_pipeline
from workers.isoforest import execute_ml
from workers.forecaster import xgb_worker
from workers.drift_watcher import drift_check
from workers.LLM_worker import generate_hypothesis # Integrated the AI Reasoner
from workers.model_registry import execute_registry_worker # Integrated the AI Reasoner

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", stream=sys.stdout)
logger = logging.getLogger("Scheduler")

def main():
    scheduler = BlockingScheduler()

    interval_etl = int(os.getenv("INTERVAL_ETL", 15))
    interval_ml = int(os.getenv("INTERVAL_ML", 30))
    interval_forecast = int(os.getenv("INTERVAL_FORECAST", 600))
    interval_drift = int(os.getenv("INTERVAL_DRIFT", 900))
    interval_llm = int(os.getenv("INTERVAL_LLM", 60))
    interval_registry = 45

    scheduler.add_job(etl_pipeline, 'interval', seconds=interval_etl, id="etl_job")
    scheduler.add_job(execute_ml, 'interval', seconds=interval_ml, id="watchdog_job")
    scheduler.add_job(xgb_worker, 'interval', seconds=interval_forecast, id="forecaster_job")
    scheduler.add_job(drift_check, 'interval', seconds=interval_drift, id="drift_job")
    scheduler.add_job(generate_hypothesis, 'interval', seconds=interval_llm, id="llm_job")
    scheduler.add_job(execute_registry_worker, 'interval', seconds=interval_registry, id="registry_job")
    logger.info(f"[*] Central Job Scheduler Starting...")
    logger.info(f"[*] Intervals (seconds) -> ETL:{interval_etl} | ML:{interval_ml} | Forecast:{interval_forecast} | Drift:{interval_drift} | AI:{interval_llm}")
    
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("[-] Scheduler terminated.")

if __name__ == "__main__":
    main()