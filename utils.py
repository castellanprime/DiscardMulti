"""
	Player Connections 
"""

import uuid
import jsonpickle

class PlayerGameConn(object):
	def __init__(self, user_id, 
			room_id, wssocket, roomates_callback):
		self.user_id = user_id
		self.room_id = room_id
		self.roomates_callback = roomates_callback
		self.wssocket = wssocket

	def startCallBack(self):
		if self.roomates_callback:
			self.roomates_callback.start()

	def stopCallBack(self):
		if self.roomates_callback.is_running():
			self.roomates_callback.stop()

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
		return 'username={0}, userid={1}'.format(
			self.username, self.user_id
		)

class DiscardMessage(object):
	def __init__(self, cmd, prompt=None, 
			data=None, next_cmd=None,
			return_type=None, extra_data=None,
			flag=None, msg_id=None):
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

	def get_payload_value(self, value):
		for key in self.__payload.keys():
			if key == value:
				return self.__payload[value]

	def __eq__(self, other):
		if not isinstance(other, DiscardMessage):
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
