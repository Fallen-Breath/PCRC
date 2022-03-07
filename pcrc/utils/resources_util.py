"""
Resource files / Inner modules getters
Don't run it directly
"""
import pkgutil
from typing import Optional

__all__ = [
	'ROOT_PACKAGE',
	'get_data',
]
from pcrc import constant

ROOT_PACKAGE = constant.PACKAGE_NAME


def __get_path(path: str) -> str:
	if path.startswith('/'):
		path = path[1:]
	return path


def get_data(path: str) -> Optional[bytes]:
	return pkgutil.get_data(ROOT_PACKAGE, __get_path(path))


if __name__ == '__main__':
	# Don't run it directly
	pass
