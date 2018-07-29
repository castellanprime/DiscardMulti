"""
	The module is for the Player object
"""

class Player(object):
    def __init__(self, user_id):
        self.user_id = user_id

    """
    This will go to the controller
    def join(self, game):
            self.__game = game
    """
    def get_user_id(self):
        return self.user_id

    def play(self, message):
        raise NotImplementedError('users must define play to use this base class')

class Computer(Player):
    def __init__(self, user_id, model):
        super().__init__(user_id)
        self.model = model

    def easy_random(self):
        """
                The computer
        """
        pass

    def play(self, message):
        pass

class Human(Player):
    def __init__(self, user_id, controller, model):
        super().__init__(user_id)
        self.model = model
        self.last_card = False
        self.room_id = None
        self._controller = controller
        self.__prompt = prompt

    def set_deck(self, cards):
        self.hand = cards

    def set_room_id(self, room_id):
        self.room_id = room_id

    def get_room_id(self):
        return self.room_id
        
    def has_played_last_card(self):
        return len(self.model.get_hand()) == 0
    
    def has_last_card(self):
        return len(self.model.get_hand()) == 1
    
    def get_controller(self):
        return self._controller

    def set_nickname(self, nick):
        self.nick = nick

    def get_nickname(self):
        return self.nick

    def play(self):
        choice = None
        if self.__prompt:
            choice = self._controller.get_str_input(self.__prompt)
        else:
            choice = self._controller.get_str_input('Send a message: ')

    
    def __str__(self):
        return 'Player: {}'.format(self.nick)