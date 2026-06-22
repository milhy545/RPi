import re

with open("fix_tui.py", "r") as f:
    content = f.read()

new_code = """# Remove INACTIVITY_TIMEOUT
content = re.sub(
    r'INACTIVITY_TIMEOUT = 999999\\.0\\n',
    '', content
)

# Remove MatrixRain and IdleScreen
content = re.sub(
    r'class MatrixRain:.*?class IdleScreen\\(Screen\\):.*?(?=\\nclass RPiDashboard|\\n\\nclass RPiDashboard)',
    '', content, flags=re.DOTALL
)"""

content = content.replace(
    """# Remove INACTIVITY_TIMEOUT and MatrixRain and IdleScreen
content = re.sub(
    r'INACTIVITY_TIMEOUT = 999999\\.0.*?class IdleScreen\\(Screen\\):.*?(?=\\n\\nclass RPiDashboard)',
    '', content, flags=re.DOTALL
)""",
    new_code
)

content = content.replace(
    "content = re.sub(r'    def on_mount\\(self\\) -> None:', CACHE_INIT, content)",
    "content = re.sub(r'class RPiDashboard:.*?    def on_mount\\(self\\) -> None:', 'class RPiDashboard:\\n' + CACHE_INIT, content, flags=re.DOTALL)"
)

with open("fix_tui.py", "w") as f:
    f.write(content)
