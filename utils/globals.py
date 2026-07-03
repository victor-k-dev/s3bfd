
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import os
from dataclasses import dataclass
from .logger import get_logger
from logging import Formatter
import threading
from multiprocessing import Queue, Manager
from multiprocessing.managers import DictProxy
from hashlib import md5, sha256
	
@dataclass
class Globals:

	manager = Manager()

	s3bfd_prefix_cache = {}

	file_metadata:DictProxy = manager.dict() # [Path,FileMetadata]
	
	invalid_file_metadata:DictProxy = manager.dict() # retry downloading file [Path,FileMetadata]
	parentless_file_metadata:DictProxy = manager.dict() # retry storing metadata [Path,FileMetadata]

	parentless_directory_metadata:DictProxy = manager.dict()

	current_node_id = manager.Value(typecode="i", value=0)

	node_id = 1 # first bucket name/url occupies ID #0
	node_id_semaphore:threading.BoundedSemaphore = threading.BoundedSemaphore(1)

	download_queue:Queue = manager.Queue()
	validation_queue:Queue = manager.Queue()
	storage_queue:Queue = manager.Queue()
	message_queue:Queue = manager.Queue()

	graceful_stop_event = manager.Event()
	immediate_stop_event = manager.Event()

	

	current_tree_id = 0

	hash_functions = {"md5": md5, "sha256": sha256}
	hash_lengths = {32: "md5", 64: "sha256"}
	new_checksum_type = "sha256"
	
	
	logger = get_logger()
	formatter = Formatter(fmt="%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

	thread_multiplier = 2
	cpu_count = os.cpu_count() * thread_multiplier
	request_threads = int(cpu_count/2)
	download_threads = cpu_count - request_threads
	validation_processes = 4

	process_list = []
	
	concurrent_request_tasks = 256
	concurrent_download_tasks = 256
	concurrent_file_tasks = 1024
	request_semaphore = manager.BoundedSemaphore(concurrent_request_tasks)
	download_semaphore = manager.BoundedSemaphore(concurrent_download_tasks)
	files_semaphore = manager.BoundedSemaphore(concurrent_file_tasks)
	writing_to_database_semaphore = manager.BoundedSemaphore(1)
	storage_semaphore = manager.BoundedSemaphore(32)