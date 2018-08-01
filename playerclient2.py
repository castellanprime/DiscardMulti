"""
	Client module for the game clients(Player)

	# yield a Future returns a result
"""


import requests
import json
import sys
import uuid
import logging

from tornado import ioloop, websocket, gen

from model import Model
from players import Human
from serverenums import ( ClientRcvMessage, RoomGameStatus,
		RoomRequest, MainLoopChoices)
from utils import DiscardMessage


class PlayerController(object):

	def __init__(self, room_url, game_url, doc_url):
		self.wsconn = None
		self.player = None
		self.model = Model()
		self.wsconn_close = False
		self.room_url = room_url 
		self.game_url = game_url 
		self.doc_url = doc_url
		self.has_initialised = False 
		self.has_initial_player_been_choosen = False

	def get_str_input(self, question):
		"""
		This gets a string input

		:param question: Prompt for user to give an answer to
		:returns: str -- User answer
		"""
		choice = input(question)
		while any(( choice is None, 
			not choice.strip() )):
			print("You entered any empty answer")
			choice = input(question)
		return choice

	def get_int_input(self, question):
		"""
		This gets a integer

		:param question: Prompt for user to give an answer to
		:returns: int -- User answer
		"""
		while True:
			choice = input(question)
			try:
				choice = int(choice)
				return choice
			except ValueError as err:
				print(err)

	def create_new_user(self):
		"""	This creates a new Human user """
		user_id = uuid.uuid4().hex 
		self.player = Human(user_id, self, self.model)

		question = 'What is your username?: '
		username = self.get_str_input(question)
		self.player.set_nickname(username)

	def create_room(self):
		""" This creates a room	"""
		print("=== Creating a room ===")
		self.create_new_user()
		question = 'How many players do you want to play with:'
		num_of_players = self.get_int_input(question)	
		while num_of_players == 0:
			num_of_players = self.get_int_input(question)

		msg = {'username': self.player.get_nickname(), \
		 	'userid': self.player.get_user_id(), \
			'num_of_players':num_of_players}
		param = {'cmd': RoomRequest.CREATE_A_ROOM.value}
		req = requests.post(self.room_url, 
			json=msg, params=param)
		response = DiscardMessage.to_obj(req.text)
		print("Your new room id=", response.get_payload_value(value='data'))
		self.player.set_room_id(response.get_payload_value(value='data'))

	def find_room(self):
		""" 
		This find rooms 

		:returns: bool -- True if rooms has been found. False if otherwise
		"""
		print('==== Getting rooms to play the game ====')	
		return_value = False
		param = {'cmd': RoomRequest.GET_ROOMS.value}
		req = requests.get(self.room_url, 
			params=param)
		rooms = DiscardMessage.to_obj(req.text)
		if rooms.get_payload_value(value='data'):
			ls = [str(ind)+') '+ str(value) 
				for ind, value in enumerate(
				rooms.get_payload_value(value='data'))
			]
			room_str = '\n'.join(ls)
			print('The rooms available:', '\n', room_str)
			choice = self.get_int_input('Choose room to join: ')
			while choice >= len(ls):
				choice = self.get_int_input('Choose room to join: ')
			room_ = rooms.get_payload_value(value='data')
			room = room_[choice]
			print(room)
			
			self.create_new_user()

			self.player.set_room_id(room['roomid'])
			print('You selected: ', self.player.get_room_id())
			
			param = { 'cmd': RoomRequest.JOIN_ROOM.value }
			msg = {
				'username': self.player.get_nickname(), 
				'userid':self.player.get_user_id(), 
				'roomid': room['roomid']
			}
			req = requests.post(self.room_url, 
				json=msg, params=param)
			response = DiscardMessage.to_obj(req.text)
			print(response)
			return_value = True 
		return return_value 

	def show_roomates(self):
		""" This shows roomates """
		param = {
			'cmd': RoomRequest.GET_ROOMATES.value,
			'userid':self.player.get_user_id(),
			'roomid':self.player.get_room_id()
		}
		req = requests.get(self.room_url, 
			params=param)
		response = DiscardMessage.to_obj(req.text)
		ls = [str(ind)+') '+value for ind,
				value in enumerate(
				response.get_payload_value(value='data'))]
		if ls:
			room_str = '\n'.join(ls)
			print('My roomates:', '\n', room_str)
		else:
			print('You have no roomates yet!!')

	def choose_wait_or_create(self):
		question = 'Do you want to wait(w) for a room to come up(Recommended) ' + \
			'go ahead and create(c) a room?(w/c)?: '
		choice = self.get_str_input(question)
		while choice in ['w', 'c'] == False:
			print('Wrong option')
			choice = self.get_str_input(question)
		return choice

	def negotiate(self):
		""" This finds or creates a room """
		print('==== Starting game ====')

		success = self.find_room()
		if success == False:
			print("Can't find any rooms")
			while success == False:
				success = self.find_room()
				if success:
					break 
				choice = self.choose_wait_or_create()
				if choice == 'c':
					choice = self.choose_wait_or_create()
					self.create_room()
					break
			

	def gen_ping(self):
		""" 
		This generates a ping message to send to 
		the server to ask if roomates can actually
		start playing the game
		""" 
		msg_ = DiscardMessage(cmd=RoomGameStatus.ARE_ROOMATES_IN_GAME.value,
			data={
				'roomid': self.player.get_room_id(),
				'userid': self.player.get_user_id()
			}
		)
		return DiscardMessage.to_json(msg_)

	def start_game(self):
		""" This sends a START_GAME request to game server """
		msg_ = {
			'userid':self.player.get_user_id(),
			'roomid':self.player.get_room_id()
		}
		param = {'cmd': RoomRequest.START_GAME.value }
		req = requests.post(self.room_url, 
			json=msg_, params=param)
		response = DiscardMessage.to_obj(req.text)
		print(response)

	def gen_test_message(self):
		""" This generates a user-generated message 

		:param question: Question to be asked
		"""
		choice = None
		if self.has_initialised == True:
			choice = self.get_ping()
		else:
			choice = self.get_str_input('Send a message: ')
		if choice == "End":
			msg_ = {}
			return json.dumps(msg_)
		else:
			msg_ = DiscardMessage(cmd=RoomGameStatus.GAME_MESSAGE.value,
				data={
					'roomid': self.player.get_room_id(),
					'userid': self.player.get_user_id(),
					'message': choice
				}
			)
			return DiscardMessage.to_json(msg_)

	def generate_wsmessage(self):
		""" This generates the message to send to the game server """
		print("[[ In generate_wsmessage ]]")
		msg = None
		if self.has_initialised == False:
			msg = self.gen_ping()
		else:
			if self.has_initial_player_been_choosen == False:
				msg = self.gen_test_message()
			else:
				msg = self.main_loop()
			if msg == json.dumps({}):
				return None 
		return msg

	def handle_msg(self, message):
		""" Handles messages received from the game server """
		print("[[ In handle_msg ]]")
		msg = DiscardMessage.to_obj(message)
		if all(( msg.cmd == ClientRcvMessage.GAME_MESSAGE_REP.value,
			msg.get_prompt() == ClientRcvMessage.GAME_CAN_BE_STARTED_REP.value )):
			print("[[ Starting game ]]")
			if self.has_initialised == False:
				self.has_initialised = True
				self.start_game()
				self.choose_initial_player()
		elif all(( msg.cmd == ClientRcvMessage.GAME_MESSAGE_REP.value,
			msg.get_prompt() == ClientRcvMessage.GAME_HAS_STARTED_REP.value )):
			print("[[ Joining stared game ]]")
			if self.has_initialised == False:
				self.has_initialised = True
				self.choose_initial_player()
		elif msg.cmd== ClientRcvMessage.ASK_FOR_ROOMATES_REP:
			self.show_roomates()
		print("Received game message from server: ", msg)
		if self.has_initial_player_been_choosen == True:
			self.player.set_message_to_process(msg)
	
	def choose_initial_player(self):
		param = { 'cmd': RoomRequest.SET_FIRST_PLAYER.value }
		msg_ = {
			'userid': self.player.get_user_id(),
			'roomid': self.player.get_room_id(),
			'username': self.player.get_nickname()
		}
		rep = requests.post(self.room_url, params=param,
			json=msg_)
		response = DiscardMessage.to_obj(rep)
		print(response.get_payload_value(value='prompt'), 
			response.get_payload_value(value='data'))
		if self.has_initial_player_been_choosen == False:
			self.has_initial_player_been_choosen = True

	def print_currently_playing(self):
		param = { 'cmd' : RoomRequest.GET_CURRENT_PLAYER.value }
		rep = requests.get(self.room_url, params=param)
		response = DiscardMessage.to_obj(rep)
		return ( response.get_payload_value(value='prompt'), 
		response.get_payload_value(value='data'))		

	@gen.coroutine
	def connect_on_websocket(self):
		""" This makes a websocket connection to the game server """
		try:
			url = self.game_url + '?userId=' + \
				self.player.get_user_id() + \
				'&roomId=' + self.player.get_room_id() + \
				'&username=' + self.player.get_nickname()
			self.wsconn = yield websocket.websocket_connect(
				url)
		except Exception as err:
			print("Connection error: {}".format(err))
		else:
			print("Initial server connection")
			yield self.communicate_with_websocket()

	# Experimental
	def menu(self):
		return 'Menu Options:\n\n' + \
		'Select the option below related to an action.\n\n' + \
		'h/H/pretty/Pretty - Help and rules in a browser\n' + \
		'r/R/rules/Rules - Help and rules in your command line\n' + \
		'p/p/play/Play - Play your turn. Note you have to play to skip' + \
		'q/Q/quit/Quit - Exit the game\n\n' + \
		'What is your option: '
		
	# Experimental
	def main_loop(self):
		"""This is the main loop in the game"""
		choice = None
		msg_ = {}
		prompt, player = self.print_currently_playing()
		print(prompt, player)
		choice = self.get_enum_choice(
			self.get_str_input(self.menu())
		)
		while choice == None:
			print('Wrong option')
			choice = self.get_enum_choice(
				self.get_str_input(self.menu())
			)
		if choice == MainLoopChoices.PRETTY_HELP:
			#req = requests.get(self.doc_url)
			msg_ = DiscardMessage(cmd='DOCUMENTATION')
		elif choice == MainLoopChoices.CMD_RULES:
			msg_ = DiscardMessage(cmd='DOCUMENTATION')
		elif choice == MainLoopChoices.PLAY_ROUND:
			msg_ = self.player.play()		
		elif choice == MainLoopChoices.LEAVE_GAME:
			msg_ = DiscardMessage(cmd='DOCUMENTATION')
		return msg_						

	@gen.coroutine
	def send_wsmessage(self):
		""" This sends a websocket message """
		print("[[ In send_wsmessage ]]")
		msg = self.generate_wsmessage()
		if msg:
			if isinstance(self.wsconn, 
				websocket.WebSocketClientConnection):
				print("[[ Writing game message to send to server ]]")
				yield self.wsconn.write_message(msg) 
			else:
				raise RuntimeError('Websocket connection closed')
		else:
			self.wsconn_close = True

	@gen.coroutine
	def communicate_with_websocket(self):
		""" 
		This receives messages from the game server and
		sends back messages to the game server on the 
		websocket connection 
		"""
		print("[[ In communicate_with_websocket ]]")
		recv_msg = None 
		while True:
			if self.wsconn_close == True:
				self.wsconn.close()
				sys.exit()
			recv_msg = yield self.wsconn.read_message()
			if recv_msg is None:
				self.wsconn.close()
				sys.exit()
			self.handle_msg(recv_msg)
			yield self.send_wsmessage()
		print("IOLoop terminate")

	def get_enum_choice(self, choice):
		""" 
		Choices for the main loop. A player is expected to choose
		from them

		:param choice: The choice to return a MainLoopChoice
		:returns Enum -- A MainLoopChoice
		"""
		if choice in [ 'h', 'h', 'pretty', 'PRETTY']:
			return MainLoopChoices.PRETTY_HELP
		elif choice in [ 'r', 'R', 'rules', 'RULES']:
			return MainLoopChoices.CMD_ROUND
		elif choice in [ 'p', 'P', 'play', 'PLAY']:
			return MainLoopChoices.PLAY_ROUND
		elif choice in [ 'q', 'Q', 'quit', 'QUIT']:
			return MainLoopChoices.LEAVE_GAME
		return None

	@gen.coroutine
	def main(self):
		""" Thjs is the entry point for the ioloop """
		if self.player == None:
			self.negotiate()
		yield self.connect_on_websocket()

if __name__ == "__main__":
	try:
		client = PlayerController(
			"http://localhost:8888/room", 
			"ws://localhost:8888/game",
			"http://localhost:8888.doc")
		ioloop.IOLoop.instance().add_callback(client.main)
		ioloop.IOLoop.instance().start()
	except (SystemExit, KeyboardInterrupt):
		ioloop.IOLoop.instance().stop()
		print("Client closed")
