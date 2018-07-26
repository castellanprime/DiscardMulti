"""
	Player Connections 
"""

import jsonpickle

class JSONSerializer(object):
	@staticmethod
	def toJSON(self, py_obj):
		return jsonpickle.encode(py_obj)

	@staticmethod
	def toObj(self, json_obj):
		return jsonpickle.decode(json_obj)


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