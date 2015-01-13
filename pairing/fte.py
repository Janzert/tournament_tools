#!/usr/bin/python

import os.path
import sys
from argparse import ArgumentParser
from collections import Counter

_base_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(_base_dir, "lib"))

from pair import (
        assign_colors, from_eventlist,
        parse_seeds, parse_history, parse_tournament,
        rate, weighted_pairing,
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
        self.num_alive = len(tourn.players)
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

def filter_games(tourn, lives):
    losses = Counter()
    events = list()
    for event in tourn.events:
        if event[0] != "game":
            events.append(event)
            continue
        p1, p2, result = event[1]
        if losses[p1] >= lives and losses[p2] >= lives:
            continue
        if losses[p1] >= lives or losses[p2] >= lives:
            raise ValueError(
                "Found game between active and eliminated player, %s vs %s" % (
                    p1, p2))
        events.append(event)
        if result[0] == "winner":
            loser = p1 if result[1] == p2 else p2
            losses[loser] += 1
        elif result[0] == "double loss":
            losses[p1] += 1
            losses[p2] += 1
    return from_eventlist(events)

def get_pairings(tourn, lives, virtual=0.5, use_utpr=False):
    stpr = rate(tourn.seeds, tourn.wins, tourn.pair_counts, virtual)
    tourn.players = set([p for p in tourn.players if tourn.losses[p] < lives])
    if use_utpr:
        utpr = rate({p: 1500 for p in tourn.players},
                tourn.wins, tourn.pair_counts, virtual)
        def order(p):
            return (tourn.losses[p], -utpr[p], -stpr[p])
    else:
        def order(p):
            return (tourn.losses[p], -stpr[p])
    tourn.player_order = {p: order(p) for p in tourn.players}
    sorted_players = sorted(tourn.players, key=order)
    tourn.ranks = {p: rank for rank, p in enumerate(sorted_players, start=1)}
    scale = FTE_Scale(lives, tourn)
    pairings, bye = weighted_pairing(tourn, scale)
    return pairings, bye

def parse_args(args=None):
    parser = ArgumentParser(description="Pair FTE tournament")
    parser.add_argument("-v", "--virtual", help="Virtual game weight",
            type=float, default=0.5)
    parser.add_argument("-l", "--lives", help="Number of lives",
            type=int, default=3)
    parser.add_argument("--utpr", help="Use UTPR as in WC2013 pairing rules",
            action="store_true")
    parser.add_argument("--all-games",
            help="Use all games, including those by eliminated players",
            action="store_true")
    parser.add_argument("--ranks", help="Print player rankings",
            action="store_true")
    parser.add_argument("--show-arbitrary",
            help="Indicate arbitrary color assignments",
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

    if not args.all_games:
        tourn = filter_games(tourn, args.lives)
    pairings, bye = get_pairings(tourn, args.lives, args.virtual, args.utpr)
    if args.ranks:
        players = sorted(tourn.players, key=lambda p: tourn.ranks[p])
        for p in players:
            print "#", tourn.ranks[p], p, tourn.player_order[p][0],
            for r in tourn.player_order[p][1:]:
                print -r,
            print

    pairings, arbitrary = assign_colors(tourn, pairings)

    if bye:
        print "bye", bye
    for p1, p2 in pairings:
        if args.show_arbitrary:
            print "game", p1, p2, "A" if (p1, p2) in arbitrary else ""
        else:
            print "game", p1, p2

if __name__ == "__main__":
    main()

