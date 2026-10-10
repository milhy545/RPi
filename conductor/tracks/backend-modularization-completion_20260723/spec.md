# Specification: Backend Modularization, Visual Redesign, and Legacy Retirement

## Overview

Finish the behavioral module boundaries left incomplete by the original
full-stack refactor, deliver a coherent redesign of the production WebUI and
live TUI, and retire supported legacy endpoints through an explicit versioned
migration rather than indefinite compatibility duplication.

## Motivation

`webserver.py` remains 2,922 lines, Audio exceeds the intended module size, and
terminal plus several legacy endpoints still have duplicate runtime ownership.
The current production UI also contains overlapping old/new surfaces, while
compatibility routes keep obsolete implementations alive.

## Functional Requirements

- Add a working `python -m rpi_dashboard` entrypoint.
- Move remaining domain behavior behind service/API boundaries with one runtime
  owner per behavior.
- Inventory every legacy endpoint and consumer in WebUI, TUI, scripts, mobile
  clients, documentation, tests, and network integrations.
- Define a versioned replacement API and migration map for supported legacy
  endpoints; add deprecation responses/telemetry before removal where feasible.
- Migrate all in-repository consumers and provide household/client migration
  instructions before removing a supported endpoint.
- Remove obsolete legacy endpoints, inline frontend, and duplicate runtime code
  only after replacement behavior and rollback are verified.
- Redesign the production `rpi_dashboard/static/` WebUI and live `tui.py` with a
  consistent information architecture, responsive layouts, CZ/EN content,
  keyboard/gamepad navigation, high contrast, and task-oriented sections.
- Treat saved prototypes as references, not production entrypoints; eliminate
  visual duplication after the new production surfaces are proven.
- Split oversized modules by cohesive responsibility rather than line count.

## Non-Functional Requirements

- Reliability: runtime behavior and a controlled client migration take priority
  over fast deletion or line-count targets.
- Performance: redesign and modularization must reduce or preserve startup time,
  steady-state RAM, polling, and per-core CPU usage on the Raspberry Pi 3B.
- Accessibility: production WebUI and TV TUI remain usable by keyboard and
  gamepad, from 2-3 metres, with constrained terminal and mobile widths.
- Maintainability: one implementation, one route owner, and one production UI
  component for each behavior.

## Acceptance Criteria

- [ ] `python -m rpi_dashboard` starts the supported server entrypoint.
- [ ] No domain behavior or visible control has two active runtime owners.
- [ ] Every legacy endpoint has a recorded consumer, replacement, migration
  state, removal decision, and rollback path.
- [ ] All approved legacy removals occur only after in-repository and documented
  external consumers migrate; removed routes return a clear versioned response
  during the agreed transition where technically possible.
- [ ] Production WebUI and live TUI pass approved desktop, tablet, mobile, TV,
  constrained-terminal, CZ/EN, keyboard, and gamepad visual/interaction checks.
- [ ] Oversized modules have documented cohesive boundaries and focused tests.
- [ ] Startup, API, memory, polling, and per-core CPU measurements do not regress.
- [ ] Runtime service/API/UI smoke checks pass on the RPi.

## Constraints and Dependencies

- The production TUI is `tui.py`; `rpi_dashboard/tui/modern.py` remains a
  prototype until a separately verified migration replaces it.
- Browser-heavy screenshot and interaction verification runs on Milhy-PC.
- Removing a supported route is a breaking change and requires an approved
  migration inventory, not an assumption that no external client exists.

## Risks

- Endpoint removal can break phones, scripts, or household integrations not
  visible in repository search; add telemetry, an announced window, and rollback.
- A broad redesign can obscure behavior regressions; migrate section by section
  with screenshots, interaction tests, and live TV checks.
- Large refactors can increase memory temporarily; keep phases independently
  shippable and measure on the RPi.

## Out of Scope

- Keeping obsolete endpoints forever after their approved migration completes.
- Replacing lightweight Textual/static HTML with Electron or a desktop stack.
- Decorative animation or redesign work that violates the Goat Principle or
  the Raspberry Pi memory budget.
