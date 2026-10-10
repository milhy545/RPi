import re

with open("tui.py", "r") as f:
    content = f.read()

# Update play_media mpv command
content = re.sub(
    r'"mpv", "--fs", "--input-ipc-server=/tmp/mpv-socket",\n\s*"--cache=yes",',
    '"mpv", "--fs", "--input-ipc-server=/tmp/mpv-socket", "--vo=drm",\n            "--cache=yes",',
    content
)

# Update btn_gfn to use moonlight-qt if moonlight is missing? moonlight-qt installs `moonlight-qt` binary. Let's use moonlight-qt explicitly.
content = re.sub(
    r'cmd = \["moonlight", "stream", "192\.168\.0\.67", "GeForce Now"\]\n\s*if not shutil\.which\("moonlight"\):',
    'cmd = ["moonlight-qt", "stream", "192.168.0.67", "GeForce Now"]\n            if not shutil.which("moonlight-qt"):',
    content
)

# Update btn_mpv to use --vo=drm
content = re.sub(
    r'cmd = \["mpv"\]',
    'cmd = ["mpv", "--vo=drm"]',
    content
)

# Update btn_spotify to use cog
content = re.sub(
    r'cmd = \["wpe"\]\n\s*if not shutil\.which\("wpe"\):',
    'cmd = ["cog", "--platform=drm", "https://open.spotify.com"]\n            if not shutil.which("cog"):',
    content
)

# Update btn_amazon to use cage
content = re.sub(
    r'cmd = \["chromium", "--kiosk"',
    'cmd = ["cage", "-d", "--", "chromium", "--kiosk"',
    content
)
# Make sure checking for cage instead of chromium
content = re.sub(
    r'if not shutil\.which\("chromium"\):',
    'if not shutil.which("cage") or not shutil.which("chromium"):',
    content
)

with open("tui.py", "w") as f:
    f.write(content)

print("Done")
