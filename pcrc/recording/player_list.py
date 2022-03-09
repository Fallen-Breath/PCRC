from typing import Dict, List, TYPE_CHECKING, Optional, Tuple

from minecraft.networking.packets import PlayerListItemPacket
from minecraft.networking.types import GameMode

if TYPE_CHECKING:
	from pcrc.recording.recorder import Recorder


class PlayerInfo:
	name: str
	properties: List[PlayerListItemPacket.PlayerProperty]
	game_mode: int
	ping: int
	display_name: Optional[str]

	def __init__(self):
		pass

	def is_spectator(self) -> bool:
		return self.game_mode == GameMode.SPECTATOR

	def __lt__(self, other):
		if not isinstance(other, type(self)):
			return False
		if self.is_spectator() and not other.is_spectator():
			return False
		elif not self.is_spectator() and other.is_spectator():
			return True
		else:
			return self.name.lower() < other.name.lower()


class PlayerListManager:
	def __init__(self, recorder: 'Recorder'):
		self.recorder: 'Recorder' = recorder
		self.logger = recorder.logger
		# uuid -> player info
		self.__player_map: Dict[str, PlayerInfo] = {}

	def reset(self):
		self.__player_map.clear()

	def on_packet(self, packet: PlayerListItemPacket):
		for action in packet.actions:
			player_uuid = action.uuid
			if isinstance(action, PlayerListItemPacket.AddPlayerAction):
				info = PlayerInfo()
				info.name = action.name
				info.properties = action.properties
				info.game_mode = action.gamemode
				info.ping = action.ping
				info.display_name = action.display_name
				self.__player_map[player_uuid] = info
			else:
				info = self.__player_map.get(player_uuid)
				if info is not None:
					if isinstance(action, PlayerListItemPacket.UpdateGameModeAction):
						info.game_mode = action.gamemode
					elif isinstance(action, PlayerListItemPacket.UpdateLatencyAction):
						info.ping = action.ping
					elif isinstance(action, PlayerListItemPacket.UpdateDisplayNameAction):
						info.display_name = action.display_name
					elif isinstance(action, PlayerListItemPacket.RemovePlayerAction):
						self.__player_map.pop(player_uuid)
				else:
					self.logger.warning('Unknown player uuid {} from {}'.format(player_uuid, packet))

	def get_game_mode(self, player_uuid: str) -> Optional[int]:
		info = self.__player_map.get(player_uuid)
		if info is None:
			return None
		return info.game_mode

	def dump_player_list(self) -> str:
		data: Dict[PlayerInfo, Tuple[str, str]] = {}
		for uuid, info in self.__player_map.items():
			if info.display_name is not None:
				name = '{} ({})'.format(info.display_name, info.name)
			else:
				name = info.name
			data[info] = (name, '{} {}ms'.format(GameMode.name_from_value(info.game_mode).lower(), info.ping))
		lines: List[Tuple[str, str]] = list(map(data.get, sorted(data.keys())))
		max_name_length = max(map(lambda l: len(l[0]), lines))
		return '\n'.join(map(lambda l: '{}{} | {}'.format(l[0], ' ' * (max_name_length - len(l[0])), l[1]), lines))
