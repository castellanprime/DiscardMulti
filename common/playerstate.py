"""
	This module contains the code
	for recoding the playing state of a
	player
"""


class State(object):

	def __init__(self, game_state, cards_played, current_deck):
		self.player_state = game_state
		self.cards_played = cards_played
		self.current_deck = current_deck
		self.num_of_cards_played = 0 	# This records the number of cards that have been
										# played
		self.is_blocking = False
		self.win_status = None

	def get_list_of_moves(self):
		return self.cards_played

	def get_last_cards_played(self):
		return self.cards_played[-self.num_of_cards_played:]

	def set_win_status(self, status):
		"""One of the enums Gamestate"""
		self.win_status = status
		