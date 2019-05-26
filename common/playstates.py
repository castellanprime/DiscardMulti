"""
    State machine for the states
"""

from common.enums import PlayerState, ShapeColour, CardColour, Shapes
from common.cards import NormalCard, SpecialCard

class PlayStates(object):

	"""Superclass for playing states of Discard"""
	def evaluate(self, discardGame, playedCards):
		raise NotImplementedError
	def __str__(self):
		return self.__doc__

class BeginPlayState(PlayStates):
	"""Initial beginning state"""
	def evaluate(self, discardGame, playedCards):
		top_card = discardGame._controller.get_top_card()
		if discardGame.do_cards_match(playedCards, top_card):
			if discardGame.is_card_a_normalcard(playedCards):
				return NormalCardState()
			elif any((discardGame.is_card_a_pickone(playedCards), 
				discardGame.is_card_a_picktwo(playedCards))):
				return PickCardsState() 
			elif discardGame.is_card_a_question(playedCards):
				return QuestionCardState()
			elif discardGame.is_card_a_drop(playedCards):
				return DropCardState()
			elif discardGame.is_card_a_skip(playedCards):
				return SkipCardState()
		else:
			return PunishWrongMatchesState()

class NormalCardState(PlayStates):
	"""Rules for normal cards"""
	def evaluate(self, discardGame, playedCards):
		discardGame._logger.info("Beginning NormalCardState")
		discardGame.update(playedCards)
		#if (discardGame._controller.get_last_playing_state == "SkipCardState" and 
		#	discardGame._controller.get_num_of_players() == 2):
		#	discardGame._controller.force_player_to_play()
		discardGame.update_state(self.__class__.__name__)
		discardGame.playing.player_state = PlayerState.PLAYED
		discardGame._controller.set_current_player()
		return None

class PunishWrongMatchesState(PlayStates):
	""" Punishment for wrong card matches """
	def evaluate(self, discardGame, playedCards):
		discardGame._logger.info("Beginning PunishWrongMatchesState")
		if playedCards:
			discardGame.update(playedCards)
		discardGame.update_state(self.__class__.__name__)
		discardGame._controller.punish_for_wrong_match(discardGame._controller.current_player)
		discardGame.playing.player_state = PlayerState.PLAYED
		discardGame._controller.set_current_player()
		return None

