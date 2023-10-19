# Comp-472-Project-MVN

from __future__ import annotations
import argparse
import copy
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field
from time import sleep
from typing import Tuple, TypeVar, Type, Iterable, ClassVar
import random
import requests
import math

# maximum and minimum values for our heuristic scores (usually represents an end of game condition)
MAX_HEURISTIC_SCORE = 2000000000
MIN_HEURISTIC_SCORE = -2000000000

file_path = None


class UnitType(Enum):
    """Every unit type."""
    AI = 0
    Tech = 1
    Virus = 2
    Program = 3
    Firewall = 4


class Player(Enum):
    """The 2 players."""
    Attacker = 0
    Defender = 1

    def next(self) -> Player:
        """The next (other) player."""
        if self is Player.Attacker:
            return Player.Defender
        else:
            return Player.Attacker


class GameType(Enum):
    AttackerVsDefender = 0
    AttackerVsComp = 1
    CompVsDefender = 2
    CompVsComp = 3

##############################################################################################################


@dataclass(slots=True)
class Unit:
    player: Player = Player.Attacker
    type: UnitType = UnitType.Program
    health: int = 9
    # class variable: damage table for units (based on the unit type constants in order)
    damage_table: ClassVar[list[list[int]]] = [
        [3, 3, 3, 3, 1],  # AI
        [1, 1, 6, 1, 1],  # Tech
        [9, 6, 1, 6, 1],  # Virus
        [3, 3, 3, 3, 1],  # Program
        [1, 1, 1, 1, 1],  # Firewall
    ]
    # class variable: repair table for units (based on the unit type constants in order)
    repair_table: ClassVar[list[list[int]]] = [
        [0, 1, 1, 0, 0],  # AI
        [3, 0, 0, 3, 3],  # Tech
        [0, 0, 0, 0, 0],  # Virus
        [0, 0, 0, 0, 0],  # Program
        [0, 0, 0, 0, 0],  # Firewall
    ]

    def is_alive(self) -> bool:
        """Are we alive ?"""
        return self.health > 0

    def mod_health(self, health_delta: int):
        """Modify this unit's health by delta amount."""
        self.health += health_delta
        if self.health < 0:
            self.health = 0
        elif self.health > 9:
            self.health = 9

    def to_string(self) -> str:
        """Text representation of this unit."""
        p = self.player.name.lower()[0]
        t = self.type.name.upper()[0]
        return f"{p}{t}{self.health}"

    def __str__(self) -> str:
        """Text representation of this unit."""
        return self.to_string()

    def damage_amount(self, target: Unit) -> int:
        """How much can this unit damage another unit."""
        
        # calculate damage value 
        amount = self.damage_table[self.type.value][target.type.value]

        with open(file_path, 'a') as file:
            file.write(f"{amount}")

        if target.health - amount < 0:
            # if the value is negative then return the target's CURRENT health to be subtracted later
            # from the target's health to equal 0 and die eventually
            return target.health
        # Otherwise return the amount of damage and subtract from CURRENT target health
        return amount

    def repair_amount(self, target: Unit) -> int:
        """How much can this unit repair another unit."""
        
        # calculate repair value 
        amount = self.repair_table[self.type.value][target.type.value]

        with open(file_path, 'a') as file:
            file.write(f"{amount}")

        if target.health + amount > 9:
            # if the value is >9 then return (9 - target's CURRENT health) to be added later
            # to the target's health
            return 9 - target.health
        # Otherwise return the amount of repair and add to CURRENT target health
        return amount
##############################################################################################################


@dataclass(slots=True)
class Coord:
    """Representation of a game cell coordinate (row, col)."""
    row: int = 0
    col: int = 0

    def col_string(self) -> str:
        """Text representation of this Coord's column."""
        coord_char = '?'
        if self.col < 16:
            coord_char = "0123456789abcdef"[self.col]
        return str(coord_char)

    def row_string(self) -> str:
        """Text representation of this Coord's row."""
        coord_char = '?'
        if self.row < 26:
            coord_char = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"[self.row]
        return str(coord_char)

    def to_string(self) -> str:
        """Text representation of this Coord."""
        return self.row_string()+self.col_string()

    def __str__(self) -> str:
        """Text representation of this Coord."""
        return self.to_string()

    def clone(self) -> Coord:
        """Clone a Coord."""
        return copy.copy(self)

    def iter_range(self, dist: int) -> Iterable[Coord]:
        """Iterates over Coords inside a rectangle centered on our Coord."""
        for row in range(self.row-dist, self.row+1+dist):
            for col in range(self.col-dist, self.col+1+dist):
                yield Coord(row, col)

    def iter_adjacent(self) -> Iterable[Coord]:
        """Iterates over adjacent Coords."""
        yield Coord(self.row-1, self.col)
        yield Coord(self.row, self.col-1)
        yield Coord(self.row+1, self.col)
        yield Coord(self.row, self.col+1)

    @classmethod
    def from_string(cls, s: str) -> Coord | None:
        """Create a Coord from a string. ex: D2."""
        s = s.strip()
        for sep in " ,.:;-_":
            s = s.replace(sep, "")
        if (len(s) == 2):
            coord = Coord()
            coord.row = "ABCDEFGHIJKLMNOPQRSTUVWXYZ".find(s[0:1].upper())
            coord.col = "0123456789abcdef".find(s[1:2].lower())
            return coord
        else:
            return None

