from tornado import (
    web, options, httpserver,
    ioloop, websocket, log, escape
)
import logging, sys, asyncio
from serverenums import GameStatus

def enable_server_logging():
    options.options['log_file_prefix'] = 'mainserver.log'
    options.parse_command_line()

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(logging.INFO)
    stream_handler.setFormatter(logging.Formatter(logging.BASIC_FORMAT))
    root_logger.addHandler(stream_handler)

class WSHandler(websocket.WebSocketHandler):
    clients = set()

    def check_origin(self, origin):
        return True

    def open(self):
        self.clients.add(self)
        print(f'Websocket opened. ClientID = {str(self)}')

    def on_message(self, message):
        [client.write_message(message) for client in self.clients]

    def on_pong(self, data):
        # Refer to https://github.com/tornadoweb/tornado/issues/2532, and https://github.com/tornadoweb/tornado/issues/2021
        # since the on_message handler is priority, the on_pong handler is made asynchronous
        # so that the pong does not block and close connection
        asyncio.ensure_future(self.on_pong_async(data))

    async def on_pong_async(self, data):
        print(f'Websocket ping from client')
        await self.write_message(dict(cmd='GameStatus.HAS_ALREADY_STARTED', msg='Server sent pong'))

    def on_close(self):
        self.clients.remove(self)
        print(f'Closing websocket connection for {str(self)}')

def maks_app():
    return web.Application([
        (r"/wshandler", WSHandler)
    ], websocket_ping_interval=10)

if __name__ == "__main__":
    enable_server_logging()
    try:
        app = maks_app()
        app.listen(8888)
        ioloop.IOLoop.current().start()
    except (SystemExit, KeyboardInterrupt):
        ioloop.IOLoop.current().stop()
        print('Stopped server')