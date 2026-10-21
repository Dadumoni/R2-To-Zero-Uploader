import time

def log(msg: str):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)