##############################################################################################################


@dataclass(slots=True)
class CoordPair:
    """Representation of a game move or a rectangular area via 2 Coords."""
    src: Coord = field(default_factory=Coord)
    dst: Coord = field(default_factory=Coord)

    def to_string(self) -> str:
        """Text representation of a CoordPair."""
        return self.src.to_string()+" "+self.dst.to_string()

    def __str__(self) -> str:
        """Text representation of a CoordPair."""
        return self.to_string()

    def clone(self) -> CoordPair:
        """Clones a CoordPair."""
        return copy.copy(self)

    def iter_rectangle(self) -> Iterable[Coord]:
        """Iterates over cells of a rectangular area."""
        for row in range(self.src.row, self.dst.row+1):
            for col in range(self.src.col, self.dst.col+1):
                yield Coord(row, col)

    @classmethod
    def from_quad(cls, row0: int, col0: int, row1: int, col1: int) -> CoordPair:
        """Create a CoordPair from 4 integers."""
        return CoordPair(Coord(row0, col0), Coord(row1, col1))

    @classmethod
    def from_dim(cls, dim: int) -> CoordPair:
        """Create a CoordPair based on a dim-sized rectangle."""
        return CoordPair(Coord(0, 0), Coord(dim-1, dim-1))

    @classmethod
    def from_string(cls, s: str) -> CoordPair | None:
        """Create a CoordPair from a string. ex: A3 B2"""
        s = s.strip()
        for sep in " ,.:;-_":
            s = s.replace(sep, "")
        if (len(s) == 4):
            coords = CoordPair()
            coords.src.row = "ABCDEFGHIJKLMNOPQRSTUVWXYZ".find(s[0:1].upper())
            coords.src.col = "0123456789abcdef".find(s[1:2].lower())
            coords.dst.row = "ABCDEFGHIJKLMNOPQRSTUVWXYZ".find(s[2:3].upper())
            coords.dst.col = "0123456789abcdef".find(s[3:4].lower())
            return coords
        else:
            return None

##############################################################################################################


@dataclass(slots=True)
class Options:
    """Representation of the game options."""
    dim: int = 5
    max_depth: int | None = 4
    min_depth: int | None = 2
    max_time: float | None = 5.0
    game_type: GameType = GameType.AttackerVsDefender
    alpha_beta: bool = True
    max_turns: int | None = 100
    randomize_moves: bool = True
    broker: str | None = None
    heuristic: str | None = "e0"
    alpha_beta_option: bool | None = False

##############################################################################################################


@dataclass(slots=True)
class Stats:
    """Representation of the global game statistics."""
    total_seconds: float = 0.0
    cumulative_evals: int = 0
    cumulative_evals_by_depth: dict[int, int] = field(default_factory=dict)
    cumulative_percentage_evals_by_depth: float = 0.0
    average_branching_factor: float = 0.0
##############################################################################################################


