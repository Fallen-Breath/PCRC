import json
import zipfile

import utils


class ReplayFile:
	def __init__(self, file_name=None, tmcpr_name=None, meta_data=None, markers=None, mods=None):
		self.file_name = file_name
		self.tmcpr_name = tmcpr_name if tmcpr_name is not None else utils.RecordingFileName
		self.meta_data = meta_data
		self.markers = markers if markers is not None else []
		self.mods = mods if mods is not None else []

	def set_file_name(self, file_name):
		self.file_name = file_name

	def set_tmcpr_name(self, tmcpr_name):
		self.tmcpr_name = tmcpr_name

	def set_meta_data(self, meta_data):
		self.meta_data = meta_data

	def set_markers(self, markers):
		self.markers = markers

	def set_mods(self, mods):
		self.mods = mods

	def create(self):
		zipf = zipfile.ZipFile(self.file_name, 'w', zipfile.ZIP_DEFLATED)
		utils.addFile(zipf, 'markers.json', fileData=json.dumps(self.markers))
		utils.addFile(zipf, 'mods.json', fileData=json.dumps({"requiredMods": self.mods}))
		utils.addFile(zipf, 'metaData.json', fileData=json.dumps(self.meta_data))
		utils.addFile(zipf, '{}.crc32'.format(utils.RecordingFileName), fileData=str(utils.crc32f(self.tmcpr_name)))
		utils.addFile(zipf, self.tmcpr_name, arcname=utils.RecordingFileName)
		zipf.close()
