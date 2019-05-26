"""
	GameServer program
	This holds all the current games
"""

import zmq, sys
from uuid import uuid4
from utils import DiscardMsg
from gamecontroller import GameController
from serverenums import (
    GameRequest,
    ClientResponse,
    GameStatus
)

class GameServer(object):

    def __init__(self, port):
        self.ctx = zmq.Context()
        self.socket = self.ctx.socket(zmq.PAIR)
        self.db_socket = self.ctx.socket(zmq.PAIR)
        self.socket.bind('tcp://127.0.0.1:{}'.format(port))
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
                    cmd=ClientResponse.GAME_HAS_STARTED_REP,
                    data=dict(
                        cards=g.get_player_cards_for(player),
                        game_id=g_id
                    ),
                    extra_data=g.get_top_card(),
                    room_id=msg.get_payload_value('room_id')
                )
            )

    def _find_game(self, msg):
        return next((index for index, game in self.games if game.g_id == msg.get_payload_value('game_id')), None)

    def set_initial_player(self, msg):
        found_index = self._find_game(msg)
        found = self.games[found_index]
        found.set_initial_player(msg.get_payload_value('player'))
        self.games[found_index] = found
        self.socket.send_pyobj(
            DiscardMsg(cmd=ClientResponse.SET_INITIAL_PLAYER_REP, 
                data=msg.get_payload_value('player'),
                room_id=msg.get_payload_value('room_id')
            )
        )

    def get_game_status(self, msg):
        pass

    def play_move(self, msg):
        found_index = self._find_game(msg)
        found = self.games[found_index]
        found.play_move(msg.get_payload_value('player'), msg.get_payload_value('card'))
        self.socket.send_pyobj(
            DiscardMsg(cmd=ClientResponse.PLAY_MOVE_REP, data=dict(
                current_player=found.get_current_player(),
                current_deck=found.get_current_deck()
            ))
        )

    def close(self):
        self.socket.close()
        self.ctx.term()
        sys.exit(0)

    def main(self):
        while True:
            msg_recv = self.socket.recv_obj()
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
    c.main()
