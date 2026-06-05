import random
from collections import Counter
from itertools import combinations


RANKS = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
SUITS = ['♠', '♥', '♦', '♣']
HAND_NAMES = ["High Card", "One Pair", "Two Pair", "Three of a Kind", "Straight", "Flush", "Full House", "Four of a Kind", "Straight Flush", "Royal Flush"]


def make_deck():
    return [{'rank': r, 'suit': s} for r in RANKS for s in SUITS]


def card_str(card):
    return f"{card['rank']}{card['suit']}"


def hand_str(cards):
    return "  ".join(card_str(c) for c in cards)


def rank_value(card):
    return RANKS.index(card['rank'])


def score_five(hand):
    values = sorted([rank_value(c) for c in hand], reverse=True)
    suits = [c['suit'] for c in hand]
    counts = Counter(values)
    freqs = sorted(counts.values(), reverse=True)
    grouped = sorted(values, key=lambda v: (counts[v], v), reverse=True)

    flush = len(set(suits)) == 1
    straight = len(set(values)) == 5 and (values[0] - values[4] == 4)
    royal = flush and straight and values[0] == RANKS.index('A')

    if royal:return (9, grouped)
    if flush and straight: return (8, grouped)
    if freqs[0] == 4:  return (7, grouped)
    if freqs[:2] == [3, 2]: return (6, grouped)
    if flush: return (5, grouped)
    if straight:  return (4, grouped)
    if freqs[0] == 3:   return (3, grouped)
    if freqs[:2] == [2, 2]: return (2, grouped)
    if freqs[0] == 2: return (1, grouped)
    return   (0, grouped)

def best_hand(cards):
    best = max(combinations(cards, 5), key=score_five)
    score = score_five(best)
    return list(best), score, HAND_NAMES[score[0]]

class Player:
    def __init__(self, name, chips):
        self.name = name
        self.chips = chips
        self.hole_cards = []
        self.current_bet = 0
        self.folded = False
        self.all_in = False

    def reset_for_round(self):
        self.hole_cards = []
        self.current_bet = 0
        self.folded = False
        self.all_in = False

    def place_bet(self, amount):
        actual = min(amount, self.chips)
        self.chips -= actual
        self.current_bet += actual
        return actual

    def __str__(self):
        return self.name


