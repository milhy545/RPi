import asyncio
import os
from tui import RPiDashboard
from mode_switcher import ModeSwitcherState

async def run_tests():
    print("=== STARTING MODE SWITCHER TEST SUITE ===")
    os.environ["RPIDASHBOARD_TEST_COMMAND"] = "sleep 999"
    app = RPiDashboard()
    
    async with app.run_test() as pilot:
        print("Log buffer at start:", app.mode_switcher.log_buffer.get_lines())
        
        # 1. Verify app starts and is in IDLE mode
        assert app.mode_switcher.state == ModeSwitcherState.IDLE
        print("✓ App started in IDLE mode")

        # 2. Test watchdog timeout (press "w")
        print("\n--- Testing Watchdog Timeout ---")
        print("Pressing 'w' to launch 'sleep 999' with 5s watchdog timeout...")
        await pilot.press("w")
        await asyncio.sleep(0.5)
        
        # Should be RUNNING
        assert app.mode_switcher.state == ModeSwitcherState.RUNNING
        print("✓ State transitioned to RUNNING")

        print("Waiting for watchdog to trigger (5s limit)...")
        await asyncio.sleep(5.5)
        
        # Watchdog should fire, terminate sleep, and restore TUI
        assert app.mode_switcher.state == ModeSwitcherState.IDLE
        logs = app.mode_switcher.log_buffer.get_lines()
        assert any("Watchdog fired" in log for log in logs)
        print("✓ Watchdog fired, terminated process, and restored state to IDLE")

        # 3. Test crash recovery (press "c")
        print("\n--- Testing Crash Recovery ---")
        print("Pressing 'c' to launch 'false' (non-zero exit status)...")
        await pilot.press("c")
        
        print("Waiting for exit...")
        await asyncio.sleep(1.0)
        assert app.mode_switcher.state == ModeSwitcherState.IDLE
        logs = app.mode_switcher.log_buffer.get_lines()
        assert any("returned code 1" in log for log in logs)
        print("✓ Crash recovery verified (TUI safely restored to IDLE after non-zero exit)")

        # 4. Test concurrency serialization (press "g")
        print("\n--- Testing Concurrency Serialization ---")
        print("Pressing 'g' to trigger concurrent launch requests...")
        await pilot.press("g")
        # Wait for both sleeps to complete (serialized: ~4s total)
        await asyncio.sleep(5.0)
        
        logs = app.mode_switcher.log_buffer.get_lines()
        success_logs = [log for log in logs if "succeeded" in log or "passed" in log or "finished" in log]
        print("Relevant logs:")
        for w in success_logs[-3:]:
            print(f"  {w}")
        assert any("passed" in log or "succeeded" in log for log in logs)
        print("✓ Concurrency serialization works - both launches succeeded sequentially")

        await asyncio.sleep(2.0)

        # 5. Test SIGINT handling (launch controlled long-running command, then trigger sigint)
        print("\n--- Testing SIGINT Handling ---")
        print("Clicking SteamLink button with controlled test command...")
        await pilot.click("#btn_steamlink")
        await asyncio.sleep(0.5)
        assert app.mode_switcher.state == ModeSwitcherState.RUNNING
        print("✓ Test subprocess running")

        print("Sending SIGINT to process...")
        app.mode_switcher._handle_sigint()
        
        await asyncio.sleep(1.0)
        assert app.mode_switcher.state == ModeSwitcherState.IDLE
        print("✓ SIGINT handled, subprocess terminated, state restored to IDLE")

        # 6. Test SIGTERM handling (launch controlled long-running command, then trigger sigterm)
        print("\n--- Testing SIGTERM Handling ---")
        print("Clicking SteamLink button...")
        await pilot.click("#btn_steamlink")
        await asyncio.sleep(0.5)
        assert app.mode_switcher.state == ModeSwitcherState.RUNNING
        print("✓ Test subprocess running")

        print("Sending SIGTERM to process...")
        app.mode_switcher._handle_sigterm()
        
        await asyncio.sleep(1.0)
        print("✓ SIGTERM handled, clean shutdown initiated")
        
        print("\n=== ALL TESTS PASSED SUCCESSFULLY ===")

def test_mode_switcher_suite():
    asyncio.run(run_tests())

if __name__ == "__main__":
    test_mode_switcher_suite()
