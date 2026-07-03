# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import argparse
import sys
from cli.cli import init_cli
from gui.gui import init_gui
from initialize.initialize import initialize


if __name__ == "__main__":
	parser = argparse.ArgumentParser(
								prog="s3bfd",
								description="Download files from S3 buckets",
								allow_abbrev=False)
	parser.add_argument("--nogui", action="store_true")
	parser.add_argument("--version", action="store_true")

	args = parser.parse_args()
	if args.version:
		# TODO print version
		sys.exit(0)

	initialize()
	
	if args.nogui:
		init_cli(args)
	else:
		init_gui()
	

"""
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
"""