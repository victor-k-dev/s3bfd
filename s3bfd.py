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

import argparse
import hashlib
import heapq
import pickle
import requests
import traceback
import threading
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from queue import Empty, LifoQueue, Queue
from utils import ReturnCodes, init_logger, download_files
from xml.etree import ElementTree as ET
from sqlalchemy import Integer, ForeignKey, Boolean, DateTime, create_engine, select, update, func
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship
from time import sleep
from typing import Any, Optional
from tqdm import tqdm

DATABASE_NAME = "s3bfd_cache.db"
PREFIX_CACHE_NAME = "s3bfd_prefix_cache.pkl"
BUCKET_INFO_TABLE_NAME = "bucket_info"
UNIQUE_BUCKETS_TABLE_NAME = "unique_buckets"
REQUESTS_BUFFER_FILE_BASE = "r-buffer"
DIRS_BUFFER_FILE_BASE = "d-buffer"
FILES_BUFFER_FILE_BASE = "f-buffer"
REQUESTS_BUFFER_SIZE = 32786
DIRS_BUFFER_SIZE = 1024
FILES_BUFFER_SIZE = 1024
DEFAULT_DATA_DIRECTORY = "~/.s3bfd/data"
DEFAULT_LOG_DIRECTORY = f"{DEFAULT_DATA_DIRECTORY}/logs"
DEFAULT_DATABASE_DIRECTORY = f"{DEFAULT_DATA_DIRECTORY}/database"
DEFAULT_PREFIX_CACHE_DIRECTORY = f"{DEFAULT_DATA_DIRECTORY}/prefix_cache"
DEFAULT_BUFFER_DIRECTORY = f"{DEFAULT_DATA_DIRECTORY}/buffer"
DEFAULT_DOWNLOAD_DIRECTORY = f"{DEFAULT_DATA_DIRECTORY}/downloads"

# Globals
request_semaphore = threading.Semaphore(1024)
files_semaphore = threading.Semaphore(1024)
validation_semaphore = threading.Semaphore(64)
s3bfd_prefix_cache = {} # { "dir_path": {"id": ..., "tree_id": ..., "tree_name": ..., "parent_id": ..., "name": ..., "path": ..., "is_directory": ...,}, ...}
global_is_debug_enabled = False

@dataclass(order=True)
class PrioritizedItem:
	priority: int
	item: Any=field(compare=False)

class Base(DeclarativeBase):
	pass

class UniqueBuckets(Base):
	__tablename__ = UNIQUE_BUCKETS_TABLE_NAME
	id: Mapped[int] = mapped_column(primary_key=True)
	bucket_name: Mapped[str] = mapped_column(nullable=False)
	bucket_id: Mapped[int] = mapped_column(nullable=False)

class BucketInfo(Base):
	__tablename__ = BUCKET_INFO_TABLE_NAME

	id: Mapped[int] = mapped_column(primary_key=True)
	tree_id: Mapped[int] = mapped_column(nullable=False)
	tree_name: Mapped[str] = mapped_column(nullable=False) # Set to bucket_url
	parent_id: Mapped[Optional[int]] = mapped_column(ForeignKey("bucket_info.id"), nullable=True)
	name: Mapped[str] = mapped_column(nullable=False)
	path: Mapped[str] = mapped_column(nullable=False)
	is_directory: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
	size_bytes: Mapped[Optional[int]] = mapped_column(Integer, nullable=False, default=0)
	last_modified: Mapped[datetime] = mapped_column(DateTime, nullable=True) # Not set for directories
	downloaded_at: Mapped[datetime] = mapped_column(DateTime, nullable=True) # Only set for files
	original_checksum_type: Mapped[str] = mapped_column(nullable=True)
	original_checksum: Mapped[str] = mapped_column(nullable=True)
	checksum_type: Mapped[str] = mapped_column(default="sha256", nullable=False)
	checksum: Mapped[str] = mapped_column(nullable=True)
	validation_passed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

	parent = relationship("BucketInfo", remote_side=[id], back_populates="children")
	children = relationship("BucketInfo", back_populates="parent")

# TODO: use regular Queue/LifoQueue without manager; multiprocessing is not used
from multiprocessing.managers import BaseManager
class QueueManager(BaseManager):
	pass

QueueManager.register('LifoQueue', LifoQueue)
QueueManager.register('FifoQueue', Queue)

is_s3_connection_successful = False
base_url = ""

