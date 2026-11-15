import pygame
import random
from sys import exit
from map_Classes import Tile
from map_Classes import Terrain
from map_Classes import Fire
from map_Classes import Drone
from map_Classes import Resource
from map_Classes import is_blocked
from random_gen import noise_map
from pathfinding import bfs_path
from resources import place_resources
from resources import place_features
from resources import collect_foam
from textures import make_textures

pygame.init()

#pick the map size here, Small, Medium or Large
MAP_SIZE = "Small"

#rows, cols and the terrain seed for each map size
map_Sizes = {

    "Small": (20, 40, 8),
    "Medium": (30, 60, 13),
    "Large": (40, 80, 13),

}

MAP_ROWS = map_Sizes[MAP_SIZE][0]
MAP_COLS = map_Sizes[MAP_SIZE][1]
MAP_SEED = map_Sizes[MAP_SIZE][2]

#the window should not pass the pixels of the monitor, a little is left for the title bar and taskbar
SCREEN_WIDTH = pygame.display.get_desktop_sizes()[0][0]
SCREEN_HEIGHT = pygame.display.get_desktop_sizes()[0][1]
MAX_WIDTH = SCREEN_WIDTH - 20
MAX_HEIGHT = SCREEN_HEIGHT - 120
LEGEND_WIDTH = 240

