import pygame
import random
from sys import exit
from map_Classes import Tile
from map_Classes import Terrain
from map_Classes import Fire
from map_Classes import Drone

pygame.init()
screen = pygame.display.set_mode((1200, 800))
pygame.display.set_caption('Map Gen')
clock = pygame.time.Clock()
fire_font = pygame.font.SysFont("Segoe UI Emoji", 56)

tile_Surface = pygame.Surface((100,100))

tile_Colors = {

    Terrain.GRASS: (124, 252, 0),
    Terrain.WATER: (94, 143, 199),
    Terrain.GRAVEL: (74, 75, 70),
    Terrain.ASH: (178, 190, 181),

}

tile_Map = [[0,0,0,0,0,0,0,0,0,0,0,0],
            [0,0,0,0,0,0,0,0,0,0,0,0],
            [0,0,0,0,0,0,0,0,0,0,0,0],
            [0,0,0,0,0,0,0,0,0,0,0,0],
            [0,0,0,0,0,0,0,0,0,0,0,0],
            [0,0,0,0,0,0,0,0,0,0,0,0],
            [0,0,0,0,0,0,0,0,0,0,0,0],
            [0,0,0,0,0,0,0,0,0,0,0,0],]

for row in range(len(tile_Map)):
    for item in range (len(tile_Map[row])):
        tile_Map[row][item] = Tile(Terrain(random.randint(0,len(Terrain)-1)), row, item, random.randint(0,1), 0)

fire = Fire()
drone_tile = random.choice([tile for row in tile_Map for tile in row if not tile.fireState])
drone = Drone(drone_tile)


def draw_tile(tile):
    draw_x = tile.col * 100
    draw_y = tile.row * 100

    tile_Surface.fill(tile_Colors[tile.terrain])
    screen.blit(tile_Surface,(draw_x,draw_y))

    if tile.fireState:
        fire_emoji = fire_font.render("\U0001F525", True, (255, 100, 20))
        screen.blit(fire_emoji, fire_emoji.get_rect(center=(draw_x + 50, draw_y + 50)))


def draw_drone(drone):
    center_x = drone.col * 100 + 50
    center_y = drone.row * 100 + 50
    color = (20, 45, 190)

    for offset_x, offset_y in ((-18, -18), (18, -18), (-18, 18), (18, 18)):
        rotor_x = center_x + offset_x
        rotor_y = center_y + offset_y
        pygame.draw.line(screen, color, (center_x, center_y), (rotor_x, rotor_y), 4)
        pygame.draw.circle(screen, color, (rotor_x, rotor_y), 6, 2)

    pygame.draw.circle(screen, color, (center_x, center_y), 7)


fire_spawn_timer = 0
fire_spread_timer = 0
fire_spread_interval = random.randint(5000, 10000)

while True:
    delta_time = clock.tick(60)
    fire_spawn_timer += delta_time
    if fire_spawn_timer >= 3000:
        fire_spawn_timer -= 3000
        if random.random() < 0.25:
            fire.spawn_random_source(tile_Map)

    if fire.burning_tiles:
        fire_spread_timer += delta_time
        if fire_spread_timer >= fire_spread_interval:
            fire.spread(tile_Map)
            fire_spread_timer = 0
            fire_spread_interval = random.randint(5000, 10000)
    else:
        fire_spread_timer = 0

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            exit()

    for row in tile_Map:
        for item in row:
            draw_tile(item)

    draw_drone(drone)
    pygame.display.update()
