"""
	The module is for the Player object
"""

from serverenums import GameMoveType

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
    def __init__(self, user_id, controller, model, nick):
        super().__init__(user_id)
        self.model = model
        self.last_card = False
        self.room_id = None
        self.nick = nick
        self._controller = controller
        self.__message_to_process = None

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

    def __get_pick_option(self, prompt):
        choice = None
        if (self.__message_to_process.get_payload(value='return_type')
            == GameMoveType.DATATYPE_STR.value):
            choice = self._controller.get_str_input(prompt)
            while ( choice not in self.__message_to_process.get_paylaod_value(
                value='extra_data')):
                print('Wrong option')
                choice = self._controller.get_str_input(prompt)
        elif (self._message_to_process.get_payload_value(
            value='return_type') == GameMoveType.DATATYPE_INT.value):
            choice = self._controller.get_int_input(prompt)
            while ( choice not in self.__message_to_process.get_payload_value(
                value='extra_data')):
                print('Wrong option')
                choice = self._controller.get_int_input(prompt)
        return DiscardMessage(
            cmd=RoomGameStatus.GAME_MESSAGE.value,
            data=choice,
            return_type=self.__message.get_payload_value(value='return_type'),
            flag=self.__message_to_process.get_payload_value(value='flag'),
            msg_id=self.__message_to_process.msg_id
        )

    def __punish(self, prompt):
        print(prompt)
        if ( self.__message.get_payload_value(value='next_cmd')
          == GameMoveType.PICK_ONE.value):
            self.model.pick_one(
              self.__message_to_process.get_payload_value('extra_data'))
        elif ( self.__message.get_payload_value(value='next_cmd')
          == GameMoveType.PICK_TWO.value):
            for card in self.__message_to_process.get_payload_value('extra-data'):
                self.model.pick_one(card) 
           

    def play(self):
        choice = None
        msg_ = {}
        if self.__message_to_process:
            prompt = self.__message_to_process.get_payload_value(
                value='prompt')
            print(self.__message_to_process.get_payload_value(
                value='data'))
            if all((self.__message_to_process.get_payload_value(
                value='return_type') in [ GameMoveType.DATATYPE_STR.value,
                    GameMoveType.DATATYPE_INT.value],
                self.__message_to_process.get_payload_value(
                    value='next_cmd') == GameMoveType.PICK_OPTION.value)):
                msg_ = self.__get_pick_option(prompt)
            elif all((self.__message_to_process.get_payload_value(
                value='return_type') == GameMoveType.DATATYPE_LIST.value,
                self.__message_to_process.get_payload_value(
                 value='next_cmd') == GameMoveType.PICK_CARDS.value )):
                print('My hand: ')
                print('\n'.join([ str(ind) + ') ' + value 
                  for ind, value in enumerate(self.model.get_hand())]))
                choice = self._controller.get_int_input(prompt)
                cards = self.model.select_cards([choice])
                msg_ = DiscardMessage(
                    cmd=RoomGameStatus.GAME_MESSAGE.value,
                    data=cards,
                    flag=self.__message_to_process.get_payload_value(value='flag'),
                    msg_id=self.__message_to_process.msg_id
                )
            elif ( self.__message_to_process.get_payload_value(
                   value='next_cmd') in [ GameMoveType.PICK_ONE.value, 
                     GameMoveType.PICK_TWO.value ]):
                   # it is a punishment or an error   
                self.__punish(prompt)
                return msg
        print("Do nothing")

    
    def __str__(self):
        return 'Player: {}'.format(self.nick)
