"""
	The module is for the Player object
"""

from utils import GameMoveType

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
        self.__message = None

    def set_deck(self, cards):
        self.hand = cards

    def set_room_id(self, room_id):
        self.room_id = room_id

    def set_message_to_process(self, msg):
        self.__mesage_to_process = msg 

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
	"""
	    Messages to process
	    cmd: GAME_MESSAGE
	    data:
	        prompt: question asked
	        return_type: GameMoveType.DATATYPE
	        extra_data: It would normally be the top card
		nextCmd: Can be used for validation of options	
	"""
        choice = None
        msg = {}
        if self.__message_to_process:
            prompt = self.__message_to_process.get_payload_value(
                value='prompt')
            print(prompt)
            print(self.__message_to_process.get_payload_value(
                value='extra_data')
            if self.__message_to_process.get_payload_value(
                value='return_type') in [ GameMoveType.DATATYPE_STR.value,
                    GameMoveType.DATATYPE_INT.value]:
                if self.__message_to_process.get_payload_value(
                    value='return_type') == GameMoveType.DATATYPE_STR.value:
                    choice = self._controller.get_str_input(prompt)
                    while choice not in self.__message_to_process.get_payload_value(
                        value='next_cmd'):
                        print('Wrong_option')
                        choice = self._controller.get_str_input(prompt)
                elif self.__message_to_process.get_payload_value(
                    value='return_type') == GameMoveType.DATATYPE_INT.value:
                    choice = self._controller.get_int_input(prompt)
                    while choice not in self.__message_to_process.get_payload_value(
                        value='next_cmd'):
                        print('Wrong option!!')
                        choice = self._controller.get_int_input(prompt)
                msg = DiscardMessage(cmd=RoomGameStatus.GAME_MESSAGE.value,
                    data=choice, return_type=self.__message_to_process.get_payload_value(
                    value='return_type', flag=self.__message_to_process.get_payload_value(
                    value='flag'))
                msg.set_id(self.__message_to_process.get_id())
            elif 
                    
           
            if self.__message_to_process.get_payload_value(
                value='
        if self.__prompt:
            choice = self._controller.get_str_input(self.__prompt)
        else:
            choice = self._controller.get_str_input('Send a message: ')

    
    def __str__(self):
        return 'Player: {}'.format(self.nick)
