#!/usr/bin/python

import os.path
import sys
from argparse import ArgumentParser

_base_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(_base_dir, "lib"))

from pair import (
        parse_seeds, parse_history, parse_tournament,
        rate, Tournament, weighted_pairing,
        )

class FTE_Scale(object):
    """
    If an odd number of players remain, one bye will be given, otherwise none.
    Give the bye only to a player among the players with the fewest byes so far.
    In descending order of N, minimize the number of pairings occurring for the Nth time.
    Give the bye to a player with as few losses as possible.
    In descending order of N, minimize the number of pairings between players whose number of losses differ by N.
    Give the bye to the player with the best possible rank.
    Maximize the sum of the squares of the rank differences between paired players.
    """
    def __init__(self, lives, tourn):
        self.lives = lives
        self.tourn = tourn
        self.num_alive = len(tourn.live_players)
        if len(tourn.games):
            most_repeated_pairing = tourn.pair_counts.most_common(1)[0][1]
            self.pair_mul = (self.num_alive + 1) ** most_repeated_pairing
            self.most_games = tourn.played.most_common(1)[0][1]
        else:
            self.pair_mul = 1
            self.most_games = 0

    def bye(self, player):
        lives = self.lives
        num_alive = self.num_alive

        weight = self.most_games - self.tourn.played[player]
        weight *= self.pair_mul * lives
        weight += self.tourn.losses[player]
        weight *= lives * (num_alive + 1) * ((num_alive + 1) ** lives)
        weight += self.tourn.ranks[player]
        weight *= num_alive ** 2
        return weight

    def pair(self, p1, p2):
        lives = self.lives
        num_alive = self.num_alive

        weight = (num_alive + 1) ** self.tourn.pair_counts[frozenset((p1, p2))]
        weight *= lives ** 2 * ((num_alive + 1) ** lives)
        weight += (num_alive + 1) ** abs(
                self.tourn.losses[p1] - self.tourn.losses[p2])
        weight *= (num_alive + 1) * (num_alive ** 2)
        weight += num_alive ** 2 - (
                self.tourn.ranks[p1] - self.tourn.ranks[p2]) ** 2
        return weight

def parse_args(args=None):
    parser = ArgumentParser(description="Pair FTE tournament")
    parser.add_argument("-v", "--virtual", help="Virtual game weight",
            type=float, default=0.5)
    parser.add_argument("-l", "--lives", help="Number of lives",
            type=int, default=3)
    parser.add_argument("--utpr", help="Use UTPR as in WC2013 pairing rules",
            action="store_true")
    parser.add_argument("--ranks", help="Print player rankings",
            action="store_true")
    parser.add_argument("--seed_file", "--seeds", help="aaaa style player seeds")
    parser.add_argument("--game_file", "--games",
            help="aaaa style tournament history")
    parser.add_argument("tournament_state", help="Tournament state file",
            nargs="?")
    args = parser.parse_args(args)
    if args.seed_file and args.tournament_state:
        print "Cannot use both regular tournament state file and aaaa style"
        parser.print_help()
        sys.exit(1)
    if not args.seed_file and not args.tournament_state:
        print "Must give tournament state"
        parser.print_help()
        sys.exit(1)
    return args

def main(args=None):
    args = parse_args(args)
    if args.tournament_state:
        with open(args.tournament_state) as state_file:
            tourn = parse_tournament(state_file.read())
    else:
        with open(args.seed_file) as seed_file:
            seed_data = seed_file.read()
            tourn = parse_seeds(seed_data)
        if args.game_file:
            with open(args.game_file) as history_file:
                history_data = history_file.read()
                parse_history(tourn, history_data)

    stpr = rate(tourn.seeds, tourn.wins, tourn.pair_counts, args.virtual)
    tourn.live_players = [p for p in tourn.players
            if tourn.losses[p] < args.lives]
    if args.utpr:
        utpr = rate({p: 1500 for p in tourn.players},
                tourn.wins, tourn.pair_counts, args.virtual)
        def order(p):
            return (tourn.losses[p], -utpr[p], -stpr[p])
    else:
        def order(p):
            return (tourn.losses[p], -stpr[p])
    tourn.live_players.sort(key=order)
    tourn.ranks = {p: rank for rank, p in enumerate(tourn.live_players, start=1)}
    if args.ranks:
        for r, p in enumerate(tourn.live_players, 1):
            print "#", r, p, order(p)
    scale = FTE_Scale(args.lives, tourn)
    pairings, bye = weighted_pairing(tourn, scale)

    if bye:
        print "# Bye:", bye
    for p1, p2 in pairings:
        print p1, p2

if __name__ == "__main__":
    main()

