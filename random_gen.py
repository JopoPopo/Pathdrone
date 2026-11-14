"""Seeded random noise for deciding where things go on a grid.

This module doesn't create or change the grid. It only gives a number
from 0 to 1 for any (x, y) cell. Whoever builds the grid uses those
numbers to decide what goes where, for example:

    for x in range(width):
        for y in range(height):
            if noise(x, y, seed=1) > 0.75:
                ...  # put an obstacle here

    fire_map = noise_map(width, height, seed=2, scale=4)

The same (x, y, seed) always gives the same value, so a map can be
recreated from its seed. Use a different seed for each kind of thing
(fires, obstacles, resources) so they don't line up.
"""

import math


def _hash(ix, iy, seed):
    """Deterministic pseudo-random value in [0, 1) for an integer point."""
    h = (ix * 374761393 + iy * 668265263 + seed * 2246822519) & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    h ^= h >> 16
    return h / 4294967296.0


def _smooth(t):
    """Smoothstep curve, so values blend without hard edges."""
    return t * t * (3 - 2 * t)


def _value_noise(x, y, seed):
    """Smooth noise from blending random values at the four corners."""
    x0, y0 = math.floor(x), math.floor(y)
    tx, ty = _smooth(x - x0), _smooth(y - y0)

    a = _hash(x0, y0, seed)
    b = _hash(x0 + 1, y0, seed)
    c = _hash(x0, y0 + 1, seed)
    d = _hash(x0 + 1, y0 + 1, seed)

    top = a + (b - a) * tx
    bottom = c + (d - c) * tx
    return top + (bottom - top) * ty


def noise(x, y, seed=0, scale=1.0, octaves=1):
    """Return a random value from 0 to 1 for cell (x, y).

    Args:
        x, y: Cell coordinates (ints or floats).
        seed: Change this to get a completely different pattern.
        scale: Size of the "blobs" in cells. With 1 (the default), every
            cell is independent, like pure random noise. With larger
            values (like 4 or 8), nearby cells get similar values, so
            things cluster, e.g. a patch of fires or a stretch of terrain.
        octaves: Number of noise layers stacked together. More layers add
            finer detail on top of the big blobs. 1 is fine for most uses.
    """
    if scale <= 0:
        raise ValueError("scale must be > 0")
    if octaves < 1:
        raise ValueError("octaves must be >= 1")

    if scale == 1 and octaves == 1:
        return _hash(int(x), int(y), seed)

    total, amplitude, frequency, max_total = 0.0, 1.0, 1.0 / scale, 0.0
    for i in range(octaves):
        total += amplitude * _value_noise(x * frequency, y * frequency, seed + i)
        max_total += amplitude
        amplitude *= 0.5
        frequency *= 2
    return total / max_total


def noise_map(width, height, seed=0, scale=1.0, octaves=1):
    """Return a height x width list of noise values (map[y][x])."""
    return [[noise(x, y, seed, scale, octaves) for x in range(width)]
            for y in range(height)]