def get_s3_metadata(bucket_url, prefix="", region=None, sep=".", max_pages=None) -> tuple[list[dict],list[dict]]:

	global is_s3_connection_successful
	global base_url

	if not base_url:
		base_url = f"https://s3{sep}{region}.amazonaws.com/{bucket_url}"
	else:
		pass
	
	headers = {
		'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:149.0) Gecko/20100101 Firefox/149.0',
		'Accept': '*/*',
		'Origin': f'{bucket_url}',
		'Referer': f'{bucket_url}',
		'Sec-Fetch-Dest': 'empty',
		'Sec-Fetch-Mode': 'cors',
		'Sec-Fetch-Site': 'cross-site'
	}
	
	all_files = []
	all_directories = []
	marker = None
	page_count = 0
	max_retries = 5
	retries = 0
	delay = 60
	
	while (max_pages is None) or (page_count < max_pages):
		if early_stop_event.is_set():
			return [], []

		request_params = {
			'delimiter': '/',
			'prefix': prefix
		}
		
		if marker:
			request_params['marker'] = marker
			
		try:
			is_fetched_data = False
			retries = 0
			response = None
			while retries <= max_retries:
				if early_stop_event.is_set():
					return [], []
				try:
					status_code = None
					response = requests.get(base_url, params=request_params, headers=headers)
					status_code = response.status_code
					response.raise_for_status()
					is_fetched_data = True
					is_s3_connection_successful = True
					break
				except Exception:
					if (status_code is not None) and (status_code == 404) and (not is_s3_connection_successful):
						logger.warning(f"(get_s3_metadata) S3 bucket not found at {base_url}; attempting https://{bucket_url} in {delay} seconds")
						base_url = f"https://{bucket_url}"
					elif (status_code is not None):
						logger.error(f"(get_s3_metadata) failed to fetch S3 data ({status_code}); retrying in {delay} seconds\n", exc_info=True)
					else:
						logger.error(f"(get_s3_metadata) failed to fetch S3 data (response code unavailable); retrying in {delay} seconds\n", exc_info=True)
					sleep(delay)
					retries += 1
					continue
			if not is_fetched_data:
				raise Exception(f"failed to fetch S3 data; no more retries remain")
			
			try:
				root = ET.fromstring(response.content)
			except Exception:
				logger.error(f"(get_s3_metadata) error occurred during XML parsing for page {page_count}:\n", exc_info=True)
				logger.error(f"(get_s3_metadata) XML response: {root}")
				break
				
			files = []
			dirs = []
			
			for content in root.findall('.//{http://s3.amazonaws.com/doc/2006-03-01/}Contents'):
				key = content.find('{http://s3.amazonaws.com/doc/2006-03-01/}Key').text
				last_modified = content.find('{http://s3.amazonaws.com/doc/2006-03-01/}LastModified').text
				size = content.find('{http://s3.amazonaws.com/doc/2006-03-01/}Size').text
				etag = content.find('{http://s3.amazonaws.com/doc/2006-03-01/}ETag').text
				etag = etag.strip("\"")

				files.append({
					'Key': key, # file path
					'LastModified': last_modified,
					'Size': size, # in bytes
					'ETag': etag, # checksum
					'Type': 'file'
				})
			
			for prefix_elem in root.findall('.//{http://s3.amazonaws.com/doc/2006-03-01/}CommonPrefixes'):
				prefix_key = prefix_elem.find('{http://s3.amazonaws.com/doc/2006-03-01/}Prefix').text
				dirs.append({
					'Key': prefix_key,
					'LastModified': '',
					'Size': '',
					'Type': 'directory'
				})
			
			all_files.extend(files)
			all_directories.extend(dirs)
			
			is_truncated = root.find('.//{http://s3.amazonaws.com/doc/2006-03-01/}IsTruncated')
			if is_truncated is not None and is_truncated.text == 'true':
				#logger.debug("found 'IsTruncated'")
				next_marker = root.find('.//{http://s3.amazonaws.com/doc/2006-03-01/}NextMarker')
				if next_marker is not None:
					#logger.debug("found 'NextMarker'")
					marker = next_marker.text
				else:
					if files:
						marker = files[-1]['Key']
					else:
						#logger.debug("no files found; no 'NextMarker' found")
						break
			else:
				#logger.debug("no 'IsTruncated' found")
				break
				
			page_count += 1
			sleep(0.1) # TODO: consider making adjustable
			
		except Exception:
			logger.error(f"(get_s3_metadata) Error on page {page_count}:", exc_info=True)
			break
	#logger.debug(f"(s3) all directories {all_directories}")
	#logger.debug(f"(s3) all files {all_files}")
	return all_files, all_directories

def bytes_to_human_readable(size_in_bytes):
	"""Convert bytes to human readable format"""
	size_in_bytes = int(size_in_bytes)
	units = [' B', ' kB', ' MB', ' GB']
	i = 0
	while size_in_bytes >= 1024 and i < len(units) - 1:
		size_in_bytes /= 1024
		i += 1
	return f"{size_in_bytes:.1f}{units[i]}"



def request_bucket_metadata(task_args:tuple):

	#logger.debug("(request_bucket_metadata) starting")
	bucket_url, dir, region, engine = task_args
	prefix = dir['Key']

	logger.debug(f"(request_bucket_metadata) checking dir: {dir}")
	files, dirs = get_s3_metadata(bucket_url, prefix, region, max_pages=10)

	return files, dirs

def store_bucket_metadata(task_args:tuple) -> None|list[list[dict],list[dict]]:
	#logger.debug("(store_bucket_metadata) starting")
	records, record_type, bucket_url, engine, current_tree_id = task_args
	is_parent_found = False
	#logger.debug(f"(store_bucket_metadata) received {type(records)} containing {records}")
	if record_type == "files" and records:
		#logger.debug("(store_bucket_metadata) received files")

		path = str(Path(records[0]['Key']).parent) + "/"
		logger.debug(f"(store_bucket_metadata) looking for node with path '{path}'")
		if path in s3bfd_prefix_cache:
			is_parent_found = True
		else:
			logger.warning(f"(store_bucket_metadata) node with path '{path}' does not exist in the directory cache")
		if is_parent_found:
			try:
				#logger.debug("found files")
				#logger.debug(f"(store_bucket_metadata) files: {records}")
				with Session(engine) as session:
					new_records = []
					for file in records:
						file_name = Path(file['Key']).name
						last_modified = datetime.fromisoformat(file['LastModified'])
						new_records.append(
							BucketInfo(
								tree_id=current_tree_id,
								tree_name=bucket_url,
								parent_id=s3bfd_prefix_cache[path]["parent_id"],
								name=file_name,
								path=file['Key'],
								size_bytes=int(file['Size']),
								last_modified=last_modified,
								original_checksum=file['ETag']
							)
						)
						#logger.debug(f"(store_metadata) new file records: {new_records}")
					session.add_all(new_records)
					session.commit()
			except Exception:
				logger.error("(store_bucket_metadata) Error when writing file metadata:\n", exc_info=True)
	if record_type == "dirs" and records:
		#logger.debug(f"(store_bucket_metadata) received dirs:\n{records}")

		path = str(Path(records[0]['Key']).parent) + "/"
		logger.debug(f"(store_bucket_metadata) looking for node with path '{path}'")
		if path in s3bfd_prefix_cache:
			is_parent_found = True
		else:
			logger.warning(f"(store_bucket_metadata) node with path '{path}' does not exist in the directory cache")
		if is_parent_found:
			try:
				#logger.debug("found dirs")
				#logger.debug(f"(store_bucket_metadata) dirs: {records}")
				with Session(engine) as session:
					new_records = []
					for dir in records:
						dir_name = Path(dir['Key']).name
						new_records.append(
							BucketInfo(
								tree_id=current_tree_id,
								tree_name=bucket_url,
								parent_id=s3bfd_prefix_cache[path]["parent_id"],
								name=dir_name,
								path=dir['Key'],
								is_directory=True,
							)
						)
					#logger.debug("(store_metadata) new dir records:\n")
					#for nr in new_records:
					#	logger.debug(f"{nr.path}\n")
					session.add_all(new_records)
					session.commit()
			except Exception:
				logger.error("(store_bucket_metadata) Error when writing directory metadata to database:\n", exc_info=True)

			try:
				for dir in records:
					dir_parent_path = str(Path(dir['Key']).parent) + "/"
					dir_parent_id = s3bfd_prefix_cache[dir_parent_path]["parent_id"]
					s3bfd_prefix_cache[dir['Key']] = {"tree_id": current_tree_id, "tree_name": bucket_url, "parent_id": dir_parent_id, "name": Path(dir['Key']).name}

			except Exception:
				logger.error("(store_bucket_metadata) Error when writing directory metadata to prefix cache:\n", exc_info=True)

	if not is_parent_found:
		logger.warning(f"(store_bucket_metadata) unable to store {record_type}; couldn't find parent node, or another error occurred")
		return records

	else:
		return None

