"""Pydantic models for representing records."""

import errno
import grp
import os
import pwd
import stat

import xattr
from pydantic import BaseModel


def get_extended_attribute(path: str, attr_name: str) -> str:
    """Get the value of an extended attribute."""
    try:
        # Get the value of the specified extended attribute
        value = xattr.getxattr(path, attr_name).decode("utf-8")
        return value
    except OSError as e:
        # Handle the case when the attribute is not found
        if e.errno == errno.ENODATA:
            raise ValueError(f"extended attribute {attr_name} not found") from e
        else:
            # Re-raise the exception for other errors
            raise


class FsDirectory(BaseModel):
    """Information about a file system directory.

    This consists of the classic POSIX file system attributes and
    additional Ceph extended attributes.
    """

    #: Absolute path to the directory.
    path: str
    #: The username of the owner of the directory.
    owner_name: str
    #: The user UID of the owner of the directory.
    owner_uid: int
    #: The group of the directory.
    group_name: str
    #: The group GID of the directory.
    group_gid: int
    #: The directory permissions.
    perms: str

    #: The size of the directory in bytes.
    rbytes: int
    #: The number of files in the directory.
    rfiles: int
    #: The bytes quota.
    quota_bytes: int
    #: The files quota.
    quota_files: int

    @staticmethod
    def from_path(path: str) -> "FsDirectory":
        """Create a new instance from a path."""
        # Get owner user name, owner uid, group name, group gid
        uid = os.stat(path).st_uid
        gid = os.stat(path).st_gid
        owner_name = pwd.getpwuid(uid).pw_name
        group_name = grp.getgrgid(gid).gr_name
        # Get permissions mask
        mode = os.stat(path).st_mode
        permissions = stat.filemode(mode)
        # Get Ceph extended attributes.
        rbytes = int(get_extended_attribute(path, "ceph.dir.rbytes"))
        rfiles = int(get_extended_attribute(path, "ceph.dir.rfiles"))
        quota_bytes = int(get_extended_attribute(path, "ceph.quota.max_bytes"))
        quota_files = int(get_extended_attribute(path, "ceph.quota.max_files"))

        return FsDirectory(
            path=path,
            owner_name=owner_name,
            owner_uid=uid,
            group_name=group_name,
            group_gid=gid,
            perms=permissions,
            rbytes=rbytes,
            rfiles=rfiles,
            quota_bytes=quota_bytes,
            quota_files=quota_files,
        )
