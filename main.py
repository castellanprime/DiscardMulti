"""
	Client program
	This holds the game loop and connects to 
	net client
"""

import zmq
import time
import sys
import json

class Client(object):
	def __init__(self, port):
		self.context = zmq.Context()
		# only one PAIR socket per thread 
		self.socket = self.context.socket(zmq.PAIR)
		self.socket.connect('tcp://127.0.0.1:{}'.format(port))
		self.player = None	

	def get_str_input(self, question):
		while True:
			choice = input(question)
			if any((choice is None, not choice.strip() )):
				print("You can not enter an empty string!")
			else:
				return choice

	def get_int_input(self, question):
		while True:
			choice = input(question)
			try:
				choice = int(choice)
				return choice
			except ValueError as err:
				print(err)


	def validate_entry(self, input_cb=None, 
				input_question_cb=None,
				validation_params=[]):
		choice = input_cb(input_question_cb())
		while choice in validation_params == False:
			print('Wrong option')
			choice = input_cb(input_question())
		return choice

	def gen_post_message(self):
		msg_, payload_ = None, None
		choice = self.validate_entry(
			input_cb=self.get_int_input,
			input_question_cb=self.type_menu,
			validation_params=[1, 2]
		)
		if choice == 1:
			payload_ = self.get_str_input('Enter a string: ')
		elif choice == 2:
			payload_ = self.get_int_input('Enter a int: ')
		
		choice = self.validate_entry(
			input_cb=self.get_int_input,
			input_question_cb=self.send_menu,
			validation_params=[1, 2]
		)		
		if choice == 1:
			msg_ = {
				'cmd': 'WEB',
				'payload': payload_
			}
		elif choice == 2:
			msg_ = {
				'cmd': 'GAME',
				'payload': payload_
			}
		return msg_
		
	def type_menu(self):
		return '\n\nType Menu: \n\n' + \
			'1> Send a string\n' + \
			'2> Send an int\n\n' + \
			'Select your option: '

	def options_menu(self):
		return '\n\n Options menu: \n\n' + \
			'1] Send\n' + \
			'2] Receive\n' + \
			'3] Exit\n\n' + \
			'Selecet your option: '

	def send_menu(self):
		return '\n\nSend Menu: \n\n' + \
			'1) Post the message\n to the Web Handler\n' + \
			'2) Post the message\n to the Game Handler\n\n' + \
			'Select your option: ' 

	def main(self):
		print("Mine")
		while True:
			print("Tool")
			msg = self.socket.recv()
			print("Message received, ", msg)
			choice = self.validate_entry(
				input_cb=self.get_int_input,
				input_question_cb=self.options_menu,
				validation_params = [1,2,3]
			)
			if choice == 1:
				msg = self.gen_post_message()
				print("Message to send: ", msg)
				# instead of send, i used send_string
				# as unicade is not allowed
				self.socket.send_string(json.dumps(msg))
			elif choice == 3:
				self.socket.send({})
			if choice == 3:
				sys.exit()
			time.sleep(1)

if __name__ == '__main__':
	try:
		c = Client(sys.argv[1])
		c.main()
	except (SystemExit, KeyboardInterrupt):
		print('Client closed')
