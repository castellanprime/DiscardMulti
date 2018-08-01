"""
	Server model 
"""

class ServerModel(object):
	def __init__(self, players):
		self.players = players
		self.initial_player = None 

	def get_initial_player(self):
		return self.initial_player

	def set_initial_player(self, user_id):
		for player in self.players:
			if player.user_id == user_id:
				self.initial_player = player