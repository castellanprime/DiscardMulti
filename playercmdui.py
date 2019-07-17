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
from serverenums import (
	GameStatus,
	GameRequest,
	LoopChoices,
	MessageDestination
)
from model import PlayerModel
from gamemessage import DiscardMsg


class CmdUI(object):
	def __init__(self, port):
		self._logger = logging.getLogger(__name__)
		self.ctx = zmq.Context()
		self.socket = self.ctx.socket(zmq.PAIR)
		self.socket.connect('tcp://127.0.0.1:{0}'.format(port))
		self.player = None
		self.current_player = None
		self.model = PlayerModel()
		self.current_roomates = []
		self.msg_recv = None

	'''BEGIN:  Entry methods'''
	def get_str_input(self, question):
		while True:
			choice = input(question)
			if any((choice is None, not choice.strip())):
				print('Error: Empty string entered!!!')
				self._logger.error('Error: Empty string entered!!!')
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
		while (choice in validation_params) is False:
			print(f'Error: Option choosen not in valid options={validation_params}')
			self._logger.debug(f'Error: Option choosen not in valid options={validation_params}')
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
			'q) Exit',
			'\nSelect option: '
		])

	@staticmethod
	def room_menu_str():
		return 'How many players do you want to play with' + \
			'[1-7]: '

	@staticmethod
	def choose_room_menu_str():
		return 'Choose room to join: '

	def landing_page_menu(self):
		while True:
			choice = self.validate_user_entry(
				input_func_cb=self.get_str_input,
				input_question=CmdUI.landing_page_menu_str(),
				validation_params=['j', 'c', 'q']
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
			input_func_cb=self.get_str_input,
			input_question=CmdUI.game_menu_str(),
			validation_params=['h', 'r', 'p','q']
		)
		answer=LoopChoices(choice)
		if answer == LoopChoices.PRETTY_HELP:
			return dict()
		elif answer == LoopChoices.CMD_RULES:
			return dict()
		elif answer == LoopChoices.PLAY_ROUND:
			return dict(
				dest=MessageDestination.GAME,
				**self.player.play()
			)
		elif answer == LoopChoices.LEAVE_GAME:
			return dict(
				cmd=GameRequest.STOP_GAME
			)

	def choose_player_menu_str(self, roomates):
		return '\n'.join(['\nList of roomates:', roomates, 
			'Choose initial player: '])

	''' END: Menu string '''

	def print_current_playing(self):
		msg_snd = dict(
			cmd=DiscardMsg.Request.GAME_REQUEST,
			next_cmd=GameRequest.GET_GAME_STATUS,
			room_id=self.player.room_id,
			game_id=self.player.game_id,
			dest=MessageDestination.GAME,
			delivery=MessageDestination.UNICAST
		)
		self._logger.debug(f'Sent a {GameRequest.GET_GAME_STATUS.name} message to the backend')
		self.socket.send_pyobj(msg_snd)
		msg_recv = self.socket.recv_pyobj()
		self.current_player = msg_recv.get_payload_value('user_id')
		self._logger.debug(f'Current player={self.current_player}'\
			f' , current roomates={str(self.current_roomates)}')
		cur_player = [item.get('nickname') for item in self.current_roomates
			if self.current_player == item.get('user_id')][0]
		print('Currently playing: {0}'.format(cur_player))
		self._logger.debug('Currently playing: {0}'.format(cur_player))
			
	def create_new_user(self):
		print('\n\nEnter your credentials:\n')
		user_id = uuid4().hex
		user_name = self.get_str_input('What is your username: ')
		self.player = Human(user_id, self, self.model)
		self.player.nickname = user_name
		self._logger.debug(f'Created a new user: {self.player}')
	
	def create_new_room(self):
		print('\n\n\t====Creating a new room====')
		self.create_new_user()
		room_name = self.get_str_input("What is the room's name: ")
		num_of_players = self.validate_user_entry(
			input_func_cb=self.get_int_input,
			input_question=CmdUI.room_menu_str(),
			validation_params=[x for x in range(1, 8)]
		)
		num_of_players = num_of_players + 1
		self.socket.send_pyobj(dict(
			user_name=self.player.nickname,
			user_id=self.player.user_id,
			num_of_players=num_of_players,
			room_name=room_name,
			cmd=DiscardMsg.Request.CREATE_A_ROOM,
			dest=MessageDestination.WEB,
			req_type='POST'
		))
		self._logger.debug(f'Sent a {DiscardMsg.Request.CREATE_A_ROOM.name} message to the backend')
		msg_recv = self.socket.recv_pyobj()
		self.player.room_id = msg_recv.get_payload_value('room_id')
		self._logger.debug(f'Player created and added themselves to a room: {self.player}')

	def find_room(self):
		print('\n\n\t====Getting rooms to join====')
		self.socket.send_pyobj(dict(
			cmd=DiscardMsg.Request.GET_ROOMS.name,
			dest=MessageDestination.WEB,
			req_type='GET'
		))
		msg_recv = self.socket.recv_pyobj()
		room_list = msg_recv.get_payload_value('rooms')
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
				input_func_cb=self.get_int_input,
				input_question=CmdUI.choose_room_menu_str(),
				validation_params=[x for x in range(len(ls_))]
			)
			room = room_list[choice]
			self._logger.debug(f'Found room: {room}')
			return room
		print("Can't find rooms. You can try to find rooms",
			" again (Recommended) or create a room")
		self._logger.debug('Could not find a room')
		return None

	def join_room(self, room):
		print('\n\n\t=====Joining room====')
		self.create_new_user()
		self.player.room_id = room.get('room_id')
		self.socket.send_pyobj(dict(
			user_name=self.player.nickname,
			user_id=self.player.user_id,
			room_id=room.get('room_id'),
			cmd=DiscardMsg.Request.JOIN_ROOM,
			dest=MessageDestination.WEB,
			req_type='POST'
		))
		self._logger.debug(f'Sent a {DiscardMsg.Request.JOIN_ROOM.name} message to the backend')
		msg_recv = self.socket.recv_pyobj()
		print(msg_recv.get_payload_value('prompt'))
		self._logger.debug(f"Joined a room: {room.get('room_id')}")

	def create_new_game_conn(self):
		self.socket.send_pyobj(dict(
			cmd=DiscardMsg.Request.START_GAME.name,
			room_id=self.player.room_id,
			user_id=self.player.user_id,
			user_name=self.player.nickname,
			dest=MessageDestination.GAME
		))
		self._logger.debug(f'Sent a {DiscardMsg.Request.START_GAME.name} message to the server')
		while True:
			print('Waiting for game connection')
			msg_recv = self.socket.recv_pyobj()
			print(
				" ".join(msg_recv.get_payload_value('prompt').name.split('_'))
			)
			print("Cards Received: ", msg_recv.get_payload_value('cards'))
			self._logger.debug(f"Received message from the server {str(msg_recv.get_payload_value('prompt'))}")
			if (msg_recv.get_payload_value('prompt') ==
					DiscardMsg.Response.GAME_HAS_STARTED):
				self.player.game_id = msg_recv.get_payload_value('game_id')
				self.player.set_deck(msg_recv.get_payload_value('cards'))
				self._logger.debug(f"Cards {str(msg_recv.get_payload_value('cards'))}")
				self.player.top_card = msg_recv.get_payload_value('extra_data')
				return
	
	def choose_initial_player(self):
		self.socket.send_pyobj(dict(
			cmd=DiscardMsg.Request.GET_ROOMMATES.name,
			user_id=self.player.user_id,
			room_id=self.player.room_id,
			req_type='GET',
			dest=MessageDestination.WEB
		))
		self._logger.debug(f'Sent a {DiscardMsg.Request.GET_ROOMMATES.name} message to the server')
		msg_recv = self.socket.recv_pyobj()
		self.current_roomates = msg_recv.get_payload_value('roomates')
		self._logger.debug(f'Received current roomates: {str(self.current_roomates)}')
		self._logger.info(f'Received current roomates: {str(self.current_roomates)}')
		roomates = self.current_roomates[:]
		roomates.append(dict(nickname=self.player.nickname, user_id=self.player.user_id))
		ls = [str(ind) + ') ' + str(value) 
			for ind, value in enumerate(roomates)]
		roomates_str = '\n'.join(ls)
		choice = self.validate_user_entry(
			input_func_cb=self.get_int_input,
			input_question=self.choose_player_menu_str(roomates_str),
			validation_params=[x for x in range(len(roomates))]
		)
		roomate = roomates[choice]
		print(f'Chose roomate: {str(roomate)}')
		self._logger.debug(
			f'Sent an {GameRequest.SET_INITIAL_PLAYER.name} message to backend' \
			f' for roomate: {str(roomate)}' \
			f' for room: {self.player.room_id}'
		)
		self.socket.send_pyobj(dict(
			cmd=DiscardMsg.Request.GAME_REQUEST,
			next_cmd=GameRequest.SET_INITIAL_PLAYER,
			room_id=self.player.room_id,
			user_id=roomate.get('user_id'),
			user_name=roomate.get('nickname'),
			game_id=self.player.game_id,
			dest=MessageDestination.GAME,
			delivery=MessageDestination.UNICAST
		))
		msg_recv = self.socket.recv_pyobj()
		print(msg_recv.get_payload_value('prompt'))
		self._logger.debug(f"Received message from the server: {str(msg_recv.get_payload_value('prompt'))}")

	def close_game(self):
		self.socket.close()
		self.ctx.term()
		sys.exit(0)

	def close_on_panic(self):
		self.socket.send_pyobj(dict(
			cmd=GameRequest.STOP_GAME
		))
		msg = self.socket.recv_pyobj()
		self._logger.debug(f'Received on exit={str(msg)}')
		self.close_game()

	# Method of entry
	def main(self):
		self._logger.info('CmdUI')
		self.landing_page_menu()
		self.create_new_game_conn()
		self.choose_initial_player()
		while True:
			msg_snd = self.game_menu()
			if all([self.current_player == self.player.user_id, msg_snd]):
				self.socket.send_pyobj(msg_snd)
				msg_recv = self.socket.recv_obj()
				if msg_recv.get('cmd') == GameStatus.ENDED:
					print('Player ended game session')
					self._logger.debug('Player ended game session')
					self.close_game()
				if msg_recv.cmd == DiscardMsg.Response.PLAY_MOVE:
					self.player.set_message_to_process(msg_recv)
			else:
				print('Not your turn!!', 
					self.current_player, ' is still playing!!')
				self._logger.debug(f'Not your turn!!!' \
					f'{self.current_player} is still playing!!')
		
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
			c = CmdUI()
			c.main()
		except(SystemExit, KeyboardInterrupt):
			c.close_on_panic()
			print('\n Player has exited game \n')
