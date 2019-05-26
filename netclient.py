"""
	This is responsible for sending 
	to, and receiving from the server

	on_recv() is the primary way to use a ZMQStream

"""

import zmq
import requests
import time
import json
import sys
import argparse

from tornado import ioloop as TLoop, websocket, gen
from zmq.eventloop.future import Context
from zmq.eventloop.zmqstream import ZMQStream
from zmq.eventloop import ioloop

from serverenums import ( ClientRcvMsg, 
	RoomRequest, RoomGameStatus,
	LoopChoices)

from utils import DiscardMsg

ctx = zmq.Context.instance()

class NetClient(object):
	
	def __init__(self, port, room_url, game_url):
		self.wsconn = None
		self.wsconn_close = False
		self.room_url = room_url
		self.game_url = game_url
		self.socket = ctx.socket(zmq.PAIR)
		# do not use localhost, because it would complain 
		# with error [zmq.error.ZMQError: No such device]
		self.socket.bind('tcp://127.0.0.1:{}'.format(port))
		self.stream = ZMQStream(self.socket)
		self.stream.on_recv(self.communicate_with_server)
		self.has_wsconn_initialised = False
		self.room_id = None
		self.user_id = None
		self.user_name = None

	def send_to_web_handler(self, msg, other_msg):
		print('[[ In send_to_web_handler ]]')
		req = None
		if other_msg['req_type'] == 'POST':
			headers = {'Content-type':'application/json', 
				'Accept':'text/plain'}
			print('==Message to send: ',msg, '==')
			req = requests.post(self.room_url, data=msg,
				headers=headers)
		if other_msg['req_type'] == 'GET':
			print('==Message to send: ',other_msg, '==')
			req = requests.get(self.room_url,
				params=other_msg)
		self.socket.send_pyobj(DiscardMsg.to_obj(req.text))

	@gen.coroutine
	def read_with_websocket(self):
		print("[[ In read_with_websocket ]]")
		msg_recv = None
		if self.wsconn_close == True:
			self.wsconn.close()
			self.socket.send({
				'cmd': 'GAME_CONNECTION_CLOSED'
			})
			return
		msg_recv = yield self.wsconn.read_message()
		print("Received from websocket: ", msg_recv)
		if msg_recv is None:
			self.wsconn.close()
			self.socket.send({
				'cmd':'GAME_CONNECTION_CLOSED'
			})
		return DiscardMsg.to_obj(msg_recv)

	def compose_message_to_server(self, msg):
		print('[[ In compose_message_to_server ]]')
		data_ = { key:value 
			for key, value in msg.items() 
			if key not in ['cmd', 'user_id', 
				'room_id', 'dest', 'req_type']}
		print('MESSAGE TO COMPOSE: ',data_)
		msg_snd = DiscardMsg(cmd=msg['cmd'], data=data_)
		if 'user_id' in msg.keys() and 'room_id' in msg.keys():
			msg_snd = DiscardMsg(cmd=msg['cmd'], 
			data=data_, user_id=msg['user_id'],
			room_id=msg['room_id'])
			self.user_id = msg['user_id']
			self.room_id = msg['room_id']
		else:
			if 'user_id' in msg.keys() and 'room_id':
				msg_snd = DiscardMsg(cmd=msg['cmd'], 
				data=data_, user_id=msg['user_id'])
				self.user_id = msg['user_id']
			if 'room_id' in msg.keys():
				msg_snd = DiscardMsg(cmd=msg['cmd'],
				data=data_, room_id=msg['room_id'])
				self.room_id = msg['room_id']
		if 'user_name' in msg.keys():
			self.user_name = msg['user_name']
		return DiscardMsg.to_json(msg_snd)
		

	@gen.coroutine
	def send_with_websocket(self, msg):
		print('[[ In send_with_websocket ]]')
		if msg:
			msg_snd = self.compose_message_to_server(msg)
			if isinstance(self.wsconn, 
				websocket.WebSocketClientConnection):
				print("[[ Writing game message to server ]]")
				# Cannot send a dict(somehow)
				yield self.wsconn.write_message(msg_snd)
			else:
				raise RuntimeError("Websocket connection closed")
		else:
			self.wsconn_close = True

	@gen.coroutine
	def poll_for_connections(self):
		print('[[Polling for connections]]')
		msg_snd = {
			'cmd':RoomGameStatus.ARE_ROOMATES_IN_GAME.value,
			'room_id':self.room_id, 
			'user_id':self.user_id
		}
		while True:
			if self.has_wsconn_initialised == True:	
				yield self.send_with_websocket(msg_snd)
			msg_recv = yield self.read_with_websocket()
			if self.has_wsconn_initialised == False:
				self.has_wsconn_initialised = True
			if (msg_recv.get_payload_value('prompt') ==	
				ClientRcvMsg.GAME_CAN_BE_STARTED_REP.value):
					msg_snd = {'cmd': RoomRequest.START_GAME.value,
						'room_id':self.room_id,
						'user_id':self.user_id,
						'req_type': 'POST'
						}
					msg__ = self.compose_message_to_server(msg_snd) 
					self.send_to_web_handler(msg__, msg_snd)
					break
			if (msg_recv.get_payload_value('prompt') ==
				ClientRcvMsg.GAME_HAS_STARTED_REP.value):
				self.socket.send_pyobj(msg_recv)
				break

	@gen.coroutine
	def init_game_conn(self):
		print('[[ In init_game_conn ]]')
		try:
			url = self.game_url + '?user_id=' + self.user_id \
				+ '&room_id=' + self.room_id \
				+ '&user_name=' + self.user_name
			self.wsconn = yield websocket.websocket_connect(url)
		except Exception as err:
			print("Connection error: {}".format(err))
		else:
			print("Initial server connection")
			yield self.poll_for_connections()

	@gen.coroutine
	def communicate_with_server(self):
		print('[[ In communicate_with_server ]]')
		while True:
			msg_recv = self.socket.recv_pyobj()
			if all(( 'cmd' in msg_recv.keys(), 
				msg_recv['cmd'] == RoomGameStatus.STOP_GAME.value)):
				self.cleanup()
			msg_snd = self.compose_message_to_server(msg_recv)
			if msg_recv['dest'] == 'WEB':
				 self.send_to_web_handler(msg_snd, msg_recv)
			if msg_recv['dest'] == 'GAME':
				if self.has_wsconn_initialised == False:
					print('Create Game Conn')
					yield self.init_game_conn()
				else:
					yield self.send_with_websocket(msg_snd)
					msg_recv = yield self.read_with_websocket()
					self.socket.send_pyobj(msg_recv)

	def cleanup(self):
		self.socket.close()
		self.ctx.term()
		sys.exit(0)


if __name__ == '__main__':
	parser = argparse.ArgumentParser()
	parser.add_argument('-p', '--port',
		help='Enter the port for the client to connect to',
		type=int)
	parser.add_argument('-v', '--verbose',
		help='Turn on logging')
	args = parser.parse_args()
	if args.port:
		try:
			n = NetClient(args.port, 
				"http://localhost:8888/room",
				"ws://localhost:8888/game")
			TLoop.IOLoop.instance().add_callback(
				n.communicate_with_server
			)
			TLoop.IOLoop.instance().start()
		except (SystemExit, KeyboardInterrupt):
			TLoop.IOLoop.instance().stop()
			print("NetClient closed")
