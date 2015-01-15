
import hashlib
import math
import sys
from collections import Counter, defaultdict

from mwmatching import maxWeightMatching

class Tournament(object):
    def __init__(self):
        self.events = tuple()
        self.players = frozenset()
        self.seeds = dict()
        self.games = tuple()
        self.byes = Counter()
        self.rounds = None

    def update_stats(tourn):
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
            if g[2][0] != "vacated":
                pset = frozenset(g[:2])
                tourn.pair_counts[pset] += 1
            tourn.played[g[0]] += 1
            tourn.played[g[1]] += 1
        return tourn

def from_eventlist(events):
    players = set()
    seeds = dict()
    games = list()
    byes = Counter()
    cur_round = [0]
    def player_event(event_num, info):
        name, seed = info
        if name in seeds:
            raise ValueError(
                    "Duplicate player entry found for %s at event %d" % (
                        name, event_num))
        seeds[name] = seed
        players.add(name)
    def remove_event(event_num, info):
        player = info[0]
        if player not in seeds:
            raise ValueError("Tried to remove unknown player %s at event %d" % (
                player, event_num))
        if player not in players:
            raise ValueError(
                    "Tried to remove already removed player %s at event %d" % (
                        player, event_num))
        players.remove(player)
    def add_event(event_num, info):
        if info not in seeds:
            raise ValueError("Tried to re-add unknown player %s at event %d" % (
                event, event_num))
        players.add(player)
    def bye_event(event_num, info):
        player, result = info
        if player not in seeds:
            raise ValueError("Gave bye to unknown player %s at line %d" % (
                line, line_num))
        if player not in players:
            raise ValueError("Gave bye to removed player %s at line %d" % (
                line, line_num))
        byes[player] += 1
    def game_event(event_num, info):
        p1, p2, result = info
        if p1 not in seeds:
            raise ValueError("Unknown player 1 '%s' in game at event %d" % (
                p1, event_num))
        if p1 not in players:
            raise ValueError("Removed player '%s' in game at event %d" % (
                p1, event_num))
        if p2 not in seeds:
            raise ValueError("Unknown player 2 '%s' in game at event %d" % (
                p2, event_num))
        if p2 not in players:
            raise ValueError("Removed player '%s' in game at event %d" % (
                p2, event_num))
        if result[0] == "winner":
            winner = result[1]
            if winner not in (p1, p2):
                raise ValueError(
                        "Recorded winner %s not a player in game at event %d" % (
                            winner, event_num))
            games.append(info)
        elif result[0] in ("draw", "double win", "double loss", "no decision",
                "vacated"):
            games.append(info)
        else:
            raise ValueError("Unrecognized result %s for game at event %d" % (
                result, event_num))
    def round_event(event_num, info):
        cur_round[0] = info
    type_handlers = {
            "seed": player_event,
            "remove": remove_event,
            "add": add_event,
            "bye": bye_event,
            "game": game_event,
            "round": round_event,
            }
    for event_num, (event, info) in enumerate(events):
        try:
            type_handlers[event](event_num, info)
        except KeyError:
            raise ValueError("Unrecognized event type %s at event %d" % (
                event, event_num))
    tourn = Tournament()
    tourn.events = tuple(events)
    tourn.players = frozenset(players)
    tourn.seeds = seeds
    tourn.games = tuple(games)
    tourn.byes = byes
    if cur_round[0] != 0:
        tourn.rounds = cur_round[0]
    tourn.update_stats()
    return tourn

def parse_seeds(seed_data):
    """ Parse aaaa style seed file """
    events = []
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
        events.append(("seed", (player, rating)))
        players.append(player)
        seeds[player] = rating
    tourn = Tournament()
    tourn.events = tuple(events)
    tourn.players = frozenset(players)
    tourn.seeds = seeds
    tourn.update_stats()
    return tourn

def parse_history(tourn, history_data):
    """ Parse aaaa style game history file """
    events = list(tourn.events)
    active = set(tourn.players)
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
                events.append(("remove", (p1,)))
            else:
                active.add(p1)
                events.append(("add", (p1,)))
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
            events.append(("game", (p1, p2, ("double loss",))))
            games.append((p1, p2, ("double loss",)))
            continue
        winner = words[2]
        if winner not in (p1, p2):
            raise ValueError(
                    "Winner (%s) not a player of game in history at line %d" % (
                    winner, line_num))
        events.append(("game", (p1, p2, ("winner", winner))))
        games.append((p1, p2, ("winner", winner)))
    tourn.events = tuple(events)
    tourn.players = frozenset(active)
    tourn.games = tuple(games)
    tourn.update_stats()
    # format doesn't record byes so add games not played as byes
    if tourn.played.most_common(1): # only check if there have been games played
        most_played = tourn.played.most_common(1)[0][1]
        for p in tourn.seeds.keys():
            tourn.byes[p] = most_played - tourn.played[p]

