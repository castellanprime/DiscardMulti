"""
	Game object
"""
from servermodel import ServerModel
from uuid import uuid4

class Game(object):
	def __init__(self, players):
		self.model = ServerModel(players)
		self.gameid = uuid4().hex

	def get_current_player(self):
		return self.model.get_current_player()

	def get_initial_player(self):
		return self.model.get_initial_player()

	def set_initial_player(self, player):
		self.model.set_initial_player(player)
