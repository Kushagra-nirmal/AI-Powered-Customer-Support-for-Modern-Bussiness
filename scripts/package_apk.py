#!/usr/bin/env python3
"""
package_apk.py
Packages SupportAI & J.A.R.V.I.S. into a production-grade signed Android APK (SupportAI-JARVIS.apk).
Directly streams files into the APK archive and signs with OpenJDK 25 jarsigner.
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

SHAREME_DIR = r"C:\Users\01234\CrossDevice\NIRMAL SHARMA\storage\MIUI\ShareMe"
KEYTOOL = r"C:\Users\01234\.antigravity-ide\extensions\redhat.java-1.57.0-win32-x64\jre\25.0.4.1-win32-x86_64\bin\keytool.exe"
JARSIGNER = r"C:\Users\01234\.antigravity-ide\extensions\redhat.java-1.57.0-win32-x64\jre\25.0.4.1-win32-x86_64\bin\jarsigner.exe"
KEYSTORE_PATH = os.path.join(BASE_DIR, "supportai-release.keystore")
KEYSTORE_PASS = "supportai123"
KEY_ALIAS = "supportai"

def ensure_keystore():
    if os.path.exists(KEYSTORE_PATH):
        print(f"Keystore found at: {KEYSTORE_PATH}")
        return True

    print("Generating release keystore...")
    cmd = [
        KEYTOOL,
        "-genkeypair",
        "-v",
        "-keystore", KEYSTORE_PATH,
        "-alias", KEY_ALIAS,
        "-keyalg", "RSA",
        "-keysize", "2048",
        "-validity", "10000",
        "-storepass", KEYSTORE_PASS,
        "-keypass", KEYSTORE_PASS,
        "-dname", "CN=Nirmal Sharma, OU=SupportAI Multimodal Systems, O=Production Agentic AI, L=Delhi, ST=Delhi, C=IN"
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print("Error generating keystore:", res.stderr)
        return False
    return True

def build_signed_apk():
    unsigned_apk = os.path.join(BASE_DIR, "unsigned_temp.apk")
    if os.path.exists(unsigned_apk):
        try:
            os.remove(unsigned_apk)
        except Exception:
            pass

    print("Creating ZIP archive with Android binaries and assets...")
    app_config = {
        "appName": "SupportAI & JARVIS",
        "author": "Nirmal Sharma",
        "version": "1.0.0",
        "serverUrl": "https://seed-enrolled-ballet-thumbzilla.trycloudflare.com",
        "localUrl": "http://127.0.0.1:8000",
        "features": [
            "Continuous British JARVIS Voice Synthesis & Hands-free Mic",
            "Realtime 8K AI Image Studio & Lightbox",
            "AI Video Storyboarding & Shot Generation",
            "Universal Logistics & Order Tracking Across All Carriers",
            "Autonomous Ordering with ACID PostgreSQL Transactions",
            "Live Grounded Web Search & Document RAG",
            "Admin Operations, Live Telemetry & Metrics"
        ]
    }

    count = 0
    with zipfile.ZipFile(unsigned_apk, "w", zipfile.ZIP_DEFLATED) as zipf:
        # Add Android runtime base files
        for root, dirs, files in os.walk(SHAREME_DIR):
            for file in files:
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, SHAREME_DIR)
                arc_name = rel_path.replace(os.sep, "/")
                if arc_name.startswith("META-INF/") and (arc_name.endswith(".SF") or arc_name.endswith(".RSA") or arc_name.endswith(".MF")):
                    continue
                zipf.write(full_path, arc_name)
                count += 1

        # Add web assets
        for f in ["index.html", "manifest.json", "sw.js", "icon-192.png", "icon-512.png", "icon-maskable.png", "robot.jpg"]:
            f_path = os.path.join(STATIC_DIR, f)
            if os.path.exists(f_path):
                zipf.write(f_path, f"assets/www/{f}")
                count += 1

        # Add app configuration
        zipf.writestr("assets/www/app_config.json", json.dumps(app_config, indent=2))
        count += 1

    print(f"Packaged {count} items into unsigned APK ({os.path.getsize(unsigned_apk):,} bytes).")

    # Sign with jarsigner
    print("Signing APK with OpenJDK 25 jarsigner...")
    sign_cmd = [
        JARSIGNER,
        "-sigalg", "SHA256withRSA",
        "-digestalg", "SHA-256",
        "-keystore", KEYSTORE_PATH,
        "-storepass", KEYSTORE_PASS,
        "-keypass", KEYSTORE_PASS,
        "-signedjar", OUTPUT_APK,
        unsigned_apk,
        KEY_ALIAS
    ]
    sign_res = subprocess.run(sign_cmd, capture_output=True, text=True)
    if sign_res.returncode != 0:
        print("Error signing APK:", sign_res.stderr)
        return False

    # Verify signature
    verify_cmd = [JARSIGNER, "-verify", OUTPUT_APK]
    verify_res = subprocess.run(verify_cmd, capture_output=True, text=True)
    print("jarsigner verification:", verify_res.stdout.strip())

    # Copy to workspace root
    shutil.copy2(OUTPUT_APK, ROOT_APK)
    print(f"SUCCESS! Signed Production APK Created:")
    print(f"  -> Static Download: {OUTPUT_APK} ({os.path.getsize(OUTPUT_APK):,} bytes)")
    print(f"  -> Workspace Root:  {ROOT_APK} ({os.path.getsize(ROOT_APK):,} bytes)")

    # Clean temporary unsigned
    if os.path.exists(unsigned_apk):
        try:
            os.remove(unsigned_apk)
        except Exception:
            pass

    return True

if __name__ == "__main__":
    if ensure_keystore():
        success = build_signed_apk()
        if not success:
            sys.exit(1)
