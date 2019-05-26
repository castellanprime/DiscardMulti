"""
    Server program
    This holds the game loop and connects to
    net client
"""

'''Cant use await for zmq since I need asyncio to run the '''

import zmq, sys
import logging
from zmq.eventloop.future import Context
from zmq.eventloop.zmqstream import ZMQStream
from roomserver import RoomServer
from gameserver import GameServer
from tornado import (
    web, options, httpserver,
    ioloop, websocket, log
)
from serverenums import (
    RoomRequest,
    GameRequest,
    ClientResponse
)
from utils import DiscardMsg

###
# set up logging to stdout
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setFormatter(logging.Formatter(logging.BASIC_FORMAT))
root_logger.addHandler(stream_handler)
context = Context.instance()
game_server_port = 5556


class RoomHandler(web.RequestHandler):
    def initialize(self, controller, logger):
        self.room_server = controller
        self._logger = logger

    def write_error(self, status_code, **kwargs):
        err_cls, err, traceback = kwargs['exc_info']
        if err.log_message:
            msg_ = DiscardMsg(cmd=ClientResponse.ERROR,
                              data=err.log_message)
            self.write(DiscardMsg.to_json(msg_))

    def get(self):
        rep = self.get_query_argument('cmd')
        cmd = RoomRequest[rep]
        msg_ = {}
        if cmd == RoomRequest.GET_ROOMATES:
            user_id = self.get_query_argument('user_id')
            room_id = self.get_query_argument('room_id')
            list_of_roomates = self.room_server.get_all_roomates(user_id,
                        room_id)
            msg_ = DiscardMsg(
                cmd=ClientResponse.GET_ROOMATES_REP.value,
                data=list_of_roomates
            )
        elif cmd == RoomRequest.GET_ROOMS:
            list_of_rooms = self.room_server.get_all_rooms()
            msg_ = DiscardMsg(
                cmd=ClientResponse.GET_ROOMS_REP.value,
                data=list_of_rooms
            )
        self.write(DiscardMsg.to_json(msg_))

    def post(self):
        recv_data = DiscardMsg.to_obj(self.request.body)
        self._logger.info('Object received: {0}'.format(recv_data))
        user_id = recv_data.get_payload_value('user_id')
        cmd_str = recv_data.cmd
        cmd = RoomRequest[cmd_str]
        msg_ = {}
        if cmd == RoomRequest.CREATE_A_ROOM:
            user_name = recv_data.get_payload_value('data')['user_name']
            num_of_players = recv_data.get_payload_value('data')['num_of_players']
            room_name = recv_data.get_payload_value('data')['room_name']
            room_id = self.room_server.create_room(num_of_players, room_name)
            self.room_server.add_player(room_id, user_id, user_name)
            msg_ = DiscardMsg(
                cmd=ClientResponse.CREATE_A_ROOM_REP.value,
                data=room_id
            )
            self.write(DiscardMsg.to_json(msg_))
        elif cmd == RoomRequest.JOIN_ROOM:
            room_id = recv_data.get_payload_value('room_id')
            user_name = recv_data.get_payload_value('data')['user_name']
            if self.room_server.can_join(room_id, user_id):
                self.room_server.add_player(room_id, user_id, user_name)
                self._logger.info('You have been added to room: {0}'.format(str(room_id)))
                msg_ = DiscardMsg(
                    cmd=ClientResponse.JOIN_ROOM_REP.value,
                    prompt='You have been added to room: {0}'.format(str(room_id))
                )
                # this should be a broadcast
                self.write(DiscardMsg.to_json(msg_))
            else:
                raise web.HTTPError(status_code=500, 
                    log_message='Room is full')


class GameHandler(websocket.WebSocketHandler):

    room_server = None

    def initialize(self, controller, logger):
        GameHandler.room_server = controller
        self._logger = logger

    def check_origin(self, origin):
        return True

    def open(self, *args, **kwargs):
        self._client_id = self.get_argument('user_id')
        room_id = self.get_argument('room_id')
        GameHandler.room_server.add_game_conn(self._client_id, room_id, self)
        self._logger.info('Websocket opened. ClientID = {0}'.format(self._client_id))

    ''' This function receives a message from the client and sends that message to the game engine'''
    def on_message(self, message):
        self._logger.info('[PWS] received message {msg} from client'.format(msg=message))
        GameHandler.room_server.handle_msg(message)

    ''' This function receives a message from the game engine and sends that message back to the client'''
    @classmethod
    def publish_message(cls, msg):
        msg_ = GameHandler.room_server.game_socket.recv_pyobj(msg)
        room_id = msg_.get_payload_value('extra_data')['room_id']
        for room in GameHandler.room_server.rooms:
            if room.room_id == room_id:
                for player in room.players:
                    wbsocket = player.get('wbsocket')
                    wbsocket.write_message(DiscardMsg.to_json(msg_))

    def on_close(self):
        GameHandler.room_server.remove_game_conn(self._client_id)
        if GameHandler.room_server.shutdown():
            GameHandler.room_server.handle_msg(DiscardMsg(cmd=GameRequest.STOP_GAME))
            sys.exit(0)

class Server(web.Application):
    def __init__(self):
        self._logger = logging.getLogger(__name__)
        self.room_server = RoomServer()
        client_sock = context.socket(zmq.PAIR)
        client_sock.connect('tcp://127.0.0.1:{port}'.format(port=game_server_port))
        stream_sock = ZMQStream(client_sock)
        stream_sock.on_recv(GameHandler.publish_message)
        self.room_server.game_socket = stream_sock

        handlers = [
            (r'/game', GameHandler, {'controller': self.room_server, 'logger': self._logger}),
            (r'/room', RoomHandler, {'controller': self.room_server, 'logger': self._logger})
        ]
        web.Application.__init__(self, handlers)

    def close(self):
        self.room_server.handle_msg(DiscardMsg(cmd=GameRequest.STOP_GAME))

if __name__ == 'main':
    log.enable_pretty_logging()
    options.parse_command_line()
    app = None
    try:
        game_server = GameServer(game_server_port)
        import threading
        t = threading.Thread(target=game_server.main)
        t.start()
        app = Server()
        server = httpserver.HTTPServer(app)
        server.listen(8888)
        ioloop.IOLoop.instance().start()
    except(SystemExit, KeyboardInterrupt):
        app.close()
        ioloop.IOLoop.instance().stop()
        print('Server closed')