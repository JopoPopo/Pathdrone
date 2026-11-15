import pygame
import random
from sys import exit
from map_Classes import Tile
from map_Classes import Terrain
from map_Classes import Fire
from map_Classes import Drone
from random_gen import noise_map

MAP_ROWS = 20
MAP_COLS = 40
TILE_SIZE = 25

MAP_WIDTH = MAP_COLS * TILE_SIZE
MAP_HEIGHT = MAP_ROWS * TILE_SIZE
LEGEND_WIDTH = 240

WINDOW_WIDTH = MAP_WIDTH + LEGEND_WIDTH
WINDOW_HEIGHT = MAP_HEIGHT

pygame.init()
screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
pygame.display.set_caption('Map Gen')
clock = pygame.time.Clock()
fire_font = pygame.font.SysFont("Segoe UI Emoji", TILE_SIZE)
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
LEGEND_ITEMS = (
    ("Grass", Terrain.GRASS),
    ("Water", Terrain.WATER),
    ("Gravel", Terrain.GRAVEL),
    ("ASH", Terrain.ASH)
)

LEGEND_BACKGROUND = (35, 38, 45)
LEGEND_BORDER = (160, 165, 175)
DRONE_COLOR = (20, 45, 190)

noise_Map = noise_map(MAP_COLS, MAP_ROWS, 8, 8, 3)

tile_Map = [
    [Tile(Terrain(tile_decider(row, col, noise_Map)), row, col, 0, 0)
     for col in range(MAP_COLS)]
    for row in range(MAP_ROWS)
]
fire = Fire()
drone_tile = random.choice([tile for row in tile_Map for tile in row if not tile.fireState])
drone = Drone(drone_tile)


def draw_tile(y, x, tile):
    draw_x = x * TILE_SIZE
    draw_y = y * TILE_SIZE

    tile_Surface.fill(tile_Colors[tile.terrain])
    screen.blit(tile_Surface,(draw_x,draw_y))

    if tile.fireState:
        fire_emoji = fire_font.render("\U0001F525", True, (255, 100, 20))
        screen.blit(
            fire_emoji,
            fire_emoji.get_rect(center=(draw_x + TILE_SIZE // 2, draw_y + TILE_SIZE // 2)),
        )


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

    for y, row in enumerate(tile_Map):
        for x, item in enumerate(row):
            draw_tile(y, x, item)
    draw_drone(drone)
    draw_legend_panel()
    pygame.display.update()
