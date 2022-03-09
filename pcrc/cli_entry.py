import sys
import time
from logging import Logger

from pcrc import constant
from pcrc.config import SettableOptions, Config
from pcrc.pcrc_client import PcrcClient
from pcrc.protocol import SUPPORTED_MINECRAFT_VERSIONS

pcrc = PcrcClient()
logger: Logger = pcrc.logger


def on_start_up():
	if pcrc.config.was_missing_file:
		logger.error('Config file not found, default config file generated')
		logger.error('Please fill in the config file on demand')
		sys.exit(1)

	logger.info('PCRC {} starting up'.format(constant.VERSION))
	logger.info('PCRC is open source, u can find it here: https://github.com/Fallen-Breath/PCRC')
	logger.info('Supported Minecraft version = {}'.format(SUPPORTED_MINECRAFT_VERSIONS))


def is_working():
	return pcrc.recorder.is_recording()


def is_stopped():
	return pcrc.is_fully_stopped()


def start():
	global pcrc
	if is_stopped():
		if pcrc.start():
			logger.info('PCRC started')
		else:
			logger.warning('Failed to start PCRC')
	else:
		logger.warning('PCRC is running, ignore')


def stop():
	global pcrc
	if is_working():
		pcrc.stop(block=True)
	else:
		logger.info('PCRC is not running, ignore')


def say(message: str):
	pcrc.chat(message)


def whitelist_commands(text: str, config: Config):
	whitelist = config.get('whitelist')
	wl_isenabled = config.get('enabled')
	cmd = text.split(' ')
	if len(cmd) == 1:
		logger.info('whitelist add|del|on|off|status')
	elif len(cmd) == 3 and cmd[1] == 'add':
		whitelist.append(cmd[2])
		logger.info('Added {} to whitelist'.format(cmd[2]))
	elif len(cmd) == 3 and cmd[1] == 'del':
		try:
			whitelist.remove(cmd[2])
		except ValueError:
			logger.info('Player {} is not in the whitelist!'.format(cmd[2]))
		else:
			logger.info('Removed {} from the whitelist.'.format(cmd[2]))
	elif len(cmd) == 2 and cmd[1] == 'on':
		config.set_value('enabled', 'True')
		logger.info('Whitelist Enabled.')
	elif len(cmd) == 2 and cmd[1] == 'off':
		config.set_value('enabled', 'False')
		logger.info('Whitelist Disabled.')
	elif len(cmd) == 2 and cmd[1] == 'status':
		logger.info('Status: {}'.format(wl_isenabled))
		logger.info('White list: {}'.format(whitelist))


def set_option_commands(text: str, config: Config):
	cmd = text.split(' ')
	if len(cmd) == 1:
		logger.info('Available commands: {}'.format(SettableOptions))
		return
	option = cmd[1]
	try:
		value = config.convert_to_option_type(option, cmd[2])
		config.set_value(option, value)
		logger.info('Assign "{}" = "{}" ({}) now'.format(option, value, config.get_option_type(option).__name__))
		config.set_value(option, value, forced=True)
	except Exception as e:
		logger.error('Failed to set config: {}'.format(e))


def show_status():
	msg = 'Online: {}; \n{}'.format(pcrc.is_online(), pcrc.recorder.get_status())
	for line in msg.splitlines():
		logger.info(line)


def main():
	on_start_up()
	pcrc.authenticate()

	logger.info('Enter "start" to start PCRC')
	while True:
		try:
			text = input()
			if text == '':
				continue
			logger.info('Processing command "{}"'.format(text))

			config = pcrc.config
			config_changed = False
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
				say(text[4:])
			elif text.startswith('whitelist'):
				whitelist_commands(text, config)
				config_changed = True
			elif text.startswith('set'):
				set_option_commands(text, config)
				config_changed = True
			elif text == 'status':
				show_status()
			else:
				logger.error('Command "{}" not found!'.format(text))

			if config_changed:
				config.write_to_file()

		except (KeyboardInterrupt, SystemExit):
			logger.info('User interrupted')
			break
		except:
			logger.exception('Error handling console input')
	try:
		if is_working():
			logger.info('Stopping recorder before exit')
			stop()
		else:
			logger.info('Waiting for recorder to stop before exit')
			while pcrc.is_running():
				time.sleep(0.1)
	except (KeyboardInterrupt, SystemExit):
		logger.info('Forced to stop')
		return
	except:
		logger.exception('Error waiting for recorder to stop')

	logger.info('Exited')
