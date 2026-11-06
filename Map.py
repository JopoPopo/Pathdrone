import pygame
import random
from sys import exit
from map_Classes import Tile
from map_Classes import Terrain

pygame.init()
screen = pygame.display.set_mode((500,400))
pygame.display.set_caption('Map Gen')
clock = pygame.time.Clock()

tile_Surface = pygame.Surface((100,100))




tile_Colors = {

    Terrain.GRASS: (124, 252, 0),
    Terrain.WATER: (94, 143, 199),
    Terrain.GRAVEL: (74, 75, 70),
    Terrain.ASH: (178, 190, 181),

}

tile_Map = [[0,0,0,0,0],
            [0,0,0,0,0],
            [0,0,0,0,0],
            [0,0,0,0,0],]

for row in range(len(tile_Map)):
    for item in range (len(tile_Map[row])):
        tile_Map[row][item] = Tile(Terrain(random.randint(0,len(Terrain)-1)), row, item, random.randint(0,1), random.randint(0,1))

def draw_tile(tile):
    draw_x = tile.col * 100
    draw_y = tile.row * 100

    tile_Surface.fill(tile_Colors[tile.terrain])
    screen.blit(tile_Surface,(draw_x,draw_y))





while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            exit()

    for row in tile_Map:
        for item in row:
            draw_tile(item)
    
    
    
    
    pygame.display.update()
    clock.tick(60)


