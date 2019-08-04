"""
	This is responsible for sending 
	to, and receiving from the server

	on_recv() is the primary way to use a ZMQStream

"""

import zmq
import logging
import requests
import sys
import uuid
# import argparse

from tornado import ioloop as TLoop, websocket, gen
# from zmq.eventloop.future import Context
from logging import handlers
from zmq.eventloop.zmqstream import ZMQStream
from serverenums import (
	GameRequest,
	GameStatus,
	MessageDestination
)
from gamemessage import DiscardMsg
from playercmdui import CmdUI

root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)

stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setLevel(logging.INFO)
stream_handler.setFormatter(logging.Formatter(logging.BASIC_FORMAT))

file_handler = handlers.RotatingFileHandler(f'cmdui_{str(uuid.uuid4())}.log', maxBytes=(1048576*5), backupCount=7)
file_handler.setLevel(logging.DEBUG)
f_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(f_format)

root_logger.addHandler(stream_handler)
root_logger.addHandler(file_handler)

ctx = zmq.Context.instance()


def get_random_port():
	import socket
	s = socket.socket()
	s.bind(("", 0))
	port = s.getsockname()[1]
	s.close()
	return port

import time
from functools import wraps


def retry(ExceptionToCheck, tries=4, delay=3, backoff=2, logger=None):
    """Retry calling the decorated function using an exponential backoff.

    http://www.saltycrane.com/blog/2009/11/trying-out-retry-decorator-python/
    original from: http://wiki.python.org/moin/PythonDecoratorLibrary#Retry

    :param ExceptionToCheck: the exception to check. may be a tuple of
        exceptions to check
    :type ExceptionToCheck: Exception or tuple
    :param tries: number of times to try (not retry) before giving up
    :type tries: int
    :param delay: initial delay between retries in seconds
    :type delay: int
    :param backoff: backoff multiplier e.g. value of 2 will double the delay
        each retry
    :type backoff: int
    :param logger: logger to use. If None, print
    :type logger: logging.Logger instance
    """
    def deco_retry(f):

        @wraps(f)
        def f_retry(*args, **kwargs):
            mtries, mdelay = tries, delay
            while mtries > 1:
                try:
                    return f(*args, **kwargs)
                except ExceptionToCheck:
                    msg = "%s, Retrying in %d seconds..." % (mdelay)
                    if logger:
                        logger.warning(msg)
                    else:
                        print(msg)
                    time.sleep(mdelay)
                    mtries -= 1
                    mdelay *= backoff
            return f(*args, **kwargs)

        return f_retry  # true decorator

    return deco_retry


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
		# self.socket.bind('inproc://uisocket')
		self.socket.bind('tcp://127.0.0.1:{}'.format(port))
		self.stream = ZMQStream(self.socket)
		self.stream.on_recv(self.communicate_with_server)
		self.has_wsconn_initialised = False
		self.room_id = None
		self.user_id = None
		self.user_name = None
		self.user_exit = False  # Only use if the user actually exited from the menu option

	def send_to_web_handler(self, msg, other_msg):
		req = None
		if other_msg.get('req_type') == 'POST':
			headers = {'Content-type':'application/json', 
				'Accept':'text/plain'}
			req = requests.post(self.room_url, data=msg,
				headers=headers)
		if other_msg.get('req_type') == 'GET':
			req = requests.get(self.room_url,
				params=other_msg)
		self._logger.debug('Sent msg={} to the room handler'.format(str(msg)))
		self._logger.debug('Received from room handler: {0}'.format(str(req.text)))
		self.socket.send_pyobj(DiscardMsg.to_obj(req.text))


	@gen.coroutine
	def read_with_websocket(self):
		if self.wsconn_close == True:
			self.wsconn.close()
			self.socket.send({
				'cmd': 'GAME_CONNECTION_CLOSED'
			})
			return
		msg_recv = yield self.wsconn.read_message()
		self._logger.debug('Received from websocket={}'.format(str(msg_recv)))
		if msg_recv is None:
			self.wsconn.close()
			self.socket.send_pyobj({
				'cmd':'GAME_CONNECTION_CLOSED'
			})
		msg = DiscardMsg.to_obj(msg_recv)
		self._logger.debug('Received from websocket(Decoded)={}'.format(str(msg)))
		return msg

	def set_conn_parameters(self, msg):
		if 'user_name' in msg.keys():
			self.user_name = msg.get('user_name')
		if 'room_id' in msg.keys():
			self.room_id = msg.get('room_id')
		if 'user_id' in msg.keys():
			self.user_id = msg.get('user_id')

	def compose_message_to_server(self, msg):
		self.set_conn_parameters(msg)
		msg_snd = DiscardMsg(**msg)
		return DiscardMsg.to_json(msg_snd)
		

	@gen.coroutine
	def send_with_websocket(self, msg):
		if msg:
			msg_snd = self.compose_message_to_server(msg)
			if isinstance(self.wsconn, 
				websocket.WebSocketClientConnection):
				self._logger.debug('Sending game request')
				# Cannot send a dict(somehow)
				yield self.wsconn.write_message(msg_snd)
			else:
				raise RuntimeError("Websocket connection closed")
		else:
			self.wsconn_close = True

	@gen.coroutine
	def poll_for_connections(self):
		self._logger.debug('Polling for connections')
		msg_snd = {
			'cmd':DiscardMsg.Request.START_GAME,
			'room_id':self.room_id, 
			'user_id':self.user_id
		}
		self._logger.info('Waiting for game to be started')
		while True:
			if self.has_wsconn_initialised:
				yield self.send_with_websocket(msg_snd)
			msg_recv= yield self.read_with_websocket()
			self._logger.debug(msg_recv.get_payload_value('prompt'))
			if self.has_wsconn_initialised == False:
				self.has_wsconn_initialised = True
			if (msg_recv.get_payload_value('prompt') ==
				DiscardMsg.Response.GAME_HAS_STARTED):
				self.socket.send_pyobj(msg_recv)
				break

	@gen.coroutine
	@retry(Exception, logger=root_logger)
	def reconnect_to_server(self):
		self._logger.debug('Recreating game server connection')
		try:
			self._logger.debug(
				f'Game url={self.game_url}' \
					f', User_id={self.user_id}, Room_id={self.room_id}' \
					f', Username={self.user_name}'
			)
			url = self.game_url + '?user_id=' + self.user_id \
				  + '&room_id=' + self.room_id \
				  + '&user_name=' + self.user_name
			self.wsconn = yield websocket.websocket_connect(url)
		except Exception as err:
			raise Exception("Connection error: {}".format(err))
		else:
			yield self.poll_for_connections()

	@gen.coroutine
	def init_game_conn(self, msg):
		self._logger.debug('Creating initial game server connection')
		try:
			self.set_conn_parameters(msg)
			self._logger.debug(
				f'Game url={self.game_url}' \
				f', User_id={self.user_id}, Room_id={self.room_id}' \
				f', Username={self.user_name}'
			)
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
		while True:
			msg_recv = self.socket.recv_pyobj()
			if msg_recv.get('cmd') == GameRequest.STOP_GAME:
				self.cleanup()
			if msg_recv.get('dest') == MessageDestination.WEB:
				msg_snd = self.compose_message_to_server(msg_recv)
				self.send_to_web_handler(msg_snd, msg_recv)
			if msg_recv.get('dest') == MessageDestination.GAME:
				if self.has_wsconn_initialised == False:
					yield self.init_game_conn(msg_recv)
				else:
					yield self.send_with_websocket(msg_recv)
					msg_recv = yield self.read_with_websocket()
					self.socket.send_pyobj(msg_recv)

	def cleanup(self):
		self.socket.send_pyobj(DiscardMsg(
			cmd=GameStatus.ENDED
		))
		self.user_exit = True
		self.socket.close()
		ctx.term()
		sys.exit(0)


if __name__ == '__main__':
	ui, t = None, None
	try:
		# We have to use a port since you can only use one set of pairs bound to a
		# an address at any time
		port = get_random_port()
		ui = CmdUI(port)
		import threading

		t = threading.Thread(target=ui.nonblocking_main)
		t.start()
		n = NetClient(
			port,
			"http://localhost:8888/room",
			"ws://localhost:8888/game")
		n._logger.debug(f'Running on a port: {str(port)}')
		print(f'Running on a port: {str(port)}')
		TLoop.IOLoop.current().spawn_callback(n.communicate_with_server)
		TLoop.IOLoop.current().start()
	except (SystemExit, KeyboardInterrupt):
		if not n.user_exit:
			ui.close_on_panic()
		t.join()
		TLoop.IOLoop.current().stop()
		print("NetClient closed")
