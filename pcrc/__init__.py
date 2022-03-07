import os
import sys

pycraft_lib_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'pycraft')


def append_pycraft_lib_path():
	if pycraft_lib_path not in sys.path:
		sys.path.append(pycraft_lib_path)
		# print('Appended {}'.format(pycraft_lib_path))


def pop_pycraft_lib_path():
	try:
		while True:
			sys.path.remove(pycraft_lib_path)
	except ValueError:
		pass


def __patch():
	from pcrc.connection.patch import patch_pycraft
	patch_pycraft()


append_pycraft_lib_path()
__patch()