class PokerGame:
    def __init__(self, player_names, starting_chips=1000, small_blind=10):
        self.players = [Player(name, starting_chips) for name in player_names]
        self.small_blind = small_blind
        self.big_blind = small_blind * 2
        self.deck = []
        self.community_cards = []
        self.pot = 0
        self.dealer_index = 0

    def rotate_dealer(self):
        self.dealer_index = (self.dealer_index + 1) % len(self.players)

    def active_players(self):
        return [p for p in self.players if not p.folded]

    def post_blinds(self):
        sb_index = (self.dealer_index + 1) % len(self.players)
        bb_index = (self.dealer_index + 2) % len(self.players)

        sb_player = self.players[sb_index]
        bb_player = self.players[bb_index]

        sb_amount = sb_player.place_bet(self.small_blind)
        bb_amount = bb_player.place_bet(self.big_blind)

        self.pot += sb_amount + bb_amount
        print(f"\n{sb_player.name} posts small blind: ${sb_amount}")
        print(f"{bb_player.name} posts big blind: ${bb_amount}")

        return bb_index

    def deal_hole_cards(self):
        self.deck = make_deck()
        random.shuffle(self.deck)
        for player in self.players:
            player.reset_for_round()
            player.hole_cards = [self.deck.pop(), self.deck.pop()]

    def deal_community(self, n):
        for _ in range(n):
            self.community_cards.append(self.deck.pop())

    def print_table(self, current_player=None):
        if self.community_cards:
            print(f"Community: {hand_str(self.community_cards)}")
        print(f"Pot: ${self.pot}")
        for p in self.players:
            status = ""
            if p.folded:
                status = " [FOLDED]"
            elif p.all_in:
                status = " [ALL IN]"
            if p == current_player:
                print(f">>> {p.name}: ${p.chips} chips  |  {hand_str(p.hole_cards)}{status}")
            else:
                print(f"    {p.name}: ${p.chips} chips{status}")

    def betting_round(self, first_to_act_index, current_bet=0):
        num_players = len(self.players)
        players_acted = set()
        index = first_to_act_index

        while True:
            player = self.players[index % num_players]
            index += 1

            if player.folded or player.all_in:
                if len(players_acted) >= len(self.active_players()):
                    break
                continue

            self.print_table(current_player=player)
            call_amount = current_bet - player.current_bet

            print(f"\n{player.name}'s turn  |  Chips: ${player.chips}  |  To call: ${call_amount}")
            print(f"Cards: {hand_str(player.hole_cards)}")

            action = self.get_action(player, call_amount)
            if action == 'fold':
                player.folded = True
                print(f"{player.name} folds.")
                players_acted.add(player.name)

            elif action == 'check':
                print(f"{player.name} checks.")
                players_acted.add(player.name)

            elif action[0] == 'call':
                amount = player.place_bet(call_amount)
                self.pot += amount
                if player.chips == 0:
                    player.all_in = True
                print(f"{player.name} calls ${amount}.")
                players_acted.add(player.name)

            elif action[0] == 'raise':
                raise_to = action[1]
                extra = raise_to - player.current_bet
                amount = player.place_bet(extra)
                self.pot += amount
                current_bet = player.current_bet
                if player.chips == 0:
                    player.all_in = True
                print(f"{player.name} raises to ${current_bet}.")
                players_acted = {player.name}

            if len(self.active_players()) == 1:
                break

            all_matched = all(
                p.current_bet == current_bet or p.folded or p.all_in
                for p in self.players
            )
            if all_matched and len(players_acted) >= len(self.active_players()):
                break

        return current_bet

    def get_action(self, player, call_amount):
        while True:
            if call_amount == 0:
                options = "check / raise / fold"
            else:
                options = f"call ${call_amount} / raise / fold"

            #choice = input(f"Action ({options}): ").strip().lower()
            if call_amount==0:
                choice = 'check'
            else:
                choice = 'call'

            if choice == 'fold':
                return 'fold'

            if choice == 'check':
                if call_amount == 0:
                    return 'check'
                print("You can't check, there's a bet to call.")

            elif choice == 'call':
                if call_amount == 0:
                    print("Nothing to call, you can check.")
                elif call_amount >= player.chips:
                    print(f"Going all in for ${player.chips}.")
                    return ('call',)
                else:
                    return ('call',)

            elif choice == 'raise':
                min_raise = player.current_bet + call_amount + self.big_blind
                try:
                    amount = int(input(f"Raise to (min ${min_raise}, you have ${player.chips + player.current_bet}): $"))
                    total_chips = player.chips + player.current_bet
                    if amount < min_raise and amount != total_chips:
                        print(f"Raise must be at least ${min_raise}.")
                    elif amount > total_chips:
                        print(f"You only have ${total_chips} total.")
                    else:
                        return ('raise', amount)
                except ValueError:
                    print("Enter a valid number.")
            else:
                print("Type: fold, check, call, or raise")

    def showdown(self):
        print("\nSHOWDOWN")
        alive = self.active_players()

        if len(alive) == 1:
            winner = alive[0]
            print(f"{winner.name} wins ${self.pot} (everyone else folded)")
            winner.chips += self.pot
            return

        results = []
        for player in alive:
            all_cards = player.hole_cards + self.community_cards
            _, score, name = best_hand(all_cards)
            print(f"{player.name}: {hand_str(player.hole_cards)}  ->  {name}")
            results.append((score, player))

        results.sort(key=lambda x: x[0], reverse=True)
        top_score = results[0][0]
        winners = [p for score, p in results if score == top_score]

        split = self.pot // len(winners)
        for winner in winners:
            winner.chips += split
            print(f"\n{winner.name} wins ${split}!")

    def play_round_demo(self):
        self.community_cards = []
        self.pot = 0

        for player in self.players:
            player.reset_for_round()

        print(f"  Dealer: {self.players[self.dealer_index].name}")

        self.deal_hole_cards()
        bb_index = self.post_blinds()

        current_bet = self.big_blind
        first_preflop = (bb_index + 1) % len(self.players)
        current_bet = self.betting_round(first_preflop, current_bet)

        if len(self.active_players()) > 1:
            self.deal_community(3)
            print("\nFLOP")
            for p in self.players:
                p.current_bet = 0
            current_bet = self.betting_round(self.dealer_index + 1, 0)

        if len(self.active_players()) > 1:
            self.deal_community(1)
            print("\nTURN")
            for p in self.players:
                p.current_bet = 0
            current_bet = self.betting_round(self.dealer_index + 1, 0)

        if len(self.active_players()) > 1:
            self.deal_community(1)
            print("\nRIVER")
            for p in self.players:
                p.current_bet = 0
            self.betting_round(self.dealer_index + 1, 0)

        self.print_table()
        self.showdown()
        self.rotate_dealer()

    def play_round(self):
        self.community_cards = []
        self.pot = 0

        for player in self.players:
            player.reset_for_round()

        print(f"  Dealer: {self.players[self.dealer_index].name}")

        self.deal_hole_cards()
        bb_index = self.post_blinds()

        current_bet = self.big_blind
        first_preflop = (bb_index + 1) % len(self.players)
        current_bet = self.betting_round(first_preflop, current_bet)

        if len(self.active_players()) > 1:
            self.deal_community(3)
            print("\nFLOP")
            for p in self.players:
                p.current_bet = 0
            current_bet = self.betting_round(self.dealer_index + 1, 0)

        if len(self.active_players()) > 1:
            self.deal_community(1)
            print("\nTURN")
            for p in self.players:
                p.current_bet = 0
            current_bet = self.betting_round(self.dealer_index + 1, 0)

        if len(self.active_players()) > 1:
            self.deal_community(1)
            print("\nRIVER")
            for p in self.players:
                p.current_bet = 0
            self.betting_round(self.dealer_index + 1, 0)

        self.print_table()
        self.showdown()
        self.rotate_dealer()

    def remove_broke_players(self):
        broke = [p for p in self.players if p.chips == 0]
        for p in broke:
            print(f"\n{p.name} is out of chips and leaves the game.")
        self.players = [p for p in self.players if p.chips > 0]
        
    def play(self):
        print("\nWelcome to Texas Hold'em!")
        while len(self.players) > 1:
            self.play_round()
            self.remove_broke_players()

            if len(self.players) == 1:
                break

            again = input("\nPlay another round? (y/n): ").strip().lower()
            if again != 'y':
                break

        print("\nFINAL CHIP COUNTS")
        for p in sorted(self.players, key=lambda x: x.chips, reverse=True):
            print(f"  {p.name}: ${p.chips}")
        if len(self.players) == 1:
            print(f"\n{self.players[0].name} wins the game!")


def demonstration():
    game = PokerGame(["Player 1", "Player 2", "Player 3"])
    game.play()


def main():
    print("Texas Hold'em Poker")
    """
    while True:
        try:
            num = int(input("Number of players (2-8): "))
            if 2 <= num <= 8:
                break
            print("Please enter between 2 and 8.")
        except ValueError:
            print("Enter a valid number.")
    """
    names = ['Zaid', 'Ha', "Eri"]
    #for i in range(num):
        #name = input(f"Name for player {i + 1}: ").strip() or f"Player {i + 1}"
        #names.append(name)

    while True:
        try:
            #chips = int(input("Starting chips per player (default 1000): ") or "1000")
            chips = 1000
            if chips > 0:
                break
            print("Must be positive.")
        except ValueError:
            print("Enter a valid number.")

    game = PokerGame(names, starting_chips=chips)
    game.play()

if __name__ == "__main__":
    main()