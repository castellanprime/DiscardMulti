import zmq
import logging
import sys
import uuid

from ast import literal_eval
from logging import handlers
from zmq.eventloop.zmqstream import ZMQStream
from tornado import ioloop as TLoop, websocket
from serverenums import GameStatus
from playerui import CmdUI

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
    port_num = s.getsockname()[1]
    s.close()
    return port_num

class Client(object):
    def __init__(self, port, game_url):
        self._logger = logging.getLogger(__name__)
        self.wsconn = None
        self.wsconn_close = False
        self.has_wsconn_initialised = False
        self.user_exit = False
        self.game_url = game_url
        self.socket = ctx.socket(zmq.PAIR)
        # do not use localhost, because it would complain
        # with error [zmq.error.ZMQError: No such device]
        # self.socket.bind('inproc://uisocket')
        self.socket.bind('tcp://127.0.0.1:{}'.format(port))
        self.stream = ZMQStream(self.socket)
        self.stream.on_recv(self.communicate_with_server)

    async def read_with_websocket(self):
        if self.wsconn_close == True:
            self.wsconn.close()
            self.socket.send_pyobj(dict(
                cmd=GameStatus.ENDED
            ))
            return
        msg_recv = await self.wsconn.read_message()
        self._logger.debug(f'Received from websocket={msg_recv}')
        if msg_recv is None:
            self.wsconn.close()
            self.socket.send_pyobj(dict(
                cmd=GameStatus.ENDED
            ))
        msg = literal_eval(msg_recv)
        self._logger.debug('Received from websocket(Decoded)={}'.format(str(msg)))
        return msg

    async def send_with_websocket(self, msg):
        if msg:
            if isinstance(self.wsconn,
                          websocket.WebSocketClientConnection):
                self._logger.debug('Sending game request')
                # Cannot send a dict(somehow)
                yield self.wsconn.write_message(str(msg))
            else:
                raise RuntimeError("Websocket connection closed")
        else:
            self.wsconn_close = True

    async def wait_for_initial_connection(self):
        self._logger.debug('Polling for connections')
        while True:
            if not self.has_wsconn_initialised:
                msg_recv = await self.read_with_websocket()
            if not self.has_wsconn_initialised:
                self.has_wsconn_initialised = True
                break

    async def init_game_conn(self):
        self._logger.debug('Creating initial game server connection')
        try:
            self.wsconn = await websocket.websocket_connect(self.game_url)
        except Exception as err:
            print("Connection error: {}".format(err))
        else:
            await self.wait_for_initial_connection()

    async def communicate_with_server(self):
        while True:
            msg_recv = self.socket.recv_pyobj()
            if msg_recv.get('cmd') == GameStatus.ENDED:
                self.cleanup()
            elif not self.has_wsconn_initialised:
                await self.init_game_conn()
            else:
                await self.send_with_websocket(msg_recv)
                msg_recv = await self.read_with_websocket()
                self.socket.send_pyobj(msg_recv)

    def cleanup(self):
        self.socket.send_pyobj(dict(
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
        n = Client(port, "ws://localhost:8888/game")
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