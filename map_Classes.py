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


#how long a tile burns in ms, the burn time is the terrain plus everything on it
terrain_Burn = {

    Terrain.GRASS: 15000,
    Terrain.WATER: 0,
    Terrain.GRAVEL: 8000,
    Terrain.ASH: 0,

}

#0 means it does not burn, so it stays when the tile turns to ash
resource_Burn = {

    Resource.Water: 0,
    Resource.Tree: 15000,
    Resource.Bush: 7500,
    Resource.Mountain: 0,
    Resource.Foam: 0,

}

#chance a tile catches fire from one burning neighbor each spread tick
terrain_Spread = {

    Terrain.GRASS: 0.03,
    Terrain.WATER: 0,
    Terrain.GRAVEL: 0.015,
    Terrain.ASH: 0,

}

#added to the terrain chance when the object is on the tile
resource_Spread = {

    Resource.Water: 0,
    Resource.Tree: 0.03,
    Resource.Bush: 0.02,
    Resource.Mountain: 0,
    Resource.Foam: 0,

}


def spread_chance(tile):
    chance = terrain_Spread[tile.terrain]
    for thing in tile.occupant:
        chance += resource_Spread[thing]
    return chance


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


def burn_time(tile):
    time = terrain_Burn[tile.terrain]
    for thing in tile.occupant:
        time += resource_Burn[thing]
    return time


def can_burn(tile):
    #water and ash have nothing left to burn
    if tile.terrain == Terrain.WATER or tile.terrain == Terrain.ASH:
        return False
    if tile.fireState or is_blocked(tile):
        return False
    return True


class Tile ():
    
    def __init__(self, terrain: Terrain, row, col, occupant, fireState):
        self.terrain = terrain
        self.row = row
        self.col = col
        self.occupant = []
        self.fireState = fireState
        self.burn_left = 0

    def get_neighbors(self):
        print(self.row)


class Fire:

    def __init__(self):
        self.burning_tiles = []

    def ignite(self, tile):
        tile.fireState = True
        tile.burn_left = burn_time(tile)
        self.burning_tiles.append(tile)

    def extinguish(self, tile):
        tile.fireState = False
        tile.burn_left = 0
        if tile in self.burning_tiles:
            self.burning_tiles.remove(tile)

    def burn(self, delta_time):
        #loop over a copy because tiles leave burning_tiles while we loop
        for tile in list(self.burning_tiles):
            tile.burn_left -= delta_time
            if tile.burn_left <= 0:
                self.burn_out(tile)

    def burn_out(self, tile):
        self.extinguish(tile)
        tile.terrain = Terrain.ASH

        #trees and bushes are destroyed, foam and mountains stay
        left = []
        for thing in tile.occupant:
            if resource_Burn[thing] == 0:
                left.append(thing)
        tile.occupant = left

    def spawn_random_source(self, tile_Map):
        flammable_tiles = [
            tile
            for row in tile_Map
            for tile in row
            if can_burn(tile)
        ]
        if flammable_tiles:
            self.ignite(random.choice(flammable_tiles))

    def spread(self, tile_Map):
        #tiles are lit after the loop so a new fire does not spread in the same tick
        new_fires = []

        for tile in self.burning_tiles:
            for row_offset, col_offset in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                neighbor_row = tile.row + row_offset
                neighbor_col = tile.col + col_offset

                if 0 <= neighbor_row < len(tile_Map) and 0 <= neighbor_col < len(tile_Map[neighbor_row]):
                    neighbor = tile_Map[neighbor_row][neighbor_col]
                    if can_burn(neighbor) and neighbor not in new_fires:
                        if random.random() < spread_chance(neighbor):
                            new_fires.append(neighbor)

        for tile in new_fires:
            self.ignite(tile)


#how many tiles one foam puts out at once, the tile and the burning tiles next to it
FOAM_TILES = 3


def foam_group(tile_Map, tile):
    group = [tile]
    for row_offset, col_offset in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        neighbor_row = tile.row + row_offset
        neighbor_col = tile.col + col_offset

        if 0 <= neighbor_row < len(tile_Map) and 0 <= neighbor_col < len(tile_Map[neighbor_row]):
            neighbor = tile_Map[neighbor_row][neighbor_col]
            if neighbor.fireState and len(group) < FOAM_TILES:
                group.append(neighbor)
    return group


class Drone:

    def __init__(self, tile, max_water=1, max_foam=1):
        self.row = tile.row
        self.col = tile.col
        self.max_water = max_water   # fires it can put out before refilling
        self.water = max_water
        self.max_foam = max_foam
        self.foam = 0
