with open("tests/test_fix_tui.py", "r") as f:
    content = f.read()
# We need to make sure the mocked tui.py has an empty line before class RPiDashboard
# so that the original regex from fix_tui.py works.
content = content.replace("    pass\nclass RPiDashboard:", "    pass\n\nclass RPiDashboard:")
with open("tests/test_fix_tui.py", "w") as f:
    f.write(content)
