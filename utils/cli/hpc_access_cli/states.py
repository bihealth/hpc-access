"""State gathering, comparison and update."""

import os
from typing import Dict, List

from hpc_access_cli.config import HpcaccessSettings, Settings
from hpc_access_cli.fs import FsResourceManager
from hpc_access_cli.ldap import LdapConnection
from hpc_access_cli.models import (
    FsDirectory,
    FsDirectoryOp,
    Gecos,
    HpcaccessState,
    HpcUser,
    LdapGroup,
    LdapGroupOp,
    LdapUser,
    LdapUserOp,
    OperationsContainer,
    ResourceData,
    StateOperation,
    SystemState,
)
from hpc_access_cli.rest import HpcaccessClient
from rich.console import Console

#: The rich console to use for output.
console = Console()

#: Base DN for work groups.
BASE_DN_GROUPS = "ou=Teams,ou=Groups,dc=hpc,dc=bihealth,dc=org"
#: Base DN for projects
BASE_DN_PROJECTS = "ou=Projects,ou=Groups,dc=hpc,dc=bihealth,dc=org"
#: Base DN for Charite users
BASE_DN_CHARITE = "ou=Charite,ou=Users,dc=hpc,dc=bihealth,dc=org"
#: Base DN for MDC users
BASE_DN_MDC = "ou=MDC,ou=Users,dc=hpc,dc=bihealth,dc=org"

# Quota on user home (1G)
QUOTA_HOME_BYTES = 1024 * 1024 * 1024
# Quota on scratch (100T)
QUOTA_SCRATCH_BYTES = 100 * 1024 * 1024 * 1024 * 1024


def user_dn(user: HpcUser) -> str:
    """Get the DN for the user."""
    if user.username.endswith("_m"):
        return f"cn={user.full_name},{BASE_DN_MDC}"
    else:
        return f"cn={user.full_name},{BASE_DN_CHARITE}"


