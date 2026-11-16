"""Drone decision algorithms.

Each algorithm answers one question every step: "where should the drone
go next?" They all have the same shape:

    algo = SomeAlgorithm(tile_Map, water_Tiles)
    path, mode = algo.next_path(drone, fire.burning_tiles)

`path` is a list of (row, col) starting at the drone, and `mode` is
"fire", "refill" or "home" (used for the path color).

To add a new algorithm, write a class like the ones below and add it to
ALGORITHMS at the bottom of this file.
"""

from map_Classes import Terrain, Resource, can_burn, is_blocked, tile_value, foam_group
from pathfinding import bfs_path, distance_map, neighbors


def _positions(tiles):
    return [(tile.row, tile.col) for tile in tiles]


class NearestFirst:
    """Baseline: always go to the closest fire, refill at the closest water."""

    name = "Nearest first"

    def __init__(self, tile_Map, water_Tiles):
        self.tile_Map = tile_Map
        self.stations = _positions(water_Tiles)

    def next_path(self, drone, burning_tiles):
        fires = _positions(burning_tiles)
        start = (drone.row, drone.col)
        if drone.water == 0 or (not fires and drone.water < drone.max_water):
            return bfs_path(self.tile_Map, start, self.stations) or [], "refill"
        return bfs_path(self.tile_Map, start, fires) or [], "fire"


# ---- Priority planner ------------------------------------------------------

SWITCH_RATIO = 2.0   # how much more urgent another fire must be to switch to it
DISTANCE_BIAS = 5    # keeps very close fires from getting a huge score
AGE_STEPS = 40       # every 40 drone steps (10 s) burning adds +1 urgency


class PriorityPlanner:
    """Fixes the baseline's weak spots.

    1. Worst fire first. Burning tiles that touch form one fire (a
       "cluster"). Each cluster is scored by how much it can still burn:
       the value of the unburnt tiles right next to it (grass, trees,
       bushes), plus a bonus for how long it has been burning. That is
       divided by how far away it is, so a big fire a bit further away
       beats a tiny one next door.
    2. No changing its mind. It sticks with a fire until it's out, unless
       another becomes SWITCH_RATIO times more urgent.
    3. No forgotten fires. The age bonus keeps growing, so far-away fires
       eventually become the top priority.
    4. Smarter refills. With no water, it picks the water tile with the
       shortest total trip: drone -> water -> fire. With no fires, it
       waits at the most central water tile.

    Inside a fire it goes for the edge tiles first, since those are the
    ones the fire spreads from.
    """

    name = "Priority planner"

    def __init__(self, tile_Map, water_Tiles):
        self.tile_Map = tile_Map
        self.stations = _positions(water_Tiles)
        self.home = self._central_station()
        self.target = None    # set of (row, col) of the fire we committed to
        self.station = None   # water tile we committed to
        self.step = 0
        self.first_seen = {}  # (row, col) -> step it was first seen burning

    def next_path(self, drone, burning_tiles):
        self.step += 1
        burning = set(_positions(burning_tiles))
        self.first_seen = {pos: self.first_seen.get(pos, self.step) for pos in burning}
        start = (drone.row, drone.col)

        if drone.water > 0:
            self.station = None

        self._choose_target(self._clusters(burning), start, burning, drone.water > 0)

        if self.target is None:
            # Nothing burning: refill if needed, then wait at the central water.
            if self.home is None:
                return [], "home"
            path = bfs_path(self.tile_Map, start, [self.home]) or []
            return path, "refill" if drone.water < drone.max_water else "home"

        if drone.water == 0:
            if self.station is None and self.stations:
                to_fire = distance_map(self.tile_Map, self.target)
                from_drone = distance_map(self.tile_Map, [start])
                self.station = min(
                    self.stations,
                    key=lambda s: from_drone.get(s, float("inf")) + to_fire.get(s, float("inf")),
                )
            if self.station is None:
                return [], "refill"
            return bfs_path(self.tile_Map, start, [self.station]) or [], "refill"

        edges = [pos for pos in self.target if self._at_risk(pos, burning)]
        return bfs_path(self.tile_Map, start, edges or self.target) or [], "fire"

    def _choose_target(self, clusters, start, burning, has_water):
        """Keep the current fire unless another one is much more urgent."""
        if not clusters:
            self.target = None
            return

        current = None
        if self.target:
            current = next((c for c in clusters if c & self.target), None)

        from_drone = distance_map(self.tile_Map, [start])
        scored = [(self._urgency(c, from_drone, burning, has_water), c) for c in clusters]
        best_score, best = max(scored, key=lambda item: item[0])
        if current is None:
            self.target = best
            return

        current_score = next(score for score, c in scored if c is current)
        if best_score > SWITCH_RATIO * current_score:
            self.target = best
            self.station = None
        else:
            self.target = current   # follow it as it grows or shrinks

    def _urgency(self, cluster, from_drone, burning, has_water):
        at_risk = set()
        for pos in cluster:
            at_risk.update(self._at_risk(pos, burning))
        value = sum(tile_value(self.tile_Map[r][c]) for r, c in at_risk)
        oldest = min(self.first_seen[pos] for pos in cluster)
        danger = value + 1 + (self.step - oldest) / AGE_STEPS

        if has_water or not self.stations:
            trip = min(from_drone.get(pos, float("inf")) for pos in cluster)
        else:
            # Without water, the real cost is the trip through a water tile.
            dist = distance_map(self.tile_Map, cluster)
            trip = min(from_drone.get(s, float("inf")) + dist.get(s, float("inf"))
                       for s in self.stations)
        return danger / (trip + DISTANCE_BIAS)

    def _clusters(self, burning):
        """Group burning tiles that touch (up/down/left/right) into fires."""
        clusters, seen = [], set()
        for pos in burning:
            if pos in seen:
                continue
            cluster, stack = set(), [pos]
            seen.add(pos)
            while stack:
                cur = stack.pop()
                cluster.add(cur)
                for nxt in neighbors(self.tile_Map, *cur):
                    if nxt in burning and nxt not in seen:
                        seen.add(nxt)
                        stack.append(nxt)
            clusters.append(cluster)
        return clusters

    def _at_risk(self, pos, burning):
        """Unburnt neighbors this burning tile could spread to."""
        risky = []
        for r, c in neighbors(self.tile_Map, *pos):
            if (r, c) not in burning and can_burn(self.tile_Map[r][c]):
                risky.append((r, c))
        return risky

    def _central_station(self):
        """Water tile with the smallest total distance to all land tiles."""
        if not self.stations:
            return None
        land = [(t.row, t.col) for row in self.tile_Map for t in row
                if t.terrain != Terrain.WATER and not is_blocked(t)]

        def total(station):
            dist = distance_map(self.tile_Map, [station])
            return sum(dist.get(pos, 10_000) for pos in land)

        return min(self.stations, key=total)


