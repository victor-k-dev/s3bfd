# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from sqlalchemy.orm import Session
from sqlalchemy import select
from .globals import Globals as dg
from .schema import BucketInfo
from utils.globals import Globals as gl

from pathlib import Path

"""
def fetch_files(child_id:int):
	gl.logger.debug(child_id)
	with Session(dg.engine) as session:
		statement = select(BucketInfo).where(BucketInfo.parent_id == child_id, BucketInfo.is_directory == False)
		results = session.execute(statement).scalars().all()

	return results
"""

def fetch_children(children:list[int]):
	with Session(dg.engine) as session:
		statement = select(BucketInfo).where(BucketInfo.node_id.in_(children))
		results = session.execute(statement).scalars().all()
	
	return results

def fetch_single_file(path:str) -> BucketInfo:
	with Session(dg.engine) as session:
		statement = select(BucketInfo).where(BucketInfo.path == path, BucketInfo.is_directory == False)
		result = session.execute(statement).scalar()

	return result

def fetch_multi_files(child_ids:list[int]):
	with Session(dg.engine) as session:
		statement = select(BucketInfo).where(BucketInfo.node_id.in_(child_ids), BucketInfo.is_directory == False)
		results = session.execute(statement).scalars().all()

	return results

"""
def fetch_all_directory_nodes():
	with Session(dg.engine) as session:
		statement = select(BucketInfo).where(BucketInfo.is_directory == True)
		results = session.execute(statement).scalars().all()

	return results
"""

def fetch_directory_node(node_id:int):
	with Session(dg.engine) as session:
		statement = select(BucketInfo).where(BucketInfo.node_id == node_id, BucketInfo.is_directory == True)
		result = session.execute(statement).scalar()
		
		return {"key": result.path, "id": result.id, "parent_id": result.parent.id, "child_ids": [child.id for child in result.children]}
		
def fetch_directory_nodes(node_ids:list[int]):
	processed_results = []
	with Session(dg.engine) as session:
		statement = select(BucketInfo.id, BucketInfo.path).where(BucketInfo.node_id.in_(node_ids), BucketInfo.is_directory == True)
		results = session.execute(statement).all()
		
		processed_results = {Path(result.path): result.id for result in results}
		return processed_results
	
def fetch_file_nodes(node_ids:list[int]):
	processed_results = []
	with Session(dg.engine) as session:
		statement = select(BucketInfo.id, BucketInfo.path).where(BucketInfo.node_id.in_(node_ids), BucketInfo.is_directory == False)
		results = session.execute(statement).all()
		
		processed_results = {Path(result.path): result.id for result in results}
		return processed_results
	
def fetch_parent_nodes(child_paths:list[Path]):
	processed_results = []
	parent_paths = set([str(child_path.parent) for child_path in child_paths])

	with Session(dg.engine) as session:
		statement = select(BucketInfo.id, BucketInfo.path).where(BucketInfo.path.in_(parent_paths), BucketInfo.is_directory == False)
		results = session.execute(statement).all()
		
		processed_results = {Path(result.path): result.id for result in results}
		return processed_results
	
def fetch_file_node(id:int):
	with Session(dg.engine) as session:
		statement = select(BucketInfo).where(BucketInfo.id == id, BucketInfo.is_directory == False)
		result = session.execute(statement).scalar()
	
	return result

def debug_fetch():
	
	with Session(dg.engine) as session:
		statement = select(BucketInfo).where(BucketInfo.is_directory == True, BucketInfo.id > 100000)
		result = session.execute(statement).scalar()
		gl.logger.debug(result.id, result.path, result.node_id, result.parent_id)
		gl.logger.debug(result.parent.id, result.parent.path, result.parent.node_id)