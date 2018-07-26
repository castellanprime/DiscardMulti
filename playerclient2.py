"""
	Client module for the game clients(Player)

	# yield a Future returns a result
"""

from tornado import ioloop, websocket, gen
from model import Model
from players import Human
from serverenums import ClientEnum
import requests
import json
import sys
import uuid

class PlayerController(object):
	def __init__(self, room_url, game_url):
		self.wsconn = None
		self.player = None
		self.model = Model()
		self.wsconn_close = False
		self.has_connected = False
		self.room_url = room_url 
		self.game_url = game_url 
		self.has_initialised = False 
		self.game_has_started = False

	def get_str_input(self, question):
		choice = input(question)
		while any(( choice is None, 
			not choice.strip() )):
			print("You entered any empty answer")
			choice = input(question)
		return choice

	def get_int_input(self, question):
		while True:
			choice = input(question)
			try:
				choice = int(choice)
				return choice
			except ValueError as err:
				print(err)

	def create_new_user(self):
		user_id = uuid.uuid4().hex 
		self.player = Human(user_id, self, self.model)

		question = 'What is your username?: '
		username = self.get_str_input(question)
		self.player.set_nickname(username)

	def create_room(self):
		print("=== Creating a room ===")
		self.create_new_user()
		question = 'How many players do you want to play with:'
		num_of_players = self.get_int_input(question)	
		while num_of_players == 0:
			num_of_players = self.get_int_input(question)

		msg = {'username': self.player.get_nickname(), \
		 	'userid': self.player.get_user_id(), \
			'num_of_players':num_of_players}
		param = {'cmd': 'CREATE_A_ROOM'}
		req = requests.post(self.room_url, 
			json=msg, params=param)
		response = json.loads(req.text)
		print("Your new room id=", response['prompt'])
		self.player.set_room_id(response['prompt'])

	def find_room(self):
		print('==== Getting rooms to play the game ====')	
		return_value = False
		param = {'cmd': 'GET_ROOMS'}
		req = requests.get(self.room_url, 
			params=param)
		rooms = json.loads(req.text)
		if rooms['lis']:
			ls = [str(ind)+') '+ str(value) 
				for ind, value in enumerate(rooms['lis'])
			]
			room_str = '\n'.join(ls)
			print('The rooms available:', '\n', room_str)
			choice = self.get_int_input('Choose room to join: ')
			while choice >= len(ls):
				choice = self.get_int_input('Choose room to join: ')
			room = rooms['lis'][choice]
			print(room)
			
			self.create_new_user()

			self.player.set_room_id(room['roomid'])
			print('You selected: ', self.player.get_room_id())
			
			param = { 'cmd': 'JOIN'}
			msg = {'username': self.player.get_nickname(), \
				'userid':self.player.get_user_id(), \
				'roomid': room['roomid']}
			req = requests.post(self.room_url, 
				json=msg, params=param)
			response = json.loads(req.text)
			print(response)
			return_value = True 
		return return_value 

	def show_roomates(self):
		param = {'cmd': 'GET_ROOMATES',
			'userid':self.player.get_user_id(),
			'roomid':self.player.get_room_id()}
		req = requests.get(self.room_url, 
			params=param)
		response = json.loads(req.text) 
		ls = [str(ind)+') '+value for ind,
				value in enumerate(response['roomates'])]
		if ls:
			room_str = '\n'.join(ls)
			print('My roomates:', '\n', room_str)
		else:
			print('You have no roomates yet!!')

	def negotiate(self):
		print('==== Starting game ====')

		success = self.find_room()
		if success == False:
			print("Can't find any rooms")
			self.create_room()

		"""
		question = 'Do you want to show your roomates(y/n)?: '
		choice = self.get_str_input(question)
		if choice == 'y':
			self.show_roomates()
		"""

	def ping(self):
		msg = {'cmd':'ARE_ROOMATES_IN_GAME',
			'roomid': self.player.get_room_id(),
			'userid': self.player.get_user_id()}
		return json.dumps(msg)

	def start_game(self):
		msg = {'userid':self.player.get_user_id(), \
			'roomid':self.player.get_room_id()}
		param = {'cmd': 'START_GAME'}
		req = requests.post(self.room_url, 
			json=msg, params=param)
		response = json.loads(req.text)
		print(response)

	def send_test_message(self):
		choice = self.get_str_input('Send a message: ')
		msg = {'cmd': 'GAME_MESSAGE',
			'roomid': self.player.get_room_id(),
			'userid': self.player.get_user_id(),
			'message': choice }
		return json.dumps(msg)

	def generate_wsmessage(self):
		print("[[ In generate_wsmessage ]]")
		msg = None
		if self.has_initialised == False:
			msg = self.ping()
		else:
			msg = self.send_test_message()
			if msg['message'] == "End":
				return None 
		return msg

	def handle_msg(self, msg):
		print("[[ In handle_msg ]]")
		cmd = ClientEnum[msg['cmd']]
		if cmd == ClientEnum.GAME_MESSAGE_REP and \
			msg['prompt'] == 'Game is initializing':
			if self.has_initialised == False:
				self.has_initialised = True
				self.start_game()
		elif cmd == ClientEnum.ASK_FOR_ROOMATES:
			self.show_roomates()
		print("Received game message from server: ", msg)
		

	@gen.coroutine
	def connect_on_websocket(self):
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

	@gen.coroutine
	def send_wsmessage(self):
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
			self.handle_msg(json.loads(recv_msg))
			yield self.send_wsmessage()
		print("IOLoop terminate")

	@gen.coroutine
	def main(self):
		if self.player == None:
			self.negotiate()
		yield self.connect_on_websocket()

if __name__ == "__main__":
	try:
		client = PlayerController("http://localhost:8888/room", 
			"ws://localhost:8888/game")
		ioloop.IOLoop.instance().add_callback(client.main)
		ioloop.IOLoop.instance().start()
	except (SystemExit, KeyboardInterrupt):
		ioloop.IOLoop.instance().stop()
		print("Client closed")
