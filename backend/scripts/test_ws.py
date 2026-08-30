import asyncio
import websockets
import httpx
import json
import threading
import time

def trigger_batch():
    time.sleep(1) # wait for WS to connect
    print("Triggering /api/run-batch...")
    r = httpx.post("http://localhost:8000/api/run-batch")
    print(r.json())

async def listen_ws():
    uri = "ws://localhost:8000/ws/live"
    try:
        async with websockets.connect(uri) as ws:
            print("Connected to WS.")
            threading.Thread(target=trigger_batch, daemon=True).start()
            
            while True:
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=20.0)
                    data = json.loads(msg)
                    print(f"WS Event: {data['type']} | TX {data['transaction_id']}")
                except asyncio.TimeoutError:
                    print("Timeout waiting for events. Batch probably finished.")
                    break
    except Exception as e:
        print("WS Error:", e)

asyncio.run(listen_ws())
