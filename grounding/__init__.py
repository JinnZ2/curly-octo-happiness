"""grounding — the shared core of the playground repository.

Single home for the classes that were previously copy-pasted across
garden*, weave*, unified_playground* and shared.py (REVIEW.md §1.6/§4.2):
Claim, DependencyTree, EpisodicMemory, SharedMemory, Mentor, BumpyWorld,
WorldModel, and the canonical Gray-coding helpers.

Run scripts from the repository root (or `pip install -e .`) so this
package is importable.
"""

from grounding.core.claims import Claim, DepNode, DependencyTree
from grounding.core.graycode import gray_bits, gray_to_index
from grounding.core.memory import EpisodicMemory, MemoryStream, SharedMemory
from grounding.core.mentor import Mentor, MentorInterface
from grounding.worlds.bumpy import BumpyWorld, WorldModel

__all__ = [
    "Claim", "DepNode", "DependencyTree",
    "gray_bits", "gray_to_index",
    "EpisodicMemory", "MemoryStream", "SharedMemory",
    "Mentor", "MentorInterface",
    "BumpyWorld", "WorldModel",
]
