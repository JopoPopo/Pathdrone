from enum import Enum
import random

class Terrain (Enum):
    GRASS = 0
    WATER = 1
    GRAVEL = 2
    ASH = 3


class Tile ():
    
    def __init__(self, terrain: Terrain, row, col, occupant, fireState):
        self.terrain = terrain
        self.row = row
        self.col = col
        self.occupant = occupant
        self.fireState = fireState

    def get_neighbors(self):
        print(self.row)


class Fire:

    def __init__(self):
        self.burning_tiles = []

    def ignite(self, tile):
        tile.fireState = True
        self.burning_tiles.append(tile)

    def spawn_random_source(self, tile_Map):
        flammable_tiles = [
            tile
            for row in tile_Map
            for tile in row
            if tile.terrain != Terrain.WATER and not tile.fireState
        ]
        if flammable_tiles:
            self.ignite(random.choice(flammable_tiles))

    def spread(self, tile_Map):
        possible_spreads = []

        for tile in self.burning_tiles:
            neighbors = []
            for row_offset, col_offset in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                neighbor_row = tile.row + row_offset
                neighbor_col = tile.col + col_offset

                if 0 <= neighbor_row < len(tile_Map) and 0 <= neighbor_col < len(tile_Map[neighbor_row]):
                    neighbor = tile_Map[neighbor_row][neighbor_col]
                    if neighbor.terrain != Terrain.WATER and not neighbor.fireState:
                        neighbors.append(neighbor)

            if neighbors:
                possible_spreads.append((tile, neighbors))

        if possible_spreads:
            source, neighbors = random.choice(possible_spreads)
            self.ignite(random.choice(neighbors))


class Drone:

    def __init__(self, tile):
        self.row = tile.row
        self.col = tile.col