def get_bucket_metadata(task_args:tuple[str, str, str, Any, int, LifoQueue, Queue, str]) -> bool:
	bucket_url, prefix, prefix_root, region, engine, max_workers, out_queue, pbar_queue, buffer_directory = task_args

	current_tree_id = None
	current_root = None

	logger.info("(get_bucket_metadata) starting")

	with Session(engine) as session:
		try:
			logger.debug("(get_bucket_metadata) checking for pre-existing root node/dir in database")
			statement = select(UniqueBuckets).where(UniqueBuckets.bucket_name == bucket_url)
			try:
				unique_bucket_result = session.execute(statement).scalar_one()
				logger.debug(f"unique_bucket_result: {unique_bucket_result}")
				logger.debug(f"{bucket_url} exists in database")
				statement = select(BucketInfo).where(BucketInfo.tree_name == bucket_url, BucketInfo.parent_id == None)
				current_root = session.execute(statement).scalar_one()
				logger.debug(f"retrieved root node for {bucket_url}: {current_root}")
			except NoResultFound:
				current_max_bucket_id = session.execute(select(UniqueBuckets.bucket_id).order_by(UniqueBuckets.bucket_id.desc()).limit(1)).scalars().first()
				if current_max_bucket_id is not None:
					new_max_bucket_id = current_max_bucket_id + 1
				else:
					new_max_bucket_id = 0

				current_tree_id = new_max_bucket_id

				new_unique_bucket = UniqueBuckets(
					bucket_name=bucket_url,
					bucket_id=new_max_bucket_id
				)
				session.add(new_unique_bucket)
				logger.debug(f"new unique bucket: {new_unique_bucket}")
				if prefix_root:
					logger.debug(f"prefix_root exists: {prefix_root}")
					
					is_root_node = True
					previous_node = None
					new_records = []

					for part in prefix.split("/"):
						if not part:
							continue
						if is_root_node:
							s3bfd_prefix_cache[prefix_root] = {"tree_id": current_tree_id, "tree_name": bucket_url, "parent_id": None, "name": part, "path": prefix_root}
							node = BucketInfo(
								tree_id=current_tree_id,
								tree_name=bucket_url,
								parent_id=None,
								name=part,
								path=prefix_root,
								is_directory=True
							)
							is_root_node = False
							previous_node = deepcopy(node)
							logger.info(f"(get_bucket_metadata) previous node: {previous_node}")
							new_records.append(node)
						else:
							logger.info(f"(get_bucket_metadata) previous node: {previous_node}")
							s3bfd_prefix_cache[f"{previous_node.path}{part}/"] = {"tree_id": current_tree_id, "tree_name": bucket_url, "parent_id": previous_node.id, "name": part, "path": f"{previous_node.path}{part}/"}
							node = BucketInfo(
								tree_id=current_tree_id,
								tree_name=bucket_url,
								parent_id=previous_node.id,
								name=part,
								path=f"{previous_node.path}{part}/",
								is_directory=True,
							)
							previous_node = deepcopy(node)
							new_records.append(node)
					session.add_all(new_records)
					session.commit()
				else: # Need to get name of bucket root folder
					# TODO: finish implementation
					logger.debug(f"prefix_root does not exist: {prefix_root}")
					files, dirs = get_s3_metadata(bucket_url, prefix, max_pages=1)
					if files:
						prefix_root = files[0]['Key'].split("/")[0]
						# TODO: if prefix root starts with "/" raise error ?
					elif dirs:
						prefix_root = dirs[0]['Key'].split("/")[0]
						# TODO: if prefix root starts with "/" raise error ?
					else:
						raise RuntimeError(f"no files/directories found at {bucket_url}")
					root = BucketInfo(
						tree_id=new_max_bucket_id, # tree_id == UniqueBuckets.bucket_id
						tree_name=bucket_url,
						parent_id=None,
						name="/",
						path=prefix_root,
						is_directory=True,
					)
					current_root = deepcopy(root)
		except Exception:
			logger.error("(get_bucket_metadata) Error occurred when getting/creating root node in database:\n", exc_info=True)
			return False

	try:
		
		internal_requests_buffer = []
		internal_dirs_buffer = []
		internal_files_buffer = []
		is_r_buffer_full = False

		external_requests_buffer = []
		r_buffer_files = []
		f_buffer_files = []
		r_buffer_file_count = 0
		f_buffer_file_count = 0

		is_remaining_requests = True
		

		if pbar_queue is None:
			internal_r_buffer_tbar = tqdm(total=0, desc="Internal R-Buffer")
			internal_d_buffer_tbar = tqdm(total=0, desc="Internal D-Buffer")
			internal_f_buffer_tbar = tqdm(total=0, desc="Internal F-Buffer")
			external_r_buffer_tbar = tqdm(total=0, desc="External R-Buffer")
		
		with ThreadPoolExecutor(max_workers=max_workers) as executor:
			logger.info("(get_bucket_metadata) start of thread pool")
			request_futures:list[Future] = []
			request_futures.append(executor.submit(request_bucket_metadata, (bucket_url, {'Key': "data/"}, region, engine)))
			entry_count = 0
			while True:
				if early_stop_event.is_set():
					executor.shutdown(wait=True, cancel_futures=True)
					return True

				logger.info("(get_bucket_metadata) waiting for metadata request tasks to complete")
				#logger.debug(f"request futures: {request_futures}")
				for future in as_completed(request_futures):
					#logger.debug(f"(get_bucket_metadata) current internal_requests_buffer:\n{internal_requests_buffer}")
					#logger.info("completed request task")
					result_files, result_dirs = future.result()
					request_semaphore.release()
					if result_dirs:
						#logger.debug(f"(get_bucket_metadata) result dirs: {result_dirs}")
						is_remaining_requests = True
						if not is_r_buffer_full:
							internal_requests_buffer.extend(result_dirs)
							if pbar_queue is None:
								internal_r_buffer_tbar.set_description(f"Internal R-Buffer: {len(internal_requests_buffer)}")
							else:
								pbar_queue.put_nowait(("r_buffer", len(internal_requests_buffer)))
						else:
							external_requests_buffer.extend(result_dirs)
							if pbar_queue is None:
								external_r_buffer_tbar.set_description(f"External R-Buffer: {len(internal_requests_buffer)}")
					
						priority = len(result_dirs[0]['Key'].split()) - 1
						heapq.heappush(internal_dirs_buffer, (priority, entry_count, result_dirs))
						if pbar_queue is None:
							internal_d_buffer_tbar.set_description(f"Internal D-Buffer: {len(internal_dirs_buffer)}")
						else:
							pbar_queue.put_nowait(("d_buffer", len(internal_dirs_buffer)))
						
						entry_count += 1
					if result_files:

						internal_files_buffer.append(result_files)
						if pbar_queue is None:
							internal_f_buffer_tbar.set_description(f"Internal F-Buffer: {len(internal_files_buffer)}")
						else:
							pbar_queue.put_nowait(("f_buffer", len(internal_files_buffer)))

					if (len(external_requests_buffer) >= REQUESTS_BUFFER_SIZE):
						r_buffer_files.append(f"{buffer_directory}/{REQUESTS_BUFFER_FILE_BASE}-{r_buffer_file_count}.pkl")
						with open(f"{buffer_directory}/{REQUESTS_BUFFER_FILE_BASE}-{r_buffer_file_count}.pkl", "ab") as f:
							f.write(pickle.dumps(external_requests_buffer))
							external_requests_buffer.clear()
							if pbar_queue is None:
								external_r_buffer_tbar.set_description(f"External R-Buffer: {len(external_requests_buffer)}")
							r_buffer_file_count += 1

					if (len(internal_files_buffer) >= FILES_BUFFER_SIZE):
						f_buffer_files.append(f"{buffer_directory}/{FILES_BUFFER_FILE_BASE}-{f_buffer_file_count}.pkl")
						with open(f"{buffer_directory}/{FILES_BUFFER_FILE_BASE}-{f_buffer_file_count}.pkl", "ab") as f:
							pickle.dump(internal_files_buffer, f)
							internal_files_buffer.clear()
							if pbar_queue is None:
								internal_f_buffer_tbar.set_description(f"Internal F-Buffer: {len(internal_files_buffer)}")
							else:
								pbar_queue.put_nowait(("f_buffer", len(internal_files_buffer)))
							f_buffer_file_count += 1

				logger.info("(get_bucket_metadata) finished waiting for metadata requests")
				# Clear out finished tasks from request_futures
				request_futures.clear()

				logger.info("(get_bucket_metadata) storing dir metadata")
				while internal_dirs_buffer:
					#logger.debug(f"dir heap (before): {internal_dirs_buffer}")
					_, _, dirs = heapq.heappop(internal_dirs_buffer)
					#logger.debug(f"dir heap (after): {internal_dirs_buffer}")
					storage_result = store_bucket_metadata((dirs, "dirs", bucket_url, engine, current_tree_id))
					if pbar_queue is None:
						internal_d_buffer_tbar.set_description(f"Internal D-Buffer: {len(internal_dirs_buffer)}")
					else:
						pbar_queue.put_nowait(("d_buffer", len(internal_dirs_buffer)))
					if storage_result is not None:
						logger.warning("not handling failed dir storage tasks")
						logger.debug(storage_result)
						sleep(1)
							
				logger.info("(get_bucket_metadata) finished storing dir metadata")

				if (not internal_requests_buffer):
					logger.info("(get_bucket_metadata) no more dirs to explore")
					is_remaining_requests = False
				else:
					logger.info("(get_bucket_metadata) submitting metadata request tasks")
					# Clear out finished tasks
					while internal_requests_buffer:
						if request_semaphore.acquire(blocking=False):
							
							request_futures.append(executor.submit(request_bucket_metadata, (bucket_url, internal_requests_buffer.pop(), region, engine)))
							
							if pbar_queue is None:
								internal_r_buffer_tbar.set_description(f"Internal R-Buffer: {len(internal_requests_buffer)}")
							else:
								pbar_queue.put_nowait(("r_buffer", len(internal_requests_buffer)))
							
							if (not internal_requests_buffer) and external_requests_buffer:
								internal_requests_buffer.extend(external_requests_buffer)
								if pbar_queue is None:
									internal_r_buffer_tbar.set_description(f"Internal R-Buffer: {len(internal_requests_buffer)}")
								else:
									pbar_queue.put_nowait(("r_buffer", len(internal_requests_buffer)))
								external_requests_buffer.clear()
								if pbar_queue is None:
									external_r_buffer_tbar.set_description(f"External R-Buffer: {len(internal_requests_buffer)}")
								is_r_buffer_full = False
								break
							elif (not internal_requests_buffer) and (not external_requests_buffer) and r_buffer_files:
								r_buffer_file = r_buffer_files.pop()
								with open(r_buffer_file, "rb") as f:
									internal_requests_buffer = pickle.load(f)
									if pbar_queue is None:
										internal_r_buffer_tbar.set_description(f"Internal R-Buffer: {len(internal_requests_buffer)}")
									else:
										pbar_queue.put_nowait(("r_buffer", len(internal_requests_buffer)))
								Path(r_buffer_file).unlink(missing_ok=True)
								is_r_buffer_full = False
								break
							else:
								is_r_buffer_full = False
						else:
							break
					logger.info("(get_bucket_metadata) finished submitting metadata request tasks")

				logger.info("(get_bucket_metadata) sending file storage tasks to file_storage_thread")
				while internal_files_buffer:
					if files_semaphore.acquire(blocking=False) or (not is_remaining_requests):
						out_queue.put_nowait((internal_files_buffer.pop(), bucket_url, current_tree_id))
						if pbar_queue is None:
							internal_f_buffer_tbar.set_description(f"Internal F-Buffer: {len(internal_files_buffer)}")
						else:
							pbar_queue.put_nowait(("f_buffer", len(internal_files_buffer)))

						if (not internal_files_buffer) and f_buffer_files:
							while f_buffer_files:
								f_buffer_file = f_buffer_files.pop()
								with open(f_buffer_file, "rb") as f:
									internal_files_buffer = pickle.load(f)
									if pbar_queue is None:
										internal_f_buffer_tbar.set_description(f"Internal F-Buffer: {len(internal_files_buffer)}")
									else:
										pbar_queue.put_nowait(("f_buffer", len(internal_files_buffer)))
								Path(f_buffer_file).unlink(missing_ok=True)
						#is_f_buffer_full = False
					else:
						break

				logger.info("(get_bucket_metadata) finished sending file storage tasks to file_storage_thread")
				
				if (not is_remaining_requests):
					logger.info("(get_bucket_metadata) sending stop signal to file_storage_process")
					out_queue.put_nowait(None)
					logger.info("(get_bucket_metadata) no more tasks; stopping")
					return

				sleep(1.0)
	except KeyboardInterrupt:
		logger.info("Process stopped via KeyboardInterrupt")
		return True
	except Exception:
		logger.error("(get_bucket_data) Error occurred while requesting/storing bucket metadata:\n", exc_info=True)
		return False