#the tiles are as big as the monitor allows, bigger maps get smaller tiles
TILE_SIZE = max(4, min(64, (MAX_WIDTH - LEGEND_WIDTH) // MAP_COLS, MAX_HEIGHT // MAP_ROWS))

#ms between tries to start a new fire, the same on every map size
FIRE_SPAWN_TIME = 3000

MAP_WIDTH = MAP_COLS * TILE_SIZE
MAP_HEIGHT = MAP_ROWS * TILE_SIZE

WINDOW_WIDTH = MAP_WIDTH + LEGEND_WIDTH
WINDOW_HEIGHT = MAP_HEIGHT

screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
pygame.display.set_caption('Map Gen')
clock = pygame.time.Clock()
#the legend fire is a fixed size, so big tiles do not make it cover the text
fire_font = pygame.font.SysFont("Segoe UI Emoji", 25)
legend_title_font = pygame.font.SysFont("Arial", 28, bold=True)
legend_item_font = pygame.font.SysFont("Arial", 20)

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

#the textures are drawn once here, the screen has to be open first
tile_Textures, feature_Textures, fire_Texture = make_textures(TILE_SIZE, tile_Colors)

LEGEND_ITEMS = (
    ("Grass", Terrain.GRASS),
    ("Water", Terrain.WATER),
    ("Gravel", Terrain.GRAVEL),
    ("ASH", Terrain.ASH)
)

LEGEND_BACKGROUND = (35, 38, 45)
LEGEND_BORDER = (160, 165, 175)
DRONE_COLOR = (20, 45, 190)

#seed, scale, octaves
noise_Map = noise_map(MAP_COLS, MAP_ROWS, MAP_SEED, 8, 3)

tile_Map = [
    [Tile(Terrain(tile_decider(row, col, noise_Map)), row, col, 0, 0)
     for col in range(MAP_COLS)]
    for row in range(MAP_ROWS)
]
resources = place_resources(tile_Map)
place_features(tile_Map)

#terrain does not change so we find the water once
water_Tiles = []
for row in tile_Map:
    for item in row:
        if item.terrain == Terrain.WATER:
            water_Tiles.append(item)

fire = Fire()
station_tile = next(
    (tile for row in tile_Map for tile in row if Resource.FireStation in tile.occupant),
    None,
)
drone_tiles = [
    tile for row in tile_Map for tile in row
    if Resource.DronePad in tile.occupant
]
drones = [Drone(tile) for tile in drone_tiles]
fire.spawn_random_source(
    tile_Map,
    excluded={(drone.row, drone.col) for drone in drones},
)  # start with one fire so the drones have a target right away


def draw_tile(y, x, tile):
    draw_x = x * TILE_SIZE
    draw_y = y * TILE_SIZE

    #each terrain has a few textures, the position picks one so the map does not repeat
    versions = tile_Textures[tile.terrain]
    screen.blit(versions[(x * 73856093 + y * 19349663) % len(versions)], (draw_x, draw_y))

    #draw everything in the occupant list
    for thing in tile.occupant:
        if thing in feature_Textures:
            screen.blit(feature_Textures[thing], (draw_x, draw_y))

    if tile.fireState:
        screen.blit(fire_Texture, (draw_x, draw_y))


def draw_drone(drone):
    center_x = drone.col * TILE_SIZE + TILE_SIZE // 2
    center_y = drone.row * TILE_SIZE + TILE_SIZE // 2
    color = DRONE_COLOR
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


PATH_COLORS = {"fire": (255, 255, 255), "refill": (0, 255, 255)}


def draw_path(path, mode):
    if len(path) < 2:
        return
    half = TILE_SIZE // 2
    points = [(col * TILE_SIZE + half, row * TILE_SIZE + half) for row, col in path]
    pygame.draw.lines(screen, PATH_COLORS[mode], False, points, 2)


def choose_goals(drone):
    """Fires if the drone has water; otherwise the nearest water tile.

    It also tops up at water while no fires are burning, so it
    starts the next fire with a full tank.
    """
    fires = [(tile.row, tile.col) for tile in fire.burning_tiles]
    stations = [(tile.row, tile.col) for tile in water_Tiles]
    if drone.water == 0 or (not fires and drone.water < drone.max_water):
        return stations, "refill"
    return fires, "fire"


def move_drone(drone, occupied_positions=()):
    """Take one step toward the current goal, then act on the tile reached.

    The path is recalculated every step, since fires spread and new ones
    appear. Returns the path still ahead and the mode, for drawing.
    """
    goals, mode = choose_goals(drone)
    path = bfs_path(
        tile_Map,
        (drone.row, drone.col),
        goals,
        blocked_positions=occupied_positions,
    )
    if path is None:
        return [], mode
    if len(path) > 1:
        drone.row, drone.col = path[1]

    tile = tile_Map[drone.row][drone.col]
    if tile.fireState and drone.water > 0:
        fire.extinguish(tile)
        drone.water -= 1
    if tile.terrain == Terrain.WATER:
        drone.water = drone.max_water
    collect_foam(tile, station_tile, drone)
    return path[1:], mode


drone_paths = [([], "fire") for drone in drones]
drone_move_timer = 0
DRONE_MOVE_INTERVAL = 250   # ms per tile

fire_spawn_timer = 0
fire_spread_timer = 0
fire_spread_interval = random.randint(5000, 10000)

def draw_legend_panel():
    legend_rect = pygame.Rect(
        MAP_WIDTH,
        0,
        LEGEND_WIDTH,
        WINDOW_HEIGHT
    )

    pygame.draw.rect(screen, LEGEND_BACKGROUND, legend_rect)

    pygame.draw.line(
        screen,
        LEGEND_BORDER,
        (MAP_WIDTH, 0),
        (MAP_WIDTH, WINDOW_HEIGHT),
        2
    )


    item_x = MAP_WIDTH + 20
    item_start_y = 75
    box_size = 20
    row_spacing = 35

    symbol_start_y = item_start_y + len(LEGEND_ITEMS) * row_spacing + 10

    for index, (label, terrain) in enumerate(LEGEND_ITEMS):
        item_y = item_start_y + index * row_spacing

        color_box = pygame.Rect(
            item_x,
            item_y,
            box_size,
            box_size
        )

        pygame.draw.rect(
            screen,
            tile_Colors[terrain],
            color_box
        )

        pygame.draw.rect(
            screen,
            LEGEND_BORDER,
            color_box,
            1
        )

        drone_y = symbol_start_y + 40
        drone_center = (
            item_x + box_size // 2,
            drone_y + box_size // 2
        )

        pygame.draw.circle(
            screen,
            DRONE_COLOR,
            drone_center,
            7
        )

        fire_symbol = fire_font.render(
            "\U0001F525",
            True,
            (255, 100, 20)
        )

        title_surface = legend_title_font.render(
            "LEGEND",
            True,
            (240, 240, 240)
        )

        screen.blit(
            title_surface,
            (MAP_WIDTH + 20, 20)
        )

        item_surface = legend_item_font.render(
            label,
            True,
            (240, 240, 240)
        )

        screen.blit(
            item_surface,
            (item_x + box_size + 12, item_y - 2)
        )

        screen.blit(
            fire_symbol,
            (item_x -2, symbol_start_y-4)
        )

        fire_label = legend_item_font.render(
            "Active Fire",
            True,
            (240, 240, 240)
        )

        screen.blit(
            fire_label,
            (item_x + box_size + 12, symbol_start_y)
        )

        drone_label = legend_item_font.render(
        "Drone",
        True,
        (240, 240, 240)
        )

        screen.blit(
        drone_label,
        (item_x + box_size + 12, drone_y)
        )




while True:
    delta_time = clock.tick(60)
    fire_spawn_timer += delta_time
    if fire_spawn_timer >= FIRE_SPAWN_TIME:
        fire_spawn_timer -= FIRE_SPAWN_TIME
        if random.random() < 0.25:
            fire.spawn_random_source(tile_Map)

    #tiles that burned long enough turn to ash
    fire.burn(delta_time)

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
        drone_paths = []
        for drone in drones:
            occupied_positions = {
                (other.row, other.col) for other in drones if other is not drone
            }
            drone_paths.append(move_drone(drone, occupied_positions))
        water_levels = ", ".join(
            f"{drone.water}/{drone.max_water}" for drone in drones
        )
        station_capacity = station_tile.foam_capacity if station_tile else 0
        pygame.display.set_caption(
            f"Map Gen - water {water_levels} - station foam {station_capacity}"
        )

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            exit()

    for y, row in enumerate(tile_Map):
        for x, item in enumerate(row):
            draw_tile(y, x, item)
    for path, mode in drone_paths:
        draw_path(path, mode)
    for drone in drones:
        draw_drone(drone)
    draw_legend_panel()
    pygame.display.update()
