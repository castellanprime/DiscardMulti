"""
	Player Connections 
"""

import uuid
import jsonpickle

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
	def __init__(self, cmd, prompt=None, 
			data=None, next_cmd=None,
			return_type=None, extra_data=None,
			flag=None, msg_id=None,
			user_id=None, room_id=None):
		"""
		This is the main message used to 
		communicated between the servers and
		clients

		:param cmd: The command that will be run
		on the server or return command 
		on the client
		
		:param prompt: This sends what is displayed
		on the client(mainly for the console version)
		of the game). Might not be used on the
		the GUI version of the game 
		
		:param data: This is used to send data
		to the server from the client
		
		:param extra_data: This is used to send 
		options to the client from the server. This 
		is used for validation on the client before
		client sends messages to the server. The
		server can also send the latest top of the 
		deck here

		:param next_cmd: This is the cmd for the 
		rules engine on the client used to dispatch
		different actions

		:param flag: This is used for continuation
		purposes and is used to pause execution in 
		the game engine on the server

		:param msg_id: This is automatically on 
		sending of messages, if not user specified.  
		
		:param user_id: This will removed in later
		versions

		:param room_id: This helps in the delivery
		of the message to a room on the server 
		"""
		self.cmd = cmd 
		self.__payload = {}
		self.msg_id = msg_id if msg_id else uuid.uuid4().hex
		if prompt:
			self.__payload['prompt'] = prompt 
		if data:	# for client tom server
			self.__payload['data'] = data
		if extra_data:	# for server to client
			self.__payload['extra_data'] = extra_data
		if return_type:
			self.__payload['return_type'] = return_type
		if flag:
			self.__payload['flag'] = flag 
		if next_cmd:
			self.__payload['next_cmd'] = next_cmd
		if room_id:
			self.__payload['room_id'] = room_id
		if user_id:
			self.__payload['user_id'] = user_id

	def get_payload_value(self, value):
		for key in self.__payload.keys():
			if key == value:
				return self.__payload[value]

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
