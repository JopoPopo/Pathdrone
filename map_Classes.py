from enum import Enum
import random

class Resource (Enum):
    Water = 0
    Tree = 1
    Bush = 2
    Mountain = 3
    Foam = 4


class Terrain (Enum):
    GRASS = 0
    WATER = 1
    GRAVEL = 2
    ASH = 3


#how much a tile is worth saving the tile value is the terrain plus everything on it
terrain_Values = {

    Terrain.GRASS: 1.0,
    Terrain.WATER: 0,
    Terrain.GRAVEL: 0.5,
    Terrain.ASH: 0,

}

resource_Values = {

    Resource.Water: 0,
    Resource.Tree: 0.5,
    Resource.Bush: 0.25,
    Resource.Mountain: 0,
    Resource.Foam: 0,

}

#True means the drone cannot go through it and fire cannot burn it
resource_Blocks = {

    Resource.Water: False,
    Resource.Tree: False,
    Resource.Bush: False,
    Resource.Mountain: True,
    Resource.Foam: False,

}


def tile_value(tile):
    value = terrain_Values[tile.terrain]
    for thing in tile.occupant:
        value += resource_Values[thing]
    return value


def is_blocked(tile):
    for thing in tile.occupant:
        if resource_Blocks[thing]:
            return True
    return False


class Tile ():
    
    def __init__(self, terrain: Terrain, row, col, occupant, fireState):
        self.terrain = terrain
        self.row = row
        self.col = col
        self.occupant = []
        self.fireState = fireState

    def get_neighbors(self):
        print(self.row)


class Fire:

    def __init__(self):
        self.burning_tiles = []

    def ignite(self, tile):
        tile.fireState = True
        self.burning_tiles.append(tile)

    def extinguish(self, tile):
        tile.fireState = False
        if tile in self.burning_tiles:
            self.burning_tiles.remove(tile)

    def spawn_random_source(self, tile_Map):
        flammable_tiles = [
            tile
            for row in tile_Map
            for tile in row
            if tile.terrain != Terrain.WATER and not tile.fireState and not is_blocked(tile)
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
                    if neighbor.terrain != Terrain.WATER and not neighbor.fireState and not is_blocked(neighbor):
                        neighbors.append(neighbor)

            if neighbors:
                possible_spreads.append((tile, neighbors))

        if possible_spreads:
            source, neighbors = random.choice(possible_spreads)
            self.ignite(random.choice(neighbors))


class Drone:

    def __init__(self, tile, max_water=1, max_foam=1):
        self.row = tile.row
        self.col = tile.col
        self.max_water = max_water   # fires it can put out before refilling
        self.water = max_water
        self.max_foam = max_foam
        self.foam = 0
