
import math
import sys
from collections import Counter

from mwmatching import maxWeightMatching

def parse_seeds(seed_file):
    players = []
    seeds = dict()
    for line_num, line in enumerate(seed_file.readlines(), start=1):
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

def parse_history(history_file, active):
    games = list()
    players = active.keys()
    for line_num, line in enumerate(history_file.readlines(), start=1):
        line = line.strip()
        if len(line) == 0 or line.startswith("#"):
            continue
        words = line.split()
        p1 = words[0]
        if p1 not in players:
            raise ValueError(
                    "Unrecognized player 1 (%s) in history at line %d",
                    p1, line_num)
        if len(words) == 1:
            active[p1] = False if active[p1] else True
            continue
        p2 = words[1]
        if p2 not in players:
            raise ValueError(
                    "Unrecognized player 2 (%s) in history at line %d",
                    p2, line_num)
        if len(words) == 2:
            # double forfeit
            games.append((p1, p2, None))
            continue
        winner = words[2]
        if winner not in (p1, p2):
            raise ValueError(
                    "Winner (%s) not a player of game in history at line %d",
                    winner, line_num)
        games.append((p1, p2, winner))
    return games

def rate(seeds, scores, pair_counts, virtual_weight):
    scores = Counter(scores)
    scores.update({p: 0.5 * virtual_weight for p in seeds.keys()})
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
                weight = pair_counts[frozenset((player, opponent))]
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
    tourn.losses = Counter()
    tourn.pair_counts = Counter()
    for g in tourn.games:
        tourn.played[g[0]] += 1
        tourn.played[g[1]] += 1
        if g[2] != g[0]:
            tourn.losses[g[0]] += 1
        if g[2] != g[1]:
            tourn.losses[g[1]] += 1
        if not g[2]:
            continue
        tourn.wins[g[2]] += 1
        pset = frozenset(g[:2])
        tourn.pair_counts[pset] += 1
    return tourn

def pair_fte(tourn, lives):
    players = tourn.live_players
    wins = tourn.wins
    losses = tourn.losses
    played = tourn.played
    ranks = tourn.ranks

    num_alive = len(tourn.live_players)
    if len(tourn.games):
        pair_mul = (num_alive + 1) ** tourn.pair_counts.most_common(1)[0][1]
        most_games = played.most_common(1)[0][1]
    else:
        pair_mul = 1
        most_games = 0

    ###
    # If an odd number of players remain, one bye will be given, otherwise none.
    # Give the bye only to a player among the players with the fewest byes so far.
    # In descending order of N, minimize the number of pairings occurring for the Nth time.
    # Give the bye to a player with as few losses as possible.
    # In descending order of N, minimize the number of pairings between players whose number of losses differ by N.
    # Give the bye to the player with the best possible rank.
    # Maximize the sum of the squares of the rank differences between paired players.
    ###

    def bye_weight(player):
        weight = most_games - played[player]
        weight *= pair_mul * lives
        weight += losses[player]
        weight *= lives * (num_alive + 1) * ((num_alive + 1) ** lives)
        weight += ranks[player]
        weight *= num_alive ** 2
        return weight

    def pair_weight(p1, p2):
        weight = (num_alive + 1) ** tourn.pair_counts[frozenset((p1, p2))]
        weight *= lives ** 2 * ((num_alive + 1) ** lives)
        weight += (num_alive + 1) ** abs(losses[p1] - losses[p2])
        weight *= (num_alive + 1) * (num_alive ** 2)
        weight += num_alive ** 2 - (ranks[p1] - ranks[p2]) ** 2
        return weight

    weights = []
    for p1_ix, p1 in enumerate(players):
        for p2_ix, p2 in enumerate(players[p1_ix + 1:], p1_ix + 1):
            wt = pair_weight(p1, p2)
            weights.append((p1_ix, p2_ix, 0 - wt))
        if num_alive % 2 == 1:
            wt = bye_weight(p1)
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

