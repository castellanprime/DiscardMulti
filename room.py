"""
	Class for Room object
	Each room has one game going through it.
"""
from serverenums import RoomGameStatus
from utils import RoomPlayer
from game import Game

class Room(object):
	def __init__(self, room_id, room_name):
		self.room_id = room_id
		self.room_name = room_name
		self.num_of_game_players = 0
		self.players = []
		self.game = None
		self.has_initial_player_been_choosen = False
		self.game_status = RoomGameStatus.GAME_NOT_STARTED

	def get_name(self):
		return self.room_name

	def get_num_of_cur_players(self):
		return len(self.players)

	def add_player(self, username, user_id):
		player = RoomPlayer(nickname=username, user_id=user_id)
		self.players.append(player)

	#def make_player_ready(self):
	#	self.players_pending = self.players_pending - 1

	def get_current_player(self):
		return self.game.get_current_player()

	def set_num_of_game_players(self, num):
		self.num_of_game_players = num

	def set_initial_player(self, player):
		if self.has_initial_player_been_choosen == False:
			self.game.set_initial_player(player)
			self.has_initial_player_been_choosen = True

	def get_initial_player(self):
		return self.game.get_initial_player()

	def get_username(self, user_id):
		for player in self.players:
			if player.user_id == user_id:
				return player.nickname

	def is_not_full(self):
		return self.num_of_game_players > self.get_num_of_cur_players()
	
	def is_full(self):
		return self.num_of_game_players == self.get_num_of_cur_players()

	def start_new_game(self):
		if self.game_status == RoomGameStatus.GAME_NOT_STARTED:
			self.game = Game(self.players)
			self.game_status = RoomGameStatus.GAME_HAS_STARTED
	
	def has_game_started(self):
		return self.game_status == RoomGameStatus.GAME_HAS_STARTED

	def get_roomates(self):
		return self.players

	def get_room_id(self):
		return self.room_id

	def get_num_of_players_remaining(self):
		return self.num_of_game_players - self.get_num_of_cur_players()

	def is_player_in_room(self, user_id):
		for player in self.players:
			if player.user_id == user_id:
				return True 
		return False
