"""
	Server program
	This holds the game loop and connects to
	net client
"""

import json
import sys

from uuid import uuid4
from tornado import ( web, options, httpserver,
		ioloop, websocket, log, escape)
from random import randint

from room import Room
from serverenums import ( ClientRcvMsg, RoomRequest,
		RoomGameStatus )
from utils import DiscardMsg, PlayerGameConn

class Controller(object):
	def __init__(self):
		self.rooms = []
		self.game_conns = []
		self.can_player_restart_game = True

	''' == Post methods Begin =='''
	''' WebHandler Begin'''
	def create_room(self, num_of_players, room_name):
		""" 
		This creates a room and adds to the list of rooms. 
 
		:param num_of_players: Number of players allowed for the game in the room 		
		:param room_name: Name of the room
		:returns: str -- the room_id 
		"""
		room_id = uuid4().hex
		room = Room(room_id, room_name)
		room.set_num_of_game_players(num_of_players)
		self.rooms.append(room)
		return room_id

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

	def can_start_game(self, room_id, user_id):
		"""
		This determines if a particular player belonging to a
		room can start the game in the room.

		:param room_id: Room identifier
		:param user_id: Player identifier
		:returns: bool -- True if player can start game, False if otherwise
		"""
		print('[[ In can_start_game for userid:',user_id, ' and room_id:',  user_id) 
		for room in self.rooms:
			print('Room id=', room_id, ' room.get_room_id()=', room.get_room_id())
			print('room.is_player_in_room()=', room.is_player_in_room(user_id))
			print('self.can_player_restart_game=',  self.can_player_restart_game)
			if all(( room.get_room_id() == room_id,
				room.is_player_in_room(user_id) == True,
				self.can_player_restart_game == True )):
				self.can_player_restart_game = False
				print('User', user_id, ' has started this game')
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
	
	def get_game_id(self, room_id):
		"""
		This returns a game id.

		:param room_id: Room identifier
		:returns: str -- the game id
		"""
		for room in self.rooms:
			if room.get_room_id() == room_id:
				return room.get_game_id()

	def set_initial_player(self, user_id, room_id):
		"""
		This sets the player that would start playing initially

		:param user_id: User identifier
		:param room_id: Room identifier
		"""
		print("In set_initial_player")
		for room in self.rooms:
			if room.get_room_id() == room_id:
				for player in room.get_roomates():
					if player.user_id == user_id:
						print("Player selected: ", player)
						room.set_initial_player(player)
						break
		print("Out of set_initial_player")

	''' WebHandler End '''	

	''' GameHandler Methods '''
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
			game_conn = PlayerGameConn(user_id=user_id, 
					room_id=room_id, wbsocket=conn)
			print("A new game connection has been created")
			self.game_conns.append(game_conn)
			prompt_ = username + " just joined game"
			msg_ = DiscardMsg(
				cmd=ClientRcvMsg.PLAYER_JOINED_GAME.value,
				prompt=prompt_)
			self.broadcast_game_message(user_id, room_id, msg_)
		print("[[ Out of add_game_conn ]]")

	def handle_wsmessage(self, msg):
		"""
		Process game messages received from the client

		:param msg: Game message
		"""
		cmd = RoomGameStatus[msg.cmd]
		msg_ = {}
		prompt_ = ""
		room_id = msg.get_payload_value('room_id')
		user_id = msg.get_payload_value('user_id')
		if cmd == RoomGameStatus.ARE_ROOMATES_IN_GAME:
			for room in self.rooms:
				if room.get_room_id() == room_id:
					if room.has_game_started() == False:
						if room.get_num_of_players_remaining() > 0:
							print('Waiting')
							prompt_ = 'Waiting for ' + \
								str(room.get_num_of_players_remaining()) + \
								' players to join'
							msg_ = DiscardMsg(
								cmd=ClientRcvMsg.ARE_ROOMATES_IN_GAME_REP.value,
								prompt=prompt_
							)
							self.reply_on_game_conn(user_id, room_id, msg_)
						elif room.get_num_of_players_remaining() == 0:
							print('Success')
							msg_ = DiscardMsg(
								cmd=ClientRcvMsg.GAME_MESSAGE_REP.value,
								prompt=ClientRcvMsg.GAME_CAN_BE_STARTED_REP.value
							)
							self.broadcast_game_message(user_id, room_id, msg_)
					else:
						msg_ = DiscardMsg(
							cmd=ClientRcvMsg.GAME_MESSAGE_REP.value,
							prompt=ClientRcvMsg.GAME_HAS_STARTED_REP.value
						)
						self.reply_on_game_conn(user_id, room_id, msg_)
					break
		elif cmd == RoomGameStatus.GAME_MESSAGE: 
			msg_ = DiscardMsg(
				cmd=ClientRcvMsg.GAME_MESSAGE_REP.value,
				prompt='Game is in session'
			)
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
	''' GameHandler Methods '''
	''' == Post methods End == '''
	
	''' == Get methods Begin =='''
	''' WebHandler Methods '''
	def get_all_roomates(self, user_id, room_id):
		"""
		This gets all the roomates in a room.

		:param user_id: Player identifier
		:param room_id: Room identifier
		:returns: list -- all the roomates of a particular Player
		"""
		for room in self.rooms:
			if all((room.get_room_id() == room_id, 
				room.is_player_in_room(user_id) == True )):
				roomates = room.get_roomates()
				break
		return roomates
		
	def get_username(self, user_id, room_id):
		for room in self.rooms:
			if room.get_room_id() == room_id:
				return room.get_username(user_id)

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
						'room_name': room.get_name(), 
						'room_id': room.get_room_id(),
						'num_of_cur_players': room.get_num_of_cur_players(), 
						'num_of_players_remaining' : room.get_num_of_players_remaining()
					}
				)
		return rooms

	def get_initial_player(self, room_id):
		"""
		This gets the player that would start playing initially 
		:param room_id: Room identifier
		"""
		for room in self.rooms:
			if room.get_room_id() == room_id:
				return room.get_initial_player()

	def get_current_player(self, room_id):
		"""
		This gets the player that is currently playing
		:param room_id: Room identifier
		"""
		for room in self.rooms:
			if room.get_room_id() == room_id:
				return room.get_current_player()		

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
	''' WebHandler Methods '''

	''' GameHandler Methods '''
	def shutdown(self):
		"""
		This checks if there are no more players playing.
		:returns: bool -- True if there are no more players playing. False if otherwise
		"""
		return len(self.game_conns) == 0

	def broadcast_game_message(self, user_id, room_id, msg):
		"""
		Server broadcasts messages to all roomates
		
		:param user_id: Player identifier
		:param room_id: Room identifier
		:param msg: Message to be broadcasted
		"""
		if len(self.game_conns) > 0:
			for player_conn in self.game_conns:
				conn = player_conn.wbsocket
				conn.write_message(DiscardMsg.to_json(msg))

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
				game_conn.wbsocket.write_message(
					DiscardMsg.to_json(msg)
				)
				break
	''' GameHandler Methods '''
	''' == Get methods End == '''

