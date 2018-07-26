"""
    Server module for game server

	Rooms are represented by a dictionary:
		rooms: list of players in a room, num of players that are supposed to be a room

	When a client comes online:
	1. It sends a GET request to '/room' to get a list of all rooms
	2. It receives a response. 
	3a. If response from (2) is empty, the client sends a POST request
	to '/room' with {user_id. username, num_of_players}. If num_of_players
	is 0, it returns a error. Else, the server creates a room and the 
	server returns with a message with the room_id. 
	3b. The client then sends a POST request to '/room' to join the 
	room selected. If the room is already full, the server sends a 
	an error. Else The server responds with a OK message.
	3c. The client then sends a POST request to '/room' to start the
	game. If the game has not started and the room is full, the server 
	starts the game and responds with an OK message. Else The server 
	responds with an Error.
	3d. The client then connects to the server with a websocket connection. 
	4. If response from (2) is not empty, the client chooses to create a 
	room or join a room. If it is the former, 3a-3f is followed. Else
	3b-3f is followed. 

	Messages are the form: { commandType, userid, payload}
	- command:
		- join: The command is for joining to the room
		- leave: The command is for leaving the room
		- nick_list: The command is getting the nick_names for strategy(chat)
		- play: This command is used for the game loop to play and return with a result
		- skip: This command is used for the game loop to skip the player and move onto the next player
"""

import json
import sys
import uuid
from serverenums import ServerEnum, ClientEnum
from tornado import web, options, httpserver, ioloop, websocket, log, escape
from random import randint
from room import Room
from playerconn import PlayerGameConn

