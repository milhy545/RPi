import re

MOCK_TUI_CONTENT = """import time

INACTIVITY_TIMEOUT = 999999.0
class SystemStats:
    def on_mount(self) -> None:
        pass

class MatrixRain:
    pass

class IdleScreen(Screen):
    pass
class RPiDashboard:
    def on_mount(self) -> None:
        pass
"""

print("Original regex:")
content1 = re.sub(
    r'INACTIVITY_TIMEOUT = 999999\.0.*?class IdleScreen\(Screen\):.*?(?=\n\nclass RPiDashboard)',
    '', MOCK_TUI_CONTENT, flags=re.DOTALL
)
print(repr(content1))

print("Modified regex:")
content2 = re.sub(
    r'INACTIVITY_TIMEOUT = 999999\.0.*?class IdleScreen\(Screen\):.*?(?=\nclass RPiDashboard)',
    '', MOCK_TUI_CONTENT, flags=re.DOTALL
)
print(repr(content2))
