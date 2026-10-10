# Specification: Unified Return Control and MPV EOF Recovery

## Overview

Create one reliable return-to-dashboard action used by every external mode,
automatic MPV EOF recovery, one global keyboard shortcut, and a long press of
the Xbox controller B button.

Approved default: `Ctrl+Alt+Backspace` on the keyboard and a 2-second hold of
Xbox B. The duration remains configurable within a safe tested range.

## Motivation

EOF helper functions and a shallow unit test exist, but production callers do
not start the listener. Return instructions are inconsistent: Steam Link often
uses `Ctrl+Q`, terminal uses tmux detach, other apps use `Ctrl+C`, and WebUI has
a separate Stop action. There is no single physical escape mechanism that works
across MPV, Steam Link, Moonlight/GFN, Spotify/WPE, Amazon Music, terminal, and
future modes.

The Xbox controller is visible as gamepad, consumer-control, keyboard, and
mouse input. A global listener must avoid exclusive grabs, duplicate events,
and conflicts with Steam Input, xpadneo, Textual, triggerhappy, and `keys2mpv`.

## Functional Requirements

- Define one idempotent `return_to_dashboard(reason, source)` service action
  used by TUI, WebUI/API, EOF, process exit/crash, keyboard, and gamepad.
- Apply a mode-specific graceful shutdown first, then a bounded escalation; the
  dashboard must resume exactly once and record the reason/source.
- Support all current external modes: MPV, Steam Link, Moonlight/GFN,
  Spotify/WPE, Amazon Music, terminal/tmux, and any mode registered later.
- Install the approved global keyboard shortcut, `Ctrl+Alt+Backspace`, that
  works while any mode owns the foreground. Prevent accidental activation and
  document/remap it centrally rather than per application.
- Detect a continuous 2-second Xbox B hold across controller
  reconnect and event-device renumbering. Normal B taps and shorter holds must
  continue to reach the active game/application unchanged.
- Do not exclusively grab the controller or synthesize a B release into the
  active application. Deduplicate multiple Xbox input interfaces and repeated
  key events.
- Make the keyboard/gamepad watcher adapter- and device-hotplug aware, bounded
  in CPU/memory, and compatible with `keys2mpv` and triggerhappy.
- Start MPV EOF monitoring in the production playback lifecycle and distinguish
  EOF, user stop, crash, stale socket, and emergency return.
- Preserve playback resume memory semantics and expose concise status/log data.
- Provide a WebUI/TUI setting and status for shortcut mapping, B-hold duration,
  watcher health, last activation, and temporary disable.

## Non-Functional Requirements

- Reliability: no orphan listener, double teardown, stuck key state, or return
  loop after dashboard resume.
- Performance: event-driven input with negligible idle CPU and bounded logs.
- Safety: destructive/system power actions must never share this shortcut.
- Usability: the shortcut works without SSH and is documented consistently in
  CZ/EN help for every mode.

## Acceptance Criteria

- [ ] One tested action returns from every registered mode and records its
  reason/source exactly once.
- [ ] `Ctrl+Alt+Backspace` works globally and does
  not fire from partial/unrelated keyboard input.
- [ ] Holding Xbox B for 2 seconds returns from every external mode;
  a normal tap and a just-under-threshold hold remain untouched.
- [ ] Controller disconnect/reconnect, input renumbering, duplicate interfaces,
  Steam Input, triggerhappy, and `keys2mpv` do not cause false or double returns.
- [ ] Integration tests prove EOF triggers one clean return; stop, crash, stale
  socket, and emergency-return paths remain deterministic.
- [ ] Resume memory is saved only when appropriate.
- [ ] Controlled live checks cover MPV EOF plus keyboard and Xbox return from
  MPV, Steam Link, Moonlight/GFN, Spotify/WPE, Amazon Music, and terminal.
- [ ] Dashboard shutdown no longer reaches a forced systemd timeout.

## Constraints and Dependencies

- Linux input/udev, xpadneo, triggerhappy, `keys2mpv`, MPV IPC, tmux, mode
  switcher lifecycle, and live `tui.py` entrypoint.
- Xbox B is normally `BTN_EAST`, but matching must use verified device
  capabilities/identity rather than a hard-coded `/dev/input/eventN` path.
- Global input access and service changes require least privilege and rollback.

## Risks

- A global shortcut can discard unsaved foreground work; require deliberate
  combination/hold, visible feedback where possible, and configurable mapping.
- Steam Input or multiple Xbox interfaces can duplicate/suppress events; test
  the actual controller path without exclusive grabs.
- Race between mode teardown, EOF, and shortcut listener; use one idempotent
  owner and reason-priority rules.

## Out of Scope

- Replacing MPV, Steam Link, Moonlight, or the Xbox driver.
- Mapping a short/normal B press to dashboard return.
- Reboot, shutdown, or unrelated privileged actions from the return shortcut.
