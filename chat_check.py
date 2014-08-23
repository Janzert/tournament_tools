#!/usr/bin/env python

import os
import sys
from argparse import ArgumentParser

import requests

_base_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(_base_dir, "pairing/lib"))

from pair import parse_tournament

def main():
    arg_parser = ArgumentParser()
    arg_parser.add_argument("--user", "-u")
    arg_parser.add_argument("--auth", "-a")
    arg_parser.add_argument("tournament_state")
    args = arg_parser.parse_args()

    payload = dict(cmd="users", user=args.user, auth=args.auth)
    resp = requests.post("http://arimaa.com/arimaa/chat/srv.php", data=payload)
    users = resp.content[3:].split()

    with open(args.tournament_state) as state_file:
        tourn = parse_tournament(state_file.read())

    missing = 0
    for player in tourn.players:
        if player not in users:
            print "Did not find %s in the chatroom" % (player,)
            missing += 1

    if missing == 0:
        print "All players present, good to go."
    else:
        print "Missing %d players!" % (missing,)

if __name__ == "__main__":
    main()