class TargetStateBuilder:
    """ "Helper class that is capable of building the target state giving data
    from hpc-access.
    """

    def __init__(self, settings: HpcaccessSettings, system_state: SystemState):
        #: The settings to use.
        self.settings = settings
        #: The current system state, used for determining next group id.
        self.system_state = system_state
        #: The next gid.
        self.next_gid = self._get_next_gid(system_state)
        console.log(f"Next available GID is {self.next_gid}.")

    def _get_next_gid(self, system_state: SystemState) -> int:
        """Get the next available GID."""
        gids = [g.gid_number for g in system_state.ldap_groups.values()]
        gids.extend([u.gid_number for u in system_state.ldap_users.values()])
        return max(gids) + 1 if gids else 1000

    def run(self) -> SystemState:
        """Run the builder."""
        hpcaccess_state = self._gather()
        return self._build(hpcaccess_state)

    def _gather(self) -> HpcaccessState:
        """Gather the state."""
        console.log("Loading hpc-access users, groups, and projects...")
        rest_client = HpcaccessClient(self.settings)
        result = HpcaccessState(
            hpc_users={u.uuid: u for u in rest_client.load_users()},
            hpc_groups={g.uuid: g for g in rest_client.load_groups()},
            hpc_projects={p.uuid: p for p in rest_client.load_projects()},
        )
        console.log("  # of users:", len(result.hpc_users))
        console.log("  # of groups:", len(result.hpc_groups))
        console.log("  # of projects:", len(result.hpc_projects))
        console.log("... have hpc-access data now.")
        return result

    def _build(self, hpcaccess_state: HpcaccessState) -> SystemState:
        """Build the target state."""
        return SystemState(
            ldap_users=self._build_ldap_users(hpcaccess_state),
            ldap_groups=self._build_ldap_groups(hpcaccess_state),
            fs_directories=self._build_fs_directories(hpcaccess_state),
        )

    def _build_fs_directories(self, hpcaccess_state: HpcaccessState) -> Dict[str, FsDirectory]:
        """Build the file system directories from the hpc-access state."""
        result = {}
        for user in hpcaccess_state.hpc_users.values():
            if not user.uid:
                console.log(
                    f"User {user.full_name} has no uid, skipping.",
                )
                continue
            primary_group = hpcaccess_state.hpc_groups[user.primary_group]
            if not primary_group.gid:
                console.log(
                    f"Primary group {primary_group.name} has no gid, skipping.",
                )
                continue
            result[f"/data/cephfs-1/home/users/{user.username}"] = FsDirectory(
                path=f"/data/cephfs-1/home/users/{user.username}",
                owner_name=user.username,
                owner_uid=user.uid,
                group_name=primary_group.name,
                group_gid=primary_group.gid,
                perms="drwx--S---",
                rbytes=None,
                rfiles=None,
                # Currently, hard-coded user quotas only.
                # Note: maybe remove from HpcUser model!
                quota_bytes=QUOTA_HOME_BYTES,
                quota_files=None,
            )
        for group in hpcaccess_state.hpc_groups.values():
            if not group.gid:
                console.log(
                    f"Group {group.name} has no gid, skipping.",
                )
                continue
            owner = hpcaccess_state.hpc_users[group.owner]
            if not owner.uid:
                console.log(
                    f"Owner {owner.full_name} has no uid, skipping.",
                )
                continue
            # Tier 1
            quota_work = (group.resources_requested or ResourceData).tier1
            if not quota_work:
                continue
            for volume, quota in (
                ("home", QUOTA_HOME_BYTES),
                ("scratch", QUOTA_SCRATCH_BYTES),
                ("work", quota_work * 1024 * 1024 * 1024 * 1024),
            ):
                result[f"/data/cephfs-1/{volume}/groups/{group.name}"] = FsDirectory(
                    path=f"/data/cephfs-1/{volume}/groups/{group.name}",
                    owner_name=owner.username,
                    owner_uid=owner.uid,
                    group_name=group.name,
                    group_gid=group.gid,
                    perms="drwxrwS---",
                    rbytes=None,
                    rfiles=None,
                    quota_bytes=None if quota is None else int(quota),
                    quota_files=None,
                )
            # Tier 2
            for variant in ("unmirrored", "mirrored"):
                if variant == "mirrored":
                    quota = (group.resources_requested or ResourceData).tier2_mirrored
                elif variant == "unmirrored":
                    quota = (group.resources_requested or ResourceData).tier2_unmirrored
                else:
                    raise ValueError("Invalid variant")
                if not quota:
                    continue
                result[f"/data/cephfs-2/{variant}/groups/{group.name}"] = FsDirectory(
                    path=f"/data/cephfs-2/{variant}/groups/{group.name}",
                    owner_name=owner.username,
                    owner_uid=owner.uid,
                    group_name=group.name,
                    group_gid=group.gid,
                    perms="drwxrwS---",
                    rbytes=None,
                    rfiles=None,
                    quota_bytes=None if quota is None else int(quota),
                    quota_files=None,
                )
        for project in hpcaccess_state.hpc_projects.values():
            if not project.gid:
                console.log(
                    f"Project {project.name} has no gid, skipping.",
                )
                continue
            owning_group = hpcaccess_state.hpc_groups[project.group]
            owner = hpcaccess_state.hpc_users[owning_group.owner]
            if not owner.uid:
                console.log(
                    f"Owner {owner.full_name} has no uid, skipping.",
                )
                continue
            # Tier 1
            quota_work = (project.resources_requested or ResourceData).tier1
            if not quota_work:
                continue  # no quota requested
            for volume, quota in (
                ("home", QUOTA_HOME_BYTES),
                ("scratch", QUOTA_SCRATCH_BYTES),
                ("work", quota_work * 1024 * 1024 * 1024 * 1024),
            ):
                result[f"/data/cephfs-1/{volume}/projects/{project.name}"] = FsDirectory(
                    path=f"/data/cephfs-1/{volume}/projects/{project.name}",
                    owner_name=owner.username,
                    owner_uid=owner.uid,
                    group_name=f"hpc-prj-{project.name}",
                    group_gid=project.gid,
                    perms="drwxrwS---",
                    rbytes=None,
                    rfiles=None,
                    quota_bytes=None if quota is None else int(quota),
                    quota_files=None,
                )
            # Tier 2
            for variant in ("unmirrored", "mirrored"):
                if variant == "mirrored":
                    quota = (project.resources_requested or ResourceData).tier2_mirrored
                elif variant == "unmirrored":
                    quota = (project.resources_requested or ResourceData).tier2_unmirrored
                else:
                    raise ValueError("Invalid variant")
                if not quota:
                    continue
                result[f"/data/cephfs-2/{variant}/projects/{project.name}"] = FsDirectory(
                    path=f"/data/cephfs-2/{variant}/projects/{project.name}",
                    owner_name=owner.username,
                    owner_uid=owner.uid,
                    group_name=f"hpc-prj-{project.name}",
                    group_gid=project.gid,
                    perms="drwxrwS---",
                    rbytes=None,
                    rfiles=None,
                    quota_bytes=None if quota is None else int(quota),
                    quota_files=None,
                )

        return result

    def _build_ldap_users(self, hpcaccess_state: HpcaccessState) -> Dict[str, LdapUser]:
        """Build the LDAP users from the hpc-access state."""
        result = {}
        for user in hpcaccess_state.hpc_users.values():
            gecos = Gecos(
                full_name=user.full_name,
                office_location=None,
                office_phone=user.phone_number,
                other=None,
            )
            primary_group = hpcaccess_state.hpc_groups[user.primary_group]
            if not user.uid:
                console.log(
                    f"User {user.full_name} has no uid, skipping.",
                )
                continue
            if not primary_group.gid:
                console.log(
                    f"User {user.full_name} has no primary group, skipping.",
                )
                continue
            result[user.username] = LdapUser(
                dn=user_dn(user),
                cn=user.full_name,
                sn=user.last_name,
                given_name=user.first_name,
                uid=user.username,
                gecos=gecos,
                uid_number=user.uid,
                gid_number=primary_group.gid,
                home_directory=f"/data/cephfs-1/home/users/{user.username}",  # user.home_directory,
                login_shell="/usr/bin/bash",  # user.login_shell,
                # SSH keys are managed via upstream LDAP.
                ssh_public_key=[],
            )
        return result

    def _build_ldap_groups(self, state: HpcaccessState) -> Dict[str, LdapGroup]:
        """Build the LDAP groups from the hpc-access state."""
        result = {}
        # build for work groups
        for group in state.hpc_groups.values():
            if not group.gid:
                console.log(
                    f"Group {group.name} has no gid, skipping.",
                )
                continue
            group_dn = f"cn=hpc-ag-{group.name},{BASE_DN_GROUPS}"
            owner = state.hpc_users[group.owner]
            delegate = state.hpc_users[group.delegate] if group.delegate else None
            group_name = f"hpc-ag-{group.name}"
            result[group_name] = LdapGroup(
                dn=group_dn,
                cn=group_name,
                gid_number=group.gid,
                owner_dn=user_dn(owner),
                delegate_dns=[user_dn(delegate)] if delegate else [],
                member_uids=[],
            )
        # build for projects
        for project in state.hpc_projects.values():
            if not project.gid:
                console.log(
                    f"Project {project.name} has no gid, skipping.",
                )
                continue
            group_dn = f"cn=hpc-prj-{project.name},{BASE_DN_PROJECTS}"
            owning_group = state.hpc_groups[project.group]
            owner = state.hpc_users[owning_group.owner]
            delegate = state.hpc_users[project.delegate] if project.delegate else None
            project_name = f"hpc-prj-{project.name}"
            result[project_name] = LdapGroup(
                dn=group_dn,
                cn=project_name,
                gid_number=project.gid,
                owner_dn=user_dn(owner),
                delegate_dns=[user_dn(delegate)] if delegate else [],
                member_uids=[],
            )
        return result