class WebHandler(web.RequestHandler):

	def initialize(self, controller):
		self.__controller = controller

	def write_error(self, status_code, **kwargs):
		err_cls, err, traceback = kwargs['exc_info']
		if err.log_message:
			msg_ = DiscardMsg(cmd=ClientRcvMsg.ERROR, 
				data=err.log_message) 
			self.write(DiscardMsg.to_json(msg_))
	
	def get(self):
		"""Handles requests concerning all the rooms"""
		rep = self.get_query_argument('cmd')
		cmd = RoomRequest[rep]
		msg_ = {}
		if cmd == RoomRequest.GET_ROOMATES:
			user_id = self.get_query_argument('user_id')
			room_id = self.get_query_argument('room_id')
			list_of_roomates = self.__controller.get_all_roomates(user_id,
						room_id)
			msg_ = DiscardMsg(cmd=ClientRcvMsg.GET_ROOMATES_REP.value,
				data=list_of_roomates)
		elif cmd == RoomRequest.GET_ROOMS:
			list_of_rooms = self.__controller.get_all_rooms()
			msg_ = DiscardMsg(cmd=ClientRcvMsg.GET_ROOMS_REP.value,
				data=list_of_rooms)
		elif cmd == RoomRequest.GET_CURRENT_PLAYER:
			room_id = self.get_query_argument('room_id')
			player = self.__controller.get_current_player(room_id)
			print("Player: ", player)
			prompt_ = 'Currently playing: ' + player.nickname
			msg_ = DiscardMsg(cmd=ClientRcvMsg.GET_CURRENT_PLAYER_REP.value, 
				prompt=prompt_,
				data=player.nickname)
		self.write(DiscardMsg.to_json(msg_))

	def post(self):
		recv_data = DiscardMsg.to_obj(self.request.body)
		print(' Object received: ', recv_data)
		user_id = recv_data.get_payload_value('user_id')
		cmd_str = recv_data.cmd
		cmd = RoomRequest[cmd_str]
		msg_ = {}
		if cmd == RoomRequest.CREATE_A_ROOM:
			user_name = recv_data.get_payload_value('data')['user_name']
			num_of_players = recv_data.get_payload_value('data')['num_of_players']
			room_name = recv_data.get_payload_value('data')['room_name']
			room_id = self.__controller.create_room(num_of_players, room_name)
			self.__controller.add_player_to_room(room_id, user_id, user_name)
			msg_ = DiscardMsg(cmd=ClientRcvMsg.CREATE_A_ROOM_REP.value,
				data=room_id)			
			self.write(DiscardMsg.to_json(msg_))
		elif cmd == RoomRequest.JOIN_ROOM:
			room_id = recv_data.get_payload_value('room_id')
			user_name = recv_data.get_payload_value('data')['user_name']
			print('Can join')
			if self.__controller.can_join(room_id, user_id):
				self.__controller.add_player_to_room(room_id, user_id, user_name)
				prompt_ = 'You have been added to room ' + str(room_id)
				print(prompt_)
				msg_ = DiscardMsg(cmd=ClientRcvMsg.JOIN_ROOM_REP.value,
					prompt=prompt_)
				self.write(DiscardMsg.to_json(msg_))
			else:
				raise web.HTTPError(status_code=500, 
					log_message='Room is full')
		elif cmd == RoomRequest.START_GAME:
			print('[[ Attempting to start game ]]')
			room_id = recv_data.get_payload_value('room_id')
			if self.__controller.can_start_game(room_id, user_id):
				self.__controller.start_game(room_id)
				msg_ = DiscardMsg(cmd=ClientRcvMsg.START_GAME_REP.value,
					prompt=ClientRcvMsg.GAME_HAS_STARTED_REP.value,
					data=self.__controller.get_game_id(room_id)
				)
			else:
				print('[[ Sending GAME_HAS_ALREADY_STARTED_REP to ', 
					self.__controller.get_username(user_id, room_id), ']]')
				msg_ = DiscardMsg(cmd=ClientRcvMsg.START_GAME_REP.value,
					prompt=ClientRcvMsg.GAME_HAS_ALREADY_STARTED_REP.value,
					data=self.__controller.get_game_id(room_id)
				)
			self.write(DiscardMsg.to_json(msg_))
		elif cmd == RoomRequest.SET_FIRST_PLAYER:
			room_id = recv_data.get_payload_value('room_id')
			self.__controller.set_initial_player(user_id, room_id)
			player = self.__controller.get_initial_player(room_id)
			prompt_ = 'Player to start: ' + str(player.nickname)
			print(prompt_)
			msg_ = DiscardMsg(cmd=ClientRcvMsg.SET_FIRST_PLAYER_REP.value,
				prompt=prompt_, data=player.nickname)
			self.write(DiscardMsg.to_json(msg_))


