"""
	Server model 
"""

class ServerModel(object):
	def __init__(self, players):
		self.players = players
		self.initial_player = None 
		self.current_player = None

	def get_initial_player(self):
		return self.initial_player

	def set_initial_player(self, player):
		self.initial_player = player
		print("Initial player set: ",  
			self.initial_player)
		self.set_current_player(player)

	def set_current_player(self, player):
		self.current_player = player
		print("Current player set: ",  
			self.current_player)

	def get_current_player(self):
		return self.current_player
