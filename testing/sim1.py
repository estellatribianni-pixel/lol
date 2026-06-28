import requests
import time
import random
import argparse
from datetime import datetime, timezone

API_URL = "http://localhost:8080/ingest"

def simulate_traffic(interval: float, anomaly_rate: int):
    print(f"[*] Starting Traffic Simulator...")
    print(f"[*] Firing every {interval} seconds.")
    print(f"[*] Injecting a massive anomaly every {anomaly_rate} requests.\n")
    
    count = 0
    # THIS HEADER MATCHES YOUR .ENV FILE
    headers = {
        "X-API-Key": "super_secret_test_key"
    }
    
    try:
        while True:
            count += 1
            is_anomaly = (count % anomaly_rate == 0)
            
            payment_val = random.uniform(5000, 15000) if is_anomaly else random.uniform(15, 120)
            payment_val = round(payment_val, 2)
            
            payload = {
                "order_id": f"TEST_{int(time.time())}_{count}",
                "order_status": "delivered",
                "payment_value": payment_val,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            try:
                # WE PASS THE HEADERS HERE TO BYPASS THE 403 ERROR
                res = requests.post(API_URL, json=payload, headers=headers)
                
                if res.status_code == 200:
                    status = "🚨 ANOMALY INJECTED" if is_anomaly else "✅ Normal Tick"
                    print(f"{status} | ID: {payload['order_id']} | Value: ${payment_val}")
                else:
                    print(f"[!] Server Error: {res.status_code} - {res.text}")
            except requests.exceptions.ConnectionError:
                print("[!] Connection failed. Is the Docker API Gateway running on port 8080?")
                
            time.sleep(interval)
            
    except KeyboardInterrupt:
        print("\n[*] Simulator halted by user.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="BizIntel Traffic Simulator")
    parser.add_argument("--interval", type=float, default=2.0, help="Seconds between requests")
    parser.add_argument("--anomaly-rate", type=int, default=15, help="Inject anomaly every X requests")
    
    args = parser.parse_args()
    simulate_traffic(args.interval, args.anomaly_rate)