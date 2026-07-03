# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import random
import requests
from time import sleep
from utils.constants import Constants as ct
from utils.globals import Globals as gl
from process.parameters import Parameters
from utils.paths import CurrentPaths
from xml.etree import ElementTree
from database.metadata import FileMetadata, DirectoryMetadata
from pathlib import Path
from datetime import datetime

def get_file(key:Path, retries:int=5, delay:int=60) -> str:
	#gl.logger.debug("(get_file)")
	file = gl.file_metadata[key]
	file.local_file_path = CurrentPaths.download_directory.joinpath(file.path)
	file.local_file_path.parent.mkdir(parents=True, exist_ok=True)
	
	try:
		while True:
			if gl.immediate_stop_event.is_set():
				raise StopIteration
			try:
				r = requests.get(url=file.url, proxies=ct.PROXIES)
				r.raise_for_status()
				file.downloaded_at = datetime.now()
				break
			except Exception:
				sleep(delay)
				retries -= 1
				if retries <= 0:
					break
				continue
		try:
			with open(file.local_file_path, "wb") as f:
				f.write(r.content)

		except Exception:
			gl.logger.error("(get_file) An error occurred:\n", exc_info=True)
	except StopIteration:
		gl.logger.info("stop event set; stopping")
	finally:
		gl.file_metadata[key] = file
		return key
	
def get_files(files:dict[Path, FileMetadata], retries:int=5, delay:int=5):
	try:
		for path in files.keys():
			if gl.immediate_stop_event.is_set():
				raise StopIteration

			if not files[path].local_file_path:
				files[path].local_file_path = CurrentPaths.download_directory.joinpath(files[path].path)
			files[path].local_file_path.parent.mkdir(parents=True, exist_ok=True)

			while True:
				if gl.immediate_stop_event.is_set():
					raise StopIteration
				try:
					r = requests.get(url=files[path].url, proxies=ct.PROXIES)
					r.raise_for_status()
					files[path].downloaded_at = datetime.now()
					break
				except Exception:
					sleep(delay)
					retries -= 1
					if retries <= 0:
						break
					continue
			if Parameters.process_in_memory and not Parameters.skip_validation:
				files[path].bytes = r.content
			else:
				try:
					with open(files[path].local_file_path, "wb") as f:
						f.write(r.content)
				except Exception:
					gl.logger.error("(get_files) An error occurred:\n", exc_info=True)
	except StopIteration:
		gl.logger.info("(get_files) stop event set; stopping")
	finally:
		return files
	
def get_single_file(file:FileMetadata, retries:int=5, delay:int=60):
	file.local_file_path = CurrentPaths.download_directory.joinpath(file.path)
	file.local_file_path.parent.mkdir(parents=True, exist_ok=True)

	try:
		while True:
			if gl.immediate_stop_event.is_set():
				raise StopIteration
			try:
				r = requests.get(url=file.url, proxies=ct.PROXIES)
				r.raise_for_status()
				file.downloaded_at = datetime.now()
				file.bytes = r.content
				break
			except Exception:
				sleep(delay)
				retries -= 1
				if retries <= 0:
					break
				continue

	except StopIteration:
		gl.logger.info("stop event set; stopping")
	finally:
		return file
	
def get_multi_files(files:dict[Path, FileMetadata], retries:int=5, delay:int=5):
	try:
		for key in files.keys():
			if gl.immediate_stop_event.is_set():
				raise StopIteration

			while True:
				if gl.immediate_stop_event.is_set():
					raise StopIteration
				try:
					r = requests.get(url=files[key].url, proxies=ct.PROXIES)
					r.raise_for_status()
					files[key].downloaded_at = datetime.now()
					files[key].bytes = r.content
					break
				except Exception:
					sleep(delay)
					retries -= 1
					if retries <= 0:
						break
					continue
	except StopIteration:
		gl.logger.info("stop event set; stopping")
	finally:
		return files
	
