# Specification: Core TUI Framework & Telemetry

## Overview
Implement the foundational Terminal User Interface (TUI) for the RPi Dumb TV Dashboard using a lightweight Python library (e.g., `blessed` or standard `curses`) to ensure RAM usage remains strictly under 20MB.

## Functional Requirements
- Display real-time CPU usage, RAM allocation, and CPU temperature.
- Implement a "Matrix" style idle screen that activates after a period of inactivity.
- Graceful handling of standard terminal signals (SIGINT, SIGTERM).

## Non-Functional Requirements
- **Memory Limit:** Core process must not exceed 20MB RAM.
- **CPU Limit:** Idle dashboard must use < 1% CPU.
- **Aesthetics:** Minimalist, text-based, function over form.

## Out of Scope
- Network API (handled in a separate track).
- Direct media playback integration (handled in a separate track).
