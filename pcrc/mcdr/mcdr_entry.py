import os
import time
from queue import Queue, Empty
from typing import Optional

from mcdreforged.api.decorator import new_thread
from mcdreforged.command.builder.exception import UnknownArgument, UnknownCommand
from mcdreforged.command.builder.nodes.arguments import GreedyText
from mcdreforged.command.builder.nodes.basic import Literal, CommandContext
from mcdreforged.command.command_source import CommandSource, PlayerCommandSource
from mcdreforged.plugin.server_interface import PluginServerInterface, ServerInterface
from mcdreforged.utils.logger import SyncStdoutStreamHandler

import pcrc as pcrc_module
from pcrc.input import InputManager
from pcrc.mcdr.mcdr_config import McdrConfig
from pcrc.pcrc_client import PcrcClient

psi = ServerInterface.get_instance().as_plugin_server_interface()
config: McdrConfig
pcrc: PcrcClient
source_that_starts_pcrc: Optional[CommandSource] = None
user_inputs = Queue()


class MCDRInputManager(InputManager):
	def input(self, message: str) -> str:
		while True:
			try:
				user_inputs.get_nowait()
			except Empty:
				break
		if isinstance(source_that_starts_pcrc, PlayerCommandSource):
			source_that_starts_pcrc.reply('Check server console for PCRC to login with microsoft')
		psi.logger.info('Use command `!!PCRC set_redirect_url <url>` to input the redirected url')
		return user_inputs.get()


def tweaks_pcrc_constants():
	def modify_based_dir(file_path: str) -> str:
		return os.path.join(psi.get_data_folder(), os.path.basename(file_path))

	import pcrc.config as pcrc_config
	from pcrc.connection import pcrc_authentication

	pcrc_config.CONFIG_FILE = modify_based_dir(pcrc_config.CONFIG_FILE)
	pcrc_authentication.SAVED_TOKEN_FILE = modify_based_dir(pcrc_authentication.SAVED_TOKEN_FILE)


def on_load(server: PluginServerInterface, old):
	tweaks_pcrc_constants()
	global pcrc
	pcrc = PcrcClient(input_manager=MCDRInputManager())
	pcrc.logger.set_console_handler(SyncStdoutStreamHandler())
	pcrc.logger.set_console_logging_prefix('PCRC@{}'.format(hex((id(pcrc) >> 16) & (id(pcrc) & 0xFFFF))[2:].rjust(4, '0')))
	register_command(server)

	new_thread('PCRC init')(pcrc.init)()


def register_command(server: PluginServerInterface):
	reload_config(None)

	server.register_command(
		Literal('!!PCRC').
		requires(lambda src: src.has_permission(config.permission_required)).
		on_error(UnknownCommand, lambda: 0, handled=True).
		on_error(UnknownArgument, lambda: 0, handled=True).
		then(Literal('start').runs(start_pcrc)).
		then(Literal('stop').runs(stop_pcrc)).
		then(Literal('reload').runs(reload_config)).
		then(Literal('set_redirect_url').then(GreedyText('url').runs(set_redirect_url)))
	)


def set_redirect_url(source: CommandSource, context: CommandContext):
	user_inputs.put_nowait(context['url'])


def reload_config(source: Optional[CommandSource]):
	global config
	config = psi.load_config_simple('mcdr_config.json', target_class=McdrConfig)
	pcrc.reload_config()
	if source is not None:
		source.reply('PCRC config reloaded')


@new_thread('PCRC Connect')
def start_pcrc(source: CommandSource):
	global source_that_starts_pcrc
	source_that_starts_pcrc = source
	if pcrc.start():
		source.reply('PCRC started')
	else:
		source.reply('PCRC failed to start, check console for more information')
	source_that_starts_pcrc = None


def stop_pcrc(source: CommandSource):
	# for players, the bot is able to handle `!!PCRC stop` command itself
	if source.is_console:
		source.reply('Stopping PCRC')
		pcrc.stop()


def cleanup():
	pcrc_module.pop_pycraft_lib_path()
	pcrc.logger.close_file()
	pcrc.discard()


def on_unload(server: PluginServerInterface):
	if pcrc.is_running():
		pcrc.stop(callback=cleanup)
	else:
		cleanup()


def on_mcdr_stop(server: PluginServerInterface):
	if pcrc.is_running():
		if not pcrc.is_stopping():
			pcrc.stop(block=True)
		for i in range(60 * 10):
			if pcrc.is_running():
				server.logger.info('Waiting for PCRC to stop')
				for j in range(10):
					if pcrc.is_running():
						time.sleep(0.1)
		if pcrc.is_running():
			server.logger.info('PCRC took too long to stop (more than 10min)! Exit anyway')
	cleanup()
