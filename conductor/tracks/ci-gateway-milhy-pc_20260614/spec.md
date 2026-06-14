# Specification: Milhy-PC CI Gateway

## Overview

Create a safe commit handoff workflow where the Raspberry Pi live repository never pushes directly to GitHub. Finished work is committed on the RPi, handed to Milhy-PC, validated there by CI/security checks, and only then pushed to GitHub.

## Goals

- Prevent accidental rollback or old-backup overwrites from reaching GitHub.
- Keep Milhy-PC as the validation gateway for commits from the live RPi tree.
- Produce clear failure reports when tests fail.
- Keep hardware-sensitive tests out of GitHub Actions while still running syntax/security checks in GitHub.

## Functional Requirements

- Provide `tools/run-ci.sh` for local, Milhy-PC, and GitHub-safe CI.
- Provide `tools/finish-track.sh` for safe commit handoff from RPi to Milhy-PC.
- Provide `tools/ci-agent.sh` for Milhy-PC to fetch from RPi, run CI, and push to GitHub only on success.
- Provide `tools/extract-webui-js.py` for embedded WebUI JavaScript syntax validation.
- Add GitHub Actions workflow for cloud-side checks.
- Store CI reports under `conductor/ci/reports/`.
- Never include BrowserOS passwords, cookies, or secrets in reports.

## Non-Goals

- No automatic production restarts.
- No automatic package installation on the RPi.
- No hardware-mutating tests by default.
- No direct GitHub push from RPi workflow.

## Acceptance Criteria

- [ ] `tools/run-ci.sh` runs Python syntax checks.
- [ ] `tools/run-ci.sh` extracts and checks embedded WebUI JavaScript when Node.js is available.
- [ ] `tools/run-ci.sh` writes Markdown CI reports.
- [ ] `tools/finish-track.sh` creates a safety stash checkpoint, runs CI, commits, and pushes only to Milhy-PC.
- [ ] `tools/ci-agent.sh` fetches RPi commits, runs CI, pushes to GitHub only on pass, and reports failures.
- [ ] GitHub Actions workflow runs project CI and uploads reports.
- [ ] Milhy-PC repository is synchronized with the RPi live state.
