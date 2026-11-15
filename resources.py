#Foam depot, trees, bushes and mountains
#Water is not here, the drone refills at the water tiles

import random

from map_Classes import Terrain
from map_Classes import Resource
from random_gen import noise

RESOURCE_SEED = 875
DEPOT_SIZE = 9
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


def distance(tile, center):
    return (tile.row - center.row) ** 2 + (tile.col - center.col) ** 2


def place_resources(tile_Map, seed = RESOURCE_SEED, count = DEPOT_SIZE):
    land_Tiles = get_land(tile_Map)
    if len(land_Tiles) == 0:
        return []

    #same seed picks the same center
    center = random.Random(seed).choice(land_Tiles)

    #take the closest land tile to the center one at a time
    placed = []
    for i in range(min(count, len(land_Tiles))):
        closest = land_Tiles[0]
        for item in land_Tiles:
            if distance(item, center) < distance(closest, center):
                closest = item
        closest.occupant.append(Resource.Foam)
        placed.append(closest)
        land_Tiles.remove(closest)
    return placed


def place_features(tile_Map):
    #run after place_resources so the depot stays clear
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