def file_storage_thread(task_args:tuple[int, Any, LifoQueue]) -> bool:
	max_workers, engine, in_queue = task_args
	is_operating = True
	try:		
		with ThreadPoolExecutor(max_workers=max_workers) as executor:
			while is_operating:
				if early_stop_event.is_set():
					executor.shutdown(wait=True, cancel_futures=True)
					return True
				try:
					task = in_queue.get_nowait()
					if task is None:
						is_operating = False
						continue
					files, bucket_url, current_tree_id = task
					future = executor.submit(store_bucket_metadata, (files, "files", bucket_url, engine, current_tree_id ))
					#logger.info("(file_storage_thread) storing file metadata")
					file_storage_result = future.result()
					if file_storage_result is not None:
						logger.warning("not handling failed file storage tasks")
						logger.debug(file_storage_result)
						sleep(1)
					files_semaphore.release()
					#logger.info("(file_storage_thread) finished storing file metadata")
				except Empty:
					sleep(0.1)
			executor.shutdown(wait=True)
		logger.info("(file_storage_thread) told to stop by get_bucket_metadata; stopping thread")
	except Exception:
		logger.error("(file_storage_thread) Error:\n", exc_info=True)
		return False
	return True

# TODO: add ability to download only files within specified prefixes/directories
def download_bucket_files(task_args:tuple[str,Any,int,Queue,list[str], str, str]) -> bool:
	try:
	
		logger.info("(download_bucket_files) starting")
		bucket_url, engine, max_workers, out_queue, file_type_filter, prefix, download_parent_directory = task_args
		offset = 0
		limit = 1024
		total_file_count = None
		total_file_size = 0

		base_url = f"https://{bucket_url}/"
		try:
			with Session(engine) as session:
				logger.info("(download_bucket_files) counting number of files in database (this could take a while)...")
				if file_type_filter:
					statement = select(func.count()).select_from(BucketInfo).where(BucketInfo.is_directory == False, ~BucketInfo.name.iendswith('.checksum'))#.limit(limit).offset(offset).order_by(BucketInfo.id)
				else:
					statement = select(func.count()).select_from(BucketInfo).where(BucketInfo.is_directory == False)#.limit(limit).offset(offset).order_by(BucketInfo.id)
				total_file_count = session.execute(statement).scalar()
				if total_file_count is None:
					raise ValueError("no files found in database")
				else:
					logger.info(f"(download_bucket_files) total file count: {total_file_count}")
				logger.info("(download_bucket_files) calculating total size of files to download (this could take a while)...")
				if file_type_filter:
					statement = select(func.sum(BucketInfo.size_bytes)).where(BucketInfo.is_directory == False, ~BucketInfo.name.iendswith('.checksum'))#.limit(limit).offset(offset).order_by(BucketInfo.id)
				else:
					statement = select(func.sum(BucketInfo.size_bytes)).where(BucketInfo.is_directory == False)#.limit(limit).offset(offset).order_by(BucketInfo.id)
				total_file_size = session.execute(statement).scalar()
				if total_file_size is None:
					raise ValueError(f"failed to sum file sizes, as {statement} returned {total_file_size}")
				logger.info(f"(download_bucket_files) total size of all files: {bytes_to_human_readable(total_file_size)}")

		except Exception:
			logger.error("(download_bucket_files) An error occurred while getting file count/sizes from the database:\n", exc_info=True)
			return False
		
		offset = 0

		# TODO: add prompt requesting user permission to download files (mention total size of all files to download)

		with ThreadPoolExecutor(max_workers=max_workers) as executor:
			while offset < total_file_count:
				if early_stop_event.is_set():
					executor.shutdown(wait=True, cancel_futures=True)
					return True
				download_results = []
				validation_tasks = []

				files = None
				try:
					with Session(engine) as session:
						if file_type_filter:
							statement = select(BucketInfo).where(BucketInfo.is_directory==False, ~BucketInfo.name.iendswith(".checksum")).limit(limit).offset(offset).order_by(BucketInfo.id)
						else:
							statement = select(BucketInfo).where(BucketInfo.is_directory==False).limit(limit).offset(offset).order_by(BucketInfo.id)
						files = session.execute(statement).scalars().all()
						offset += limit	
				except Exception:
					logger.error("(download_bucket_files) An error occurred while fetching file info from the database:\n", exc_info=True)
					return False

				for file in files:
					download_url = f"{base_url}{file.path}"
					download_directory = Path(f"{download_parent_directory}/{bucket_url}/{str(Path(file.path).parent)}/")
					if download_directory.joinpath(file.name).exists():
						logger.info(f"(download_bucket_files) {file.name} was already downloaded; skipping...")
						continue
					download_results.append(executor.submit(download_files, (download_url, file.name, download_directory, file.original_checksum, file.id)))
				if not download_results:
					logger.info("(download_bucket_files) no files to download")
					# TODO: add proper handling of skipping file downloading
				else:					
					for future in as_completed(download_results):
						return_code, url, filename, download_directory, original_checksum, id = future.result()
						if return_code == ReturnCodes.SUCCESS:
							validation_tasks.append((filename, download_directory, original_checksum, id))
						else:
							logger.error(f"(download_bucket_files) An error occurred during the download process:\nURL: {url}\nFilename: {filename}\nDownload Directory{download_directory}")
				out_queue.put_nowait(validation_tasks)
			logger.info("(download_bucket_files) finished downloading files; sending stop signal to validation thread")
			out_queue.put_nowait(None)
		return True
	except Exception:
		logger.error("(download_bucket_files) Error: ", exc_info=True)
		return False
	
