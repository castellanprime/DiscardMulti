from serverenums import (
    RoomStatus,
    GameStatus
)


class Room(object):
    """
    Room class
    """
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
            user_name=user_name,
            user_id=user_id,
            wbsocket=None
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
        if all([self.is_open(), len(self.players) == self.num_of_players]):
            self.room_status = RoomStatus.FULL
        elif all([self.is_full(), len(self.players) < self.num_of_players]):
            self.room_status = RoomStatus.OPEN

    def leave_room(self, user_id):
        self.players[:] = [player for player in self.players if player.get('user_id') != user_id]

    def update_user(self, user_id, user_name=None, game_conn=None):
        for player in self.players:
            if player.get('user_id') == user_id:
                if user_name:
                    player['user_name'] = user_name
                if game_conn:
                    player['wbsocket'] = game_conn
                    self.toggle_room_status()
                break

    def can_join(self, user_id):
        self.toggle_room_status()
        player = [player for player in self.players if player.get('user_id') == user_id]
        return not player and self.is_open()    # if can find a player and the room is open

    def get_num_of_players_remaining(self):
        return self.num_of_players - len(self.players)

    def __str__(self):
        return f'Room name: {self.room_name}' \
            + f', Room id: {self.room_id}' \
            + f', Room status: {self.room_status}' \
            + f', Game status: {self.game_status}'