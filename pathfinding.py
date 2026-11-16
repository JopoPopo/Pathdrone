"""Drone pathfinding (baseline).

Breadth-first search over the tile grid, moving up, down, left or right.
It finds the path with the fewest steps to the nearest goal tile.

The drone flies, so every tile is passable except the blocked ones
(mountains). `neighbors` skips those.
"""

from collections import deque

from map_Classes import is_blocked

DIRECTIONS = ((-1, 0), (1, 0), (0, -1), (0, 1))


def neighbors(tile_Map, row, col):
    for d_row, d_col in DIRECTIONS:
        r, c = row + d_row, col + d_col
        if 0 <= r < len(tile_Map) and 0 <= c < len(tile_Map[r]):
            if not is_blocked(tile_Map[r][c]):
                yield r, c


def bfs_path(tile_Map, start, goals, blocked_positions=()):
    """Shortest path from `start` to the nearest of `goals`.

    `start` is a (row, col) pair and `goals` is a collection of them.
    `blocked_positions` contains coordinates occupied by other drones.
    Returns the path as a list of (row, col) from start to goal, both
    included, or None if there are no goals or none can be reached.
    """
    goals = set(goals)
    blocked_positions = set(blocked_positions)
    came_from = {start: None}
    frontier = deque([start])

    while frontier:
        pos = frontier.popleft()
        if pos in goals:
            path = []
            while pos is not None:
                path.append(pos)
                pos = came_from[pos]
            return path[::-1]

        for nxt in neighbors(tile_Map, *pos):
            if nxt not in blocked_positions and nxt not in came_from:
                came_from[nxt] = pos
                frontier.append(nxt)

    return None


def distance_map(tile_Map, sources):
    """Steps from the nearest of `sources` to every reachable tile.

    One BFS that starts from all sources at once. Returns a dict of
    {(row, col): steps}. Useful for asking "how far is every station
    from this fire?" in a single pass.
    """
    dist = {pos: 0 for pos in sources}
    frontier = deque(dist)
    while frontier:
        pos = frontier.popleft()
        for nxt in neighbors(tile_Map, *pos):
            if nxt not in dist:
                dist[nxt] = dist[pos] + 1
                frontier.append(nxt)
    return dist


if __name__ == "__main__":
    # Quick check: run `python pathfinding.py` to see a path on a small grid.
    from map_Classes import Tile, Terrain

    rows, cols = 6, 10
    grid = [[Tile(Terrain.GRASS, r, c, 0, 0) for c in range(cols)] for r in range(rows)]
    start, fires = (5, 0), [(0, 9), (1, 3)]

    path = bfs_path(grid, start, fires)
    print(f"Drone at {start}, fires at {fires}")
    print(f"Path to nearest fire ({len(path) - 1} steps): {path}\n")

    on_path = set(path)
    for r in range(rows):
        line = ""
        for c in range(cols):
            if (r, c) == start:
                line += "D "
            elif (r, c) in fires:
                line += "F "
            elif (r, c) in on_path:
                line += "* "
            else:
                line += ". "
        print(line)
    print("\nD = drone, F = fire, * = path")
