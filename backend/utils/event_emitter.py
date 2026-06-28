import asyncio
import os
import httpx
import pandas as pd
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()   

SECURE_KEY = os.getenv("INGEST_API_KEY")

async def stream_data(file_path: str, target_url: str, delay_seconds: float, column_map: dict):
    print(f"[*] Starting Data Spigot. Streaming to {target_url}")
    try:
        df = pd.read_csv(file_path)
        df = df.dropna(subset=['payment_value', 'order_id', 'order_status'])            
    except FileNotFoundError:
        print("[!] No CSV found.")
        return

    headers = {"X-API-Key": SECURE_KEY}
    
    async with httpx.AsyncClient() as client:
        for index, row in df.iterrows():
            payload = {}
            for api_field, csv_column in column_map.items():
                val = row[csv_column]
                
                if pd.isna(val):
                    payload[api_field] = None
                elif api_field == "payment_value":
                    payload[api_field] = float(val) # Explicitly cast to float
                else:
                    payload[api_field] = str(val)
                
            payload["timestamp"] = datetime.now(timezone.utc).isoformat()
            
            try:
                response = await client.post(target_url, json=payload, headers=headers)
                
                if response.status_code != 200:
                    print(f"[!] 422 Data Contract Breach: {response.text}")
                else:
                    print(f"[Emit ->] Order {payload['order_id'][:8]}... | ${payload.get('payment_value')}")
                    
            except Exception as e:
                print(f"[!] Connection failed: {e}")
                
            await asyncio.sleep(delay_seconds)

if __name__ == "__main__":
    TARGET_API = "http://localhost:8080/ingest"
    CSV_FILE = "./public/data.csv" 
    
    olist_mapping = {
        "order_id": "order_id",
        "order_status": "order_status",
        "payment_value": "payment_value"
    }
    try:
        asyncio.run(stream_data(CSV_FILE, TARGET_API, 1.5, olist_mapping))
    except KeyboardInterrupt:
        print("\n[*] Spigot manually closed.")