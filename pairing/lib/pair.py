
import math
import sys
from collections import Counter, defaultdict

from mwmatching import maxWeightMatching

def parse_seeds(seed_data):
    """ Parse aaaa style seed file """
    players = []
    seeds = dict()
    for line_num, line in enumerate(seed_data.splitlines(), start=1):
        line = line.strip()
        if len(line) == 0 or line.startswith("#"):
            continue
        player, rating = line.split()[:2]
        try:
            rating = float(rating)
        except ValueError:
            raise ValueError("Bad rating for player %s found at line %d",
                    player, line_num)
        players.append(player)
        seeds[player] = rating
    return tuple(players), seeds

def parse_history(history_data, active):
    """ Parse aaaa style game history file """
    games = list()
    for line_num, line in enumerate(history_data.splitlines(), start=1):
        line = line.strip()
        if len(line) == 0 or line.startswith("#"):
            continue
        words = line.split()
        p1 = words[0]
        if len(words) == 1:
            if p1 in active:
                active.remove(p1)
            else:
                active.add(p1)
            continue
        if p1 not in active:
            raise ValueError(
                    "Unrecognized player 1 (%s) in history at line %d" % (
                    p1, line_num))
        p2 = words[1]
        if p2 not in active:
            raise ValueError(
                    "Unrecognized player 2 (%s) in history at line %d" % (
                    p2, line_num))
        if len(words) == 2:
            # double forfeit
            games.append((p1, p2, ("double loss",)))
            continue
        winner = words[2]
        if winner not in (p1, p2):
            raise ValueError(
                    "Winner (%s) not a player of game in history at line %d" % (
                    winner, line_num))
        games.append((p1, p2, ("winner", winner)))
    games = tuple(games)
    return games

def parse_tournament(tourn_state):
    players = set()
    seeds = dict()
    games = list()
    def parse_player(line_num, line):
        tokens = line.split()
        if len(tokens) != 2:
            raise ValueError("Bad player entry at line %d" % (line_num,))
        name, seed = tokens
        seed = float(seed)
        if name in seeds:
            raise ValueError(
                    "Duplicate player entry found for %s at line %d" % (
                        name, line_num))
        seeds[name] = seed
        players.add(name)
    def parse_remove(line_num, line):
        if line not in seeds:
            raise ValueError("Tried to remove unknown player %s at line %d" % (
                line, line_num))
        if line not in players:
            raise ValueError(
                    "Tried to remove already removed player %s at line %d" % (
                        line, line_num))
        players.remove(line)
    def parse_add(line_num, line):
        if line not in seeds:
            raise ValueError("Tried to re-add unknown player %s at line %d" % (
                line, line_num))
        players.add(line)
    def parse_bye(line_num, line):
        tokens = line.split()
        if len(tokens) == 2:
            player, result = tokens
        else:
            player = line
        if player not in seeds:
            raise ValueError("Gave bye to unknown player %s at line %d" % (
                line, line_num))
        if player not in players:
            raise ValueError("Gave bye to removed player %s at line %d" % (
                line, line_num))
    def parse_game(line_num, line):
        tokens = line.split(None, 2)
        if len(tokens) != 3:
            raise ValueError("Bad game entry at line %d" % (line_num,))
        p1, p2, result = tokens
        if p1 not in seeds:
            raise ValueError("Unknown player 1 '%s' in game at line %d" % (
                p1, line_num))
        if p2 not in seeds:
            raise ValueError("Unknown player 2 '%s' in game at line %d" % (
                p2, line_num))
        if result.startswith("winner"):
            tokens = result.split(None, 1)
            if len(tokens) != 2:
                raise ValueError("Bad game result at line %d" % (line_num,))
            winner = tokens[1]
            if winner not in (p1, p2):
                raise ValueError(
                        "Recorded winner %s not a player in game at line %d" % (
                            winner, line_num))
            games.append((p1, p2, ("winner", winner)))
        elif result in ("draw", "double win", "double loss", "no decision",
                "vacated"):
            games.append((p1, p2, (result,)))
        else:
            raise ValueError("Unrecognized result %s for game at line %d" % (
                result, line_num))
    type_handlers = {
            "player": parse_player,
            "remove": parse_remove,
            "add": parse_add,
            "bye": parse_bye,
            "game": parse_game,
            "pair": parse_game,
            "pick": parse_game,
            }
    for line_num, line in enumerate(tourn_state.splitlines(), start=1):
        line = line.strip()
        if len(line) == 0 or line[0] == "#" or line[0] == "*":
            continue
        tokens = line.split(None, 1)
        if len(tokens) > 1:
            ltype, lrest = tokens
        elif toks[0] == "stop":
            break
        else:
            raise ValueError("Unrecognized entry at line %d" % (line_num,))
        try:
            type_handlers[ltype](line_num, lrest)
        except KeyError:
            raise ValueError("Unrecognized line type %s at line %d" % (
                ltype, line_num))
    players = frozenset(players)
    games = tuple(games)
    return players, seeds, games

