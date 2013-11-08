#!/usr/bin/python

import os.path
import sys
from argparse import ArgumentParser

_base_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(_base_dir, "lib"))

from pair import parse_seeds, parse_history, add_stats, rate, pair_fte

def parse_args(args=None):
    parser = ArgumentParser(description="Pair FTE tournament")
    parser.add_argument("-v", "--virtual", help="Virtual game weight",
            type=float, default=0.5)
    parser.add_argument("-l", "--lives", help="Number of lives",
            type=int, default=3)
    parser.add_argument("--utpr", help="Use UTPR as in WC2013 pairing rules",
            action="store_true")
    parser.add_argument("seed_file", help="File with player seeds")
    parser.add_argument("history_file", help="File with tournament history",
            nargs="?")
    return parser.parse_args(args)

def main(args=None):
    args = parse_args(args)
    class Tournament(object):
        pass
    tourn = Tournament()
    with open(args.seed_file) as seed_file:
        tourn.players, tourn.seeds = parse_seeds(seed_file)
    tourn.active = {p: True for p in tourn.players}
    if args.history_file:
        with open(args.history_file) as history_file:
            tourn.games = parse_history(history_file, tourn.active)
    else:
        tourn.games = list()

    add_stats(tourn)
    stpr = rate(tourn.seeds, tourn.wins, tourn.pair_counts, args.virtual)
    tourn.live_players = [p for p in tourn.players
            if tourn.active[p] and tourn.losses[p] < args.lives]
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
    pairings, bye = pair_fte(tourn, args.lives)

    for r, p in enumerate(tourn.live_players, 1):
        print "#", r, p, order(p)

    if bye:
        print "# Bye:", bye
    for p1, p2 in pairings:
        print p1, p2

if __name__ == "__main__":
    main()

