import logging
from uuid import uuid4
from serverenums import RoomStatus

class Room(object):
    def __init__(self, room_name, num_of_players, room_id):
        self.room_name = room_name
        self.num_of_players = num_of_players
        self.room_id = room_id
        self.players = []
        self.room_status = RoomStatus.OPEN
        self.game_id = None

    def add_player(self, user_name, user_id):
        self.players.append(dict(
            user_name = user_name,
            user_id = user_id,
            wbsocket = None
        ))

    def is_full(self):
        return self.room_status == RoomStatus.FULL

    def is_open(self):
        return self.room_status == RoomStatus.OPEN

    def toggle_game_status(self):
        if all([self.is_open() , len(self.players) == self.num_of_players]):
            self.room_status = RoomStatus.FULL
        elif all([self.is_full() , len(self.players) < self.num_of_players]):
            self.room_status = RoomStatus.OPEN

    def leave_room(self, user_id):
        self.players[:] = [player for player in self.players if player.user_id != user_id]

    def update_user(self, user_id, user_name=None, game_conn=None):
        for player in self.players:
            if player.user_id == user_id:
                if user_name:
                    player.user_name = user_name
                if game_conn:
                    player.wbsocket = game_conn
                break

    def add_game(self, game_id):
        self.game_id = game_id

    def can_join(self):
        self.toogle_game_status()
        return self.is_open()

    def get_num_of_players_remaining(self):
        return self.num_of_game_players - len(self.players)


class RoomServer(object):
    def __init__(self):
        self._logger = logging.getLogger(__name__)
        self.rooms = []
        self.game_socket = None

    def add_room(self, room_name, num_of_players):
        room_id = uuid4().hex
        room = Room(room_name, num_of_players, room_id)
        self.rooms.append(room)
        return room_id

    def add_player(self, room_id, user_id, user_name):
        for room in self.rooms:
            if room.get_room_id() == room_id:
                room.add_player(user_name, user_id)
                self._logger.info('Added player {0} to room {1}'.format(user_name, room_id))
                break

    def add_game_conn(self, room_id, user_id, game_conn):
        for room in self.rooms:
            if room.get_room_id() == room_id:
                room.update_user(user_id, user_name=None, game_conn=game_conn)
                self._logger.info('Added websocket conn for player {0}'.format(user_id))
                self.send_reply(user_id, 'Added websocket conn for player {0}'.format(user_id))
                break

    def send_reply(self, user_id, msg, broadcast=False):
        pass

