# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import logging
import re
import traceback
from logging.handlers import RotatingFileHandler, QueueHandler
from queue import Queue
from utils.paths import CurrentPaths
from pathlib import Path

# Typing
from logging import Logger

# TODO: needs rewrite of filtering functions and other improvements
def _init_logger(process_name:str, log_dir:Path = CurrentPaths.log_directory, log_name:str = "main", console_log_level:str = "INFO", file_log_level:str = "INFO", is_gui:bool=False, message_queue:Queue=None) -> Logger:
	try:
		print(f"Setting up logger\nLog Directory: {log_dir}\nFilename: {log_name}\nLogging Level (console): {console_log_level}\nLogging Level (file): {file_log_level}")

		def show_only_file_log_level(record):
			try:
				if re.compile(r"^(?:INFO|DEBUG|WARNING|ERROR|CRITICAL)$").match(file_log_level) is None:
					raise ValueError("invalid log level selected; must be one of: 'INFO', 'DEBUG', 'WARNING', 'ERROR', 'CRITICAL'\ndefaulting to 'INFO'")
				else:
					return record.levelname == file_log_level
			except ValueError as e:
				print(e)
				return record.levelname == "INFO"
		def show_only_console_log_level(record):
			try:
				if re.compile(r"^(?:INFO|DEBUG|WARNING|ERROR|CRITICAL)$").match(console_log_level) is None:
					raise ValueError("invalid log level selected; must be one of: 'INFO', 'DEBUG', 'WARNING', 'ERROR', 'CRITICAL'\ndefaulting to 'INFO'")
				else:
					return record.levelname == console_log_level
			except ValueError as e:
				print(e)
				return record.levelname == "INFO"

		logger = logging.getLogger(process_name)
		logger.setLevel(logging.DEBUG)

		formatter = logging.Formatter(fmt="%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
		
		print("Initializing console handler")
		console_handler = logging.StreamHandler()
		console_handler.setLevel(logging.INFO)
		console_handler.setFormatter(formatter)
		#console_handler.addFilter(show_only_console_log_level)
		logger.addHandler(console_handler)

		if is_gui and message_queue is not None:
			print("Initializing GUI handler")
			gui_handler = QueueHandler(message_queue)
			gui_handler.setLevel(logging.INFO)
			gui_handler.setFormatter(formatter)
			logger.addHandler(gui_handler)

		file_handler = RotatingFileHandler(filename=f"{str(log_dir)}/{log_name}.log", encoding="utf-8", mode="a", maxBytes=4096000, backupCount=1024)
		file_handler.setLevel(logging.DEBUG)
		file_handler.setFormatter(formatter)
		#file_handler.addFilter(show_only_file_log_level)
		logger.addHandler(file_handler)

	except Exception:
		traceback.print_exc()
	return logger

def get_logger() -> Logger:
	return _init_logger("main")