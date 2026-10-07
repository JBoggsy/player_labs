"""Uniform-random legal orders: the same choice rule as the bundled random bot / league
filler (players.legal_orders.LegalOrders.choose), wrapped in our policy interface so the
local arena can field it."""

from collections import Counter

from players.legal_orders import LegalOrders

from webdip_bot.dumbbot import Board


class RandomLegal:
    def __init__(self, variant, board, country, phase, turn, rng):
        self.b = Board(variant, board)
        self.legal = LegalOrders(variant, board)
        self.country, self.phase, self.rng = country, phase, rng
        self.trace = Counter()

    def choose(self, slots):
        context = {"game": {"phase": self.phase}, "member": {"countryID": self.country}, "orders": {"orders": slots}}
        return self.legal.choose(context, self.rng)
