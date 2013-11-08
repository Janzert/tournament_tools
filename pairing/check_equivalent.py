#!/usr/bin/python

# aaaa args 0 {seeds} .5 {games} 3 6
# aaaa <randomize_ties> <seeds> <virtual_weight> <games> <lives> <swiss_rounds>

import math
import random
import sys
from argparse import ArgumentParser
from subprocess import check_output

SEED_FILENAME = "cseeds"
GAMES_FILENAME = "cgames"

def get_pairings(cmdline):
    pair_str = check_output(cmdline, shell=True)
    pairs = [tuple(line.split()) for line in pair_str.splitlines()
            if not line.strip().startswith("#")]
    # drop byes from aaaa programs
    pairs = [p for p in pairs if len(p) != 1]
    return pairs

def check_round(args, prg_pairs):
    prg_opponents = []
    for prg, pairs in enumerate(prg_pairs, start=1):
        opponents = dict()
        for p1, p2 in pairs:
            if p1 in opponents or p2 in opponents:
                print prg_pairs
                raise ValueError("Program %d tried to pair someone twice")
            opponents[p1] = p2
            opponents[p2] = p1
        prg_opponents.append(opponents)

    opp1 = prg_opponents[0]
    opp2 = prg_opponents[1]
    for p1, p2 in opp1.items():
        if p1 not in opp2:
            if args.ignore_extra:
                continue
            print prg_pairs
            print "Program 2 did not pair %s when 1 did" % (p1,)
            return False
        if opp2[p1] != p2:
            print prg_pairs
            print "Program 1 paired %s versus %s 2 paired %s versus %s" % (
                    p1, p2, p1, opp2[p1])
            return False
        del opp2[p1]

    for p1, p2 in opp2.items():
        if p1 not in opp1:
            if args.ignore_extra:
                continue
            print prg_pairs
            print "Program 1 did not pair %s when 2 did" % (p1,)
            return False
        if opp1[p1] != p2:
            print prg_pairs
            print "Program 2 paired %s versus %s 1 paired %s versus %s" % (
                    p1, p2, p1, opp1[p1])
            return False
    return True

def create_seeds(num_players, rating_range, unique=True):
    seeds = set()
    mid_rating = max(1500, math.floor(rating_range / 2.0) + 1)
    min_rating = mid_rating - math.floor(rating_range / 2.0)
    max_rating = mid_rating + math.ceil(rating_range / 2.0)
    for n in range(num_players):
        new_seed = None
        while new_seed in seeds or new_seed is None:
            new_seed = random.randint(min_rating, max_rating)
        seeds.add(new_seed)
    seeds = list(seeds)
    seeds.sort(reverse=True)
    seeds = [("p%d" % (n,), s) for n, s in enumerate(seeds, start=1)]
    return seeds

def main(args=None):
    parser = ArgumentParser(
            description="Check if two pairing programs result in same pairings"
            )
    parser.add_argument("-x", "--ignore_extra", help="Ignore extra pairings",
            action="store_true")
    parser.add_argument("prg1", help="First pairing program")
    parser.add_argument("prg2", help="Second pairing program")
    args = parser.parse_args(args)

    cmdlines = []
    for prg in [args.prg1, args.prg2]:
        cmdline = prg.format(
                seeds = SEED_FILENAME, games = GAMES_FILENAME,
                )
        print cmdline
        cmdlines.append(cmdline)

    tested = 0
    pairs_match = True
    try:
        while pairs_match and tested < 20000:
            num_players = random.randint(16, 64)
            rating_range = random.randint(5, 25) * num_players
            seeds = create_seeds(num_players, rating_range)
            seeds = "\n".join("%s %d" % (p, s) for p, s in seeds)

            with open(SEED_FILENAME, "w") as seed_file:
                seed_file.write(seeds)

            rounds = []
            while pairs_match:
                with open(GAMES_FILENAME, "w") as game_file:
                    games_str = []
                    for round in rounds:
                        games_str.append("\n".join(" ".join(game)
                            for game in round) + "\n")
                    games_str = "\n".join(games_str)
                    game_file.write(games_str)

                prg_pairs = []
                for cmdline in cmdlines:
                    pairs = get_pairings(cmdline)
                    prg_pairs.append(pairs)

                min_pairs = (prg_pairs[0]
                    if len(prg_pairs[0]) < len(prg_pairs[1])
                    else prg_pairs[1])
                pairs_match = check_round(args, prg_pairs)

                if len(min_pairs) == 0:
                    break
                rounds.append([(p1, p2, random.choice((p1, p2)))
                    for p1, p2 in min_pairs])
            tested += 1
            if (tested % 10) == 0:
                sys.stdout.write(".")
                sys.stdout.flush()
    finally:
        print
        print "Rounds %d, players %d" % (len(rounds), num_players)
        print "Tournaments tested %d" % (tested,)


if __name__ == "__main__":
    main()

