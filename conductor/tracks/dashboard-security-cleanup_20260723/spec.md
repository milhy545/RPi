# Specification: Dashboard Security Cleanup

## Overview

Close the concrete security gaps found during Conductor reconciliation without
changing the dashboard's trusted LAN/Tailscale operating model.

## Motivation

Wi-Fi credentials still reach command-line arguments on some paths, the
terminal WebSocket relies only on an IP allowlist, one bare `except:` remains,
and Bandit currently reports medium-severity findings.

## Functional Requirements

- Pass Wi-Fi credentials through stdin or another non-command-line channel.
- Move Wi-Fi settings out of Devices and into the existing Network section in
  both WebUI and the live `tui.py`; Devices must link to Network rather than
  retain a second Wi-Fi implementation.
- Preserve scan, status, saved-network, connect/disconnect, rescue-hotspot, and
  actionable error behavior after the move.
- Require authenticated terminal WebSocket setup in addition to subnet checks.
- Remove the remaining bare exception and review swallowed security failures.
- Review and disposition every current medium Bandit finding.
- Preserve CORS, rate limiting, HTTPS, and legacy API compatibility.

## Non-Functional Requirements

- Security: credentials must not appear in process arguments or logs.
- Reliability: Wi-Fi and terminal workflows retain focused regression tests.
- Performance: authentication adds negligible overhead on the Raspberry Pi.

## Acceptance Criteria

- [ ] Process inspection cannot reveal a submitted Wi-Fi password.
- [ ] WebUI and live TUI expose one Wi-Fi settings implementation under Network;
  Devices contains no duplicate controls and provides a clear navigation hint.
- [ ] Wi-Fi scan, connect, disconnect, saved-network, and rescue-hotspot tests
  pass from the new location at supported screen sizes.
- [ ] Unauthorized WebSocket clients are rejected before tmux access.
- [ ] No bare `except:` remains in production Python.
- [ ] Bandit has zero high findings and all medium findings are fixed or documented.
- [ ] Focused security and API tests pass.

## Constraints and Dependencies

- Existing API-key/subnet configuration and WebUI terminal client.

## Risks

- Locking out the household terminal; provide a tested migration and clear error.
- Moving Wi-Fi controls can break saved selectors or keyboard navigation; use
  characterization tests and retain service/API behavior during the UI move.

## Out of Scope

- Public internet exposure or a new identity provider.
