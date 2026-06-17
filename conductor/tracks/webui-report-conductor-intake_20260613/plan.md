# Implementation Plan: WebUI Report to Conductor Intake

## Phase 1: Safe MVP Without Agent
- [ ] Add `conductor/inbox/feedback/` storage.
- [ ] Add `/feedback/report` endpoint with input validation.
- [ ] Add `/feedback/status` endpoint.
- [ ] Add deterministic draft-track generator from templates.
- [ ] Add modal UI and footer buttons to every tab.

## Phase 2: Background Processing
- [ ] Add non-blocking worker thread/process for report processing.
- [ ] Store progress states: `queued`, `diagnosing`, `needs_questions`, `draft_created`, `failed`.
- [ ] Persist worker logs to report JSON.

## Phase 3: Pi Agent Integration
- [ ] Add configurable environment variable `WEBUI_REPORT_PI_MODEL`.
- [ ] Add safe `pi -p --thinking high` invocation wrapper with timeout.
- [ ] Parse agent output into either draft track or follow-up questions.
- [ ] Never apply code changes automatically from a report.

## Phase 4: UI Progress and Questions
- [ ] Show progress dialog after submit.
- [ ] Poll `/feedback/status` until complete/question/error.
- [ ] Display follow-up questions and append answers to the same report.
- [ ] Link to generated Conductor track in the UI.

## Phase 5: Validation
- [ ] Unit-test report validation and slug generation.
- [ ] E2E-test bug report from at least two tabs.
- [ ] E2E-test feature request with vague wording and follow-up question state.
- [ ] Confirm no mpv interruption and no WebUI regression.
