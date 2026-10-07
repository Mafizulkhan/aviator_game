import os
import sys
import subprocess

def count_tests():
    test_dir = "tests"
    if not os.path.exists(test_dir) and os.path.exists(os.path.join("anti_gravity", test_dir)):
        test_dir = os.path.join("anti_gravity", test_dir)

    env = os.environ.copy()
    env["PYTHONPATH"] = "."
    env["KIVY_NO_ARGS"] = "1"
    env["KIVY_NO_CONSOLELOG"] = "1"
    env["KIVY_WINDOW"] = "mock"

    cmd = [sys.executable, "-m", "pytest", test_dir, "--collect-only", "-q"]
    result = subprocess.run(cmd, capture_output=True, text=True, env=env, encoding="utf-8", errors="replace")

    node_ids = []
    for line in result.stdout.splitlines():
        line = line.strip()
        if "::" in line and not line.startswith("="):
            node_ids.append(line)

    count = len(node_ids)
    print(f"Collected test count: {count}")

    if count >= 200:
        sys.exit(0)
    else:
        print(f"ERROR: Expected >=200 tests, found {count}", file=sys.stderr)
        if result.stderr:
            print(f"Pytest stderr:\n{result.stderr}", file=sys.stderr)
        print(f"Pytest returncode: {result.returncode}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    count_tests()
