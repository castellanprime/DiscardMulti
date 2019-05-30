"""
	Command-line client UI interface
	This is designed to be used to be in multiplayer.
"""

import zmq
import sys
import argparse
import logging

from uuid import uuid4

from players import Human
from serverenums import ( ClientRcvMsg, 
	RoomRequest,
	GameStatus,
	GameRequest,
	ClientResponse,
	LoopChoices,
	MessageDestination
)
from model import PlayerModel

# root_logger = logging.getLogger()
# root_logger.setLevel(logging.INFO)
# stream_handler = logging.StreamHandler(sys.stdout)
# stream_handler.setFormatter(logging.Formatter(logging.BASIC_FORMAT))
# root_logger.addHandler(stream_handler)

class CmdUI(object):
	def __init__(self, port):
		self._logger = logging.getLogger(__name__)
		self.ctx = zmq.Context()
		self.socket = self.ctx.socket(zmq.PAIR)
		self.socket.connect('tcp://127.0.0.1:{}'.format(port))
		self.player = None
		self.game_id = None
		self.current_player = None
		self.model = PlayerModel()
		self.msg_recv = None

	'''BEGIN:  Entry methods'''
	def get_str_input(self, question):
		while True:
			choice = input(question)
			if any(( choice is None, not choice.strip() )):
				print('Error: Empty string entered!!!')
			else:
				return choice

	def get_int_input(self, question):
		while True:
			choice = self.get_str_input(question)
			try:
				choice = int(choice)
				return choice
			except ValueError as err:
				print(err)

	def validate_user_entry(self, input_func_cb, 
			input_question, validation_params):
		choice = input_func_cb(input_question)
		while choice in validation_params == False:
			print('Error: Option choosen not in ',
				'valid options=', validation_params)
			choice = input_func_cb(input_question)
		return choice
		
	'''END: Entry methods'''	

	''' BEGIN: Menu string'''
	@staticmethod
	def landing_page_menu_str():
		return '\n'.join([
			'\n Choose from these options:',
			'j) Join an existing room(Recommended)',
			'c) Create a room',
			'e) Exit',
			'\nSelect option: '
		])

	@staticmethod
	def room_menu_str(self):
		return 'How many players do you want to play with' + \
			'[1-7]: '

	@staticmethod
	def choose_room_menu_str():
		return 'Choose room to join: '

	def landing_page_menu(self):
		while True:
			choice = self.validate_user_entry(
				input_func_cb = self.get_str_input,
				input_question_cb = self.landing_page_menu_str(),
				validation_params = ['j', 'c', 'q']
			)
			choice = LoopChoices(choice)
			if choice == LoopChoices.JOIN_ROOM:
				room = self.find_room()
				if room:
					self.join_room(room)
					break
			elif choice == LoopChoices.CREATE_ROOM:
				self.create_new_room()
				break
			elif choice == LoopChoices.LEAVE_GAME:
				self.close_on_panic()

	@staticmethod
	def game_menu_str():
		return '\n'.join(['\nMenu Options:\n',
		'Select an option below related to an action.\n',
		'h -- help and rules in a browser',
		'r -- help and rules in your command line',
		'p -- play your turn. Note you have to play to skip',
		'q -- quit game\n',
		'Enter your option: '
		])

	def game_menu(self):
		self.print_current_playing()
		choice = self.validate_user_entry(
			input_func_cb = self.get_str_input,
			input_question_cb = CmdUI.game_menu_str(),
			validation_params = ['h', 'r', 'p','q']
		)
		answer=LoopChoices(choice)
		if answer == LoopChoices.PRETTY_HELP:
			return dict()
		elif answer == LoopChoices.CMD_RULES:
			return dict()
		elif answer == LoopChoices.PLAY_ROUND:
			return self.generate_message_for_netclient(
					self.player.play(), dest='game')
		elif answer == LoopChoices.LEAVE_GAME:
			return self.generate_message_for_netclient(
				{'cmd': GameRequest.STOP_GAME},
				dest=MessageDestination.GAME
			)

	def choose_player_menu_str(self, roomates):
		return '\n'.join(['\nList of roomates:', roomates, 
			'Choose initial player: '])

	''' END: Menu string '''

	def print_current_playing(self):
		msg_snd = self.generate_message_for_netclient(
			{'cmd': RoomRequest.GAME_REQUEST,
		  	'next_cmd': GameRequest.GET_GAME_STATUS,
			'room_id': self.player.room_id,
			'game_id': self.game_id,
			},
			dest=MessageDestination.GAME
		)
		self.socket.send_pyobj(msg_snd)
		msg_recv = self.socket.recv_pyobj()
		print(msg_recv.get_payload_value('prompt'))
		self.current_player = msg_recv.get_payload_value('nickname')
	
	def generate_message_for_netclient(self, msg,
		post=False, get=False):
		msg_snd = msg
		if post:
			msg_snd['req_type'] = 'POST'
		if get:
			msg_snd['req_type'] = 'GET'
		return msg_snd
			
	def create_new_user(self):
		print('\n\nEnter your credentials:\n')
		user_id = uuid4().hex
		user_name = self.get_str_input('What is your username: ')
		self.player = Human(user_id, self,
			self.model, user_name)
	
	def create_new_room(self):
		print('\n\n\t====Creating a new room====')
		self.create_new_user()
		room_name = self.get_str_input("What is the room's name: ")
		num_of_players = self.validate_user_entry(
			input_func_cb = self.get_int_input,
			input_question_cb = CmdUI.room_menu_str(),
			validation_params = [x for x in range(1, 8)]
		)
		num_of_players = num_of_players + 1
		msg_snd = self.generate_message_for_netclient(
			{ 'user_name': self.player.nickname,
			'user_id': self.player.user_id,
			'num_of_players': num_of_players,
			'room_name': room_name,
			'cmd': RoomRequest.CREATE_A_ROOM.value
			},
			dest=MessageDestination.WEB,
			post=True
		)
		self.socket.send_pyobj(msg_snd)
		msg_recv = self.socket.recv_pyobj()
		self.player.room_id = msg_recv.get_payload_value('data')

	def find_room(self):
		print('\n\n\t====Getting rooms to join====')
		msg_snd = self.generate_message_for_netclient(
			{ 'cmd' : RoomRequest.GET_ROOMS.value },
			dest=MessageDestination.WEB,
			get=True
		)
		self.socket.send_pyobj(msg_snd)
		msg_recv = self.socket.recv_pyobj()
		room_list = msg_recv.get_payload_value('data')
		if room_list:
			ls_ = [{key: value 
				for key, value in value.items()
				if key != 'room_id'
			} for value in room_list]
			ls_[:] = [str(ind)+') '+ repr(value) 
				for ind, value in enumerate(ls_)
			]
			rooms_str = '\n'.join(ls_)
			print('The rooms available: ', rooms_str)
			choice = self.validate_user_entry(
				input_func_cb = self.get_int_input,
				input_question_cb = CmdUI.choose_room_menu_str(),
				validation_params = [x for x in range(len(ls_))]
			)
			room = room_list[choice]
			return room
		print("Can't find rooms. You can try to find rooms",
			" again (Recommended) or create a room")
		return None

	def join_room(self, room):
		print('\n\n\t=====Joining room====')
		self.create_new_user()
		self.player.room_id = room['room_id']
		msg_snd = self.generate_message_for_netclient(
			{ 'user_name': self.player.nickname,
			'user_id': self.player.user_id,
			'room_id': room['room_id'],
			'cmd': RoomRequest.JOIN_ROOM.value
			}, 
			dest=MessageDestination.WEB,
			post=True
		)
		self.socket.send_pyobj(msg_snd)
		msg_recv = self.socket.recv_pyobj()
		print(msg_recv.get_payload_value('prompt'))	

	def print_enum_as_sentence(self, st):
		s = " ".join(st.split('_'))
		print(s)
	
	def create_new_game_conn(self):
		print('[[ In create_new_game_conn ]]')
		msg_snd = self.generate_message_for_netclient(
			{ 'cmd': RoomRequest.START_GAME.value,
			'room_id': self.player.room_id,
			'user_id': self.player.user_id,
			'user_name': self.player.nickname,
			},
			dest=MessageDestination.GAME
		)
		self.socket.send_pyobj(msg_snd)
		while True:
			print('Waiting for game connection')
			msg_recv= self.socket.recv_pyobj()
			self.print_enum_as_sentence(
				msg_recv.get_payload_value('prompt')
			)
			print("Message received: ", msg_recv)
			if (msg_recv.get_payload_value('prompt') ==
					ClientResponse.GAME_HAS_STARTED_REP.value):
				self.game_id = msg_recv.get_payload_value('data')['game_id']
				self.player.set_deck(msg_recv.get_payload_value('data')['cards'])
				self.player.top_card = msg_recv.get_payload_value('extra_data')
				return
	
	def choose_initial_player(self):
		print('[[ In choose_initial_player ]]')
		msg_snd = self.generate_message_for_netclient(
			{ 'cmd': RoomRequest.GET_ROOMATES.value,
			'user_id': self.player.user_id,
			'room_id': self.player.room_id
			 },
			get=True,
			dest=MessageDestination.WEB
		)
		self.socket.send_pyobj(msg_snd)
		print('[[ Getting roomates ]]')
		msg_recv = self.socket.recv_pyobj()
		roomates = msg_recv.get_payload_value('data')
		ls = [str(ind) + ') ' + str(value) 
			for ind, value in enumerate(roomates)]
		roomates_str = '\n'.join(ls)
		choice = self.validate_user_entry(
			input_func_cb = self.get_int_input,
			input_question_cb = self.choose_player_menu_str(roomates_str),
			validation_params = [x for x in range(len(roomates))]
		)
		roomate = roomates[choice]
		msg_snd = self.generate_message_for_netclient(
			{ 'cmd': RoomRequest.GAME_REQUEST.value,
			'next_cmd': RoomRequest.SET_FIRST_PLAYER.value,
			'room_id': self.player.room_id,
			'user_id': roomate.user_id,
			'data': self.game_id
			},
			dest=MessageDestination.GAME,
		)
		self.socket.send_pyobj(msg_snd)
		msg_recv = self.socket.recv_pyobj()
		print(msg_recv.get_payload_value('prompt'))

	def close_game(self):
		self.socket.close()
		self.ctx.term()
		sys.exit(0)

	def close_on_panic(self):
		self.socket.send_pyobj(
			self.generate_message_for_netclient(
				{'cmd': GameRequest.STOP_GAME.value},
				dest=MessageDestination.GAME
			)
		)
		msg = self.socket.recv_pyobj()
		self._logger.info('Received on exit={}'.format(str(msg)))
		self.close_game()

	# Method of entry
	def main(self):
		self.landing_page_menu()
		self.create_new_game_conn()
		self.choose_initial_player()
		while True:
			msg_snd = self.game_menu()
			if all([self.current_player == self.player.nickname, msg_snd]):
				self.socket.send_pyobj(msg_snd)
				msg_recv = self.socket.recv_obj()
				if msg_recv.cmd == GameStatus.ENDED:
					print('Player ended game session')
					self.close_game()
				if msg_recv.cmd == ClientRcvMsg.GAME_MESSAGE_REP.value:
					self.player.set_message_to_process(msg_recv)
			else:
				print('Not your turn!!', 
					self.current_player, ' is still playing!!')
		
if __name__ == '__main__':
	parser = argparse.ArgumentParser()
	parser.add_argument('-p', '--server_port', 
		help='Enter the port number for the client server port',
		type=int)
	parser.add_argument('-v', '--verbose',
		help='Turn on logging')
	args = parser.parse_args()
	c = None
	if args.server_port:
		try:
			c = CmdUI(args.server_port)
			c.main()
		except(SystemExit, KeyboardInterrupt):
			c.close_on_panic()
			print('\n Player has exited game \n')
			
