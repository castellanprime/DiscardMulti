"""
	Client app
"""

from Pyside2 import QtCore

class NetClient(object):
	def __init__(self, room_url, game_url):
		self.wsconn = None
		self.wsconn_close = False
		self.room_url = room_url
		self.game_url = game_url

class Controller(QObject):
	def __init__(self):
		self.app = QtCore.QCoreApplication(sys.argv)
		self.model = None	# Model object
	
	def start(self):
		return self.app.exec_()

if __name__ == '__main__':
	pass

