#!/usr/bin/python

# interesting funds and splits:
# 65001 split 10 ways causes naive to distribute 64999
# 100000 split 15 ways causes naive to distribute 100001
# WC2013 fund was 52357 split 14 ways
# WC2014 fund was 259011 split 15 ways

import argparse
import heapq
from fractions import Fraction

def naive(fund, num):
    total = sum(1 / float(n) for n in range(1, num+1))
    pers = [(1 / float(n)) / total for n in range(1, num+1)]
    return [int(round(fund * n)) for n in pers]

def naive_sainte_lague(fund, num):
    prop = [Fraction(1, n) for n in range(1, num+1)]
    pts = [0] * num
    quots = list(prop)
    for i in range(fund):
        mi = max(range(len(quots)), key=quots.__getitem__)
        pts[mi] += 1
        quots[mi] = prop[mi] / ((2*pts[mi]) + 1)
    return pts

def sainte_lague(fund, num):
    """ A performance improvement over the naive sainte-lague in that it uses
    a heap to hold quotient and player_rank pairs so it can run in
    O(fund_size log num_players) instead of O(fund_size * num_players).
    Because python's heapq is a min-heap we actually store 1/quotient.
    """
    prop = [Fraction(1, n) for n in range(1, num+1)]
    pts = [0] * num
    invquots = [(Fraction(n+1, 1), n) for n in range(num)]
    heapq.heapify(invquots)
    for i in range(fund):
        mi = invquots[0][1]
        pts[mi] += 1
        iq = 1 / (prop[mi] / ((2*pts[mi]) + 1))
        heapq.heapreplace(invquots, (iq, mi))
    return pts

dmethods = {
        "naive": naive,
        "sl": sainte_lague,
        "sainte-lague": sainte_lague,
        "naive_sl": naive_sainte_lague,
        }

def main():
    parser = argparse.ArgumentParser(
            description="Break up a prize fund proportional to ranking")
    parser.add_argument("fund", type=int, help="Size of the prize fund")
    parser.add_argument("num_winners", type=int, help="Number receiving prizes")
    parser.add_argument("-m", "--method", default="sainte-lague",
            choices=dmethods.keys(),
            help="Method to use when splitting the fund")
    args = parser.parse_args()

    distributor = dmethods[args.method]
    print "Splitting a fund of %d, %d ways" % (args.fund, args.num_winners)
    dist = distributor(args.fund, args.num_winners)
    prize_str = []
    for place, prize in enumerate(dist, start=1):
        prize_str.append("%d. %d" % (place, prize))
    prize_str = ", ".join(prize_str)
    print prize_str
    print "Total distributed:", sum(dist)

if __name__ == "__main__":
    main()