def get_metadata(prefix:str, max_pages=10) -> tuple[dict[FileMetadata],dict[str,DirectoryMetadata]]:
	#gl.logger.debug("(get_metadata)")
	
	if not Parameters.s3_url:
		base_url = ct.BASE_S3_URL % (ct.S3_URL_SEPARATORS[0], Parameters.region, Parameters.url)
	else:
		base_url = "https://%s" % Parameters.s3_url

	headers = {
		'User-Agent': ct.USER_AGENTS[random.randint(0,len(ct.USER_AGENTS)-1)],
		'Accept': '*/*',
		'Origin': f'{Parameters.url}',
		'Referer': f'{Parameters.url}',
		'Sec-Fetch-Dest': 'empty',
		'Sec-Fetch-Mode': 'cors',
		'Sec-Fetch-Site': 'cross-site'
	}
	
	all_files:dict[Path, FileMetadata] = {}
	all_directories:dict[Path,DirectoryMetadata] = {}
	marker = None
	page_count = 0
	max_retries = 5
	retries = 0
	delay = 5
	try:
		while (max_pages is None) or (page_count < max_pages):
			if gl.immediate_stop_event.is_set():
				raise StopIteration

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

					if gl.immediate_stop_event.is_set():
						raise StopIteration
					
					try:
						
						status_code = None
						response = requests.get(base_url, params=request_params, headers=headers, proxies=ct.PROXIES)
						status_code = response.status_code
						response.raise_for_status()
						is_fetched_data = True
						is_s3_connection_successful = True
						break
					except StopIteration:
						raise
					except Exception:
						if (status_code is not None) and (status_code == 404) and (not is_s3_connection_successful):
							gl.logger.warning(f"(get_metadata) S3 bucket not found at {base_url}; attempting https://{Parameters.url} in {delay} seconds")
							base_url = "https://%s" % Parameters.url
							Parameters.s3_url = base_url
						elif (status_code is not None):
							gl.logger.error(f"(get_metadata) failed to fetch S3 data ({status_code}); retrying in {delay} seconds\n", exc_info=True)
						else:
							gl.logger.error(f"(get_metadata) failed to fetch S3 data (response code unavailable); retrying in {delay} seconds\n", exc_info=True)
						sleep(delay)
						retries += 1
						continue
				if not is_fetched_data:
					raise Exception(f"failed to fetch S3 data; no more retries remain")

				try:
					root = ElementTree.fromstring(response.content)
				except Exception:
					gl.logger.error(f"(get_metadata) error occurred during XML parsing for page {page_count}:\n", exc_info=True)
					gl.logger.error(f"(get_metadata) XML response: {root}")
					break

				for prefix_elem in root.findall('.//{http://s3.amazonaws.com/doc/2006-03-01/}CommonPrefixes'):

					if gl.immediate_stop_event.is_set():
						raise StopIteration

					prefix_key = prefix_elem.find('{http://s3.amazonaws.com/doc/2006-03-01/}Prefix').text
					if prefix_key is not None:
						dir_path = Path(prefix_key)

						if dir_path in gl.s3bfd_prefix_cache[Parameters.url]:
							continue

						gl.node_id_semaphore.acquire()
						if dir_path.parent in gl.s3bfd_prefix_cache[Parameters.url] and dir_path not in gl.s3bfd_prefix_cache[Parameters.url]:
							all_directories[dir_path] = DirectoryMetadata(
								node_id=gl.node_id,
								parent_id=gl.s3bfd_prefix_cache[Parameters.url][dir_path.parent]["node_id"],
								name=dir_path.name, 
								path=dir_path, 
								prefix=prefix_key, 
								tree_id=Parameters.tree_id, 
								tree_name=Parameters.url
							)

							gl.s3bfd_prefix_cache[Parameters.url][dir_path] = {
								"node_id": gl.node_id,
								"tree_id": Parameters.tree_id,
								"tree_name": Parameters.url,
								"parent_id": gl.s3bfd_prefix_cache[Parameters.url][dir_path.parent]["node_id"],
								"name": dir_path.name,
								"path": dir_path,
								"children": [],
							}
							
							gl.node_id += 1
						else:
							gl.logger.warning("(get_metadata) dir parent not found in cache:\n%s\n%s\n%s" % (dir_path, dir_path.parent, gl.s3bfd_prefix_cache[Parameters.url]))
						gl.node_id_semaphore.release()
					else:
						gl.logger.warning("(get_metadata) dir prefix not found")

				for content in root.findall('.//{http://s3.amazonaws.com/doc/2006-03-01/}Contents'):
					
					if gl.immediate_stop_event.is_set():
						raise StopIteration
					
					key = content.find('{http://s3.amazonaws.com/doc/2006-03-01/}Key').text
					last_modified = content.find('{http://s3.amazonaws.com/doc/2006-03-01/}LastModified').text
					size = content.find('{http://s3.amazonaws.com/doc/2006-03-01/}Size').text
					etag = content.find('{http://s3.amazonaws.com/doc/2006-03-01/}ETag').text
					etag = etag.strip("\"")

					if key.lower().endswith(".checksum"):
						continue

					if key is not None:
						gl.node_id_semaphore.acquire()
						file_path = Path(key)
						file_url = base_url + "/" + key
						if file_path.parent in gl.s3bfd_prefix_cache[Parameters.url]:
							all_files[file_path] = FileMetadata(
								node_id=gl.node_id,
								parent_id=gl.s3bfd_prefix_cache[Parameters.url][file_path.parent]["node_id"],
								tree_id=Parameters.tree_id, 
								tree_name=Parameters.url, 
								name=file_path.name, 
								path=file_path, 
								size_bytes=size, 
								last_modified=datetime.fromisoformat(last_modified), 
								old_checksum=etag,
								#local_file_path=CurrentPaths.download_directory.joinpath(file_path)
								url=file_url
							)

							gl.s3bfd_prefix_cache[Parameters.url][file_path.parent]["children"].append(gl.node_id)

							gl.node_id += 1
						else:
							gl.logger.warning("(alt_get_metadata) file parent not found")
						gl.node_id_semaphore.release()
					else:
						gl.logger.warning("(alt_get_metadata) file key not found")

				is_truncated = root.find('.//{http://s3.amazonaws.com/doc/2006-03-01/}IsTruncated')
				if is_truncated is not None and is_truncated.text == 'true':
					#gl.logger.debug("found 'IsTruncated'")
					next_marker = root.find('.//{http://s3.amazonaws.com/doc/2006-03-01/}NextMarker')
					if next_marker is not None:
						#gl.logger.debug("found 'NextMarker'")
						marker = next_marker.text
					else:
						if list(all_files):
							marker = list(all_files)[-1]['Key']
						else:
							#gl.logger.debug("no files found; no 'NextMarker' found")
							break
				else:
					#gl.logger.debug("no 'IsTruncated' found")
					break

				page_count += 1
				sleep(0.1) # TODO: consider making adjustable
			except StopIteration:
				raise
			except Exception:
				gl.logger.error(f"(get_metadata) Error on page {page_count}:", exc_info=True)
				break
		#gl.logger.debug(f"(s3) all directories {all_directories}")
		#gl.logger.debug(f"(s3) all files {all_files}")
	except StopIteration:
		gl.logger.info("(get_metadata) stop event set; stopping")
	finally:
		#gl.logger.info("(alt_get_metadata) finished")
		return all_files, all_directories