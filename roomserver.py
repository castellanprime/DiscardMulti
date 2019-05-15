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
        self.game_status = RoomStatus.GAME_NOT_STARTED

    def add_player(self, user_name, user_id):
        self.players.append(dict(
            user_name = user_name,
            user_id = user_id,
            wbsocket = None
        ))

    def has_game_not_started(self):
        return self.game_status == RoomStatus.GAME_NOT_STARTED

    def is_full(self):
        return self.room_status == RoomStatus.FULL

    def is_open(self):
        return self.room_status == RoomStatus.OPEN

    def toggle_room_status(self):
        if all([self.is_open() , len(self.players) == self.num_of_players]):
            self.room_status = RoomStatus.FULL
        elif all([self.is_full() , len(self.players) < self.num_of_players]):
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

    def add_game(self, game_id):
        self.game_id = game_id

    def can_join(self, user_id):
        self.toogle_room_status()
        player = [player for player in self.players if player.get('user_id') == user_id]
        return not player[0] and self.is_open()

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
                msg = DiscardMsg(
                    cmd=ClientRcvMsg.HANDSHAKE_REP.value,
                    prompt='Added websocket conn for player {0}'.format(user_id)
                )
                self.send_reply(user_id, room_id, msg)
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
        cmd = RoomRequest[msg.cmd]
        ret = {}
        room_id = msg.get_payload_value('room_id')
        user_id = msg.get_payload_value('user_id')
        prompt = ''
        if cmd == RoomRequest.CAN_GAME_BE_STARTED:
            for room in self.rooms:
                if room.room_id == room_id:
                    if room.is_open():
                        ret = DiscardMsg(
                            cmd=ClientRcvMsg.CAN_GAME_BE_STARTED_REP.value,
                            prompt='Waiting for {} players to join'.format(str(room.get_num_of_players_remaining()))
                        )
                        self.send_reply(user_id, room_id, ret)
                    elif all([room.is_full(), room.has_game_not_started()]):
                        ret = DiscardMsg(
                            cmd=GameServerMsg.START_GAME.value,
                            data=room_id
                        )
                        self.game_socket.send_pyobj(ret)
                        room.game_status = RoomStatus.GAME_HAS_STARTED
                    else:
                        ret = DiscardMsg(
                            cmd=ClientRcvMsg.GAME_MESSAGE_REP.value,
                            prompt=ClientRcvMsg.GAME_HAS_ALREADY_STARTED_REP.value
                        )
                        self.send_reply(user_id, room_id, ret)
        elif cmd == RoomRequest.GAME_MESSAGE:
            ret = DiscardMsg(
                cmd=GameServerMsg[msg.get_payload_value('next_cmd')],
                data=msg.get_payload_value('data')
            )
            self.game_socket.send_pyobj(ret)

                        
    def get_all_rooms(self):
        return [dict(room_name=room.room_name, room_id=room.room_id, num_of_players_remaining=room.get_num_of_players_remaining())
            for room in self.rooms
        ]

    def get_all_roomates(self, user_id, room_id):
        roomates = []
        for room in self.rooms:
            if room.room_id == room_id:
                roomates = [player for player in room.players if player.user_id != user_id]
                break
        return roomates

    def remove_game_conn(self, user_id):
        for room in self.rooms:
            for player in room.players:
                if player.user_id == user_id:
                    room.update_user(user_id, user_name=None, game_conn=None)
                    self._logger.info('{0}\'s connection has been dropped'.format(user_name))
                    break

    def shutdown(self):
        return all([player.get('wbsocket') == None for room in self.rooms for player in room])


