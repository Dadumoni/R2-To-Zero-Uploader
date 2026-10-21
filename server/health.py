from flask import Flask, jsonify
from config import PORT

app = Flask(__name__)

@app.route("/")
@app.route("/health")
def health_check():
    return jsonify({"status": "healthy", "service": "R2 Video Processor"}), 200

def run_health_server():
    app.run(host="0.0.0.0", port=PORT)
