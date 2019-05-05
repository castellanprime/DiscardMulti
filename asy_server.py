"""
	Server program
	This holds the game loop and connects to
	net client
"""

'''Cant use await for zmq since I need asyncio to run the '''

import zmq
import logging
from zmq.eventloop.future import Context
from zmq.eventloop.zmqstream import ZMQStream
from uuid import uuid4
from tornado import (
    web, options, httpserver,
	ioloop, websocket, log
)
from utils import DiscardMsg, PlayerGameConn

###
# set up logging to stdout
import sys
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setFormatter(logging.Formatter(logging.BASIC_FORMAT))
root_logger.addHandler(stream_handler)

game_engine_port = '5556'
context = Context.instance()

class RoomServer(object):
    pass

class RoomHandler(web.RequestHandler):
    pass

class GameHandler(websocket.WebSocketHandler):

    def initialize(self, controller, sock):
        self.room_server = controller
        self.game_eng_sock = sock

    def check_origin(self, origin):
        return True

    def open(self, *args, **kwargs):
        pass

    ''' This function receives a message from the client and sends that message to the game engine'''
    def on_message(self, message):
        logging.info('[PWS] received message {msg} from client'.format(msg=message))
        self.game_eng_sock.send_pyobj(DiscardMsg.to_obj(message))

    ''' This function receives a message from the game engine and sends that message back to the client'''
    @classmethod
    def publish_message(cls, msgs):
        pass

    def on_close(self):
        pass

class Server(web.Application):
    def __init__(self):
        room_server = RoomServer()
        client_sock = context.socket(zmq.PAIR)
        client_sock.connect('tcp://127.0.0.1:{port}'.format(port=game_engine_port))
        stream_sock = ZMQStream(client_sock)
        stream_sock.on_recv(GameHandler.publish_message)

        handlers = [(r'/room', GameHandler, {'controller': room_server, 'sock': stream_sock})]
        web.Application.__init__(self, handlers)

if __name__ == 'main':
    log.enable_pretty_logging()
    options.parse_command_line()
    try:
        # Somewhere here would be a game thread
        app = Server()
        server = httpserver.HTTPServer(app)
        server.listen(8888)
        ioloop.IOLoop.instance().start()
    except(SystemExit, KeyboardInterrupt):
        ioloop.IOLoop.instance().stop()
        print('Server closed')