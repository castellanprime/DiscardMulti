import logging, pickle

filepath="player.db"

class PlayerModel(object):
    
    def __init__(self):
        self._hand = []
        self.played_moves = []
        self.last_played = []
        self.is_db_loaded = False
        self.room_id = ""
        self._top_card = None
        #self.load(filepath)
    
    def pick_cards(self, card_numbers):
        self.last_played = [self.hand.pop(card_number) for card_number in card_numbers]

    @property
    def hand(self):
        return self._hand
    
    def pick_one(self, card):
        self.hand.insert(0, card)
        
    def add_a_card(self, card):
        self.hand.append(card)

    @property
    def top_card(self):
        return self._top_card

    @top_card.setter
    def top_card(self, card):
        self._top_card = card
        
    def __str__(self):
        return 'Playermodel'
    
    def save(self, filepath):
        #self._logger.info('Saving to database')
        file = open(filepath, 'wb')
        data = {}
        data['hand'] = self.hand
        data['played_moves'] = self.played_moves
        data['last_played'] = self.last_played
        data['room_id'] = self.room_id
        pickle.dump(data, file)
        file.close()
        
    def load(self, filepath):
        if self.is_db_loaded == False:
            obj=None
            try:
                #self._logger.info('Loading database')
                file = open(filepath, 'rb')
                obj=pickle.load(file)
            except(FileNotFoundError):
                #self._logger.debug('File is not found. Create new file')
                obj = {}
            except(EOFError):
                #self._logger.debug("File is empty")
                #self._logger.info('File is initially empty')
                obj = {}
            file.close()
            self.is_db_loaded = True
            if obj:
                self.hand = obj['hand']
                self.last_played = obj['last_played']
                self.played_moves = obj['played_moves']
                self.room_id = obj['room_id']
