# Core Rules local copy
Loaded from: /home/milhy777/.agents/skills/core-rules/SKILL.md

CRITICAL RULES:
1. Never dismiss failures — always full diagnostics.
2. Use SUDO_ASKPASS=/usr/bin/ssh-askpass sudo -A.
3. Speak Czech to user; write ALL code/docs/commands/memories/rules in English.
4. ALWAYS search Mega-Orchestrator memory + forai MCPs BEFORE asking/guessing.
5. MEGA-ORCHESTRATOR: Used for remote HAS operations. Remote HAS tools (filesystem/git/terminal-mcp) ONLY for HAS; research-mcp DISABLED. Local stdio fully allowed.
6. RPi CI: MUST run tools/verify-done.sh (/home/milhy777/rpi-dashboard) before claiming done. Exit 0=done, 1=NOT done. No SHA = not committed. No GitHub URL = not pushed. Never ignore stderr. Never || true on critical paths. Only receipt in conductor/ci/receipts/ proves success.
