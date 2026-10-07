import os
import sys
import pytest

class TestCollectorPlugin:
    def __init__(self):
        self.node_ids = set()

    def pytest_itemcollected(self, item):
        self.node_ids.add(item.nodeid)

    def pytest_collection_modifyitems(self, session, config, items):
        for item in items:
            self.node_ids.add(item.nodeid)

    def pytest_collection_finish(self, session):
        for item in getattr(session, "items", []):
            self.node_ids.add(item.nodeid)

def count_tests(test_dir="tests"):
    if not os.path.exists(test_dir) and os.path.exists(os.path.join("anti_gravity", test_dir)):
        test_dir = os.path.join("anti_gravity", test_dir)

    plugin = TestCollectorPlugin()
    ret = pytest.main(["--collect-only", "-q", test_dir], plugins=[plugin])
    count = len(plugin.node_ids)

    print(f"Collected test count: {count}")
    if count >= 200 and int(ret) == 0:
        sys.exit(0)
    else:
        print(f"ERROR: Expected >=200 tests, found {count} (exit code: {ret})", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    count_tests()
