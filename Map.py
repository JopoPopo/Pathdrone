import argparse
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
from algorithms import ALGORITHMS
from resources import place_resources
from resources import place_features

# Pick the starting algorithm with: python Map.py --algorithm priority
# You can also switch while it runs: click a button in the panel, or press 1 / 2.
parser = argparse.ArgumentParser(description="Drone fire simulation")
parser.add_argument("--algorithm", choices=list(ALGORITHMS), default="priority",
                    help="which drone algorithm to start with")
args = parser.parse_args()

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
resources = place_resources(tile_Map)
place_features(tile_Map)

feature_Colors = {

    Resource.Tree: (0, 90, 20),
    Resource.Bush: (85, 107, 47),
    Resource.Mountain: (150, 150, 150),

}

#terrain does not change so we find the water once
water_Tiles = []
for row in tile_Map:
    for item in row:
        if item.terrain == Terrain.WATER:
            water_Tiles.append(item)

fire = Fire()
fire.spawn_random_source(tile_Map)   # start with one fire so the drone has a target right away
drone_tile = random.choice([tile for row in tile_Map for tile in row if not tile.fireState and not is_blocked(tile)])
drone = Drone(drone_tile)


def set_algorithm(key):
    """Switch the drone's brain. The new algorithm starts with a clean slate."""
    global algorithm_key, algorithm
    algorithm_key = key
    algorithm = ALGORITHMS[key](tile_Map, water_Tiles)


set_algorithm(args.algorithm)


def draw_tile(y, x, tile):
    draw_x = x * TILE_SIZE
    draw_y = y * TILE_SIZE

    tile_Surface.fill(tile_Colors[tile.terrain])
    screen.blit(tile_Surface,(draw_x,draw_y))

    center = (draw_x + TILE_SIZE // 2, draw_y + TILE_SIZE // 2)

    #draw everything in the occupant list
    for thing in tile.occupant:
        if thing == Resource.Foam:
            pygame.draw.circle(screen, (255, 255, 255), center, TILE_SIZE // 4)
            pygame.draw.circle(screen, (0, 0, 0), center, TILE_SIZE // 4, 2)
        elif thing == Resource.Tree:
            pygame.draw.circle(screen, feature_Colors[thing], center, TILE_SIZE // 3)
        elif thing == Resource.Bush:
            pygame.draw.circle(screen, feature_Colors[thing], center, TILE_SIZE // 5)
        elif thing == Resource.Mountain:
            edge = TILE_SIZE // 8
            triangle = [
                (center[0], draw_y + edge),
                (draw_x + edge, draw_y + TILE_SIZE - edge),
                (draw_x + TILE_SIZE - edge, draw_y + TILE_SIZE - edge),
            ]
            pygame.draw.polygon(screen, feature_Colors[thing], triangle)
            pygame.draw.polygon(screen, (40, 40, 40), triangle, 2)

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


PATH_COLORS = {"fire": (255, 255, 255), "refill": (0, 255, 255), "home": (120, 120, 120)}


def draw_path(path, mode):
    if len(path) < 2:
        return
    half = TILE_SIZE // 2
    points = [(col * TILE_SIZE + half, row * TILE_SIZE + half) for row, col in path]
    pygame.draw.lines(screen, PATH_COLORS[mode], False, points, 2)


def move_drone(drone):
    """Take one step toward the current goal, then act on the tile reached.

    The path is recalculated every step, since fires spread and new ones
    appear. Returns the path still ahead and the mode, for drawing.
    """
    path, mode = algorithm.next_path(drone, fire.burning_tiles)
    if not path:
        return [], mode
    if len(path) > 1:
        drone.row, drone.col = path[1]

    tile = tile_Map[drone.row][drone.col]
    if tile.fireState and drone.water > 0:
        fire.extinguish(tile)
        drone.water -= 1
    if tile.terrain == Terrain.WATER:
        drone.water = drone.max_water
    if Resource.Foam in tile.occupant and drone.foam < drone.max_foam:
        tile.occupant.remove(Resource.Foam)
        drone.foam += 1
    return path[1:], mode


drone_path, drone_mode = [], "fire"
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



# ---- algorithm picker (bottom of the side panel) ---------------------------

BUTTON_HEIGHT = 34
BUTTON_GAP = 8
BUTTON_ACTIVE = (70, 130, 220)
BUTTON_IDLE = (60, 64, 74)
PICKER_TOP = WINDOW_HEIGHT - 30 - len(ALGORITHMS) * (BUTTON_HEIGHT + BUTTON_GAP) - 34


def algorithm_buttons():
    """(key, rect) for each algorithm button, in ALGORITHMS order."""
    buttons = []
    for index, key in enumerate(ALGORITHMS):
        y = PICKER_TOP + 34 + index * (BUTTON_HEIGHT + BUTTON_GAP)
        buttons.append((key, pygame.Rect(MAP_WIDTH + 20, y, LEGEND_WIDTH - 40, BUTTON_HEIGHT)))
    return buttons


def draw_algorithm_picker():
    title = legend_item_font.render("ALGORITHM", True, (240, 240, 240))
    screen.blit(title, (MAP_WIDTH + 20, PICKER_TOP))
    for index, (key, rect) in enumerate(algorithm_buttons()):
        color = BUTTON_ACTIVE if key == algorithm_key else BUTTON_IDLE
        pygame.draw.rect(screen, color, rect, border_radius=6)
        pygame.draw.rect(screen, LEGEND_BORDER, rect, 1, border_radius=6)
        label = legend_item_font.render(f"{index + 1}. {ALGORITHMS[key].name}", True, (240, 240, 240))
        screen.blit(label, label.get_rect(midleft=(rect.x + 10, rect.centery)))


def handle_algorithm_input(event):
    """Clicks on a button or number keys 1, 2, ... choose the algorithm."""
    global drone_path
    chosen = None
    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
        for key, rect in algorithm_buttons():
            if rect.collidepoint(event.pos):
                chosen = key
    elif event.type == pygame.KEYDOWN and pygame.K_1 <= event.key <= pygame.K_9:
        keys = list(ALGORITHMS)
        index = event.key - pygame.K_1
        if index < len(keys):
            chosen = keys[index]
    if chosen and chosen != algorithm_key:
        set_algorithm(chosen)
        drone_path = []


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
        drone_path, drone_mode = move_drone(drone)
        pygame.display.set_caption(
            f"Map Gen - {algorithm.name} - water {drone.water}/{drone.max_water}"
        )

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            exit()
        handle_algorithm_input(event)

    for y, row in enumerate(tile_Map):
        for x, item in enumerate(row):
            draw_tile(y, x, item)
    draw_path(drone_path, drone_mode)
    draw_drone(drone)
    draw_legend_panel()
    draw_algorithm_picker()
    pygame.display.update()
