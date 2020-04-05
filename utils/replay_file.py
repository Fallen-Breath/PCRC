import json
import os
import shutil
import time
import zipfile

from . import utils


class ReplayFile:
	def __init__(self, path='./'):
		self.path = path
		self.mods = []
		self.meta_data = {}
		self.markers = []
		if path[-1] not in ['/', '\\']:
			path = path + '/'
		if not os.path.exists(path):
			os.makedirs(path)
		self.file_size = 0
		open('{}recording.tmcpr'.format(self.path), 'w').close()
		self.write_markers()
		self.write_mods()
		self.write_meta_data()

	def create(self, file_name):
		tmcpr = '{}recording.tmcpr'.format(self.path)
		if not os.path.isfile(tmcpr):
			open(tmcpr, 'w').close()
		zipf = zipfile.ZipFile(file_name, 'w', zipfile.ZIP_DEFLATED)

		def add(zipf, name, data=None):
			file_name = '{}{}'.format(self.path, name)
			if data is not None:
				with open(file_name, 'w') as f:
					f.write(data)
			zipf.write(file_name, arcname=name)
			time.sleep(0.01)

		add(zipf, 'markers.json')
		add(zipf, 'mods.json')
		add(zipf, 'metaData.json')
		add(zipf, 'recording.tmcpr.crc32', str(utils.crc32_file(tmcpr)))
		add(zipf, 'recording.tmcpr')
		zipf.close()
		shutil.rmtree(self.path)

	def add_marker(self, time_stamp, pos, name=None):
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

	def set_meta_data(self, meta_data):
		self.meta_data = meta_data
		self.write_meta_data()

	def write(self, data):
		with open('{}recording.tmcpr'.format(self.path), 'ab+') as replay_recording:
			replay_recording.write(data)
		self.file_size += len(data)

	def write_markers(self):
		with open('{}markers.json'.format(self.path), 'w') as markers_file:
			markers_file.write(json.dumps(self.markers))

	def write_mods(self):
		with open('{}mods.json'.format(self.path), 'w') as mods_file:
			mods_file.write(json.dumps({"requiredMods": self.mods}))

	def write_meta_data(self):
		with open('{}metaData.json'.format(self.path), 'w') as meta_data_file:
			meta_data_file.write(json.dumps(self.meta_data))

	def size(self):
		return self.file_size
