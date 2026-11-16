#Foam depot, trees, bushes and mountains
#Water is not here, the drone refills at the water tiles

import random

from map_Classes import Terrain
from map_Classes import Resource
from random_gen import noise

DEPOT_SIZE = 4
STATION_FOAM_CAPACITY = 20
RESOURCE_SEED = 875
CARDINAL_DIRECTIONS = ((-1, 0), (1, 0), (0, -1), (0, 1))
DIAGONAL_DIRECTIONS = ((-1, -1), (-1, 1), (1, -1), (1, 1))
FEATURE_SCALE = 6

#share is the part of the land tiles the object covers, mountain goes first
feature_Shares = {
    Resource.Mountain: 0.04,
    Resource.Tree: 0.10,
    Resource.Bush: 0.08,
}

#each object has its own seed so the patterns dont line up
feature_Seeds = {
    Resource.Mountain: 303,
    Resource.Tree: 101,
    Resource.Bush: 202,
}


def get_land(tile_Map):
    land_Tiles = []
    for row in tile_Map:
        for item in row:
            if item.terrain != Terrain.WATER:
                land_Tiles.append(item)
    return land_Tiles


def place_resources(tile_Map, seed=None, count=DEPOT_SIZE):
    land_Tiles = get_land(tile_Map)
    if not land_Tiles:
        return []

    station_options = []
    for center in land_Tiles:
        adjacent = []
        diagonals = []
        for directions, tiles in (
            (CARDINAL_DIRECTIONS, adjacent),
            (DIAGONAL_DIRECTIONS, diagonals),
        ):
            for row_offset, col_offset in directions:
                row = center.row + row_offset
                col = center.col + col_offset
                if 0 <= row < len(tile_Map) and 0 <= col < len(tile_Map[row]):
                    tiles.append(tile_Map[row][col])

        if (len(adjacent) == len(CARDINAL_DIRECTIONS)
                and len(diagonals) == len(DIAGONAL_DIRECTIONS)
                and all(tile.terrain != Terrain.WATER for tile in adjacent + diagonals)):
            station_options.append((center, adjacent, diagonals))

    if not station_options:
        return []

    chooser = random if seed is None else random.Random(seed)
    center, depot_Tiles, drone_Tiles = chooser.choice(station_options)
    center.occupant.append(Resource.FireStation)
    center.foam_capacity = STATION_FOAM_CAPACITY

    placed = []
    for tile in depot_Tiles[:count]:
        tile.occupant.append(Resource.Foam)
        placed.append(tile)
    for tile in drone_Tiles:
        tile.occupant.append(Resource.DronePad)
    return placed


def collect_foam(tile, station, drone):
    if Resource.Foam not in tile.occupant or drone.foam >= drone.max_foam:
        return False

    tile.occupant.remove(Resource.Foam)
    drone.foam += 1
    if station is not None and station.foam_capacity > 0:
        tile.occupant.append(Resource.Foam)
        station.foam_capacity -= 1
    return True


def place_features(tile_Map):
    #Keep the station, supply tiles, and drone pads clear.
    land_Tiles = get_land(tile_Map)
    placed = []

    for kind in feature_Shares:
        free_Tiles = []
        noise_Values = []
        for item in land_Tiles:
            if len(item.occupant) == 0:
                free_Tiles.append(item)
                noise_Values.append(noise(item.col, item.row, feature_Seeds[kind], FEATURE_SCALE))

        how_many = int(feature_Shares[kind] * len(land_Tiles))
        if how_many == 0 or how_many > len(free_Tiles):
            continue

        #the cutoff is the lowest noise value that still makes the share
        sorted_Values = sorted(noise_Values, reverse = True)
        cutoff = sorted_Values[how_many - 1]

        for i in range(len(free_Tiles)):
            if noise_Values[i] >= cutoff:
                free_Tiles[i].occupant.append(kind)
                placed.append(free_Tiles[i])
    return placed
