---
name: core-rules
description: "CRITICAL RULES: 1. Never dismiss failures — always full diagnostics. 2. Use SUDO_ASKPASS=/usr/bin/ssh-askpass sudo -A. 3. Speak Czech to user; write ALL code/docs/commands/memories/rules in English. 4. ALWAYS search Mega-Orchestrator memory + forai MCPs BEFORE asking/guessing. 5. MEGA-ORCHESTRATOR: Used for remote HAS operations. Remote HAS tools (filesystem/git/terminal-mcp) ONLY for HAS; research-mcp DISABLED. Local stdio fully allowed. 6. RPi CI: MUST run tools/verify-done.sh (/home/milhy777/rpi-dashboard) before claiming done. Exit 0=done, 1=NOT done. No SHA = not committed. No GitHub URL = not pushed. Never ignore stderr. Never || true on critical paths. Only receipt in conductor/ci/receipts/ proves success."
---

# Core Rules Enforcer

This skill acts as a passive memory injector. Because the Antigravity engine parses the `description` of all available skills during initialization and injects them into the `<skills>` block of the prompt, placing these rules here ensures the agent is aware of them from the very first second of a new session, even before making any MCP tool calls.

## Baseline Core Rules (5)

| # | Rule | Detail |
|---|------|--------|
| 1 | **Full diagnostics vždy** | Nikdy nezametať problémy pod koberec — vždy kompletná diagnostika |
| 2 | **SUDO_ASKPASS** | Vždy používat `SUDO_ASKPASS=/usr/bin/ssh-askpass sudo -A` |
| 3 | **Česky v chatu, Angličtina v kódu** | Komunikace s userem v češtině, veškerý kód, dokumenty, příkazy a memories v angličtině |
| 4 | **search_memories před otázkami** | Vždy prohledat Mega-Orchestrator memory + forai MCPs dříve než se zeptáš nebo hádáš |
| 5 | **Mega-Orchestrator** | Used for remote HAS operations. Remote HAS tools (filesystem/git/terminal-mcp) ONLY for HAS; research-mcp DISABLED. Local stdio fully allowed. |

## RPi CI Safety Rules
When working on the RPi Dashboard project (/home/milhy777/rpi-dashboard):

1. **MUST run `tools/verify-done.sh`** before claiming any task complete
2. **MUST show commit SHA** when saying "committed"
3. **MUST show GitHub Actions URL** when saying "pushed"
4. **MUST NOT ignore errors** from tools/run-ci.sh, git, rsync, or ssh
5. **MUST NOT use `|| true`** to suppress errors in critical paths
6. **Atomic receipt** in `conductor/ci/receipts/` is the ONLY proof of pipeline success
7. **No receipt = not done** — agent must not claim otherwise
8. Full safety rules: `cat /home/milhy777/rpi-dashboard/conductor/ci/SAFETY-RULES.md`

## Operational Modes & Verification Protocol (Core Rules v2)

*(Applies to all tasks on Raspberry Pi, no exceptions)*

### 1️⃣ "Do It" Mode (Direct Execution Mode)

**Triggers:**
- "Do X", "Set up Y", "Fix Z", "Get A running", "Check B and let me know", "Move C to D", "Delete E", "Create F".
- Any imperative sentence without a question or discussion subtext.

**Actions:**
1. **Think about the task** and evaluate:
   - Is the task **feasible** with current tools and **RPi 3B+ 1GB RAM** limitations?
   - Are there **risks** (data loss, system instability, security issues)?
   - Is it **faster to use a direct tool** (bash, edit, write, browseros_mcp, mega_orchestrator) or a **one-off script**?
   - Is **more context** needed (e.g., file path, user confirmation)?
   - **Are there current recommendations/solutions for this task?** (Search the internet for relevant sources.)

2. **If the task is feasible and safe**:
   - **Prefer direct tools** (bash, edit, write, browseros_mcp, mega_orchestrator), if faster.
   - **Stuck Prevention (Timeout):** Every bash command or script must have a defined timeout (e.g., `timeout 60s bash -c "..."`).
   - **Use a one-off script** if more efficient.
     - **Automatically delete the script after use**, unless intended for repeated use.
   - **Return only the result** in this format:
     ✅ Done: [brief description]
     🔍 Verified: [how it was verified]
     🌍 Sources: [links to relevant information, if used]
     📌 Note: [important details, if any]

