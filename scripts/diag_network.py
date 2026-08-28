"""Diagnóstico de red Railway -> Alpaca: aísla si el problema es DNS, TCP,
o el propio cliente HTTP del SDK/CLI, para depurar el cuelgue de
client.get_account() visto en live_agent.py corriendo en Railway."""

import os
import socket
import subprocess
import sys
import time

print("=== diag_network arrancando ===", flush=True)

for host in ["paper-api.alpaca.markets", "data.alpaca.markets", "8.8.8.8"]:
    t0 = time.time()
    try:
        if host == "8.8.8.8":
            print(f"[skip DNS] {host}", flush=True)
            continue
        ip = socket.gethostbyname(host)
        print(f"[DNS OK] {host} -> {ip} ({time.time()-t0:.2f}s)", flush=True)
    except Exception as e:
        print(f"[DNS FAIL] {host}: {e} ({time.time()-t0:.2f}s)", flush=True)

for host, port in [("paper-api.alpaca.markets", 443), ("data.alpaca.markets", 443)]:
    t0 = time.time()
    try:
        s = socket.create_connection((host, port), timeout=10)
        s.close()
        print(f"[TCP OK] {host}:{port} ({time.time()-t0:.2f}s)", flush=True)
    except Exception as e:
        print(f"[TCP FAIL] {host}:{port}: {e} ({time.time()-t0:.2f}s)", flush=True)

print("=== probando alpaca CLI (account get) ===", flush=True)
t0 = time.time()
try:
    r = subprocess.run(["alpaca", "account", "get"], capture_output=True, text=True, timeout=20)
    print(f"[CLI] rc={r.returncode} ({time.time()-t0:.2f}s) stdout[:200]={r.stdout[:200]!r} stderr[:200]={r.stderr[:200]!r}", flush=True)
except subprocess.TimeoutExpired:
    print(f"[CLI TIMEOUT] tras 20s ({time.time()-t0:.2f}s)", flush=True)
except Exception as e:
    print(f"[CLI FAIL] {e} ({time.time()-t0:.2f}s)", flush=True)

print("=== probando alpaca-py SDK (requests con timeout via env) ===", flush=True)
t0 = time.time()
try:
    import requests
    resp = requests.get(
        "https://paper-api.alpaca.markets/v2/account",
        headers={
            "APCA-API-KEY-ID": os.getenv("ALPACA_API_KEY", ""),
            "APCA-API-SECRET-KEY": os.getenv("ALPACA_SECRET_KEY", ""),
        },
        timeout=15,
    )
    print(f"[requests OK] status={resp.status_code} ({time.time()-t0:.2f}s) body[:200]={resp.text[:200]!r}", flush=True)
except Exception as e:
    print(f"[requests FAIL] {type(e).__name__}: {e} ({time.time()-t0:.2f}s)", flush=True)

print("=== probando TradingClient del SDK (alpaca-py, sin timeout explicito) ===", flush=True)
t0 = time.time()
try:
    from alpaca.trading.client import TradingClient
    client = TradingClient(os.getenv("ALPACA_API_KEY", ""), os.getenv("ALPACA_SECRET_KEY", ""), paper=True)
    cuenta = client.get_account()
    print(f"[SDK OK] id={cuenta.id} ({time.time()-t0:.2f}s)", flush=True)
except Exception as e:
    print(f"[SDK FAIL] {type(e).__name__}: {e} ({time.time()-t0:.2f}s)", flush=True)

print("=== diag_network termino ===", flush=True)