def validate_bucket_files(task_args:tuple[int, Any, Queue]):
	logger.info("(validate_bucket_files) starting")
	max_workers, engine, in_queue = task_args
	is_operating = True
	hash_functions = {"md5": hashlib.md5, "sha256": hashlib.sha256}

	def validate_file(task_args:tuple[dict, list[tuple[str,Path,str,int]]]) -> tuple[bool, str, str]: # Success/Fail, original_checksum_type
		hash_functions, validation_tasks = task_args
		validation_results = []

		# Guess checksum type by length
		for filename, download_directory, original_checksum, record_id in validation_tasks:
			if len(original_checksum) == 32:
				original_checksum_type = "md5"
			elif len(original_checksum) == 64:
				original_checksum_type = "sha256"
			else:
				logger.warning(f"(validate_file) unknown checksum type: {original_checksum}, length: {len(original_checksum)}; skipping validation")
				validation_results.append((False, None, None, record_id))

			with open(f"{download_directory}/{filename}", "rb") as f:
				file_data = f.read()
				file_hash = hash_functions[original_checksum_type](file_data).hexdigest()
				if file_hash == original_checksum:
					logger.debug(f"(validate_file) sucessfully validated file '{filename}':\noriginal checksum: {original_checksum}, calculated checksum: {file_hash}")
					logger.debug(f"(validate_file) checksum type was {original_checksum_type}")
				else:
					logger.warning(f"(validate_file) failed to validate file '{filename}':\noriginal checksum: {original_checksum}, calculated checksum: {file_hash}")
					validation_results.append((False, None, original_checksum_type, record_id))

				new_checksum = 	hash_functions['sha256'](file_data).hexdigest()
				validation_results.append((True, new_checksum, original_checksum_type, record_id))

		if validation_results:
			return validation_results
	try:		
		while is_operating:
			if early_stop_event.is_set():
				break
			try:
				validation_tasks = in_queue.get_nowait()
				if validation_tasks is None:
					is_operating = False
					continue
	
				validation_results = validate_file((hash_functions, validation_tasks))
				update_vals = []
				for validation_result, original_checksum_type, new_checksum, returned_record_id in validation_results:
					update_vals.append({"id": returned_record_id, "original_checksum_type": original_checksum_type, "checksum": new_checksum, "validation_passed": validation_result})
					
				with Session(engine) as session:
					session.execute(update(BucketInfo), update_vals)
					session.commit()

			except Empty:
				sleep(0.1)
			
		logger.info("(validate_bucket_files) told to stop by download_bucket_files; stopping thread")
	except Exception:
		logger.error("(validate_bucket_files) Error:\n", exc_info=True)
		return False
	return True

