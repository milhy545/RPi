# Session Validation Benchmark — Live RPi Evidence

**Host:** rpi-tv  
**Python:** 3.11.2  
**Date:** 2026-07-30T13:49:11+01:00  
**File tested:** `rpi_dashboard/auth.py`  
**File SHA256:** `c6ac15a48e6b5ef90b7c6c97116b946cbfe9ee902673cec0e5065c6b05942d5a`  
**Benchmark:** custom 1000-call Python script directly exercising `SessionStore.validate()`  

## Results

| Metric | Measured | Limit | Status |
|--------|----------|-------|--------|
| Median | 0.0368 ms | ≤ 1 ms | PASS |
| P95    | 0.0452 ms | ≤ 5 ms | PASS |
| Max    | 0.2599 ms | —     | — |

## Provenance

The `auth.py` file was tested under an **isolated temporary package** (copied to a
standalone directory containing only `rpi_dashboard/__init__.py` and the
copied `auth.py`). The production runtime on rpi-tv — including the running
dashboards, `auth.json`, and any service state — was **not** modified, read,
or accessed during the test.

### Harness note

An earlier run using a bare `importlib` harness failed with
`AttributeError: 'NoneType' object has no attribute '__dict__'` during
dataclass processing because the dynamically loaded module was not inserted
in `sys.modules`. The benchmark was re-run successfully with a proper
package-import approach (temporary directory with `rpi_dashboard/__init__.py`
and the copied `auth.py`), which placed the module in `sys.modules` and
produced the results above.

## Conclusion

All measured values are well within the spec limits (median ≤ 1 ms,
p95 ≤ 5 ms). Session validation on the target RPi performs no PBKDF or
filesystem I/O — only a SHA-256 digest and a locked dictionary lookup.
The Phase 3 `SessionStore` implementation is validated on target hardware.
