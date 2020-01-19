# coding: utf8

from __future__ import print_function

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
	if recorder is None or (not isWorking() and recorder.canStart()):
		try:
			recorder = Recorder(ConfigFile, TranslationFolder)
		except YggdrasilError as e:
			logger.error(e)
			return
		recorder.start()
	else:
		logger.warn('Recorder is running, ignore')

def isWorking():
	global recorder
	return recorder is not None and recorder.isWorking()

def stop():
	global recorder, logger
	if isWorking():
		recorder.stop()
		while not not recorder.canStart():
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
			elif text == 'status':
				if recorder is not None:
					msg = 'Online: {}; '.format(recorder.isOnline())
					msg += recorder.format_status(recorder.translations.translate('CommandStatusResult','en_us'))
					for line in msg.splitlines():
						logger.log(line)
				else:
					logger.log('Recorder is None')
			else:
				logger.log('Command not found!')
		except (KeyboardInterrupt, SystemExit):
			break
		except Exception:
			logger.error(traceback.format_exc())
	try:
		if isWorking():
			logger.log('Stopping recorder before exit')
			stop()
			while not recorder.canStart():
				time.sleep(0.01)
	except (KeyboardInterrupt, SystemExit):
		logger.log('Forced to stop')
		return
	except Exception:
		logger.error(traceback.format_exc())


if __name__ == "__main__":
	main()