@dataclass(slots=True)
class Game:
    """Representation of the game state."""
    board: list[list[Unit | None]] = field(default_factory=list)
    next_player: Player = Player.Attacker   # Current Player is next_player
    turns_played: int = 0
    options: Options = field(default_factory=Options)
    stats: Stats = field(default_factory=Stats)
    _attacker_has_ai: bool = True
    _defender_has_ai: bool = True

    def __post_init__(self):
        """Automatically called after class init to set up the default board state."""
        dim = self.options.dim
        self.board = [[None for _ in range(dim)] for _ in range(dim)]
        md = dim-1
        self.set(Coord(0, 0), Unit(player=Player.Defender, type=UnitType.AI))
        self.set(Coord(1, 0), Unit(player=Player.Defender, type=UnitType.Tech))
        self.set(Coord(0, 1), Unit(player=Player.Defender, type=UnitType.Tech))
        self.set(Coord(2, 0), Unit(
            player=Player.Defender, type=UnitType.Firewall))
        self.set(Coord(0, 2), Unit(
            player=Player.Defender, type=UnitType.Firewall))
        self.set(Coord(1, 1), Unit(
            player=Player.Defender, type=UnitType.Program))
        self.set(Coord(md, md), Unit(player=Player.Attacker, type=UnitType.AI))
        self.set(Coord(md-1, md),
                 Unit(player=Player.Attacker, type=UnitType.Virus))
        self.set(Coord(md, md-1),
                 Unit(player=Player.Attacker, type=UnitType.Virus))
        self.set(Coord(md-2, md),
                 Unit(player=Player.Attacker, type=UnitType.Program))
        self.set(Coord(md, md-2),
                 Unit(player=Player.Attacker, type=UnitType.Program))
        self.set(Coord(md-1, md-1),
                 Unit(player=Player.Attacker, type=UnitType.Firewall))

    def clone(self) -> Game:
        """Make a new copy of a game for minimax recursion.

        Shallow copy of everything except the board (options and stats are shared).
        """
        new = copy.copy(self)
        new.board = copy.deepcopy(self.board)
        return new

    def is_empty(self, coord: Coord) -> bool:
        """Check if contents of a board cell of the game at Coord is empty (must be valid coord)."""
        return self.board[coord.row][coord.col] is None

    def get(self, coord: Coord) -> Unit | None:
        """Get contents of a board cell of the game at Coord."""
        if self.is_valid_coord(coord):
            return self.board[coord.row][coord.col]
        else:
            return None

    def set(self, coord: Coord, unit: Unit | None):
        """Set contents of a board cell of the game at Coord."""
        if self.is_valid_coord(coord):
            self.board[coord.row][coord.col] = unit

    def remove_dead(self, coord: Coord):
        """Remove unit at Coord if dead."""
        unit = self.get(coord)
        if unit is not None and not unit.is_alive():
            self.set(coord, None)
            if unit.type == UnitType.AI:
                if unit.player == Player.Attacker:
                    self._attacker_has_ai = False
                else:
                    self._defender_has_ai = False

    def mod_health(self, coord: Coord, health_delta: int):
        """Modify health of unit at Coord (positive or negative delta)."""
        target = self.get(coord)
        if target is not None:
            target.mod_health(health_delta)
            self.remove_dead(coord)

    def is_valid_distance(self, coords: CoordPair) -> bool:
        """Checks to see that the two coordinates are directly above, below or beside one another i.e. Distance = 1"""

        # create empty list
        adjacent_coordinates = list()

        # appends surrounding coordinates (above, below or beside) to adjacent_coordinates
        for coord in coords.src.iter_adjacent():
            adjacent_coordinates.append(coord)

        # distance is valid if dst coordinate is in adjacent_coordinates
        return coords.dst in adjacent_coordinates

    def is_in_combat(self, coords: CoordPair) -> bool:
        """Checks to see if the unit at src coordinate is in combat --check to see if there's at least 1 enemy adjacent to unit at src"""
        unit = self.get(coords.src)

        # iterate through adjacent coordinates
        for adjacent_coord in coords.src.iter_adjacent():
            adjacent_unit = self.get(adjacent_coord)
            # A check to make sure an adjacent_unit (exists) + (is an opponent unit)
            if (adjacent_unit is not None) and (adjacent_unit.player != unit.player):
                return True
        return False

    def is_valid_repair(self, unit_src: Unit, unit_dst: Unit) -> bool:
        """Checks to see if the move being made is a repair and if it's valid"""
        if unit_src is None or unit_dst is None:
            return False
        
        # only AI (0) and Tech (1) can repair
        if (unit_dst.player.value == unit_src.player.value) and ((unit_src.type.value == 0) or (unit_src.type.value == 1)):
            if (unit_dst.health < 9):
                return True

        return False

    def is_valid_movement_direction(self, unit_src: Unit, unit_dst: Unit, coords: CoordPair) -> bool:
        """Checks to see if the unit is moving in its allowed direction
        Tech and Virus units can move up, down, left and right.
        Remaining attackers may only move up and left. 
        Remaining defenders may only move down and right."""

        if unit_dst is not None:
            return False
        # If the unit is (1 = Tech) OR (2 = Virus)
        if (unit_src.type.value == 1 or unit_src.type.value == 2):
            return True

        # Attackers move up and left
        if unit_src.player.value == 0:
            if (coords.dst.col <= coords.src.col) and (coords.dst.row <= coords.src.row):
                return True
        # Defenders move down and right
        else:
            if (coords.dst.col >= coords.src.col) and (coords.dst.row >= coords.src.row):
                return True
        return False

    def is_valid_move(self, coords: CoordPair) -> bool:
        """Validate a move expressed as a CoordPair."""

        # A check to make sure the coord is valid
        if not self.is_valid_coord(coords.src) or not self.is_valid_coord(coords.dst):
            return False

        # Get unit at source and at destination 
        unit_src = self.get(coords.src)
        unit_dst = self.get(coords.dst)

        # A check to make sure a player does not move his opponent's unit
        if unit_src is None or unit_src.player != self.next_player:
            return False

        # A check for self-destruct
        if (unit_src is not None) and (unit_dst is not None) and (coords.src.col == coords.dst.col) and (coords.src.row == coords.dst.row):
            return True

        # A check to make sure that the destination coordinate is an adjacent square
        if not self.is_valid_distance(coords):
            return False

        ### ENGAGED IN COMBAT ###
        # A check to make sure if the current unit is ALLOWED TO MOVE WHILE IN COMBAT
        if self.is_in_combat(coords):
            # Check if destination unit is (not empty) or is (not my unit) AKA I can attack it
            # Destination has no unit --> (Invalid Move)
            if (unit_dst is None) and ((unit_src.type.value != 1) and (unit_src.type.value != 2)):
                return False
            # Destination is MY UNIT and is either (AI or TECH) --> (REPAIR)
            elif (unit_dst is not None and unit_src is not None) and (unit_dst.player.value == unit_src.player.value) and not self.is_valid_repair(unit_src, unit_dst):
                return False
            # Destination is an OPPONENT UNIT --> (ATTACK)
            else:
                return True

        ### NOT ENGAGED IN COMBAT ###
        # Check direction moved (which opponent you pressed on to attack)

        # A check to see if we are ALLOWED TO REPAIR
        if self.is_valid_repair(unit_src, unit_dst):
            return True

        # If no units are adjacent to me
        if not self.is_valid_movement_direction(unit_src, unit_dst, coords):
            return False

        return True

    def type_of_move(self, unit_src, unit_dst, coords) -> str:
        """Returns a string corresponding to the type of move being performed by the src unit:
        1. Invalid Move    
        2. Move            
        3. Attack          
        4. Self-Destruct    
        5. Repair    
        """

        # A check to make sure the move is valid
        valid = self.is_valid_move(coords)
        if valid:
            # MOVE
            if(unit_dst is None):
                return "Move"
            # ATTACK
            elif (unit_dst.player.value != unit_src.player.value):
                return "Attack"
            # SELF-DESTRUCT
            elif ((unit_src is not None) and (unit_dst is not None) and (coords.src.col == coords.dst.col) and (coords.src.row == coords.dst.row)):
                return "Self-Destruct"
            # REPAIR
            elif (unit_dst.player.value == unit_src.player.value):
                return "Repair"
        else:
            return "Invalid"

    def perform_self_destruct(self, unit_src: Unit, coords: CoordPair) -> Tuple[bool, str]:
        """Kills off the unit performing the self-destruct, reduces the health of the 
        surrounding units by 2 and removes any dead units from the board."""
        total_damage = 0
        
        #kill off src unit 
        self.mod_health(coords.src, -9)

        # reduces the health of the surrounding units by 2 
        for surrounding_coord in coords.src.iter_range(1):
            if self.get(surrounding_coord) is not None:
                self.mod_health(surrounding_coord, -2)
                self.remove_dead(surrounding_coord)
                total_damage = total_damage + 2

        with open(file_path, 'a') as file:
            file.write(
                f"self-destruct at {coords.src} \nself-destructed for {total_damage} total damage\n")
        return

    def perform_attack(self, unit_src: Unit, unit_dst: Unit, coords: CoordPair) -> Tuple[bool, str]:
        """Allows the src unit to attack the target unit, decreasing the health of both units by a 
        predetermined value defined in damage_table. If one of the units dies, it gets removed from the board."""
        with open(file_path, 'a') as file:
            file.write(
                f"attack from {coords.src} to {coords.dst} \ncombat damage: to source = ")

        # calculate damage and modify health value 
        damage = unit_dst.damage_amount(unit_src)
        self.mod_health(coords.src, -damage)
        self.remove_dead(coords.src)

        with open(file_path, 'a') as file:
            file.write(f", to target = ")

        # calculate damage and modify health value 
        damage = unit_src.damage_amount(unit_dst)
        self.mod_health(coords.dst, -damage)
        self.remove_dead(coords.dst)

        with open(file_path, 'a') as file:
            file.write("\n")

        return

    def perform_repair(self, unit_src: Unit, unit_dst: Unit, coords: CoordPair) -> Tuple[bool, str]:
        """Allows the src unit to repair the target unit, increasing the health of the target unit by a
        predetermined value defined in repair_table. """
        with open(file_path, 'a') as file:
            file.write(f"repair from {coords.src} to {coords.dst} \nrepaired ")

        # calculate repair and modify health value
        repair = unit_src.repair_amount(unit_dst)
        self.mod_health(coords.dst, repair)

        with open(file_path, 'a') as file:
            file.write(" health points \n")
        return

    def perform_move(self, coords: CoordPair) -> Tuple[bool, str]:
        """Validate and perform a move expressed as a CoordPair."""
        # Get unit at source
        unit_src = self.get(coords.src)
        unit_dst = self.get(coords.dst)

        # Get type of move 
        type_of_move = self.type_of_move(unit_src, unit_dst, coords)

        if unit_src is not None:
            with open(file_path, 'a') as file:
                file.write(f"\n\n\n{unit_src.player.name}: ")

        # once type of move to be played is determined, perform the move 
        if type_of_move == "Move":
            # Move logic
            self.set(coords.dst, self.get(coords.src))
            self.set(coords.src, None)

            with open(file_path, 'a') as file:
                file.write(f"move from {coords.src} to {coords.dst}\n")

            return (True, "")

        elif type_of_move == "Attack":
            self.perform_attack(unit_src, unit_dst, coords)
            return (True, "")

        elif type_of_move == "Self-Destruct":
            self.perform_self_destruct(unit_src, coords)
            return (True, "")

        elif type_of_move == "Repair":
            self.perform_repair(unit_src, unit_dst, coords)
            return (True, "")
        else:
            with open(file_path, 'a') as file:
                file.write(f"Invalid Move!\n")
            return (False, "Invalid Move")

    def next_turn(self):
        """Transitions game to the next turn."""
        self.next_player = self.next_player.next()
        self.turns_played += 1

    def to_string(self) -> str:
        """Pretty text representation of the game."""
        dim = self.options.dim
        output = ""
        output += f"Next player: {self.next_player.name}\n"
        output += f"Turns played: {self.turns_played}\n"
        coord = Coord()
        output += "\n   "
        for col in range(dim):
            coord.col = col
            label = coord.col_string()
            output += f"{label:^3} "
        output += "\n"
        for row in range(dim):
            coord.row = row
            label = coord.row_string()
            output += f"{label}: "
            for col in range(dim):
                coord.col = col
                unit = self.get(coord)
                if unit is None:
                    output += " .  "
                else:
                    output += f"{str(unit):^3} "
            output += "\n"
        return output

    def __str__(self) -> str:
        """Default string representation of a game."""
        return self.to_string()

    def is_valid_coord(self, coord: Coord) -> bool:
        """Check if a Coord is valid within out board dimensions."""
        dim = self.options.dim
        if coord.row < 0 or coord.row >= dim or coord.col < 0 or coord.col >= dim:
            return False
        return True

    def read_move(self) -> CoordPair:
        """Read a move from keyboard and return as a CoordPair."""
        while True:
            s = input(F'Player {self.next_player.name}, enter your move: ')
            coords = CoordPair.from_string(s)
            if coords is not None and self.is_valid_coord(coords.src) and self.is_valid_coord(coords.dst):
                return coords
            else:
                print('Invalid coordinates! Try again.')

    def human_turn(self):
        """Human player plays a move (or get via broker)."""
        if self.options.broker is not None:
            print("Getting next move with auto-retry from game broker...")
            while True:
                mv = self.get_move_from_broker()
                if mv is not None:
                    (success, result) = self.perform_move(mv)
                    print(f"Broker {self.next_player.name}: ", end='')
                    print(result)
                    if success:
                        self.next_turn()
                        break
                sleep(0.1)
        else:
            while True:
                mv = self.read_move()
                (success, result) = self.perform_move(mv)
                if success:
                    print(f"Player {self.next_player.name}: ", end='')
                    print(result)
                    self.next_turn()
                    break
                else:
                    print("The move is not valid! Try again.")

    def computer_turn(self) -> CoordPair | None:
        """Computer plays a move."""
        mv = self.suggest_move()
        if mv is not None:
            (success, result) = self.perform_move(mv)
            if success:
                print(f"Computer {self.next_player.name}: ", end='')
                print(result)
                self.next_turn()
        return mv

    def player_units(self, player: Player) -> Iterable[Tuple[Coord, Unit]]:
        """Iterates over all units belonging to a player."""
        for coord in CoordPair.from_dim(self.options.dim).iter_rectangle():
            unit = self.get(coord)
            if unit is not None and unit.player == player:
                yield (coord, unit)

    def is_finished(self) -> bool:
        """Check if the game is over."""
        return self.has_winner() is not None

    # def has_winner(self) -> Player | None:
    #     """Check if the game is over and returns winner"""
    #     if self.options.max_turns is not None and self.turns_played >= self.options.max_turns:
    #         return Player.Defender
    #     # gives win to defender in the case that both AIs die in the same move (Only happens when AI self-destructs and kills opponent AI)
    #     elif (not self._attacker_has_ai) and (not self._defender_has_ai):
    #         return Player.Defender
    #     elif self._attacker_has_ai:
    #         if self._defender_has_ai:
    #             return None
    #         else:
    #             return Player.Attacker
    #     elif self._defender_has_ai:
    #         return Player.Defender
    
    def has_winner(self) -> Player | None:
        """Check if the game is over and returns winner"""
        if self.options.max_turns is not None and self.turns_played >= self.options.max_turns:
            return Player.Defender
        if self._attacker_has_ai:
            if self._defender_has_ai:
                return None
            else:
                return Player.Attacker    
        return Player.Defender

    def move_candidates(self) -> Iterable[CoordPair]:
        """Generate valid move candidates for the next player."""
        move = CoordPair()
        for (src, _) in self.player_units(self.next_player):
            move.src = src
            for dst in src.iter_adjacent():
                move.dst = dst
                if self.is_valid_move(move):
                    yield move.clone()
            move.dst = src
            yield move.clone()

    def random_move(self) -> Tuple[int, CoordPair | None, float]:
        """Returns a random move."""
        move_candidates = list(self.move_candidates())
        random.shuffle(move_candidates)
        if len(move_candidates) > 0:
            return (self.heuristic_score_e2(), move_candidates[0])
        else:
            return (self.heuristic_score_e2(), None)


    def heuristic_score_e0(self) -> int:
        """Returns the heuristic score for current unit configuration"""
        # AI = 0, Tech = 1, Virus = 2, Program = 3, Firewall = 4
        # E0 = (3VP1 + 3TP1 + 3FP1 + 3PP1 + 9999AIP1) − (3VP2 + 3TP2 + 3FP2 + 3PP2 + 9999AIP2)
        # VPi = nb of Virus of Player i
        # TPi = nb of Tech of Player i
        # FPi = nb of Firewall of Player i
        # PPi = nb of Program of Player i
        # AIPi = nb of AI of Player i
        
        # initialize variables 
        VP1 = TP1 = FP1 = PP1 = AIP1 = VP2 = TP2 = FP2 = PP2 = AIP2 = 0

        # iterate through all current player units and count the number of each type of unit
        for (_, unit) in self.player_units(self.next_player):
            if unit.type.value == 0:
                AIP1 += 1
            elif unit.type.value == 1:
                TP1 += 1
            elif unit.type.value == 2:
                VP1 += 1
            elif unit.type.value == 3:
                PP1 += 1
            elif unit.type.value == 4:
                FP1 += 1
        
        # iterate through all next player units and count the number of each type of unit
        for (_, unit) in self.player_units(self.next_player.next()):
            if unit.type.value == 0:
                AIP2 += 1
            elif unit.type.value == 1:
                TP2 += 1
            elif unit.type.value == 2:
                VP2 += 1
            elif unit.type.value == 3:
                PP2 += 1
            elif unit.type.value == 4:
                FP2 += 1
                
        heuristic_score = (3*VP1 + 3*TP1 + 3*FP1 + 3*PP1 + 9999*AIP1) - (3*VP2 + 3*TP2 + 3*FP2 + 3*PP2 + 9999*AIP2)
        
        if heuristic_score > MAX_HEURISTIC_SCORE:
            heuristic_score = MAX_HEURISTIC_SCORE
        if heuristic_score < MIN_HEURISTIC_SCORE:
            heuristic_score = MIN_HEURISTIC_SCORE
        
        return heuristic_score
   
   
    def can_strike_to_kill(self, src, unit) -> bool:
        """Checks to see if the unit at src coordinate can strike to kill an enemy unit"""
        for coord in src.iter_adjacent():
            coord_unit = self.get(coord)
            if coord_unit is not None and coord_unit.player != unit.player:
                if unit.damage_amount(coord_unit) >= coord_unit.health:
                    return True
        return False
    
    def can_get_killed(self, src, unit) -> bool:
        """Checks to see if the unit at src coordinate can get killed by an enemy unit"""
        for coord in src.iter_adjacent():
            coord_unit = self.get(coord)
            if coord_unit is not None and coord_unit.player != unit.player:
                if coord_unit.damage_amount(unit) >= unit.health:
                    return True
        return False
    
    def distance_from_nearest_opponent(self, src, unit) -> int:
        """Returns the distance from the nearest opponent (Manhattan distance)."""
        min_distance = 1000
        for coord in CoordPair.from_dim(self.options.dim).iter_rectangle():
            coord_unit = self.get(coord)
            if coord_unit is not None and coord_unit.player != unit.player:
                manhattan_distance = abs(src.row - coord.row) + abs(src.col - coord.col)
                if manhattan_distance < min_distance:
                    min_distance = manhattan_distance
        return min_distance
    
    def multiplier(self, src, unit) -> int:
        """"Returns an int by which the value should be multiplied if the unit is in an offensive postion."""
        multiplier = 0
        can_get_killed = self.can_get_killed(src, unit)
        
        # if the unit can strike to kill an opponent, this is a good move
        if self.can_strike_to_kill(src, unit):
            multiplier += 8
        
         # if the unit can get killed by an opponent, this is a bad move
        if can_get_killed:
            multiplier -= 8
            
        # if the unit can take damage from an opponent and still live, this is okay 
        if self.distance_from_nearest_opponent(src, unit) == 1 and not can_get_killed:
            multiplier += 5
        
        return multiplier
        
    def heuristic_score_e1(self) -> int:
        """Returns the heuristic score for current unit configuration. Offensive Heuristic."""
        # (Coord(row=2, col=4), Unit(player=<Player.Attacker: 0>, type=<UnitType.Program: 3>, health=7))        
        # values of pieces differ by impotance: AI = 100. Tech = 80, Virus = 100, Program = 50, Firewall = 30
        
        # initialize variables 
        heuristic_score = 0

        # iterate through all current player units
        for (src, unit) in self.player_units(self.next_player):
            
            if unit.type.value == 0: # AI
                # if current player AI can die, avoid this move
                if self.can_get_killed(src, unit):
                    return MIN_HEURISTIC_SCORE
                heuristic_score += 100 + 100*self.multiplier(src, unit)
                
            elif unit.type.value == 1 or unit.type.value == 2: # Tech or Virus 
                heuristic_score += 80 + 80*self.multiplier(src, unit)
                
            elif unit.type.value == 3: # Program
                heuristic_score += 50 + 50*self.multiplier(src, unit)
                
            elif unit.type.value == 4: # Firewall
                heuristic_score += 30 + 30*self.multiplier(src, unit)
        
        # iterate through all opponent player units 
        for (src, unit) in self.player_units(self.next_player.next()):
            
            if unit.type.value == 0: # Opp AI
                # if opponent's AI can die, this is a good move
                if self.can_get_killed(src, unit):
                    return MAX_HEURISTIC_SCORE
                heuristic_score -= 100 + 100*self.multiplier(src, unit)
                
            elif unit.type.value == 1 or unit.type.value == 2: # Tech or Virus 
                heuristic_score -= 80 + 80*self.multiplier(src, unit)
                
            elif unit.type.value == 3: # Opp Program
                heuristic_score -= 50 + 50*self.multiplier(src, unit)
                
            elif unit.type.value == 4: # Opp Firewall
                heuristic_score -= 30 + 30*self.multiplier(src, unit)
        
            
        if heuristic_score > MAX_HEURISTIC_SCORE:
            heuristic_score = MAX_HEURISTIC_SCORE
        if heuristic_score < MIN_HEURISTIC_SCORE:
            heuristic_score = MIN_HEURISTIC_SCORE

        return heuristic_score
    
    def heuristic_score_e2(self) -> int:
        """Returns the heuristic score for current unit configuration. Health-based Heuristic."""
        # initialize variables 
        heuristic_score = 0

        # iterate through all current player units
        for (src, unit) in self.player_units(self.next_player):
            
            if unit.type.value == 0: # AI
                # of current player AI can die, avoid this move
                if self.can_get_killed(src, unit):
                    return MIN_HEURISTIC_SCORE
                heuristic_score += 100*unit.health
                
            elif unit.type.value == 1 or unit.type.value == 2: # Tech or Virus 
                heuristic_score += 80*unit.health
                
            elif unit.type.value == 3: # Program
                heuristic_score += 50*unit.health
                
            elif unit.type.value == 4: # Firewall
                heuristic_score += 30*unit.health
        
        # iterate through all opponent player units 
        for (src, unit) in self.player_units(self.next_player.next()):
            
            if unit.type.value == 0: # Opp AI
                # if oppenent's AI can die, this is a good move
                if self.can_get_killed(src, unit):
                    return MAX_HEURISTIC_SCORE
                heuristic_score -= 100*unit.health
                
            elif unit.type.value == 1 or unit.type.value == 2: # Tech or Virus 
                heuristic_score -= 80*unit.health
                
            elif unit.type.value == 3: # Opp Program
                heuristic_score -= 50*unit.health
                
            elif unit.type.value == 4: # Opp Firewall
                heuristic_score -= 30*unit.health
        
            
        if heuristic_score > MAX_HEURISTIC_SCORE:
            heuristic_score = MAX_HEURISTIC_SCORE
        if heuristic_score < MIN_HEURISTIC_SCORE:
            heuristic_score = MIN_HEURISTIC_SCORE

        return heuristic_score
        
        
    def is_maximizing_player(self, player: Player) -> bool:
        """Check if the player is the maximizing player."""
        
        # if Human is Attacker, maximizing player = Defender (AI)
        if self.options.game_type == GameType.AttackerVsComp:
            return player != Player.Attacker
        
        # if Human is Defender, maximizing player = Attacker (AI)
        elif self.options.game_type == GameType.CompVsDefender:
            return player != Player.Defender
        
        # if AI vs AI, maximizing player = current player
        else:
            return True
    
    def suggest_move(self) -> CoordPair | None:
        """Suggest the next move using minimax alpha beta. TODO: REPLACE RANDOM_MOVE WITH PROPER GAME LOGIC!!!"""
        start_time = datetime.now()
        (score, move) = self.random_move()
        elapsed_seconds = (datetime.now() - start_time).total_seconds()
        self.stats.total_seconds += elapsed_seconds
        print(f"Heuristic score: {self.heuristic_score_e2()}")
        # print(f"Average recursive depth: {avg_depth:0.1f}")
        print(f"Cumulative evals by depth", end='')
        for k in sorted(self.stats.cumulative_evals_by_depth.keys()):
            print(f"{k}:{self.stats.cumulative_evals_by_depth[k]} ", end='')
        # total_evals = sum(self.stats.cumulative_evals_by_depth.values())
        # if self.stats.total_seconds > 0:
        #     print(
        #         f"Eval perf.: {total_evals/self.stats.total_seconds/1000:0.1f}k/s")
        print(f"Cumulative evals: {self.stats.cumulative_evals}")
        print(f"Cumulative % evals by depth: {self.stats.cumulative_percentage_evals_by_depth}")
        print(f"Average branching factor: {self.stats.average_branching_factor}")
        print()
        print(f"Time for this action: {elapsed_seconds:0.1f}s")
        return move
    
    #  def suggest_move(self) -> CoordPair | None:
    #     """Suggest the next move using minimax alpha beta. TODO: REPLACE RANDOM_MOVE WITH PROPER GAME LOGIC!!!"""
    #     start_time = datetime.now()
    #     (score, move, avg_depth) = self.random_move()
    #     elapsed_seconds = (datetime.now() - start_time).total_seconds()
    #     self.stats.total_seconds += elapsed_seconds
    #     print(f"Heuristic score: {score}")
    #     print(f"Average recursive depth: {avg_depth:0.1f}")
    #     print(f"Evals per depth: ", end='')
    #     for k in sorted(self.stats.evaluations_per_depth.keys()):
    #         print(f"{k}:{self.stats.evaluations_per_depth[k]} ", end='')
    #     print()
    #     total_evals = sum(self.stats.evaluations_per_depth.values())
    #     if self.stats.total_seconds > 0:
    #         print(
    #             f"Eval perf.: {total_evals/self.stats.total_seconds/1000:0.1f}k/s")
    #     print(f"Elapsed time: {elapsed_seconds:0.1f}s")
    #     return move

    def post_move_to_broker(self, move: CoordPair):
        """Send a move to the game broker."""
        if self.options.broker is None:
            return
        data = {
            "from": {"row": move.src.row, "col": move.src.col},
            "to": {"row": move.dst.row, "col": move.dst.col},
            "turn": self.turns_played
        }
        try:
            r = requests.post(self.options.broker, json=data)
            if r.status_code == 200 and r.json()['success'] and r.json()['data'] == data:
                # print(f"Sent move to broker: {move}")
                pass
            else:
                print(
                    f"Broker error: status code: {r.status_code}, response: {r.json()}")
        except Exception as error:
            print(f"Broker error: {error}")

    def get_move_from_broker(self) -> CoordPair | None:
        """Get a move from the game broker."""
        if self.options.broker is None:
            return None
        headers = {'Accept': 'application/json'}
        try:
            r = requests.get(self.options.broker, headers=headers)
            if r.status_code == 200 and r.json()['success']:
                data = r.json()['data']
                if data is not None:
                    if data['turn'] == self.turns_played+1:
                        move = CoordPair(
                            Coord(data['from']['row'], data['from']['col']),
                            Coord(data['to']['row'], data['to']['col'])
                        )
                        print(f"Got move from broker: {move}")
                        return move
                    else:
                        # print("Got broker data for wrong turn.")
                        # print(f"Wanted {self.turns_played+1}, got {data['turn']}")
                        pass
                else:
                    # print("Got no data from broker")
                    pass
            else:
                print(
                    f"Broker error: status code: {r.status_code}, response: {r.json()}")
        except Exception as error:
            print(f"Broker error: {error}")
        return None


