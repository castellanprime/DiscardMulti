"""
	Game object
"""
import logging, random
from servermodel import ServerModel
from serverenums import NumberOfCardsToDeal
from gameengine import DiscardGame


class GameController(object):
	def __init__(self, players):
		self._logger = logging.getLogger(__name__)
		self.model = ServerModel(players)
		self.game_engine = DiscardGame(self)
		self.has_initial_player = False
		self.init_cards()
		self.current_player = None
		self.winner = None
		self.state = None

	def init_cards(self):
		self.deal()
		while self.game_engine.is_card_a_specialcard(self.get_top_card()):
			self.deal()

	def get_current_player(self):
		return self.model.get_current_player()

	def set_initial_player(self, player):
		if not self.has_initial_player:
			self.model.set_current_player(player)
		else:
			self.get_current_player()

	# Set the player state here
	def deal(self):
		self._logger.info('Dealing the cards')
		self._logger.debug('Dealing the cards')
		players = self.model.players
		num_of_cards_to_deal = 0
		if len(players) == 2:
			num_of_cards_to_deal = NumberOfCardsToDeal.TWO_PLAYER.value
		elif len(players) == 3:
			num_of_cards_to_deal = NumberOfCardsToDeal.THREE_PLAYER.value
		else:
			num_of_cards_to_deal = NumberOfCardsToDeal.OTHER_PLAYER.value
		temp_list = self.model.get_game_deck()
		random.shuffle(temp_list)
		self.model.main_deck[:] = temp_list
		for card_index in range(0, num_of_cards_to_deal):
			for player in self.model.players:
				self.model.give_player_a_card(player, index=None)
		for index, card in enumerate(reversed(self.model.get_game_deck())):
			if self.game_engine.is_card_a_normalcard(card):
				self.model.discard_deck.append(self.model.get_a_card(index))
				break

	def get_player_cards_for(self, player):
		return self.model.get_player_cards(player)
		
	def get_top_card(self):
		return self.model.get_top_card()

	def start_game(self):
		pass
