import urllib.request
import urllib.error
import json
import os

token = os.environ.get("GITHUB_TOKEN")
if not token:
    print("GITHUB_TOKEN not set, cannot create PR.")
    exit(0)

# getting repo dynamically
import subprocess
try:
    url_out = subprocess.check_output(["git", "config", "--get", "remote.origin.url"], text=True).strip()
    if url_out.endswith(".git"):
        url_out = url_out[:-4]
    if "github.com" in url_out:
        repo = url_out.split("github.com/")[-1]
    else:
        repo = "milhy545/rpi-tv"
except Exception:
    repo = "milhy545/rpi-tv"

url = f"https://api.github.com/repos/{repo}/pulls"
headers = {
    "Authorization": f"token {token}",
    "Accept": "application/vnd.github.v3+json"
}

with open("pr_body.txt", "r") as f:
    body = f.read()

data = {
    "title": "⚡ Bolt: [network native optimization]",
    "head": "bolt/system-network-optimization",
    "base": "main",
    "body": body
}

req = urllib.request.Request(url, data=json.dumps(data).encode("utf-8"), headers=headers, method="POST")
try:
    with urllib.request.urlopen(req) as response:
        print(f"PR Created Successfully: {response.getcode()}")
except urllib.error.HTTPError as e:
    print(f"Failed to create PR: {e}")
    print(e.read().decode("utf-8"))
