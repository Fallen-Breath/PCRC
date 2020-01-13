# coding: utf8

from __future__ import print_function

import sys
import utils
from Logger import Logger
from Recorder import Recorder
from pycraft.compat import input
from pycraft.exceptions import YggdrasilError

logger = Logger(name='PCRC', file_name=utils.LoggingFileName)

def main():
	try:
		recorder = Recorder('config.json')
	except YggdrasilError as e:
		print(e)
		return
	recorder.connect()
	while True:
		try:
			text = input()
			if text == "/stop":
				recorder.stop_recording()
				break
			elif text == "/restart":
				recorder.restart_recording()
				break
		except KeyboardInterrupt:
			recorder.stop_recording()
			logger.log("Bye!")
			sys.exit()
		except:
			recorder.stop_recording()


if __name__ == "__main__":
	main()
