"""Make `cheater` importable when tests run from the repo root
(`uv run pytest cue_n_woo_lab/cheater/tests`)."""
import os
import sys

sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..")))
