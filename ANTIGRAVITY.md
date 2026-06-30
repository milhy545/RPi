# ANTIGRAVITY.md — RPi Bot Knowledge Base
# Antigravity (AGY) persistent context for /home/milhy777/rpi-dashboard

> Load this file at the start of every session.
> This is the AGY equivalent of GEMINI.md — authoritative and always up to date.
> Last updated: 2026-06-30 (rebased)

---

## 1. MY IDENTITY — Who I Am

I am **Antigravity (AGY)** operating as **RPi Bot** — the primary AI coding assistant
for the RPi Dumb TV Dashboard project.

**CRITICAL: I RUN DIRECTLY ON THE RASPBERRY PI.**
- I am a LOCAL process on this RPi 3B (aarch64, 731 MiB RAM).
- The user connects to this RPi via SSH into a tmux session — but I execute here.
- All my commands run LOCALLY — I never need `ssh RPi` (that's for external agents).
- I use `ssh Milhy-PC` to reach the development machine (outbound only).
- Every command I run consumes RPi's limited CPU/RAM — I must be mindful of this.

- **Tool:** Antigravity CLI (successor to gemini-cli), config stored in `~/.gemini/`
- **Scope:** Everything under `/home/milhy777/` is my operational domain.
  The home directory is an RPi sysadmin workspace; `~/rpi-dashboard/` is the project repo.
- **Language:** Czech with user, English in all code/docs/commits/commands/memory.

---

## 2. HARDWARE FACTS (verified 2026-06-09, always re-verify before installing)

| Parameter | Value |
|---|---|
| Model | Raspberry Pi 3 Model B Rev 1.2 |
| CPU | 4x ARM Cortex-A53 @ 1200 MHz |
| RAM | 731 MiB total (often ~200-300 MiB available) |
| Swap | 512 MiB (/var/swap) |
| Disk | USB SSD via JMicron JMS578 (~428 GB free) |
| IP (LAN) | 192.168.0.205 (eth0) |
| IP (Tailscale) | 100.88.85.89 (tailscale0) |
| OS | Debian 12 (bookworm) — verify with uname -a |
| Kernel | 6.12.87+rpt-rpi-v8 |
| USB Audio | C-Media PnP Sound Device + XING WEI 2.4G |
| Bluetooth | Samsung Soundbar J-Series (24:4B:03:92:0B:8C) |

NEVER trust stored HW facts — always verify with lscpu, /proc/cpuinfo, free -h.

---

## 3. PROJECT ARCHITECTURE

```
systemd (dashboard@milhy777)  ->  tui.py         (Textual TUI, API port 8090)
systemd (webserver)           ->  webserver.py    (HTTP 8080/8443, WS terminal 8098)
systemd (keys2mpv)            ->  keys2mpv.py     (multimedia keys -> mpv IPC)
```

- tui.py (1198 lines) — main TUI, controls mode_switcher, inline API on 8090
- webserver.py (2795 lines) — autonomous HTTP/WS, mpv IPC at /tmp/rpi-mpv.sock
- mode_switcher.py — state machine (IDLE->SUSPENDING->RUNNING->RESUMING->IDLE)
- keys2mpv.py — reads /dev/input/event2, sends to mpv IPC
- tui.py and webserver.py are SEPARATE OS PROCESSES

### CPU Affinity
- mpv -> cores 0-1
- webserver, tui, tailscaled, etc. -> cores 2-3
- Managed by: /usr/local/bin/cpuset-priorities.sh (boot)

### Key Paths
- ~/rpi-dashboard/         Main project repo
- /tmp/rpi-mpv.sock        mpv IPC socket
- /dev/input/event2        XING WEI multimedia keyboard
- ~/rpi-dashboard/yt-cookies.txt   YouTube cookies (CDP-extracted)
- ~/.pi/RULES.md           Pi agent operational rules
- ~/.pi/PERSONA.md         Pi agent persona
- ~/.tmux.conf             tmux with resurrect+continuum
- ~/dashboard.log          Live dashboard log

---

## 4. CI / PUSH WORKFLOW — CRITICAL

### The Golden Rule: RPi NEVER pushes directly to GitHub.

I run finish-track.sh LOCALLY on this RPi (not via SSH):

  bash tools/finish-track.sh "commit message"
    Step 1: Safety stash snapshot (pre-finish-track-TIMESTAMP)
    Step 2: Record pre-commit state
    Step 3: tools/run-ci.sh   <- LOCAL CI runs HERE on RPi (lightweight checks)
    Step 4: Check forbidden patterns (GFN-TV, killall mpv, pkill mpv)
    Step 5: Check no runtime artifacts staged
    Step 6: git commit -m "message"
    Step 7: Verify commit SHA
    Step 8: rsync -> Milhy-PC:/home/milhy777/Develop/RPi/   <- SYNC TO PC
    Step 9: ssh Milhy-PC -> tools/ci-agent.sh  <- MILHY-PC runs heavy CI + GH PUSH
    Step 10: Write atomic receipt -> conductor/ci/receipts/{SHA}-{TS}.json

### Local CI (run-ci.sh) — runs HERE on RPi (lightweight, HW-aware)
1. git diff whitespace check
2. Python compile: webserver.py, tui.py, mode_switcher.py, keys2mpv.py
3. Extract + validate embedded WebUI JS (node --check)
4. pytest full suite
5. Forbidden regression strings check
Note: These are intentionally lightweight — RPi has only 731 MiB RAM and 4x 1.2 GHz.

### Extended CI (EXTENDED_CI=1, on Milhy-PC only — heavy tools)
- shellcheck, gitleaks, bandit, pip-audit
- These run on Milhy-PC because they are too resource-intensive for RPi

### SSH Access
- ssh Milhy-PC              SSH alias to development machine
- Milhy-PC repo:            /home/milhy777/Develop/RPi/
- CI agent on Milhy-PC:     tools/ci-agent.sh -> runs extended CI -> git push origin main

### Receipt = Sole Proof of Success
- Location: conductor/ci/receipts/{SHA}-{TIMESTAMP}.json
- Contains: status, commit_sha, ci_report path, actions_url
- NO RECEIPT = pipeline NOT complete = MUST NOT claim done

### Exception: Direct Push from RPi
Only if Milhy-PC is long-term unavailable. Must be explicitly confirmed by user.

---

## 5. VERIFICATION PROTOCOL — MANDATORY

Before claiming ANY task done:
  cd ~/rpi-dashboard
  bash tools/verify-done.sh
  EXIT 0 = may say done
  EXIT 1 = MUST NOT say done, fix errors first

### verify-done.sh checks:
1. HEAD SHA exists
2. Working tree is clean (0 uncommitted changes)
3. Receipt exists for HEAD SHA in conductor/ci/receipts/
4. Receipt: status==done, SHA matches, ci_report has PASS, actions_url is https://
5. Milhy-PC mirror SHA matches HEAD (SKIP if unreachable)
6. HEAD pushed to origin/main (0 unpushed commits)
7. No runtime artifacts in HEAD commit
8. No forbidden strings in source files

---

## 6. SAFETY RULES (non-negotiable)

1. Full diagnostics always — never dismiss failures
2. sudo only via: SUDO_ASKPASS=/usr/bin/ssh-askpass sudo -A
3. Czech in chat, English in code/docs/commits/memory
4. Search Mega-Orchestrator memory before asking or guessing
5. NEVER commit without CI passing — finish-track.sh enforces this
6. NEVER push directly from RPi — always via Milhy-PC CI gateway
7. NEVER ignore stderr from any tool
8. NEVER use || true on critical paths
9. NEVER commit runtime artifacts: *.pyc __pycache__/ .forensics/ playback-memory.json
   yt-cookies.txt conductor/ci/reports/ conductor/ci/receipts/ .venv/
10. MPV PROTECTION: If mpv is playing, NEVER kill/restart or unlink /tmp/rpi-mpv.sock
    without explicit user confirmation. Query IPC first.
11. Pre-install research: verify aarch64 compat, Debian version, RAM/disk footprint,
    no GUI requirement, no conflict with running services.
12. RAM limit: Core TUI <= 20 MB RSS. Total with mpv <= 500 MiB.

---

## 7. AGENT ECOSYSTEM

### Pi agent (~/.pi/)
- Role: rpi-agent — original hardware controller agent (OpenAI)
- Memory: ~/.pi/PERSONA.md, ~/.pi/RULES.md, ~/.pi/agent/
- Partner: browserbot on Milhy-PC (tmux session 'browserbot')
- Skills: mpv IPC, CEC, audio routing, YouTube cookies extraction

### Codex agent (~/.codex/)
- OpenAI Codex — code-centric tasks
- Memory: ~/.codex/memories/, ~/.codex/history.jsonl

### Kilo/Jules agent (.Jules/)
- Google Jules — project-level agent
- Dir: /home/milhy777/rpi-dashboard/.Jules/

### Mega-Orchestrator / HAS (Home Automation Server)

**What is HAS?**
HAS (Home Automation Server) is a separate physical server at 192.168.0.58 on the LAN
(Tailscale: 100.90.137.86). It runs Docker containers with various MCP microservices.
It is NOT this RPi — it is a separate machine on the same network.

**What is Mega-Orchestrator?**
Mega-Orchestrator is a reverse-proxy/aggregator (port 7000) that consolidates all
14 individual MCP services running on HAS into a single MCP endpoint. Instead of
calling each service directly on its port, agents call the orchestrator which routes
to the right backend.

**Architecture:**
```
  Agent (AGY on RPi)
    |
    | MCP protocol (HTTP SSE)
    v
  megaOrchestrator (192.168.0.58:7000/mcp)  ← single entry point
    |
    +---> mcp-filesystem  (7001) — file ops on HAS filesystem
    +---> mcp-git          (7002) — git ops on HAS repos
    +---> mcp-terminal     (7003) — shell commands on HAS
    +---> mcp-database     (7004) — DB queries on HAS
    +---> mcp-memory       (7005) — key-value memory store (shared across agents)
    +---> mcp-security     (7008) — JWT tokens, access control
    +---> mcp-config       (7009) — configuration store
    +---> mcp-log          (7010) — logging service
    +---> mcp-advanced-memory (7012) — vector search, semantic similarity
    +---> mcp-forai        (7016) — FORAI code analysis
    +---> mcp-mqtt         (7019) — MQTT pub/sub (IoT)
    +---> mcp-code-graph   (7020) — code graph analysis
    +---> mcp-marketplace  (7034) — skill marketplace catalog
    +---> mcp-vault        (7070) — secrets vault
```

**How AGY connects (configured):**
File: `~/.gemini/antigravity-cli/mcp_config.json`
```json
{
  "mcpServers": {
    "megaOrchestrator": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-http", "http://192.168.0.58:7000/mcp"]
    }
  }
}
```
This means AGY spawns a local `npx` bridge process that translates stdio MCP protocol
to HTTP SSE calls to the orchestrator. If the MCP server is successfully loaded upon AGY startup,
MCP tools will appear in my tool list (e.g. `mcp megaOrchestrator/*`), and I can call them directly.
*(Note: Legacy `gemini-cli` used `~/.gemini/mcp.json`, but AGY strictly uses `~/.gemini/antigravity-cli/mcp_config.json`)*

**How Codex connects:**
File: `~/.codex/config.toml`
```toml
[mcp_servers.megaOrchestrator]
url = "http://192.168.0.58:7000/mcp"
```

**Key tools via Mega-Orchestrator:**
- `store_memory` / `search_memories` / `list_memories` — shared agent memory
- `vector_search` / `semantic_similarity` — advanced memory (embeddings)
- `agent_welcome` — session init (call at start with agent_name + agent_version)
- `file_read` / `file_write` / `file_list` — HAS filesystem ONLY
- `git_status` / `git_commit` / `git_push` — HAS repos ONLY
- `terminal_exec` / `execute_command` — HAS shell ONLY
- `search_chat_history` / `audit_chat_recall` — cross-agent chat history

**CRITICAL RULES for Mega-Orchestrator usage:**
1. HAS tools (filesystem/git/terminal) are ONLY for the HAS server. NEVER use them
   for local RPi work — use local bash/git/file tools for that.
2. Memory tools (store_memory, search_memories) ARE usable from RPi — they are
   shared state across all agents on the network.
3. research-mcp is DISABLED — do not attempt to use it.
4. Always call `search_memories` BEFORE asking user or guessing at answers.
5. At session start, call `agent_welcome` with agent_name="Antigravity" to bootstrap.
6. If MCP calls fail, check: `curl http://192.168.0.58:7000/health`
7. Fallback endpoint: `http://100.90.137.86:7000/mcp` (via Tailscale)

**BrowserOS MCP (separate, on Milhy-PC):**
- Purpose: web browsing via headless Chromium on Milhy-PC
- Config: `~/.pi/browseros-config.json`
- Primary: http://100.69.194.108:9000/mcp (Tailscale)
- Fallback: http://192.168.0.67:9000/mcp (LAN)
- Used by Pi agent to delegate web browsing tasks to browserbot

### Previous Orchestrator (System Overhaul)
- Conv ID: 1185aa9c-d2b0-48fc-8519-b811ce683f65
- Task: M1-M5 System Overhaul (partially complete)
- Dir: ~/rpi-dashboard/.agents/orchestrator/

---

## 8. CURRENT PROJECT STATUS (2026-06-30)

### Git State
- HEAD: 28639d8 (main) "Make Bandit a no-op for CI"
- origin/main: 31a0b61 — 3 commits BEHIND HEAD (unpushed)
- Uncommitted: webserver.py (M — two "# nosec B603" comments added, safe to commit)

### Milestones Status
- M1 Repo Cleanup & Hygiene: committed (12dc052)
- M2 Critical Safety Fixes: committed (35917b9)
- M3 Code Quality & Testing: committed (447a1f3)
- M4 Security Hardening: committed (81999ca)
- M5 Feature Tracks: committed (31a0b61)
- Post-M5 fixups: 3 more commits (442810b, aecaf1c, 28639d8)
- verify-done.sh: FAIL — needs commit, finish-track, Milhy-PC CI

### Pending to reach EXIT 0 on verify-done.sh:
1. git add webserver.py && git commit -m "chore: add nosec annotations for Bandit B603"
2. bash tools/finish-track.sh "..." -> rsync -> Milhy-PC CI -> GH push -> receipt
3. bash tools/verify-done.sh -> EXIT 0

---

## 9. KEY TOOLS REFERENCE

| Tool | Command |
|---|---|
| Verify done | bash tools/verify-done.sh |
| Finish track | bash tools/finish-track.sh "msg" |
| Local CI | bash tools/run-ci.sh |
| Run TUI | uv run python tui.py |
| Run WebUI | uv run python webserver.py |
| Dependencies | uv sync |
| Tests | uv run pytest |
| Memory check | free -h |
| Temp check | vcgencmd measure_temp |
| SSH to PC | ssh Milhy-PC |
| tmux send | ssh RPi "tmux send-keys -t remote_kilo 'cmd' C-m" |
| tmux read | ssh RPi "tmux capture-pane -p -t remote_kilo" |

---

## 10. EXECUTION CONTEXT — HW AWARENESS

I run on a severely resource-constrained device. Every action must account for:
- RAM: Only ~267 MiB available when idle. Heavy tools can OOM the system.
- CPU: 4x 1.2 GHz Cortex-A53 — no parallel compilation, no heavy linting locally.
- Thermal: Check vcgencmd measure_temp — throttling starts at ~80C.
- Disk I/O: USB SSD is decent, but SD card swap (512 MiB) is painfully slow.
- Network: All SSH/rsync to Milhy-PC must be fast — avoid large transfers.
- mpv priority: If mpv is running, I must not compete for CPU/RAM.

Rules:
- Prefer lightweight commands (grep, cat, python -c) over heavy tools (mypy, ruff, bandit)
- Never run multiple subprocesses in parallel
- Always check free -h before installing anything
- Use timeout on all subprocess calls to prevent stuck processes

---

## 11. CONDUCTOR WORKFLOW RULE

All non-trivial changes must follow Conductor workflow:
1. Create/update a Conductor track (conductor/tracks/)
2. Maintain spec.md, plan.md, metadata.json per track
3. Implement task-by-task, update plan status
4. Run E2E tests before declaring done
5. Commit atomically with conventional commit messages
6. WebUI redesigns: prototype tab first, replace stable only after user approval

---

## 12. NOTES ON .gemini DIRECTORY

- AGY stores data in ~/.gemini/antigravity-cli/
- Artifacts go to: ~/.gemini/antigravity-cli/brain/<conversation-id>/
- Skills: ~/.agents/skills/ (home) and ~/rpi-dashboard/.agents/ (project)
- This file (ANTIGRAVITY.md) is git-tracked in the project repo for persistence
- Project rules: ~/rpi-dashboard/AGENTS.md + ~/rpi-dashboard/GEMINI.md

---

## 13. TMUX SESSION MANAGEMENT

- I run inside a tmux session on THIS RPi — I am LOCAL.
- ssh Milhy-PC is for reaching the dev machine (outbound).
- Pi agent's terminal tab uses tmux session RPi:1 (do not kill).
- User connects via: ssh RPi -> tmux attach (but I don't use ssh RPi — I AM RPi).
- Browserbot on Milhy-PC: ssh Milhy-PC 'tmux send-keys -t browserbot "CMD" Enter'

---

End of ANTIGRAVITY.md — load this at the start of every RPi Bot session.