def gather_system_state(settings: Settings) -> SystemState:
    """Gather the system state from LDAP and file system."""
    connection = LdapConnection(settings.ldap_hpc)
    console.log("Loading LDAP users and groups...")
    ldap_users = connection.load_users()
    ldap_groups = connection.load_groups()
    console.log("Loading file system directories...")
    fs_mgr = FsResourceManager(prefix="/data/sshfs" if os.environ.get("DEBUG", "0") == "1" else "")
    fs_directories = fs_mgr.load_directories()
    result = SystemState(
        ldap_users={u.uid: u for u in ldap_users},
        ldap_groups={g.cn: g for g in ldap_groups},
        fs_directories={d.path: d for d in fs_directories},
    )
    console.log("  # of users:", len(result.ldap_users))
    console.log("  # of groups:", len(result.ldap_groups))
    console.log("  # of directories:", len(result.fs_directories))
    console.log("... have system state now")
    return result


class TargetStateComparison:
    """Helper class that compares two system states.

    Differences are handled as follows.

    - LDAP
        - Missing LDAP objects are created.
        - Existing but differing LDAP objects are updated.
        - Extra LDAP users are disabled by setting `loginShell` to `/sbin/nologin`.
    - file system
        - Missing directories are created.
        - Existing but differing directories are updated.
        - Extra directories have the owner set to ``root:root`` and the access
          to them is disabled.
    """

    def __init__(self, settings: HpcaccessSettings, src: SystemState, dst: SystemState):
        #: Configuration of ``hpc-access`` system to use.
        self.settings = settings
        #: Source state
        self.src = src
        #: Target state
        self.dst = dst

    def run(self) -> OperationsContainer:
        """Run the comparison."""
        console.log("Comparing source and target state...")
        result = OperationsContainer(
            ldap_user_ops=self._compare_ldap_users(),
            ldap_group_ops=self._compare_ldap_groups(),
            fs_ops=self._compare_fs_directories(),
        )
        console.log("... have operations now.")
        return result

    def _compare_ldap_users(self) -> List[LdapUserOp]:
        """Compare ``LdapUser`` records between system states."""
        result = []
        extra_usernames = set(self.src.ldap_users.keys()) - set(self.dst.ldap_users.keys())
        missing_usernames = set(self.dst.ldap_users.keys()) - set(self.src.ldap_users.keys())
        common_usernames = set(self.src.ldap_users.keys()) & set(self.dst.ldap_users.keys())
        for username in extra_usernames:
            user = self.src.ldap_users[username]
            result.append(LdapUserOp(operation=StateOperation.DISABLE, user=user, diff={}))
        for username in missing_usernames:
            user = self.src.ldap_users[username]
            result.append(LdapUserOp(operation=StateOperation.CREATE, user=user, diff={}))
        for username in common_usernames:
            src_user = self.src.ldap_users[username]
            dst_user = self.dst.ldap_users[username]
            src_user_dict = src_user.model_dump()
            dst_user_dict = dst_user.model_dump()
            all_keys = set(src_user_dict.keys()) | set(dst_user_dict.keys())
            if src_user_dict != dst_user_dict:
                diff = {}
                for key in all_keys:
                    if src_user_dict.get(key) != dst_user_dict.get(key):
                        diff[key] = dst_user_dict.get(key)
                result.append(LdapUserOp(operation=StateOperation.UPDATE, user=src_user, diff=diff))
        return result

    def _compare_ldap_groups(self) -> List[LdapGroupOp]:
        result = []
        extra_group_names = set(self.src.ldap_groups.keys()) - set(self.dst.ldap_groups.keys())
        missing_group_names = set(self.dst.ldap_groups.keys()) - set(self.src.ldap_groups.keys())
        common_group_names = set(self.src.ldap_groups.keys()) & set(self.dst.ldap_groups.keys())
        for name in extra_group_names:
            group = self.src.ldap_groups[name]
            result.append(LdapGroupOp(operation=StateOperation.DISABLE, group=group, diff={}))
        for name in missing_group_names:
            group = self.dst.ldap_groups[name]
            result.append(LdapGroupOp(operation=StateOperation.CREATE, group=group, diff={}))
        for name in common_group_names:
            src_group = self.src.ldap_groups[name]
            dst_group = self.dst.ldap_groups[name]
            src_group_dict = src_group.model_dump()
            dst_group_dict = dst_group.model_dump()
            all_keys = set(src_group_dict.keys()) | set(dst_group_dict.keys())
            if src_group_dict != dst_group_dict:
                diff = {}
                for key in all_keys:
                    if src_group_dict.get(key) != dst_group_dict.get(key):
                        diff[key] = dst_group_dict.get(key)
                result.append(
                    LdapGroupOp(operation=StateOperation.UPDATE, group=src_group, diff=diff)
                )
        return result

    def _compare_fs_directories(self) -> List[FsDirectoryOp]:
        result = []
        extra_paths = set(self.src.fs_directories.keys()) - set(self.dst.fs_directories.keys())
        missing_paths = set(self.dst.fs_directories.keys()) - set(self.src.fs_directories.keys())
        common_paths = set(self.src.fs_directories.keys()) & set(self.dst.fs_directories.keys())
        for path in extra_paths:
            directory = self.src.fs_directories[path]
            result.append(
                FsDirectoryOp(operation=StateOperation.DISABLE, directory=directory, diff={})
            )
        for path in missing_paths:
            directory = self.dst.fs_directories[path]
            result.append(
                FsDirectoryOp(operation=StateOperation.CREATE, directory=directory, diff={})
            )
        for path in common_paths:
            src_directory = self.src.fs_directories[path]
            dst_directory = self.dst.fs_directories[path]
            src_directory_dict = src_directory.model_dump()
            dst_directory_dict = dst_directory.model_dump()
            all_keys = set(src_directory_dict.keys()) | set(dst_directory_dict.keys())
            if src_directory_dict != dst_directory_dict:
                diff = {}
                for key in all_keys:
                    if src_directory_dict.get(key) != dst_directory_dict.get(key):
                        diff[key] = dst_directory_dict.get(key)
                result.append(
                    FsDirectoryOp(
                        operation=StateOperation.UPDATE,
                        directory=src_directory,
                        diff=diff,
                    )
                )
        return result