# coding: utf8

import os
import time
import zlib

from . import constant


def get_path(file):
	for path in constant.ROOT_PATH:
		p = os.path.join(path, file)
		if os.path.isdir(p) or os.path.isfile(p):
			return p


def crc32_file(fn):
	BUFFER_SIZE = constant.BytePerMB
	crc = 0
	with open(fn, 'rb') as f:
		while True:
			buffer = f.read(BUFFER_SIZE)
			if len(buffer) == 0:
				break
			crc = zlib.crc32(buffer, crc)
	return crc & 0xffffffff


def get_meta_data(server_name, duration, date, mcversion, protocol, player_uuids):
	file_format_version_dict = {
		'1.12': '6',
		'1.12.2': '9',
		'1.14.4': '14',
		'1.15.2': '14',
	}
	if player_uuids is None:
		player_uuids = []
	file_format_version = file_format_version_dict[mcversion]
	meta_data = {
		'singleplayer': False,
		'serverName': server_name,
		'duration': duration,
		'date': date,
		'mcversion': mcversion,
		'fileFormat': 'MCPR',
		'fileFormatVersion': file_format_version,
		'protocol': protocol,
		'generator': 'PCRC',
		'selfId': -1,
		'players': player_uuids
	}
	return meta_data


# convert file size to MB
def convert_file_size_MB(file_size):
	return format(file_size / 1024 / 1024, '.2f')


# convert file size to KB
def convert_file_size_KB(file_size):
	return format(file_size / 1024, '.2f')


def getMilliTime():
	return int(time.time() * 1000)


def format_vector(vec, f='.2f'):
	return '({}, {}, {})'.format(format(vec.x, f), format(vec.y, f), format(vec.z, f))


# Returns a string like h:m for given millis
def convert_millis(millis):
	seconds = int(millis / 1000) % 60
	minutes = int(millis / (1000 * 60)) % 60
	hours = int(millis / (1000 * 60 * 60))
	if seconds < 10:
		seconds = '0' + str(seconds)
	if minutes < 10:
		minutes = '0' + str(minutes)
	if hours < 10:
		hours = '0' + str(hours)
	return str(hours) + ':' + str(minutes) + ':' + str(seconds)