# ---- Greedy ratio ----------------------------------------------------------

#steps it takes to put a fire out, so the cost is never 0 even when the drone is on the fire
EXTINGUISH_STEPS = 1


class GreedyRatio:
    #every step the drone scores its options and does the best one
    #score = what we save / time it takes, benefit over cost
    #benefit = the value of the tile + the value of the tiles it could spread to
    #cost = steps to get there + steps to put it out
    #foam puts out a group of tiles at once so its benefit is the whole group
    #it never plans ahead, it only picks the best choice right now, that is what greedy means
    #the team is shared by all the drones, each drone writes what it is going for there
    #so the other drones leave those tiles alone

    name = "Greedy ratio"

    def __init__(self, tile_Map, water_Tiles):
        self.tile_Map = tile_Map
        self.stations = _positions(water_Tiles)

        #Map.py gives all the drones the same team, alone it just has its own
        self.team = {}

    def next_path(self, drone, burning_tiles):
        start = (drone.row, drone.col)
        me = id(drone)
        self.team[me] = set()

        #what the other drones are already going for
        taken = set()
        for other in self.team:
            if other != me:
                taken = taken | self.team[other]

        #one search from the drone gives the steps to every tile
        from_drone = distance_map(self.tile_Map, [start])

        #the closest foam we could go and get
        dot = None
        from_dot = {}
        if drone.foam < drone.max_foam:
            dot = self.closest_foam(from_drone, taken)
        if dot is not None:
            from_dot = distance_map(self.tile_Map, [dot])

        best_score = -1
        best_goal = None
        best_mode = "fire"
        best_claim = set()

        for tile in burning_tiles:
            spot = (tile.row, tile.col)
            if spot in taken or spot not in from_drone:
                continue

            #the tiles one foam would put out, without the ones another drone has
            group = []
            for item in foam_group(self.tile_Map, tile):
                if (item.row, item.col) not in taken:
                    group.append(item)

            water_benefit = self.benefit(tile)
            foam_benefit = 0
            group_spots = set()
            for item in group:
                foam_benefit += self.benefit(item)
                group_spots.add((item.row, item.col))

            #option 1, fight with what the drone carries
            if drone.foam > 0 and len(group) > 1:
                score = foam_benefit / (from_drone[spot] + EXTINGUISH_STEPS)
                if score > best_score:
                    best_score = score
                    best_goal = spot
                    best_mode = "fire"
                    best_claim = group_spots
            elif drone.water > 0:
                score = water_benefit / (from_drone[spot] + EXTINGUISH_STEPS)
                if score > best_score:
                    best_score = score
                    best_goal = spot
                    best_mode = "fire"
                    best_claim = {spot}

            #option 2, go and get foam first, only worth it if the foam puts out a group
            if dot is not None and len(group) > 1 and spot in from_dot:
                trip = from_drone[dot] + from_dot[spot] + EXTINGUISH_STEPS
                score = foam_benefit / trip
                if score > best_score:
                    best_score = score
                    best_goal = dot
                    best_mode = "foam"
                    best_claim = group_spots | {dot}

        if best_goal is None:
            #nothing to fight with or nothing to fight, so fill the tank
            if drone.water < drone.max_water:
                return bfs_path(self.tile_Map, start, self.stations) or [], "refill"
            return [], "fire"

        self.team[me] = best_claim
        return bfs_path(self.tile_Map, start, [best_goal]) or [], best_mode

    def benefit(self, tile):
        #the tile and the tiles next to it that can still burn
        return tile_value(tile) + self.spread_value(tile)

    def spread_value(self, tile):
        #the value of the tiles next to this fire that can still burn
        value = 0
        for row, col in neighbors(self.tile_Map, tile.row, tile.col):
            neighbor = self.tile_Map[row][col]
            if can_burn(neighbor):
                value += tile_value(neighbor)
        return value

    def closest_foam(self, from_drone, taken):
        #the foam the drone can reach in the fewest steps, that no other drone is going for
        closest = None
        for row in self.tile_Map:
            for item in row:
                spot = (item.row, item.col)
                if Resource.Foam in item.occupant and spot not in taken and spot in from_drone:
                    if closest is None or from_drone[spot] < from_drone[closest]:
                        closest = spot
        return closest


# Name shown in the game -> class. Order here is the order of the buttons.
ALGORITHMS = {
    "nearest": NearestFirst,
    "priority": PriorityPlanner,
    "ratio": GreedyRatio,
}
