import sys
import os
import pytest

class TestCollectorPlugin:
    def __init__(self):
        self.collected = 0

    def pytest_collection_modifyitems(self, session, config, items):
        self.collected = len(items)

def count_tests(test_dir="tests"):
    # Ensure tests directory exists relative to current working directory
    if not os.path.exists(test_dir) and os.path.exists(os.path.join("anti_gravity", test_dir)):
        test_dir = os.path.join("anti_gravity", test_dir)

    plugin = TestCollectorPlugin()
    # Run pytest with --collect-only and custom plugin
    ret = pytest.main(["--collect-only", "-q", test_dir], plugins=[plugin])
    count = plugin.collected
    print(f"Collected test count: {count}")
    if count >= 200:
        sys.exit(0)
    else:
        print(f"ERROR: Expected >=200 tests, found {count}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    count_tests()