class PickCardsState(PlayStates):
	""" Pick Card State """
	def evaluate(self, discardGame, playedCards):
		discardGame._logger.info("Beginning PickCardsState")
		if discardGame.num_of_pick_cards < 0:
			discardGame.num_of_pick_cards = 0
		strs = "Num of pick cards = " + str(discardGame.num_of_pick_cards) 
		discardGame._logger.info(strs)
		if all((playedCards is None, discardGame.num_of_pick_cards > 0)):
			# that means the current player can not block the @pick_card on the discard_pile
			strs = "Num of cards(" + discardGame._controller.get_top_card().get_name() 	+ ") current player has to deal with " + str(discardGame.num_of_pick_cards)
			#strs = "Num of cards current player is being dealt=" + str(discardGame.num_of_pick_cards)
			discardGame._logger.info(strs)
			if discardGame.is_card_a_pickone(discardGame._controller.get_top_card()):
				for i in range(discardGame.num_of_pick_cards):
					discardGame.pick_one()
			if discardGame.is_card_a_picktwo(discardGame._controller.get_top_card()):
				for i in range(discardGame.num_of_pick_cards):
					discardGame.pick_two()
			discardGame.num_of_pick_cards = 0
			discardGame.played_cards = None
		elif playedCards:
			top_card = discardGame._controller.get_top_card()
			if any((all((discardGame.is_card_a_picktwo(playedCards), discardGame.is_card_a_picktwo(top_card))),
				   all((discardGame.is_card_a_pickone(playedCards), discardGame.is_card_a_pickone(top_card))))):
				discardGame.add_to_pick_cards()
				discardGame.update(playedCards)
				choice = input(discardGame._controller.views[0].prompts(20))	# Prompt if current player wants to pile on
				while choice == 'y':
					top_card = discardGame._controller.get_top_card()
					# it allows multiple pick cards
					if any((all((discardGame.is_card_a_picktwo(playedCards), discardGame.is_card_a_picktwo(top_card))),
						   all((discardGame.is_card_a_pickone(playedCards), discardGame.is_card_a_pickone(top_card))))):
						discardGame.add_to_pick_cards()
						discardGame.update(playedCards)
					else:
						return PunishWrongMatchesState()
					choice = input(discardGame._controller.views[0].prompts(20))
				strs = "Number of cards the new player has to pick=" + str(discardGame.num_of_pick_cards)
				discardGame._logger.info(strs)
			elif discardGame.do_cards_match(playedCards, top_card) == True:
				#discardGame.update_state(self.__class__.__name__)
				state_to_evaluate = None
				if discardGame.is_card_a_drop(playedCards):
					state_to_evaluate = DropCardandPickState()
				elif discardGame.is_card_a_question(playedCards):
					state_to_evaluate = QuestionCardandPickState()
				else:
					return PunishWrongMatchesState()
				state_to_evaluate = state_to_evaluate.evaluate(discardGame, top_card)
				return state_to_evaluate
			elif discardGame.do_cards_match(playedCards, top_card) == False:
				state_to_evaluate = PunishWrongMatchesState()
				state_to_evaluate = state_to_evaluate.evaluate(discardGame, top_card)
				return state_to_evaluate
		discardGame.update_state(self.__class__.__name__)
		discardGame.playing.player_state = PlayerState.PLAYED
		discardGame._controller.set_current_player()
		return None

class QuestionCardState(PlayStates):
	""" Question Card Rules """
	def evaluate(self, discardGame, playedCards):
		discardGame._logger.info("Beginning QuestionCardState")
		if discardGame.is_card_a_question(discardGame._controller.get_top_card()) is False:
			discardGame.update(playedCards)
			discardGame.update_state(self.__class__.__name__)
			return self
		else:
			if playedCards is None:		# If it is  not combinable
				request_type, requested_card = discardGame._controller.request_a_card()
				player = discardGame._controller.get_next_turn()
				discardGame._controller.display_cards(player)
				request = request_type + requested_card
				card_choice = discardGame._controller.request_a_card_from_player(request, player)
				while card_choice[0] is None:
					discardGame._controller.deal_to_player(player)
					player = discardGame._controller.get_next_player(player)
					discardGame._controller.display_cards(player)
					if player == discardGame._controller.current_player:
						break
					card_choice = discardGame._controller.request_a_card_from_player(request, player)
				card_to_compare = None
				if request_type == "Shape:":
					card_to_compare = NormalCard(CardColour.BLACK, discardGame._controller.get_random_colour(), discardGame._controller.get_shape(requested_card))
				elif request_type == "Colour:":
					card_to_compare = NormalCard(CardColour.BLACK, discardGame._controller.get_colour(requested_card), discardGame._controller.get_random_shape())
				if any(( card_choice[0] is None, all((discardGame.is_card_a_normalcard(card_choice[0]), 
				 	discardGame.do_cards_match(card_to_compare, card_choice[0]))) )):
					if card_choice[0] is None: # if card_choice is None, meaning that you are still playing
						discardGame.update(playedCards)
					else:	
						discardGame.update(card_choice[0])
						discardGame._controller.set_player_state(player, PlayerState.PLAYED)
					discardGame.playing.player_state = PlayerState.PLAYED
					discardGame.update_state(self.__class__.__name__)
					discardGame._controller.set_current_player()
					if discardGame.is_card_a_question(card_choice[0]) is True:
						return self
					return None
				else:
					if discardGame.is_card_a_drop(playedCards):
						return QuestionCardandDropCardState()
					elif discardGame.is_card_a_skip(playedCards):
						return QuestionCardandSkipState()
					elif any((discardGame.is_card_a_picktwo(playedCards),
						discardGame.is_card_a_pickone(playedCards))):
						return QuestionCardandPickState()
					return PunishWrongMatchesState()
			elif playedCards:
				if discardGame.is_card_a_drop(playedCards):
					return QuestionCardandDropCardState()
				elif discardGame.is_card_a_skip(playedCards):
					return QuestionCardandSkipState()
				elif any((discardGame.is_card_a_picktwo(playedCards),
					discardGame.is_card_a_pickone(playedCards))):
					return QuestionCardandPickState()
				elif discardGame.is_card_a_question(playedCards):	# cases where you play more than one question card
					return self
				else:
					return PunishWrongMatchesState()

