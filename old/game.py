"""
	Game object
"""
import logging, random, sys
from servermodel import ServerModel

class Game(object):
	def __init__(self, players):
		self._logger = logging.getLogger(__name__)
		self.model = ServerModel()
		self.model.players.extend(players)
		self.current_player = None
		self.winner = None
		self.state = None

	def get_current_player(self):
		return self.model.get_current_player()

	def get_initial_player(self):
		return self.model.get_initial_player()

	def set_initial_player(self, player):
		self.model.set_initial_player(player)

	# Set the player state here
	def deal(self):
		temp_list = self.model.get_game_deck()
		random.shuffle(temp_list)
		self.model.main_deck[:] = temp_list


	def get_game_cards(self):
		pass

	def start_game(self):
		pass
