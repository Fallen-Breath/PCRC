from typing import Dict, Collection

from ruamel.yaml import YAML

from pcrc.utils import resources_util

LANGUAGES = ['en_us', 'zh_cn']


class Translation:
	def __init__(self):
		self.translations: Dict[str, Dict[str, str]] = {}
		for lang in LANGUAGES:
			lang_file_path = 'resources/lang/{}.yml'.format(lang)
			self.translations[lang] = YAML().load(resources_util.get_data(lang_file_path))

	@property
	def languages(self) -> Collection[str]:
		return self.translations.keys()

	def has_language(self, language: str) -> bool:
		return language in self.languages

	def translate(self, key: str, language: str) -> str:
		return self.translations[language][key]

