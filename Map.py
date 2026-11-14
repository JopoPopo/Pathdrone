import pygame
import random
from sys import exit
from map_Classes import Tile
from map_Classes import Terrain
from random_gen import noise_map

map_row = 20
map_col = 40
TILE_SIZE = 50

pygame.init()
screen = pygame.display.set_mode((TILE_SIZE * map_col,TILE_SIZE * map_row))
pygame.display.set_caption('Map Gen')
clock = pygame.time.Clock()

tile_Surface = pygame.Surface((TILE_SIZE,TILE_SIZE))



def tile_decider(x,y,noise_Map):

    noise = noise_Map[x][y]
    if noise < .5:
        return 0
    elif noise < .8:
        return 1
    elif noise < 1:
        return 2


tile_Colors = {

    Terrain.GRASS: (124, 252, 0),
    Terrain.WATER: (94, 143, 199),
    Terrain.GRAVEL: (74, 75, 70),
    Terrain.ASH: (178, 190, 181),

}
noise_Map = noise_map(map_col, map_row,8,8,3)

tile_Map = [
    [Tile(Terrain(tile_decider(x,y,noise_Map)),x,y,0,0) for y in range(len(noise_Map[x]))]for x in range(len(noise_Map))
]


def draw_tile(y, x, tile):
    draw_x = x * TILE_SIZE
    draw_y = y * TILE_SIZE

    tile_Surface.fill(tile_Colors[tile.terrain])
    screen.blit(tile_Surface,(draw_x,draw_y))





while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            exit()

    for y, row in enumerate(tile_Map):
        for x, item in enumerate(row):
            draw_tile(y, x, item)
    
    
    
    
    pygame.display.update()
    clock.tick(60)


