
import os.path
import sys
import unittest

_base_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(_base_dir, "..", "lib"))

import pair

seeds_bad_rating = """
player1 1234.0
player2 abcdef
"""

seeds_bad_name = """\
player1 1234.0
player name 123
"""

seeds_good = """\
# test seed comment
player1 1234.0
player2 123
"""

history_active = set([
        "player1",
        "player2",
        "player3",
        "player4",
        ])

history_good = """\
player1 player2 player1
player3 player4 player4
player2
player4 player1 player1
player2
player1 player3 player3
player2 player4 player4
# last round
player3 player2
"""

history_good_games = (
        ("player1", "player2", ("winner", "player1")),
        ("player3", "player4", ("winner", "player4")),
        ("player4", "player1", ("winner", "player1")),
        ("player1", "player3", ("winner", "player3")),
        ("player2", "player4", ("winner", "player4")),
        ("player3", "player2", ("double loss",)),
        )

history_removed_player = """\
player1 player2 player1
player1
player2 player1 player2
"""

history_bad_winner = """\
player1 player2 player2
player3 player4 player1
"""

tournament_state_good = """\
player player1 1234.5
player player2 1200
player player3 1150.3
player player4 1100.2

# Round 1
game player1 player2 winner player1
pair player3 player4 winner player3

# Round 2
remove player2
bye player3
pick player4 player1 double loss

* Round 3
add player2
game player1 player3 double win
game player2 player4 no decision

# Round 4
game player2 player1 draw
game player4 player3 vacated

# Round 5 special bye tests
bye player2 win
bye player3 loss
"""

tournament_state_good_players = frozenset([
    "player1", "player2", "player3", "player4"])
tournament_state_good_seeds = {
        "player1": 1234.5, "player2": 1200,
        "player3": 1150.3, "player4": 1100.2,
        }
tournament_state_good_games = (
        ("player1", "player2", ("winner", "player1")),
        ("player3", "player4", ("winner", "player3")),
        ("player4", "player1", ("double loss",)),
        ("player1", "player3", ("double win",)),
        ("player2", "player4", ("no decision",)),
        ("player2", "player1", ("draw",)),
        ("player4", "player3", ("vacated",)),
        )

tournament_state_bad_name = """\
player player name 1234
"""
tournament_state_bad_rating = """\
player player1 1abd
"""
tournament_state_bad_remove = """\
player player1 1234
remove player2
"""
tournament_state_bad_add = """\
player player1 1234
add player2
"""
tournament_state_bad_bye_1 = """\
player player1 1234
bye player2
"""
tournament_state_bad_bye_2 = """\
player player1 1234
remove player1
bye player1
"""
tournament_state_bad_game_1 = """\
player player1 1234
player player2 1234
game player1 player2
"""
tournament_state_bad_game_2 = """\
player player1 1234
game player2 player1 winner player1
"""
tournament_state_bad_game_3 = """\
player player1 1234
player player2 1234
game player1 player2 winner
"""
tournament_state_bad_game_4 = """\
player player1 1234
player player2 1234
player player3 1234
game player1 player2 winner player3
"""
tournament_state_bad_game_5 = """\
player player1 1234
player player2 1234
game player1 player2 nonexistent
"""
bad_tournament_states = [
        tournament_state_bad_name,
        tournament_state_bad_rating,
        tournament_state_bad_remove,
        tournament_state_bad_add,
        tournament_state_bad_bye_1,
        tournament_state_bad_bye_2,
        tournament_state_bad_game_1,
        tournament_state_bad_game_2,
        tournament_state_bad_game_3,
        tournament_state_bad_game_4,
        tournament_state_bad_game_5,
        ]

class ParseTestCase(unittest.TestCase):
    def test_parse_seeds(self):
        with self.assertRaises(ValueError):
            pair.parse_seeds(seeds_bad_rating)
        with self.assertRaises(ValueError):
            pair.parse_seeds(seeds_bad_name)
        result = pair.parse_seeds(seeds_good)
        self.assertEqual(len(result), 2)
        players, seeds = result
        self.assertEqual(players, ("player1", "player2"))
        self.assertEqual(seeds, {"player1": 1234.0, "player2": 123})

    def test_parse_history(self):
        games = pair.parse_history(history_good, history_active)
        self.assertEqual(games, history_good_games)
        with self.assertRaises(ValueError):
            pair.parse_history(history_removed_player, history_active)
        with self.assertRaises(ValueError):
            pair.parse_history(history_bad_winner, history_active)

    def test_parse_tournament(self):
        tourn = pair.parse_tournament(tournament_state_good)
        self.assertEqual(tourn.players, tournament_state_good_players)
        self.assertEqual(tourn.seeds, tournament_state_good_seeds)
        self.assertEqual(tourn.games, tournament_state_good_games)
        for state in bad_tournament_states:
            try:
                with self.assertRaises(ValueError):
                    pair.parse_tournament(state)
            except AssertionError:
                print "parse_tournament did not raise ValueError on:"
                print state
                raise


