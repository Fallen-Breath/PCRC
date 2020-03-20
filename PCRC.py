# coding: utf8

from __future__ import print_function

import time
import traceback

import utils
from logger import Logger
from recorder import Recorder
from config import Config
from pycraft.compat import input
from pycraft.exceptions import YggdrasilError

recorder = None
logger = Logger(name='PCRC')
ConfigFile = 'config.json'
TranslationFolder = 'lang/'


def on_start_up():
	global logger
	logger.log('PCRC {} starting up'.format(utils.Version))
	logger.log('PCRC is open source, u can find it here: https://github.com/Fallen-Breath/PCRC')
	logger.log('PCRC is still in development, it may not work well')


def start():
	global recorder, logger, ConfigFile
	if recorder is None or recorder.is_stopped():
		logger.log('Creating new PCRC recorder')
		try:
			recorder = Recorder(ConfigFile, TranslationFolder)
		except YggdrasilError as e:
			logger.error(e)
			return
		ret = recorder.start()
		logger.log('Recorder started, success = {}'.format(ret))
	else:
		logger.warn('Recorder is running, ignore')


def is_working():
	global recorder
	return recorder is not None and recorder.is_working()


def stop():
	global recorder, logger
	if is_working():
		recorder.stop(by_user=True)
		while not recorder.is_stopped():
			time.sleep(0.1)
		logger.log('Recorder stopped')
	else:
		logger.warn('Recorder is not running, ignore')


def main():
	global recorder, logger
	while True:
		try:
			text = input()
			logger.log('Processing command "{}"'.format(text))
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
			elif text == 'set':
				commands = Config(ConfigFile).data.keys()
				good_cmds = []
				for command in commands:
					if not command.startswith('__'):
						good_cmds.append(command)
				logger.log('Available commands: {}'.format(good_cmds))
			elif text.startswith('set '):
				success = False
				try:
					cmd = text.split(' ')
					option = cmd[1]
					value = cmd[2]
					config = Config(ConfigFile)
					value = config.convert_to_option_type(option, value)
					config.set_value(option, value)
					config.write_to_file()
					logger.log(
						'Assign "{}" = "{}" ({}) now'.format(option, value, config.get_option_type(option).__name__))
					if recorder is not None:
						recorder.set_config(option, value, forced=True)
					success = True
				except Exception:
					logger.error(traceback.format_exc())
				if not success:
					logger.log('Parameter error')
			elif text == 'status':
				if recorder is not None:
					msg = 'Online: {}; '.format(recorder.is_online())
					msg += recorder.format_status(recorder.translations.translate('CommandStatusResult', 'en_us'))
					for line in msg.splitlines():
						logger.log(line)
				else:
					logger.log('Recorder is None')
			elif text == 'config':
				messages = Config(ConfigFile).display().splitlines()
				for message in messages:
					logger.log(message)
			else:
				logger.log('Command not found!')
		except (KeyboardInterrupt, SystemExit):
			break
		except Exception:
			logger.error(traceback.format_exc())
	try:
		if is_working():
			logger.log('Stopping recorder before exit')
			stop()
			while not recorder.is_stopped():
				time.sleep(0.01)
	except (KeyboardInterrupt, SystemExit):
		logger.log('Forced to stop')
		return
	except Exception:
		logger.error(traceback.format_exc())

	logger.log('Exited')


if __name__ == "__main__":
	on_start_up()
	main()
