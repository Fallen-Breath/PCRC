from typing import Dict, Collection

from ruamel.yaml import YAML

from pcrc.utils import resources_util

LANGUAGES = ['en_us', 'zh_cn']


class Translation:
	def __init__(self):
		self.translations: Dict[str, Dict[str, str]] = {}
		for lang in LANGUAGES:
			lang_file_path = 'resources/lang/{}.yml'.format(lang)
			self.translations[lang] = self.__build_translation(YAML().load(resources_util.get_data(lang_file_path)))
		l1 = list(self.translations['en_us'].keys())
		l2 = list(self.translations['zh_cn'].keys())
		assert len(l1) == len(l2)
		for i in range(len(l1)):
			if l1[i] != l2[i]:
				print(l1[i], l2[i])
		assert l1 == l2

	@staticmethod
	def __build_translation(yml: dict) -> dict:
		def __build(obj: dict, path: str):
			for key, value in obj.items():
				child_path = key if len(path) == 0 else (path if key == '.' else path + '.' + key)
				if isinstance(value, str):
					translation[child_path] = value
				elif isinstance(value, dict):
					__build(value, child_path)
				else:
					raise TypeError()
		translation = {}
		__build(yml, '')
		return translation

	@property
	def languages(self) -> Collection[str]:
		return self.translations.keys()

	def has_language(self, language: str) -> bool:
		return language in self.languages

	def translate(self, key: str, language: str) -> str:
		return self.translations[language][key]