class Controller(object):
	""" This handles the rooms that houses the game """
	def __init__(self):
		self.rooms = []		# a list of rooms
		self.game_conns = []

	def add_room(self, num_of_players):
		room_id = uuid.uuid4().hex
		room = Room(room_id)
		room.set_num_of_game_players(num_of_players)
		self.rooms.append(room)
		return room_id

	def get_all_rooms(self):
		rooms = []
		if len(self.rooms) > 0:
			for room in self.rooms:
				rooms.append(
					{ 
					'roomid': room.get_room_id(), \
					'num_of_cur_players': room.get_num_of_cur_players(), \
					'num_of_players_remaining' : room.get_num_of_players_remaining()
					})
		return rooms

	def can_join(self, room_id, user_id):
		for room in self.rooms:
			if room.get_room_id() == room_id:
				if all(( room.is_not_full(), 
					room.is_player_in_room(user_id) == False )):
					return True
		return False

	def can_start_game(self, room_id, user_id):
		for room in self.rooms:
			if all(( room.get_room_id() == room_id,
				room.is_player_in_room(user_id) == True,
				room.has_game_started() == False )):
				return True 
		return False

	def start_game(self, room_id):
		for room in self.rooms:
			if room.get_room_id() == room_id:
				room.start_new_game()

	def get_all_roomates(self, user_id, room_id):
		roomates = []
		for room in self.rooms:
			if all((room.get_room_id() == room_id, 
				room.is_player_in_room(user_id) == True )):
				roomates = room.get_roomates()
				#roomates[:] = [roomate.nickname
				#	for roomate in roomates 
				#	if roomate.user_id != user_id]
				break
		return roomates

	def add_player(self, room_id, user_id, username):
		for room in self.rooms:
			if room.get_room_id() == room_id:
				room.add_player_to_room(username, user_id)
				break

	def broadcast_game_message(self, user_id, room_id, message):
		"""Broadcasts messages to all roomates"""
		if len(self.game_conns) > 0:
			#roomates_game_conns = self.get_roomates_game_conns(
			#		user_id, room_id)
			msg = json.dumps(message)
			#for player_conns in roomates_game_conns:
			for player_conns in self.game_conns:
				conn = player_conns.wssocket
				conn.write_message(msg)

	def all_roomates_cb(self):
		roomates = []
		for game_conn in self.game_conns:
			msg = json.dumps({'cmd': 'ASK_FOR_ROOMATES'})
			game_conn.conn.write_message(msg)

	def add_game_conn(self, user_id, username, room_id, conn):
		""" Always add the connection"""
		print("[[ In add_game_conn ]]")
		add_new_conn = True
		if len(self.game_conns) > 0:
			for game_conn in self.game_conns:
				if all((game_conn.user_id == user_id,
					game_conn.room_id == room_id )):
					game_conn.wssocket = conn 
					add_new_conn = False
					break 
		if add_new_conn == True:
			callback = ioloop.PeriodicCallback(
				lambda: self.all_roomates_cb, 120)
			game_conn = PlayerGameConn(user_id=user_id, 
					room_id=room_id, wssocket=conn, 
					roomates_callback=callback)
			print("A new game connection has been created")
			self.game_conns.append(game_conn)
			self.broadcast_game_message(user_id, room_id,
				{
					'prompt': 'Just joined the game', 
					'username': username,
					'cmd': ClientEnum.GAME_JOIN_REP.name
				}
			)
			#game_conn.startCallBack()
		print("[[ Out of add_game_conn ]]")

	def get_roomates_game_conns(self, user_id, room_id):
		roomates_game_conns = [game_conn for game_conn in self.game_conns
			if all((game_conn.user_id != user_id,
				game_conn.room_id == room_id ))]
		return roomates_game_conns

	def reply_on_game_conn(self, user_id, room_id, return_message):
		print("[[ In reply_on_game_conn ]]")
		for game_conn in self.game_conns:
			if all(( game_conn.user_id == user_id, 
				game_conn.room_id == room_id)):
				game_conn.wssocket.write_message(json.dumps(return_message))
				break

	def stop_all_roomates_cb(self, room_id):
		for game_conn in self.game_conns:
			if game_conn.room_id == room_id:
				game_conn.stopCallBack()

	def handle_wsmessage(self, message):
		print("[[ In handle_wsmessage ]]")
		cmd = ServerEnum[message['cmd']]
		return_message = {}
		if cmd == ServerEnum.ARE_ROOMATES_IN_GAME:
			room_id = message['roomid']
			for room in self.rooms:
				print("[[ In rooms ]]")
				print("Room-id-1: ", room.get_room_id(), 
					" room-id-2: ", room_id)
				if room.get_room_id() == room_id:
					print("[[ In rooms 45 ]]")
					user_id = message['userid']
					if all(( room.has_game_started() == False,
						 room.get_num_of_players_remaining() > 0 )):
						print("[[ Waiting ]]")
						return_message['cmd'] = ClientEnum.ARE_ROOMATES_IN_GAME_REP.name
						return_message['prompt']= 'Waiting for ' + \
							str(room.get_num_of_players_remaining()) + \
							' players to join'
						#room.make_player_ready()
						self.reply_on_game_conn(user_id, room_id, 
							return_message)
					elif all(( room.has_game_started() == False,
						 room.get_num_of_players_remaining() == 0 )):
						print("[[ Success ]]")
						return_message['cmd'] = ClientEnum.GAME_MESSAGE_REP.name
						return_message['prompt'] = 'Game is initializing'
						self.broadcast_game_message(user_id, room_id, 
							return_message)
						#self.stop_all_roomates_cb(room_id)
					else:
						print("[[ Player is trying to see if game has started ]]")
						return_message['cmd'] = ClientEnum.GAME_MESSAGE_REP.name
						return_message['prompt'] =  'Game is initializing'
						self.reply_on_game_conn(user_id, room_id, 
							return_message)
				print("[[ Out of rooms ]]")
		elif cmd == ServerEnum.GAME_MESSAGE:
			return_message['cmd'] = ClientEnum.GAME_MESSAGE_REP.name
			return_message['prompt'] = 'Game is in session'
			room_id = message['roomid']
			user_id = message['userid']
			self.reply_on_game_conn(user_id, room_id, 
					return_message)

	def remove_game_conn(self, user_id):
		pass

