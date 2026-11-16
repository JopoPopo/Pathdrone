import pygame

from map_Classes import Resource, Terrain
from textures import make_textures


BACKGROUND = (25, 30, 40)
TEXT = (240, 240, 240)
MUTED_TEXT = (185, 195, 210)
ACCENT = (255, 190, 64)


DESCRIPTION = (
    "Pathdrone is an interactive wildfire-response simulation where autonomous "
    "drones navigate changing terrain, avoid obstacles, manage water and foam, "
    "and work together to contain spreading fires. Edit the map and compare "
    "pathfinding strategies to explore how different decisions affect the outcome."
)


GUIDE_ITEMS = (
    (Terrain.GRASS, "Grass", "Burnable land with the highest base value to protect."),
    (Terrain.WATER, "Water", "Cannot burn and refills a drone's water tank."),
    (Terrain.GRAVEL, "Gravel", "Burnable ground with lower value and spread chance."),
    (Terrain.ASH, "Ash", "Burned-out land that cannot catch fire again."),
    (Resource.Tree, "Tree", "Adds value, fuel, and a higher fire-spread chance."),
    (Resource.Bush, "Bush", "Adds value and fuel, but burns faster than a tree."),
    (Resource.Mountain, "Mountain", "A permanent obstacle that blocks drones and fire."),
    (Resource.Foam, "Foam", "Extinguishes a group of up to three fire tiles."),
    (Resource.FireStation, "Fire Station", "Fireproof depot that stores replacement foam."),
    ("drone", "Drone", "Fights fires and refills its water or foam supply."),
    ("fire", "Fire", "Spreads to nearby burnable tiles and leaves ash."),
)


def _wrapped_lines(text, font, max_width):
    lines = []
    current = ""

    for word in text.split():
        candidate = f"{current} {word}".strip()
        if not current or font.size(candidate)[0] <= max_width:
            current = candidate
        else:
            lines.append(current)
            current = word

    if current:
        lines.append(current)
    return lines


def _make_drone_icon(size):
    """Create the same drone glyph used by the map."""
    surface = pygame.Surface((size, size), pygame.SRCALPHA)
    center = size // 2
    color = (20, 45, 190)
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
        rotor_x = center + offset_x
        rotor_y = center + offset_y
        pygame.draw.line(surface, color, (center, center), (rotor_x, rotor_y), line_width)
        pygame.draw.circle(surface, color, (rotor_x, rotor_y), rotor_radius, 1)
    pygame.draw.circle(surface, color, (center, center), body_radius)
    return surface


def _make_guide_icons(size):
    """Build guide icons from the exact texture generators used by the map."""
    tile_colors = {
        Terrain.GRASS: (124, 252, 0),
        Terrain.WATER: (94, 143, 199),
        Terrain.GRAVEL: (74, 75, 70),
        Terrain.ASH: (178, 190, 181),
    }
    tile_textures, feature_textures, fire_texture = make_textures(size, tile_colors)
    grass = tile_textures[Terrain.GRASS][0]
    icons = {terrain: versions[0] for terrain, versions in tile_textures.items()}

    def on_grass(overlay):
        icon = grass.copy()
        icon.blit(overlay, (0, 0))
        return icon

    for resource, texture in feature_textures.items():
        icons[resource] = on_grass(texture)
    icons["drone"] = on_grass(_make_drone_icon(size))
    icons["fire"] = on_grass(fire_texture)
    return icons


