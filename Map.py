import argparse
import pygame
import math
import random
from sys import exit
from map_Classes import Tile
from map_Classes import Terrain
from map_Classes import Fire
from map_Classes import Drone
from map_Classes import Resource
from map_Classes import is_blocked
from map_Classes import can_burn
from map_Classes import foam_group
from random_gen import noise_map
from pathfinding import bfs_path
from algorithms import ALGORITHMS
from resources import place_resources, RESOURCE_SEED, DEPOT_SIZE
from resources import place_features
from resources import collect_foam
from textures import make_textures
from startup_screen import run_startup_screen

# Pick the starting algorithm with: python Map.py --algorithm priority
# You can also switch while it runs: click a button in the panel, or press F1 / F2.
parser = argparse.ArgumentParser(description="Drone fire simulation")
parser.add_argument("--algorithm", choices=list(ALGORITHMS), default="priority",
                    help="which drone algorithm to start with")
args = parser.parse_args()

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
LEGEND_WIDTH = 320
STATUS_HEIGHT = 130

#the tiles are as big as the monitor allows, bigger maps get smaller tiles
TILE_SIZE = max(4, min(64, (MAX_WIDTH - LEGEND_WIDTH) // MAP_COLS, (MAX_HEIGHT - STATUS_HEIGHT) // MAP_ROWS))

#ms between tries to start a new fire, the same on every map size
FIRE_SPAWN_TIME = 3000

#ms between spread ticks, every burning tile tries to light its neighbors
FIRE_SPREAD_TIME = 1000

MAP_WIDTH = MAP_COLS * TILE_SIZE
MAP_HEIGHT = MAP_ROWS * TILE_SIZE

WINDOW_WIDTH = MAP_WIDTH + LEGEND_WIDTH
WINDOW_HEIGHT = MAP_HEIGHT + STATUS_HEIGHT

screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
pygame.display.set_caption('Map Gen')
clock = pygame.time.Clock()
if not run_startup_screen(screen, clock):
    pygame.quit()
    exit()

legend_title_font = pygame.font.SysFont("Arial", 24, bold=True)
legend_head_font = pygame.font.SysFont("Arial", 14, bold=True)
legend_item_font = pygame.font.SysFont("Arial", 16)

tile_Surface = pygame.Surface((TILE_SIZE,TILE_SIZE))

def tile_decider(x,y,noise_Map):
    noise = noise_Map[x][y]
    if noise < .5:
        return 0
    elif noise < .8:
        return 1
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
LEGEND_TEXT = (240, 240, 240)
LEGEND_DIM = (150, 155, 165)
LEGEND_HIGHLIGHT = (255, 205, 80)
DRONE_COLOR = (20, 45, 190)
FIRE_COLOR = (255, 69, 0)

# --- customization settings -------------------------------------------------
# "regen" settings only take effect when the map is rebuilt (G); the rest are
# read by the simulation every frame, so they apply straight away.
SETTINGS = [
    {"key": "seed",      "label": "Terrain seed",  "value": 8,  "min": 0, "max": 9999, "step": 1, "regen": True},
    {"key": "scale",     "label": "Terrain scale", "value": 8,  "min": 1, "max": 32,   "step": 1, "regen": True},
    {"key": "octaves",   "label": "Terrain detail","value": 3,  "min": 1, "max": 6,    "step": 1, "regen": True},
    {"key": "tank",      "label": "Drone tank",    "value": 1,  "min": 1, "max": 10,   "step": 1, "regen": True},
    {"key": "fire_rate", "label": "Fire rate",     "value": 100, "min": 0, "max": 100,  "step": 5, "regen": False, "suffix": "%"},
]
SETTINGS_BY_KEY = {entry["key"]: entry for entry in SETTINGS}
setting_index = 0


def setting(key):
    return SETTINGS_BY_KEY[key]["value"]


def adjust_setting(index, direction):
    """Nudge one setting by its step, clamped to its range."""
    global world_dirty
    entry = SETTINGS[index]
    new_value = min(entry["max"], max(entry["min"], entry["value"] + direction * entry["step"]))
    if new_value == entry["value"]:
        return
    entry["value"] = new_value
    if entry["regen"]:
        world_dirty = True


# --- paint brushes ----------------------------------------------------------
# (label, kind, payload); picked with keys 1-8 and applied by clicking a tile.
BRUSHES = (
    ("Grass",    "terrain",  Terrain.GRASS),
    ("Water",    "terrain",  Terrain.WATER),
    ("Gravel",   "terrain",  Terrain.GRAVEL),
    ("Ash",      "terrain",  Terrain.ASH),
    ("Fire",     "fire",     None),
    ("Resource", "resource", None),
    ("Erase",    "erase",    None),
    ("Move drone", "drone",  None),
)
brush_index = 0
ERASE_BRUSH = next(i for i, brush in enumerate(BRUSHES) if brush[1] == "erase")
painting = False
paint_button = 1

world_dirty = False
options_open = False
brush_open = False


def draw_gear(center, radius, color):
    """A gear glyph: a toothed ring with a hole in the middle."""
    teeth = 8
    for index in range(teeth):
        angle = index * math.tau / teeth
        inner = (center[0] + math.cos(angle) * radius * 0.62,
                 center[1] + math.sin(angle) * radius * 0.62)
        outer = (center[0] + math.cos(angle) * radius * 1.15,
                 center[1] + math.sin(angle) * radius * 1.15)
        pygame.draw.line(screen, color, inner, outer, 4)
    pygame.draw.circle(screen, color, center, int(radius * 0.8), 3)
    pygame.draw.circle(screen, color, center, int(radius * 0.3), 2)


# Both pickers live behind a button in the legend; neither is shown by default.
GEAR_HITBOX = pygame.Rect(MAP_WIDTH + 20, 48, LEGEND_WIDTH - 40, 36)
GEAR_CENTER = (GEAR_HITBOX.left + 24, GEAR_HITBOX.centery)
GEAR_RADIUS = 11
BRUSH_HITBOX = pygame.Rect(MAP_WIDTH + 20, 92, LEGEND_WIDTH - 40, 36)

# Each panel floats over the middle of the map.
OPTIONS_ROW_HEIGHT = 34
OPTIONS_RECT = pygame.Rect(0, 0, 440, 108 + len(SETTINGS) * OPTIONS_ROW_HEIGHT)
OPTIONS_RECT.center = (MAP_WIDTH // 2, MAP_HEIGHT // 2)

BRUSH_ROW_HEIGHT = 32
BRUSH_RECT = pygame.Rect(0, 0, 320, 96 + len(BRUSHES) * BRUSH_ROW_HEIGHT)
BRUSH_RECT.center = (MAP_WIDTH // 2, MAP_HEIGHT // 2)


def options_row_rects():
    """Per-setting (row, minus, plus) rects, shared by drawing and hit tests."""
    rects = []
    for index in range(len(SETTINGS)):
        top = OPTIONS_RECT.top + 62 + index * OPTIONS_ROW_HEIGHT
        row = pygame.Rect(OPTIONS_RECT.left + 16, top, OPTIONS_RECT.width - 32, 26)
        minus = pygame.Rect(row.right - 108, top, 26, 26)
        plus = pygame.Rect(row.right - 26, top, 26, 26)
        rects.append((row, minus, plus))
    return rects


def brush_row_rects():
    """Per-brush row rects, shared by drawing and hit tests."""
    return [
        pygame.Rect(BRUSH_RECT.left + 16, BRUSH_RECT.top + 56 + index * BRUSH_ROW_HEIGHT,
                    BRUSH_RECT.width - 32, 26)
        for index in range(len(BRUSHES))
    ]


def build_world():
    """Create a fresh map, station, drones, and fire from the current settings."""
    global tile_Map, resources, fire, drones, drone_paths, station_tile, world_dirty, water_Tiles
    global drone_move_timer, fire_spawn_timer, fire_spread_timer

    noise_Map = noise_map(MAP_COLS, MAP_ROWS, setting("seed"), setting("scale"), setting("octaves"))
    tile_Map = [
        [Tile(Terrain(tile_decider(row, col, noise_Map)), row, col, 0, 0)
         for col in range(MAP_COLS)]
        for row in range(MAP_ROWS)
    ]
    resources = place_resources(
        tile_Map,
        seed=RESOURCE_SEED + setting("seed"),
        count=DEPOT_SIZE,
    )
    place_features(tile_Map)
    water_Tiles = [tile for row in tile_Map for tile in row if tile.terrain == Terrain.WATER]
    station_tile = next(
        (tile for row in tile_Map for tile in row if Resource.FireStation in tile.occupant),
        None,
    )
    drone_tiles = [
        tile for row in tile_Map for tile in row
        if Resource.DronePad in tile.occupant
    ]
    drones = [Drone(tile, max_water=setting("tank")) for tile in drone_tiles]
    if not drones:
        open_tiles = [
            tile for row in tile_Map for tile in row
            if not is_blocked(tile) and tile.terrain != Terrain.WATER
        ]
        if open_tiles:
            drones = [Drone(random.choice(open_tiles), max_water=setting("tank"))]

    fire = Fire()
    fire.spawn_random_source(
        tile_Map,
        excluded={(drone.row, drone.col) for drone in drones},
    )
    set_algorithm(algorithm_key)

    drone_paths = [([], "fire") for drone in drones]
    drone_move_timer = 0
    fire_spawn_timer = 0
    fire_spread_timer = 0
    world_dirty = False


def clear_resource(tile):
    if Resource.Foam in tile.occupant:
        tile.occupant.remove(Resource.Foam)
    if tile in resources:
        resources.remove(tile)


def paint_tile(tile, index=None):
    """Apply a brush to one tile, defaulting to the selected one."""
    global drone_paths, water_Tiles
    label, kind, payload = BRUSHES[brush_index if index is None else index]

    if kind == "terrain":
        tile.terrain = payload
        if payload in (Terrain.WATER, Terrain.ASH):
            fire.extinguish(tile)
        if payload == Terrain.WATER:
            # Water can't burn and can't hold a resource point.
            clear_resource(tile)
            tile.occupant.clear()
        water_Tiles = [item for row in tile_Map for item in row if item.terrain == Terrain.WATER]
        set_algorithm(algorithm_key)
    elif kind == "fire":
        if can_burn(tile):
            fire.ignite(tile)
    elif kind == "resource":
        if tile.terrain != Terrain.WATER and not is_blocked(tile) and Resource.Foam not in tile.occupant:
            tile.occupant.append(Resource.Foam)
            resources.append(tile)
    elif kind == "erase":
        fire.extinguish(tile)
        clear_resource(tile)
    elif kind == "drone" and drones and not is_blocked(tile):
        drone = min(drones, key=lambda item: abs(item.row - tile.row) + abs(item.col - tile.col))
        if all(item is drone or (item.row, item.col) != (tile.row, tile.col) for item in drones):
            drone.row, drone.col = tile.row, tile.col
        set_algorithm(algorithm_key)
    drone_paths = [([], "fire") for drone in drones]


def tile_at(pos):
    """The tile under a screen position, or None if the click missed the map."""
    x, y = pos
    if not (0 <= x < MAP_WIDTH and 0 <= y < MAP_HEIGHT):
        return None
    return tile_Map[y // TILE_SIZE][x // TILE_SIZE]


def set_algorithm(key):
    """Switch all drones to the selected algorithm with fresh planner state."""
    global algorithm_key, algorithm, algorithms, drone_paths
    algorithm_key = key

    #the team is shared by all the drones, only the greedy ratio reads it, the other algorithms are untouched
    team = {}
    algorithms = []
    for drone in drones:
        brain = ALGORITHMS[key](tile_Map, water_Tiles)
        brain.team = team
        algorithms.append(brain)
    algorithm = algorithms[0] if algorithms else ALGORITHMS[key](tile_Map, water_Tiles)
    drone_paths = [([], "fire") for drone in drones]


algorithm_key = args.algorithm


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
    draw_drone_glyph(center_x, center_y, TILE_SIZE)

    #a white dot over the drone when it carries foam
    if drone.foam > 0:
        pygame.draw.circle(screen, (255, 255, 255), (center_x, center_y - TILE_SIZE // 3), max(2, TILE_SIZE // 8))


def draw_drone_glyph(center_x, center_y, size):
    """The drone symbol, sized to fit a `size` box, for the map and the legend."""
    color = DRONE_COLOR
    rotor_offset = size * 18 // 50
    rotor_radius = max(2, size * 6 // 50)
    body_radius = max(2, size * 7 // 50)
    line_width = max(1, size * 4 // 50)

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


PATH_COLORS = {"fire": (255, 255, 255), "refill": (0, 255, 255), "foam": (255, 200, 0), "home": (120, 120, 120)}


def draw_path(path, mode):
    if len(path) < 2:
        return
    half = TILE_SIZE // 2
    points = [(col * TILE_SIZE + half, row * TILE_SIZE + half) for row, col in path]
    pygame.draw.lines(screen, PATH_COLORS[mode], False, points, 2)


def draw_hover_highlight():
    """Outline the tile the brush would land on."""
    if options_open or brush_open:
        return
    tile = tile_at(pygame.mouse.get_pos())
    if tile is None:
        return
    pygame.draw.rect(
        screen,
        LEGEND_HIGHLIGHT,
        (tile.col * TILE_SIZE, tile.row * TILE_SIZE, TILE_SIZE, TILE_SIZE),
        2,
    )


def put_out_fire(drone, tile):
    #foam puts out the tile and the burning tiles next to it, water puts out one tile
    group = foam_group(tile_Map, tile)
    if drone.foam > 0 and len(group) > 1:
        for item in group:
            fire.extinguish(item)
        drone.foam -= 1
    elif drone.water > 0:
        fire.extinguish(tile)
        drone.water -= 1
    elif drone.foam > 0:
        fire.extinguish(tile)
        drone.foam -= 1


def move_drone(drone, brain, occupied_positions=()):
    """Take one step toward the current goal, then act on the tile reached.

    The path is recalculated every step, since fires spread and new ones
    appear. Returns the path still ahead and the mode, for drawing.
    """
    path, mode = brain.next_path(drone, fire.burning_tiles)
    if not path:
        return [], mode
    if len(path) > 1 and tuple(path[1]) in occupied_positions:
        path = bfs_path(
            tile_Map,
            (drone.row, drone.col),
            [path[-1]],
            blocked_positions=occupied_positions,
        )
        if not path:
            return [], mode
    if len(path) > 1:
        drone.row, drone.col = path[1]

    tile = tile_Map[drone.row][drone.col]
    if tile.fireState:
        put_out_fire(drone, tile)
    if tile.terrain == Terrain.WATER:
        drone.water = drone.max_water
    if collect_foam(tile, station_tile, drone) and Resource.Foam not in tile.occupant:
        clear_resource(tile)
    return path[1:], mode


def move_all_drones():
    paths = []
    for index, drone in enumerate(drones):
        occupied = {
            (other.row, other.col) for other in drones if other is not drone
        }
        brain = algorithms[index]
        paths.append(move_drone(drone, brain, occupied))
    return paths


DRONE_MOVE_INTERVAL = 250   # ms per tile
paused = False


def draw_brush_swatch(x, y, size, brush):
    """A small preview of what a brush paints."""
    label, kind, payload = brush
    box = pygame.Rect(x, y, size, size)

    if kind == "terrain":
        pygame.draw.rect(screen, tile_Colors[payload], box)
        pygame.draw.rect(screen, LEGEND_BORDER, box, 1)
    elif kind == "fire":
        inset = size // 8
        pygame.draw.rect(screen, FIRE_COLOR, box.inflate(-2 * inset, -2 * inset))
    elif kind == "resource":
        pygame.draw.circle(screen, (255, 255, 255), box.center, size // 4)
        pygame.draw.circle(screen, (0, 0, 0), box.center, size // 4, 2)
    elif kind == "erase":
        pygame.draw.rect(screen, LEGEND_BORDER, box, 1)
        pygame.draw.line(screen, LEGEND_BORDER, box.topleft, box.bottomright, 2)
        pygame.draw.line(screen, LEGEND_BORDER, box.topright, box.bottomleft, 2)
    elif kind == "drone":
        draw_drone_glyph(box.centerx, box.centery, size * 2)


def draw_legend_panel():
    legend_rect = pygame.Rect(MAP_WIDTH, 0, LEGEND_WIDTH, WINDOW_HEIGHT)
    pygame.draw.rect(screen, LEGEND_BACKGROUND, legend_rect)
    pygame.draw.line(screen, LEGEND_BORDER, (MAP_WIDTH, 0), (MAP_WIDTH, WINDOW_HEIGHT), 2)

    item_x = MAP_WIDTH + 20
    text_x = item_x + 32
    box_size = 20

    screen.blit(legend_title_font.render("LEGEND", True, LEGEND_TEXT), (item_x, 12))

    mouse_pos = pygame.mouse.get_pos()

    # Options button.
    gear_hot = options_open or GEAR_HITBOX.collidepoint(mouse_pos)
    pygame.draw.rect(screen, (58, 52, 38) if gear_hot else (48, 52, 60), GEAR_HITBOX)
    pygame.draw.rect(screen, LEGEND_HIGHLIGHT, GEAR_HITBOX, 2)
    draw_gear(GEAR_CENTER, GEAR_RADIUS, LEGEND_HIGHLIGHT)
    screen.blit(
        legend_item_font.render("OPTIONS", True, LEGEND_HIGHLIGHT),
        (GEAR_HITBOX.left + 44, GEAR_HITBOX.centery - 9),
    )
    if world_dirty:
        # The settings are hidden, so say so here when a rebuild is pending.
        pending = legend_head_font.render("rebuild pending", True, LEGEND_HIGHLIGHT)
        screen.blit(
            pending,
            (GEAR_HITBOX.right - pending.get_width() - 14, GEAR_HITBOX.centery - 7),
        )

    # Brush button, showing the brush currently selected.
    brush_hot = brush_open or BRUSH_HITBOX.collidepoint(mouse_pos)
    pygame.draw.rect(screen, (58, 52, 38) if brush_hot else (48, 52, 60), BRUSH_HITBOX)
    pygame.draw.rect(screen, LEGEND_HIGHLIGHT, BRUSH_HITBOX, 2)
    draw_brush_swatch(BRUSH_HITBOX.left + 13, BRUSH_HITBOX.centery - 10, 20, BRUSHES[brush_index])
    screen.blit(
        legend_item_font.render(f"BRUSH: {BRUSHES[brush_index][0]}", True, LEGEND_HIGHLIGHT),
        (BRUSH_HITBOX.left + 44, BRUSH_HITBOX.centery - 9),
    )

    # Terrain, fire and drone keys.
    screen.blit(legend_head_font.render("MAP", True, LEGEND_DIM), (item_x, 142))
    y = 162
    for label, terrain in LEGEND_ITEMS:
        color_box = pygame.Rect(item_x, y, box_size, box_size)
        pygame.draw.rect(screen, tile_Colors[terrain], color_box)
        pygame.draw.rect(screen, LEGEND_BORDER, color_box, 1)
        screen.blit(legend_item_font.render(label, True, LEGEND_TEXT), (text_x, y))
        y += 26

    inset = box_size // 8
    pygame.draw.rect(
        screen,
        FIRE_COLOR,
        (item_x + inset, y + inset, box_size - 2 * inset, box_size - 2 * inset),
    )
    screen.blit(legend_item_font.render("Active Fire", True, LEGEND_TEXT), (text_x, y))
    y += 26

    draw_drone_glyph(item_x + box_size // 2, y + box_size // 2, box_size * 2)
    screen.blit(legend_item_font.render("Drone", True, LEGEND_TEXT), (text_x, y))


def draw_panel_backdrop(rect, title):
    """Dim the map and draw an empty titled panel. Shared by both pickers."""
    shade = pygame.Surface((MAP_WIDTH, MAP_HEIGHT), pygame.SRCALPHA)
    shade.fill((0, 0, 0, 140))
    screen.blit(shade, (0, 0))

    pygame.draw.rect(screen, LEGEND_BACKGROUND, rect)
    pygame.draw.rect(screen, LEGEND_BORDER, rect, 2)
    screen.blit(
        legend_title_font.render(title, True, LEGEND_TEXT),
        (rect.left + 16, rect.top + 12),
    )


def draw_brush_panel():
    """The brush picker. Hidden until the BRUSH button is clicked."""
    draw_panel_backdrop(BRUSH_RECT, "BRUSH")
    mouse_pos = pygame.mouse.get_pos()

    for index, (brush, row) in enumerate(zip(BRUSHES, brush_row_rects())):
        selected = index == brush_index
        hot = row.collidepoint(mouse_pos)
        if selected or hot:
            pygame.draw.rect(screen, (58, 52, 38) if hot else (55, 60, 70), row.inflate(8, 4))
        draw_brush_swatch(row.left, row.top + 3, 20, brush)
        color = LEGEND_HIGHLIGHT if selected else LEGEND_TEXT
        screen.blit(
            legend_item_font.render(f"{index + 1}   {brush[0]}", True, color),
            (row.left + 32, row.top + 3),
        )

    screen.blit(
        legend_head_font.render("click a brush, or press 1-8    B or ESC close", True, LEGEND_DIM),
        (BRUSH_RECT.left + 16, BRUSH_RECT.bottom - 28),
    )


def draw_options_panel():
    """The settings, as a panel over the map. Hidden until the gear is clicked."""
    draw_panel_backdrop(OPTIONS_RECT, "OPTIONS")
    draw_gear((OPTIONS_RECT.right - 32, OPTIONS_RECT.top + 26), 11, LEGEND_HIGHLIGHT)
    mouse_pos = pygame.mouse.get_pos()
    for index, (entry, (row, minus, plus)) in enumerate(zip(SETTINGS, options_row_rects())):
        selected = index == setting_index
        if selected:
            pygame.draw.rect(screen, (55, 60, 70), row.inflate(8, 4))

        color = LEGEND_HIGHLIGHT if selected else LEGEND_TEXT
        screen.blit(legend_item_font.render(entry["label"], True, color), (row.left, row.top + 3))

        value = f"{entry['value']}{entry.get('suffix', '')}"
        value_surface = legend_item_font.render(value, True, color)
        screen.blit(value_surface, (minus.right + 24 - value_surface.get_width() // 2, row.top + 3))

        for button, glyph in ((minus, "-"), (plus, "+")):
            hot = button.collidepoint(mouse_pos)
            pygame.draw.rect(screen, LEGEND_HIGHLIGHT if hot else LEGEND_BORDER, button, 1)
            glyph_surface = legend_item_font.render(glyph, True, LEGEND_HIGHLIGHT if hot else color)
            screen.blit(glyph_surface, glyph_surface.get_rect(center=button.center))

    hint_y = OPTIONS_RECT.bottom - 40
    hints = (
        "UP/DOWN select    LEFT/RIGHT change    N random seed",
        "G rebuild map    TAB or ESC close",
    )
    for line in hints:
        screen.blit(legend_head_font.render(line, True, LEGEND_DIM), (OPTIONS_RECT.left + 16, hint_y))
        hint_y += 18

    if world_dirty:
        screen.blit(
            legend_head_font.render("map rebuild pending - press G", True, LEGEND_HIGHLIGHT),
            (OPTIONS_RECT.left + 16, OPTIONS_RECT.bottom - 60),
        )


STATUS_LINES = (
    "SPACE  pause / resume      .  step one drone move (paused)      ESC  quit",
    "left-click  paint      right-click  erase      drag to paint      1-8  pick brush",
    "BRUSH button or B  brushes      OPTIONS button or TAB  settings      G  rebuild      N  seed",
)

# ---- algorithm picker (bottom of the side panel) ---------------------------

BUTTON_HEIGHT = 34
BUTTON_GAP = 8
BUTTON_ACTIVE = (70, 130, 220)
BUTTON_IDLE = (60, 64, 74)
PICKER_TOP = 330   # just below the legend's fire and drone rows


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
        label = legend_item_font.render(f"F{index + 1}. {ALGORITHMS[key].name}", True, (240, 240, 240))
        screen.blit(label, label.get_rect(midleft=(rect.x + 10, rect.centery)))


def handle_algorithm_input(event):
    """Clicks on a button or function keys F1, F2, ... choose the algorithm."""
    chosen = None
    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
        for key, rect in algorithm_buttons():
            if rect.collidepoint(event.pos):
                chosen = key
    elif event.type == pygame.KEYDOWN and pygame.K_F1 <= event.key <= pygame.K_F9:
        keys = list(ALGORITHMS)
        index = event.key - pygame.K_F1
        if index < len(keys):
            chosen = keys[index]
    if chosen and chosen != algorithm_key:
        set_algorithm(chosen)


def draw_status_bar():
    bar = pygame.Rect(0, MAP_HEIGHT, MAP_WIDTH, STATUS_HEIGHT)
    pygame.draw.rect(screen, LEGEND_BACKGROUND, bar)
    pygame.draw.line(screen, LEGEND_BORDER, (0, MAP_HEIGHT), (MAP_WIDTH, MAP_HEIGHT), 2)

    y = MAP_HEIGHT + 12
    state = "PAUSED" if paused else "RUNNING"
    water = ", ".join(f"{item.water}/{item.max_water}" for item in drones) or "none"
    carried = ", ".join(f"{item.foam}/{item.max_foam}" for item in drones) or "none"
    foam_reserve = station_tile.foam_capacity if station_tile else 0
    status = (
        f"{state}      drones {len(drones)} water {water} foam {carried}"
        f"      fires {len(fire.burning_tiles)}"
        f"      foam reserve {foam_reserve}"
        f"      brush: {BRUSHES[brush_index][0]}"
    )
    screen.blit(
        legend_item_font.render(status, True, LEGEND_HIGHLIGHT if paused else LEGEND_TEXT),
        (16, y),
    )
    y += 26
    for line in STATUS_LINES:
        screen.blit(legend_item_font.render(line, True, LEGEND_DIM), (16, y))
        y += 22


def handle_event(event):
    global paused, brush_index, setting_index, painting, paint_button
    global drone_paths, world_dirty, options_open, brush_open

    if event.type == pygame.QUIT:
        pygame.quit()
        exit()

    if event.type == pygame.MOUSEBUTTONDOWN and event.button in (1, 3):
        if GEAR_HITBOX.collidepoint(event.pos):
            options_open = not options_open
            brush_open = False       # only one panel at a time
            return
        if BRUSH_HITBOX.collidepoint(event.pos):
            brush_open = not brush_open
            options_open = False
            return
        if options_open:
            if OPTIONS_RECT.collidepoint(event.pos):
                for index, (row, minus, plus) in enumerate(options_row_rects()):
                    if minus.collidepoint(event.pos):
                        setting_index = index
                        adjust_setting(index, -1)
                    elif plus.collidepoint(event.pos):
                        setting_index = index
                        adjust_setting(index, 1)
                    elif row.collidepoint(event.pos):
                        setting_index = index
            else:
                options_open = False   # click away to dismiss
            return   # never paint through the panel
        if brush_open:
            if BRUSH_RECT.collidepoint(event.pos):
                for index, row in enumerate(brush_row_rects()):
                    if row.collidepoint(event.pos):
                        brush_index = index
                        brush_open = False   # picking a brush closes the panel
            else:
                brush_open = False
            return   # never paint through the panel
        handle_algorithm_input(event)
        tile = tile_at(event.pos)
        if tile is not None:
            painting = True
            paint_button = event.button
            paint_tile(tile, ERASE_BRUSH if event.button == 3 else None)
    elif event.type == pygame.MOUSEBUTTONUP:
        painting = False
    elif event.type == pygame.MOUSEMOTION and painting:
        index = ERASE_BRUSH if paint_button == 3 else brush_index
        tile = tile_at(event.pos)
        if tile is not None and BRUSHES[index][1] != "drone":
            paint_tile(tile, index)   # dragging the drone brush would be a trail, not a move

    elif event.type == pygame.KEYDOWN:
        if not options_open and not brush_open:
            handle_algorithm_input(event)
        if event.key == pygame.K_ESCAPE:
            if options_open or brush_open:
                options_open = brush_open = False
                return
            pygame.quit()
            exit()
        elif event.key == pygame.K_TAB:
            options_open = not options_open
            brush_open = False
        elif event.key == pygame.K_b:
            brush_open = not brush_open
            options_open = False
        elif event.key == pygame.K_SPACE:
            paused = not paused
        elif event.key == pygame.K_PERIOD and paused:
            drone_paths = move_all_drones()
        elif pygame.K_1 <= event.key <= pygame.K_8:
            brush_index = event.key - pygame.K_1
            brush_open = False
        elif event.key == pygame.K_DOWN and options_open:
            setting_index = (setting_index + 1) % len(SETTINGS)
        elif event.key == pygame.K_UP and options_open:
            setting_index = (setting_index - 1) % len(SETTINGS)
        elif event.key == pygame.K_RIGHT and options_open:
            adjust_setting(setting_index, 1)
        elif event.key == pygame.K_LEFT and options_open:
            adjust_setting(setting_index, -1)
        elif event.key == pygame.K_n:
            SETTINGS_BY_KEY["seed"]["value"] = random.randint(0, 9999)
            world_dirty = True
        elif event.key == pygame.K_g:
            build_world()


build_world()

while True:
    delta_time = clock.tick(60)

    for event in pygame.event.get():
        handle_event(event)

    if paused:
        delta_time = 0   # freeze fires and the drone, but keep drawing

    fire_spawn_timer += delta_time
    if fire_spawn_timer >= FIRE_SPAWN_TIME:
        fire_spawn_timer -= FIRE_SPAWN_TIME
        if random.random() < setting("fire_rate") / 100:
            fire.spawn_random_source(tile_Map)

    #tiles that burned long enough turn to ash
    fire.burn(delta_time)

    fire_spread_timer += delta_time
    if fire_spread_timer >= FIRE_SPREAD_TIME:
        fire_spread_timer -= FIRE_SPREAD_TIME
        fire.spread(tile_Map)

    drone_move_timer += delta_time
    if drone_move_timer >= DRONE_MOVE_INTERVAL:
        drone_move_timer -= DRONE_MOVE_INTERVAL
        drone_paths = move_all_drones()

    pygame.display.set_caption(
        f"Map Gen - {algorithm.name} - {'paused' if paused else 'running'}"
        f" - drones {len(drones)} - station foam "
        f"{station_tile.foam_capacity if station_tile else 0}"
    )

    for y, row in enumerate(tile_Map):
        for x, item in enumerate(row):
            draw_tile(y, x, item)
    for path, mode in drone_paths:
        draw_path(path, mode)
    for drone in drones:
        draw_drone(drone)
    draw_hover_highlight()
    draw_legend_panel()
    draw_algorithm_picker()
    draw_status_bar()
    if options_open:
        draw_options_panel()
    elif brush_open:
        draw_brush_panel()
    pygame.display.update()
