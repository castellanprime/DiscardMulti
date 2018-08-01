"""
	Game object
"""
from servermodel import ServerModel

class Game(object):
	def __init__(self, players):
		self.model = ServerModel(players)

	def get_current_player(self):
		return None

	def is_there_an_initial_player(self):
		return self.model.get_initial_player() == None
