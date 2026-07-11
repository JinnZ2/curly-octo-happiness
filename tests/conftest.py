"""Make the repo's script directories importable during tests.

There are no packages outside grounding/ — root scripts, modules/,
plugins/, diagnostic/ and project/ all rely on their own directory
being on sys.path (see CLAUDE.md).
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for sub in ("", "modules", "plugins", "diagnostic", "project"):
    path = os.path.join(ROOT, sub) if sub else ROOT
    if path not in sys.path:
        sys.path.insert(0, path)
