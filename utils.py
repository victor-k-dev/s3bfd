# MIT License
# 
# Copyright (c) 2026 victor-k-dev
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import logging
from queue import Queue
import re
import requests
import traceback
from dataclasses import dataclass
from logging.handlers import RotatingFileHandler, QueueHandler
from time import sleep

# Typing imports
from logging import Logger
from pathlib import Path


@dataclass(frozen=True)
class ReturnCodes:
	SUCCESS: int = 0
	FAILED: int = -1
	FAILED_EXISTS: int = -2
	FAILED_TRY_NEXT: int = -3
	FAILED_NO_INTERNET: int = -4
	FAILED_UNKNOWN: int = -5


def init_logger(process_name:str, log_dir:str = ".", log_name:str = "main", console_log_level:str = "INFO", file_log_level:str = "INFO", is_gui:bool=False, message_queue:Queue=None) -> Logger:
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

		file_handler = RotatingFileHandler(filename=f"{log_dir}/{log_name}.log", encoding="utf-8", mode="a", maxBytes=4096000, backupCount=1024)
		file_handler.setLevel(logging.DEBUG)
		file_handler.setFormatter(formatter)
		#file_handler.addFilter(show_only_file_log_level)
		logger.addHandler(file_handler)

	except Exception:
		traceback.print_exc()
	return logger

def download_files(task_args:tuple[str,str,Path], retries: int = 5, delay: int = 60) -> tuple[int,str,str,Path]:

	url, filename, download_dir, checksum, id = task_args


	download_dir.mkdir(parents=True,exist_ok=True)


	while True:
		try:
			print(f"Downloading {filename} at {url}...")
			r = requests.get(url)
			r.raise_for_status()
			print(f"{filename} downloaded.")

			with open(f"{download_dir}/{filename}", "wb") as f:
				f.write(r.content)
			break
		except requests.HTTPError as he_error:
			print(f"An HTTP error occurred during the download process:\n{he_error}")	
			if retries > 0:
				print(f"Retrying in {delay} seconds. {retries} attempt(s) remaining...")
				retries -= 1
				sleep(delay)
				continue
			elif retries <= 0:
				print(f"out of retries; ceasing download attempt for {filename} as {url}")
				return ReturnCodes.FAILED, url, filename, download_dir
		except requests.ConnectionError as ce_error:
			print(f"A ConnectionError: {ce_error}")
			if retries > 0:
				print(f"Retrying in {delay} seconds. {retries} attempt(s) remaining...")
				retries -= 1
				sleep(delay)
				continue
			elif retries <= 0:
				print(f"out of retries; ceasing download attempt for {filename} as {url}")
				return ReturnCodes.FAILED, url, filename, download_dir
		except Exception as error:
			print(f"An unknown error occurred during the download process:\n{error}")
			print(traceback.format_exc())
			return ReturnCodes.FAILED_UNKNOWN, url, filename, download_dir
		
	return ReturnCodes.SUCCESS, url, filename, download_dir, checksum, id