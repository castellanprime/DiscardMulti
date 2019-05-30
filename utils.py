"""
	Player Connections 
"""

import uuid
import jsonpickle
from enum import auto
from serverenums import MyEnum

class PlayerGameConn(object):
	def __init__(self, user_id, 
			room_id, wbsocket):
		self.user_id = user_id
		self.room_id = room_id
		self.wbsocket = wbsocket

class RoomPlayer(object):
	def __init__(self, nickname, user_id):
		self.nickname = nickname
		self.user_id = user_id

	def __eq__(self, other):
		if not isinstance(other, RoomPlayer):
			return False

		return all(( self.nickname == other.nickname,
			self.user_id == other.user_id ))

	def __ne__(self, other):
		return not self == other

	def __hash__(self):
		return hash(( self.nickname, self.user_id )) 

	def __str__(self):
		return 'nickname={0}, userid={1}'.format(
			self.nickname, self.user_id
		)

	@staticmethod
	def to_json(msg_obj):
		return jsonpickle.encode(msg_obj)

	@staticmethod
	def to_obj(json_obj):
		return jsonpickle.decode(json_obj)

class DiscardMsg(object):
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
		ROOM_ID = auto()
		USER_ID = auto()
		GAME_ID = auto()

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

	def get_payload_value(self, value):
		for key in self.__payload.keys():
			if key == value:
				return self.__payload[value]

	@classmethod
	def is_not_payload_type(cls, value):
		return value.upper() in cls.__PayloadTypes.__members__.keys()

	@classmethod
	def is_not_a_command_type(cls, value):
		return all([value.upper() != cls.__PayloadTypes.NEXT_CMD, value != 'cmd'])

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
