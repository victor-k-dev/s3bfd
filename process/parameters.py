# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from dataclasses import dataclass
from utils.globals import Globals
from pathlib import Path

@dataclass
class Parameters:
	tree_id:int = None
	url:str = None
	s3_url:str = None
	prefix:Path = None
	region:str = None
	total_threads:int = Globals.cpu_count
	requests_threads:int = Globals.request_threads
	download_threads:int = Globals.download_threads
	validation_processes:int = Globals.validation_processes
	cache_only = False
	skip_validation = False
	no_gui = False

	single_file_path:str = None
	single_file_url:str = None

	multi_file_directory:Path = None
	multi_file_base_url:str = None

	is_running:bool = False

	process_in_memory:bool = False
	save_to_disk:bool = True
	delete_after_validation:bool = False