def _draw_icon_guide(screen, rect, heading_font, item_font, detail_font, icons, icon_size):
    """Draw a compact two-column guide using the game's real map icons."""
    heading = heading_font.render("What everything does", True, TEXT)
    screen.blit(heading, heading.get_rect(midtop=(rect.centerx, rect.top)))

    column_gap = 42
    column_width = (rect.width - column_gap) // 2
    items_per_column = (len(GUIDE_ITEMS) + 1) // 2
    content_top = rect.top + heading.get_height() + 14
    row_height = icon_size + 9

    # Center each column as a group, then keep every icon and label on the
    # same vertical guides. This avoids entries shifting with text length.
    column_starts = []
    for column in range(2):
        start = column * items_per_column
        end = min(start + items_per_column, len(GUIDE_ITEMS))
        text_width = 0
        for _, name, description in GUIDE_ITEMS[start:end]:
            text_width = max(
                text_width,
                item_font.size(name)[0],
                detail_font.size(description)[0],
            )
        entry_width = icon_size + 11 + text_width
        column_left = rect.left + column * (column_width + column_gap)
        column_starts.append(column_left + (column_width - entry_width) // 2)

    for index, (icon_key, name, description) in enumerate(GUIDE_ITEMS):
        column = index // items_per_column
        row = index % items_per_column
        y = content_top + row * row_height

        name_surface = item_font.render(name, True, TEXT)
        detail_surface = detail_font.render(description, True, MUTED_TEXT)
        x = column_starts[column]
        text_x = x + icon_size + 11

        screen.blit(icons[icon_key], (x, y))
        screen.blit(name_surface, (text_x, y - 1))
        screen.blit(detail_surface, (text_x, y + name_surface.get_height() + 3))


def run_startup_screen(screen, clock):
    """Show a simple project introduction until Space is pressed."""
    scale = max(
        0.78,
        min(1.15, screen.get_width() / 1280, screen.get_height() / 760),
    )
    title_font = pygame.font.SysFont("Arial", int(54 * scale), bold=True)
    description_font = pygame.font.SysFont("Arial", int(19 * scale))
    prompt_font = pygame.font.SysFont("Arial", int(25 * scale), bold=True)
    guide_heading_font = pygame.font.SysFont("Arial", int(23 * scale), bold=True)
    guide_item_font = pygame.font.SysFont("Arial", int(17 * scale), bold=True)
    guide_detail_font = pygame.font.SysFont("Arial", int(14 * scale))
    guide_icon_size = max(34, int(46 * scale))
    guide_icons = _make_guide_icons(guide_icon_size)

    title = title_font.render("Welcome to Pathdrone", True, TEXT)
    description_lines = _wrapped_lines(
        DESCRIPTION,
        description_font,
        min(1120, screen.get_width() - 100),
    )

    line_height = description_font.get_linesize() + 5
    description_height = len(description_lines) * line_height
    items_per_column = (len(GUIDE_ITEMS) + 1) // 2
    guide_height = (
        guide_heading_font.get_linesize()
        + 14
        + items_per_column * (guide_icon_size + 9)
    )
    prompt = prompt_font.render("Press Space to Start", True, ACCENT)
    total_height = (
        title.get_height()
        + 18
        + description_height
        + 20
        + guide_height
        + 24
        + prompt.get_height()
    )
    content_top = max(20, (screen.get_height() - total_height) // 2)

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    return True
                if event.key == pygame.K_ESCAPE:
                    return False

        screen.fill(BACKGROUND)

        title_rect = title.get_rect(midtop=(screen.get_width() // 2, content_top))
        screen.blit(title, title_rect)

        description_y = title_rect.bottom + 18
        for index, line in enumerate(description_lines):
            line_surface = description_font.render(line, True, MUTED_TEXT)
            line_rect = line_surface.get_rect(
                center=(
                    screen.get_width() // 2,
                    description_y + index * line_height,
                )
            )
            screen.blit(line_surface, line_rect)

        description_bottom = description_y + description_height
        guide_width = min(1180, screen.get_width() - 60)
        guide_top = description_bottom + 20
        guide_rect = pygame.Rect(
            (screen.get_width() - guide_width) // 2,
            guide_top,
            guide_width,
            guide_height,
        )
        _draw_icon_guide(
            screen,
            guide_rect,
            guide_heading_font,
            guide_item_font,
            guide_detail_font,
            guide_icons,
            guide_icon_size,
        )

        prompt_y = guide_rect.bottom + 24 + prompt.get_height() // 2
        screen.blit(
            prompt,
            prompt.get_rect(center=(screen.get_width() // 2, prompt_y)),
        )

        pygame.display.update()
        clock.tick(60)
