---
name: core-rules
description: "RPi-Specific Core Rules: RPi 3B (731MB RAM, Cortex-A53). Milhy-PC sole GitHub gateway. RPi NEVER push. Exact SHA binds evidence. Browsers forbidden on RPi. Guard exact playback processes (mpv/steamlink/moonlight/tui.py - NOT keys2mpv.py). CPU>20% gates. flock pipeline. Candidate worktree isolation. Atomic receipts required."
---

# Core Rules Enforcer — Raspberry Pi Host (RPi 3B)

## RPi-Specific Baseline Rules (Preserved from existing core-rules)

1. **Full diagnostics vždy** — Nikdy nezametať problémy pod koberec — vždy kompletná diagnostika
2. **SUDO_ASKPASS** — Vždy používat `SUDO_ASKPASS=/usr/bin/ssh-askpass sudo -A`
3. **Česky v chatu, Angličtina v kódu** — Komunikace s userem v češtině, veškerý kód, dokumenty, příkazy a memories v angličtině
4. **search_memories před otázkami** — Vždy prohledat Mega-Orchestrator memory + forai MCPs dříve než se zeptáš nebo hádáš
5. **Mega-Orchestrator** — Used for remote HAS operations. Remote HAS tools (filesystem/git/terminal-mcp) ONLY for HAS; research-mcp DISABLED. Local stdio fully allowed.

## Safe Validation Pipeline & Host Routing (CRITICAL — RPi-Specific)

### Host Gateway Routing
- **Milhy-PC is the sole GitHub push and merge gateway** — RPi host MUST NEVER execute `git push` or push code to remote repositories.

### Playback & User Workload Protection
- **Automated RPi candidate validation and hardware checks must NEVER kill, signal, restart, reroute, or disrupt**: active playback (`mpv`), gaming (`steamlink`, `moonlight`), TUI dashboard modes (`tui.py`), audio, Bluetooth, CEC, or system services.
- **Process Abort & Requeue**: If user playback or active mode starts during a candidate validation run, candidate/test processes must be terminated immediately without touching user playback, and the job requeued.

### Resource Constraints (RPi 3B Hardware-Specific)
- **Target hardware**: 4× Cortex-A53 CPU, **731 MB usable RAM**. Sustained user workload CPU >20%, low free RAM (<50 MB), or thermal limit (>75°C) gates candidate execution.
- **Browsers strictly forbidden on RPi**: Playwright, Chrome, Firefox, Chromium must never run on RPi host.

### Exact Process Matching
- **Authoritative playback/gaming**: Exact executable matches for `mpv`, `steamlink`, `moonlight`. TUI dashboard via `tui.py`.
- **Strict exclusion**: Helper scripts like `keys2mpv.py` must NEVER be misidentified as `mpv` (substring match is not authoritative).

### CPU Attribution & Self-Deadlock Prevention
- **User CPU >20%**: Sustained user workload CPU >20% triggers busy state.
- **Self-CPU exclusion**: CI runner/test process CPU is explicitly attributed and excluded from user CPU calculation to prevent self-deadlock.

### Candidate Staging & Worktree Isolation
- **Izolated worktree**: Candidate code is staged in isolated directories (`/home/milhy777/rpi-dashboard-candidate-<sha>`) outside live checkout.
- **Dirty checkout refusal**: Refuse staging if live checkout or target directory has uncommitted dirty changes. `rsync --delete` is forbidden over dirty checkouts.
- **Health-check and rollback**: Safe rollback on failure with cleanup.

### Exact Receipt Requirement
- **SHA binding**: Agents MUST NOT claim completion ("done", "hotovo", "finished") without an atomic receipt (`conductor/ci/receipts/{sha}-{timestamp}.json`) matching the exact commit SHA or Git tree hash.
- **Evidence invalidation**: Any subsequent code change invalidates previous validation receipts.

### Pipeline Locking
- **flock ownership**: Pipeline execution uses `flock` lock file (`/tmp/rpi-ci-pipeline.lock`) for exclusive ownership and concurrency control.

## Verification Protocol (RPi-Specific)

- Before each task: check system load, memory, thermal state.
- After each task: verify result (stdout AND stderr).
- Return only confirmed result with verification.

## System Resource Management (RPi-Specific)

- Check `free -h` before resource-intensive operations.
- Avoid launching memory-heavy processes if RAM is low.
- RPi runs serially with `flock`, low priority, bounded runtime.
