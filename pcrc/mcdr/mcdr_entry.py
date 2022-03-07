import os
import time
from typing import Optional

from mcdreforged.api.decorator import new_thread
from mcdreforged.command.builder.nodes.basic import Literal
from mcdreforged.command.command_source import CommandSource
from mcdreforged.plugin.server_interface import PluginServerInterface, ServerInterface
from mcdreforged.utils.logger import SyncStdoutStreamHandler

import pcrc as pcrc_module
import pcrc.config as pcrc_config
from pcrc.mcdr.mcdr_config import McdrConfig
from pcrc.pcrc_client import PcrcClient

psi = ServerInterface.get_instance().as_plugin_server_interface()
config: McdrConfig
pcrc: PcrcClient


def on_load(server: PluginServerInterface, old):
	pcrc_config.CONFIG_FILE = os.path.join(psi.get_data_folder(), 'config.json')
	global pcrc
	pcrc = PcrcClient()
	pcrc.logger.set_console_handler(SyncStdoutStreamHandler())
	pcrc.logger.set_console_logging_prefix('PCRC@{}'.format(hex((id(pcrc) >> 16) & (id(pcrc) & 0xFFFF))[2:].rjust(4, '0')))
	register_command(server)


def register_command(server: PluginServerInterface):
	reload_config(None)

	server.register_command(
		Literal('!!PCRC').
		requires(lambda src: src.has_permission(config.permission_required)).
		then(Literal('start').runs(start_pcrc)).
		then(Literal('stop').runs(stop_pcrc)).
		then(Literal('reload').runs(reload_config))
	)


def reload_config(source: Optional[CommandSource]):
	global config
	config = psi.load_config_simple('mcdr_config.json', target_class=McdrConfig)
	if source is not None:
		source.reply('Config reloaded')


@new_thread('PCRC Connect')
def start_pcrc(source: CommandSource):
	if pcrc.start():
		source.reply('PCRC started')
	else:
		source.reply('PCRC failed to start, check console for more information')


def stop_pcrc(source: CommandSource):
	source.reply('Stopping PCRC')
	pcrc.stop(by_user=True, callback=lambda: source.reply('PCRC stopped'))


def on_unload(server: PluginServerInterface):
	def on_pcrc_stop():
		pcrc_module.pop_pycraft_lib_path()
		pcrc.logger.close_file()

	if pcrc.is_running():
		pcrc.stop(by_user=True, callback=on_pcrc_stop)
	else:
		on_pcrc_stop()


def on_mcdr_stop(server: PluginServerInterface):
	if pcrc.is_running():
		for i in range(60 * 10):
			if pcrc.is_running():
				server.logger.info('Waiting for PCRC to stop')
				for j in range(10):
					if pcrc.is_running():
						time.sleep(0.1)
		if pcrc.is_running():
			server.logger.info('PCRC took too long to stop (more than 10min)! Exit anyway')
