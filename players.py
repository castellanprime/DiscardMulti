"""
	The module is for the Player object
"""

from serverenums import (
    GameMoveType,
    RoomRequest,
    GameRequest
)
class Player(object):
    def __init__(self, user_id, model):
        self._user_id = user_id
        self._game_id = None
        self._last_card = False
        self._room_id = None
        self._nickname = None
        self.model = model

    @property
    def room_id(self):
        return self._room_id

    @room_id.setter
    def room_id(self, value):
        self._room_id = value

    @property
    def game_id(self):
        return self._game_id

    @game_id.setter
    def game_id(self, value):
        self._game_id = value

    @property
    def user_id(self):
        return self._user_id

    @property
    def nickname(self):
        return self._nickname

    @nickname.setter
    def nickname(self, nickname):
        self._nickname = nickname

    @property
    def last_card(self):
        return self._last_card

    @last_card.setter
    def last_card(self, value):
        self._last_card = value

    @property
    def top_card(self):
        return self.model.top_card

    @top_card.setter
    def top_card(self, card):
        self.model.top_card = card

    def set_deck(self, cards):
        for card in cards:
            self.model.add_a_card(card)

    def has_played_last_card(self):
        return len(self.model.get_hand()) == 0

    def has_last_card(self):
        return len(self.model.get_hand()) == 1

    def play(self, message):
        raise NotImplementedError('users must define play to use this base class')

    def __str__(self):
        return f'<Username={self.nickname}, userid={self.user_id}, roomid={self.room_id}>'

class Computer(Player):
    def __init__(self, user_id, model):
        super().__init__(user_id, model)

    def easy_random(self):
        """
                The computer
        """
        pass

    def play(self, message):
        pass

class Human(Player):
    def __init__(self, user_id, controller, model):
        super().__init__(user_id, model)
        self._controller = controller
        self.__message_to_process = None

    @property
    def controller(self):
        return self._controller

    def set_message_to_process(self, msg):
        self.__message_to_process = msg

    def __get_prompt(self, prompt):
        return prompt

    # def __get_pick_option(self, prompt):
    #     choice = None
    #     if (self.__message_to_process.get_payload('return_type')
    #         == GameMoveType.DATATYPE_STR.value):
    #         choice = self._controller.validate_user_entry(
    #             input_func_cb=self._controller.get_str_input,
    #             input_question_cb=self.__get_prompt(prompt),
    #             validation_params=self.__message_to_process.get_payload_value('extra_data')
    #         )
    #     elif (self.__message_to_process.get_payload_value('return_type')
    #         == GameMoveType.DATATYPE_INT.value):
    #         choice = self._controller.validate_user_entry(
    #             input_func_cb=self._controller.get_int_input,
    #             input_question_cb=self.__get_prompt(prompt),
    #             validation_params=self.__message_to_process.get_payload_value('extra_data')
    #         )
    #     return {
    #         'cmd': RoomGameStatus.GAME_MESSAGE.value,
    #         'data': choice,
    #         'room_id': self.get_room_id(),
    #         'user_id': self.get_user_id(),
    #         'return_type': self.__message_to_process.get_payload_value('return_type'),
    #         'flag':self.__message_to_process.get_payload_value('flag'),
    #         'msg_id':self.__message_to_process.msg_id
    #     }

    def __punish(self, prompt):
        print(prompt)
        if ( self.__message_to_process.get_payload_value('next_cmd')
          == GameMoveType.PICK_ONE.value):
            self.model.pick_one(
              self.__message_to_process.get_payload_value('extra_data'))
        elif ( self.__message_to_process.get_payload_value('next_cmd')
          == GameMoveType.PICK_TWO.value):
            for card in self.__message_to_process.get_payload_value('extra-data'):
                self.model.pick_one(card) 
           

    def turn(self, msg):
        # Play a turn
        pass


    def play(self):
        return dict(
            cmd=RoomRequest.GAME_REQUEST,
            next_cmd=GameRequest.GET_GAME_STATUS,
            room_id=self.room_id,
            user_id=self.user_id,
            game_id=self.game_id
        )

    # def play(self):
    #     choice = None
    #     msg_ = {}
    #     if self.__message_to_process:
    #         prompt = self.__message_to_process.get_payload_value('prompt')
    #         print(self.__message_to_process.get_payload_value('data'))
    #         if all((self.__message_to_process.get_payload_value('return_type')
    #             in [ GameMoveType.DATATYPE_STR.value, GameMoveType.DATATYPE_INT.value],
    #             self.__message_to_process.get_payload_value('next_cmd')
    #             == GameMoveType.PICK_OPTION.value)):
    #                 msg_ = self.__get_pick_option(prompt)
    #         elif all((self.__message_to_process.get_payload_value('return_type')
    #             == GameMoveType.DATATYPE_CARDS.value,
    #             self.__message_to_process.get_payload_value('next_cmd')
    #             == GameMoveType.PICK_CARDS.value )):
    #                 print('My hand: ')
    #                 print('\n'.join([ str(ind) + ') ' + value
    #                     for ind, value in enumerate(self.model.get_hand())]))
    #                 choice = self._controller.get_int_input(prompt)
    #                 cards = self.model.select_cards([choice])
    #                 msg_ = {
    #                     'cmd':RoomGameStatus.GAME_MESSAGE.value,
    #                     'data': cards,
    #                     'room_id': self.get_room_id(),
    #                     'user_id':self.get_user_id(),
    #                     'flag': self.__message_to_process.get_payload_value(value='flag'),
    #                     'msg_id': self.__message_to_process.msg_id
    #                 }
    #         elif ( self.__message_to_process.get_payload_value('next_cmd')
    #             in [ GameMoveType.PICK_ONE.value, GameMoveType.PICK_TWO.value ]):
    #                # it is a punishment or an error
    #                 self.__punish(prompt)
    #         else:
    #             msg_ = {
    #                 'cmd': RoomGameStatus.GAME_MESSAGE.value,
    #                 'data':'[Test] I sent a game move',
    #                 'room_id':self.room_id,
    #                 'user_id':self.user_id
    #             }
    #         return msg_
    #     else:
    #         print("Do nothing")
    
    def __str__(self):
        return 'Player: {}'.format(self.nick)
