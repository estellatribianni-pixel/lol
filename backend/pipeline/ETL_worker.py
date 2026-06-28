import time
import polars as pl
from sqlalchemy.orm import Session
from sqlalchemy import update
from db.db import SessionLocal
from db.models import RawIncomingEvent,DailyMetric
import numpy as np

def etl_pipeline():
    db: Session = SessionLocal()
    try:
        unprocessed = db.query(RawIncomingEvent).filter(RawIncomingEvent.is_processed == False).limit(5000).with_for_update(skip_locked=True).all()        
        if not unprocessed:
            return

        print(f"[*] ETL: Processing {len(unprocessed)} raw events...")

        data = [{
            "id": r.id,"timestamp": r.event_timestamp,
            "order_status": r.order_status,
            "payment_value": r.payment_value
        } for r in unprocessed]
        
        df = pl.DataFrame(data)

        valid_orders = df.filter(~pl.col("order_status").is_in(["canceled", "unavailable"]))
        
        if valid_orders.is_empty():
            print("[-] No valid orders to aggregate after filtering.")
            # Mark as processed
            db.execute(update(RawIncomingEvent).where(RawIncomingEvent.id.in_(df["id"].to_list())).values(is_processed=True))
            db.commit()
            return
        
        aggregated_df = (
            valid_orders
            .with_columns(pl.col("timestamp").dt.truncate("1h").alias("metric_timestamp"))
            .group_by("metric_timestamp")
            .agg([
                pl.col("payment_value").sum().alias("total_revenue")])
        )
        row_count = aggregated_df.height
        
        # assumption 2% conversion and injecting noise for realisitic ML Watchdog
        
        newdf = aggregated_df.with_columns([
            (pl.col("total_revenue") * np.random.uniform(0.8, 1.5, row_count)).cast(pl.Int32).alias("total_visitors"),
            (pl.col("total_revenue") * np.random.uniform(0.05, 0.15, row_count)).alias("total_marketing_spend")
        ])

        for row in newdf.to_dicts():
            existing = db.query(DailyMetric).filter(DailyMetric.timestamp == row["metric_timestamp"]).first()
            if existing:
                existing.revenue += row["total_revenue"]
                existing.website_visitors += row["total_visitors"]
                existing.marketing_spend += row["total_marketing_spend"]
            else:
                new_metric = DailyMetric(
                    timestamp=row["metric_timestamp"],
                    revenue=row["total_revenue"],
                    website_visitors=row["total_visitors"],
                    marketing_spend=row["total_marketing_spend"]
                )
                db.add(new_metric)

        processed_ids = df["id"].to_list()
        db.execute(update(RawIncomingEvent).where(RawIncomingEvent.id.in_(processed_ids)).values(is_processed=True))
        
        db.commit()
        print(f"[+] ETL Success: Saved {len(newdf)} hourly aggregations.")
    except Exception as e:
        db.rollback()
        print(f"[!] ETL Pipeline Failed: {e}")
    finally:
        db.close()