def get_user_input():
    '''Prompt the user for input for each parameter'''
    max_depth = int(input("Enter max depth: "))
    max_time = float(input("Enter max time in seconds: "))
    game_type = input("Enter game type (auto|attacker|defender|manual): ")
    #broker = input("Enter broker (optional): ")
    max_turns = int(input("Enter max turns: "))
    heuristic = input("Enter heuristic name (e0|e1|e2): ")
    alpha_beta_option = input("Enter alpha-beta option (on|off): ")

    # create the name for the output file
    global file_path
    file_path = f"gameTrace-b-t-{max_turns}.txt"

    return game_type, max_time, max_depth, max_turns, heuristic, alpha_beta_option


def game_board_config(file_path: str, game: Game):
    '''Print the current game board configuration'''
    with open(file_path, 'a') as file:
        file.write(str(game))
        file.write("\n")


##############################################################################################################

def main():
    # Get user input
    game_type, max_time, max_depth, max_turns, heuristic, alpha_beta_option= get_user_input()

    # create the output trace file
    with open(file_path, 'w') as file:
        file.write(f"The game parameters:\n"
                   f"The value of the timeout in seconds t: {max_time}\n"
                   f"The max number of turns: {max_turns}\n"
                   f"Alpha-beta is (on or off): {alpha_beta_option}\n"
                   f"The play mode: {game_type}\n"
                   f"The name of the heuristic: {heuristic}\n\n"
                   )

    # parse the game type
    if game_type == "attacker":
        game_type = GameType.AttackerVsComp
    elif game_type == "defender":
        game_type = GameType.CompVsDefender
    elif game_type == "manual":
        game_type = GameType.AttackerVsDefender
    else:
        game_type = GameType.CompVsComp

    # set up game options
    options = Options(game_type=game_type)

    # override class defaults via command line options
    if max_depth is not None:
       options.max_depth = max_depth
    if max_time is not None:
       options.max_time = max_time
    # if broker is not None:
    #    options.broker = broker
    if max_turns is not None:
        options.max_turns = max_turns
    if heuristic is not None:
        options.heuristic = heuristic.lower().strip()
        
    if alpha_beta_option is not None:
       if alpha_beta_option.lower().strip() == "on": 
            options.alpha_beta_option = True
       else: 
           options.alpha_beta_option = False

    # create a new game
    game = Game(options=options)

    # append initial configuration to the output trace file
    with open(file_path, 'a') as file:
        file.write(f"-----------INITIAL CONFIGURATION-----------\n")

    # the main game loop
    while True:
        print()
        print(game)
        # append the current game board configuration to the output trace file
        game_board_config(file_path, game)
        winner = game.has_winner()
        # append the winner to the output trace file
        if winner is not None:
            print(f"----------------Game Over----------------\n\n{winner.name} wins in {game.turns_played} turns\n")
            with open(file_path, 'a') as file:
                file.write(f"----------------Game Over----------------\n")
                file.write(
                    f"{winner.name} wins in {game.turns_played} turns\n")
            break
        if game.options.game_type == GameType.AttackerVsDefender:
            game.human_turn()
        elif game.options.game_type == GameType.AttackerVsComp and game.next_player == Player.Attacker:
            game.human_turn()
        elif game.options.game_type == GameType.CompVsDefender and game.next_player == Player.Defender:
            game.human_turn()
        else:
            player = game.next_player
            move = game.computer_turn()
            if move is not None:
                game.post_move_to_broker(move)
            else:
                print("Computer doesn't know what to do!!!")
                exit(1)

##############################################################################################################


if __name__ == '__main__':
    main()
