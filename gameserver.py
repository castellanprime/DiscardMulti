"""
	GameServer program
	This holds all the current games
"""

import zmq, sys, logging
from uuid import uuid4
from gamemessage import DiscardMsg
from gamecontroller import GameController
from serverenums import (
    GameRequest,
    GameStatus
)

def get_random_port():
    import socket
    s = socket.socket()
    s.bind(("", 0))
    port = s.getsockname()[1]
    s.close()
    return port


class GameServer(object):

    def __init__(self):
        self._logger = logging.getLogger(__name__)
        self.ctx = zmq.Context.instance()
        self.socket = self.ctx.socket(zmq.PAIR)
        # self.db_socket = self.ctx.socket(zmq.PAIR)
        # self.socket.bind('tcp://127.0.0.1:{0}'.format(port))
        self.socket.bind('inproc://gameserversocket')
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
            self.socket.send_string(
                DiscardMsg.to_json(
                    DiscardMsg(
                        cmd=DiscardMsg.Response.START_GAME,
                        prompt=DiscardMsg.Response.GAME_HAS_STARTED,
                        cards=g.get_player_cards_for(player),
                        user_id=player,
                        game_id=g_id,
                        extra_data=g.get_top_card(),
                        room_id=msg.get_payload_value('room_id'),
                        delivery=msg.get_payload_value('delivery')
                    )
                )
            )

    def find_game(self, msg):
        index = next((index for index, game in enumerate(self.games) if game.get('game_id') == msg.get_payload_value('game_id')), None)
        self._logger.debug(f'Game index : {index}')
        game_server_obj = self.games[index]
        game = game_server_obj.get('game')
        return game_server_obj, game, index

    def set_initial_player(self, msg):
        game_server_obj, game, index = self.find_game(msg)
        cur_player = game.set_initial_player(msg.get_payload_value('user_id'))
        game_server_obj['game'] = game
        self.games[index] = game_server_obj
        if cur_player is None:
            self.socket.send_string(
                DiscardMsg.to_json(
                    DiscardMsg(cmd=DiscardMsg.Response.SET_INITIAL_PLAYER,
                        prompt='{0} is now the initial player'.format(msg.get_payload_value('user_name')),
                        user_id=msg.get_payload_value('user_id'),
                        room_id=msg.get_payload_value('room_id'),
                        delivery=msg.get_payload_value('delivery')
                    )
                )
            )
            print('{0} is now the initial player'.format(msg.get_payload_value('user_name')))
        else:
            self.socket.send_string(
                DiscardMsg.to_json(
                    DiscardMsg(cmd=DiscardMsg.Response.SET_INITIAL_PLAYER,
                        prompt='{0} is already the initial player'.format(cur_player),
                        user_id=cur_player,
                        room_id=msg.get_payload_value('room_id'),
                        delivery=msg.get_payload_value('delivery')
                    )
                )
            )
            print('{0} is already the initial player'.format(cur_player))
        self._logger.debug(f'Sent back a game message for setting the initial player')

    def get_game_status(self, msg):
        game_server_obj, game, _ = self.find_game(msg)
        current_player = game.get_current_player()
        self.socket.send_string(
            DiscardMsg.to_json(
                DiscardMsg(cmd=DiscardMsg.Response.GET_GAME_STATUS,
                    user_id=current_player,
                    game_status=game_server_obj.get('game_status'),
                    room_id=msg.get_payload_value('room_id'),
                    delivery=msg.get_payload_value('delivery')
                )
            )
        )
        self._logger.debug(f'Sent back a game message for getting the game status')

    def play_move(self, msg):
        game_server_obj, game, index = self.find_game(msg)
        game.play_move(msg.get_payload_value('player'), msg.get_payload_value('card'))
        game_server_obj['game'] = game
        self.games[index] = game_server_obj
        self.socket.send_pyobj(
            DiscardMsg.to_json(
                DiscardMsg(cmd=DiscardMsg.Response.PLAY_MOVE,
                    current_player=game.get_current_player(),
                    room_id=msg.get_payload_value('room_id'),
                    current_deck=game.get_current_deck()
                )
            )
        )
        self._logger.debug(f'Sent back a game message for playing a move')

    def close(self):
        self.socket.send_string(
            DiscardMsg.to_json(
                DiscardMsg(cmd=DiscardMsg.Response.STOP_GAME)
            )
        )
        self.socket.close()
        self.ctx.term()
        self._logger.debug(f'Closing game server')
        sys.exit(0)

    def mainMethod(self):
        self._logger.debug('Started Game Server')
        while True:
            msg_recv = self.socket.recv_pyobj()
            self._logger.debug('Message received by Gameserver: {0}'.format(str(msg_recv)))
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
    port = get_random_port()
    c = GameServer(port)
    c.mainMethod()
