# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

def initialize():
	from database.schema import Base
	from database.globals import Globals as dg
	from database.prefix import load
	from utils.globals import Globals as gl
	from utils.paths import DefaultPaths
	from utils.paths import CurrentPaths
	from sqlalchemy import create_engine

	DefaultPaths.DEFAULT_DATA_DIRECTORY.mkdir(exist_ok=True)
	DefaultPaths.DEFAULT_LOG_DIRECTORY.mkdir(exist_ok=True)
	DefaultPaths.DEFAULT_PREFIX_CACHE_DIRECTORY.mkdir(exist_ok=True)
	DefaultPaths.DEFAULT_DATABASE_DIRECTORY.mkdir(exist_ok=True)
	DefaultPaths.DEFAULT_BUFFER_DIRECTORY.mkdir(exist_ok=True)
	DefaultPaths.DEFAULT_DOWNLOAD_DIRECTORY.mkdir(exist_ok=True)

	gl.logger.debug(CurrentPaths.database_file_path)
	engine = create_engine(f"sqlite:///{CurrentPaths.database_file_path}", connect_args={"autocommit": False}, echo=False)
	Base.metadata.create_all(engine)
	dg.engine = engine

	if CurrentPaths.prefix_cache_file_path.exists():
		gl.s3bfd_prefix_cache = load(CurrentPaths.prefix_cache_file_path)
	else:
		gl.s3bfd_prefix_cache = {}
		gl.logger.debug("prefix cache file not found")

	return