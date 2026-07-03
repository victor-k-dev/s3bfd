# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from .constants import Constants as ct
from dataclasses import dataclass
from pathlib import Path

from typing import Literal

@dataclass(frozen=True)
class DefaultPaths:
	HOME_DIRECTORY = Path.home()
	DEFAULT_DATA_DIRECTORY = HOME_DIRECTORY.joinpath(".s3bfd")
	DEFAULT_LOG_DIRECTORY = DEFAULT_DATA_DIRECTORY.joinpath("logs")
	DEFAULT_DATABASE_DIRECTORY = DEFAULT_DATA_DIRECTORY.joinpath("database")
	DEFAULT_PREFIX_CACHE_DIRECTORY = DEFAULT_DATA_DIRECTORY.joinpath("prefix_cache")
	DEFAULT_BUFFER_DIRECTORY = DEFAULT_DATA_DIRECTORY.joinpath("buffer")
	DEFAULT_DOWNLOAD_DIRECTORY = DEFAULT_DATA_DIRECTORY.joinpath("downloads")
	
	DEFAULT_DATABASE_FILE_PATH = DEFAULT_DATABASE_DIRECTORY.joinpath(ct.DATABASE_NAME)
	DEFAULT_PREFIX_CACHE_FILE_PATH = DEFAULT_PREFIX_CACHE_DIRECTORY.joinpath(ct.PREFIX_CACHE_NAME)
	
@dataclass()
class CurrentPaths:
	home_directory = DefaultPaths.HOME_DIRECTORY
	data_directory = DefaultPaths.DEFAULT_DATA_DIRECTORY
	log_directory = DefaultPaths.DEFAULT_LOG_DIRECTORY
	database_directory = DefaultPaths.DEFAULT_DATABASE_DIRECTORY
	prefix_cache_directory = DefaultPaths.DEFAULT_PREFIX_CACHE_DIRECTORY
	buffer_directory = DefaultPaths.DEFAULT_BUFFER_DIRECTORY
	download_directory = DefaultPaths.DEFAULT_DOWNLOAD_DIRECTORY
	database_file_path = DefaultPaths.DEFAULT_DATABASE_FILE_PATH
	prefix_cache_file_path = DefaultPaths.DEFAULT_PREFIX_CACHE_FILE_PATH
	

	def update(self, path:str|Path, type:Literal["file","directory"], dir:Literal["home","data","database","prefix","buffer","download"]|None=None, file:Literal["database","prefix"]|None=None):
		if isinstance(path, str):
			path = Path(path)

		if type == "file":
			if file == "database":
				self.database_file_path = path
			elif file == "prefix":
				self.prefix_cache_file_path = path
		elif type == "directory":
			if dir == "home":
				self.home_directory = path
			elif dir == "data":
				self.data_directory = path
			elif dir == "database":
				self.database_directory = path
			elif dir == "prefix":
				self.prefix_cache_directory = path
			elif dir == "buffer":
				self.buffer_directory = path
			elif dir == "download":
				self.download_directory = path












