import yaml
import os

FileSuffix = '.yml'


class Translation:
	def __init__(self, lang_dir):
		files = os.listdir(lang_dir)
		self.translations = {}
		for file in files:
			if file.endswith(FileSuffix):
				lang = file.rstrip(FileSuffix)
				with open(lang_dir + file, encoding='utf8') as f:
					self.translations[lang] = yaml.load(f, Loader=yaml.FullLoader)

	@property
	def languages(self):
		return self.translations.keys()

	def has_language(self, language):
		return language in self.languages

	def translate(self, text, language):
		return self.translations[language][text]

