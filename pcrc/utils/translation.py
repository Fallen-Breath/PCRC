from ruamel.yaml import YAML
import os

from pcrc.utils import file_util

FILE_SUFFIX = '.yml'
LANG_DIR = 'lang'


class Translation:
	def __init__(self):
		self.translations = {}
		for file_path in file_util.list_file_with_suffix(LANG_DIR, FILE_SUFFIX):
			lang = os.path.basename(file_path)[:-len(FILE_SUFFIX)]
			with open(file_path, encoding='utf8') as f:
				self.translations[lang] = YAML().load(f)

	@property
	def languages(self):
		return self.translations.keys()

	def has_language(self, language):
		return language in self.languages

	def translate(self, key: str, language: str) -> str:
		return self.translations[language][key]

