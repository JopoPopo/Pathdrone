import pygame
import random
from sys import exit
from map_Classes import Tile
from map_Classes import Terrain
from map_Classes import Fire
from map_Classes import Drone
from random_gen import noise_map
from pathfinding import path_to_nearest_fire
from resources import place_resources

MAP_ROWS = 20
MAP_COLS = 40
TILE_SIZE = 25

pygame.init()
screen = pygame.display.set_mode((TILE_SIZE * MAP_COLS, TILE_SIZE * MAP_ROWS))
pygame.display.set_caption('Map Gen')
clock = pygame.time.Clock()
fire_font = pygame.font.SysFont("Segoe UI Emoji", TILE_SIZE)

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
noise_Map = noise_map(MAP_COLS, MAP_ROWS, 8, 8, 3)

tile_Map = [
    [Tile(Terrain(tile_decider(row, col, noise_Map)), row, col, 0, 0)
     for col in range(MAP_COLS)]
    for row in range(MAP_ROWS)
]
resources = place_resources(tile_Map)
fire = Fire()
fire.spawn_random_source(tile_Map)   # start with one fire so the drone has a target right away
drone_tile = random.choice([tile for row in tile_Map for tile in row if not tile.fireState])
drone = Drone(drone_tile)


def draw_tile(y, x, tile):
    draw_x = x * TILE_SIZE
    draw_y = y * TILE_SIZE

    tile_Surface.fill(tile_Colors[tile.terrain])
    screen.blit(tile_Surface,(draw_x,draw_y))

    if tile.resource:
        center = (draw_x + TILE_SIZE // 2, draw_y + TILE_SIZE // 2)
        pygame.draw.circle(screen, (255, 255, 255), center, TILE_SIZE // 4)
        pygame.draw.circle(screen, (0, 0, 0), center, TILE_SIZE // 4, 2)

    if tile.fireState:
        # A plain square works on every OS; the fire emoji font only exists on Windows.
        inset = TILE_SIZE // 8
        pygame.draw.rect(
            screen,
            (255, 69, 0),
            (draw_x + inset, draw_y + inset, TILE_SIZE - 2 * inset, TILE_SIZE - 2 * inset),
        )


def draw_drone(drone):
    center_x = drone.col * TILE_SIZE + TILE_SIZE // 2
    center_y = drone.row * TILE_SIZE + TILE_SIZE // 2
    color = (20, 45, 190)
    rotor_offset = TILE_SIZE * 18 // 50
    rotor_radius = max(2, TILE_SIZE * 6 // 50)
    body_radius = max(2, TILE_SIZE * 7 // 50)
    line_width = max(1, TILE_SIZE * 4 // 50)

    for offset_x, offset_y in (
        (-rotor_offset, -rotor_offset),
        (rotor_offset, -rotor_offset),
        (-rotor_offset, rotor_offset),
        (rotor_offset, rotor_offset),
    ):
        rotor_x = center_x + offset_x
        rotor_y = center_y + offset_y
        pygame.draw.line(screen, color, (center_x, center_y), (rotor_x, rotor_y), line_width)
        pygame.draw.circle(screen, color, (rotor_x, rotor_y), rotor_radius, 1)

    pygame.draw.circle(screen, color, (center_x, center_y), body_radius)


def draw_path(path):
    if len(path) < 2:
        return
    half = TILE_SIZE // 2
    points = [(col * TILE_SIZE + half, row * TILE_SIZE + half) for row, col in path]
    pygame.draw.lines(screen, (255, 255, 255), False, points, 2)


def move_drone(drone):
    """Move one tile toward the nearest fire and put it out on arrival.

    The path is recalculated every step, since fires spread and new ones
    appear. Returns the path still ahead, for drawing.
    """
    path = path_to_nearest_fire(tile_Map, (drone.row, drone.col), fire)
    if path is None:
        return []
    if len(path) > 1:
        drone.row, drone.col = path[1]
    tile = tile_Map[drone.row][drone.col]
    if tile.fireState:
        fire.extinguish(tile)
    return path[1:]


drone_path = []
drone_move_timer = 0
DRONE_MOVE_INTERVAL = 250   # ms per tile

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

    drone_move_timer += delta_time
    if drone_move_timer >= DRONE_MOVE_INTERVAL:
        drone_move_timer -= DRONE_MOVE_INTERVAL
        drone_path = move_drone(drone)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            exit()

    for y, row in enumerate(tile_Map):
        for x, item in enumerate(row):
            draw_tile(y, x, item)
    draw_path(drone_path)
    draw_drone(drone)
    pygame.display.update()