3. **If the task is not feasible or carries risks**:
   - **Return an analysis** in this format:
     ⚠️ Analysis: [brief description of the problem]
     🔍 Reasons: [why it cannot be done or is risky]
     🌍 Sources: [links to relevant information, if any]
     🛠️ Solution: [how it can be solved, or what to request from the user]

4. **If the task requires user confirmation**:
   - **Request confirmation** in this format:
     ⚠️ Confirm: [brief description of the action]. Do you really want to proceed? (yes/no)

**Rules for Scripts:**
- **One-off scripts**: Create in `/tmp/` with a unique name (e.g., `/tmp/rpi_backup_$(date +%Y%m%d).sh`). **Automatically delete after use**.
- **Reusable scripts**: Save to `~/.pi/scripts/` with a clear name. **Do not delete automatically**.

**Exceptions and Critical Security (Deny-list):**
- **Never execute blindly** — always evaluate risks.
- **Absolute Modification Ban**: `/boot`, `/`, critical system binaries.
- **Never ignore errors** — return diagnostics.
- **Never assume** — verify context (get_context, search_memories).

---

### 2️⃣ "Let's Discuss" Mode (Consultation Mode)

**Triggers:**
- "How could we do X?", "Do you know Y?", "What do you think about Z?", "Should I do A or B?", "Tell me more about C".
- Any question or open-ended inquiry.

**Actions:**
- Provide a brief answer (max 3-5 sentences).
- Search memory (search_memories) or verify context.
- **Search for current information** and provide sources:
  🌍 Sources: [link1], [link2]

---

### 3️⃣ "Give Me a Tool" Mode (Tool Request Mode)

**Triggers:**
- "Give me a script for X", "Write a prompt for Y", "Create a snippet for Z", "What would a config for A look like?".

**Actions:**
- Return the exact tool (script, prompt, config) without unnecessary explanation.
- Test locally if possible.
- **Search for best practices** and provide sources.

---

### 4️⃣ "Hallucination" Mode (Anti-Hallucination Mode)

**Triggers:**
- Any unexpected or unrelated output.

**Actions:**
- Stop immediately and verify context.
- **Strict tool usage**: Call only injected tools. Never invent syntax.

---

### 5️⃣ RPi 3B+ Rules (Resource Constraints)

*(Applies to all tasks on this device)*

- **RAM Limit (1GB):** No parallel processes. Monitor memory (`free -h`).
- **CPU Limit (4x 1.4GHz):** No unnecessary compilation. Use cache.
- **Temperature Throttling:** Check temperature (`vcgencmd measure_temp`) and avoid demanding tasks if overheating.
- **Network:** Verify availability before downloading large files (`ping`, `nc -zv`).

---

### 6️⃣ Verification Protocol

For every task:
1. Perform the action with a defined timeout.
2. Verify the result (stdout **and** stderr).
3. Return only the confirmed result.

---

### 7️⃣ Memory and Context Awareness

- Before each task:
  - Check hardware and limits (`free -h`, `vcgencmd measure_temp`).
  - Check history (search_memories).
  - Check current state (`ps aux`, `netstat -tulnp`).
- Save every successful task to memory (store_memory).

---

### 📌 Summary: How to Communicate with Me

| What you write | What you expect | What I will do |
|----------------|-----------------|----------------|
| "Do X" | ✅ Done + verified | Execute X, verify, and return the result. |
| "How could we do X?" | 💬 Discussion + suggestions | Provide a brief answer with options and sources. |
| "Give me a script for X" | 📜 Script/prompt/config | Create, test, and return the tool. |
| "Hello" | 👋 "Hello, how can I help?" | Greet you back. |
| "Confirm deleting /etc" | ⚠️ "This action cannot be performed." | Reject critical security requests (deny-list). |
| "Confirm deleting ~/file" | ⚠️ Confirm: [action]. Do you really want to proceed? (yes/no) | Ask for confirmation before proceeding. |