def parse_tournament(tourn_state):
    events = list()
    players = set()
    seeds = dict()
    games = list()
    byes = Counter()
    cur_round = [0]
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
        events.append(("seed", (name, seed)))
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
        events.append(("remove", (line,)))
        players.remove(line)
    def parse_add(line_num, line):
        if line not in seeds:
            raise ValueError("Tried to re-add unknown player %s at line %d" % (
                line, line_num))
        events.append(("add", (line,)))
        players.add(line)
    def parse_bye(line_num, line):
        tokens = line.split()
        if len(tokens) == 2:
            player, result = tokens
        else:
            player, result = line, None
        if player not in seeds:
            raise ValueError("Gave bye to unknown player %s at line %d" % (
                line, line_num))
        if player not in players:
            raise ValueError("Gave bye to removed player %s at line %d" % (
                line, line_num))
        events.append(("bye", (player, result)))
        byes[player] += 1
    def parse_game(line_num, line):
        tokens = line.split(None, 2)
        if len(tokens) != 3:
            raise ValueError("Bad game entry at line %d" % (line_num,))
        p1, p2, result = tokens
        if p1 not in seeds:
            raise ValueError("Unknown player 1 '%s' in game at line %d" % (
                p1, line_num))
        if p1 not in players:
            raise ValueError("Removed player '%s' in game at line %d" % (
                p1, line_num))
        if p2 not in seeds:
            raise ValueError("Unknown player 2 '%s' in game at line %d" % (
                p2, line_num))
        if p2 not in players:
            raise ValueError("Removed player '%s' in game at line %d" % (
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
            game = (p1, p2, ("winner", winner))
            events.append(("game", game))
            games.append(game)
        elif result in ("draw", "double win", "double loss", "no decision",
                "vacated"):
            game = (p1, p2, (result,))
            events.append(("game", game))
            games.append(game)
        else:
            raise ValueError("Unrecognized result %s for game at line %d" % (
                result, line_num))
    def parse_round(line_num, line):
        try:
            next_round = int(line)
        except ValueError:
            raise ValueError("Bad round entry at line %d" % (line_num,))
        if next_round != cur_round[0] + 1:
            raise ValueError("Out of order round found at line %d" % (line_num,))
        cur_round[0] = next_round
        events.append(("round", next_round))
    type_handlers = {
            "player": parse_player,
            "remove": parse_remove,
            "add": parse_add,
            "bye": parse_bye,
            "game": parse_game,
            "pair": parse_game,
            "pick": parse_game,
            "round": parse_round,
            }
    for line_num, line in enumerate(tourn_state.splitlines(), start=1):
        line = line.split("#")[0]
        line = line.split("*")[0]
        line = line.strip()
        if len(line) == 0:
            continue
        tokens = line.split(None, 1)
        if len(tokens) > 1:
            ltype, lrest = tokens
        elif tokens[0] == "stop":
            break
        else:
            raise ValueError("Unrecognized entry at line %d" % (line_num,))
        try:
            type_handlers[ltype.lower()](line_num, lrest)
        except KeyError:
            raise ValueError("Unrecognized line type %s at line %d" % (
                ltype, line_num))
    tourn = Tournament()
    tourn.events = tuple(events)
    tourn.players = frozenset(players)
    tourn.seeds = seeds
    tourn.games = tuple(games)
    tourn.byes = byes
    if cur_round[0] != 0:
        tourn.rounds = cur_round[0]
    tourn.update_stats()
    return tourn

def rate(seeds, tourn, virtual_weight):
    scores = tourn.wins
    pair_counts = tourn.pair_counts
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
    count = 0
    while True:
        new_error = list()
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
            new_error.append(error ** 2)
        new_error = math.fsum(new_error)
        if new_error < old_error:
            old_error = new_error
            best_rating = dict(new_rating)
        else:
            if best_rating == new_rating:
                break
            br = sorted(best_rating.keys(), key=lambda p: (best_rating[p], p))
            nr = sorted(new_rating.keys(), key=lambda p: (new_rating[p], p))
            if br == nr:
                count += 1
                if count > 10:
                    break
            else:
                count = 0
        old_rating = dict(new_rating)
    # round to 12 significant decimal places
    ratings = {p: round(r, 11-int(math.floor(math.log10(r))))
            for p, r in best_rating.items()}
    # convert back to elo range
    ratings = {p: (math.log(r) / CF) + mid_rating
            for p, r in ratings.items()}
    return ratings

def clyring_rate(seeds, tourn, virtual_weight):
    def gradient_from(strength_diff):
        return 1 / (1 + math.exp(strength_diff * math.log(10) / 400))

    def get_gradients(seeds, ratings, wins, losses, prior):
        gradients = dict()
        players = ratings.keys()
        for player in players:
            prating = ratings[player]
            prior_gradient = gradient_from(prating - seeds[player])
            gradient = prior * prior_gradient - (prior / 2)
            for opponent in players:
                if opponent == player:
                    continue
                pair = (player, opponent)
                op_gradient = gradient_from(prating - ratings[opponent])
                gradient += wins[pair] * op_gradient
                gradient += losses[pair] * (op_gradient - 1)
            gradients[player] = gradient
        return gradients

    def get_hessians(seeds, ratings, wins, losses, prior):
        hessians = dict()
        players = ratings.keys()
        for player in players:
            prating = ratings[player]
            prior_gradient = gradient_from(prating - seeds[player])
            hessian = prior * prior_gradient * (1 - prior_gradient)
            for opponent in players:
                if opponent == player:
                    continue
                pair = (player, opponent)
                faced = wins[pair] + losses[pair]
                op_gradient = gradient_from(prating - ratings[opponent])
                hessian += faced * op_gradient * (1 - op_gradient)
            hessians[player] = hessian
        return hessians

    wins = defaultdict(int)
    losses = defaultdict(int)
    for event in tourn.games:
        if event[2][0] == "winner":
            w = event[2][1]
            l = event[0] if w == event[1] else event[1]
            wins[(w, l)] += 1
            losses[(l, w)] += 1
        else:
            raise ValueError("Cannot handle game result type, %s" % (
                event[2][0],))
    ratings = dict(seeds)

    NATELO = 400 / math.log(10)
    gradients = get_gradients(seeds, ratings, wins, losses, virtual_weight)
    while math.fsum(abs(g) for g in gradients.values()) > 0.000000001:
        hessians = get_hessians(seeds, ratings, wins, losses, virtual_weight)
        for player in seeds.keys():
            prev = ratings[player]
            ratings[player] += (gradients[player] * NATELO) / max(
                    hessians[player], 0.3)
        gradients = get_gradients(seeds, ratings, wins, losses, virtual_weight)
    return ratings

def weighted_pairing(tourn, scale):
    players = list(tourn.players)
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

def assign_colors(tourn, pairings):
    """
    1. Assign Gold to the player with a lower total of previous games as Gold minus previous games as Silver.
    2. Assign Gold to the player with fewer previous games as Gold among games between the two players.
    3. Break both color streaks, i.e. give both players a different color then the color they played with in their most recent game.
    4. Break the color streak of the player with the longer streak.
    5. Swap colors with respect to the last time the two players played against each other.
    6. Assign color arbitrarily.
    """
    tourn_hash = hashlib.sha256()
    tourn_hash.update("\n".join(sorted(tourn.players)))
    tourn_hash.update("\n")
    tourn_hash.update("\n".join(sorted("%s %s" % g[:2] for g in tourn.games)))
    extra_gold = Counter()
    prev_pair = Counter()
    p1_streak = Counter()
    p2_streak = Counter()
    last_pairing = dict()
    for p1, p2, result in tourn.games:
        if result[0] == "vacated":
            continue
        extra_gold[p1] += 1
        extra_gold[p2] -= 1
        prev_pair[(p1, p2)] += 1
        p1_streak[p1] += 1
        p2_streak[p1] = 0
        p1_streak[p2] = 0
        p2_streak[p2] += 1
        last_pairing[frozenset((p1, p2))] = p1
    games = list()
    arbitrary = set()
    for p1, p2 in pairings:
        # 1 p1 to player with less previous (games as p1 - games as p2)
        if extra_gold[p1] != extra_gold[p2]:
            if extra_gold[p2] < extra_gold[p1]:
                p1, p2 = p2, p1
            games.append((p1, p2))
            continue
        # 2 p1 to player with fewer games as p1 in games against p2
        if prev_pair[(p1, p2)] != prev_pair[(p2, p1)]:
            if prev_pair[(p1, p2)] > prev_pair[(p2, p1)]:
                    p1, p2 = p2, p1
            games.append((p1, p2))
            continue
        # 3 break both player's color streak
        if p1_streak[p1] > 0 and p2_streak[p2] > 0:
            games.append((p2, p1))
            continue
        elif p2_streak[p1] > 0 and p1_streak[p2] > 0:
            games.append((p1, p2))
            continue
        # 4 break the color streak of the player with the longest streak
        p1_max = max(p1_streak[p1], p2_streak[p1])
        p2_max = max(p1_streak[p2], p2_streak[p2])
        if p1_max != p2_max:
            if ((p1_max > p2_max and p1_streak[p1] > 0)
                    or (p2_max > p1_max and p2_streak[p2] > 0)):
                p1, p2 = p2, p1
            games.append((p1, p2))
            continue
        # 5 swap colors from last game they played against each other
        if frozenset((p1, p2)) in last_pairing:
            if last_pairing[frozenset((p1, p2))] == p1:
                p1, p2 = p2, p1
            games.append((p1, p2))
            continue
        # 6 assign colors arbitrarily
        p1_hash = tourn_hash.copy()
        p1_hash.update("\n%s %s" % (p1, p2))
        p1_hash = int(p1_hash.hexdigest(), 16)
        p2_hash = tourn_hash.copy()
        p2_hash.update("\n%s %s" % (p2, p1))
        p2_hash = int(p2_hash.hexdigest(), 16)
        if p2_hash < p1_hash:
            p1, p2 = p2, p1
        game = (p1, p2)
        games.append(game)
        arbitrary.add(game)
    return games, arbitrary

