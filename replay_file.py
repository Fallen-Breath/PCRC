import json
import os
import zipfile

import utils


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
		open('{}recording.tmcpr'.format(self.path), 'w').close()
		self.file_size = 0

	def create(self, file_name):
		tmcpr = '{}recording.tmcpr'.format(self.path)
		if not os.path.isfile(tmcpr):
			open(tmcpr, 'w').close()
		zipf = zipfile.ZipFile(file_name, 'w', zipfile.ZIP_DEFLATED)

		def add(zipf, name, data=None):
			utils.addFile(zipf, '{}{}'.format(self.path, name), arcname=name, fileData=data)

		add(zipf, 'markers.json', json.dumps(self.markers))
		add(zipf, 'mods.json', json.dumps({"requiredMods": self.mods}))
		add(zipf, 'metaData.json', json.dumps(self.meta_data))
		add(zipf, 'recording.tmcpr.crc32', str(utils.crc32_file(tmcpr)))
		add(zipf, 'recording.tmcpr')
		zipf.close()

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
		return marker

	def write(self, data):
		with open('{}recording.tmcpr'.format(self.path), 'ab+') as replay_recording:
			replay_recording.write(data)
		self.file_size += len(data)

	def size(self):
		return self.file_size