class RoomHandler(web.RequestHandler):
	""" This handles connections relating to the rooms that house a game"""
	def initialize(self, controller):
		self.controller = controller

	def write_error(self, status_code, **kwargs):
		err_cls, err, traceback = kwargs['exc_info']
		if err.log_message:
			message = {}
			message['error'] = err.log_message
			self.write(json.dumps(message))

	def get(self):
		"""Get a list of rooms/nickname"""
		rep = self.get_query_argument('cmd')
		cmd = ServerEnum[rep]
		data = {}
		if cmd == ServerEnum.GET_ROOMATES:
			user_id = self.get_query_argument('userid')
			room_id = self.get_query_argument('roomid')
			list_of_roomates = self.controller.get_all_roomates(user_id,
						room_id)
			data['roomates'] = list_of_roomates
		elif cmd == ServerEnum.GET_ROOMS:
			list_of_rooms = self.controller.get_all_rooms()
			data['lis'] = list_of_rooms
		self.write(json.dumps(data))

	def post(self):
		"""Get a room"""
		recv_data = escape.json_decode(self.request.body)
		user_id = recv_data.get('userid')
		username = recv_data.get('username')
		query = self.get_query_argument('cmd')
		cmd = ServerEnum[query]
		message = {}
		if cmd == ServerEnum.CREATE_A_ROOM:
			num_of_players = recv_data.get('num_of_players')
			if num_of_players == 0:
				raise web.HTTPError(status_code=400, 
					log_message="Argument num_of_players can't be zero")
			else:
				room_id = self.controller.add_room(num_of_players)
				self.controller.add_player(room_id, user_id, username)
				message['status'] = ClientEnum.CREATE_A_ROOM_REP.name
				message['prompt'] = room_id
				self.write(json.dumps(message))
		elif cmd == ServerEnum.JOIN:
			room_id = recv_data.get('roomid')
			if self.controller.can_join(room_id, user_id):
				self.controller.add_player(room_id, user_id, username)
				message['status'] = ClientEnum.JOIN_REP.name
				message['prompt'] = "You have been added to room " + str(room_id)
				self.write(json.dumps(message))
			else:
				raise web.HTTPError(status_code=500, 
					log_message="Room is full")
		elif cmd == ServerEnum.START_GAME:
			room_id = recv_data.get('roomid')
			if self.controller.can_start_game(room_id, user_id):
				self.controller.start_game(room_id)
				message['status'] = ClientEnum.START_GAME_REP.name
				message['prompt'] = 'Game has started'
			else:
				message['status'] = ClientEnum.START_GAME_REP.name
				message['prompt'] = 'Game has already started'
			self.write(json.dumps(message))
		elif cmd == ServerEnum.LEAVE: 
			pass
		else:
			pass

class GameHandler(websocket.WebSocketHandler):
	""" This handles connections relating to the game"""
	def initialize(self, controller):
		self.controller = controller

	def open(self):
		# called anytime a new connection with this server is opened
		self.clientId = self.get_argument('userId')
		roomId = self.get_argument('roomId')
		username = self.get_argument('username')
		self.controller.add_game_conn(self.clientId, username
					,roomId, self)
		print("Websocket opened. ClientID = %s" % self.clientId)
		
	def on_message(self, message):
		# called anytime a new message is received
		print("Received from client ,msg=", message)
		self.controller.handle_wsmessage(escape.json_decode(message))

	def check_origin(self, origin):
		return True

	def on_close(self):
		print("Websocket closed")
		self.controller.remove_game_conn(self.clientId)

class Server(web.Application):
	""" This is the main entry point to the server"""
	def __init__(self):
		controller = Controller()
		handlers = [
			(r"/room", RoomHandler, {'controller': controller}),
			(r"/game", GameHandler, {'controller': controller})
		]
		web.Application.__init__(self, handlers)

if __name__ == "__main__":
	log.enable_pretty_logging()
    #log.app_log.level = logging.INFO
	options.parse_command_line()
	try:
		application = Server()
		server = httpserver.HTTPServer(application)
		server.listen(8888)
		ioloop.IOLoop.instance().start()
	except KeyboardInterrupt:
		ioloop.IOLoop.instance().stop()
		print("Server closed")
