"""
	GameServer program
	This holds all the current games
"""

import zmq
from uuid import uuid4
from utils import DiscardMsg
from game import Game
from serverenums import GameServerMsg, RoomGameStatus

ctx = zmq.Context.instance()


class GameServer(object):

    def __init__(self, port):
        self.socket = ctx.socket(zmq.PAIR)
        self.db_socket = ctx.socket()
        self.socket.bind('tcp://127.0.0.1:{}'.format(port))
        self.games = []

    def create_game(self, msg):
        g_id = uuid4().hex
        g = Game(msg.get_payload_value('players'))
        self.games.append(dict(
            game_id = g_id,
            game = g
        ))
        self.socket.send_pyobj(
            DiscardMsg(cmd=RoomGameStatus.GAME_HAS_STARTED,
            data=g.get_player_cards(),
            extra_data=g.get_top_card())
        )

    def _find_game(self, msg):
        return next((index for index, game in self.games if game.g_id == msg.get_payload_value('game_id')), None)

    def set_initial_player(self, msg):
        found_index = self._find_game(msg)
        found = self.games[found_index]
        found.set_initial_player(msg.get_payload_value('player'))
        self.games[found_index] = found
        self.socket.send_pyobj(
            DiscardMsg(cmd=GameServerMsg.INITIAL_PLAYER_SET)
        )

    def get_game_status(self, msg):
        pass

    def play_move(self, msg):
        found_index = self._find_game(msg)
        found = self.games[found_index]
        found.play_move(msg.get_payload_value('player'), msg.get_payload_value('card'))
        self.socket.send_pyobj(
            DiscardMsg(cmd=GameServerMsg.MOVE_PLAYED, data=dict(
                current_player=found.get_current_player(),
                current_deck=found.get_current_deck()
            ))
        )

    def main(self):
        while True:
            msg_recv = self.socket.recv_obj()
            if msg_recv.cmd == GameServerMsg.START_GAME:
                self.create_game(msg_recv)
            elif msg_recv.cmd == GameServerMsg.SET_INITIAL_PLAYER:
                self.set_initial_player(msg_recv)
            elif msg_recv.cmd == GameServerMsg.GET_GAME_STATUS:
                self.get_game_status(msg_recv)
            elif msg_recv.cmd == GameServerMsg.PAUSE_GAME:
                pass
            elif msg_recv.cmd == GameServerMsg.PLAY_MOVE:
                self.play_move(msg_recv)

if __name__ == '__main__':
    c = GameServer(5557)
    c.main()
