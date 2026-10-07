import os
import sys
import subprocess
import re

def count_tests():
    test_dir = "tests"
    if not os.path.exists(test_dir) and os.path.exists(os.path.join("anti_gravity", test_dir)):
        test_dir = os.path.join("anti_gravity", test_dir)

    env = os.environ.copy()
    env["PYTHONPATH"] = "."
    env["KIVY_NO_ARGS"] = "1"
    env["KIVY_NO_CONSOLELOG"] = "1"
    env["KIVY_WINDOW"] = "mock"

    cmd = [sys.executable, "-m", "pytest", test_dir, "--collect-only", "-q", "--disable-warnings"]
    result = subprocess.run(cmd, capture_output=True, text=True, env=env, encoding="utf-8", errors="replace")

    combined_output = f"{result.stdout}\n{result.stderr}"

    # Extract test count from pytest collection summary (e.g. "202 tests collected")
    match = re.search(r"(\d+)\s+tests?\s+collected", combined_output, re.IGNORECASE)
    
    count = 0
    if match:
        count = int(match.group(1))
    else:
        # Fallback: count collected node IDs with '::'
        node_ids = [line.strip() for line in result.stdout.splitlines() if "::" in line and not line.strip().startswith("=")]
        count = len(node_ids)

    print(f"Collected test count: {count}")

    if count >= 200:
        sys.exit(0)
    else:
        print(f"ERROR: Expected >=200 tests, found {count}", file=sys.stderr)
        print("--- PYTEST COLLECTION STDOUT ---", file=sys.stderr)
        print(result.stdout, file=sys.stderr)
        print("--- PYTEST COLLECTION STDERR ---", file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        print(f"Pytest returncode: {result.returncode}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    count_tests()
