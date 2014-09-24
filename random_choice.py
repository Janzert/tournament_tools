#!/usr/bin/env python
"""
This expects to be given a yaml file that looks like:

---
seed: H9gA9rKXroUPkMBa4dnjY55HDQct
seed_hash: e516033c754ef4953fc20f9af22a4519498416b6
# Add DJI closing price on Sep 23, 2014 into seed
# Taken from http://finance.yahoo.com/q/hp?s=^DJI+Historical+Prices
seed_add: 1705587

selections: 5
choices:
  - [player1, 10]
  - [player2, 15]
  - [player3, 10]
  - [player4, 6]
  - [player5, 3]
  - [player6, 1]
  - [player7, 1]

Using the seed to initialize the random generator and verifying that the given
hash matches the seed. The program then makes the number of selections
requested by making a series of weighted random choices from the list.

You can generate a random seed and corresponding hash by running the program
with the --gen-seed option.

"""

import argparse
import base64
import binascii
import numbers
import os
import sys

from hashlib import sha1

import yaml

class Random(object):
    def __init__(self, seed):
        self.seed = seed
        self.count = 0
        self.max_rand = (2 ** (sha1().digest_size * 8)) - 1

    def next(self):
        countbytes = str(self.count).encode("ascii")
        hashinput = countbytes + self.seed + countbytes
        self.count += 1
        return int(sha1(hashinput).hexdigest(), 16)

    def randint(self, a, b):
        if b < a:
            raise ValueError("Maximum value must be >= minimum")
        interval = (b - a) + 1
        cutoff = self.max_rand - (self.max_rand % interval)

        candidate = self.next()
        while candidate >= cutoff:
            candidate = self.next()

        return a + (candidate % interval)

def parse_args(args):
    parser = argparse.ArgumentParser(
        description="Make weighted random selections", epilog=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--gen-seed", action="store_true")
    parser.add_argument("filename", nargs="?")
    args = parser.parse_args(args)
    if args.gen_seed and args.filename:
        print("Can not generate a seed and make a selection at the same time.")
        sys.exit(1)
    if not args.gen_seed and not args.filename:
        print("Must give a selection file to parse if not generating a seed.")
        sys.exit(1)
    return args

def main(args):
    args = parse_args(args)
    if args.gen_seed:
        seed = os.urandom(21)
        print("seed: " + base64.b64encode(seed).decode("utf-8"))
        print("seed_hash: " + sha1(seed).hexdigest())
        return 0

    with open(args.filename) as sfile:
        config = yaml.safe_load(sfile)
        if "seed" not in config or "seed_hash" not in config:
            print("Must include random seed and hash.")
            return 1
        seed = base64.b64decode(config["seed"])
        if config["seed_hash"] != sha1(seed).hexdigest():
            print("Seed does not match seed hash.")
            return 1

        if "seed_add" not in config:
            print("WARNING: No supplemental seed found.")
        else:
            # convert supplemental seed to byte sequence
            sup_str = "%x" % (config["seed_add"],)
            if len(sup_str) % 2 != 0:
                sup_str = "0" + sup_str
            seed += binascii.unhexlify(sup_str)
        random = Random(seed)
        print("seed: " + config["seed"])
        if "choices" not in config:
            print("File does not contain list of choices")
            return 1
        selections = config.get("selections", 1)
        choices = config["choices"]
        choices.sort()
        for c, w in choices:
            if not isinstance(w, numbers.Integral):
                print("Weights must be integers.")
                print(c, w)
                return 1
        print("Choosing %d of %d choices." % (selections, len(choices)))
        for picked in range(selections):
            summed = 0
            sweights = list()
            for c, w in choices:
                summed += w
                sweights.append((c, summed))
            selected_sum = random.randint(1, summed)
            s_ix = 0
            while selected_sum > sweights[s_ix][1]:
                s_ix += 1
            assert sweights[s_ix][0] == choices[s_ix][0]
            print("Selected %s with weight %d of %d with random number %d" % (
                    choices[s_ix][0], choices[s_ix][1], summed, selected_sum))
            del choices[s_ix]

if __name__ == "__main__":
    main(sys.argv[1:])
