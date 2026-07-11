"""Canonical Gray-coding helpers.

Convention (shared by every encoder in plugins/): the band index is the
HIGHEST band whose threshold is <= value; bands are sorted ascending and
usually start at 0.0.
"""


def gray_bits(value, bands, n_bits=3):
    """Gray-coded band index of `value` against sorted `bands` thresholds."""
    idx = 0
    for i, th in enumerate(bands):
        if value >= th:
            idx = i
    g = idx ^ (idx >> 1)
    return format(g, f"0{n_bits}b")


def gray_to_index(bits):
    """Decode a Gray-coded bitstring back to its band index."""
    g = int(bits, 2)
    idx = g
    while g:
        g >>= 1
        idx ^= g
    return idx
