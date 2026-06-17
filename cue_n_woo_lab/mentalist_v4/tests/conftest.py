"""Make `mentalist_v4` importable when tests run from the repo root."""
import os
import sys

sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..")))
