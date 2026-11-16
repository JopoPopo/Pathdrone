#Tile textures, drawn once with code when the game starts
#Every texture is made for the tile size we are given, so it works for any map size

import pygame
import random

from map_Classes import Terrain
from map_Classes import Resource

VARIANTS = 4


def shade(color, amount):
    #positive amount is lighter, negative is darker
    red = min(255, max(0, color[0] + amount))
    green = min(255, max(0, color[1] + amount))
    blue = min(255, max(0, color[2] + amount))
    return (red, green, blue)


def make_grass(size, color, rand):
    surface = pygame.Surface((size, size))
    surface.fill(shade(color, rand.randint(-12, 12)))

    #dark blades of grass
    for i in range(max(3, size // 2)):
        blade_x = rand.randint(1, size - 2)
        blade_y = rand.randint(size // 3, size - 1)
        lean = rand.randint(-1, 1)
        pygame.draw.line(surface, shade(color, -45), (blade_x, blade_y), (blade_x + lean, blade_y - max(2, size // 5)), 1)

    #light specks
    for i in range(max(2, size // 3)):
        surface.set_at((rand.randint(0, size - 1), rand.randint(0, size - 1)), shade(color, 35))
    return surface


def make_water(size, color, rand):
    surface = pygame.Surface((size, size))
    #the color changes very little so the water does not look like squares
    surface.fill(shade(color, rand.randint(-3, 3)))

    #light and dark ripples
    for i in range(max(2, size // 8)):
        ripple_x = rand.randint(0, size // 2)
        ripple_y = rand.randint(1, size - 2)
        ripple_length = max(3, size // 3)
        pygame.draw.line(surface, shade(color, 32), (ripple_x, ripple_y), (ripple_x + ripple_length, ripple_y), 1)
        pygame.draw.line(surface, shade(color, -22), (ripple_x, ripple_y + 1), (ripple_x + ripple_length, ripple_y + 1), 1)
    return surface


def make_gravel(size, color, rand):
    surface = pygame.Surface((size, size))
    surface.fill(shade(color, rand.randint(-8, 8)))

    #small stones, some lighter and some darker
    for i in range(max(4, size // 2)):
        stone_x = rand.randint(1, size - 2)
        stone_y = rand.randint(1, size - 2)
        pygame.draw.circle(surface, shade(color, rand.randint(-25, 35)), (stone_x, stone_y), max(1, size // 12))
    return surface


def make_ash(size, color, rand):
    surface = pygame.Surface((size, size))
    surface.fill(shade(color, rand.randint(-8, 8)))

    #dark burnt flecks and light dust
    for i in range(max(4, size // 2)):
        fleck_x = rand.randint(1, size - 2)
        fleck_y = rand.randint(1, size - 2)
        pygame.draw.line(surface, shade(color, -70), (fleck_x, fleck_y), (fleck_x + rand.randint(-2, 2), fleck_y + rand.randint(-1, 1)), 1)
    for i in range(max(2, size // 3)):
        surface.set_at((rand.randint(0, size - 1), rand.randint(0, size - 1)), shade(color, 25))
    return surface


def make_tree(size):
    surface = pygame.Surface((size, size), pygame.SRCALPHA)
    half = size // 2
    trunk_width = max(2, size // 8)

    #shadow, trunk, then the leaves on top
    pygame.draw.ellipse(surface, (0, 0, 0, 70), (size // 5, size * 3 // 4, size * 3 // 5, max(2, size // 6)))
    pygame.draw.rect(surface, (101, 67, 33), (half - trunk_width // 2, size * 6 // 10, trunk_width, size * 3 // 10))
    pygame.draw.circle(surface, (0, 90, 20), (half, size * 4 // 10), size // 3)
    pygame.draw.circle(surface, (30, 135, 45), (half - size // 10, size * 33 // 100), max(2, size // 6))
    return surface


def make_bush(size):
    surface = pygame.Surface((size, size), pygame.SRCALPHA)
    half = size // 2
    radius = max(2, size // 5)

    pygame.draw.ellipse(surface, (0, 0, 0, 60), (size // 5, size * 7 // 10, size * 3 // 5, max(2, size // 6)))
    pygame.draw.circle(surface, (70, 95, 35), (half - size // 6, size * 6 // 10), radius)
    pygame.draw.circle(surface, (70, 95, 35), (half + size // 6, size * 6 // 10), radius)
    pygame.draw.circle(surface, (85, 112, 45), (half, size * 45 // 100), radius)
    pygame.draw.circle(surface, (125, 150, 70), (half - size // 10, size * 4 // 10), max(1, size // 12))
    return surface


def make_mountain(size):
    surface = pygame.Surface((size, size), pygame.SRCALPHA)
    half = size // 2
    edge = max(1, size // 8)

    #the left side is lit, the right side is in the dark
    pygame.draw.polygon(surface, (170, 170, 170), [(half, edge), (edge, size - edge), (half, size - edge)])
    pygame.draw.polygon(surface, (115, 115, 115), [(half, edge), (half, size - edge), (size - edge, size - edge)])

    #snow on top
    snow = max(2, size // 6)
    pygame.draw.polygon(surface, (240, 240, 245), [(half, edge), (half - snow, edge + snow * 3 // 2), (half + snow, edge + snow * 3 // 2)])
    pygame.draw.polygon(surface, (40, 40, 40), [(half, edge), (edge, size - edge), (size - edge, size - edge)], max(1, size // 14))
    return surface


def make_foam(size):
    surface = pygame.Surface((size, size), pygame.SRCALPHA)
    half = size // 2

    pygame.draw.circle(surface, (255, 255, 255), (half, half), size // 4)
    pygame.draw.circle(surface, (200, 230, 255), (half - size // 12, half - size // 12), max(1, size // 10))
    pygame.draw.circle(surface, (0, 0, 0), (half, half), size // 4, 2)
    return surface


def make_fire_station(size):
    surface = pygame.Surface((size, size), pygame.SRCALPHA)
    inset = max(1, size // 8)
    roof_peak = max(1, size // 6)
    body_top = size // 3
    half = size // 2

    pygame.draw.rect(
        surface,
        (190, 45, 38),
        (inset, body_top, size - 2 * inset, size - body_top - inset),
    )
    pygame.draw.polygon(
        surface,
        (115, 25, 25),
        ((0, body_top), (half, roof_peak), (size, body_top)),
    )
    cross_width = max(2, size // 5)
    cross_thickness = max(1, size // 12)
    pygame.draw.rect(
        surface,
        (255, 245, 220),
        (half - cross_thickness // 2, body_top - cross_width, cross_thickness, cross_width * 2),
    )
    pygame.draw.rect(
        surface,
        (255, 245, 220),
        (half - cross_width, body_top - cross_thickness, cross_width * 2, cross_thickness),
    )

    garage_width = max(2, size // 2)
    garage_height = max(2, size // 3)
    pygame.draw.rect(
        surface,
        (65, 75, 85),
        (half - garage_width // 2, size - inset - garage_height, garage_width, garage_height),
    )
    pygame.draw.rect(
        surface,
        (210, 210, 200),
        (half - garage_width // 2, size - inset - garage_height, garage_width, max(1, size // 16)),
    )
    return surface


def make_fire(size):
    surface = pygame.Surface((size, size), pygame.SRCALPHA)
    half = size // 2

    #big orange flame with a yellow flame inside
    outer = [(half, size * 1 // 10), (size * 72 // 100, size * 45 // 100), (size * 78 // 100, size * 70 // 100),
             (half, size * 9 // 10), (size * 22 // 100, size * 70 // 100), (size * 28 // 100, size * 45 // 100)]
    inner = [(half, size * 35 // 100), (size * 62 // 100, size * 60 // 100), (half, size * 85 // 100), (size * 38 // 100, size * 60 // 100)]
    pygame.draw.polygon(surface, (255, 69, 0), outer)
    pygame.draw.polygon(surface, (255, 200, 0), inner)
    return surface


def make_textures(size, tile_Colors):
    #needs the window to be open, convert makes the drawing faster
    tile_Textures = {}
    makers = {
        Terrain.GRASS: make_grass,
        Terrain.WATER: make_water,
        Terrain.GRAVEL: make_gravel,
        Terrain.ASH: make_ash,
    }

    #each terrain gets a few versions so the map does not look like a repeating pattern
    #the random here is its own, so the game random is not touched and the same map always looks the same
    for terrain in makers:
        tile_Textures[terrain] = []
        for i in range(VARIANTS):
            rand = random.Random(terrain.value * 100 + i)
            tile_Textures[terrain].append(makers[terrain](size, tile_Colors[terrain], rand).convert())

    feature_Textures = {
        Resource.Tree: make_tree(size).convert_alpha(),
        Resource.Bush: make_bush(size).convert_alpha(),
        Resource.Mountain: make_mountain(size).convert_alpha(),
        Resource.Foam: make_foam(size).convert_alpha(),
        Resource.FireStation: make_fire_station(size).convert_alpha(),
    }
    fire_Texture = make_fire(size).convert_alpha()
    return tile_Textures, feature_Textures, fire_Texture
