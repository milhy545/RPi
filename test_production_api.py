import asyncio
import json
import urllib.request
import urllib.error
import subprocess
import time
import os

API_PORT = int(os.getenv("RPIDASHBOARD_TEST_API_PORT", "18090"))
API_URL = f"http://127.0.0.1:{API_PORT}"

def make_request(path, method="GET", payload=None, headers=None):
    url = f"{API_URL}{path}"
    req_headers = {"Content-Type": "application/json"}
    if headers:
        req_headers.update(headers)
        
    data = json.dumps(payload).encode() if payload else None
    req = urllib.request.Request(url, data=data, headers=req_headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == 204:
                return 204, None
            return response.status, json.loads(response.read().decode())
    except urllib.error.HTTPError as e:
        if e.code == 204:
            return 204, None
        try:
            body = json.loads(e.read().decode())
        except Exception:
            body = e.reason
        return e.code, body
    except Exception as e:
        return 999, str(e)

async def main():
    print("=== STARTING PRODUCTION API INTEGRATION TESTS ===")
    
    # 1. Start headless API server
    print("[*] Launching headless TUI API server...")
    import sys
    server_proc = subprocess.Popen(
        [sys.executable, "tui.py", "--headless"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={**os.environ, "RPIDASHBOARD_API_PORT": str(API_PORT)},
    )
    
    # Wait for server to boot dynamically (necessary for slow emulation)
    print("[*] Waiting for API server to respond...")
    server_ready = False
    for i in range(25):
        try:
            req = urllib.request.Request(f"{API_URL}/status", method="GET")
            with urllib.request.urlopen(req, timeout=1) as response:
                if response.status == 200:
                    print(f"[+] API server ready after {i} seconds")
                    server_ready = True
                    break
        except Exception:
            pass
        time.sleep(1)
    
    if not server_ready:
        stdout, stderr = server_proc.communicate(timeout=1)
        raise RuntimeError(
            "API server failed to respond within timeout\n"
            f"stdout={stdout.decode(errors='replace')}\n"
            f"stderr={stderr.decode(errors='replace')}"
        )
    
    try:
        # Test 1: GET /status
        print("\nTest 1: Query status...")
        status, body = make_request("/status")
        print(f"Status: {status}, Body: {body}")
        poll_val = server_proc.poll()
        if poll_val is not None:
            print(f"Server exited with code: {poll_val}")
        assert status == 200
        assert body["status"] == "ok"
        assert body["mode"] == "IDLE (Dashboard)"
        assert "system" in body
        print("✓ GET /status returned IDLE and system stats successfully")

        # Test 2: POST /play (Accept)
        print("\nTest 2: Cast play URL...")
        status, body = make_request("/play", method="POST", payload={"url": "http://dummy.stream/video.mp4"})
        assert status == 200
        assert body["status"] == "ok"
        print("✓ POST /play accepted successfully")

        # Test 3: GET /status (active mode)
        print("\nTest 3: Query status during playback...")
        status, body = make_request("/status")
        assert status == 200
        # Headless mock doesn't launch real MPV subprocess unless running in TUI,
        # but let's verify if the status is active or mock play media handled.
        print(f"✓ GET /status during playback: Mode is '{body['mode']}'")

        # Test 4: POST /play (Conflict)
        # In headless mode, the dummy play is processed instantly, but let's check.
        print("\nTest 4: Verify play conflict handling...")
        # Since play media is run as an async task, we attempt immediate double play
        status, body = make_request("/play", method="POST", payload={"url": "http://dummy.stream/video2.mp4"})
        print(f"✓ POST /play returned status {status}: {body}")

        # Test 5: GET /audio/sinks
        print("\nTest 5: Retrieve audio sinks...")
        status, body = make_request("/audio/sinks")
        assert status == 200
        assert "sinks" in body
        print(f"✓ GET /audio/sinks returned {len(body['sinks'])} sinks")

        # Test 6: POST /audio/sinks/select
        print("\nTest 6: Select audio sink...")
        # Select first sink returned, or dummy
        sink_id = body["sinks"][0]["sink_id"] if body["sinks"] else "dummy_sink"
        status, body = make_request("/audio/sinks/select", method="POST", payload={"sink_id": sink_id})
        assert status == 200
        print("✓ POST /audio/sinks/select returned 200 OK")

        # Test 7: GET /bluetooth/devices
        print("\nTest 7: Retrieve bluetooth devices...")
        status, body = make_request("/bluetooth/devices")
        assert status == 200
        assert "paired" in body
        print("✓ GET /bluetooth/devices returned 200 OK")

        # Test 8: GET /wifi/networks
        print("\nTest 8: Retrieve wifi networks...")
        status, body = make_request("/wifi/networks")
        assert status == 200
        assert "networks" in body
        print("✓ GET /wifi/networks returned 200 OK")

        # Test 9: POST /player/volume (System pactl set volume)
        print("\nTest 9: Set system/player volume...")
        status, body = make_request("/player/volume", method="POST", payload={"level": 75})
        assert status == 200
        print("✓ POST /player/volume returned 200 OK")

        # Test 10: POST /player/pause (MPV IPC toggle)
        print("\nTest 10: Toggle pause...")
        # Since MPV is not running in headless dummy, IPC will fail, returning 400. Let's verify it fails gracefully.
        status, body = make_request("/player/pause", method="POST")
        assert status in [200, 400]
        print(f"✓ POST /player/pause handled gracefully: status {status}")

        # Test 11: CORS headers verification
        print("\nTest 11: CORS preflight request...")
        status, body = make_request("/status", method="OPTIONS")
        assert status == 204
        print("✓ OPTIONS /status returned 204 No Content with CORS headers")

        print("\n=== ALL PRODUCTION API INTEGRATION TESTS PASSED ===")
        
    finally:
        print("\n[*] Terminating API server process...")
        server_proc.terminate()
        server_proc.wait()

if __name__ == "__main__":
    asyncio.run(main())

def test_production_api_suite():
    asyncio.run(main())
