import inspect
from typing import Type, Callable, Any, Optional, Tuple, List

from redbaron import RedBaron, ProxyList, DefNode


def read_class(clazz: Type) -> Tuple[RedBaron, Any]:
	try:
		source = inspect.getsource(clazz)
	except OSError:
		raise OSError('Cannot get source code of class {} from {}'.format(clazz, inspect.getsourcefile(clazz)))
	red = RedBaron(source)
	return red, red[0]


def __get_node(
		red: ProxyList, *,
		node_type: Optional[Type] = None, predicate: Optional[Callable[[Any], bool]] = None,
		ordinal: int = 0,
		error_msg: Optional[str] = None
	) -> Tuple[Any, int]:
	for i, node in enumerate(red.value):
		if node_type is not None and not isinstance(node, node_type):
			continue
		if predicate is not None and not predicate(node):
			continue
		if ordinal == 0:
			return node, i
		else:
			ordinal -= 1
	else:
		raise Exception() if error_msg is None else Exception(error_msg)


def get_node(
		red: ProxyList, *,
		node_type: Optional[Type] = None, predicate: Optional[Callable[[Any], bool]] = None,
		ordinal: int = 0,
		error_msg: Optional[str] = None
	) -> Any:
	return __get_node(red, node_type=node_type, predicate=predicate, ordinal=ordinal, error_msg=error_msg)[0]


def get_node_index(
		red: ProxyList, *,
		node_type: Optional[Type] = None, predicate: Optional[Callable[[Any], bool]] = None,
		ordinal: int = 0,
		error_msg: Optional[str] = None
	) -> int:
	return __get_node(red, node_type=node_type, predicate=predicate, ordinal=ordinal, error_msg=error_msg)[1]


def get_def(red: ProxyList, def_name: str):
	return get_node(red, node_type=DefNode, predicate=lambda n: n.name == def_name, error_msg='Cannot found method {}'.format(def_name))


def insert_nodes(red: ProxyList, index: int, nodes: List):
	for i in range(len(nodes)):
		red.value.insert(index, nodes[len(nodes) - i - 1])
