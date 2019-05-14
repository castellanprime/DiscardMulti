"""
	Game object
"""
from model import ServerModel

class Game(object):
	def __init__(self, players):
		self.model = ServerModel(players)

	def get_current_player(self):
		return self.model.get_current_player()

	def get_initial_player(self):
		return self.model.get_initial_player()

	def set_initial_player(self, player):
		self.model.set_initial_player(player)

	def get_game_id(self):
		return self.game_id

	def start_game(self):
		pass
