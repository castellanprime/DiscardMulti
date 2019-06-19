"""
	Player Connections 
"""

import uuid
import jsonpickle
from enum import auto
from serverenums import MyEnum, NoValue

class DiscardMsg(object):

	class Request(NoValue):
		GET_ROOMMATES = auto()
		GET_ROOMS = auto()
		CREATE_A_ROOM = auto()
		JOIN_ROOM = auto()
		START_GAME = auto()
		LEAVE_GAME = auto()
		GAME_REQUEST = auto()
		PLAY_MOVE = auto()
		GET_GAME_STATUS = auto()
		SET_INITIAL_PLAYER = auto()
		STOP_GAME = auto()

	class Response(NoValue):
		GET_ROOMMATES = auto()
		GET_ROOMS = auto()
		CREATE_A_ROOM = auto()
		JOIN_ROOM = auto()
		START_GAME = auto()
		LEAVE_GAME = auto()
		GAME_REQUEST = auto()
		PLAY_MOVE = auto()
		GET_GAME_STATUS = auto()
		SET_INITIAL_PLAYER = auto()
		STOP_GAME = auto()
		GAME_IS_STARTING = auto()
		GAME_HAS_STARTED = auto()
		ADDED_NEW_GAME_CONN = auto()
		ERROR = auto()


	class __PayloadTypes(MyEnum):
		"""
		These are the allowed values for keys
		for payloads between client and server

		PROMPT: This sends what is displayed
		on the client(mainly for the console version)
		of the game). Might not be used on the
		the GUI version of the game

		DATA: This is used to send data
		to the server from the client

		EXTRA_DATA: This is used to send
		options to the client from the server. This
		is used for validation on the client before
		client sends messages to the server. The
		server can also send the latest top of the
		deck here

		NEXT_CMD: This is the cmd for the
		rules engine on the client used to dispatch
		different actions

		FLAG: This is used for continuation
		purposes and is used to pause execution in
		the game engine on the server

		MSG_ID: This is automatically on
		sending of messages, if not user specified.

		USER_ID: This will removed in later
		versions

		ROOM_ID: This helps in the delivery
		of the message to a room on the server

		DEST: This means this message is bound for the
		GameHandler or the RoomHandler
		"""
		NEXT_CMD = auto()
		DATA = auto()
		PROMPT = auto()
		EXTRA_DATA = auto()
		RETURN_TYPE = auto()
		FLAG = auto()
		DEST = auto()

	def __init__(self, cmd, **kwargs):

		"""
		This is the main message used to 
		communicated between the servers and
		clients

		A message is divided into two parts:
		header(cmd, msg_id), body(payload)
		"""

		self.cmd = cmd 
		self.__payload = {}
		self.msg_id = uuid.uuid4().hex
		for key, value in kwargs.items():
			if key.upper() in DiscardMsg.__PayloadTypes.__members__.keys():
				self.__payload[key]=value
		data_ = {key: value for key, value in kwargs.items()
			if DiscardMsg.is_not_a_payload_type(key)}
		self.__payload['data'] = data_

	def get_payload_value(self, value):
		for key in self.__payload.keys():
			if key == value:
				return self.__payload[value]
		for key in self.__payload.get('data'):
			if key == value:
				return self.__payload.get('data')[value]

	@classmethod
	def is_not_a_payload_type(cls, value):
		return not value.upper() in cls.__PayloadTypes.__members__.keys()

	@classmethod
	def is_not_a_command_type(cls, value):
		return not value.upper() in [cls.__PayloadTypes.NEXT_CMD.name, 'CMD']

	def __eq__(self, other):
		if not isinstance(other, DiscardMsg):
			return False

		return all(( self.cmd == other.cmd, 
			self.__payload == other.__payload ))

	def __ne__(self, other):
		return not self == other

	def __hash__(self):
		return hash((self.cmd, self.__payload))

	def __str__(self):
		return "cmd={0}, payload={1}".format(
			self.cmd, str(self.__payload)
		)

	@staticmethod
	def to_json(msg_obj):
		return jsonpickle.encode(msg_obj)

	@staticmethod
	def to_obj(json_obj):
		return jsonpickle.decode(json_obj)
