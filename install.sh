#!/bin/bash
# SAMSAMCO JARVIS AI — Install Script
# Installs all HTML pages and server routes to /root/ai-browser on CT108

set -e
DEST="/root/ai-browser"

echo "[1/3] Copying HTML pages..."
cp -f public/*.html "$DEST/"
echo "[2/3] Copying JS..."
cp -f public/*.js "$DEST/" 2>/dev/null || true
echo "[3/3] Injecting /links route into server.py..."
python3 inject_routes.py
echo "Done — restart jarvis-agent: systemctl restart jarvis-agent"
