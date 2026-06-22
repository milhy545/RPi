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

content = re.sub(
    r'INACTIVITY_TIMEOUT = 999999\.0\n',
    '', MOCK_TUI_CONTENT
)

content = re.sub(
    r'class MatrixRain:.*?class IdleScreen\(Screen\):.*?(?=\nclass RPiDashboard)',
    '', content, flags=re.DOTALL
)

print(repr(content))

content2 = re.sub(r'    def on_mount\(self\) -> None:', "TEST", content)
print(repr(content2))
