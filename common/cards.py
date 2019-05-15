from .enums import SpecialCardName

class Card:

	def __init__(self, card_colour, other_colour):
		self.card_colour = card_colour
		self.other_colour = other_colour

	def __repr__(self):
		return "{0}:{1}".format(self.card_colour, self.other_colour)

class NormalCard(Card):

	def __init__(self, card_colour, shape_colour, shape):
		super().__init__(card_colour, shape_colour)
		self.shape = shape

	def get_shape(self):
		return self.shape

	def get_card_colour(self):
		return self.card_colour

	def get_shape_colour(self):
		return self.other_colour

	def get_name(self):
		return 'Shape'

	def __repr__(self):
		return "(Shape:{0} Colours:{1})".format(self.shape, super().__repr__())

class SpecialCard(Card):

	def __init__(self, card_colour, char_colour, char):
		super().__init__(card_colour, char_colour)
		self.char = char

	def get_char(self):
		return self.char

	def get_card_colour(self):
		return self.card_colour

	def get_char_colour(self):
		return self.other_colour

	def get_name(self):
		return SpecialCardName(self.char).name

	def __repr__(self):
		return "(Char:{0} Colours:{1})".format(self.char, super().__repr__())