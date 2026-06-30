#!/usr/bin/env python3
import os
import json
import glob
import time
import shutil

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORTS_DIR = os.path.join(ROOT_DIR, "reports")
PROCESSED_DIR = os.path.join(REPORTS_DIR, "processed")
TRACKS_DIR = os.path.join(ROOT_DIR, "conductor", "tracks")
TRACKS_MD = os.path.join(ROOT_DIR, "conductor", "tracks.md")

def process_reports():
    if not os.path.exists(REPORTS_DIR):
        return
    os.makedirs(PROCESSED_DIR, exist_ok=True)
    os.makedirs(TRACKS_DIR, exist_ok=True)

    report_files = glob.glob(os.path.join(REPORTS_DIR, "*.json"))
    for file_path in report_files:
        if "processed" in file_path:
            continue
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                report = json.load(f)

            rtype = report.get("type", "unknown")
            desc = report.get("description", "No description")
            ts = report.get("timestamp", int(time.time()))
            
            track_name = f"report_{ts}_{rtype}"
            track_dir = os.path.join(TRACKS_DIR, track_name)
            os.makedirs(track_dir, exist_ok=True)
            
            # Create spec.md
            spec_path = os.path.join(track_dir, "spec.md")
            with open(spec_path, "w", encoding="utf-8") as f:
                f.write(f"# User Report: {rtype.upper()}\n\n")
                f.write(f"**Timestamp:** {ts}\n")
                f.write(f"**Type:** {rtype}\n\n")
                f.write("## Description\n")
                f.write(f"{desc}\n")

            # Create plan.md
            plan_path = os.path.join(track_dir, "plan.md")
            with open(plan_path, "w", encoding="utf-8") as f:
                f.write(f"# Implementation Plan - {track_name}\n\n")
                f.write(f"## Goal\nInvestigate and resolve the user report.\n\n")
                f.write(f"Description: {desc}\n\n")
                f.write("## Tasks\n")
                f.write("| # | Description | Owner | Status |\n")
                f.write("|---|-------------|-------|--------|\n")
                f.write("| 1 | Investigate and resolve the report | agent | ⏳ Pending |\n")

            # Create metadata.json
            meta_path = os.path.join(track_dir, "metadata.json")
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump({"type": rtype, "timestamp": ts}, f)

            # Append to tracks.md
            if os.path.exists(TRACKS_MD):
                with open(TRACKS_MD, "a", encoding="utf-8") as f:
                    f.write(f"\n- [ ] **Track: {track_name}** — {rtype.capitalize()} report | [Plan](./tracks/{track_name}/plan.md)\n")

            # Move processed report
            shutil_dest = os.path.join(PROCESSED_DIR, os.path.basename(file_path))
            shutil.move(file_path, shutil_dest)
            print(f"Processed report {os.path.basename(file_path)} into {track_name}")

        except Exception as e:
            print(f"Failed to process {file_path}: {e}")

if __name__ == "__main__":
    process_reports()
