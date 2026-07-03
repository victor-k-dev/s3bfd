# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from .globals import Globals as dg
from .schema import UniqueBuckets, BucketInfo
from pathlib import Path
from utils.globals import Globals as gl
from sqlalchemy import select, update
from sqlalchemy.orm import Session
from process.parameters import Parameters

"""
class Base(DeclarativeBase):
	pass

class UniqueBuckets(Base):
	__tablename__ = ct.UNIQUE_BUCKETS_TABLE_NAME
	id: Mapped[int] = mapped_column(primary_key=True)
	bucket_name: Mapped[str] = mapped_column(nullable=False)
	bucket_id: Mapped[int] = mapped_column(nullable=False)

class BucketInfo(Base):
	__tablename__ = ct.BUCKET_INFO_TABLE_NAME

	id: Mapped[int] = mapped_column(primary_key=True)
	tree_id: Mapped[int] = mapped_column(nullable=False)
	tree_name: Mapped[str] = mapped_column(nullable=False) # Set to bucket_url
	node_id: Mapped[int] = mapped_column(nullable=False) # independent of id
	parent_id: Mapped[Optional[int]] = mapped_column(nullable=True) # set to parent's node_id
	#parent_id: Mapped[Optional[int]] = mapped_column(ForeignKey("bucket_info.id"), nullable=True)
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

	#parent = relationship("BucketInfo", remote_side=[id], back_populates="children")
	#children = relationship("BucketInfo", back_populates="parent")
"""
def fetch_files(child_id:int):
	gl.logger.debug(child_id)
	with Session(dg.engine) as session:
		statement = select(BucketInfo).where(BucketInfo.parent_id == child_id, BucketInfo.is_directory == False)
		gl.logger.debug(statement)
		results = session.execute(statement).scalars().all()
		gl.logger.debug(results)
	return results

def is_bucket_in_database() -> bool:
	with Session(dg.engine) as session:
		statement = select(UniqueBuckets).where(UniqueBuckets.bucket_name == Parameters.url)
		result = session.execute(statement).scalar_one_or_none()
		
	if result is None:
		gl.current_tree_id = add_unique_bucket()
		Parameters.tree_id = gl.current_tree_id
		add_new_root_nodes()
		return False
	else:
		gl.current_tree_id = result.bucket_id
		return True

def fetch_existing_root_node() -> BucketInfo:
	with Session(dg.engine) as session:
		statement = select(BucketInfo).where(BucketInfo.tree_name == Parameters.url, BucketInfo.parent_id == None)
		return session.execute(statement).scalar_one()
	
def add_unique_bucket() -> int:
	with Session(dg.engine) as session:
		current_max_bucket_id = session.execute(select(UniqueBuckets.bucket_id).order_by(UniqueBuckets.bucket_id.desc()).limit(1)).scalars().first()
		if current_max_bucket_id is not None:
			new_max_bucket_id = current_max_bucket_id + 1
		else:
			new_max_bucket_id = 0
		current_tree_id = new_max_bucket_id
		new_unique_bucket = UniqueBuckets(
			bucket_name=Parameters.url,
			bucket_id=new_max_bucket_id
		)
		session.add(new_unique_bucket)
		session.commit()

	return current_tree_id

# TODO: handle if prefix is malformed or does not contain root directory
def add_new_root_nodes():
	with Session(dg.engine) as session:
		gl.s3bfd_prefix_cache[Parameters.url] = {}
		new_records = []
		path_parts = Parameters.prefix.parts
		prefix_root = Path(path_parts[0])

		root_directories = [path for path in reversed(Parameters.prefix.parents) if path != Path(".")]
		root_directories.append(Parameters.prefix)
		for path in root_directories:
			#gl.logger.debug(path)
			if path in [Path("."), Path("/")]:
				path = prefix_root

			node = BucketInfo(
				node_id=gl.node_id,
				tree_id=gl.current_tree_id,
				tree_name=Parameters.url,
				parent_id=None if path == prefix_root else gl.s3bfd_prefix_cache[Parameters.url][path.parent]["node_id"],#gl.current_node_id.get() - 1,
				name=path.name,
				path=str(path),
				is_directory=True
			)
			
			gl.s3bfd_prefix_cache[Parameters.url][path] = {
				"node_id": gl.node_id, 
				"tree_id": node.tree_id, 
				"tree_name": node.tree_name, 
				"parent_id": node.parent_id, 
				"name": node.name, 
				"path": Path(node.path)
			}

			new_records.append(node)
			gl.node_id += 1
			#gl.current_node_id.value += 1

		session.add_all(new_records)
		session.commit()

def store_directory_metadata(directories, keys):
	new_records = [directories[key].to_bucket_info() for key in keys]
	gl.writing_to_database_semaphore.acquire()
	try:
		with Session(dg.engine) as session:
			session.add_all(new_records)
			session.commit()
	except Exception:
		gl.logger.error("(alt_store_directory_metadata) an error occurred:\n", exc_info=True)
	finally:
		gl.writing_to_database_semaphore.release()

def store_file_metadata(files:dict):
	if Parameters.process_in_memory and Parameters.save_to_disk:
		try:	
			for key in files.keys():
				with open(files[key].local_file_path, "wb") as f:
					f.write(files[key].bytes)
		except Exception:
			gl.logger.error("(store_file_metadata) An error occurred while saving files to disk:\n", exc_info=True)

	new_records = [files[key].to_bucket_info() for key in files.keys()]
	gl.writing_to_database_semaphore.acquire()
	try:
		with Session(dg.engine) as session:
			session.add_all(new_records)
			session.commit()
	except Exception:
		gl.logger.error("(alt_store_file_metadata) an error occurred:\n", exc_info=True)
	finally:
		gl.writing_to_database_semaphore.release()

def update_single_file_metadata(file, id):
	update_vals = {"id": id, "downloaded_at": file.downloaded_at, "original_checksum_type": file.old_checksum_type, "checksum": file.new_checksum, "validation_passed": file.passed_validation}
	try:
		with Session(dg.engine) as session:
			statement = update(BucketInfo).where(BucketInfo.id == id).values(update_vals)
			session.execute(statement)
			session.commit()
	except Exception:
		gl.logger.error("(update_single_file_metadata) An error occurred:\n", exc_info=True)
	finally:
		pass

def update_multi_file_metadata(files:dict):
	update_vals = []
	try:
		#for file, id in zip(files, ids):
		for key in files.keys():
			update_vals.append({"id": files[key].id, "downloaded_at": files[key].downloaded_at, "original_checksum_type": files[key].old_checksum_type, "checksum": files[key].new_checksum, "validation_passed": files[key].passed_validation})
		with Session(dg.engine) as session:
			session.execute(update(BucketInfo), update_vals)
			session.commit()
	except Exception:
		gl.logger.error("(update_multi_file_metadata) An error occurred:\n", exc_info=True)
	finally:
		pass

def optimize_database_records(update_vals):
	try:
		with Session(dg.engine) as session:
			session.execute(update(BucketInfo), update_vals)
			session.commit()
	except Exception:
		gl.logger.error("(optimize_database_records) An error occurred:\n", exc_info=True)
	finally:
		pass