class QuestionCardandDropCardState(PlayStates):
	""" Rules for combining a question card and a drop card """
	def evaluate(self, discardGame, playedCards):
		discardGame._logger.info("Beginning QuestionCardandDropCardState")
		player = discardGame._controller.get_next_turn()
		while player != discardGame._controller.get_current_player():
			cards = player.get_deck()
			for index, card in enumerate(cards):
				if discardGame.is_card_a_specialcard(cards[index]):
					discardGame.update(discardGame._controller.r_pick_a_card(index, player))
					discardGame.update_state(self.__class__.__name__)
					discardGame.playing.player_state = PlayerState.PLAYED
					discardGame._controller.set_current_player()
					return None
			player = discardGame._controller.get_next_turn(player)
		discardGame.update(discardGame._controller.player_pick_a_card(player))
		if card is None:	# to punish a player that does not call last card when he is supposed to
			return PunishWrongMatchesState()
		discardGame.update_state(self.__class__.__name__)
		discardGame.playing.player_state = PlayerState.PLAYED
		discardGame._controller.set_current_player()
		return None

class QuestionCardandPickState(PlayStates):
	""" Rules for combining a question card and a pickone/picktwo card """
	def evaluate(self, discardGame, playedCards):
		discardGame._logger.info("Beginning QuestionCardandPickState")
		if discardGame.is_a_card_pickone(playedCards):
			player = discardGame._controller.get_next_turn()
			while player != discardGame._controller.get_last_player():
				discardGame._controller.deal_to_player(player)
				player = discardGame._controller.get_next_turn(player)
			player = discardGame._controller.get_last_player()
			discardGame._controller.deal_to_player(player)
		elif discardGame.is_a_card_picktwo(playedCards):
			player = discardGame._controller.get_next_turn()
			while player != discardGame._controller.get_last_player():
				discardGame._controller.deal_to_player(player)
				discardGame._controller.deal_to_player(player)
				player = discardGame._controller.get_next_turn(player)
			player = discardGame._controller.get_last_player()
			discardGame._controller.deal_to_player(player)
			discardGame._controller.deal_to_player(player)
		discardGame.update_state(self.__class__.__name__)
		discardGame.playing.player_state = PlayerState.PLAYED
		discardGame._controller.set_current_player()
		return None

class QuestionCardandSkipState(PlayStates):
	""" Rules for combining a question card and a skip card """
	def evaluate(self, discardGame, playedCards):
		discardGame._logger.info("Beginning QuestionCardandSkipState")
		discardGame.update(playedCards)
		return BeginPlayState()


