# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from dataclasses import dataclass

@dataclass(frozen=True)
class Constants:
	POSIX_OS = "posix"
	WINDOWS_OS = "Windows"
	MAC_OS = "Darwin"
	DATABASE_NAME = "s3bfd_cache.db"
	PREFIX_CACHE_NAME = "s3bfd_prefix_cache.pkl"
	BUCKET_INFO_TABLE_NAME = "bucket_info"
	UNIQUE_BUCKETS_TABLE_NAME = "unique_buckets"
	USER_AGENTS = (
		"Mozilla/5.0 (X11; Linux x86_64; rv:152.0) Gecko/20100101 Firefox/152.0",
		"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
		"Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:152.0) Gecko/20100101 Firefox/152.0",
		"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
		"Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:152.0) Gecko/20100101 Firefox/152.0",
		"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",

	)
	BASE_S3_URL:str = "https://s3%s%s.amazonaws.com/%s"
	S3_URL_SEPARATORS = (".","-")
	LOG_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
	PROXIES = {}
	
