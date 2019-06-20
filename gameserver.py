"""
	GameServer program
	This holds all the current games
"""

import zmq, sys
from uuid import uuid4
from gamemessage import DiscardMsg
from gamecontroller import GameController
from serverenums import (
    GameRequest,
    GameStatus
)

class GameServer(object):

    def __init__(self, port):
        self.ctx = zmq.Context()
        self.socket = self.ctx.socket(zmq.PAIR)
        print('port: ', port)
        # self.db_socket = self.ctx.socket(zmq.PAIR)
        self.socket.bind('tcp://127.0.0.1:{0}'.format(port))
        self.games = []

    def create_game(self, msg):
        g_id = uuid4().hex
        g = GameController(msg.get_payload_value('players'))
        self.games.append(dict(
            game_id = g_id,
            game = g,
            game_status = GameStatus.STARTED
        ))
        for player in msg.get_payload_value('players'):
            self.socket.send_pyobj(
                DiscardMsg(
                    cmd=DiscardMsg.Response.START_GAME,
                    prompt=DiscardMsg.Response.GAME_HAS_STARTED,
                    cards=g.get_player_cards_for(player),
                    game_id=g_id,
                    extra_data=g.get_top_card(),
                    room_id=msg.get_payload_value('room_id')
                )
            )

    def _find_game(self, msg):
        return next((index for index, game in self.games if game.g_id == msg.get_payload_value('game_id')), None)

    def set_initial_player(self, msg):
        found_index = self._find_game(msg)
        found = self.games[found_index]
        found.set_initial_player(msg.get_payload_value('user_id'))
        self.games[found_index] = found
        self.socket.send_pyobj(
            DiscardMsg(cmd=DiscardMsg.Response.SET_INITIAL_PLAYER,
                prompt='{0} is now the initial player'.format(msg.get_payload_value('user_name')),
                user_id=msg.get_payload_value('user_id'),
                room_id=msg.get_payload_value('room_id')
            )
        )

    def get_game_status(self, msg):
        found_index = self._find_game(msg)
        found = self.games[found_index]
        current_player = found.get_current_player()
        self.socket.send_pyobj(
            DiscardMsg(cmd=DiscardMsg.Response.GET_GAME_STATUS,
                user_id=current_player,
                delivery=msg.get_payload_value('delivery')
            )
        )

    def play_move(self, msg):
        found_index = self._find_game(msg)
        found = self.games[found_index]
        found.play_move(msg.get_payload_value('player'), msg.get_payload_value('card'))
        self.socket.send_pyobj(
            DiscardMsg(cmd=DiscardMsg.Response.PLAY_MOVE, data=dict(
                current_player=found.get_current_player(),
                current_deck=found.get_current_deck()
            ))
        )

    def close(self):
        self.socket.send_pyobj(
            DiscardMsg(cmd=DiscardMsg.Response.STOP_GAME)
        )
        self.socket.close()
        self.ctx.term()
        sys.exit(0)

    def mainMethod(self):
        while True:
            msg_recv = self.socket.recv_pyobj()
            if msg_recv.cmd == GameRequest.START_GAME:
                self.create_game(msg_recv)
            elif msg_recv.cmd == GameRequest.SET_INITIAL_PLAYER:
                self.set_initial_player(msg_recv)
            elif msg_recv.cmd == GameRequest.GET_GAME_STATUS:
                self.get_game_status(msg_recv)
            elif msg_recv.cmd == GameRequest.PAUSE_GAME:
                pass
            elif msg_recv.cmd == GameRequest.PLAY_MOVE:
                self.play_move(msg_recv)
            elif msg_recv.cmd == GameRequest.STOP_GAME:
                self.close()

if __name__ == '__main__':
    c = GameServer(5557)
    c.mainMethod()