class DropCardState(PlayStates):
	""" Drop Card Rules """
	# Rewrite to allow for multiple drop cards
	def evaluate(self, discardGame, playedCards):
		discardGame._logger.info("Beginning DropCardState")
		if discardGame.is_card_a_drop(discardGame._controller.get_top_card()) is False:
			discardGame.update(playedCards)
			discardGame.update_state(self.__class__.__name__)
			return self
		else:
			if playedCards is None:			# you did not combine
				st = "Number of cards to discard: " + str(discardGame.num_of_cards_to_discard)
				discardGame._logger.info(st)
				for i in range(discardGame.num_of_cards_to_discard):
					# multiple discards
					discardGame._controller.display_message("Choose card to drop")
					discardGame._controller.display_cards(discardGame._controller.current_player)
					card = discardGame._controller.player_pick_a_card(discardGame._controller.get_current_player())
					if card is None:	# to punish a player that does not call last card when he is supposed to
						return PunishWrongMatchesState()
					discardGame.update(card)
					discardGame.update_state(self.__class__.__name__)
				discardGame.playing.player_state = PlayerState.PLAYED
				discardGame._controller.set_current_player()
				return None
			elif playedCards: 				# you combined
				#discardGame.num_of_cards_to_discard += 1
				state_to_evaluate = None
				if any((discardGame.is_card_a_pickone(playedCards), 
					discardGame.is_card_a_picktwo(playedCards))):
					state_to_evaluate = DropCardandPickState()
				elif discardGame.is_card_a_skip(playedCards):
					state_to_evaluate = DropCardandSkipState()
				elif discardGame.is_card_a_question(playedCards):
					state_to_evaluate = QuestionCardandDropCardState()
				elif discardGame.is_card_a_drop(playedCards):
					#discardGame.num_of_cards_to_discard += 1
					discardGame.update(playedCards)
					return self
				else:
					return PunishWrongMatchesState()
				state_to_evaluate = state_to_evaluate.evaluate(discardGame, playedCards)
				return state_to_evaluate

class DropCardandPickState(PlayStates):
	""" Rules for a drop and a pickone/picktwo card """
	def evaluate(self, discardGame, playedCards):
		discardGame._logger.info("Beginning DropCardandPickState")
		if discardGame.is_card_a_pickone(playedCards):
			card = discardGame._controller.player_pick_a_card(discardGame._controller.get_current_player())
			if card is None:	# to punish a player that does not call last card when he is supposed to
				return PunishWrongMatchesState()
			discardGame.update(card)
		elif discardGame.is_card_a_picktwo(playedCards):
			card = discardGame._controller.player_pick_a_card(discardGame._controller.get_current_player())
			if card is None:	# to punish a player that does not call last card when he is supposed to
				return PunishWrongMatchesState()
			discardGame.update(card)
			card = discardGame._controller.player_pick_a_card(discardGame._controller.get_current_player())
			if card is None:	# to punish a player that does not call last card when he is supposed to
				return PunishWrongMatchesState()
			discardGame.update(card)
		discardGame.update_state(self.__class__.__name__)
		discardGame.playing.player_state = PlayerState.PLAYED
		discardGame._controller.set_current_player()
		return None

class DropCardandSkipState(PlayStates):
	""" Rules for a drop and a skip card """
	def evaluate(self, discardGame, playedCards):
		discardGame._logger.info("Beginning DropCardandSkipState")
		player = discardGame._controller.get_next_turn()
		cards = player.get_deck()
		for index, card in enumerate(cards):
			if discardGame.is_card_a_specialcard(cards[index]):
				discardGame.update(discardGame._controller.r_pick_a_card(index, player))
				discardGame.update_state(self.__class__.__name__)
				discardGame.playing.player_state = PlayerState.PLAYED
				discardGame._controller.set_current_player()
				return None
		discardGame._controller.display_message("Dropping extra card from current player pile")
		discardGame._controller.display_cards(discardGame._controller.current_player)
		card = discardGame._controller.player_pick_a_card(discardGame._controller.get_current_player())
		if card is None:	# to punish a player that does not call last card when he is supposed to
			return PunishWrongMatchesState()
		if discardGame.is_card_a_normalcard(card):
			discardGame.update(card)
			discardGame.update_state(self.__class__.__name__)
			discardGame.playing.player_state = PlayerState.PLAYED
			discardGame._controller.set_current_player()
			return None
		elif discardGame.is_card_a_specialcard(card):
			discardGame.played_cards = card
			state_to_evaluate = None
			if discardGame.is_card_a_question(card):
				state_to_evaluate = QuestionCardandDropCardState()
			elif discardGame.is_card_a_drop(card):
				discardGame.add_to_discard_cards()
				state_to_evaluate = DropCardState()
			elif any((discardGame.is_card_a_picktwo(card), discardGame.is_card_a_pickone(card))):
				state_to_evaluate = DropCardandPickState()
			elif discardGame.is_card_a_skip(card):
				state_to_evaluate = DropCardandSkipState()
			state_to_evaluate = state_to_evaluate.evaluate(discardGame, card)
			return state_to_evaluate

