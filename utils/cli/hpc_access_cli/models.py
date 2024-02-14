"""Pydantic models for representing records."""

import datetime
import enum
import errno
import grp
import os
import pwd
import stat
from typing import Dict, List, Optional
from uuid import UUID

import xattr
from pydantic import BaseModel


def get_extended_attribute(path: str, attr_name: str) -> str:
    """Get the value of an extended attribute."""
    try:
        # Get the value of the specified extended attribute
        value = xattr.getxattr(path, attr_name).decode("utf-8")
        return value
    except OSError as e:
        if os.environ.get("DEBUG", "0") == "1":
            return "0"
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
        try:
            owner_name = pwd.getpwuid(uid).pw_name
        except KeyError:
            if os.environ.get("DEBUG", "0") == "1":
                owner_name = "unknown"
            else:
                raise
        try:
            group_name = grp.getgrgid(gid).gr_name
        except KeyError:
            if os.environ.get("DEBUG", "0") == "1":
                group_name = "unknown"
            else:
                raise
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


class Gecos(BaseModel):
    """GECOS information about a user."""

    #: The full name of the user.
    full_name: Optional[str] = None
    #: The office location of the user.
    office_location: Optional[str] = None
    #: The office phone number of the user.
    office_phone: Optional[str] = None
    #: The home phone number of the user.
    home_phone: Optional[str] = None
    #: The other information about the user.
    other: Optional[str] = None

    def to_string(self):
        """Convert the GECOS information to a GECOS string."""
        return ",".join(
            [
                self.full_name if self.full_name else "",
                self.office_location if self.office_location else "",
                self.office_phone if self.office_phone else "",
                self.home_phone if self.home_phone else "",
                self.other if self.other else "",
            ]
        )

    @staticmethod
    def from_string(gecos: str) -> "Gecos":
        """Create a new instance from a GECOS string."""
        parts = gecos.split(",", 4)
        if len(parts) < 5:
            parts.extend([""] * (5 - len(parts)))
        return Gecos(
            full_name=parts[0] if parts[0] != "None" else None,
            office_location=parts[1] if parts[1] != "None" else None,
            office_phone=parts[2] if parts[2] != "None" else None,
            home_phone=parts[3] if parts[3] != "None" else None,
            other=parts[4] if parts[4] != "None" else None,
        )


class LdapUser(BaseModel):
    """A user form the LDAP directory."""

    #: The common name of the user.
    cn: str
    #: The distinguished name of the user.
    dn: str
    #: The username.
    uid: str
    #: The user's surname.
    sn: Optional[str]
    #: The user's given name.
    given_name: Optional[str]
    #: The numeric user ID.
    uid_number: int
    #: The primary group of the user.
    gid_number: int
    #: The home directory of the user.
    home_directory: str
    #: The login shell of the user.
    login_shell: str
    #: The GECOS information of the user.
    gecos: Optional[Gecos]
    #: The email address of the user.
    ssh_public_key: List[str]


class LdapGroup(BaseModel):
    """A group from the LDAP directory.

    Note that we use this both for work groups and for projects.  Work groups
    will have ``member_uids==[]`` as the members are added via their primary
    numeric group uid.
    """

    #: The common name of the group.
    cn: str
    #: The distinguished name of the group.
    dn: str
    #: The description.
    gid_number: int
    #: The distinguished name of the group's owner.
    owner_dn: Optional[str]
    #: The distinguished name of the group's delegates.
    delegate_dns: List[str]
    #: The member uids (== user names) of the group.
    member_uids: List[str]


class ResourceData(BaseModel):
    """A resource request/usage for a user."""

    #: Storage on tier 1 in TB.
    tier1: float
    #: Storage on tier 2 (mirrored) in TB.
    tier2_mirrored: float
    #: Storage on tier 2 (unmirrored) in TB.
    tier2_unmirrored: float


@enum.unique
class Status(enum.Enum):
    """Status of a hpc user, group, or project."""

    INITIAL = "INITIAL"
    ACTIVE = "ACTIVE"
    DELETED = "DELETED"
    EXPIRED = "EXPIRED"


class HpcUser(BaseModel):
    """A user as read from the hpc-access API."""

    #: The UUID of the record.
    uuid: UUID
    #: The UUID of the primary ``HpcGroup``.
    primary_group: UUID
    #: The requested resources.
    resources_request: Optional[ResourceData]
    #: The used resources.
    resources_used: Optional[ResourceData]
    #: The status of the record.
    status: Status
    #: The POSIX UID of the user.
    uid: Optional[int]
    #: The username of the record.
    username: str
    #: Point in time of user expiration.
    expiration: datetime.datetime
    #: The version of the user record.
    current_version: int


class HpcGroup(BaseModel):
    """A group as read from the hpc-access API."""

    #: The UUID of the record.
    uuid: UUID
    #: The owning ``HpcUser``.
    owner: UUID
    #: The delegate.
    delegate: Optional[UUID]
    #: The requested resources.
    resources_request: Optional[ResourceData]
    #: The used resources.
    resources_used: Optional[ResourceData]
    #: The status of the record.
    status: Status
    #: The POSIX GID of the corresponding Unix group.
    gid: Optional[int]
    #: The name of the record.
    name: str
    #: Point in time of group expiration.
    expiration: datetime.datetime
    #: The version of the group record.
    current_version: int


class HpcProject(BaseModel):
    """A project as read from the hpc-access API."""

    #: The UUID of the record.
    uuid: UUID
    #: The owning ``HpcGroup``, owner of group is owner of project.
    group: UUID
    #: The delegate for the project.
    delegate: Optional[UUID]
    #: The requested resources.
    resources_request: Optional[ResourceData]
    #: The used resources.
    resources_used: Optional[ResourceData]
    #: The status of the record.
    status: Status
    #: The POSIX GID of the corresponding Unix group.
    gid: Optional[int]
    #: The name of the record.
    name: str
    #: Point in time of group expiration.
    expiration: datetime.datetime
    #: The version of the project record.
    current_version: int


class MailmanSubscription(BaseModel):
    """Information of a subscription to a mailman mailing list."""

    #: The member's email address.
    member_address: str


class SystemState(BaseModel):
    """System state retrieved from LDAP and file system."""

    #: Mapping from file system path to ``FsDirectory``.
    fs_directories: Dict[str, FsDirectory]
    #: Mapping from LDAP dn to ``LdapUser``.
    ldap_users: Dict[str, LdapUser]
    #: Mapping from LDAP dn to ``LdapGroup``.
    ldap_groups: Dict[str, LdapGroup]
