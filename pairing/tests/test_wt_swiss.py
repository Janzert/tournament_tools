
import os.path
import sys
import unittest

import wt_swiss

simple_r1 = """\
player player1 1400
player player2 1200
player player3 1100
player player4 1000
"""
simple_r1_pairings = [["player1", "player3"], ["player2", "player4"]]
simple_r2 = simple_r1 + """\
Round 1
game player1 player3 winner player1
game player2 player4 winner player2
"""
simple_r2_pairings = [["player1", "player2"], ["player3", "player4"]]
simple_r3 = simple_r2 + """\
Round 2
game player1 player2 winner player1
game player3 player4 winner player3
"""
simple_r3_pairings = [["player1", "player4"], ["player2", "player3"]]
simple_r4 = simple_r3 + """\
Round 3
game player1 player4 winner player1
game player2 player3 winner player2
"""
simple_r4_pairings = [["player1", "player2"], ["player3", "player4"]]
simple_r5 = simple_r4 + """\
Round 4
game player1 player2 winner player1
game player3 player4 winner player4
"""
simple_r5_pairings = [["player1", "player3"], ["player2", "player4"]]
simple_rounds = [
    (simple_r1, simple_r1_pairings),
    (simple_r2, simple_r2_pairings),
    (simple_r3, simple_r3_pairings),
    (simple_r4, simple_r4_pairings),
    (simple_r5, simple_r5_pairings),
]

bye_r1 = """\
player player1 1500
player player2 1400
player player3 1300
player player4 1200
player player5 1100
"""
bye_r1_bye = "player5"
bye_r1_pairings = [["player1", "player3"], ["player2", "player4"]]
bye_r2 = bye_r1 + """\
Round 1
bye player5
game player1 player3 winner player1
game player2 player4 winner player2
"""
bye_r2_bye = "player4"
bye_r2_pairings = [["player1", "player2"], ["player3", "player5"]]
bye_r3 = bye_r2 + """\
Round 2
bye player4
game player1 player2 winner player1
game player3 player5 winner player3
"""
bye_r3_bye = "player3"
bye_r3_pairings = [["player1", "player4"], ["player2", "player5"]]
simple_byes = [
    (bye_r1, bye_r1_pairings, bye_r1_bye),
    (bye_r2, bye_r2_pairings, bye_r2_bye),
    (bye_r3, bye_r3_pairings, bye_r3_bye),
    ]

class PairingTestCase(unittest.TestCase):
    def test_simple_tournament(self):
        for simple_round, simple_pairings in simple_rounds:
            tourn = wt_swiss.parse_tournament(simple_round)
            pairings, bye = wt_swiss.get_pairings(tourn)
            pairings = [sorted(p) for p in pairings]
            pairings.sort()
            try:
                self.assertEqual(pairings, simple_pairings)
                self.assertEqual(bye, None)
            except AssertionError:
                print "Pairing error found for:"
                print simple_round
                raise

    def test_simple_bye(self):
        for sround, spairings, sbye in simple_byes:
            tourn = wt_swiss.parse_tournament(sround)
            pairings, bye = wt_swiss.get_pairings(tourn)
            pairings = [sorted(p) for p in pairings]
            pairings.sort()
            try:
                self.assertEqual(pairings, spairings)
                self.assertEqual(bye, sbye)
            except AssertionError:
                print "Pairing error found for simple bye:"
                print sround
                raise


class FilterPlayersTestCase(unittest.TestCase):
    def test_simple_filter(self):
        tourn = wt_swiss.parse_tournament(simple_r1)
        wt_swiss.filter_players(tourn, 3)
        self.assertEqual(len(tourn.players), 0)
        tourn = wt_swiss.parse_tournament(simple_r5)
        wt_swiss.filter_players(tourn, 3)
        self.assertEqual(tourn.players, frozenset(["player3", "player4"]))

