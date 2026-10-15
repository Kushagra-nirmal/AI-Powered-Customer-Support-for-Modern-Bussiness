#!/usr/bin/env python3
"""
finalize_apk.py
Cleanly repackages SupportAI-JARVIS.apk without duplicates, updates web assets and config,
and signs with OpenJDK 25 jarsigner.
Author: Nirmal Sharma
"""

import os
import shutil
import subprocess
import zipfile
import json
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = os.path.join(BASE_DIR, "src", "static")
OUTPUT_APK = os.path.join(STATIC_DIR, "SupportAI-JARVIS.apk")
ROOT_APK = os.path.join(BASE_DIR, "SupportAI-JARVIS.apk")

JARSIGNER = r"C:\Users\01234\.antigravity-ide\extensions\redhat.java-1.57.0-win32-x64\jre\25.0.4.1-win32-x86_64\bin\jarsigner.exe"
KEYSTORE_PATH = os.path.join(BASE_DIR, "supportai-release.keystore")
KEYSTORE_PASS = "supportai123"
KEY_ALIAS = "supportai"

def finalize():
    temp_apk = os.path.join(BASE_DIR, "supportai_clean_staging.apk")
    if os.path.exists(temp_apk):
        try:
            os.remove(temp_apk)
        except Exception:
            pass

    app_config = {
        "appName": "SupportAI & JARVIS",
        "creator": "Nirmal Sharma",
        "version": "1.0.0",
        "package": "com.supportai.jarvis",
        "serverUrl": "https://upper-closure-affecting-ink.trycloudflare.com",
        "localUrl": "http://127.0.0.1:8000",
        "lanUrl": "http://192.168.1.20:8000",
        "capabilities": [
            "Continuous British JARVIS Voice Conversation",
            "Realtime 8K AI Image Studio",
            "AI Video Storyboarding",
            "Universal Logistics & Order Tracking",
            "Autonomous Food & Retail Ordering with PostgreSQL Transactions",
            "Grounded Live Web Search & Knowledge Ingestion",
            "Admin Operations, Live Telemetry & Metrics"
        ]
    }

    print("Rebuilding clean APK archive from existing APK binaries...")
    with zipfile.ZipFile(ROOT_APK, "r") as zin:
        with zipfile.ZipFile(temp_apk, "w", zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                # Skip duplicate web assets and old META-INF signatures
                if item.filename.startswith("assets/www/") or item.filename.startswith("META-INF/"):
                    continue
                zout.writestr(item, zin.read(item.filename))

            # Add fresh web files
            web_files = [
                "index.html",
                "manifest.json",
                "sw.js",
                "icon-192.png",
                "icon-512.png",
                "icon-maskable.png",
                "robot.jpg"
            ]
            for f in web_files:
                fp = os.path.join(STATIC_DIR, f)
                if os.path.exists(fp):
                    zout.write(fp, f"assets/www/{f}")
                    print(f" - Added assets/www/{f}")

            zout.writestr("assets/www/app_config.json", json.dumps(app_config, indent=2))
            print(" - Added assets/www/app_config.json")

    print(f"Clean staging APK created ({os.path.getsize(temp_apk):,} bytes).")

    print("Signing APK with OpenJDK 25 jarsigner...")
    sign_cmd = [
        JARSIGNER,
        "-sigalg", "SHA256withRSA",
        "-digestalg", "SHA-256",
        "-keystore", KEYSTORE_PATH,
        "-storepass", KEYSTORE_PASS,
        "-keypass", KEYSTORE_PASS,
        "-signedjar", OUTPUT_APK,
        temp_apk,
        KEY_ALIAS
    ]
    sign_res = subprocess.run(sign_cmd, capture_output=True, text=True)
    if sign_res.returncode != 0:
        print("Error during jarsigner signing:", sign_res.stderr)
        sys.exit(1)

    print("Verifying signed APK...")
    verify_cmd = [JARSIGNER, "-verify", OUTPUT_APK]
    verify_res = subprocess.run(verify_cmd, capture_output=True, text=True)
    print("jarsigner verification result:", verify_res.stdout.strip())

    shutil.copy2(OUTPUT_APK, ROOT_APK)
    print("\n" + "="*60)
    print("SUCCESSFULLY MERGED & SIGNED FULL ANDROID APK:")
    print(f"  -> Static Download: {OUTPUT_APK} ({os.path.getsize(OUTPUT_APK):,} bytes)")
    print(f"  -> Workspace Root:  {ROOT_APK} ({os.path.getsize(ROOT_APK):,} bytes)")
    print("="*60)

    if os.path.exists(temp_apk):
        try:
            os.remove(temp_apk)
        except Exception:
            pass

if __name__ == "__main__":
    finalize()
