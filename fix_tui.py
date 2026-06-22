"""Refactoring script to automate updating tui.py during the migration."""
import re

with open("tui.py", "r", encoding="utf-8") as f:
    content = f.read()

# Remove INACTIVITY_TIMEOUT
content = re.sub(
    r'INACTIVITY_TIMEOUT = 999999\.0\n',
    '', content
)

# Remove MatrixRain and IdleScreen
content = re.sub(
    r'class MatrixRain:.*?class IdleScreen\(Screen\):.*?(?=\nclass RPiDashboard|\n\nclass RPiDashboard)',
    '', content, flags=re.DOTALL
)

# Remove screensaver_active from handle_status
content = re.sub(r'"screensaver_active": isinstance\(self\.screen, IdleScreen\),\n', '', content)
content = re.sub(r'"screensaver_active": False,\n', '', content)

# Remove handle_system_screensaver
content = re.sub(
    r'    async def handle_system_screensaver\(.*?(?=\n    async def play_media)',
    '', content, flags=re.DOTALL
)

# Remove play_media reset_inactivity calls
content = re.sub(r'        self\.reset_inactivity\(\)\n', '', content)

# Remove reset_inactivity method and _check_settings_cache
content = re.sub(
    r'    def reset_inactivity\(self\) -> None:.*?(?=\n    def on_key)',
    '', content, flags=re.DOTALL
)

# Remove on_key reset_inactivity
content = re.sub(r'        self\.reset_inactivity\(\)\n', '', content)

# Remove on_mouse_move
content = re.sub(
    r'    def on_mouse_move\(self, event\) -> None:.*?(?=\n    async def run_watchdog_test)',
    '', content, flags=re.DOTALL
)

# Add Cache initialization in RPiDashboard
CACHE_INIT = """    def on_mount(self) -> None:
        self._settings_cache = {
            "network": 0.0,
            "audio": 0.0,
            "bluetooth": 0.0,
            "wifi": 0.0
        }
        self._settings_cache_ttl = 10.0
"""
if "class RPiDashboard:" in content and "self._settings_cache = {" not in content.split("class RPiDashboard:", 1)[1]:
    # Match only RPiDashboard's on_mount (preceded by 'class RPiDashboard:')
    content = re.sub(r'(class RPiDashboard:.*?)    def on_mount\(self\) -> None:', r'\1' + CACHE_INIT, content, flags=re.DOTALL)
    content = re.sub(r'class RPiDashboard:.*?    def on_mount\(self\) -> None:', 'class RPiDashboard:\n' + CACHE_INIT, content, flags=re.DOTALL)

# Replace update_settings_data with TTL logic
UPDATE_SETTINGS = """    async def update_settings_data(self) -> None:
        \"\"\"Refresh all settings panel widgets with system configuration data.\"\"\"
        try:
            active_tab = self.query_one(TabbedContent).active
            if active_tab != "tab_settings":
                return
        except Exception:
            return

        current_time = time.time()
        self._updating_settings = True
        try:
            if current_time - self._settings_cache["network"] > self._settings_cache_ttl:
                await self.update_network_info()
                self._settings_cache["network"] = current_time

            if current_time - self._settings_cache["audio"] > self._settings_cache_ttl:
                await self.update_audio_sinks()
                self._settings_cache["audio"] = current_time

            if current_time - self._settings_cache["bluetooth"] > self._settings_cache_ttl:
                await self.update_bluetooth_devices()
                self._settings_cache["bluetooth"] = current_time

            if current_time - self._settings_cache["wifi"] > self._settings_cache_ttl:
                await self.update_wifi_hotspot_info()
                self._settings_cache["wifi"] = current_time
        finally:
            self._updating_settings = False
"""
if "active_tab = self.query_one(TabbedContent).active" not in content:
    # Use split regex to keep it under 100 characters per line
    update_data_re = r'    async def update_settings_data\(self\) -> None:.*?'
    update_data_re += r'            self\._updating_settings = False\n'

    content = re.sub(update_data_re, UPDATE_SETTINGS, content, flags=re.DOTALL)

# Remove API routing for screensaver
content = re.sub(
    r'            api_app\.router\.add_post\("/system/screensaver", '
    r'_system_screensaver\)\n',
    '', content
)

# Remove the internal handler logic using string concatenation for the regex
content = re.sub(
    r'            async def _system_screensaver\(req\):.*?(?=\n'
    r'            api_app\.router\.add_post)',
    '', content, flags=re.DOTALL
)

with open("tui.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Done")
