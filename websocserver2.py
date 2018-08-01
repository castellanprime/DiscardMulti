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

from tornado import ( web, options, httpserver, ioloop, 
						websocket, log, escape 
					)
from random import randint

from serverenums import ( RoomGameState, RoomGameStatus, 
						RoomRequest, ClientRcvMessage 
					)	
from room import Room
from utils import PlayerGameConn, DiscardMessage

class Controller(object):
	""" This handles the rooms that houses a game """
	
	def __init__(self):
		self.rooms = []		# list of Rooms
		self.game_conns = []	# list of PlayerGameConns	

	def create_room(self, num_of_players):
		""" 
		This creates a room and adds to the list of rooms. 
 
		:param num_of_players: Number of players allowed for the game in the room 		
		:returns: str -- the room_id 
		"""
		room_id = uuid.uuid4().hex
		room = Room(room_id)
		room.set_num_of_game_players(num_of_players)
		self.rooms.append(room)
		return room_id

	def get_all_rooms(self):
		"""
		This gets all the rooms available with number of current
		players and number of players remaining to start game.

		:returns: list -- the room list
		"""
		rooms = []
		if len(self.rooms) > 0:
			for room in self.rooms:
				rooms.append(
					{ 
						'roomid': room.get_room_id(),
						'num_of_cur_players': room.get_num_of_cur_players(), 
						'num_of_players_remaining' : room.get_num_of_players_remaining()
					}
				)
		return rooms

	def can_join(self, room_id, user_id):
		"""
		This determines if a particular player can join a room. 
		
		:param room_id: Room identifier
		:param user_id: Player identifier
		:returns: bool -- True if player can join, False if otherwise
		"""
		for room in self.rooms:
			if room.get_room_id() == room_id:
				if all(( room.is_not_full(), 
					room.is_player_in_room(user_id) == False )):
					return True
		return False

	def can_start_game(self, room_id, user_id):
		"""
		This determines if a particular player belonging to a
		room can start the game in the room.

		:param room_id: Room identifier
		:param user_id: Player identifier
		:returns: bool -- True if player can start game, False if otherwise
		"""
		for room in self.rooms:
			if all(( room.get_room_id() == room_id,
				room.is_player_in_room(user_id) == True,
				room.has_game_started() == False )):
				return True 
		return False

	def start_game(self, room_id):
		"""
		This starts the game in a room.

		:param room_id: Room identifier
		"""
		for room in self.rooms:
			if room.get_room_id() == room_id:
				room.start_new_game()

	def get_all_roomates(self, user_id, room_id):
		"""
		This gets all the roomates in a room.

		:param user_id: Player identifier
		:param room_id: Room identifier
		:returns: list -- all the roomates of a particular Player
		roomates = []
		"""
		for room in self.rooms:
			if all((room.get_room_id() == room_id, 
				room.is_player_in_room(user_id) == True )):
				roomates = room.get_roomates()
				break
		return roomates

	def add_player_to_room(self, room_id, user_id, username):
		"""
		This adds a player to a room

		:param room_id: Room identifier
		:param user_id: Player identifier
		:param username: Player username
		"""
		for room in self.rooms:
			if room.get_room_id() == room_id:
				room.add_player(username, user_id)
				break

	def broadcast_game_message(self, user_id, room_id, msg):
		"""
		Server broadcasts messages to all roomates
		
		:param user_id: Player identifier
		:param room_id: Room identifier
		:param msg: Message to be broadcasted
		"""
		if len(self.game_conns) > 0:
			for player_conns in self.game_conns:
				conn = player_conns.wssocket
				conn.write_message(DiscardMessage.to_json(msg))

	def all_roomates_cb(self):
		roomates = []
		for game_conn in self.game_conns:
			msg = json.dumps({'cmd': 'ASK_FOR_ROOMATES'})
			game_conn.conn.write_message(msg)

	def add_game_conn(self, user_id, username, room_id, conn):
		"""
		This associates a websocket to a player and adds it
		to the list of game connections if the association 
		does not already exist

		:param user_id: Player identifier
		:param username: Player username
		:param room_id: Room identifier
		:param conn: Websocket connection
		"""
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
			prompt_ = username + " just joined game"
			msg_ = DiscardMessage(cmd=ClientRcvMessage.PLAYER_JOINED_GAME.value,
				prompt=prompt_)
			self.broadcast_game_message(user_id, room_id, msg_)
			#game_conn.startCallBack()
		print("[[ Out of add_game_conn ]]")

	def get_roomates_game_conns(self, user_id, room_id):
		""" 
		This returns all the connections of the roomates 
		of a Player excluding the Player.

		:param user_id: Player identifier
		:param room_id: Room identifier
		:returns: list -- list of game connections
		"""
		roomates_game_conns = [game_conn for game_conn in self.game_conns
			if all((game_conn.user_id != user_id,
				game_conn.room_id == room_id ))]
		return roomates_game_conns

	def reply_on_game_conn(self, user_id, room_id, msg):
		"""
		Server sends a message to a particular Player
		
		:param user_id: User identifier		
		:param room_id: Room identifier
		:param msg: Message to be sent to Player
		"""
		print("[[ In reply_on_game_conn ]]")
		for game_conn in self.game_conns:
			if all(( game_conn.user_id == user_id, 
				game_conn.room_id == room_id)):
				game_conn.wssocket.write_message(
					DiscardMessage.to_json(msg)
				)
				break

	def stop_all_roomates_cb(self, room_id):
		for game_conn in self.game_conns:
			if game_conn.room_id == room_id:
				game_conn.stopCallBack()

	def get_current_player(self, roomid):
		for room in self.rooms:
			if room.get_room_id() == room_id:
				return room.get_current_player()

	def handle_wsmessage(self, msg):
		"""
		Handles websocket(game) messages

		:param
		"""
		print("[[ In handle_wsmessage ]]")
		cmd = RoomGameStatus[msg.cmd]
		msg_ = {}
		prompt_ = ""
		data = msg.get_data()
		room_id = data['roomid']
		user_id = data['userid']
		if cmd == RoomGameStatus.ARE_ROOMATES_IN_GAME:
			for room in self.rooms:
				print("[[ In rooms ]]")
				print("Room-id-1: ", room.get_room_id(), 
					" room-id-2: ", room_id)
				if room.get_room_id() == room_id:
					print("[[ In rooms 45 ]]")
					if all(( room.has_game_started() == False,
						 room.get_num_of_players_remaining() > 0 )):
						print("[[ Waiting ]]")
						prompt_ = 'Waiting for ' + \
							str(room.get_num_of_players_remaining()) + \
							' players to join'
						msg_ = DiscardMessage(cmd=ClientRcvMessage.ARE_ROOMATES_IN_GAME_REP.value,
							prompt=prompt_)
						self.reply_on_game_conn(user_id, room_id, msg_)
					elif all(( room.has_game_started() == False,
						 room.get_num_of_players_remaining() == 0 )):
						print("[[ Success ]]")
						msg_ = DiscardMessage(cmd=ClientRcvMessage.GAME_MESSAGE_REP.value,
							prompt=ClientRcvMessage.GAME_CAN_BE_STARTED_REP.value)
						self.broadcast_game_message(user_id, room_id, msg_)
						#self.stop_all_roomates_cb(room_id)
					else:
						print("[[ Player is trying to see if game has started ]]")
						msg_ = DiscardMessage(cmd=ClientRcvMessage.GAME_MESSAGE_REP.value,
							prompt=ClientRcvMessage.GAME_HAS_STARTED_REP.value)
						self.reply_on_game_conn(user_id, room_id, msg_)
				print("[[ Out of rooms ]]")
		elif cmd == RoomGameStatus.GAME_MESSAGE:
			msg_ = DiscardMessage(cmd=ClientRcvMessage.GAME_MESSAGE_REP.value,
				prompt='Game is in session')
			self.reply_on_game_conn(user_id, room_id, msg_)

	def remove_game_conn(self, user_id):
		""" 
		This removes the client game conn from the server. 
		Called on the close of the websocket connection

		:param user_id: Player identifier
		"""
		for room in self.rooms:
			for player in room.get_roomates():
				if player.user_id == user_id:
					print(player.nickname, "'s connection has been closed")
					break
		self.game_conns = [ game_conn for game_conn in self.game_conns
					if game_conn.user_id != user_id
				]

	def is_there_an_initial_player(self, room_id):
		for room in self.rooms:
			if room.get_room_id() == room_id:
				return room.is_there_an_initial_player()
	
	def shutdown(self):
		"""
		This checks if there are no more players playing.

		:returns: bool -- True if there are no more players playing. False if otherwise
		"""
		return len(self.game_conns) == 0

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
		"""Handles requests concerning all the rooms"""
		rep = self.get_query_argument('cmd')
		cmd = RoomRequest[rep]
		msg_ = {}
		if cmd == RoomRequest.GET_ROOMATES:
			user_id = self.get_query_argument('userid')
			room_id = self.get_query_argument('roomid')
			list_of_roomates = self.controller.get_all_roomates(user_id,
						room_id)
			msg_ = DiscardMessage(cmd=ClientRcvMessage.GET_ROOMATES_REP.value,
				data=list_of_roomates)
		elif cmd == RoomRequest.GET_ROOMS:
			list_of_rooms = self.controller.get_all_rooms()
			msg_ = DiscardMessage(cmd=ClientRcvMessage.GET_ROOMS_REP.value,
				data=list_of_rooms)
		elif cmd == RoomRequest.GET_CURRENT_PLAYER:
			player = self.controller.get_current_player()
			msg_ = DiscardMessage(cmd=ClientRcvMessage.GET_CURRENT_PLAYER.value, 
				prompt='Currently playing: ',
				data=player)
		self.write(DiscardMessage.to_json(msg_))

	def post(self):
		"""Handles requests concerning a room"""
		recv_data = escape.json_decode(self.request.body)
		user_id = recv_data.get('userid')
		username = recv_data.get('username')
		query = self.get_query_argument('cmd')
		cmd = RoomRequest[query]
		msg_ = {}
		if cmd == RoomRequest.CREATE_A_ROOM:
			num_of_players = recv_data.get('num_of_players')
			if num_of_players == 0:
				raise web.HTTPError(status_code=400, 
					log_message="Argument num_of_players can't be zero")
			else:
				room_id = self.controller.create_room(num_of_players)
				self.controller.add_player_to_room(room_id, user_id, username)	
				msg_ = DiscardMessage(cmd=ClientRcvMessage.CREATE_A_ROOM_REP.value,
					data=room_id)			
				self.write(DiscardMessage.to_json(msg_))
		elif cmd == RoomRequest.JOIN_ROOM:
			room_id = recv_data.get('roomid')
			if self.controller.can_join(room_id, user_id):
				self.controller.add_player_to_room(room_id, user_id, username)
				prompt_ = "You have been added to room " + str(room_id)
				msg_ = DiscardMessage(cmd=ClientRcvMessage.JOIN_ROOM_REP.value,
					prompt=prompt_)
				self.write(DiscardMessage.to_json(msg_))
			else:
				raise web.HTTPError(status_code=500, 
					log_message="Room is full")
		elif cmd == RoomRequest.START_GAME:
			room_id = recv_data.get('roomid')
			if self.controller.can_start_game(room_id, user_id):
				self.controller.start_game(room_id)
				msg_ = DiscardMessage(cmd=ClientRcvMessage.START_GAME_REP.value,
					prompt=ClientRcvMessage.GAME_HAS_STARTED_REP.value)
			else:
				msg_ = DiscardMessage(cmd=ClientRcvMessage.START_GAME_REP.value,
					prompt=ClientRcvMessage.GAME_HAS_ALREADY_STARTED_REP.value)
			self.write(DiscardMessage.to_json(msg_))
		elif cmd == RoomRequest.SET_FIRST_PLAYER:
			room_id = recv_data.get('roomid')
			if self.controller.is_there_an_initial_player(room_id) == False:
				self.controller.set_initial_player(room_id, user_id)
				msg_ = DiscardMessage(cmd=ClientRcvMessage.SET_FIRST_PLAYER_REP,
					prompt='Player to start:', 
					data=username)
			else:
				msg_ = DiscardMessage(cmd=ClientRcvMessage.SET_FIRST_PLAYER_REP.value,
					prompt='Player to start',
					data=self.controller.get_initial_player())
			self.write(DiscardMessage.to_json(msg_))
		elif cmd == RoomRequest.LEAVE_ROOM: 
			pass
		else:
			pass

class DocumentationHandler(web.RequestHandler):
		def get(self):
			self.render('rules.html')

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
		
	def on_message(self, msg):
		# called anytime a new message is received
		print("Received from client ,msg=", msg)
		self.controller.handle_wsmessage(DiscardMessage.to_obj(msg))

	def check_origin(self, origin):
		return True

	def on_close(self):
		self.controller.remove_game_conn(self.clientId)
		if self.controller.shutdown():
			sys.exit()

class Server(web.Application):
	""" This is the main entry point to the server"""
	def __init__(self):
		controller = Controller()
		handlers = [
			(r"/room", RoomHandler, {'controller': controller}),
			(r"/game", GameHandler, {'controller': controller}),
			(r"/doc", DocumentationHandler)
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
	except (SystemExit, KeyboardInterrupt):
		ioloop.IOLoop.instance().stop()
		print("Server closed")
