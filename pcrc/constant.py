import minecraft

Version = '0.12.0-alpha.1'
MilliSecondPerHour = 60 * 60 * 1000
BytePerKB = 1024
BytePerMB = BytePerKB * 1024
MinimumLegalFileSize = 10 * BytePerKB
RecordingFilePath = 'temp_recording/'
RecordingStorageFolder = 'PCRC_recordings/'
ALLOWED_VERSIONS = ['1.12', '1.12.2', '1.14.4', '1.15.2', '1.16.1', '1.16.2', '1.16.3', '1.16.4', '1.17.1', '1.18', '1.18.1']
Map_VersionToProtocol = minecraft.SUPPORTED_MINECRAFT_VERSIONS
Map_ProtocolToVersion = {}
for item in Map_VersionToProtocol.items():
	Map_ProtocolToVersion[item[1]] = item[0]

EntityTypeItem = {
	'1.12': 2,
	'1.12.2': 2,
	'1.14.4': 34,
	'1.15.2': 35,
	'1.16.1': 35,
	'1.16.2': 35,
	'1.16.3': 35,
	'1.16.4': 35,
	'1.17.1': 41,
	'1.18': 41,
	'1.18.1': 41,
}
EntityTypeBat = {
	'1.12': 65,
	'1.12.2': 65,
	'1.14.4': 3,
	'1.15.2': 3,
	'1.16.1': 3,
	'1.16.2': 3,
	'1.16.3': 3,
	'1.16.4': 3,
	'1.17.1': 4,
	'1.18': 4,
	'1.18.1': 4,
}
EntityTypePhantom = {
	'1.12': -1,
	'1.12.2': -1,
	'1.14.4': 97,
	'1.15.2': 98,
	'1.16.1': 58,
	'1.16.2': 58,
	'1.16.3': 58,
	'1.16.4': 58,
	'1.17.1': 63,
	'1.18': 63,
	'1.18.1': 63,
}

FILE_FORMAT_VERSION_DICT = {
	'1.12': '6',
	'1.12.2': '9',
	'1.14.4': '14',
	'1.15.2': '14',
	'1.16.1': '14',
	'1.16.2': '14',
	'1.16.3': '14',
	'1.16.4': '14',
	'1.17.1': '14',
	'1.18': '14',
	'1.18.1': '14',
}

ENTITY_PACKETS = [
	# 1.12+
	'Entity',
	'Entity Relative Move',
	'Entity Look And Relative Move',
	'Entity Look',
	'Entity Teleport'
	'Entity Status',
	'Remove Entity Effect',
	'Entity Head Look',
	'Entity Metadata',
	'Entity Velocity',
	'Entity Equipment',
	'Entity Teleport',
	'Entity Properties',
	'Entity Effect',

	# 1.14+
	'Entity Sound Effect',
	'Entity Movement',
	'Entity Rotation',
	'Entity Position and Rotation',
	'Entity Position',
	'Entity Animation (clientbound)',
]

