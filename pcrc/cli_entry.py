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

	logger.info('PCRC v{} starting up'.format(constant.VERSION))
	logger.info('PCRC is open source, u can find it here: https://github.com/Fallen-Breath/PCRC')
	logger.info('Supported Minecraft version = {}'.format(SUPPORTED_MINECRAFT_VERSIONS))


def is_working():
	return pcrc.recorder.is_recording()


def is_stopped():
	return pcrc.is_fully_stopped()


def show_help():
	logger.info('Command list: help|start|stop|restart|exit|reload|auth|say|whitelist|set|status|list')


def start():
	if is_stopped():
		if pcrc.start():
			logger.info('PCRC started')
		else:
			logger.warning('Failed to start PCRC')
	else:
		logger.warning('PCRC is running, ignore')


def stop():
	pcrc.interrupt_auto_restart()
	if is_working():
		pcrc.stop(block=True)
	else:
		logger.info('PCRC is not running, ignore. Enter "exit" if you want to exit PCRC')


def auth(*, warn_if_already_auth: bool = True):
	if pcrc.has_authenticated():
		if warn_if_already_auth:
			logger.warning('Minecraft authentication is already done')
	else:
		pcrc.authenticate()


def say(text: str):
	args = text.split(' ', 1)
	if len(args) == 1 or len(args[1]) == 0:
		logger.info('say <message>')
	else:
		if pcrc.is_online():
			pcrc.chat(args[1])
		else:
			logger.warning('PCRC is not online, cannot chat')


def whitelist_commands(text: str, config: Config):
	whitelist = config.get('whitelist')
	wl_isenabled = config.get('enabled')
	args = text.split(' ')
	if len(args) == 1:
		logger.info('whitelist [add <name>|del <name>|on|off|status]')
	elif len(args) == 3 and args[1] == 'add':
		whitelist.append(args[2])
		logger.info('Added {} to whitelist'.format(args[2]))
	elif len(args) == 3 and args[1] == 'del':
		try:
			whitelist.remove(args[2])
		except ValueError:
			logger.info('Player {} is not in the whitelist!'.format(args[2]))
		else:
			logger.info('Removed {} from the whitelist.'.format(args[2]))
	elif len(args) == 2 and args[1] == 'on':
		config.set_value('enabled', 'True')
		logger.info('Whitelist Enabled.')
	elif len(args) == 2 and args[1] == 'off':
		config.set_value('enabled', 'False')
		logger.info('Whitelist Disabled.')
	elif len(args) == 2 and args[1] == 'status':
		logger.info('Status: {}'.format(wl_isenabled))
		logger.info('Whitelist: {}'.format(whitelist))


def set_option_commands(text: str, config: Config):
	args = text.split(' ')
	if len(args) == 1:
		logger.info('ste <option> <value>')
		logger.info('Available options: {}'.format(SettableOptions))
		return
	option = args[1]
	try:
		value = config.convert_to_option_type(option, args[2])
		config.set_value(option, value)
		logger.info('Assign "{}" = "{}" ({}) now'.format(option, value, config.get_option_type(option).__name__))
		config.set_value(option, value, forced=True)
	except Exception as e:
		logger.error('Failed to set config: {}'.format(e))


def show_status():
	logger.info('======= PCRC v{} ======='.format(constant.VERSION))
	logger.info('Online: {}'.format(pcrc.is_online()))
	logger.info('Stopped: {}'.format(is_stopped()))
	for line in pcrc.recorder.get_status().splitlines():
		logger.info(line)


def show_player_list():
	if pcrc.is_online():
		logger.info('===== Server Player List =====')
		player_manager = pcrc.recorder.packet_processor.player_manager
		for line in player_manager.dump_player_list().splitlines():
			logger.info('  ' + line)
	else:
		logger.warning('PCRC is not online, cannot get player list')


def reload():
	if pcrc.reload_config():
		logger.info('PCRC config reloaded')


def main():
	on_start_up()
	pcrc.init()
	auth(warn_if_already_auth=False)

	logger.info('Enter "start" to start PCRC')
	while True:
		try:
			text = input()
			if text == '':
				continue
			logger.info('Processing CLI command "{}"'.format(text))

			config = pcrc.config
			config_changed = False
			if text in ['help', '?']:
				show_help()
			elif text == "start":
				start()
			elif text == "stop":
				stop()
			elif text == "restart":
				stop()
				start()
			elif text == 'exit':
				break
			elif text == "reload":
				reload()
			elif text == 'auth':
				auth()
			elif text.startswith('say'):
				say(text)
			elif text.startswith('whitelist'):
				whitelist_commands(text, config)
				config_changed = True
			elif text.startswith('set'):
				set_option_commands(text, config)
				config_changed = True
			elif text == 'status':
				show_status()
			elif text == 'list':
				show_player_list()
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
			logger.info('Stopping PCRC before exit')
			stop()
		else:
			if pcrc.is_running():
				logger.info('Waiting for PCRC to stop before exit')
				while pcrc.is_running():
					time.sleep(0.1)
	except (KeyboardInterrupt, SystemExit):
		logger.info('Forced to stop')
		return
	except:
		logger.exception('Error waiting for PCRC to stop')

	logger.info('Exited')
