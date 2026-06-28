# BRIEFING — 2026-06-28T10:21:00Z

## Mission
Perform a comprehensive System Overhaul of the RPi Dumb TV Dashboard, covering repo hygiene, critical safety fixes, code quality improvements, security hardening, and three open feature tracks.

## 🔒 My Identity
- Archetype: orchestrator
- Roles: orchestrator, user_liaison, human_reporter, successor
- Working directory: /home/milhy777/rpi-dashboard/.agents/orchestrator
- Original parent: parent
- Original parent conversation ID: 9fc7b065-76b2-4cf3-bd1b-e6afd575c5de

## 🔒 My Workflow
- **Pattern**: Project
- **Scope document**: /home/milhy777/rpi-dashboard/.agents/orchestrator/PROJECT.md
1. **Decompose**: Decompose the project overhaul into logical milestones based on requirements R1 to R5.
2. **Dispatch & Execute**:
   - **Delegate (sub-orchestrator)**: For large milestones, spawn sub-orchestrators/workers.
3. **On failure** (in this order):
   - Retry: nudge stuck agent or re-send task
   - Replace: spawn fresh agent with partial progress
   - Skip: proceed without (only if non-critical)
   - Redistribute: split stuck agent's remaining work
   - Redesign: re-partition decomposition
   - Escalate: report to parent (sub-orchestrators only, last resort)
4. **Succession**: Spawn successor when spawn count reaches 16 and all subagents are complete.
- **Work items**:
  1. Repo Cleanup & Hygiene (R1) [in-progress]
  2. Critical Safety Fixes (R2) [pending]
  3. Code Quality & Testing (R3) [pending]
  4. Security Hardening (R4) [pending]
  5. Open Feature Tracks (R5) [pending]
- **Current phase**: 1
- **Current focus**: Milestone 1 Implementation

## 🔒 Key Constraints
- TUI RSS ≤ 20 MB after startup.
- Run tools/verify-done.sh to ensure all criteria are met before claiming success.
- Never write code directly; delegate all work to subagents.

## Current Parent
- Conversation ID: 9fc7b065-76b2-4cf3-bd1b-e6afd575c5de
- Updated: not yet

## Key Decisions Made
- Decompose overhaul into 5 milestones aligned with requirements R1-R5.

## Team Roster
| Agent | Type | Work Item | Status | Conv ID |
|-------|------|-----------|--------|---------|
| explorer_m1 | teamwork_preview_explorer | Milestone 1 Exploration | completed | 105d4407-3f11-4e09-a6b7-fe5f91b7377e |
| worker_m1   | teamwork_preview_worker   | Milestone 1 Implementation | in-progress | c3eaab12-3bcc-4821-9d3e-478182c3d2b8 |

## Succession Status
- Succession required: no
- Spawn count: 2 / 16
- Pending subagents: c3eaab12-3bcc-4821-9d3e-478182c3d2b8
- Predecessor: none
- Successor: not yet spawned

## Active Timers
- Heartbeat cron: 1185aa9c-d2b0-48fc-8519-b811ce683f65/task-21
- Safety timer: none

## Artifact Index
- /home/milhy777/rpi-dashboard/.agents/orchestrator/PROJECT.md — Project scope and milestones
- /home/milhy777/rpi-dashboard/.agents/orchestrator/plan.md — Project plan
- /home/milhy777/rpi-dashboard/.agents/orchestrator/progress.md — Heartbeat and status
- /home/milhy777/rpi-dashboard/.agents/orchestrator/context.md — Context and details
