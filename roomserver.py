import logging
from uuid import uuid4
from serverenums import (
    RoomStatus,
    GameStatus
)
from gamemessage import DiscardMsg

class Room(object):
    def __init__(self, room_name, num_of_players, room_id):
        self.room_name = room_name
        self.num_of_players = num_of_players
        self.room_id = room_id
        self.players = []
        self._game_id = None
        self.room_status = RoomStatus.OPEN
        self.game_status = GameStatus.NOT_STARTED

    @property
    def game_id(self):
        return self._game_id

    @game_id.setter
    def game_id(self, value):
        self._game_id = value

    def add_player(self, user_name, user_id):
        self.players.append(dict(
            user_name = user_name,
            user_id = user_id,
            wbsocket = None
        ))

    def is_game_starting(self):
        return self.game_status == GameStatus.IS_STARTING

    def has_game_not_started(self):
        return self.game_status == GameStatus.NOT_STARTED

    def is_full(self):
        return self.room_status == RoomStatus.FULL

    def is_open(self):
        return self.room_status == RoomStatus.OPEN

    def toggle_room_status(self):
        if all([self.is_open(),len(self.players) == self.num_of_players]):
            self.room_status = RoomStatus.FULL
        elif all([self.is_full(),len(self.players) < self.num_of_players]):
            self.room_status = RoomStatus.OPEN

    def leave_room(self, user_id):
        self.players[:] = [player for player in self.players if player.get('user_id') != user_id]

    def update_user(self, user_id, user_name=None, game_conn=None):
        for player in self.players:
            if player.user_id == user_id:
                if user_name:
                    player.user_name = user_name
                if game_conn:
                    player.wbsocket = game_conn
                break

    def can_join(self, user_id):
        self.toggle_room_status()
        player = [player for player in self.players if player.get('user_id') == user_id]
        return not player and self.is_open()    # if can find a player and the room is open

    def get_num_of_players_remaining(self):
        return self.num_of_players - len(self.players)


class RoomServer(object):
    def __init__(self):
        self._logger = logging.getLogger(__name__)
        self.rooms = []
        self.game_socket = None

    def add_room(self, room_name, num_of_players):
        room_id = uuid4().hex
        self.rooms.append(Room(room_name, num_of_players, room_id))
        return room_id

    def add_player(self, room_id, user_id, user_name):
        for room in self.rooms:
            if room.room_id == room_id:
                if room.can_join(user_id):
                    room.add_player(user_name, user_id)
                    self._logger.info('Added player {0} to room {1}'.format(user_name, room_id))
                    return True
                else:
                    return False

    def can_join(self, room_id, user_id):
        for room in self.rooms:
            if room.room_id == room_id:
                return room.can_join(user_id)

    def add_game_conn(self, user_id, room_id, game_conn):
        for room in self.rooms:
            if room.room_id == room_id:
                room.update_user(user_id, user_name=None, game_conn=game_conn)
                self._logger.info('Added websocket conn for player {0}'.format(user_id))
                resp = DiscardMsg(
                    cmd=DiscardMsg.Response.ADDED_NEW_GAME_CONN,
                    prompt='Added websocket conn for player {0}'.format(user_id)
                )
                self.send_reply(user_id, room_id, resp, broadcast=True)
                break

    def send_reply(self, user_id, room_id, msg, broadcast=False):
        for room in self.rooms:
            if room.room_id == room_id:
                if broadcast:
                    for player in room.players:
                        if player.user_id != user_id:
                            player.wbsocket.write_message(DiscardMsg.to_json(msg))
                else:
                    for player in room.players:
                        if player.user_id == user_id:
                            player.wbsocket.write_message(DiscardMsg.to_json(msg))

    def handle_msg(self, msg):
        msg_recv = DiscardMsg.to_obj(msg)
        room_id = msg_recv.get_payload_value('room_id')
        user_id = msg_recv.get_payload_value('user_id')
        if msg_recv.cmd == DiscardMsg.Request.START_GAME:  # it was initially ARE ROOMATES IN GAME
            for room in self.rooms:
                if room.room_id == room_id:
                    if room.is_open():
                        resp = DiscardMsg(
                            cmd=DiscardMsg.Response.START_GAME,
                            prompt='Waiting for {} players to join'.format(str(room.get_num_of_players_remaining()))
                        )
                        self._logger.info('Waiting for {} players to join'.format(str(room.get_num_of_players_remaining())))
                        self.send_reply(user_id, room_id, resp)
                        break
                    elif all([room.is_full(), room.has_game_not_started()]):
                        room.game_status = GameStatus.IS_STARTING
                        players = [item.user_id for item in room.players]
                        self.game_socket.send_pyobj(DiscardMsg(
                            cmd=DiscardMsg.Request.START_GAME,
                            players=players,
                            room_id=room_id
                        ))
                    resp = DiscardMsg(
                        cmd=DiscardMsg.Response.START_GAME,
                        prompt= DiscardMsg.Response.GAME_IS_STARTING
                    )
                    self.send_reply(user_id, room_id, resp)
        elif msg_recv.cmd == DiscardMsg.Request.GAME_REQUEST:
            self.game_socket.send_pyobj(DiscardMsg(
                cmd=msg_recv.get_payload_value('next_cmd'),
                **msg_recv.get_payload_value('data')
            ))
                        
    def get_all_rooms(self):
        return [
            dict(
                room_name=room.room_name,
                room_id=room.room_id,
                num_of_players_remaining=room.get_num_of_players_remaining()
            ) for room in self.rooms
        ]

    def get_all_roomates(self, user_id, room_id):
        roommates = []
        for room in self.rooms:
            if room.room_id == room_id:
                roommates = [dict(user_id=player.user_id, nickname=player.user_name)
                    for player in room.players if player.user_id != user_id]
                break
        return roommates

    def remove_game_conn(self, user_id):
        for room in self.rooms:
            for player in room.players:
                if player.user_id == user_id:
                    room.update_user(user_id, user_name=None, game_conn=None)
                    self._logger.info('{0}\'s connection has been dropped'.format(user_id))
                    break

    def shutdown(self):
        return all([player.get('wbsocket') == None for room in self.rooms for player in room])


