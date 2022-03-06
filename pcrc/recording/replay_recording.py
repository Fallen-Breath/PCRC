import json
import os
import shutil
import zipfile
import zlib
from typing import List, Optional

from minecraft.networking.types import PositionAndLook
from pcrc import constant


class ReplayRecording:
	def __init__(self, path: str):
		self.path = path
		self.mods = []
		self.meta_data = {}
		self.markers = []
		if not os.path.exists(path):
			os.makedirs(path)
		self.__file_size = 0

		self.__touch_recording_file()
		# these 3 files are not used in PCRC recording
		self.write_markers()
		self.write_mods()
		self.write_meta_data()

	def __get_file(self, file_name: str) -> str:
		return os.path.join(self.path, file_name)

	@property
	def size(self):
		return self.__file_size

	@property
	def recording_file(self) -> str:
		return self.__get_file('recording.tmcpr')

	def __touch_recording_file(self):
		with open(self.recording_file, 'w'):
			pass

	def create_replay_recording(self, file_name: str):
		tmcpr = self.recording_file
		if not os.path.isfile(tmcpr):
			self.__touch_recording_file()

		zipf = zipfile.ZipFile(file_name, 'w', zipfile.ZIP_DEFLATED)

		def add(name: str, data: Optional[str] = None):
			existed_file_name = os.path.join(self.path, name)
			if data is not None:
				with open(existed_file_name, 'w', encoding='utf8') as f:
					f.write(data)
			zipf.write(existed_file_name, arcname=name)

		add('markers.json')
		add('mods.json')
		add('metaData.json')
		add('recording.tmcpr.crc32', str(crc32_file(tmcpr)))
		add('recording.tmcpr')
		zipf.close()
		shutil.rmtree(self.path)

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
		with open(self.recording_file, 'ab+') as file_handler:
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
	BUFFER_SIZE = constant.BytePerMB
	crc = 0
	with open(file_name, 'rb') as handler:
		while True:
			buffer = handler.read(BUFFER_SIZE)
			if len(buffer) == 0:
				break
			crc = zlib.crc32(buffer, crc)
	return crc & 0xffffffff
