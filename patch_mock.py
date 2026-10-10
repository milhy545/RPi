with open("tests/test_fix_tui.py", "r") as f:
    content = f.read()

content = content.replace(
    "class SystemStats:\n    def on_mount(self) -> None:\n        pass\n\nclass MatrixRain:\n    pass\n\nclass IdleScreen(Screen):\n    pass\nclass RPiDashboard:\n    def on_mount(self) -> None:\n        pass",
    "class SystemStats:\n    def on_mount(self) -> None:\n        pass\n\nclass MatrixRain:\n    pass\n\nclass IdleScreen(Screen):\n    pass\n\nclass RPiDashboard:\n    def on_mount(self) -> None:\n        pass"
)
with open("tests/test_fix_tui.py", "w") as f:
    f.write(content)
