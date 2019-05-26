"""
	This is responsible for sending 
	to, and receiving from the server

	on_recv() is the primary way to use a ZMQStream

"""

import zmq
import logging
import requests
import sys
import argparse

from tornado import ioloop as TLoop, websocket, gen
from zmq.eventloop.future import Context
from zmq.eventloop.zmqstream import ZMQStream
from zmq.eventloop import ioloop
from serverenums import (
	RoomRequest,
	GameRequest,
	ClientResponse,
	GameStatus
)
from utils import DiscardMsg
from playercmdui import CmdUI


root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setFormatter(logging.Formatter(logging.BASIC_FORMAT))
root_logger.addHandler(stream_handler)

ctx = zmq.Context.instance()


class NetClient(object):
	
	def __init__(self, port, room_url, game_url):
		self._logger = logging.getLogger(__name__)
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
		req = None
		if other_msg['req_type'] == 'POST':
			headers = {'Content-type':'application/json', 
				'Accept':'text/plain'}
			req = requests.post(self.room_url, data=msg,
				headers=headers)
		if other_msg['req_type'] == 'GET':
			req = requests.get(self.room_url,
				params=other_msg)
		self.socket.send_pyobj(DiscardMsg.to_obj(req.text))
		self._logger.info('Sent msg={} to the room handler'.format(str(msg)))

	@gen.coroutine
	def read_with_websocket(self):
		if self.wsconn_close == True:
			self.wsconn.close()
			self.socket.send({
				'cmd': 'GAME_CONNECTION_CLOSED'
			})
			return
		msg_recv = yield self.wsconn.read_message()
		self._logger.info('Received from websocket={}'.format(str(msg_recv)))
		if msg_recv is None:
			self.wsconn.close()
			self.socket.send({
				'cmd':'GAME_CONNECTION_CLOSED'
			})
		return DiscardMsg.to_obj(msg_recv)

	def compose_message_to_server(self, msg):
		data_ = { key:value 
					for key, value in msg.items()
					if key not in ['cmd', 'user_id',
					'room_id', 'dest', 'req_type']
		}
		self._logger.info('Message to compose: '.format(str(data_)))
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
		if msg:
			msg_snd = self.compose_message_to_server(msg)
			if isinstance(self.wsconn, 
				websocket.WebSocketClientConnection):
				self._logger.info('Sending game request')
				# Cannot send a dict(somehow)
				yield self.wsconn.write_message(msg_snd)
			else:
				raise RuntimeError("Websocket connection closed")
		else:
			self.wsconn_close = True

	@gen.coroutine
	def poll_for_connections(self):
		self._logger.info('Polling for connections')
		msg_snd = {
			'cmd':RoomRequest.START_GAME.value,
			'room_id':self.room_id, 
			'user_id':self.user_id
		}
		while True:
			if self.has_wsconn_initialised == True:	
				yield self.send_with_websocket(msg_snd)
			msg_recv = yield self.read_with_websocket()
			self._logger.info(msg_recv.get_payload_value('prompt'))
			if self.has_wsconn_initialised == False:
				self.has_wsconn_initialised = True
			if (msg_recv.get_payload_value('prompt') ==
				ClientResponse.GAME_HAS_STARTED_REP.value):
				self.socket.send_pyobj(msg_recv)
				break

	@gen.coroutine
	def init_game_conn(self):
		self._logger.info('Creating initial game server connection')
		try:
			url = self.game_url + '?user_id=' + self.user_id \
				+ '&room_id=' + self.room_id \
				+ '&user_name=' + self.user_name
			self.wsconn = yield websocket.websocket_connect(url)
		except Exception as err:
			print("Connection error: {}".format(err))
		else:
			yield self.poll_for_connections()

	@gen.coroutine
	def communicate_with_server(self):
		self._logger.info('Communication loop')
		while True:
			msg_recv = self.socket.recv_pyobj()
			if all(( 'cmd' in msg_recv.keys(), 
				msg_recv['cmd'] == GameRequest.STOP_GAME.value)):
				self.cleanup()
			msg_snd = self.compose_message_to_server(msg_recv)
			if msg_recv['dest'] == 'WEB':
				self.send_to_web_handler(msg_snd, msg_recv)
			if msg_recv['dest'] == 'GAME':
				if self.has_wsconn_initialised == False:
					yield self.init_game_conn()
				else:
					yield self.send_with_websocket(msg_snd)
					msg_recv = yield self.read_with_websocket()
					self.socket.send_pyobj(msg_recv)

	def cleanup(self):
		self.socket.send_pyobj(DiscardMsg(
			cmd=GameStatus.ENDED
		))
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
	ui = None
	if args.port:
		try:
			ui = CmdUI(args.port)
			import threading
			t = threading.Thread(target=ui.main)
			t.start()
			n = NetClient(args.port, 
				"http://localhost:8888/room",
				"ws://localhost:8888/game")
			TLoop.IOLoop.instance().add_callback(
				n.communicate_with_server
			)
			TLoop.IOLoop.instance().start()
		except (SystemExit, KeyboardInterrupt):
			ui.close_on_panic()
			TLoop.IOLoop.instance().stop()
			print("NetClient closed")
