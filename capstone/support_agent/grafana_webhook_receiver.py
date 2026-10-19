from fastapi import FastAPI, Request
from datetime import datetime, timezone
import json

app = FastAPI(title="Grafana Alert Webhook Receiver")


@app.post("/grafana-alert")
async def receive_grafana_alert(request: Request):
    payload = await request.json()

    print("\n=== GRAFANA ALERT RECEIVED ===", flush=True)
    print("Time:", datetime.now(timezone.utc).isoformat(), flush=True)
    print(json.dumps(payload, indent=2), flush=True)

    return {"status": "received"}

# poetry run uvicorn grafana_webhook_receiver:app --host 127.0.0.1 --port 8001
