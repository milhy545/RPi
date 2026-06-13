import re

with open("provisioning/01-install-apt-deps.sh", "r") as f:
    content = f.read()

content = content.replace("    mpv", "    mpv\n    cage\n    cog")

with open("provisioning/01-install-apt-deps.sh", "w") as f:
    f.write(content)

with open("provisioning/provision.sh", "r") as f:
    content = f.read()

moonlight_repo = """echo "=== Setting up Moonlight Repository ==="
curl -1sLf 'https://dl.cloudsmith.io/public/moonlight-game-streaming/moonlight-qt/setup.deb.sh' | sudo -E bash

"""
content = content.replace('bash provisioning/01-install-apt-deps.sh', moonlight_repo + 'bash provisioning/01-install-apt-deps.sh\nsudo apt-get install -y --no-install-recommends moonlight-qt')

with open("provisioning/provision.sh", "w") as f:
    f.write(content)

print("Provisioning scripts updated")
