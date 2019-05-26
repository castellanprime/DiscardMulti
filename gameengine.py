"""
	This module contains the game logic/rules
	for Discard
"""
import logging
from common.cards import NormalCard, SpecialCard
from common.playstates import BeginPlayState, PickCardsState, QuestionCardState, \
		DropCardState, SkipCardState, QuestionCardandSkipState, NormalCardState, \
		 PunishWrongMatchesState, BlockState, LastCardState
from common.enums import PlayerState, SpecialCardName

class DiscardGame(object):

	def __init__(self, controller):
		self._controller = controller
		self._logger = logging.getLogger(__name__)
		self.state, self.playing = None, None
		self.played_cards = None
		self.num_of_pick_cards = 0
		self.num_of_cards_to_discard = 0
		self.is_there_a_winner = False			# If there is a winner
		
	""" Checks """
	def is_card_a_normalcard(self, card):
		return isinstance(card, NormalCard)

	def is_card_a_specialcard(self, card):
		return isinstance(card, SpecialCard)

	def is_card_a_pickone(self, card):
		if self.is_card_a_specialcard(card):
			return card.char == SpecialCardName['PICKONE'].value

	def is_card_a_picktwo(self, card):
		if self.is_card_a_specialcard(card):
			return card.char == SpecialCardName['PICKTWO'].value

	def is_card_a_question(self, card):
		if self.is_card_a_specialcard(card):
			return card.char == SpecialCardName['QUESTION'].value

	def is_card_a_skip(self, card):
		if self.is_card_a_specialcard(card):
			return card.char == SpecialCardName['SKIP'].value	
		
	def is_card_a_drop(self, card):
		if self.is_card_a_specialcard(card):
			return card.char == SpecialCardName['DROP'].value	

	def has_picked_cards(self):
		return self.num_of_pick_cards == 0

	def add_to_pick_cards(self):
		if self.num_of_pick_cards < 0:
			self.num_of_pick_cards = 0
		self.num_of_pick_cards = self.num_of_pick_cards + 1
		self._logger.info("Added a pick card")

	def add_to_discard_cards(self):
		self.num_of_cards_to_discard = self.num_of_cards_to_discard + 1
		self._logger.info("Added a discard card")	

	def has_someone_won(self):
		return self.is_there_a_winner == True

	def do_cards_match(self, card_one, card_two):
		self._logger.info("Do cards match")
		""" Checks if the card matches either
		(a)	Shape or Colour in the case of a normal card
		(b) Char or colour in the case of a special card
		"""
		sstr = "Card_one: " + str(card_one) +  "\nCard_two: " + str(card_two) 
		self._logger.debug(sstr)
		if self.is_card_a_normalcard(card_one) and self.is_card_a_normalcard(card_two):
			return any((card_one.get_shape() == card_two.get_shape(),
						card_one.get_shape_colour() == card_two.get_shape_colour()))
		elif self.is_card_a_specialcard(card_one) and self.is_card_a_normalcard(card_two):
			return card_one.get_char_colour() == card_two.get_shape_colour()
		elif self.is_card_a_normalcard(card_one) and self.is_card_a_specialcard(card_two):
			return card_one.get_shape_colour() == card_two.get_char_colour()
		elif self.is_card_a_specialcard(card_one) and self.is_card_a_specialcard(card_two):
			return any((card_one.get_char() == card_two.get_char(),
						card_one.get_char_colour() == card_two.get_char_colour()))

	def normal_play(self):
		# Normal play
		self._controller.display_cards(self._controller.current_player)				
		pick_choice = self._controller.ask_to_pick(True)

		if pick_choice.lower() == "pick":
			self.evaluate_pick_card_choice()
		elif pick_choice.lower() == "lastcard":
			can_play_last_card = self._controller.check_if_last_card()
			if can_play_last_card:
				self._controller.display_last_card_rules()
				self.state = LastCardState()
				st = "State to Consider = " + str(self.state)
				self._logger.debug(st)
				self.evaluate_pick_card_choice()
			else:
				pick_choice = self._controller.ask_to_pick()
				if pick_choice.lower() == "pick":
					self.state = BeginPlayState()
					st = "State to Consider = " + str(self.state)
					self._logger.debug(st)
					self.evaluate_pick_card_choice()
				else:
					self.evaluate_skip_card_choice()
		else:
			# If the player wants to skip his/her turn
			self.evaluate_skip_card_choice()

	def end_played_pick_card(self):
		# For current player that has not played a pick one or pick two card
		self._controller.display_cards(self._controller.current_player)
		choice = input(self._controller.views[0].prompts(6))	# Do he/she want to block
		if choice == 'n':
			self.state = PickCardsState()
			st = "State to Consider = " + str(self.state)
			self._logger.debug(st)
			self.state = self.state.evaluate(self, None)
			self._logger.debug(str(self.state))
		else:
			#self._controller.display_cards(self._controller.current_player)
			self.played_cards = self._controller.player_pick_a_card(self._controller.current_player)[0]	# Pick the blocking card
			self.state = BlockState()
			st = "State to Consider = " + str(self.state)
			self._logger.debug(st)
			self.state = self.state.evaluate(self, self.played_cards)

	def start_played_pick_card(self):
		# For current player that has just played a pick one or pick two card
		choice = input(self._controller.views[0].prompts(7))	# begin combo
		self.update(self.played_cards)
		if choice == 'y':
			self._logger.debug("Adding more pick cards")
			self.add_to_pick_cards()
			self.update_state(self.state)
			self._controller.display_cards(self._controller.current_player)
			self.played_cards = self._controller.player_pick_a_card(self._controller.current_player)[0]  # Allows you to pick another card
			self.state = self.state.evaluate(self, self.played_cards)
		elif choice == 'n':
			# if player only has one pick card
			self._logger.debug("Only one pick card!!")
			self.state = self.state.evaluate(self, None)
			self.add_to_pick_cards()

	def start_special_states(self):
		choice = input(self._controller.views[0].prompts(7))
		self.update(self.played_cards)    # This drops the @drop_card on the pile
		if (isinstance(self.state, DropCardState)):
			self.add_to_discard_cards()
		if choice == 'y':
			self._logger.debug("Combining cards")
			self._controller.display_cards(self._controller.current_player)
			self.played_cards = self._controller.player_pick_a_card(self._controller.current_player)[0] # Allows you to pick another card
			self.state = self.state.evaluate(self, self.played_cards)
		elif choice == 'n':
			self._logger.debug("Solitary cards")
			self.state = self.state.evaluate(self, None)

	def evaluate_pick_card_choice(self):
		self.played_cards = self._controller.player_pick_a_card(self._controller.current_player)[0]
		sstr = "You picked: " + str(self.played_cards)
		self._controller.display_message(sstr)
		self._logger.debug(sstr)
		if (self.state is None):
			self.state = BeginPlayState()
		st = "Starting the round: " + self.state.__class__.__name__
		self._logger.info(st)
		self.state = self.state.evaluate(self, self.played_cards)

	def evaluate_skip_card_choice(self):
		self._logger.info("Skipping turn")
		self.pick_one()
		self.update_state('PlayerSkip')				
		self.playing.player_state = PlayerState.PLAYED
		self._controller.set_current_player()

	def play1Round(self):
		self.state = BeginPlayState()
		self.playing = self._controller.get_player_state(self._controller.current_player)
		while self.playing.player_state == PlayerState.PLAYING:
			self._controller.display_top_card()
			if ((self.is_card_a_pickone(self._controller.get_top_card()) or 
				self.is_card_a_picktwo(self._controller.get_top_card())) and 
				self._controller.get_last_playing_state() == "PickCardsState" and
				(self.has_picked_cards() is False)):
				self.end_played_pick_card()
			elif (isinstance(self.state, PickCardsState) and (self.is_card_a_pickone(self.played_cards) or
				self.is_card_a_picktwo(self.played_cards))):
				self.start_played_pick_card()
			elif any((isinstance(self.state, QuestionCardState),
					isinstance(self.state, DropCardState), 
					isinstance(self.state, SkipCardState))):
				self.start_special_states()
			elif isinstance(self.state, QuestionCardandSkipState):
				return			# allows the player to play again
			elif any((isinstance(self.state, NormalCardState), 
				isinstance(self.state, PunishWrongMatchesState))):
					self.state = self.state.evaluate(self, self.played_cards)
			else: 
				self.normal_play()

			st = "Next/End State = " + str(self.state)
			self._logger.debug(st)

			# Determine who won and end game
			if self._controller.get_last_player().has_played_last_card():
				self._controller.set_win_status(self._controller.get_last_player())
				self.is_there_a_winner = True
				return

	def update(self, playedCards):
		self._controller.play_card(playedCards)

	def update_state(self, state):
		self._controller.update_state(state)
	
	def pick_one(self):
		self._controller.display_message("Dealing a card to current player")
		self._logger.info("Dealing a card to current player")
		self.num_of_pick_cards = self.num_of_pick_cards - 1
		self._controller.deal_to_player(self._controller.current_player)

	def pick_two(self):
		self.pick_one()
		self.pick_one()