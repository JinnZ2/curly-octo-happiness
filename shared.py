#!/usr/bin/env python3
"""shared.py – compatibility shim.

The classes that used to live here moved to the `grounding` package
(one canonical implementation instead of per-file copies). This module
re-exports them so `from shared import ...` keeps working for
playground4-8 and meta_playground.

Note: `Claim.status` is now a read-only property (there is no separate
"uncertain" state anymore), and `DependencyNode.dependencies` is an
alias of `DepNode.deps`.
"""

from grounding.core.claims import Claim, DepNode as DependencyNode, DependencyTree
from grounding.core.memory import SharedMemory
from grounding.core.mentor import MentorInterface

__all__ = ["Claim", "DependencyNode", "DependencyTree", "SharedMemory", "MentorInterface"]
