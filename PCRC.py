# coding: utf8

from __future__ import print_function

import sys
import time

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
		logger.error(e)
		return
	recorder.start()
	while True:
		try:
			text = input()
			if text == "/start":
				if not recorder.isRecording():
					recorder.start()
				else:
					logger.warn('Recorder is running, ignore')
			elif text == "/stop":
				if recorder.isRecording():
					recorder.stop()
				else:
					logger.warn('Recorder is not running, ignore')
			elif text == "/restart":
				recorder.restart()
		except KeyboardInterrupt:
			recorder.stop()
			logger.log("Bye!")
			sys.exit()
		except Exception as e:
			recorder.stop()
			logger.error(e.args)

try:
	if __name__ == "__main__":
		main()
except Exception as e:
	print(e.args)
	time.sleep(100)