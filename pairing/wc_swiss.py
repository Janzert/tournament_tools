#!/usr/bin/python

import os.path
import sys
from argparse import ArgumentParser
from collections import Counter

_base_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(_base_dir, "lib"))

from pair import (
        assign_colors, parse_seeds, parse_history, parse_tournament,
        rate, weighted_pairing,
        )

class Swiss_Scale(object):
    """
    If an odd number of players remain, one bye will be given, otherwise none.
    2. Give the bye only to a player among the players with the fewest byes so
        far.
    3. In descending order of N, minimize the number of pairings occurring for
        the Nth time.
    4. Give the bye to a player with as many losses as possible.
    5. In descending order of N, minimize the number of pairings between players
        whose number of losses differ by N.
    6. Give the bye to the player with the worst possible rank.
    7. Minimize the sum of (for players with unequal losses, the square of their
        rank difference) plus (for players with equal losses, the absolute
        difference between their rank difference and half the number of players
        with that number of losses).

    """
    def __init__(self, tourn):
        self.tourn = tourn
        self.num_alive = len(tourn.players)
        self.num_with_losses = Counter()
        if len(tourn.games):
            most_repeated_pairing = tourn.pair_counts.most_common(1)[0][1]
            self.pair_mul = (self.num_alive + 1) ** most_repeated_pairing
            self.most_games = tourn.played.most_common(1)[0][1]
            self.most_losses = tourn.losses.most_common(1)[0][1]
            for p in tourn.players:
                self.num_with_losses[tourn.losses[p]] += 1
        else:
            self.pair_mul = 1
            self.most_games = 0
            self.most_losses = 0
            self.num_with_losses[0] = len(tourn.players)

    def bye(self, player):
        num_alive = self.num_alive

        # 2 bye to fewest bye player
        weight = self.tourn.byes[player]
        # 3 descending order of N, minimize number of pairings for Nth time
        weight *= self.pair_mul
        # 4 bye to most losses
        weight *= (self.most_losses + 1)
        weight += self.most_losses - self.tourn.losses[player]
        # 5 descending order of N, minimize pairings with losses differing by N
        weight *= (num_alive + 1) ** (self.most_losses + 1)
        # 6 bye to worst ranked
        weight *= (num_alive + 1)
        weight += self.num_alive - self.tourn.ranks[player]
        # 7 minimize rank differences
        weight *= (num_alive ** 2) + 1
        return weight

    def pair(self, p1, p2):
        num_alive = self.num_alive
        losses = self.tourn.losses

        # 3 descending order of N, minimize number of pairings for Nth time
        weight = (num_alive + 1) ** self.tourn.pair_counts[frozenset((p1, p2))]
        # 4 bye to most losses
        weight *= (self.most_losses + 1)
        # 5 descending order of N, minimize pairings with losses differing by N
        weight *= (num_alive + 1) ** (self.most_losses + 1)
        weight += (num_alive + 1) ** abs(losses[p1] - losses[p2])
        # 6 bye to worst ranked
        weight *= (num_alive + 1)
        # 7 minimize rank differences
        weight *= (num_alive ** 2) + 1
        rank_difference = abs(self.tourn.ranks[p1] - self.tourn.ranks[p2])
        if losses[p1] == losses[p2]:
            weight += abs(rank_difference - (
                self.num_with_losses[losses[p1]] / 2.))
        else:
            weight += (rank_difference) ** 2
        return weight

def filter_players(tourn, min_loss):
    players = [p for p in tourn.players if tourn.losses[p] >= min_loss]
    tourn.players = frozenset(players)

def get_pairings(tourn, virtual=0.5, use_utpr=False):
    stpr = rate(tourn.seeds, tourn, virtual)
    if use_utpr:
        utpr = rate({p: 1500 for p in tourn.seeds}, tourn, virtual)
        def order(p):
            return (tourn.losses[p], -utpr[p], -stpr[p])
    else:
        def order(p):
            return (tourn.losses[p], -stpr[p])
    tourn.player_order = {p: order(p) for p in tourn.players}
    sorted_players = sorted(tourn.players, key=order)
    tourn.ranks = {p: rank for rank, p in enumerate(sorted_players, start=1)}
    scale = Swiss_Scale(tourn)
    pairings, bye = weighted_pairing(tourn, scale)
    return pairings, bye

def parse_args(args=None):
    parser = ArgumentParser(description="Pair FTE tournament")
    parser.add_argument("-v", "--virtual", help="Virtual game weight",
            type=float, default=0.5)
    parser.add_argument("-l", "--prelives",
            help="Number of lives before being paired",
            type=int, default=3)
    parser.add_argument("--utpr", help="Use UTPR as in WC2013 pairing rules",
            action="store_true")
    parser.add_argument("--ranks", help="Print player rankings",
            action="store_true")
    parser.add_argument("--show-arbitrary",
            help="Indicate arbitrary color assignments",
            action="store_true")
    parser.add_argument("--seed_file", "--seeds",
            help="aaaa style player seeds")
    parser.add_argument("--history_file", "--games",
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
            tourn = parse_seeds(seed_file.read())
        if args.history_file:
            with open(args.history_file) as history_file:
                parse_history(tourn, history_file.read())

    if args.prelives > 0:
        filter_players(tourn, args.prelives)
    pairings, bye = get_pairings(tourn, args.virtual, args.utpr)
    if args.ranks:
        players = sorted(tourn.players, key=lambda p: tourn.ranks[p])
        for p in players:
            print "#", tourn.ranks[p], p, tourn.player_order[p]

    pairings, arbitrary = assign_colors(tourn, pairings)

    pairings.sort(key=lambda pr: min(tourn.ranks[pr[0]], tourn.ranks[pr[1]]))

    if bye:
        print "bye", bye
    for p1, p2 in pairings:
        if args.show_arbitrary:
            print "game", p1, p2, "A" if (p1, p2) in arbitrary else ""
        else:
            print "game", p1, p2

if __name__ == "__main__":
    main()

