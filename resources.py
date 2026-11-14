"""Resource point placement (baseline).

Resource points are where a drone will refill or recharge. Each tile gets
a noise value from random_gen.noise; tiles above RESOURCE_THRESHOLD get a
resource. Water tiles never do.

Resources use their own seed so they don't line up with the terrain, and
the same seed always gives the same placement.
"""

from map_Classes import Terrain
from random_gen import noise

RESOURCE_SEED = 875
RESOURCE_THRESHOLD = 0.97   # higher means fewer resources (about 3% of land tiles)


def place_resources(tile_Map, seed=RESOURCE_SEED, threshold=RESOURCE_THRESHOLD):
    """Mark resource tiles in place and return them as a list."""
    placed = []
    for row in tile_Map:
        for tile in row:
            if tile.terrain == Terrain.WATER:
                continue
            if noise(tile.col, tile.row, seed) > threshold:
                tile.resource = True
                placed.append(tile)
    return placed
