import random

from . import hlt
from .hlt import EAST, NORTH, SOUTH, STILL, WEST, Move, Square

myID, game_map = hlt.get_init()
hlt.send_init("ImprovedBot")


def get_move(square):
    for direction, neighbor in enumerate(game_map.neighbors(square)):
        if neighbor.owner != myID and neighbor.strength < square.strength:
            return Move(square, direction)

    if square.strength < square.production * 5:
        return Move(square, STILL)

    return Move(square, random.choice((NORTH, WEST)))


while True:
    game_map.get_frame()
    moves = [get_move(square) for square in game_map if square.owner == myID]
    hlt.send_frame(moves)
