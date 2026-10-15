#!/usr/bin/env python3
"""
tunnel_manager.py
Persistent Cloudflare Tunnel Manager with active keepalive ping and auto-restart watchdog.
Prevents Cloudflare idle reaping ("Unauthorized: Tunnel not found") by pinging /health every 20s.
Author: Nirmal Sharma
"""

import os
import re
import sys
import time
import json
import urllib.request
import subprocess
import threading

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLOUDFLARED = os.path.join(BASE_DIR, "cloudflared.exe")
STATIC_DIR = os.path.join(BASE_DIR, "src", "static")
URL_FILE = os.path.join(STATIC_DIR, "tunnel_url.txt")
INDEX_HTML = os.path.join(STATIC_DIR, "index.html")

def update_index_share_url(new_url):
    try:
        if not os.path.exists(INDEX_HTML):
            return
        with open(INDEX_HTML, "r", encoding="utf-8") as f:
            content = f.read()

        # Update apk-share-url input
        updated = re.sub(
            r'id="apk-share-url" value="https://[a-zA-Z0-9-]+\.trycloudflare\.com"',
            f'id="apk-share-url" value="{new_url}"',
            content
        )
        if updated != content:
            with open(INDEX_HTML, "w", encoding="utf-8") as f:
                f.write(updated)
            print(f"[Watchdog] Updated index.html share URL to: {new_url}", flush=True)
    except Exception as e:
        print(f"[Watchdog] Warning updating index.html: {e}", flush=True)

def keepalive_worker(url, stop_event):
    health_url = f"{url}/health"
    print(f"[KeepAlive] Started ping worker for {health_url}", flush=True)
    fail_count = 0
    while not stop_event.is_set():
        time.sleep(20)
        if stop_event.is_set():
            break
        try:
            req = urllib.request.Request(health_url, headers={"User-Agent": "SupportAI-KeepAlive/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status == 200:
                    fail_count = 0
                    # Ping ok
                else:
                    fail_count += 1
        except Exception as e:
            fail_count += 1
            print(f"[KeepAlive] Health ping failure ({fail_count}/3): {e}", flush=True)

        if fail_count >= 3:
            print("[KeepAlive] Tunnel failed 3 consecutive health checks! Triggering restart...", flush=True)
            stop_event.set()
            break

def run_tunnel():
    if not os.path.exists(CLOUDFLARED):
        print(f"Error: cloudflared.exe not found at {CLOUDFLARED}", flush=True)
        sys.exit(1)

    while True:
        print("\n" + "="*60, flush=True)
        print("[Watchdog] Starting cloudflared tunnel daemon...", flush=True)
        print("="*60, flush=True)

        proc = subprocess.Popen(
            [CLOUDFLARED, "tunnel", "--url", "http://127.0.0.1:8000"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )

        active_url = None
        stop_event = threading.Event()
        keepalive_thread = None

        url_regex = re.compile(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com")

        for line in proc.stdout:
            sys.stdout.write(line)
            sys.stdout.flush()

            if not active_url:
                match = url_regex.search(line)
                if match:
                    active_url = match.group(0)
                    print(f"\n>>> ACTIVE PUBLIC URL: {active_url} <<<\n", flush=True)
                    with open(URL_FILE, "w", encoding="utf-8") as uf:
                        uf.write(active_url)
                    update_index_share_url(active_url)

                    # Start keepalive thread
                    keepalive_thread = threading.Thread(target=keepalive_worker, args=(active_url, stop_event), daemon=True)
                    keepalive_thread.start()

            if "Unauthorized: Tunnel not found" in line or stop_event.is_set():
                print("[Watchdog] Tunnel expired or disconnected! Restarting...", flush=True)
                break

        stop_event.set()
        try:
            proc.terminate()
            proc.wait(timeout=5)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass

        time.sleep(2)

if __name__ == "__main__":
    run_tunnel()
