# Wireframes — backend-modularization-completion_20260723

## Design goals

- Task-oriented, not feature-dump oriented.
- One primary action per section.
- Comfortable at TV distance and on phones.
- CZ/EN content parity.
- Keyboard and gamepad first.
- High contrast, low visual noise, no decorative clutter.

## Information architecture

### Primary production sections

1. Player
2. Apps
3. Audio
4. Bluetooth
5. Devices
6. Network
7. System
8. Logs
9. Terminal

### Section pairing

- **Player**: playback, URL input, seek/volume, age/cookie diagnostics.
- **Apps**: launch/return actions.
- **Audio**: output routing and mixer.
- **Bluetooth**: pairing / device control.
- **Devices**: hardware and network overview.
- **Network**: Wi‑Fi, hotspot, Tailscale.
- **System**: stats, restart actions.
- **Logs**: recent activity and warnings.
- **Terminal**: tmux bridge and diagnostics.

## WebUI — Basic layout

### Desktop / tablet

```
┌──────────────────────────────────────────────────────────────┐
│ Header: logo · language · connection status · quick actions   │
├───────────────┬──────────────────────────────────────────────┤
│ Left rail      │ Main content                                │
│ - Player       │ ┌──────────────┐ ┌────────────────────────┐ │
│ - Apps         │ │ Primary card  │ │ Secondary card         │ │
│ - Audio        │ └──────────────┘ └────────────────────────┘ │
│ - Bluetooth    │                                              │
│ - Devices      │ ┌──────────────────────────────────────────┐ │
│ - Network      │ │ Task-focused detail / diagnostics       │ │
│ - System       │ └──────────────────────────────────────────┘ │
│ - Logs         │                                              │
│ - Terminal     │ ┌──────────────────────────────────────────┐ │
│               │ │ Live feed / state / alerts                │ │
│               │ └──────────────────────────────────────────┘ │
└───────────────┴──────────────────────────────────────────────┘
```

### Mobile

```
┌──────────────────────┐
│ Header + quick bar   │
├──────────────────────┤
│ Section tabs         │
├──────────────────────┤
│ Main card            │
│ Details              │
│ Secondary controls   │
│ Alerts / logs        │
└──────────────────────┘
```

## WebUI — Expert layout

### Wide desktop

```
┌────────────────────────────────────────────────────────────────────────────┐
│ Header: connection · language · status · refresh · return · stop all      │
├────────────────────────────────────────────────────────────────────────────┤
│ Player / Apps    │ Audio topology / mixer        │ Diagnostics / logs     │
│ (top-left)       │ (center, primary)             │ (right rail)           │
├──────────────────┼───────────────────────────────┼────────────────────────┤
│ Device cards     │ Bluetooth topology            │ System / Network       │
│ (bottom-left)    │ (bottom-center)                │ (bottom-right)         │
└────────────────────────────────────────────────────────────────────────────┘
```

### Expert rules

- Audio stays visually dominant because it is the most frequent household task.
- Player remains one-click to playback and one-click to return.
- Bluetooth and Devices are adjacent, but not merged.
- Logs stay visible without stealing primary focus.

## Live TUI wireframe

### TV / 2–3 m view

```
┌────────────────────────────────────────────────────────────────────────────┐
│ DASHBOARD · mode · language · network · status                             │
├────────────────────────────────────────────────────────────────────────────┤
│ [Player] [Apps] [Audio] [Bluetooth] [Devices] [Network] [System] [Logs]   │
├────────────────────────────────────────────────────────────────────────────┤
│ Active section title                                                        │
│ Primary action row                                                          │
│ Detail panel / status text / live metrics                                   │
│ Secondary actions / hints                                                   │
└────────────────────────────────────────────────────────────────────────────┘
```

### Constrained terminal

```
┌────────────────────┐
│ DASHBOARD          │
├────────────────────┤
│ Active section     │
│ Primary action     │
│ Status             │
│ Help / keys        │
└────────────────────┘
```

## Navigation

### Keyboard

- `Tab` / arrow keys: move focus
- `Enter`: activate
- `Esc`: back/close overlay
- `Space`: toggle active controls where appropriate
- `Ctrl+Return` or explicit STOP button: return to dashboard from external modes

### Gamepad

- D-pad: move between section cards and controls
- A / South: activate
- B / East: back / return
- Start: quick actions / menu

## Current-to-target mapping

- Current player/route/audio behavior stays, but gets grouped into task-first cards.
- Existing CEC, Bluetooth, and System capabilities become compact status cards with clear action buttons.
- Legacy-only controls get moved under a compatibility/advanced foldout until removal is approved.

## Approval gate

Before production replacement:

1. Capture current desktop/tablet/mobile/TV/TUI screenshots remotely.
2. Review the wireframes with the current UI side by side.
3. Approve or adjust section ordering, spacing, and control density.
