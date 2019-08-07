import zmq
import sys
import logging

from serverenums import GameStatus


class CmdUI(object):
    def __init__(self, port):
        self._logger = logging.getLogger(__name__)
        self.ctx = zmq.Context()
        self.socket = self.ctx.socket(zmq.PAIR)
        self.socket.connect('tcp://127.0.0.1:{0}'.format(port))
        self.msg_recv = None

    def get_str_input(self, question):
        while True:
            choice = input(question)
            if any((choice is None, not choice.strip())):
                print('Error: Empty string entered!!!')
                self._logger.error('Error: Empty string entered!!!')
            else:
                return choice

    def get_int_input(self, question):
        while True:
            choice = self.get_str_input(question)
            try:
                choice = int(choice)
                return choice
            except ValueError as err:
                print(err)

    def close_on_panic(self):
        self.socket.send_pyobj(dict(
            cmd=GameStatus.ENDED
        ))
        msg = self.socket.recv_pyobj()
        self._logger.debug(f'Received on exit={str(msg)}')
        self.close_game()

    def close_game(self):
        self.socket.close()
        self.ctx.term()
        sys.exit(0)

    def nonblocking_main(self):
        self._logger.info('CmdUI')
        msg_recv = None
        while True:
            msg_snd = self.get_str_input('Enter a message: ')
            self.socket.send_pyobj(dict(cmd=msg_snd))
            # Try to receive message
            try:
                msg_recv = self.socket.recv_pyobj(flags=zmq.NOBLOCK)
            except zmq.ZMQError as exc:
                if exc.errno == zmq.EAGAIN:
                    pass
                else:
                    raise

            self._logger.info(f'Received {str(msg_recv)}')
            if msg_recv.get('cmd') == GameStatus.ENDED:
                print('Player ended game session')
                self._logger.debug('Player ended game session')
                self.close_game()
