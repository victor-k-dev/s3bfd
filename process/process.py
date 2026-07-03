# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from .parameters import Parameters
from utils.globals import Globals
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from multiprocessing import Process
from queue import Empty
from download.download import get_metadata, get_files, get_single_file, get_multi_files
from validate.validate import validate_checksums, validate_single_checksum, validate_multi_checksums
from database.database import store_directory_metadata, store_file_metadata, is_bucket_in_database, update_single_file_metadata, update_multi_file_metadata, optimize_database_records
from database.fetch import fetch_single_file, fetch_multi_files, debug_fetch, fetch_directory_nodes, fetch_file_nodes, fetch_parent_nodes
from database.metadata import FileMetadata
from time import sleep

from utils.paths import CurrentPaths
import pickle
from pathlib import Path

def debug():
	debug_fetch()
	optimize_prefix_cache()
	optimize_database()
	debug_fetch()
def start():
	Globals.logger.info("start")
	if Globals.process_list:
		Globals.logger.warning("(start) process(es) already running")
		return
	
	Globals.process_list.append(Process(target=store_files_task))
	Globals.process_list.extend([Process(target=validate_checksums) for _ in range(0,Parameters.validation_processes)])
	Globals.process_list.append(Process(target=run))

	if Globals.graceful_stop_event.is_set():
		Globals.graceful_stop_event.clear()
	if Globals.immediate_stop_event.is_set():
		Globals.immediate_stop_event.clear()

	var = is_bucket_in_database()
	if var:
		Globals.logger.info("bucket was in db")
	else:
		Globals.logger.info("bucket was not in db")

	for process in Globals.process_list:
		process.start()

	return

def stop():
	if not Globals.process_list:
		Globals.logger.warning("(stop) no processes are running")
		return
	
	Globals.logger.warning("(stop)")
	Globals.immediate_stop_event.set()
	Globals.logger.info("(stop) initiating immediate/graceful stop")
	Globals.graceful_stop_event.set()

	for process in Globals.process_list:
		process.join()
	
	Globals.process_list.clear()
	Globals.s3bfd_prefix_cache = Globals.message_queue.get()
	#Globals.logger.debug("Saving prefix cache:\n%s" % Globals.s3bfd_prefix_cache)
	with open(CurrentPaths.prefix_cache_file_path, "wb") as f:
		
		pickle.dump(Globals.s3bfd_prefix_cache, f)

	Globals.logger.info("stopped")
	return

def store_files_task():
	Globals.logger.info("(store_files_task) starting")
	workers = 16
	storage_pool = ThreadPoolExecutor(max_workers=workers)
	storage_futures:list[Future] = []
	submissions = 0
	try:
		while True:
			if Globals.immediate_stop_event.is_set():
				storage_pool.shutdown(wait=True, cancel_futures=True)
				raise StopIteration
			try:
				files = Globals.storage_queue.get_nowait()
				storage_futures.append(storage_pool.submit(store_file_metadata, files))
				submissions += 1
				if submissions >= workers:
					for future in as_completed(storage_futures):
						future.result()
					storage_futures.clear()
					submissions = 0
			except Empty:
				sleep(0.1)

	except StopIteration:
		Globals.logger.info("(store_files_task) stopping")
	finally:
		Globals.logger.info("(store_files_task) stopped")
	pass

