from abc import ABC, abstractmethod


class InputManager(ABC):
	@abstractmethod
	def input(self, message: str) -> str:
		raise NotImplementedError()


class StdinInputManager(InputManager):
	def input(self, message: str) -> str:
		return input(message)
