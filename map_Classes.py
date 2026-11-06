from enum import Enum

class Terrain (Enum):
    GRASS = 0
    WATER = 1
    GRAVEL = 2
    ASH = 3


class Tile ():
    
    def __init__(self, terrain: Terrain, row, col, occupant, fireState):
        self.terrain = terrain
        self.row = row
        self.col = col
        self.occupant = occupant
        self.fireState = fireState

    def get_neighbors(self):
        print(self.row)

