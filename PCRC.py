import time
import traceback
from typing import Optional

from pcrc import constant
from pcrc.pcrc_impl import PcrcImpl

pcrc = PcrcImpl()
logger = pcrc.logger


def on_start_up():
	logger.info('PCRC {} starting up'.format(constant.Version))
	logger.info('PCRC is open source, u can find it here: https://github.com/Fallen-Breath/PCRC')
	logger.info('PCRC is still in development, it may not work well')
	logger.info('Enter "start" to start PCRC')


def is_working():
	return pcrc.recorder.is_recording()


def is_stopped():
	return pcrc.is_fully_stopped()


def start():
	global pcrc
	if is_stopped():
		logger.info('Creating new PCRC recorder')
		pcrc.start()
		logger.info('Recorder started, success = {}'.format(1))
	else:
		logger.warning('Recorder is running, ignore')


def stop():
	global pcrc
	if is_working():
		pcrc.stop(by_user=True)
		logger.info('Recorder stopped')
	else:
		logger.info('Recorder is not running, ignore')


def main():
	global pcrc
	while True:
		try:
			text = input()
			if text != '':
				logger.info('Processing command "{}"'.format(text))
				if text == "start":
					start()
				elif text == "stop":
					stop()
				elif text == "restart":
					stop()
					start()
				elif text == 'exit':
					break
				elif text.startswith('say '):
					pcrc.chat(text[4:])
		except (KeyboardInterrupt, SystemExit):
			break
		except:
			logger.exception('Error handling console input')
	try:
		if is_working():
			logger.info('Stopping recorder before exit')
			stop()
		else:
			logger.info('Waiting for recorder to stop before exit')
			while not pcrc.is_fully_stopped():
				time.sleep(0.1)
	except (KeyboardInterrupt, SystemExit):
		logger.info('Forced to stop')
		return
	except:
		logger.exception('Error waiting for recorder to stop')

	logger.info('Exited')


if __name__ == "__main__":
	on_start_up()
	main()
