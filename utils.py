"""
	Player Connections 
"""

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

class DiscardMessage(object):
	def __init__(self, cmd, prompt=None, 
			data=None, nextCmd=None):
		self.cmd = cmd 
		self.__payload = {}
		if prompt:
			self.__payload['prompt'] = prompt 
		if data:
			self.__payload['data'] = data 
		if nextCmd:
			self.__payload['nextCmd'] = nextCmd

	def get_prompt(self):
		for key, value in self.__payload.items():
			if key == 'prompt':
				return self.__payload['prompt']

	def get_data(self):
		for key, value in self.__payload.items():
			if key == 'data':
				return self.__payload['data']

	def get_next_cmd(self):
		for key, value in self.__payload.items():
			if key == 'nextCmd':
				return self.__payload['nextCmd']

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