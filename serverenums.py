from enum import Enum

class MyEnum(Enum):

	def __str__(self):
		return "({0}={1})".format(self.__class__.__name__, self.name)

class ServerEnum(MyEnum):
	GAME_PAUSED = 1
	GAME_ENDED = 2
	GAME_STARTED = 3
	GAME_NOT_STARTED = 4
	CLIENT_CAN_START = 5
	JOIN = 6
	LEAVE = 7
	PLAY = 8
	SKIP = 9
	GET_ROOMATES = 10
	GET_ROOMS = 11
	CREATE_A_ROOM = 12
	START_GAME = 13
	ARE_ROOMATES_IN_GAME= 14
	GAME_MESSAGE = 15	# For messages in the game
	HAS_GAME_STARTED = 16

class ClientEnum(MyEnum):
	CREATE_A_ROOM_REP=1
	JOIN_REP=2
	START_GAME_REP=3
	ARE_ROOMATES_IN_GAME_REP=4
	GAME_MESSAGE_REP=5	# For messages in the game
	GAME_JOIN_REP=6
	ASK_FOR_ROOMATES=7