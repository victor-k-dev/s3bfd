# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from utils.globals import Globals
from utils.paths import CurrentPaths
from process.parameters import Parameters
from process.process import start, stop, debug
from time import sleep
from pathlib import Path

def init_cli(args):
	Globals.logger.info(args)

	initial_menu_text = """
		Welcome to s3bfd!

		This program's source code is subject to the terms of the Mozilla Public
		License, v. 2.0. If a copy of the MPL was not distributed with the
		source code, you can obtain one at https://mozilla.org/MPL/2.0/.

		Running: %s
		
		Current Bucket URL: %s
		Current Prefix: %s
		Current Region: %s
		
		Parameters:
			Cache Only: %s
			Skip Validation: %s
			Process Files in Memory: %s
			Save Files to Disk: %s
			Delete Files After Validation: %s
		
		Current Download Directory: %s

		(1) Set Bucket URL
		(2) Set Prefix
		(3) Set Region
		(4) Set Cache Only
		(5) Set Skip Validation
		(6) Set Process Files in Memory
		(7) Set Save Files to Disk
		(8) Set Delete Files After Validation
		(9) Change Download Directory
		(start) Start
		(stop) Stop
	"""
	
	menu_text = """
		Running: %s
		
		Current Bucket URL: %s
		Current Prefix: %s
		Current Region: %s
		
		Parameters:
			Cache Only: %s
			Skip Validation: %s
			Process Files in Memory: %s
			Save Files to Disk: %s
			Delete Files After Validation: %s

		Current Download Directory: %s

		(1) Set Bucket URL
		(2) Set Prefix
		(3) Set Region
		(4) Set Cache Only
		(5) Set Skip Validation
		(6) Set Process Files in Memory
		(7) Set Save Files to Disk
		(8) Set Delete Files After Validation
		(9) Change Download Directory
		(start) Start
		(stop) Stop
	"""
	is_initial = True

	try:
		while True:
			if is_initial:
				print("\x1B[2J")
				print("\x1B[3J")
				print("\x1B[H")
				print(initial_menu_text % (Parameters.is_running, Parameters.url, Parameters.prefix, Parameters.region, Parameters.cache_only, Parameters.skip_validation, Parameters.process_in_memory, Parameters.save_to_disk, Parameters.delete_after_validation, CurrentPaths.download_directory))
				is_initial = False
			else:
				print("\x1B[2J")
				print("\x1B[3J")
				print("\x1B[H")
				print(menu_text % (Parameters.is_running, Parameters.url, Parameters.prefix, Parameters.region, Parameters.cache_only, Parameters.skip_validation, Parameters.process_in_memory, Parameters.save_to_disk, Parameters.delete_after_validation, CurrentPaths.download_directory))
			user_input = input("\nChoose an option (1-5,start,stop): ")

			if user_input.strip() == "1":
				url = input("\n\nInput a new bucket URL: ")
				Parameters.url = url.strip()
				print("\nBucket URL set to %s" % Parameters.url)
				sleep(3)
			elif user_input.strip() == "2":
				prefix = input("\n\nInput a new prefix: ")
				Parameters.prefix = Path(prefix.strip())
				print("\nPrefix set to %s" % Parameters.prefix)
				sleep(3)
			elif user_input.strip() == "3":
				region = input("\n\nInput a new region: ")
				Parameters.region = region.strip()
				print("\nRegion set to %s" % Parameters.region)
				sleep(3)
			elif user_input.strip() == "4":

				decision = input("\n\nCache Only is currently %s. Set to %s? (y/N): " % (Parameters.cache_only, False if Parameters.cache_only else True))
				if decision.strip().lower() == "y":
					Parameters.cache_only = False if Parameters.cache_only else True
					print("\n\nCache Only set to %s" % Parameters.cache_only)
					sleep(3)
			elif user_input.strip() == "5":
				decision = input("\n\nSkip Validation is currently %s. Set to %s? (y/N): " % (Parameters.skip_validation, False if Parameters.skip_validation else True))
				if decision.strip().lower() == "y":
					Parameters.skip_validation = False if Parameters.skip_validation else True
					print("\n\nSkip Validation set to %s", Parameters.skip_validation)
					sleep(3)
			elif user_input.strip() == "6":
				decision = input("\n\nProcess Files in Memory is currently %s. Set to %s? (y/N): " % (Parameters.process_in_memory, False if Parameters.process_in_memory else True))
				if decision.strip().lower() == "y":
					Parameters.process_in_memory = False if Parameters.process_in_memory else True
					print("\n\nProcess Files in Memory set to %s", Parameters.process_in_memory)
					sleep(3)
			elif user_input.strip() == "7":
				decision = input("\n\nSave Files to Disk is currently %s. Set to %s? (y/N): " % (Parameters.save_to_disk, False if Parameters.save_to_disk else True))
				if decision.strip().lower() == "y":
					Parameters.save_to_disk = False if Parameters.save_to_disk else True
					print("\n\nSave Files to Disk set to %s", Parameters.save_to_disk)
					sleep(3)
			elif user_input.strip() == "8":
				decision = input("\n\nDelete Files After Validation is currently %s. Set to %s? (y/N): " % (Parameters.delete_after_validation, False if Parameters.delete_after_validation else True))
				if decision.strip().lower() == "y":
					Parameters.delete_after_validation = False if Parameters.delete_after_validation else True
					print("\n\nDelete Files After Validation set to %s", Parameters.delete_after_validation)
					sleep(3)
			elif user_input.strip() == "9":
				new_directory = input("\n\nInput a new download directory: ")
				if Path(new_directory).is_dir() and Path(new_directory).exists():
					CurrentPaths.download_directory = Path(new_directory)
					print("\nDownload directory set to %s" % str(CurrentPaths.download_directory))
				else:
					print("Invalid directory provided")	
				sleep(3)
			elif user_input.strip() == "start":
				if not Parameters.is_running:
					if Parameters.url and Parameters.prefix:
						if Parameters.url == Parameters.region:
							Parameters.s3_url = Parameters.url
							print("\n\nRegion same as Bucket URL; setting S3 URL to Bucket URL...")
						print("\n\nStarting process:\nBucket URL: %s\nPrefix: %s\nRegion: %s" % (Parameters.url, Parameters.prefix, Parameters.region))
						Globals.logger.info(
							Parameters.s3_url, 
							Parameters.download_threads,
							Parameters.requests_threads,
							Parameters.total_threads,
							Parameters.no_gui,
							Parameters.cache_only,
							Parameters.skip_validation,
							Parameters.process_in_memory,
							Parameters.save_to_disk,
							Parameters.delete_after_validation,
							Parameters.tree_id,
							CurrentPaths.download_directory,
						)
						Parameters.is_running = True
						start()
						sleep(3)
				else:
					print("\n\nA process is already running")
					sleep(3)
			elif user_input.strip() == "stop":
				if Parameters.is_running:
					stop()
					Parameters.is_running = False
				else:
					print("\n\nNo processes are currently running")
					sleep(3)
			#elif user_input.strip() == "debug":
			#	debug()

	except KeyboardInterrupt:
		pass
	except Exception:
		Globals.logger.error("(cli) An error occurred:\n", exc_info=True)
	finally:
		if Parameters.is_running:
			stop()
	pass