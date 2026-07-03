# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from .schema import BucketInfo
from pathlib import Path

class FileMetadata:
	def __init__(self, node_id:int, parent_id:int, name:str, path:Path, size_bytes:int, last_modified, old_checksum:str, url:str, tree_id:int, tree_name:str):
		self.node_id = node_id
		self.tree_id:int = tree_id
		self.tree_name:str = tree_name
		self.parent_id:int = parent_id
		self.name:str = name
		self.path:Path = path
		self.is_directory = False
		self.size_bytes = size_bytes
		self.last_modified = last_modified
		self.downloaded_at = None
		self.old_checksum = old_checksum
		self.old_checksum_type = None
		self.new_checksum = None
		self.new_checksum_type = None
		self.passed_validation = None

		self.url = url
		self.local_file_path:Path = None
		self.bytes = None
		self.id = None

	def set_local_file_path(self, local_file_path:Path) -> None:
		self.local_file_path = local_file_path
	
	def to_bucket_info(self) -> BucketInfo:
		if self.downloaded_at:
			return BucketInfo(
				node_id=self.node_id,
				tree_id=self.tree_id,
				tree_name=self.tree_name,
				parent_id=self.parent_id,
				name=self.name,
				path=str(self.path),
				is_directory=self.is_directory,
				size_bytes=self.size_bytes,
				last_modified=self.last_modified,
				downloaded_at=self.downloaded_at,
				original_checksum=self.old_checksum,
				original_checksum_type=self.old_checksum_type,
				checksum=self.new_checksum,
				checksum_type=self.new_checksum_type,
				validation_passed=self.passed_validation,
			)
		else:
			return BucketInfo(
				node_id=self.node_id,
				tree_id=self.tree_id,
				tree_name=self.tree_name,
				parent_id=self.parent_id,
				name=self.name,
				path=str(self.path),
				is_directory=self.is_directory,
				size_bytes=self.size_bytes,
				last_modified=self.last_modified,
				original_checksum=self.old_checksum,
				original_checksum_type=self.old_checksum_type,
				checksum=self.new_checksum,
				checksum_type=self.new_checksum_type,
				validation_passed=self.passed_validation,
			)
		
class DirectoryMetadata:
	def __init__(self, node_id, parent_id, name, path, prefix, tree_id, tree_name):
		self.node_id = node_id
		self.tree_id = tree_id
		self.tree_name = tree_name
		self.parent_id = parent_id
		self.name = name
		self.path = path
		self.prefix = prefix
		self.is_directory = True

	def to_bucket_info(self) -> BucketInfo:
		return BucketInfo(
			node_id=self.node_id,
			tree_id=self.tree_id,
			tree_name=self.tree_name,
			parent_id=self.parent_id,
			name=self.name,
			path=str(self.path),
			is_directory=self.is_directory,
		)