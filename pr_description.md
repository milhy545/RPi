🧹 [Code Health] Remove unused time and glob imports in keys2mpv.py

🎯 **What:** Removed the unused `time` and `glob` imports from `keys2mpv.py` and formatted the remaining imports to follow PEP 8 standards (one per line). Also cleaned up a few instances of trailing whitespace.
💡 **Why:** Improves code maintainability and readability by removing dead code. Re-formatting imports ensures standard library imports are grouped and easier to read.
✅ **Verification:** Ran `python3 -m py_compile keys2mpv.py` to ensure there are no syntax errors. Checked that tests run correctly.
✨ **Result:** Cleaner imports without changing any functionality.