def run_s3bfd(task_args:dict[str, Any]|None=None):
		
	is_started_from_gui = False
	
	bucket_url = None
	prefix = None
	region = None
	threads = None
	data_directory = None
	log_directory = None
	database_directory = None
	prefix_cache_directory = None
	buffer_directory = None
	console_log_level = None
	file_log_level = None
	is_debug_enabled = False
	debug_enable_caching = False
	debug_enable_downloading = False
	debug_enable_validation = False
	debug_enable_save_prefix_cache = False
	debug_enable_load_prefix_cache = False
	debug_max_file_downloads = None
	log_message_queue:Queue = None
	pbar_queue:Queue = None
	is_running_event = None
	global early_stop_event
	early_stop_event = None

	process_types = {
		"cache_download_validate": 0,
		"cache_download": 1,
		"download_validate": 2,
		"cache_only": 3,
		"download_only": 4
	}
	
	prefix_root = None
	
	try:
		if task_args is not None: # started from GUI
			print(f"Started from GUI with arguments:\n{task_args}, type '{type(task_args)}'")
			is_started_from_gui = True
			bucket_url = task_args["bucket_url"]
			prefix = task_args["prefix"] if not None else ""
			region = task_args["region"]
			threads = task_args["threads"]
			data_directory = task_args["data_directory"]
			log_directory = task_args["log_directory"]
			database_directory = task_args["database_directory"]
			prefix_cache_directory = task_args["prefix_cache_directory"]
			buffer_directory = task_args["buffer_directory"]
			download_directory = task_args["download_directory"]
			console_log_level = task_args["console_log_level"]
			file_log_level = task_args["file_log_level"]
			process_type = process_types[task_args["process_type"]]
			is_debug_enabled = task_args["is_debug_enabled"]
			debug_enable_caching = task_args["debug_enable_caching"]
			debug_enable_downloading = task_args["debug_enable_downloading"]
			debug_enable_validation = task_args["debug_enable_validation"]
			debug_enable_save_prefix_cache = task_args["debug_enable_save_prefix_cache"]
			debug_enable_load_prefix_cache = task_args["debug_enable_load_prefix_cache"]
			debug_max_file_downloads = task_args["debug_max_file_downloads"]
			log_message_queue = task_args["log_message_queue"]
			pbar_queue = task_args["pbar_queue"]
			is_running_event = task_args["is_running_event"]
			early_stop_event = task_args["early_stop_event"]

			if prefix is None:
				prefix = ""
			if prefix.startswith("/"):
				raise ValueError(f"prefix '{prefix}' cannot start with '/'")
			prefix_parts = prefix.split("/")
			prefix_root = prefix_parts[0] + "/"

			Path(data_directory).mkdir(exist_ok=True)
			Path(log_directory).mkdir(exist_ok=True)
			Path(database_directory).mkdir(exist_ok=True)
			Path(prefix_cache_directory).mkdir(exist_ok=True)
			Path(buffer_directory).mkdir(exist_ok=True)
			Path(download_directory).mkdir(exist_ok=True)

		else: # started via terminal

			parser = argparse.ArgumentParser(
								prog="S3 Bucket File Downloader (s3bfd)",
								description="Download files from S3 buckets",
								allow_abbrev=False)
			parser.add_argument("bucket_url", type=str, help="S3 bucket URL/name")
			parser.add_argument("prefix", type=str, help="S3 bucket prefix")
			parser.add_argument("region", type=str, help="Either an AWS region (e.g. us-east-1) or the front-end website URL")
			parser.add_argument("-t", "--threads", type=int, default=4, help="Number of threads to use")
			parser.add_argument("-p", "--process-type", type=str, default="cache_only", choices=("cache_download_validate", "cache_download", "cache_only")) # TODO: add support for download_validate and download_only
			parser.add_argument("-D", "--data-dir", type=str, default=DEFAULT_DATA_DIRECTORY)
			parser.add_argument("-L", "--log-dir", type=str, default=DEFAULT_LOG_DIRECTORY, help="Path to the log directory; defaults to the current working directory")
			parser.add_argument("-B", "--database-dir", type=str, default=DEFAULT_DATABASE_DIRECTORY)
			parser.add_argument("-P", "--prefix-cache_dir", type=str, default=DEFAULT_PREFIX_CACHE_DIRECTORY)
			parser.add_argument("-O", "--download-dir", type=str, default=DEFAULT_DOWNLOAD_DIRECTORY)
			parser.add_argument("-c", "--console-log-level", type=str, default="INFO", choices=("DEBUG","INFO","WARNING","ERROR","CRITICAL"), help="")
			parser.add_argument("-f", "--file-log-level", type=str, default="WARNING",  choices=("DEBUG","INFO","WARNING","ERROR","CRITICAL"), help="")

			# DEBUG OPTIONS
			parser.add_argument("--debug-enabled", action="store_true")
			parser.add_argument("--debug-enable-caching", action="store_true")
			parser.add_argument("--debug-enable-downloading", action="store_true")
			parser.add_argument("--debug-enable-validation", action="store_true")
			parser.add_argument("--debug-max-file-downloads", type=int, default=0, help="Maximum number of files to download; defaults to '0', meaning no limit")
			parser.add_argument("--debug-clear-files-at-startup", action="store_true")
			parser.add_argument("--debug-enable-save-prefix-cache", action="store_true")
			parser.add_argument("--debug-enable-load-prefix-cache", action="store_true")
			args = parser.parse_args()

			is_started_from_gui = False
			bucket_url = args.bucket_url
			if args.prefix is None:
				parser.exit(ReturnCodes.FAILED, message="prefix must be specified")
			else:
				prefix = args.prefix
				if prefix.startswith("/"):
					parser.exit(ReturnCodes.FAILED, message="prefix cannot start with '/'")
				prefix_parts = prefix.split("/")
				prefix_root = prefix_parts[0] + "/"

			if args.region is None:
				parser.exit(ReturnCodes.FAILED, message=f"region must be specified")
			else:
				region = args.region
			threads = args.threads
			process_type = process_types[args.process_type]
			data_directory = args.data_dir
			log_directory = args.log_dir
			database_directory = args.database_dir
			prefix_cache_directory = args.prefix_cache_dir
			console_log_level = args.console_log_level
			file_log_level = args.file_log_level
			is_debug_enabled = args.debug_enabled
			debug_enable_caching = args.debug_enable_caching
			debug_enable_downloading = args.debug_enable_downloading
			debug_enable_validation = args.debug_enable_validation
			debug_enable_save_prefix_cache = args.debug_enable_save_prefix_cache
			debug_enable_load_prefix_cache = args.debug_enable_load_prefix_cache
			# TODO: split into: clear database, clear logs, clear prefix cache, clear downloads, clear everything
			debug_clear_files_at_startup = args.debug_clear_files_at_startup 

			Path(data_directory).mkdir(exist_ok=True)
			Path(log_directory).mkdir(exist_ok=True)
			Path(database_directory).mkdir(exist_ok=True)
			Path(prefix_cache_directory).mkdir(exist_ok=True)
			Path(buffer_directory).mkdir(exist_ok=True)
			Path(download_directory).mkdir(exist_ok=True)

			print(f"Running via terminal with arguments:\n{args}")

		global logger
		logger = init_logger(__name__, log_dir=log_directory, log_name="s3bfd", console_log_level=console_log_level, file_log_level=file_log_level, is_gui=is_started_from_gui, message_queue=log_message_queue)

		if is_debug_enabled:
			opt = {True: "enabled", False: "disabled"}
			logger.info("Debug options are enabled")
			logger.info(f"Bucket caching is {opt[debug_enable_caching]}")
			logger.info(f"File downloading is {opt[debug_enable_downloading]}")
			logger.info(f"File validation is {opt[debug_enable_validation] if debug_enable_downloading and debug_enable_validation else opt[False]}")
			logger.info(f"Downloading a maximum of {debug_max_file_downloads} files")
			if not is_started_from_gui:
				logger.info(f"Clearing existing files at startup is {opt[debug_clear_files_at_startup]}")
			logger.info(f"Saving directory cache to disk is {opt[debug_enable_save_prefix_cache]}")
			logger.info(f"Loading directory cache from disk is {opt[debug_enable_load_prefix_cache]}")

		if not is_started_from_gui:
			if debug_clear_files_at_startup:
				pass # TODO: too destructive in it's current implementation
			#	Path.unlink(f"{database_directory}/{DATABASE_NAME}", missing_ok=True)
			#	Path.unlink(f"{prefix_cache_directory}/{PREFIX_CACHE_NAME}", missing_ok=True)
			#	for file in Path(log_directory).iterdir():
			#		if file.is_file():
			#			file.unlink(missing_ok=True)
			#	for file in Path(buffer_directory).iterdir():
			#		if file.is_file():
			#			file.unlink(missing_ok=True)

		global s3bfd_prefix_cache

		if debug_enable_load_prefix_cache or not is_debug_enabled:
			if Path(prefix_cache_directory).joinpath(PREFIX_CACHE_NAME).exists():
				logger.info(f"(main) loading prefix cache from {prefix_cache_directory}")
				with open(f"{prefix_cache_directory}/{PREFIX_CACHE_NAME}", "rb") as f:
					s3bfd_prefix_cache = pickle.load(f)
			else:
				logger.warning(f"(main) prefix cache does not exist at path '{prefix_cache_directory}'")

		engine = create_engine(f"sqlite:///{database_directory}/{DATABASE_NAME}", connect_args={"autocommit": False}, echo=False)

		Base.metadata.create_all(engine)

		# TODO: replace with normal Queues/LifoQueues
		queue_manager = QueueManager()
		queue_manager.start()
		queue = queue_manager.LifoQueue()
		queue2 = queue_manager.FifoQueue()

		with ThreadPoolExecutor(max_workers=4) as executor:

			if is_debug_enabled:
				logger.info("(main) (debugging) opening thread pool")
				is_running_event.set()
				if debug_enable_caching:
					gbm_future = executor.submit(get_bucket_metadata, (bucket_url, prefix, prefix_root, region, engine, threads, queue, pbar_queue, buffer_directory))
					fst_future = executor.submit(file_storage_thread, (threads, engine, queue))
					result = gbm_future.result()
					logger.info("(main) (debugging) waiting for get_bucket_metadata and file_storage_thread to reach completion")
					if result:
						logger.info("(main) (debugging) get_bucket_metadata finished normally")
					else:
						logger.error("(main) (debugging) get_bucket_metadata finished abnormally")

					result = fst_future.result()
					if result:
						logger.info("(main) (debugging) file_storage_thread finished normally")
					else:
						logger.error("(main) (debugging) file_storage_thread finished abnormally")

				if debug_enable_downloading:
					dbf_future = executor.submit(download_bucket_files, (bucket_url, engine, threads, queue2, [".checksum"], prefix, download_directory))
					if debug_enable_validation:
						vbf_future = executor.submit(validate_bucket_files, (threads, engine, queue2))

					result = dbf_future.result()
					if result:
						logger.info("(main) (debugging) download_bucket_files finished normally")
					else:
						logger.error("(main) (debugging) download_bucket_files finished abnormally")
					if debug_enable_validation:
						result = vbf_future.result()
						if result:
							logger.info("(main) (debugging) validate_bucket_files finished normally")
						else:
							logger.error("(main) (debugging) validate_bucket_files finished abnormally")
				logger.info("(main) (debugging) finished; closing thread pool")
			else:
				logger.info("(main) opening thread pool")
				is_running_event.set()
				if process_type in [0, 1, 3]:
					gbm_future = executor.submit(get_bucket_metadata, (bucket_url, prefix, prefix_root, region, engine, threads, queue, pbar_queue, buffer_directory))
					fst_future = executor.submit(file_storage_thread, (threads, engine, queue))
					logger.info("(main) waiting for get_bucket_metadata and file_storage_thread to reach completion")
					if result:
						logger.info("(main) get_bucket_metadata finished normally")
					else:
						logger.error("(main) get_bucket_metadata finished abnormally")
				if process_type in [0, 1, 2, 4]:
					dbf_future = executor.submit(download_bucket_files, (bucket_url, engine, threads, queue2, [".checksum"], prefix), download_directory)
					if process_type in [0, 2]:
						vbf_future = executor.submit(validate_bucket_files, (threads, engine, queue2))
					result = dbf_future.result()
					if result:
						logger.info("(main) download_bucket_files finished normally")
					else:
						logger.error("(main) download_bucket_files finished abnormally")

					if process_type in [0, 2]:
						result = vbf_future.result()
						if result:
							logger.info("(main) validate_bucket_files finished normally")
						else:
							logger.error("(main) validate_bucket_files finished abnormally")

				logger.info("(main) finished; closing thread pool")
		logger.info("(main) thread pool closed")

		if debug_enable_save_prefix_cache or not is_debug_enabled:
			if s3bfd_prefix_cache:
				logger.info(f"saving prefix cache to {prefix_cache_directory}")
				with open(f"{prefix_cache_directory}/{PREFIX_CACHE_NAME}", "wb") as f:
					pickle.dump(s3bfd_prefix_cache, f)
			else:
				logger.warning("(main) prefix cache was empty; not saving")

		logger.info("(main) Finished")
	except Exception:
		traceback.print_exc()
		logger.error("(main) Error:\n", exc_info=True)
	finally:
		if is_running_event is not None:
			is_running_event.clear()
		return
if __name__ == "__main__":
	run_s3bfd()
