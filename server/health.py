import time
import threading
import requests
from flask import Flask, jsonify
from config import PORT, APP_URL, PING_INTERVAL
from utils.logger import log

app = Flask(__name__)

@app.route("/")
@app.route("/health")
def health_check():
    return jsonify({
        "status": "healthy",
        "service": "R2 Video Processor",
        "timestamp": int(time.time())
    }), 200

def _ping_worker():
    # Wait 20 seconds after server startup before firing the first ping
    time.sleep(20)
    while True:
        target_url = APP_URL.strip() if APP_URL else f"http://127.0.0.1:{PORT}/health"
        
        # Ensure url format
        if not target_url.startswith("http://") and not target_url.startswith("https://"):
            target_url = "https://" + target_url
            
        if not target_url.endswith("/health") and not target_url.endswith("/"):
            target_url = target_url + "/health"

        try:
            resp = requests.get(target_url, timeout=15)
            log(f"[Auto-Ping] Ping sent to '{target_url}' | HTTP Status: {resp.status_code}")
        except Exception as e:
            log(f"[Auto-Ping] Warning pinging '{target_url}': {e}")

        time.sleep(PING_INTERVAL)

def start_auto_ping():
    t = threading.Thread(target=_ping_worker, daemon=True, name="AutoPinger")
    t.start()
    log(f"Auto-ping keepalive thread started (Interval: {PING_INTERVAL // 60} minutes / {PING_INTERVAL}s).")

def run_health_server():
    start_auto_ping()
    app.run(host="0.0.0.0", port=PORT)
