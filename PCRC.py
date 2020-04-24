# coding: utf8

import time
import traceback

if __name__ == '__main__':
	from utils import utils, constant
	from utils.logger import Logger
	from utils.recorder import Recorder
	from utils.config import Config
	from utils.pycraft.compat import input
	from utils.pycraft.exceptions import YggdrasilError
else:
	from .utils import utils, constant
	from .utils.logger import Logger
	from .utils.recorder import Recorder
	from .utils.config import Config
	from .utils.pycraft.compat import input
	from .utils.pycraft.exceptions import YggdrasilError

recorder = None
logger = Logger(name='PCRC')
ConfigFile = utils.get_path('config.json')
TranslationFolder = utils.get_path('lang/')


def on_start_up():
	global logger
	logger.log('PCRC {} starting up'.format(constant.Version))
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


def is_stopped():
	global recorder
	return recorder is None or recorder.is_stopped()


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
			if text != '':
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
				elif text.startswith('wl') or text.startswith('whitelist'):
					try:
						config = recorder.config if recorder is not None else Config(ConfigFile)
						whitelist = config.get('whitelist')
						wl_isenabled = config.get('enabled')
						cmd = text.split(' ')
					except Exception:
						logger.error(traceback.format_exc())
					else:
						if len(cmd) == 1:
							logger.log('whitelist add|del|on|off|status')
						if len(cmd) == 3 and cmd[1] == 'add':
							whitelist.append(cmd[2])
							config.set_value('whitelist', whitelist)
							logger.log('Added {} to whitelist.'.format(cmd[2]))
							if(wl_isenabled == False):
								logger.log('Plz note that whitelist is not enabled now.')
						elif len(cmd) == 3 and cmd[1] == 'del':
							try:
								whitelist.remove(cmd[2])
								config.set_value('whitelist', whitelist)
							except ValueError:
								logger.log('Player {} is not in the whitelist!'.format(cmd[2]))
							else:
								logger.log('Deleted {} from the whitelist.'.format(cmd[2]))
						elif len(cmd) == 2 and cmd[1] == 'on':
							config.set_value('enabled', 'True')
							logger.log('PCRC Whitelist Enabled.')
						elif len(cmd) == 2 and cmd[1] == 'off':
							config.set_value('enabled', 'False')
							logger.log('PCRC Whitelist Disabled.')
						elif len(cmd) == 2 and cmd[1] == 'status':
							logger.log('Status: {}'.format(wl_isenabled))
							logger.log('White list: {}'.format(whitelist))
						config.write_to_file()

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
						config = Config(ConfigFile)
						option = cmd[1]
						value = config.convert_to_option_type(option, cmd[2])
						config.set_value(option, value)
						config.write_to_file()
						logger.log(
							'Assign "{}" = "{}" ({}) now'.format(option, value, config.get_option_type(option).__name__))
						if recorder is not None:
							config.set_value(option, value, forced=True)
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
				elif recorder is not None and text.startswith(recorder.config.get('command_prefix')):
					recorder.processCommand(text, None, None)
				else:
					logger.error('Command not found!')
			else:
				logger.error("Please enter the command!")
		except (KeyboardInterrupt, SystemExit):
			break
		except Exception:
			logger.error(traceback.format_exc())
	try:
		if is_working():
			logger.log('Stopping recorder before exit')
			stop()
		else:
			logger.log('Waiting for recorder to stop before exit')
			while not recorder.is_stopped():
				time.sleep(0.1)
	except (KeyboardInterrupt, SystemExit):
		logger.log('Forced to stop')
		return
	except Exception:
		logger.error(traceback.format_exc())

	logger.log('Exited')


if __name__ == "__main__":
	on_start_up()
	main()
