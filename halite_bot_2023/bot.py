import logging
import operator
import sys
from dataclasses import dataclass
from functools import partial
from pprint import pformat
from typing import Any, Callable, Dict, Iterable, List, Set

import networkx as nx

from . import hlt
from .hlt import EAST, NORTH, SOUTH, STILL, WEST, GameMap, Move, Square, grouper

logger = logging.getLogger(__name__)


class Grid:
    def __init__(self, name: str, initializer: Callable[[Square], int] = None):
        if initializer is None:
            initializer = lambda l: 0

        self.name = name
        self.initializer = initializer
        self.grid = {}

        for square in game_map:
            self.grid[square] = initializer(square)

    def __getitem__(self, square: Square) -> int:
        return self.grid[square]

    def __setitem__(self, square: Square, value: int):
        self.grid[square] = value

    def __repr__(self):
        output = f"\n{self.name}\n"
        output += "     "
        output += " ".join(str(i)[:3].ljust(4) for i in range(game_map.width))
        output += "\n"
        for y, row in enumerate(grouper(game_map, game_map.width)):
            output += str(y)[:3].ljust(4)
            output += " ".join(str(self[s])[:3].ljust(4) for s in row)
            output += f" {y}"
            output += "\n"
        output += "     "
        output += " ".join(str(i)[:3].ljust(4) for i in range(game_map.width))
        output += "\n"

        return output


def walk_set(
    open_set: Dict[Square, Any],
    pick_next: Callable[[Dict[Square, Any]], Square],
    visit: Callable[[Square], Iterable[Square]],
):
    closed_set: Set[Square] = set()
    while open_set:
        current = pick_next(open_set)
        if current:
            open_set.pop(current)
            if current not in closed_set:
                closed_set.add(current)
                open_set |= {s: None for s in visit(current)}


def bfs(open_set: Dict[Square, Any], visit: Callable[[Square], Iterable[Square]]):
    return walk_set(open_set, lambda i: next(iter(i), None), visit)


def dijkstras(
    open_set: Dict[Square, Any],
    min_by: Callable[[Square], int],
    visit: Callable[[Square], Iterable[Square]],
):
    return walk_set(open_set, lambda i: min(iter(i), key=min_by), visit)


def move(square: Square):
    if square.strength == 0:
        return Move(square, STILL)

    target, direction = max(
        (
            (neighbor, direction)
            for direction, neighbor in enumerate(game_map.neighbors(square))
            if neighbor.owner != myID
        ),
        default=(None, None),
        key=lambda t: heuristic(t[0]),
    )

    if (
        target is not None
        and target.strength < square.strength
        and target.production > 0
    ):
        return Move(square, direction)
    elif square.strength < square.production * 5:
        return Move(square, STILL)

    if cells_to_enemy_grid[square] < 9999:
        _, direction = min(
            (cells_to_enemy_grid[n], d)
            for d, n in enumerate(game_map.neighbors(square))
        )
        return Move(square, direction)
    else:
        border = any(neighbor.owner != myID for neighbor in game_map.neighbors(square))
        if not border:
            _, direction = min(
                (cells_to_border_grid[n], d)
                for d, n in enumerate(game_map.neighbors(square))
            )
            return Move(square, direction)
        else:
            return Move(square, STILL)


def heuristic(square):
    if square.owner == 0 and square.strength > 0:
        return square.production / square.strength
    else:
        # return total potential damage caused by overkill when attacking this square
        return sum(
            neighbor.strength
            for neighbor in game_map.neighbors(square)
            if neighbor.owner not in (0, myID)
        )


def distance_to_border_grid_init(square: Square):
    if square.is_mine or square.production:
        return 9999
    else:
        return 0


def border_grid_set():
    return dict(
        sorted(
            (
                (
                    square,
                    sum(n.production for n in square.neighbors if n.is_environment),
                )
                for square in game_map
                if square.is_inner_border
            ),
            key=operator.itemgetter(1),
        )
    )


def enemy_grid_set():
    return {square: None for square in game_map if square.is_other_player}


def border_grid_visit(square: Square) -> Iterable[Square]:
    if square.is_inner_border and any(
        n.production > 0 for n in square.neighbors if n.is_environment
    ):
        cells_to_border_grid[square] = 0
    else:
        cells_to_border_grid[square] = min(
            cells_to_border_grid[square],
            1
            + +square.production
            + min(cells_to_border_grid[n] for n in square.neighbors),
        )

    return (n for n in square.neighbors if n.is_mine)


def enemy_grid_visit(square: Square) -> Iterable[Square]:
    if square.is_other_player:
        cells_to_enemy_grid[square] = 0
    else:
        cells_to_enemy_grid[square] = min(
            cells_to_enemy_grid[square],
            1
            + +square.production
            + min(cells_to_enemy_grid[n] for n in square.neighbors),
        )

    return (n for n in square.neighbors if not (n.is_environment and n.strength > 0))


######################################################

myID, game_map = hlt.get_init()
hlt.send_init("MyPythonBot")

Square.myID = myID
Square.game_map = game_map

logger.setLevel(logging.INFO)

while True:
    game_map.get_frame()

    cells_to_border_grid = Grid("cells_to_border_grid", distance_to_border_grid_init)
    cells_to_enemy_grid = Grid("cells_to_enemy_grid", lambda x: 9999)

    bfs(border_grid_set(), border_grid_visit)
    bfs(enemy_grid_set(), enemy_grid_visit)

    logger.debug(cells_to_border_grid)
    logger.debug(cells_to_enemy_grid)

    moves = [move(square) for square in game_map if square.owner == myID]
    hlt.send_frame(moves)
