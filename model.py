import pickle, logging, os

state_db_file = 'state.db'

class Model(object):
	def __init__(self):
		self.__logger = logging.getLogger(__name__) 
		self.hand = []
		self.last_played = []
		#self.__set_previous_decks()

	def _findDBfiles(self):
		self.__logger.info("Finding database file")
		for root, dirs, files in os.walk(os.getcwd()):
			for file in files:
				if file.endswith(".db") and file == state_db_file:
					return(os.path.join(root,file))

	def __set_previous_decks(self):
		filename = self._findDBfiles()
		state = self.load(filename)
		if state:
			self.hand = state['hand']
			self.last_played = state['last_played']

	def get_hand(self):
		return self.hand

	def get_last_played(self):
		return self.last_played

	def select_cards(self, card_numbers):
		self.last_played = [self.hand.pop(card_num) 
			for card_num in card_numbers]
		return self.last_played 
	
	def pick_one(self, card):
		self.hand.insert(0, card)

	def add_card(self, card):
		# Adding new card at the bottom of the hand
		self.hand.append(card)

	def add_cards(self, cards):
		self.hand.extend(cards)

	# Deprecated
	# def pick_card(self, index):
	#	self.last_played.append(self.hand.pop(index))
	#	return self.last_played[len(self.last_played) - 1]

	def save(self):
		self.__logger.info('Saving current state!!')
		filename = self._findDBfiles()
		state = {}
		state['hand'] = self.hand
		state['last_played'] = self.last_played
		file = open(filename, 'wb')
		pickle.dump(state, file)
		file.close()

	def load(self, filename):
		self.__logger.info("Loading old state!!")
		state = {}
		if os.path.getsize(filename) > 0:
			file = open(filename, 'rb')		
			try:
				state = pickle.load(file)
			except(EOFError):
				self.__logger.debug("File is empty")
				state = {}
			file.close()
		return state
