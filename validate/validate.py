# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from queue import Empty
from utils.globals import Globals
from time import sleep
import traceback
from database.metadata import FileMetadata
from process.parameters import Parameters

def validate_checksums():
	Globals.logger.info("(validate_checksums)")
	try:
		while True:
			if Globals.immediate_stop_event.is_set():
				raise StopIteration
			
			try:
				files:dict[str, FileMetadata] = Globals.validation_queue.get_nowait()
				for key in files.keys():
					if Globals.immediate_stop_event.is_set():
						raise StopIteration
					hash_length = len(files[key].old_checksum)
					if hash_length in Globals.hash_lengths:
						hash_type = Globals.hash_lengths[len(files[key].old_checksum)]
					else:
						Globals.logger.warning("(validate_checksums) no matching function for hash '%s' (length %s)" % (files[key].old_checksum, hash_length))
						#raise ValueError("no matching function for hash '%s' (length %s)" % (files[key].old_checksum, hash_length))
						continue
					file_bytes = None
					hash = None
					if Parameters.process_in_memory:
						file_bytes = files[key].bytes
						hash = Globals.hash_functions[hash_type](file_bytes).hexdigest()
					else:
						with open(files[key].local_file_path, "rb") as f:
							file_bytes = f.read()
							hash = Globals.hash_functions[hash_type](file_bytes).hexdigest()
					if hash and file_bytes:
						if hash == files[key].old_checksum:
							files[key].old_checksum_type = hash_type
							files[key].passed_validation = True
							if hash_type != files[key].new_checksum_type:
								files[key].new_checksum = Globals.hash_functions[Globals.new_checksum_type](file_bytes).hexdigest()
								files[key].new_checksum_type = Globals.new_checksum_type
						else:
							files[key].passed_validation = False
							Globals.invalid_file_metadata[key] = files[key]
							#print("(validate_checksums) hashes don't match; original: %s, file: %s" % (files[key].old_checksum, hash))
							Globals.logger.warning("hashes don't match; original: %s, file: %s" % (files[key].old_checksum, hash))
							if hash_type == "sha256":
								pass # A different hashing algo may also produce 64 char hashes
							else:
								pass
					if Parameters.delete_after_validation:
						files[key].local_file_path.unlink(missing_ok=True)
					if Globals.graceful_stop_event.is_set():
						raise StopIteration
				Globals.storage_queue.put_nowait(files)
				del files
			except Empty:
				if Globals.immediate_stop_event.is_set():
					raise StopIteration
				elif Globals.graceful_stop_event.is_set():
					raise StopIteration
				sleep(0.1)
				continue
			except Exception:
				Globals.logger.error("(validate_checksums) An error occurred:\n", exc_info=True)
	except StopIteration:
		Globals.logger.info("(validate_checksums) stop event set; stopping")
	finally:
		Globals.logger.info("(validate_checksums) finished")

def validate_single_checksum(file):
	try:
		hash_length = len(file.old_checksum)

		if hash_length in Globals.hash_lengths:
			hash_type = Globals.hash_lengths[len(file.old_checksum)]
		else:
			file.bytes = None
			file.passed_validation = False
			raise ValueError("(validate_single_checksum) no matching function for hash '%s' (length %s)" % (file.old_checksum, hash_length))

		hash = Globals.hash_functions[hash_type](file.bytes).hexdigest()
		if hash == file.old_checksum:
			file.old_checksum_type = hash_type
			file.passed_validation = True
			if hash_type != file.new_checksum_type:
				file.new_checksum = Globals.hash_functions[Globals.new_checksum_type](file.bytes).hexdigest()
				file.new_checksum_type = Globals.new_checksum_type
		else:
			file.passed_validation = False
			file.bytes = None
			Globals.logger.warning("(validate_single_checksum) hashes don't match; original: %s, file: %s" % (file.old_checksum, hash))
			if hash_type == "sha256":
				pass # A different hashing algo may also produce 64 char hashes
			else:
				pass
	except Exception:
		Globals.logger.error("(validate_single_checksum) An error occurred:\n", exc_info=True)
	finally:
		return file
	
def validate_multi_checksums(files:dict):
	try:
		for key in files.keys():

			hash_length = len(files[key].old_checksum)

			if hash_length in Globals.hash_lengths:
				hash_type = Globals.hash_lengths[len(files[key].old_checksum)]
			else:
				files[key].bytes = None
				files[key].passed_validation = False
				raise ValueError("(validate_multi_checksums) no matching function for hash '%s' (length %s)" % (files[key].old_checksum, hash_length))

			hash = Globals.hash_functions[hash_type](files[key].bytes).hexdigest()
			if hash == files[key].old_checksum:
				files[key].old_checksum_type = hash_type
				files[key].passed_validation = True
				if hash_type != files[key].new_checksum_type:
					files[key].new_checksum = Globals.hash_functions[Globals.new_checksum_type](files[key].bytes).hexdigest()
					files[key].new_checksum_type = Globals.new_checksum_type
			else:
				files[key].passed_validation = False
				files[key].bytes = None
				Globals.logger.warning("(validate_multi_checksums) hashes don't match; original: %s, file: %s" % (files[key].old_checksum, hash))
				if hash_type == "sha256":
					pass # A different hashing algo may also produce 64 char hashes
				else:
					pass
	except Exception:
		Globals.logger.error("(validate_multi_checksum) An error occurred:\n", exc_info=True)
	finally:
		return files