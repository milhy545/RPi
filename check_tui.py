import py_compile
import sys
try:
    py_compile.compile('tui.py', doraise=True)
    print("tui.py compiles successfully.")
except Exception as e:
    print(e)
    sys.exit(1)
