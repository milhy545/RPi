# Specification: WebUI Report to Conductor Intake

## Goal
Add a user-facing feedback intake system to the WebUI that can capture bug reports and feature requests from any tab and turn them into structured Conductor tracks with assistance from a background Pi agent.

## User Story
At the bottom of each WebUI tab, the user sees two buttons:
- **Report bug**: opens a floating dialog where the user describes what is broken.
- **Request feature**: opens a floating dialog where the user describes a future improvement.

After confirmation, the WebUI shows a progress dialog explaining that the system is diagnosing the request and that follow-up questions may appear. The backend stores the raw report, runs a background analysis/generation pipeline, and creates a draft Conductor track.

## Requirements
- Add reusable footer actions to every WebUI tab.
- Floating modal must support:
  - report type (`bug` or `feature`)
  - current tab/context
  - free-text description
  - optional contact/notes field in the future
- Backend must save reports to a durable local inbox before invoking any agent.
- Background worker must be non-blocking for the WebUI.
- The first implementation must be safe and deterministic: create a draft Conductor track from a template even if Pi analysis fails.
- Pi agent invocation must be configurable, not hardcoded to a private model name.
- Suggested default command form:
  - `pi --approve --model "$WEBUI_REPORT_PI_MODEL" --thinking high -p <prompt>`
- If model is unavailable, the system must keep the report as `needs_triage` and tell the user.
- Follow-up questions must be represented as a pending question state instead of silently inventing requirements.
- Never run destructive commands from the generated report automatically.

## Naming
Working feature name: **Feedback Intake**.
Backend route namespace: `/feedback/*`.
Conductor track category: `webui-feedback-intake`.

## Data Model
Reports should be stored under:
- `conductor/inbox/feedback/<timestamp>_<type>.json`
- generated tracks under `conductor/tracks/<slug>_<YYYYMMDD>/`

Minimum report fields:
- `id`
- `type`
- `tab`
- `description`
- `status`
- `created_at`
- `updated_at`
- `generated_track_id`
- `questions`
- `agent_log`

## Acceptance Criteria
- [ ] Every WebUI tab shows `Report bug` and `Request feature` buttons at the bottom.
- [ ] Modal opens without leaving the tab.
- [ ] Submitting creates a durable JSON report in `conductor/inbox/feedback/`.
- [ ] `/feedback/report` accepts bug/feature payloads and validates them.
- [ ] `/feedback/status?id=...` reports progress.
- [ ] Background worker can create a draft Conductor track from the report.
- [ ] If Pi agent analysis asks clarifying questions, UI displays them instead of marking the track done.
- [ ] If Pi is unavailable, the report remains safely queued.
- [ ] All generated markdown is English.
