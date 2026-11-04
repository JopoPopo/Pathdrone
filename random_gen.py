"""Generic random placement for a grid.

The grid is a 2D list (grid[row][col]). Empty cells are None by default.
`place_random` drops "things" into random cells. What a thing is depends
on what you plug in: a plain value, an object, or a factory function.

Example:
    grid = [[None] * 10 for _ in range(10)]
    place_random(grid, "OBSTACLE", count=15)
    place_random(grid, lambda r, c: Fire(r, c), density=0.05)
    place_random(grid, "RESOURCE", count=3, seed=42)
"""

import random


def place_random(grid, item, count=None, density=None,
                 can_place=None, rng=None, seed=None):
    """Place `item` into randomly chosen cells of `grid`.

    Args:
        grid: 2D list, modified in place.
        item: What to place. A callable is invoked as item(row, col)
            for each cell, so every placement can be a new object.
            Anything else is placed as-is.
        count: Exact number of cells to fill.
        density: Fraction (0-1) of eligible cells to fill. Use either
            count or density, not both.
        can_place: Optional function (grid, row, col) -> bool that says
            whether a cell is eligible. The default only allows cells
            that are None.
        rng: Optional random.Random instance to use.
        seed: Optional seed, used only if rng is not given, so results
            are reproducible.

    Returns:
        A list of (row, col) positions that were filled.
        If fewer cells are eligible than requested, it fills all of them.
    """
    if (count is None) == (density is None):
        raise ValueError("Pass exactly one of count or density")
    if density is not None and not 0 <= density <= 1:
        raise ValueError("density must be between 0 and 1")
    if count is not None and count < 0:
        raise ValueError("count must be >= 0")

    if rng is None:
        rng = random.Random(seed)
    if can_place is None:
        can_place = lambda g, r, c: g[r][c] is None

    candidates = [
        (r, c)
        for r in range(len(grid))
        for c in range(len(grid[r]))
        if can_place(grid, r, c)
    ]

    n = count if count is not None else round(len(candidates) * density)
    n = min(n, len(candidates))

    chosen = rng.sample(candidates, n)
    for r, c in chosen:
        grid[r][c] = item(r, c) if callable(item) else item
    return chosen