def run():
	Globals.logger.info("(run) starting")

	request_pool = ThreadPoolExecutor(max_workers=Parameters.requests_threads)
	download_pool = ThreadPoolExecutor(max_workers=Parameters.download_threads)

	request_prefixes = []
	files_to_download:list[dict[Path, FileMetadata]] = []
	
	task_id = 0
	metadata_futures:dict[int, Future] = {}
	download_futures:dict[int, Future] = {}
	completed_task_ids = []

	request_prefixes.append(str(Parameters.prefix) + "/")
	Globals.logger.debug(Globals.s3bfd_prefix_cache[Parameters.url])
	try:
		while True:
			if Globals.immediate_stop_event.is_set():
				Globals.logger.info("(run) stopping...")
				request_pool.shutdown(wait=True, cancel_futures=True)
				download_pool.shutdown(wait=True, cancel_futures=True)
				raise StopIteration
			while request_prefixes:
				if Globals.immediate_stop_event.is_set():
					Globals.logger.info("(run) stopping...")
					request_pool.shutdown(wait=True, cancel_futures=True)
					download_pool.shutdown(wait=True, cancel_futures=True)
					raise StopIteration
				if Globals.request_semaphore.acquire(blocking=False):
					metadata_futures[task_id] = request_pool.submit(get_metadata, request_prefixes.pop())
					task_id += 1
				else:
					break

			while files_to_download and not Parameters.cache_only:
				if Globals.immediate_stop_event.is_set():
					Globals.logger.info("(run) stopping...")
					request_pool.shutdown(wait=True, cancel_futures=True)
					download_pool.shutdown(wait=True, cancel_futures=True)
					raise StopIteration
				if Globals.download_semaphore.acquire(blocking=False):
					download_futures[task_id] = download_pool.submit(get_files, files_to_download.pop())
					task_id += 1
				else:
					break
			
			for id, future in metadata_futures.items():
				if Globals.immediate_stop_event.is_set():
					Globals.logger.info("(run) stopping...")
					request_pool.shutdown(wait=True, cancel_futures=True)
					download_pool.shutdown(wait=True, cancel_futures=True)
					raise StopIteration
				files = None; dirs = None
				try:
					files, dirs = future.result(timeout=0.001)
					completed_task_ids.append(id)
					Globals.request_semaphore.release()
				except TimeoutError:
					continue
				
				if dirs:
					if Globals.immediate_stop_event.is_set():
						Globals.logger.info("(run) stopping...")
						request_pool.shutdown(wait=True, cancel_futures=True)
						download_pool.shutdown(wait=True, cancel_futures=True)
						raise StopIteration
					request_prefixes.extend([dir.prefix for dir in dirs.values()])
					store_directory_metadata(dirs, list(dirs))

				if files and not Parameters.cache_only:
					files_to_download.append(files)
				elif files and Parameters.cache_only:
					Globals.storage_queue.put_nowait(files)

			for id, future in download_futures.items():
				if Globals.immediate_stop_event.is_set():
					Globals.logger.info("(run) stopping...")
					request_pool.shutdown(wait=True, cancel_futures=True)
					download_pool.shutdown(wait=True, cancel_futures=True)
					raise StopIteration
				try:
					files = future.result(timeout=0.001)
					completed_task_ids.append(id)
					Globals.download_semaphore.release()
				except TimeoutError:
					continue
				
				if Parameters.skip_validation:
					Globals.storage_queue.put_nowait(files)
				else:
					Globals.validation_queue.put_nowait(files)

			while completed_task_ids:
				id = completed_task_ids.pop()
				if id in metadata_futures:
					del metadata_futures[id]
				elif id in download_futures:
					del download_futures[id]


			if Globals.graceful_stop_event.is_set():
				Globals.logger.info("(run) stopping gracefully...")
				request_pool.shutdown(wait=True, cancel_futures=False)
				download_pool.shutdown(wait=True, cancel_futures=False)
				raise StopIteration
			sleep(0.1)

	except StopIteration:
		Globals.logger.info("(run) stopped")
	finally:
		Globals.logger.info("(run) finished")
		Globals.message_queue.put(Globals.s3bfd_prefix_cache)

def single_file_start():
	Globals.logger.info("(single_file_start)")
	if Globals.process_list:
		Globals.logger.warning("(single_file_start) process(es) already running")
		return
	
	Globals.process_list.append(Process(target=single_file_run))
	
	if Globals.graceful_stop_event.is_set():
		Globals.graceful_stop_event.clear()
	if Globals.immediate_stop_event.is_set():
		Globals.immediate_stop_event.clear()

	Globals.process_list[0].start()
	return

def multi_file_start():
	Globals.logger.info("(multi_file_start)")
	if Globals.process_list:
		Globals.logger.warning("(multi_file_start) process(es) already running")

	Globals.process_list.append(Process(target=multi_file_run))
	
	if Globals.graceful_stop_event.is_set():
		Globals.graceful_stop_event.clear()
	if Globals.immediate_stop_event.is_set():
		Globals.immediate_stop_event.clear()

	Globals.process_list[0].start()
	return

def single_file_run():
	try:
		file_node = fetch_single_file(Parameters.single_file_path)
		file_metadata = FileMetadata(
			node_id=file_node.node_id,
			parent_id=file_node.parent_id,
			name=file_node.name,
			path=Path(file_node.path),
			size_bytes=file_node.size_bytes,
			last_modified=file_node.last_modified,
			old_checksum=file_node.original_checksum,
			url=Parameters.single_file_url,
			tree_id=file_node.tree_id,
			tree_name=file_node.tree_name,
		)
		file_metadata = get_single_file(file_metadata)
		file_metadata:FileMetadata = validate_single_checksum(file_metadata)
		if file_metadata.bytes:
			with open(file_metadata.local_file_path, "wb") as f:
				f.write(file_metadata.bytes)
		update_single_file_metadata(file_metadata, file_node.id)

	except Exception:
		Globals.logger.error("(single_file_run) An error occurred:\n", exc_info=True)
	finally:
		Globals.logger.info("(single_file_run) finished")
		Globals.message_queue.put(Globals.s3bfd_prefix_cache)

