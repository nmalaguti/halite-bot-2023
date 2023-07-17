"""
A Python-based Halite starter-bot framework.

This module contains a Pythonic implementation of a Halite starter-bot framework.
In addition to a class (GameMap) containing all information about the game world
and some helper methods, the module also implements the functions necessary for
communicating with the Halite game environment.
"""

import sys
from dataclasses import dataclass, field
from itertools import chain, zip_longest
from typing import ClassVar, Iterable, List, Tuple, TypeAlias


def grouper(iterable, n, fillvalue=None):
    "Collect data into fixed-length chunks or blocks"
    # grouper('ABCDEFG', 3, 'x') --> ABC DEF Gxx"
    args = [iter(iterable)] * n
    return zip_longest(*args, fillvalue=fillvalue)


# Because Python uses zero-based indexing, the cardinal directions have a different mapping in this Python starterbot
# framework than that used by the Halite game environment.  This simplifies code in several places.  To accommodate
# this difference, the translation to the indexing system used by the game environment is done automatically by
# the send_frame function when communicating with the Halite game environment.

Direction: TypeAlias = int

NORTH, EAST, SOUTH, WEST, STILL = range(5)


def opposite_cardinal(direction: Direction) -> Direction:
    "Returns the opposing cardinal direction."
    return (direction + 2) % 4 if direction != STILL else STILL


@dataclass(frozen=True)
class Square:
    myID: ClassVar[int] = None
    game_map: ClassVar["GameMap"] = None

    x: int = field(compare=True)
    y: int = field(compare=True)
    owner: int = field(compare=False)
    strength: int = field(compare=False)
    production: int = field(compare=False)

    @property
    def is_mine(self) -> bool:
        return self.owner == self.myID

    @property
    def is_environment(self) -> bool:
        return self.owner == self.game_map.ENVIRONMENT_ID

    @property
    def is_other_player(self) -> bool:
        return self.owner not in (self.game_map.ENVIRONMENT_ID, self.myID)

    @property
    def is_combat(self) -> bool:
        return self.is_environment and self.strength == 0

    @property
    def neighbors(self) -> Iterable["Square"]:
        return self.game_map.neighbors(self)

    @property
    def neighbors_and_self(self) -> Iterable["Square"]:
        return self.game_map.neighbors(self, 1, include_self=True)

    @property
    def is_inner_border(self) -> bool:
        return self.is_mine and any(not s.is_mine for s in self.neighbors)

    @property
    def is_outer_border(self) -> bool:
        return not self.is_mine and any(s.is_mine for s in self.neighbors)


@dataclass(frozen=True, slots=True)
class Move:
    square: Square
    direction: Direction


class GameMap:
    ENVIRONMENT_ID: ClassVar[int] = 0

    width: int
    height: int
    starting_player_count: int
    contents: List[List[Square]]

    def __init__(self, size_string, production_string, map_string=None):
        self.width, self.height = tuple(map(int, size_string.split()))
        self.production = tuple(
            tuple(map(int, substring))
            for substring in grouper(production_string.split(), self.width)
        )
        self.contents = []
        self.get_frame(map_string)
        self.starting_player_count = len(set(square.owner for square in self)) - 1

    def get_frame(self, map_string=None) -> None:
        "Updates the map information from the latest frame provided by the Halite game environment."
        if map_string is None:
            map_string = get_string()
        split_string = map_string.split()
        owners = list()
        while len(owners) < self.width * self.height:
            counter = int(split_string.pop(0))
            owner = int(split_string.pop(0))
            owners.extend([owner] * counter)
        assert len(owners) == self.width * self.height
        assert len(split_string) == self.width * self.height
        self.contents = [
            [
                Square(x, y, owner, strength, production)
                for x, (owner, strength, production) in enumerate(
                    zip(owner_row, strength_row, production_row)
                )
            ]
            for y, (owner_row, strength_row, production_row) in enumerate(
                zip(
                    grouper(owners, self.width),
                    grouper(map(int, split_string), self.width),
                    self.production,
                )
            )
        ]

    def __iter__(self) -> Iterable[Square]:
        "Allows direct iteration over all squares in the GameMap instance."
        return chain.from_iterable(self.contents)

    def neighbors(
        self, square: Square, n: int = 1, include_self: bool = False
    ) -> Iterable[Square]:
        "Iterable over the n-distance neighbors of a given square.  For single-step neighbors, the enumeration index provides the direction associated with the neighbor."
        assert isinstance(include_self, bool)
        assert isinstance(n, int) and n > 0
        if n == 1:
            combos = (
                (0, -1),
                (1, 0),
                (0, 1),
                (-1, 0),
                (0, 0),
            )  # NORTH, EAST, SOUTH, WEST, STILL ... matches indices provided by enumerate(game_map.neighbors(square))
        else:
            combos = (
                (dx, dy)
                for dy in range(-n, n + 1)
                for dx in range(-n, n + 1)
                if abs(dx) + abs(dy) <= n
            )
        return (
            self.contents[(square.y + dy) % self.height][(square.x + dx) % self.width]
            for dx, dy in combos
            if include_self or dx or dy
        )

    def get_target(self, square: Square, direction: Direction) -> Square:
        "Returns a single, one-step neighbor in a given direction."
        dx, dy = ((0, -1), (1, 0), (0, 1), (-1, 0), (0, 0))[direction]
        return self.contents[(square.y + dy) % self.height][
            (square.x + dx) % self.width
        ]

    def get_distance(self, sq1: Square, sq2: Square) -> int:
        "Returns Manhattan distance between two squares."
        dx = min(
            abs(sq1.x - sq2.x), sq1.x + self.width - sq2.x, sq2.x + self.width - sq1.x
        )
        dy = min(
            abs(sq1.y - sq2.y), sq1.y + self.height - sq2.y, sq2.y + self.height - sq1.y
        )
        return dx + dy


#####################################################################################################################
# Functions for communicating with the Halite game environment (formerly contained in separate module networking.py #
#####################################################################################################################


def send_string(s: str) -> None:
    sys.stdout.write(s)
    sys.stdout.write("\n")
    sys.stdout.flush()


def get_string() -> str:
    return sys.stdin.readline().rstrip("\n")


def get_init() -> Tuple[int, GameMap]:
    playerID = int(get_string())
    m = GameMap(get_string(), get_string())
    return playerID, m


def send_init(name: str) -> None:
    send_string(name)


def translate_cardinal(direction: Direction) -> int:
    "Translate direction constants used by this Python-based bot framework to that used by the official Halite game environment."
    # Cardinal indexing used by this bot framework is
    # ~ NORTH = 0, EAST = 1, SOUTH = 2, WEST = 3, STILL = 4
    # Cardinal indexing used by official Halite game environment is
    # ~ STILL = 0, NORTH = 1, EAST = 2, SOUTH = 3, WEST = 4
    # ~ >>> list(map(lambda x: (x+1) % 5, range(5)))
    # ~ [1, 2, 3, 4, 0]
    return (direction + 1) % 5


def send_frame(moves: Iterable[Move]) -> None:
    send_string(
        " ".join(
            str(move.square.x)
            + " "
            + str(move.square.y)
            + " "
            + str(translate_cardinal(move.direction))
            for move in moves
        )
    )
