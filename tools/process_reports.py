#!/usr/bin/env python3
import os
import sys
import json
import time
import shutil
from datetime import datetime

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
REPORTS_DIR = os.path.join(BASE_DIR, "reports")
PROCESSED_DIR = os.path.join(REPORTS_DIR, "processed")
TRACKS_DIR = os.path.join(BASE_DIR, "conductor", "tracks")
TRACKS_MD = os.path.join(BASE_DIR, "conductor", "tracks.md")

def process_reports():
    os.makedirs(PROCESSED_DIR, exist_ok=True)
    
    if not os.path.exists(REPORTS_DIR):
        return
        
    for name in os.listdir(REPORTS_DIR):
        path = os.path.join(REPORTS_DIR, name)
        if not os.path.isfile(path) or not name.endswith(".json"):
            continue
            
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"Error reading report {name}: {e}", file=sys.stderr)
            continue
            
        rep_type = data.get("type", "bug")
        desc = data.get("description", "").strip()
        ts = data.get("timestamp", int(time.time()))
        
        if not desc:
            print(f"Empty description in {name}, skipping", file=sys.stderr)
            continue
            
        track_id = f"report_{ts}_{rep_type}"
        track_dir = os.path.join(TRACKS_DIR, track_id)
        os.makedirs(track_dir, exist_ok=True)
        
        # 1. Write metadata.json
        created_at = datetime.fromtimestamp(ts).strftime("%Y-%m-%dT%H:%M:%SZ")
        with open(os.path.join(track_dir, "metadata.json"), "w", encoding="utf-8") as f:
            json.dump({"status": "pending", "created_at": created_at}, f, indent=2)
            
        # 2. Write spec.md
        spec_content = f"""# User Submission Report

- **Type**: {rep_type}
- **Submitted At**: {created_at}
- **Client IP**: {data.get('client_ip', 'unknown')}

## Description
{desc}
"""
        with open(os.path.join(track_dir, "spec.md"), "w", encoding="utf-8") as f:
            f.write(spec_content)
            
        # 3. Write plan.md
        plan_content = f"""# Implementation Plan – {track_id}

## Goal
Investigate and resolve the user-submitted {rep_type} report.

## Tasks
- [ ] **1.0** Investigate and resolve the report: "{desc[:100]}"
"""
        with open(os.path.join(track_dir, "plan.md"), "w", encoding="utf-8") as f:
            f.write(plan_content)
            
        # 4. Append to conductor/tracks.md
        desc_summary = desc[:60].replace("\n", " ") + ("..." if len(desc) > 60 else "")
        track_entry = f"- [ ] **Track: {track_id}** — {rep_type.capitalize()} report: {desc_summary} | [Plan](./tracks/{track_id}/plan.md)\n"
        
        try:
            with open(TRACKS_MD, "r", encoding="utf-8") as f:
                tracks_content = f.read()
            if track_id not in tracks_content:
                with open(TRACKS_MD, "a", encoding="utf-8") as f:
                    f.write(track_entry)
        except Exception as e:
            print(f"Error updating tracks.md: {e}", file=sys.stderr)
            
        # 5. Move original report to processed/
        try:
            shutil.move(path, os.path.join(PROCESSED_DIR, name))
            print(f"Processed report {name} -> {track_id}")
        except Exception as e:
            print(f"Error moving report {name}: {e}", file=sys.stderr)

if __name__ == "__main__":
    process_reports()
