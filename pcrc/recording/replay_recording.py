import json
import os
import shutil
import zipfile
import zlib
from typing import List, Optional

from minecraft.networking.types import PositionAndLook
from pcrc import constant
from pcrc.utils import file_util


class ReplayRecording:
	def __init__(self, temp_file_dir: str):
		self.temp_file_dir = temp_file_dir
		self.mods = []
		self.meta_data = {}
		self.markers = []
		self.__file_size = 0

		if os.path.exists(temp_file_dir):
			shutil.rmtree(temp_file_dir)
		os.makedirs(temp_file_dir)
		file_util.touch_file(self.recording_file_path, forced=True)
		# these 3 files are not used in PCRC recording
		self.write_markers()
		self.write_mods()
		self.write_meta_data()

	def __get_file(self, file_name: str) -> str:
		return os.path.join(self.temp_file_dir, file_name)

	@property
	def size(self):
		return self.__file_size

	@property
	def recording_file_path(self) -> str:
		return self.__get_file('recording.tmcpr')

	def create_replay_recording(self, target_file_path: str):
		file_util.touch_directory(os.path.dirname(target_file_path))
		file_util.touch_file(self.recording_file_path)

		zipf = zipfile.ZipFile(target_file_path, 'w', zipfile.ZIP_DEFLATED)

		def add(name: str, data: Optional[str] = None):
			existed_file_name = os.path.join(self.temp_file_dir, name)
			if data is not None:
				with open(existed_file_name, 'w', encoding='utf8') as f:
					f.write(data)
			zipf.write(existed_file_name, arcname=name)

		add('markers.json')
		add('mods.json')
		add('metaData.json')
		add('recording.tmcpr.crc32', str(crc32_file(self.recording_file_path)))
		add('recording.tmcpr')
		zipf.close()
		shutil.rmtree(self.temp_file_dir)

	def add_marker(self, time_stamp: int, pos: PositionAndLook, name=None):
		marker = {
			'realTimestamp': time_stamp,
			'value': {
				'position': {
					'x': pos.x,
					'y': pos.y,
					'z': pos.z,
					# seems that replay mod switches these two values, idk y
					'yaw': pos.pitch,
					'pitch': pos.yaw,
					'roll': 0.0
				}
			}
		}
		if name is not None:
			marker['value']['name'] = name
		self.markers.append(marker)
		self.write_markers()
		return marker

	def pop_marker(self, index):
		ret = self.markers.pop(index - 1)
		self.write_markers()
		return ret

	def set_meta_data(self, server_name: str, duration: int, date: int, mc_version: str, protocol: int, player_uuids: List[str]):
		file_format_version = \
			6 if mc_version == '1.12' else \
			9 if mc_version == '1.12.2' else \
			14
		self.meta_data = {
			'singleplayer': False,
			'serverName': server_name,
			'duration': duration,
			'date': date,
			'mcversion': mc_version,
			'fileFormat': 'MCPR',
			'fileFormatVersion': file_format_version,
			'protocol': protocol,
			'generator': 'PCRC',
			'selfId': -1,
			'players': player_uuids
		}
		self.write_meta_data()

	def write_recording_content(self, content: bytes):
		with open(self.recording_file_path, 'ab+') as file_handler:
			file_handler.write(content)
		self.__file_size += len(content)

	def write_markers(self):
		with open(self.__get_file('markers.json'), 'w') as markers_file_handler:
			markers_file_handler.write(json.dumps(self.markers))

	def write_mods(self):
		with open(self.__get_file('mods.json'), 'w') as mods_file_handler:
			mods_file_handler.write(json.dumps({"requiredMods": self.mods}))

	def write_meta_data(self):
		with open(self.__get_file('metaData.json'), 'w') as meta_data_file_handler:
			meta_data_file_handler.write(json.dumps(self.meta_data))


def crc32_file(file_name: str) -> int:
	BUFFER_SIZE = constant.BYTE_PER_MB
	crc = 0
	with open(file_name, 'rb') as handler:
		while True:
			buffer = handler.read(BUFFER_SIZE)
			if len(buffer) == 0:
				break
			crc = zlib.crc32(buffer, crc)
	return crc & 0xFFFFFFFF
