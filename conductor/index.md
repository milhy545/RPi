# Conductor Index: RPi Dumb TV Dashboard

## Canonical Project Root

- Repository root: the Git top-level directory containing this project.
- Authoritative context: `<repository>/conductor`.
- Host-specific startup routing and compatibility links are local configuration. Agents must resolve the repository root before RPi Dashboard discovery, planning, Git operations, or writes.

## Project Files
- [Product Definition](./product.md)
- [Product Guidelines](./product-guidelines.md)
- [Tech Stack](./tech-stack.md)
- [Workflow](./workflow.md)
- [Tracks Registry](./tracks.md)
- [Tracks Directory](./tracks/)

## Code Style Guides
- [Python](./code_styleguides/python.md)
- [General](./code_styleguides/general.md)

## CI Safety Rules
- [CI Safety Rules](./ci/SAFETY-RULES.md)

**MANDATORY**: Before claiming any task is "done", run:
```bash
tools/verify-done.sh
```
If it exits with code 1, the task is NOT done. Period.
