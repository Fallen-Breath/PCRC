# coding: utf8

from __future__ import print_function

import json
import time
import traceback

import utils
from Logger import Logger
from Recorder import Recorder, Config
from pycraft.compat import input
from pycraft.exceptions import YggdrasilError

recorder = None
logger = Logger(name='PCRC', file_name=utils.LoggingFileName)
ConfigFile = 'config.json'
TranslationFolder = 'lang/'

def start():
	global recorder, logger, ConfigFile
	if recorder is None or recorder.canStart():
		try:
			recorder = Recorder(ConfigFile, TranslationFolder)
		except YggdrasilError as e:
			logger.error(e)
			return
		recorder.start()
	else:
		logger.warn('Recorder is running, ignore')

def stop():
	if recorder is not None and recorder.isRecording():
		recorder.stop()
		while not recorder.finishedStopping():
			time.sleep(0.1)
	else:
		logger.warn('Recorder is not running, ignore')


def main():
	global recorder, logger
	while True:
		try:
			text = input()
			if text == "start":
				start()
			elif text == "stop":
				stop()
			elif text == "restart":
				stop()
				start()
			elif text == 'exit':
				break
			elif text.startswith('say '):
				recorder.chat(text[4:])
			elif text.startswith('set '):
				success = False
				try:
					cmd = text.split(' ')
					option = cmd[1]
					value = cmd[2]
					config = Config(ConfigFile)
					config.set_value(option, value)
					config.write_to_file()
					logger.log('Assign "{}" = "{}" now'.format(option, value))
					if recorder is not None:
						recorder.set_config(option, value)
					success = True
				except Exception:
					logger.err(traceback.format_exc())
				if not success:
					logger.log('Parameter error')
		except (KeyboardInterrupt, SystemExit):
			break
		except Exception:
			logger.error(traceback.format_exc())
	try:
		if recorder.isRecording():
			logger.log('Stopping recorder before exit')
			stop()
	except (KeyboardInterrupt, SystemExit):
		logger.log('Forced to stop')
		return
	except Exception:
		logger.error(traceback.format_exc())


if __name__ == "__main__":
	main()
