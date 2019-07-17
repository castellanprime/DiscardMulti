import logging
import zmq
from zmq.eventloop.zmqstream import ZMQStream
from uuid import uuid4
from serverenums import (
    GameStatus,
    GameRequest,
    MessageDestination
)
from gamemessage import DiscardMsg
from room import Room

class RoomServer(object):
    """
    Roomserver class
    """
    def __init__(self):
        self._logger = logging.getLogger(__name__)
        self.rooms = []
        self.context = zmq.Context.instance()
        self.game_socket = self.context.socket(zmq.PAIR)
        self.game_socket.connect('inproc://gameserversocket')
        self.stream_sock = ZMQStream(self.game_socket)
        self.stream_sock.on_recv(self.send_reply_from_gameserver)

    def add_room(self, num_of_players, room_name):
        room_id = uuid4().hex
        self.rooms.append(Room(room_name, num_of_players, room_id))
        return room_id

    def add_player(self, room_id, user_id, user_name):
        for room in self.rooms:
            if room.room_id == room_id:
                if room.can_join(user_id):
                    room.add_player(user_name, user_id)
                    self._logger.debug('Added player {0} to room {1}'.format(user_name, room_id))
                    print('Added player {0} to room {1}'.format(user_name, room_id))
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
                for player in room.players:
                    if player.get('user_id') == user_id:
                        room.update_user(user_id, user_name=player.get('user_name'), game_conn=game_conn)
                        self._logger.debug('Added websocket conn for player {0}'.format(user_id))
                        resp = DiscardMsg(
                            cmd=DiscardMsg.Response.ADDED_NEW_GAME_CONN,
                            prompt='Added websocket conn for player {0}'.format(user_id)
                        )
                        self.send_reply_from_roomserver(user_id, room_id, resp, broadcast=True)
                        return

    def send_reply_from_roomserver(self, user_id, room_id, msg, broadcast=False):
        for room in self.rooms:
            if room.room_id == room_id:
                if not broadcast:
                    for player in room.players:
                        if player.get('user_id') == user_id:
                            wbsocket = player.get('wbsocket')
                            wbsocket.write_message(DiscardMsg.to_json(msg))
                            break
                else:
                    for player in room.players:
                        wbsocket = player.get('wbsocket')
                        wbsocket.write_message(DiscardMsg.to_json(msg))

    def send_reply_from_gameserver(self, msgs):
        msg_recv = DiscardMsg.to_obj(msgs[0].decode()) # because you receive the msg as a bytes list
        self._logger.debug(f' Received msg from gameserver(Decoded): {str(msg_recv)}')
        room_id = msg_recv.get_payload_value('room_id')
        if msg_recv.get_payload_value('cmd') != DiscardMsg.Response.STOP_GAME:
            for room in self.rooms:
                if room.room_id == room_id:
                    if msg_recv.get_payload_value('delivery') == MessageDestination.UNICAST:
                        player = [player for player in room.players
                            if player.get('user_id') == msg_recv.get_payload_value('user_id')][0]
                        wbsocket = player.get('wbsocket')
                        wbsocket.write_message(DiscardMsg.to_json(msg_recv))
                        print(f"Published a GAME response to player: {player.get('user_id')}")
                        self._logger.debug(f"Published a GAME response to player: {player.get('user_id')}")
                    else:
                        for player in room.players:
                            wbsocket = player.get('wbsocket')
                            wbsocket.write_message(DiscardMsg.to_json(msg_recv))
                        print('Published GAME responses to all players')
                        self._logger.debug('Published GAME responses to all players')

    def handle_msg(self, msg):
        msg_recv = DiscardMsg.to_obj(msg)
        self._logger.debug('Received message from client: {0}'.format(str(msg_recv)))
        room_id = msg_recv.get_payload_value('room_id')
        user_id = msg_recv.get_payload_value('user_id')
        if msg_recv.cmd == DiscardMsg.Request.START_GAME:  # it was initially ARE ROOMATES IN GAME
            for room in self.rooms:
                if room.room_id == room_id:
                    self._logger.debug('Room: {0}'.format(str(room)))
                    if room.is_open():
                        resp = DiscardMsg(
                            cmd=DiscardMsg.Response.START_GAME,
                            prompt='Waiting for {} players to join'.format(str(room.get_num_of_players_remaining()))
                        )
                        self._logger.debug(
                            'Waiting for {} players to join'.format(str(room.get_num_of_players_remaining()))
                        )
                        self.send_reply_from_roomserver(user_id, room_id, resp)
                        break
                    elif all([room.is_full(), room.has_game_not_started()]):
                        room.game_status = GameStatus.IS_STARTING
                        players = [item.get('user_id') for item in room.players]
                        self.game_socket.send_pyobj(DiscardMsg(
                            cmd=GameRequest.START_GAME,
                            players=players,
                            room_id=room_id,
                            delivery=MessageDestination.UNICAST
                        ))
                    resp = DiscardMsg(
                        cmd=DiscardMsg.Response.START_GAME,
                        prompt=DiscardMsg.Response.GAME_IS_STARTING
                    )
                    self.send_reply_from_roomserver(user_id, room_id, resp)
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
                roommates = [dict(user_id=player.get('user_id'), nickname=player.get('user_name'))
                    for player in room.players if player.get('user_id') != user_id]
                break
        return roommates

    def remove_game_conn(self, user_id):
        for room in self.rooms:
            for player in room.players:
                if player.get('user_id') == user_id:
                    username = player.get('user_name')
                    room.update_user(user_id, None, None)
                    print('{0}\'s connection has been dropped'.format(username))
                    self._logger.debug('{0}\'s connection has been dropped'.format(username))
                    break

    def shutdown(self):
        return all([player.get('wbsocket') is None for room in self.rooms for player in room.players])