class GameHandler(websocket.WebSocketHandler):
	
	def initialize(self, controller):
		self.__controller = controller

	def check_origin(self, origin):
		return True
	
	def open(self):
		self.__client_id = self.get_argument('user_id')
		room_id = self.get_argument('room_id')
		user_name = self.get_argument('user_name')
		self.__controller.add_game_conn(self.__client_id, user_name
			,room_id, self)
		print("Websocket opened. ClientID = %s" % self.__client_id)

	def on_message(self, msg):
		print("Received from client, msg=", msg)
		self.__controller.handle_wsmessage(
			DiscardMsg.to_obj(msg)
		)

	def on_close(self):
		self.__controller.remove_game_conn(self.__client_id)
		if self.__controller.shutdown():
			sys.exit()

class Server(web.Application):
	def __init__(self):
		controller = Controller()
		handlers = [
			(r"/room", WebHandler, {'controller': controller}),
			(r"/game", GameHandler, {'controller': controller})
		]
		web.Application.__init__(self, handlers)

if __name__ == '__main__':
	log.enable_pretty_logging()
	options.parse_command_line()
	try:
		application = Server()
		server = httpserver.HTTPServer(application)
		server.listen(8888)
		ioloop.IOLoop.instance().start()
	except(SystemExit, KeyboardInterrupt):
		ioloop.IOLoop.instance().stop()
		print("Server closed")
