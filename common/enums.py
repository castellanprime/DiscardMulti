
from enum import Enum

class MyEnum(Enum):

	def __str__(self):
		return "({0}={1})".format(self.__class__.__name__, self.name)

class ShapeColour(MyEnum):
	RED = 1
	BLUE = 2
	GREEN = 3
	YELLOW = 4

class CardColour(MyEnum):
	BLACK = 1
	WHITE = 2

class Shapes(MyEnum):
	CROSS = 1
	SQUARE = 2
	TRIANGLE = 3
	CIRCLE = 4
	CUP = 5

class PlayerState(MyEnum):
	PLAYING = 1					# Currently playing
	PLAYED = 2					# Just played before currently playing
	PAUSED = 3					# Waiting to play

class GameState(MyEnum):
	WIN = 1						# Player won
	LOSE = 2					# Player lost
	DRAW = 3 					# If the game is timed

class CardType(MyEnum):
	SPECIAL=1
	NORMAL=2

class SpecialCardName(MyEnum):
	PICKONE='1'
	PICKTWO='2'
	SKIP='->'
	QUESTION='?'
	DROP='-'