def rate(seeds, scores, pair_counts, virtual_weight):
    scores = Counter(scores)
    scores.update({p: 0.5 * virtual_weight for p in seeds.keys()})
    tuple_counts = defaultdict(int)
    tuple_counts.update({tuple(p): c for p, c in pair_counts.items()})
    tuple_counts.update({tuple(reversed(p)): c for p, c in tuple_counts.items()})
    max_rating = max(seeds.values())
    min_rating = min(seeds.values())
    mid_rating = (min_rating + max_rating) / 2.0
    CF = math.log(10) / 400.0
    # convert from elo to ratio
    seeds = {p: math.exp((s - mid_rating) * CF) for p, s in seeds.items()}
    old_rating = dict(seeds)
    old_error = float('inf')
    new_rating = dict()
    while True:
        new_error = 0
        for player, seed in seeds.items():
            rating = old_rating[player]
            # anchor
            inverse_sum = 1 / (rating + seed)
            predicted_score = [virtual_weight * rating * inverse_sum]
            derivative = [virtual_weight * seed * inverse_sum ** 2]

            for opponent in seeds.keys():
                if player == opponent:
                    continue
                weight = tuple_counts[(player, opponent)]
                if weight != 0:
                    op_rating = old_rating[opponent]
                    inverse_sum = 1 / (rating + op_rating)
                    predicted_score.append(weight * rating * inverse_sum)
                    derivative.append(weight * op_rating * inverse_sum ** 2)
            predicted_score = math.fsum(predicted_score)
            derivative = math.fsum(derivative)
            error = predicted_score - scores[player]
            new_rating[player] = max(0.5 * rating, rating - error / derivative)
            new_error += error ** 2
        if new_error < old_error:
            old_error = new_error
            old_rating = dict(new_rating)
        else:
            break
    # round to 12 significant decimal places
    ratings = {p: round(r, 11-int(math.floor(math.log10(r))))
            for p, r in old_rating.items()}
    # convert back to elo range
    ratings = {p: (math.log(r) / CF) + mid_rating
            for p, r in ratings.items()}
    return ratings

def add_stats(tourn):
    tourn.played = Counter()
    tourn.wins = Counter()
    tourn.draws = Counter()
    tourn.losses = Counter()
    tourn.pair_counts = Counter()
    for g in tourn.games:
        if g[2][0] == "winner":
            if g[2][1] != g[0]:
                tourn.losses[g[0]] += 1
            if g[2][1] != g[1]:
                tourn.losses[g[1]] += 1
            tourn.wins[g[2][1]] += 1
        elif g[2][0] == "draw":
            tourn.draws[g[0]] += 1
            tourn.draws[g[1]] += 1
        elif g[2][0] == "double win":
            tourn.wins[g[0]] += 1
            tourn.wins[g[1]] += 1
        elif g[2][0] == "double loss":
            tourn.losses[g[0]] += 1
            tourn.losses[g[1]] += 1
        # a "no decison" result doesn't assign any win or loss but does count
        # as a game played
        if g[2][0] != "vacated":
            tourn.played[g[0]] += 1
            tourn.played[g[1]] += 1
            pset = frozenset(g[:2])
            tourn.pair_counts[pset] += 1
    return tourn

def weighted_pairing(tourn, scale):
    players = tourn.live_players
    num_alive = len(players)

    weights = []
    for p1_ix, p1 in enumerate(players):
        for p2_ix, p2 in enumerate(players[p1_ix + 1:], p1_ix + 1):
            wt = scale.pair(p1, p2)
            weights.append((p1_ix, p2_ix, 0 - wt))
        if num_alive % 2 == 1:
            wt = scale.bye(p1)
            weights.append((p1_ix, num_alive, 0 - wt))
    opponents = maxWeightMatching(weights, maxcardinality=True)
    weight_dict = {(v1, v2): wt for v1, v2, wt in weights}
    result_weight = sum(weight_dict[(v1, v2)] for v1, v2 in enumerate(opponents)
        if v1 < v2)

    if num_alive % 2 == 1:
        bye = players[opponents.index(num_alive)]
    else:
        bye = None
    pairings = [(players[p1_ix], players[p2_ix])
            for p1_ix, p2_ix in enumerate(opponents[:num_alive])
            if p2_ix != num_alive and p1_ix < p2_ix
            ]
    return pairings, bye

