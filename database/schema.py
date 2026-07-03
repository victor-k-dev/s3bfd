# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from datetime import datetime
from utils.constants import Constants
from sqlalchemy import Integer, ForeignKey, Boolean, DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from typing import Optional

class Base(DeclarativeBase):
	pass

class UniqueBuckets(Base):
	__tablename__ = Constants.UNIQUE_BUCKETS_TABLE_NAME
	id: Mapped[int] = mapped_column(primary_key=True)
	bucket_name: Mapped[str] = mapped_column(nullable=False)
	bucket_id: Mapped[int] = mapped_column(nullable=False)

"""
class UniqueBuckets(Base):
	__tablename__ = Constants.UNIQUE_BUCKETS_TABLE_NAME
	id: Mapped[int] = mapped_column(primary_key=True)
	bucket_name: Mapped[str] = mapped_column(nullable=False)
	bucket_id: Mapped[int] = mapped_column(nullable=False)
	optimized: Mapped[bool] = mapped_column(nullable=False, default=False)
"""
"""
# Unoptimized
class BucketInfo(Base):
	__tablename__ = Constants.BUCKET_INFO_TABLE_NAME

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

	#parent = relationship("BucketInfo", remote_side=[node_id], back_populates="children")
	#children = relationship("BucketInfo", back_populates="parent")
"""
"""
# Optimized
class BucketInfo(Base):
	__tablename__ = Constants.BUCKET_INFO_TABLE_NAME

	id: Mapped[int] = mapped_column(primary_key=True)
	tree_id: Mapped[int] = mapped_column(nullable=False)
	tree_name: Mapped[str] = mapped_column(nullable=False) # Set to bucket_url
	#node_id: Mapped[int] = mapped_column(nullable=False) # independent of id
	parent_id: Mapped[Optional[int]] = mapped_column(ForeignKey("bucket_info.id"), nullable=True)
	name: Mapped[str] = mapped_column(nullable=False)
	path: Mapped[str] = mapped_column(nullable=False)
	is_directory: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
	size_bytes: Mapped[Optional[int]] = mapped_column(Integer, nullable=False, default=0)
	last_modified: Mapped[datetime] = mapped_column(DateTime, nullable=True) # Not set for directories
	downloaded_at: Mapped[datetime] = mapped_column(DateTime, nullable=True) # Only set for files
	old_checksum_type: Mapped[str] = mapped_column(nullable=True)
	old_checksum: Mapped[str] = mapped_column(nullable=True)
	new_checksum_type: Mapped[str] = mapped_column(default="sha256", nullable=False)
	new_checksum: Mapped[str] = mapped_column(nullable=True)
	passed_validation: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

	parent = relationship("BucketInfo", remote_side=[id], back_populates="children")
	children = relationship("BucketInfo", back_populates="parent")
"""
"""
class BucketInfo(Base):
	__tablename__ = Constants.BUCKET_INFO_TABLE_NAME

	id: Mapped[int] = mapped_column(primary_key=True)
	tree_id: Mapped[int] = mapped_column(nullable=False)
	tree_name: Mapped[str] = mapped_column(nullable=False) # Set to bucket_url
	node_id: Mapped[int] = mapped_column(nullable=False) # independent of id
	#parent_id: Mapped[Optional[int]] = mapped_column(nullable=True) # set to parent's node_id
	parent_id: Mapped[Optional[int]] = mapped_column(ForeignKey("bucket_info.node_id"), nullable=True)
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

	parent = relationship("BucketInfo", remote_side=[node_id], back_populates="children")
	children = relationship("BucketInfo", back_populates="parent")
"""

class BucketInfo(Base):
	__tablename__ = Constants.BUCKET_INFO_TABLE_NAME

	id: Mapped[int] = mapped_column(primary_key=True)
	tree_id: Mapped[int] = mapped_column(nullable=False)
	tree_name: Mapped[str] = mapped_column(nullable=False) # Set to bucket_url
	node_id: Mapped[int] = mapped_column(nullable=False) # independent of id
	parent_id: Mapped[Optional[int]] = mapped_column(nullable=True) # set to parent's node_id
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