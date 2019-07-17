"""
    Server program
    This holds the game loop and connects to
    net client
"""

'''Cant use await for zmq since I need asyncio to run the '''

import sys
import logging
from roomserver import RoomServer
from gameserver import GameServer
from tornado import (
    web, options, httpserver,
    ioloop, websocket, log
)
from serverenums import GameRequest
from gamemessage import DiscardMsg

def enable_server_logging():
    # options.options.logging = None
    options.options['log_file_prefix'] = 'mainserver.log'
    options.parse_command_line()

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    # access_log = logging.getLogger('tornado.access')
    # gen_log = logging.getLogger('tornado.general')
    # app_log = logging.getLogger('tornado.application')
    # access_log.setLevel(logging.DEBUG)
    # gen_log.setLevel(logging.DEBUG)
    # app_log.setLevel(logging.DEBUG)

    # file_handler = logging.FileHandler('mainserver.log')
    # access_log.addHandler(file_handler)
    # gen_log.addHandler(file_handler)
    # app_log.addHandler(file_handler)
    # access_log.propagate = False
    # gen_log.propagate = False
    # app_log.propagate = False

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(logging.INFO)
    stream_handler.setFormatter(logging.Formatter(logging.BASIC_FORMAT))
    root_logger.addHandler(stream_handler)

class RoomHandler(web.RequestHandler):
    def initialize(self, controller, logger):
        self.room_server = controller
        self._logger = logger

    def write_error(self, status_code, **kwargs):
        err_cls, err, traceback = kwargs['exc_info']
        if isinstance(err, web.HTTPError) and err.log_message:
            msg_ = DiscardMsg(cmd=DiscardMsg.Response.ERROR,
                              data=err.log_message)
            self.write(DiscardMsg.to_json(msg_))

    def get(self):
        rep = self.get_query_argument('cmd')
        cmd = DiscardMsg.Request[rep]
        msg_ = {}
        if cmd == DiscardMsg.Request.GET_ROOMMATES:
            user_id = self.get_query_argument('user_id')
            room_id = self.get_query_argument('room_id')
            list_of_roomates = self.room_server.get_all_roomates(user_id,
                        room_id)
            msg_ = DiscardMsg(
                cmd=DiscardMsg.Response.GET_ROOMMATES,
                roomates=list_of_roomates
            )
        elif cmd == DiscardMsg.Request.GET_ROOMS:
            list_of_rooms = self.room_server.get_all_rooms()
            msg_ = DiscardMsg(
                cmd=DiscardMsg.Response.GET_ROOMS,
                rooms=list_of_rooms
            )
        self._logger.debug('[RoomHandler] Sent back to the client:{0}'.format(str(msg_)))
        self.write(DiscardMsg.to_json(msg_))

    def post(self):
        recv_data = DiscardMsg.to_obj(self.request.body)
        self._logger.debug('[RoomHandler] Post Object received: {0}'.format(recv_data))
        user_id = recv_data.get_payload_value('user_id')
        cmd = recv_data.cmd
        msg_snd = {}
        if cmd == DiscardMsg.Request.CREATE_A_ROOM:
            user_name = recv_data.get_payload_value('user_name')
            num_of_players = recv_data.get_payload_value('num_of_players')
            room_name = recv_data.get_payload_value('room_name')
            room_id = self.room_server.add_room(num_of_players, room_name)
            self.room_server.add_player(room_id, user_id, user_name)
            msg_snd = DiscardMsg(
                cmd=DiscardMsg.Response.CREATE_A_ROOM,
                room_id=room_id
            )
        elif cmd == DiscardMsg.Request.JOIN_ROOM:
            room_id = recv_data.get_payload_value('room_id')
            user_name = recv_data.get_payload_value('user_name')
            if self.room_server.can_join(room_id, user_id):
                self.room_server.add_player(room_id, user_id, user_name)
                self._logger.info('You have been added to room: {0}'.format(str(room_id)))
                self._logger.debug('[RoomHandler] You have been added to room: {0}'.format(str(room_id)))
                msg_snd = DiscardMsg(
                    cmd=DiscardMsg.Response.JOIN_ROOM,
                    prompt='You have been added to room: {0}'.format(str(room_id))
                )
            else:
                raise web.HTTPError(status_code=500, 
                    log_message='Room is full')
        self._logger.debug('[RoomHandler] Sent back to the client:{0}'.format(str(msg_snd)))
        self.write(DiscardMsg.to_json(msg_snd))


class GameHandler(websocket.WebSocketHandler):

    def initialize(self, controller, logger):
        # Called on each request to the handler
        self._room_server = controller
        self._logger = logger

    def check_origin(self, origin):
        return True

    def open(self, *args, **kwargs):
        self._client_id = self.get_argument('user_id')
        room_id = self.get_argument('room_id')
        self._room_server.add_game_conn(self._client_id, room_id, self)
        self._logger.debug('[GameHandler] Websocket opened. ClientID = {0}'.format(self._client_id))

    def on_message(self, message):
        self._logger.debug('[GameHandler] received message {msg} from client'.format(msg=message))
        self._room_server.handle_msg(message)

    def on_close(self):
        self._room_server.remove_game_conn(self._client_id)
        if self._room_server.shutdown():
            sys.exit(0)

class Server(web.Application):
    def __init__(self):
        self._logger = logging.getLogger(__name__)
        self.room_server = RoomServer()

        handlers = [
            (r'/game', GameHandler, {'controller': self.room_server, 'logger': self._logger}),
            (r'/room', RoomHandler, {'controller': self.room_server, 'logger': self._logger})
        ]
        web.Application.__init__(self, handlers)

    def close(self):
        self.room_server.handle_msg(DiscardMsg.to_json(DiscardMsg(
            cmd=DiscardMsg.Request.GAME_REQUEST,
            next_cmd=GameRequest.STOP_GAME)
        ))

    def close_socket(self):
        self.room_server.game_socket.close()
        self.room_server.context.term()

if __name__ == '__main__':
    enable_server_logging()
    app, t = None, None
    try:
        game_server = GameServer()
        import threading
        t = threading.Thread(target=game_server.mainMethod)
        t.start()
        app = Server()
        server = httpserver.HTTPServer(app)
        server.listen(8888)
        ioloop.IOLoop.current().start()
    except(SystemExit, KeyboardInterrupt):
        app.close()
        t.join()
        app.close_socket()
        ioloop.IOLoop.current().stop()
        print('Server closed')
