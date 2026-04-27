#!/bin/bash
cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
  echo "No .venv found — run: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt"
  exit 1
fi

echo "Starting Apple Podcasts Exporter at http://localhost:5001"
open "http://localhost:5001"
.venv/bin/python app.py
