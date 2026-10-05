"""
Anti-Gravity — KV layout files loader
Ensures all .kv layout files are discovered by Kivy's Builder.
"""
from kivy.lang import Builder
import os

_KV_DIR = os.path.join(os.path.dirname(__file__), "..", "kv")


def load_all_kv():
    """Load every .kv file found in the kv/ directory."""
    for fname in sorted(os.listdir(_KV_DIR)):
        if fname.endswith(".kv"):
            Builder.load_file(os.path.join(_KV_DIR, fname))