class SkipCardState(PlayStates):
	""" Skip Card Rules """
	def evaluate(self, discardGame, playedCards):
		discardGame._logger.info("Beginning SkipCardState")
		if discardGame.is_card_a_skip(discardGame._controller.get_top_card()) is False:
			discardGame.update(playedCards)
			discardGame.update_state(self.__class__.__name__)
			return self
		else:
			if playedCards is None:
				discardGame.update_state(self.__class__.__name__)
				player = discardGame._controller.get_next_turn()
				discardGame._controller.set_player_state(player, PlayerState.PLAYED)
				if discardGame._controller.get_num_of_players() > 2:
					player = discardGame._controller.get_next_turn(player)
					discardGame._controller.set_player_state(player, PlayerState.PAUSED)
				discardGame.playing.player_state = PlayerState.PAUSED		# This in a three or more player game will kill the loop
				discardGame._controller.set_current_player()
				#return QuestionCardandSkipState()							# this will allow the player to decide if he or she wants to play again
				return None
			elif playedCards:
				state_to_evaluate = None
				if discardGame.is_card_a_question(playedCards):
					state_to_evaluate = QuestionCardandSkipState()
				elif discardGame.is_card_a_drop(playedCards):
					state_to_evaluate = DropCardandSkipState()
				elif any((discardGame.is_card_a_pickone(playedCards), discardGame.is_card_a_picktwo(playedCards))):
					state_to_evaluate = PickCardsState()
				else:
					return PunishWrongMatchesState()
				state_to_evaluate = state_to_evaluate.evaluate(discardGame, playedCards)
				return state_to_evaluate

class BlockState(PlayStates):
	""" Rules for Blocking """
	def evaluate(self, discardGame, playedCards):
		discardGame._logger.info("Beginning BlockState")
		for i in range(discardGame.num_of_pick_cards):
			if any((all((discardGame.is_card_a_pickone(playedCards),
				discardGame.is_card_a_pickone(discardGame._controller.get_top_card()))),
				all((discardGame.is_card_a_picktwo(playedCards),
				discardGame.is_card_a_picktwo(discardGame._controller.get_top_card()))))) is False:
				return PunishWrongMatchesState()
		discardGame.num_of_pick_cards = 0
		discardGame.update_state(self.__class__.__name__)
		discardGame.playing.player_state = PlayerState.PLAYED
		discardGame._controller.set_current_player()
		return None

class LastCardState(PlayStates):
	"""Rules for Last cards"""
	def evaluate(self, discardGame, playedCards):
		discardGame._logger.info("Beginning LastCardState")
		state_to_evaluate = None
		if all(( discardGame.is_card_a_specialcard(playedCards), 
			len(discardGame._controller.current_player.get_deck()) == 0 )):
			state_to_evaluate = PunishWrongMatchesState()
		elif any(( discardGame.is_card_a_pickone(playedCards), 
			discardGame.is_card_a_picktwo(playedCards) )):
			state_to_evaluate = PunishWrongMatchesState()
		elif any(( discardGame.is_card_a_drop(playedCards), discardGame.is_card_a_question(playedCards) )):
			if discardGame.is_card_a_drop(playedCards):
				state_to_evaluate = DropCardState()
			elif discardGame.is_card_a_question(playedCards):
				state_to_evaluate = QuestionCardState()
		else:
			state_to_evaluate = NormalCardState()
			discardGame._controller.current_player.set_last_card()
		state_to_evaluate = state_to_evaluate.evaluate(discardGame, playedCards)
		return state_to_evaluate