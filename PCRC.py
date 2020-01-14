# coding: utf8

from __future__ import print_function

import time
import traceback

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
			if text == "start":
				if not recorder.isRecording():
					recorder.start()
				else:
					logger.warn('Recorder is running, ignore')
			elif text == "stop":
				if recorder.isRecording():
					recorder.stop()
				else:
					logger.warn('Recorder is not running, ignore')
			elif text == "restart":
				recorder.restart()
			elif text == "exit":
				break
			elif text.startswith('say '):
				recorder.chat(text[4:])
		except Exception as e:
			logger.error(traceback.format_exc())
			break
	recorder.stop()

try:
	if __name__ == "__main__":
		main()
except Exception:
	print(traceback.format_exc())