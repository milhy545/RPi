## 2026-08-07 - Refactoring textual metrics
**Learning:** Textual widgets that share logic, such as gathering standard linux metric files (`/proc/stat`, `/proc/meminfo`, `/sys/class/thermal/thermal_zone0/temp`), are good targets for mixins instead of duplicating code.
**Action:** Use Python class mixins to share methods across components to keep bundle size down and maintenance simple.