def multi_file_run():
	child_node_ids = Globals.s3bfd_prefix_cache[Parameters.url][Parameters.multi_file_directory]["children"]
	try:
		file_metadata:dict[Path, FileMetadata] = {}
		file_nodes = fetch_multi_files(child_node_ids)

		for file_node in file_nodes:
			if file_node.path.lower().endswith(".checksum"):
				continue
			file_metadata[Path(file_node.path)] = FileMetadata(
				node_id=file_node.node_id,
				parent_id=file_node.parent_id,
				name=file_node.name,
				path=Path(file_node.path),
				size_bytes=file_node.size_bytes,
				last_modified=file_node.last_modified,
				old_checksum=file_node.original_checksum,
				url=Parameters.multi_file_base_url + file_node.path,
				tree_id=file_node.tree_id,
				tree_name=file_node.tree_name,
			)
			file_metadata[Path(file_node.path)].id = file_node.id
			file_metadata[Path(file_node.path)].local_file_path = CurrentPaths.download_directory.joinpath(file_node.path)
			
		file_metadata = get_multi_files(file_metadata)
		file_metadata = validate_multi_checksums(file_metadata)
		for key in file_metadata.keys():
			if file_metadata[key].bytes:
				file_metadata[key].local_file_path.parent.mkdir(parents=True, exist_ok=True)
				with open(file_metadata[key].local_file_path, "wb") as f:
					f.write(file_metadata[key].bytes)
		update_multi_file_metadata(file_metadata)

	except Exception:
		Globals.logger.error("(multi_file_run) An error occurred:\n", exc_info=True)
	finally:
		Globals.logger.info("(multi_file_run) finished")
		Globals.message_queue.put(Globals.s3bfd_prefix_cache)

def optimize_prefix_cache():

	Parameters.url = "historical-data.kucoin.com"
	print("optimizing prefix cache")
	keys = list(Globals.s3bfd_prefix_cache[Parameters.url])
	keys = [key for key in list(Globals.s3bfd_prefix_cache[Parameters.url]) if "children" in Globals.s3bfd_prefix_cache[Parameters.url][key] and Globals.s3bfd_prefix_cache[Parameters.url][key]["children"]]
	node_ids = [Globals.s3bfd_prefix_cache[Parameters.url][key]["node_id"] for key in keys]
	
	child_node_ids = []
	for key in keys:
		child_node_ids.append(Globals.s3bfd_prefix_cache[Parameters.url][key]["children"])
	
	node_results = fetch_directory_nodes(node_ids)
	with ThreadPoolExecutor(max_workers=32) as executor:
		futures = [executor.submit(fetch_file_nodes, ids) for ids in child_node_ids]

		child_node_results = {}
		for future in as_completed(futures):
			results = future.result()
			child_node_results.update(results)
	
	node_paths = []

	for node_path, id in node_results.items():
		Globals.s3bfd_prefix_cache[Parameters.url][node_path]["node_id"] = id
		node_paths.append(node_path)

	for child_path, id in child_node_results.items():
		Globals.s3bfd_prefix_cache[Parameters.url][child_path.parent]["children"].append(id)
		node_paths.append(child_path)

	parent_node_results = fetch_parent_nodes(node_paths)
	
	for key in keys:
		for parent_path, id in parent_node_results.items():
			if key.parent == parent_path:
				Globals.s3bfd_prefix_cache[Parameters.url][key]["parent_id"] = id
				break
	
	with open(CurrentPaths.prefix_cache_directory.joinpath("test-optimized-cache.pkl"), "wb") as f:
		
		pickle.dump(Globals.s3bfd_prefix_cache, f)

	print("finished optimizing prefix cache")
	print("proceeding in 15 seconds...")
	try:
		for x in reversed(range(0,15)):
			print(x)
	except KeyboardInterrupt:
		import sys
		sys.exit(0)

def optimize_database():
	print("optimizing database records")
	keys = list(Globals.s3bfd_prefix_cache[Parameters.url])
	update_vals = []
	for key in keys:
		print("working on record: %s" % key)
		id = Globals.s3bfd_prefix_cache[Parameters.url][key]["node_id"]
		parent_id = Globals.s3bfd_prefix_cache[Parameters.url][key]["parent_id"]
		update_vals.append({"id": id, "node_id": id, "parent_id": parent_id})
		for child_id in Globals.s3bfd_prefix_cache[Parameters.url][key]["children"]:
			update_vals.append({"id": child_id, "node_id": child_id, "parent_id": id})
	print("prepared update vals")
	optimize_database_records(update_vals)
	print("finished optimizing database records")

	