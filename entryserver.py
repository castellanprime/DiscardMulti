from tornado import (
    web, options, httpserver,
    ioloop, websocket, log, escape
)

class WSHandler(websocket.WebSocketHandler):
    clients = set()

    def check_origin(self, origin):
        return True

    def open(self):
        self.clients.add(self)
        print(f'Websocket opened. ClientID = {self}')

    def on_message(self, message):
        [client.write_message(message) for client in self.clients]

    def on_pong(self, data):
        print(f'Websocket ping from client = {str(data.decode())}')
        self.write_message('Server sent pong')

    def on_close(self):
        self.clients.remove(self)

def maks_app():
    return web.Application([
        (r"/ws", WSHandler)
    ], websocket_ping_interval=10)

if __name__ == "__main__":
    try:
        app = maks_app()
        app.listen(8888)
        ioloop.IOLoop.current().start()
    except (SystemExit, KeyboardInterrupt):
        ioloop.IOLoop.current().stop()
        print('Stopped server')