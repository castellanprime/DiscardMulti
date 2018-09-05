"""
	Command-line client UI interface
	This is designed to be used to be in multiplayer.
"""

import zmq
import time
import sys
import json
import argparse
import zlib
import pickle

from uuid import uuid4

from players import Human
from serverenums import ( ClientRcvMsg, 
	RoomRequest, RoomGameStatus,
	LoopChoices)

from utils import DiscardMsg
from model import PlayerModel

class CmdUI(object):
	def __init__(self, port):
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
			input_question_cb, validation_params):
		choice = input_func_cb(input_question_cb)
		while choice in validation_params == False:
			print('Error: Option choosen not in ',
				'valid options=', validation_params)
			choice = input_func_cb(input_question_cb)
		return choice
		
	'''END: Entry methods'''	

	''' BEGIN: Menu string'''
	def landing_page_menu_str(self):
		return '\n'.join([
			'\n Choose from these options:',
			'j) Join an existing room(Recommended)',
			'c) Create a room',
			'e) Exit',
			'\nSelect option: '
		])
	
	def room_menu_str(self):
		return 'How many players do you want to play with' + \
			'[1-7]: '

	def choose_room_menu_str(self):
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
				sys.exit(0)
	
	def game_menu_str(self):
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
			input_question_cb = self.game_menu_str(),
			validation_params = ['h', 'r', 'p','q']
		)
		answer=LoopChoices(choice)
		if answer == LoopChoices.PRETTY_HELP:
			msg_ = {}
		elif answer == LoopChoices.CMD_RULES:
			msg_ = {}
		elif answer == LoopChoices.PLAY_ROUND:
			self.msg_ = self.generate_message_for_netclient(
					self.player.play(), dest='game')
		elif answer == LoopChoices.LEAVE_GAME:
			msg_ = {}

	def choose_player_menu_str(self, roomates):
		return '\n'.join(['\nList of roomates:', roomates, 
			'Choose initial player: '])

	''' END: Menu string '''

	def print_current_playing(self):
		msg_snd = self.generate_message_for_netclient(
			{ 'cmd': 'GET_CURRENT_PLAYER',
			'room_id': self.player.get_room_id()
			},
			dest='web',
			get=True
		)
		self.socket.send_pyobj(msg_snd)
		msg_recv = self.socket.recv_pyobj()
		print(msg_recv.get_payload_value('prompt'))
		self.current_player = msg_recv.get_payload_value('nickname')
	
	def generate_message_for_netclient(self, msg,
		dest=None, post=False, get=False):
		msg_snd = msg
		if dest:
			msg_snd['dest'] = dest.upper()
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
			input_question_cb = self.room_menu_str(),
			validation_params = [x for x in range(1, 8)]
		)
		num_of_players = num_of_players + 1
		msg_snd = self.generate_message_for_netclient(
			{ 'user_name': self.player.get_nickname(),
			'user_id': self.player.get_user_id(),
			'num_of_players': num_of_players,
			'room_name': room_name,
			'cmd': RoomRequest.CREATE_A_ROOM.value
			},
			dest='web',
			post=True
		)
		self.socket.send_pyobj(msg_snd)
		msg_recv = self.socket.recv_pyobj()
		self.player.set_room_id(msg_recv.get_payload_value('data'))

	def find_room(self):
		print('\n\n\t====Getting rooms to join====')
		msg_snd = self.generate_message_for_netclient(
			{ 'cmd' : RoomRequest.GET_ROOMS.value },
			dest='web',
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
				input_question_cb = self.choose_room_menu_str(),
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
		self.player.set_room_id(room['room_id'])
		msg_snd = self.generate_message_for_netclient(
			{ 'user_name': self.player.get_nickname(),
			'user_id': self.player.get_user_id(),
			'room_id': room['room_id'],
			'cmd': RoomRequest.JOIN_ROOM.value
			}, 
			dest='web',
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
			{ 'cmd': RoomGameStatus.OPEN_GAME_CONN.value, 
			'room_id': self.player.get_room_id(),
			'user_id': self.player.get_user_id(),
			'user_name': self.player.get_nickname(),
			},
			dest='game'
		)
		self.socket.send_pyobj(msg_snd)
		while True:
			print('Waiting for game connection')
			msg_recv= self.socket.recv_pyobj()
			self.print_enum_as_sentence(
				msg_recv.get_payload_value('prompt')
			)
			print("Message received: ", msg_recv)
			self.game_id = msg_recv.get_payload_value('data')
			if (msg_recv.get_payload_value('prompt') in [
				ClientRcvMsg.GAME_HAS_ALREADY_STARTED_REP.value,
				ClientRcvMsg.GAME_HAS_STARTED_REP.value
			]):
				return
	
	def choose_initial_player(self):
		print('[[ In choose_initial_player ]]')
		msg_snd = self.generate_message_for_netclient(
			{ 'cmd': RoomRequest.GET_ROOMATES.value,
			'user_id': self.player.get_user_id(),
			'room_id': self.player.get_room_id()
			 },
			get=True,
			dest='web'
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
			{ 'cmd': RoomRequest.SET_FIRST_PLAYER.value,
			'room_id': self.player.get_room_id(),
			'user_id': roomate.user_id
			},
			dest='web',
			post=True
		)
		self.socket.send_pyobj(msg_snd)
		msg_recv = self.socket.recv_pyobj()
		print(msg_recv.get_payload_value('prompt'))

	def close_game(self, st=None):
		if st == 'in_game':
			self.socket.send_pyobj(self.generate_message_for_netclient(
				{ 'cmd': RoomGameStatus.STOP_GAME.value}
			))
		self.socket.close()
		self.ctx.term()
		sys.exit(0)

	def is_game_conn_open(self):
		return self.socket.closed == False

	# Method of entry
	def main(self):
		self.landing_page_menu()
		self.create_new_game_conn()
		self.choose_initial_player()
		while True:
			self.game_menu()
			if self.current_player == self.player.get_nickname():
				self.socket.send_pyobj(self.msg_recv)
				msg_recv = self.socket.recv_obj()
				if msg_recv.cmd == 'GAME_CONN_CLOSED':
					print('Player ended game session')
					self.close_entry()
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
			if c.is_game_conn_open():
				c.close_game('in_game')
			print('\n Player has exited game \n')
			
