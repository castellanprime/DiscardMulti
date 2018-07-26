"""
	Game object
"""
from servermodel import ServerModel

class Game(object):
	def __init__(self, players):
		self.model = ServerModel(players)

