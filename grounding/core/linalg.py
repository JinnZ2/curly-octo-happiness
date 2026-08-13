"""Symmetric eigenvalues, stdlib-first.

Two things in this repo need the spectrum of a real symmetric matrix — graph
energy in `modules/gae.py` (adjacency) and the synchronizability criterion in
`core/coupling.py` (Laplacian) — so the solver lives here rather than in either
of them.

Cyclic Jacobi rotations, which are slow but dependency-free and numerically
solid for the matrix sizes this repo deals with. numpy is used when it is
present, purely as an accelerator: the two agree to 1e-8, and there is a test
that says so. That is the tier rule in `pyproject.toml` made concrete — an
extra may make the core faster, never smarter.
"""

import math
from typing import List, Optional, Sequence

try:                      # optional accelerator, never a requirement
    import numpy as _np
except ImportError:       # pragma: no cover - exercised on numpy-less installs
    _np = None

__all__ = ["JACOBI_NODE_CAP", "symmetric_eigenvalues"]

# Above this size the pure-Python solve is too slow to be worth running, and
# callers that care are told rather than left waiting.
JACOBI_NODE_CAP = 160


def _jacobi_eigenvalues(matrix: Sequence[Sequence[float]], sweeps: int = 60,
                        tol: float = 1e-9) -> List[float]:
    """Eigenvalues of a real symmetric matrix by cyclic Jacobi rotations."""
    n = len(matrix)
    a = [list(row) for row in matrix]
    for _ in range(sweeps):
        off = sum(a[i][j] ** 2 for i in range(n) for j in range(n) if i != j)
        if off <= tol:
            break
        for p in range(n - 1):
            for q in range(p + 1, n):
                if abs(a[p][q]) < 1e-12:
                    continue
                theta = (a[q][q] - a[p][p]) / (2.0 * a[p][q])
                sign = 1.0 if theta >= 0 else -1.0
                t = sign / (abs(theta) + math.sqrt(theta * theta + 1.0))
                c = 1.0 / math.sqrt(t * t + 1.0)
                s = t * c
                for k in range(n):
                    akp, akq = a[k][p], a[k][q]
                    a[k][p] = c * akp - s * akq
                    a[k][q] = s * akp + c * akq
                for k in range(n):
                    apk, aqk = a[p][k], a[q][k]
                    a[p][k] = c * apk - s * aqk
                    a[q][k] = s * apk + c * aqk
    return [a[i][i] for i in range(n)]


def symmetric_eigenvalues(matrix: Sequence[Sequence[float]],
                          cap: Optional[int] = JACOBI_NODE_CAP) -> List[float]:
    """Ascending eigenvalues of a real symmetric matrix.

    Args:
        matrix: square, symmetric. Not checked here — callers that build the
            matrix know whether it is (both do).
        cap: refuse a pure-Python solve above this size rather than hanging.
            Ignored when numpy is available. None disables the guard.

    Raises:
        ValueError: no numpy and the matrix is larger than `cap`.
    """
    n = len(matrix)
    if n == 0:
        return []
    if _np is not None:
        return sorted(float(v) for v in _np.linalg.eigvalsh(_np.array(matrix, dtype=float)))
    if cap is not None and n > cap:
        raise ValueError(
            f"{n}x{n} symmetric eigensolve without numpy would be very slow; "
            f"install the numpy extra or pass cap=None to insist")
    return sorted(_jacobi_eigenvalues(matrix))
